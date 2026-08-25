import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orkestrasyon.orchestrator import process_input


app = FastAPI(
    title="BILTEK KAMU API",
    version="1.0.0",
)

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
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "running",
        "message": "BILTEK KAMU backend is ready",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }


@app.post("/process")
def process_document(
    file: Optional[UploadFile] = File(default=None),
    question: Optional[str] = Form(default=None),
):
    temp_path = None

    try:
        # التحقق إذا تم إرسال ملف لحفظه مؤقتاً
        if file and file.filename:
            suffix = Path(file.filename).suffix
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp_file:
                shutil.copyfileobj(
                    file.file,
                    temp_file,
                )
                temp_path = temp_file.name

        # تشغيل Orchestrator (سيتعرف تلقائياً إذا كان الإدخال سؤالاً فقط فيتجه للـ RAG مباشرة)
        result = process_input(
            file=temp_path,
            text=question,
        )

        clean_result = jsonable_encoder(result)
        return JSONResponse(content=clean_result)

    finally:
        # حذف الملف المؤقت بعد المعالجة
        if temp_path:
            path = Path(temp_path)
            if path.exists():
                path.unlink()