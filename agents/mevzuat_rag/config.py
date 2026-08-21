import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")



CHROMA_DB_DIR = str(
    BASE_DIR / os.getenv(
        "CHROMA_DB_DIR",
        "chroma_db",
    )
)
CHUNKS_DIR = BASE_DIR / os.getenv(
    "CHUNKS_DIR",
    "chunks",
)

CHROMA_COLLECTION = os.getenv(
    "CHROMA_COLLECTION",
    "project_laws",
)

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)

LLM_SERVER_URL = os.getenv(
    "LLM_SERVER_URL",
    "http://127.0.0.1:11434",
).rstrip("/")

# Ollama's Python client expects the server root.  Accept an OpenAI-compatible
# `/v1` URL in .env too, so existing installations continue to work.
OLLAMA_SERVER_URL = (
    LLM_SERVER_URL.removesuffix("/v1")
    if LLM_SERVER_URL.endswith("/v1")
    else LLM_SERVER_URL
)
LLM_MODEL = os.getenv(
    "LLM_MODEL",
    "gemma3:4b",    
)

TOP_K = int(os.getenv("TOP_K", "5"))
MAX_DISTANCE = float(os.getenv("MAX_DISTANCE", "0.75"))
INGEST_BATCH_SIZE = int(os.getenv("INGEST_BATCH_SIZE", "64"))

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))

# Comma-separated browser origins.  The bundled chat UI is served by this API.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
