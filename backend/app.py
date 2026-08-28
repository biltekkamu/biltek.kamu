import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"

import io
import sys
from pathlib import Path

import shutil
import tempfile
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal
import json

import edge_tts
from faster_whisper import WhisperModel

from fastapi import (
    FastAPI,
    File,
    Form,
    UploadFile,
    HTTPException,
)

from fastapi.encoders import (
    jsonable_encoder,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from fastapi.responses import (
    JSONResponse,
    StreamingResponse,
)

from pydantic import BaseModel


from orkestrasyon.orchestrator import (
    process_input,
    process_input_stream,
    run_real_rag_stream,
)

from agents.resmi_yazi.agent import (
    ResmiYaziAgent,
)


# =====================================================
# APP
# =====================================================

app = FastAPI(
    title="BILTEK KAMU API",
    version="1.0.0",
)


# =====================================================
# STT MODEL INITIALIZATION (FASTER-WHISPER)
# =====================================================

stt_model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)


# =====================================================
# DASHBOARD MEMORY
# =====================================================

dashboard_history = deque(
    maxlen=50
)


def record_dashboard_event(
    result: dict,
    file_name: str | None,
    question: str | None,
    mode: str,
):

    classification = (
        result.get("classification")
        if isinstance(
            result.get("classification"),
            dict,
        )
        else {}
    )

    analysis = (
        result.get("evrak_analysis")
        if isinstance(
            result.get("evrak_analysis"),
            dict,
        )
        else {}
    )

    routing = (
        result.get("routing")
        if isinstance(
            result.get("routing"),
            dict,
        )
        else {}
    )

    validation = (
        result.get("validation")
        if isinstance(
            result.get("validation"),
            dict,
        )
        else {}
    )

    rag = (
        result.get("rag")
        if isinstance(
            result.get("rag"),
            dict,
        )
        else {}
    )

    timing = (
        result.get("timing")
        if isinstance(
            result.get("timing"),
            dict,
        )
        else {}
    )


    event = {

        "timestamp": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),

        "request_type": (
            "document"
            if file_name
            else "question"
        ),

        "file_name": file_name,

        "question": (
            question[:120]
            if question
            else None
        ),

        "mode": mode,

        "success": bool(
            result.get(
                "success",
                True,
            )
        ),

        "classification": (
            classification.get(
                "label"
            )
        ),

        "classification_confidence": (
            classification.get(
                "confidence"
            )
        ),

        "analysis_confidence": (
            analysis.get(
                "analysis_confidence"
            )
        ),

        "routing": (
            routing.get(
                "selected_department"
            )
        ),

        "validation_status": (
            validation.get(
                "status"
            )
        ),

        "validation_confidence": (
            validation.get(
                "confidence"
            )
        ),

        "issue_count": len(
    validation.get(
        "issues",
        [],
    )
    or []
),

"validation_issues": (
    validation.get(
        "issues",
        [],
    )
    or []
),


        "rag_sources": len(
    rag.get(
        "sources",
        [],
    )
    or []
),

"rag_details": {
    "query": (
        rag.get("query")
        or rag.get("question")
    ),

    "answer": (
        rag.get("answer")
        or rag.get("response")
    ),

    "sources": (
        rag.get(
            "sources",
            [],
        )
        or []
    )[:5],
},

"timing": timing,
    }


    dashboard_history.append(
        event
    )

# =====================================================
# CORS
# =====================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "*",
    ],

    allow_credentials=True,

    allow_methods=[
        "*"
    ],

    allow_headers=[
        "*"
    ],
)


# =====================================================
# RESMI YAZI AGENT
# =====================================================

resmi_yazi_agent = (
    ResmiYaziAgent()
)


# =====================================================
# REQUEST MODELS
# =====================================================

class ChatStreamRequest(
    BaseModel
):
    text: str
    mode: str = "citizen"


class OfficialWritingRequest(
    BaseModel
):

    evrak_analysis: dict

    ocr_result: Optional[
        dict
    ] = None

    rag_result: Optional[
        dict
    ] = None

    routing_result: Optional[
        dict
    ] = None

    writing_type: Optional[
        Literal[
            "cevap_yazisi",
            "talep_yazisi",
            "bilgilendirme_yazisi",
            "basvuru_cevabi",
        ]
    ] = None

    recipient: Optional[
        str
    ] = None


