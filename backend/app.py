import asyncio
import json
import os
import torch
import shutil
import tempfile
import traceback
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"

load_dotenv(BASE_DIR / ".env")
if os.getenv("EVREN_API_KEY") in (None, "", "API_KEY"):
    load_dotenv(BASE_DIR / ".env", override=True)

from fastapi import (
    FastAPI,
    File,
    Form,
    Request,
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
    FileResponse,
    JSONResponse,
    StreamingResponse,
)

from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel


from orkestrasyon.orchestrator import (
    emit_event,
    process_input,
    subscribe_events,
    unsubscribe_events,
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
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
# RESMI YAZI AGENT
# =====================================================

resmi_yazi_agent = (
    ResmiYaziAgent()
)


# =====================================================
# RESMI YAZI REQUEST MODEL
# =====================================================

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

    except HTTPException:
        raise

    except Exception as error:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"İşlem sırasında sunucu hatası oluştu: {str(error)}",
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

        emit_event("orchestrator", "delegating", "Resmi Yazı ajanına görev iletiliyor...")
        emit_event("resmi_yazi", "working", "Resmi yazı taslağı oluşturuluyor...")

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

        emit_event("resmi_yazi", "done", "Resmi yazı taslağı hazırlandı.")
        emit_event("orchestrator", "done", "Resmi yazı oluşturma tamamlandı.")


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
# REAL-TIME TELEMETRY SSE ENDPOINT
# =====================================================

@app.get("/events")
async def stream_agent_events(request: Request):
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    subscribe_events(loop, queue)

    async def event_generator():
        try:
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            unsubscribe_events(loop, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# =====================================================
# FRONTEND STATIC FILES (OPTIONAL DIRECT SERVING)
# =====================================================

if (FRONTEND_DIR / "office-3d").exists():
    app.mount(
        "/office-3d",
        StaticFiles(directory=str(FRONTEND_DIR / "office-3d"), html=True),
        name="office-3d",
    )

@app.get("/{asset_name}")
def serve_frontend_asset(asset_name: str):
    allowed_assets = {
        "index.html",
        "dashboard.html",
        "app.js",
        "dashboard.js",
        "styles.css",
        "dashboard.css",
        "biltek-logo.jpg",
    }
    if asset_name in allowed_assets:
        asset_path = FRONTEND_DIR / asset_name
        if asset_path.exists():
            return FileResponse(asset_path)
    raise HTTPException(status_code=404, detail="Not Found")
