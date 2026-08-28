

import logging
import time
import uuid
from collections import defaultdict
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
BASE_DIR = Path(__file__).resolve().parent
from config import API_HOST, API_PORT, CHROMA_COLLECTION, EMBEDDING_MODEL, LLM_MODEL
from rag_service import (
    collection,
    generate_answer,
    generate_answer_stream,
    get_cached,
    normalize_question,
    retrieve_documents,
    set_cache,
)
from schemas import HealthResponse, QueryRequest, QueryResponse, SourceResponse

Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("logs/app.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("kamu-api")

_request_counts: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT     = 30   
RATE_WINDOW    = 60   


def check_rate_limit(ip: str) -> bool:
    now = time.time()
    timestamps = [t for t in _request_counts[ip] if now - t < RATE_WINDOW]
    _request_counts[ip] = timestamps
    if len(timestamps) >= RATE_LIMIT:
        return False
    _request_counts[ip].append(now)
    return True


# ─── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Kamu RAG AI API",
    description="Türk kamu mevzuatına dayalı RAG sistemi",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ────────────────────────────────────────────────────────────────────

@app.get("/chat")
def chat_ui():
    chat_file = BASE_DIR / "chat.html"

    if not chat_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"chat.html bulunamadı: {chat_file}"
        )

    return FileResponse(chat_file)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        collection=CHROMA_COLLECTION,
        document_count=collection.count(),
        embedding_model=EMBEDDING_MODEL,
        llm_model=LLM_MODEL,
    )


@app.post("/query", response_model=QueryResponse)
def query_rag(item: QueryRequest, request: Request):
   
    client_ip = request.client.host if request.client else "unknown"

    if not check_rate_limit(client_ip):
        raise HTTPException(429, "Çok fazla istek. Lütfen bekleyin.")

    request_id = str(uuid.uuid4())
    t0 = time.time()

    try:
        question = normalize_question(item.question)
        top_k    = item.top_k or 5

      
        if not item.history:
            cached = get_cached(question, top_k)
            if cached:
                logger.info("Cache hit | request_id=%s", request_id)
                return QueryResponse(**{**cached, "request_id": request_id, "cached": True})

        # Retrieval
        documents = retrieve_documents(question, top_k)

        if not documents:
            return QueryResponse(
                request_id=request_id,
                answer="Bu bilgi mevcut belgelerde bulunamadı.",
                sources=[],
                retrieved_chunks=0,
                elapsed=round(time.time() - t0, 2),
                cached=False,
            )

        # Generation
        answer = generate_answer(question, documents, item.history)

        sources = [
            SourceResponse(
                document_name=doc["metadata"].get("document_name"),
                law_number=doc["metadata"].get("law_number"),
                madde=doc["metadata"].get("madde"),
                chunk_id=doc["metadata"].get("chunk_id"),
                score=doc.get("score"),
            )
            for doc in documents
        ]

        result = dict(
            answer=answer,
            sources=sources,
            retrieved_chunks=len(documents),
            elapsed=round(time.time() - t0, 2),
            cached=False,
        )

  
        if not item.history:
            set_cache(question, top_k, result)

        logger.info(
            "Sorgu tamamlandı | %.2fs | %d kaynak | request_id=%s",
            result["elapsed"], len(documents), request_id,
        )

        return QueryResponse(request_id=request_id, **result)

    except HTTPException:
        raise
    except Exception as error:
        logger.exception("Soru işlenemedi | request_id=%s", request_id)
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Soru işlenirken hata oluştu.",
                "request_id": request_id,
                "error": str(error),
            },
        ) from error


@app.post("/query/stream")
def query_stream(item: QueryRequest, request: Request):
   
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(429, "Çok fazla istek.")

    question  = normalize_question(item.question)
    top_k     = item.top_k or 5
    documents = retrieve_documents(question, top_k)

    if not documents:
        def empty():
            yield "Bu bilgi mevcut belgelerde bulunamadı."
        return StreamingResponse(empty(), media_type="text/plain")

    def token_stream():
        for token in generate_answer_stream(question, documents, item.history):
            yield token

    return StreamingResponse(token_stream(), media_type="text/plain; charset=utf-8")


@app.get("/cache/stats")
def cache_stats():
   
    from rag_service import _answer_cache
    return {"cached_questions": len(_answer_cache)}


@app.delete("/cache/clear")
def cache_clear():
   
    from rag_service import _answer_cache
    _answer_cache.clear()
    return {"status": "cache temizlendi"}


# ─── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
   uvicorn.run(
    app,
    host=API_HOST,
    port=API_PORT,
    reload=False
)
