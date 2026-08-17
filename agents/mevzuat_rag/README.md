# PROJECT KAMU — RAG API v2.0

نظام RAG للبحث في القوانين التركية باستخدام ChromaDB + Gemma.

## الملفات

| الملف | الوظيفة |
|---|---|
| `rechunk.py` | إعادة تقسيم النصوص على حدود المواد + overlap |
| `ingest_chunks.py` | تحويل الـ chunks إلى embeddings وحفظها في ChromaDB |
| `rag_service.py` | البحث + Cache + Streaming + History |
| `app.py` | FastAPI endpoints |
| `config.py` | إعدادات من `.env` |
| `schemas.py` | نماذج البيانات |

## التشغيل لأول مرة

```bash
# 1. تثبيت المكتبات
pip install -r requirements.txt

# 2. إعادة تقسيم الـ chunks بشكل ذكي (موصى به)
python rechunk.py

# 3. عدّل CHUNKS_DIR في .env
# CHUNKS_DIR=data/chunks_v2

# 4. بناء الـ index
python ingest_chunks.py

# 5. تشغيل الـ API
python app.py
```

## الـ Endpoints

| Method | Path | الوظيفة |
|---|---|---|
| GET | `/health` | حالة النظام وعدد الـ chunks |
| POST | `/query` | سؤال عادي مع Cache وHistory |
| POST | `/query/stream` | سؤال بـ Streaming (token by token) |
| GET | `/cache/stats` | إحصائيات الـ cache |
| DELETE | `/cache/clear` | تفريغ الـ cache |
| GET | `/docs` | Swagger UI |

## أمثلة

### سؤال عادي
```json
POST /query
{
  "question": "TCK 86. madde nedir?",
  "top_k": 5
}
```

### سؤال مع تاريخ المحادثة
```json
POST /query
{
  "question": "Peki cezası ne kadar?",
  "top_k": 5,
  "history": [
    {"role": "user",      "content": "TCK 86. madde nedir?"},
    {"role": "assistant", "content": "Madde 86, kasten yaralama..."}
  ]
}
```

### Streaming
```bash
curl -N -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -d '{"question": "Kasten yaralama cezası nedir?"}'
```

## إعدادات `.env`

```env
CHUNKS_DIR=data/chunks_v2
CHROMA_DB_DIR=chroma_db
CHROMA_COLLECTION=project_laws
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
LLM_SERVER_URL=http://127.0.0.1:8080/v1
LLM_MODEL=google_gemma-3-4b-it-Q8_0.gguf
TOP_K=5
MAX_DISTANCE=0.75
INGEST_BATCH_SIZE=64
API_HOST=0.0.0.0
API_PORT=8000
```