class TTSRequest(
    BaseModel
):
    text: str
    voice: Optional[str] = "tr-TR-AhmetNeural"

# =====================================================
# ROOT
# =====================================================

@app.get("/")
def root():

    return {
        "status": "running",
        "message":
            "BILTEK KAMU backend is ready",
    }


# =====================================================
# HEALTH
# =====================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
    }

# =====================================================
# DASHBOARD
# =====================================================

@app.get("/dashboard")
def get_dashboard():

    events = list(
        dashboard_history
    )

    total = len(events)

    successful = sum(
        1
        for event in events
        if event.get("success")
    )

    invalid = sum(
        1
        for event in events
        if event.get("validation_status") == "invalid"
    )

    warning = sum(
        1
        for event in events
        if event.get("validation_status") == "warning"
    )

    total_times = [
        event.get("timing", {}).get("total")
        for event in events
        if isinstance(
            event.get("timing", {}).get("total"),
            (int, float),
        )
    ]

    average_time = (
        round(
            sum(total_times) / len(total_times),
            2,
        )
        if total_times
        else 0.0
    )

    return {
        "summary": {
            "total_requests": total,
            "successful": successful,
            "invalid": invalid,
            "warning": warning,
            "average_processing_time": average_time,
        },

        "last_process": (
            events[-1]
            if events
            else None
        ),

        "recent_processes": list(
            reversed(events)
        ),
    }

# =====================================================
@app.post("/chat/stream")
def chat_stream(
    payload: ChatStreamRequest,
):

    text = (
        payload.text or ""
    ).strip()

    if not text:

        raise HTTPException(
            status_code=400,
            detail="Soru boş olamaz.",
        )

    mode = (
        payload.mode
        if payload.mode
        in {"citizen", "expert"}
        else "citizen"
    )

    def event_generator():

        try:

            for item in (
                run_real_rag_stream(
                    question=text,
                    mode=mode,
                    top_k=5,
                )
            ):

                yield (
                    "data: "
                    + json.dumps(
                        item,
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )

            yield "data: [DONE]\n\n"

        except Exception as error:

            error_payload = {
                "type": "error",
                "text":
                    "Yanıt oluşturulurken bir hata oluştu.",
                "detail": str(error),
            }

            yield (
                "data: "
                + json.dumps(
                    error_payload,
                    ensure_ascii=False,
                )
                + "\n\n"
            )

            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":
                "no-cache",

            "Connection":
                "keep-alive",

            "X-Accel-Buffering":
                "no",
        },
    )

    # =====================================================
# STREAM DOCUMENT PROCESS
# =====================================================

@app.post("/process/stream")
def process_document_stream(

    file: Optional[
        UploadFile
    ] = File(
        default=None
    ),

    question: Optional[
        str
    ] = Form(
        default=None
    ),

    mode: str = Form(
        default="citizen"
    ),
):

    if not file or not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Belge yüklenmelidir.",
        )

    if mode not in {
        "citizen",
        "expert",
    }:
        mode = "citizen"

    suffix = Path(
        file.filename
    ).suffix

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix,
    ) as temp_file:

        shutil.copyfileobj(
            file.file,
            temp_file,
        )

        temp_path = (
            temp_file.name
        )

    original_filename = (
        file.filename
    )

    def event_generator():

        final_result = None

        try:

            for item in process_input_stream(
                file=temp_path,
                text=question,
                mode=mode,
            ):

                if (
                    isinstance(item, dict)
                    and item.get("type") == "done"
                ):
                    final_result = item.get(
                        "result"
                    )

                yield (
                    "data: "
                    + json.dumps(
                        jsonable_encoder(
                            item
                        ),
                        ensure_ascii=False,
                    )
                    + "\n\n"
                )

            # Dashboard'a kaydet
            if isinstance(
                final_result,
                dict,
            ):
                record_dashboard_event(
                    result=final_result,
                    file_name=original_filename,
                    question=question,
                    mode=mode,
                )

            yield "data: [DONE]\n\n"

        except Exception as error:

            error_payload = {
                "type": "error",
                "text":
                    "Belge işlenirken bir hata oluştu.",
                "detail": str(error),
            }

            yield (
                "data: "
                + json.dumps(
                    error_payload,
                    ensure_ascii=False,
                )
                + "\n\n"
            )

            yield "data: [DONE]\n\n"

        finally:

            path = Path(
                temp_path
            )

            if path.exists():
                path.unlink()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":
                "no-cache",

            "Connection":
                "keep-alive",

            "X-Accel-Buffering":
                "no",
        },
    )
