import shutil
import tempfile
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Literal

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
)

from pydantic import BaseModel


from orkestrasyon.orchestrator import (
    process_input,
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