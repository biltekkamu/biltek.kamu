"""
ingest_chunks.py — يقرأ JSONL/JSON chunks ويحوّلها إلى embeddings في ChromaDB

الاستخدام:
    python ingest_chunks.py              # يعالج كل ملفات CHUNKS_DIR
    python ingest_chunks.py --reset      # يمسح الـ index ويبنيه من صفر
    python ingest_chunks.py --file x.json  # ملف واحد فقط
"""

import argparse
import hashlib
import json
import logging
import sys
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_COLLECTION,
    CHROMA_DB_DIR,
    CHUNKS_DIR,
    EMBEDDING_MODEL,
    INGEST_BATCH_SIZE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("ingest")


def make_id(source: str, chunk_id: int, text: str) -> str:
    """SHA256 كـ ID — يمنع التكرار عند تشغيل الـ script أكثر من مرة."""
    raw = f"{source}|{chunk_id}|{text[:80]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def load_chunks_from_file(path: Path) -> list[dict]:
    """يقرأ JSON أو JSONL ويرجع قائمة chunks موحّدة."""
    raw = path.read_bytes()
    if not raw.strip():
        logger.warning("فارغ: %s", path.name)
        return []

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        logger.error("JSON خطأ: %s — %s", path.name, e)
        return []

    # JSONL: كل سطر كائن منفصل
    if isinstance(data, str):
        chunks = []
        for i, line in enumerate(raw.decode().splitlines()):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError:
                logger.warning("سطر %d غير صالح في %s", i, path.name)
        return chunks

    if isinstance(data, list):
        return data

    logger.warning("صيغة غير معروفة: %s", path.name)
    return []


def clean_metadata(meta: dict) -> dict:
    """ChromaDB يقبل فقط str/int/float/bool في الـ metadata."""
    cleaned = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            cleaned[k] = v
        elif v is None:
            continue
        else:
            cleaned[k] = str(v)
    return cleaned


def ingest(
    files: list[Path],
    collection: chromadb.Collection,
    embedder: SentenceTransformer,
    batch_size: int,
) -> dict:
    total_new = 0
    total_skip = 0
    total_err = 0

    for fpath in files:
        chunks = load_chunks_from_file(fpath)
        if not chunks:
            continue

        ids, texts, metas = [], [], []

        for c in chunks:
            text = c.get("text", "").strip()
            if not text or len(text) < 20:
                total_err += 1
                continue

            source   = c.get("source", fpath.stem)
            chunk_id = c.get("chunk_id", 0)

            meta = {
                "source":        source,
                "chunk_id":      int(chunk_id),
                "document_name": str(c.get("source", fpath.stem)),
                "law_number":    str(c.get("law_number", "")),
                "madde":         str(c.get("madde", "")),
                "char_count":    int(c.get("char_count", len(text))),
            }
            meta.update(clean_metadata(c.get("metadata", {})))

            ids.append(make_id(source, chunk_id, text))
            texts.append(text)
            metas.append(meta)

        if not ids:
            continue

        # تحقق من الـ IDs الموجودة مسبقاً
        try:
            existing = set(collection.get(ids=ids)["ids"])
        except Exception:
            existing = set()

        new_idx   = [i for i, id_ in enumerate(ids) if id_ not in existing]
        new_ids   = [ids[i]   for i in new_idx]
        new_texts = [texts[i] for i in new_idx]
        new_metas = [metas[i] for i in new_idx]

        total_skip += len(existing)

        if not new_ids:
            logger.info("%-45s | كل الـ chunks موجودة مسبقاً (%d)", fpath.name[:45], len(ids))
            continue

        # Embedding على دفعات
        logger.info("%-45s | %d chunk جديد يُعالج...", fpath.name[:45], len(new_ids))
        for start in range(0, len(new_ids), batch_size):
            end        = min(start + batch_size, len(new_ids))
            batch_ids  = new_ids[start:end]
            batch_txt  = new_texts[start:end]
            batch_meta = new_metas[start:end]

            vecs = embedder.encode(
                batch_txt,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()

            collection.upsert(
                ids=batch_ids,
                documents=batch_txt,
                embeddings=vecs,
                metadatas=batch_meta,
            )

        total_new += len(new_ids)

    return {"new": total_new, "skipped": total_skip, "errors": total_err}


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk ingestion → ChromaDB")
    parser.add_argument("--reset", action="store_true", help="امسح الـ collection وابدأ من صفر")
    parser.add_argument("--file",  help="عالج ملف واحد فقط")
    args = parser.parse_args()

    # تهيئة ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_DB_DIR)

    if args.reset:
        try:
            client.delete_collection(CHROMA_COLLECTION)
            logger.info("Collection محذوفة: %s", CHROMA_COLLECTION)
        except Exception:
            pass

    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("Collection: %s | موجود: %d chunk", CHROMA_COLLECTION, collection.count())

    # تحميل الـ embedding model
    logger.info("Embedding model يُحمّل: %s", EMBEDDING_MODEL)
    embedder = SentenceTransformer(EMBEDDING_MODEL)

    # تحديد الملفات
    if args.file:
        files = [CHUNKS_DIR / args.file]
        if not files[0].exists():
            logger.error("الملف غير موجود: %s", files[0])
            sys.exit(1)
    else:
        files = sorted(CHUNKS_DIR.glob("*.json"))
        if not files:
            logger.error("لا يوجد ملفات JSON في: %s", CHUNKS_DIR)
            sys.exit(1)

    logger.info("%d ملف سيُعالج", len(files))

    stats = ingest(files, collection, embedder, INGEST_BATCH_SIZE)

    print("\n" + "═" * 50)
    print(f"  ✅ جديد    : {stats['new']:,} chunk")
    print(f"  ⏭  موجود  : {stats['skipped']:,} chunk")
    print(f"  ❌ خطأ    : {stats['errors']:,} chunk")
    print(f"  📦 الإجمالي: {collection.count():,} chunk في ChromaDB")
    print("═" * 50)
    print(f"\n  الخطوة التالية: python app.py")


if __name__ == "__main__":
    main()