# MAIN PROCESS
# =====================================================

@app.post("/process")
def process_document(

    file: Optional[
        UploadFile
    ] = File(
        default=None
    ),

    question: Optional[
        str
    ] = Form(
        default=None
    ),

    mode: str = Form(
        default="citizen"
    ),
):

    temp_path = None


    try:

        # ---------------------------------------------
        # TEMP FILE
        # ---------------------------------------------

        if (
            file
            and file.filename
        ):

            suffix = Path(
                file.filename
            ).suffix


            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp_file:

                shutil.copyfileobj(
                    file.file,
                    temp_file,
                )

                temp_path = (
                    temp_file.name
                )


        # ---------------------------------------------
        # ORCHESTRATOR
        # ---------------------------------------------

        result = process_input(
            file=temp_path,
            text=question,
            mode=mode,
        )


        clean_result = (
            jsonable_encoder(
                result
            )
        )
        record_dashboard_event(

    result=clean_result,

    file_name=(
        file.filename
        if file
        else None
    ),

    question=question,

    mode=mode,
)


        return JSONResponse(
            content=clean_result
        )


    finally:

        # ---------------------------------------------
        # DELETE TEMP FILE
        # ---------------------------------------------

        if temp_path:

            path = Path(
                temp_path
            )

            if path.exists():

                path.unlink()


# =====================================================
# ON-DEMAND RESMI YAZI
# =====================================================

@app.post(
    "/official-writing"
)
def create_official_writing(
    payload: OfficialWritingRequest,
):

    try:

        result = (
            resmi_yazi_agent.generate(

                evrak_analysis=(
                    payload.evrak_analysis
                ),

                ocr_result=(
                    payload.ocr_result
                ),

                rag_result=(
                    payload.rag_result
                ),

                routing_result=(
                    payload.routing_result
                ),

                writing_type=(
                    payload.writing_type
                ),

                recipient=(
                    payload.recipient
                ),
            )
        )


        if hasattr(
            result,
            "model_dump",
        ):

            result_data = (
                result.model_dump()
            )

        else:

            result_data = result


        return JSONResponse(
            content=jsonable_encoder(
                result_data
            )
        )


    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Resmi yazı oluşturulamadı: "
                f"{str(error)}"
            ),
        )


# =====================================================
# TEXT TO SPEECH (EDGE-TTS)
# =====================================================

@app.post("/audio/tts")
async def text_to_speech_edge(
    req: TTSRequest
):
    try:
        clean_text = (
            req.text
            .replace("**", "")
            .replace("##", "")
            .replace("#", "")
            .replace("⚠️", "")
            .strip()
        )[:1000]

        if not clean_text:
            raise HTTPException(
                status_code=400,
                detail="Metin boş olamaz."
            )

        voice = req.voice or "tr-TR-AhmetNeural"
        communicate = edge_tts.Communicate(clean_text, voice)
        audio_stream = io.BytesIO()

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_stream.write(chunk["data"])

        audio_stream.seek(0)
        return StreamingResponse(
            audio_stream,
            media_type="audio/mpeg"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"TTS Hatası: {str(e)}"
        )


# =====================================================
# SPEECH TO TEXT (FASTER-WHISPER)
# =====================================================

@app.post("/audio/stt")
async def speech_to_text(
    file: UploadFile = File(...)
):
    temp_audio_path = None
    try:
        suffix = Path(file.filename or "recording.webm").suffix or ".webm"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_audio:
            shutil.copyfileobj(file.file, temp_audio)
            temp_audio_path = temp_audio.name

        segments, _ = stt_model.transcribe(
            temp_audio_path,
            language="tr",
            vad_filter=True,
            beam_size=5
        )

        transcribed_text = " ".join([s.text for s in segments]).strip()

        return JSONResponse(
            content={"text": transcribed_text}
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"STT Hatası: {str(error)}"
        )

    finally:
        if temp_audio_path:
            p = Path(temp_audio_path)
            if p.exists():
                p.unlink()