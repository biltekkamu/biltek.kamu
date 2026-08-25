from pathlib import Path
import shutil
import tempfile

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.encoders import jsonable_encoder
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
    file: UploadFile = File(...),
    question: str | None = Form(default=None),
):
    suffix = Path(file.filename).suffix

    temp_path = None

    try:
        # Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:

            shutil.copyfileobj(
                file.file,
                temp_file,
            )

            temp_path = temp_file.name

        # Orchestrator çalıştır
        result = process_input(
            file=temp_path,
            text=question,
        )

        # Enum vb. nesneleri JSON uyumlu hale getir
        clean_result = jsonable_encoder(
            result
        )

        return JSONResponse(
            content=clean_result
        )

    finally:
        # Geçici dosyayı sil
        if temp_path:
            path = Path(temp_path)

            if path.exists():
                path.unlink()