"""
rag_service.py
Ollama + ChromaDB + BM25 + Query Transformation + RRF + Reranker
"""

import hashlib
import logging
import time
from typing import Any, Generator

import chromadb
from ollama import Client
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from config import (
    CHROMA_COLLECTION,
    CHROMA_DB_DIR,
    EMBEDDING_MODEL,
    LLM_MODEL,
    OLLAMA_SERVER_URL,
    MAX_DISTANCE,
    TOP_K,
)


logger = logging.getLogger("rag-service")


# =========================================================
# Models
# =========================================================

logger.info("Reranker yükleniyor...")

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

logger.info("Reranker hazır.")


logger.info(
    "Embedding modeli yükleniyor: %s",
    EMBEDDING_MODEL
)

embedding_model = SentenceTransformer(
    EMBEDDING_MODEL
)


# =========================================================
# ChromaDB
# =========================================================

chroma_client = chromadb.PersistentClient(
    path=CHROMA_DB_DIR
)

collection = chroma_client.get_or_create_collection(
    name=CHROMA_COLLECTION,
    metadata={
        "hnsw:space": "cosine"
    },
)


logger.info(
    "RAG CHROMA PATH = %s",
    CHROMA_DB_DIR
)

logger.info(
    "RAG COLLECTION = %s",
    CHROMA_COLLECTION
)

logger.info(
    "RAG DOCUMENT COUNT = %d",
    collection.count()
)


# =========================================================
# Reranker
# =========================================================

def rerank_documents(
    query: str,
    documents: list[dict],
    top_n: int = 4,
) -> list[dict]:

    if not documents:
        return []

    pairs = [
        [query, document["text"]]
        for document in documents
    ]

    scores = reranker.predict(pairs)

    for document, score in zip(
        documents,
        scores,
    ):
        document["rerank_score"] = float(
            score
        )

    ranked = sorted(
        documents,
        key=lambda item: item[
            "rerank_score"
        ],
        reverse=True,
    )

    return ranked[:top_n]


# =========================================================
# BM25
# =========================================================

def build_bm25_index():

    count = collection.count()

    if count == 0:
        logger.warning(
            "ChromaDB boş — BM25 index atlandı."
        )

        return [], [], None, []

    batch_size = 5000

    all_documents = []
    all_ids = []
    all_metadatas = []

    for offset in range(
        0,
        count,
        batch_size,
    ):

        batch = collection.get(
            limit=batch_size,
            offset=offset,
            include=[
                "documents",
                "metadatas",
            ],
        )

        all_documents.extend(
            batch["documents"]
        )

        all_ids.extend(
            batch["ids"]
        )

        all_metadatas.extend(
            batch["metadatas"]
        )

    corpus = [
        document.lower().split()
        for document in all_documents
    ]

    index = BM25Okapi(
        corpus
    )

    logger.info(
        "BM25 index hazır: %d döküman",
        len(all_ids),
    )

    return (
        all_documents,
        all_ids,
        index,
        all_metadatas,
    )


(
    _all_docs_list,
    _bm25_ids,
    _bm25_index,
    _all_metadatas,
) = build_bm25_index()


logger.info(
    "BM25 döküman sayısı: %d",
    len(_bm25_ids),
)


# =========================================================
# Ollama
# =========================================================

ollama_client = Client(
    host=OLLAMA_SERVER_URL
)


# =========================================================
# Cache
# =========================================================

_answer_cache: dict[str, dict] = {}

CACHE_MAX_SIZE = 200


def _cache_key(
    question: str,
    top_k: int,
) -> str:

    value = (
        f"{question.strip().lower()}|{top_k}"
    )

    return hashlib.md5(
        value.encode()
    ).hexdigest()


def get_cached(
    question: str,
    top_k: int,
) -> dict | None:

    return _answer_cache.get(
        _cache_key(
            question,
            top_k,
        )
    )


def set_cache(
    question: str,
    top_k: int,
    result: dict,
) -> None:

    if len(
        _answer_cache
    ) >= CACHE_MAX_SIZE:

        oldest = next(
            iter(
                _answer_cache
            )
        )

        del _answer_cache[
            oldest
        ]

    _answer_cache[
        _cache_key(
            question,
            top_k,
        )
    ] = result


# =========================================================
# Question normalization
# =========================================================

def normalize_question(
    question: str,
) -> str:

    question = " ".join(
        question.strip().split()
    )

    question = question.replace(
        "MADDE",
        "Madde",
    )

    question = question.replace(
        "madde",
        "Madde",
    )

    return question


# =========================================================
# Query Transformation
# =========================================================

def transform_query(
    question: str,
) -> str:

    prompt = f"""
Sen Türk hukuku için bir RAG arama sorgusu dönüştürücüsün.

Görevin:
Kullanıcının sorusunu mevzuat veri tabanında arama yapmak için
daha açık ve hukuki terminoloji içeren bir sorguya dönüştür.

Kurallar:
- Sorunun anlamını değiştirme.
- Kullanıcının önemli anahtar kelimelerini koru.
- Uygun hukuki terimleri ekle.
- Emin olmadığın kanun veya madde numarasını uydurma.
- Soruyu cevaplama.
- Açıklama yapma.
- Sadece dönüştürülmüş arama sorgusunu yaz.

Örnekler:

"Kiracımı nasıl çıkarırım?"
→ Kiracının tahliyesi, tahliye şartları ve ilgili mevzuat

"Komşum bana vurdu"
→ Kasten yaralama suçu ve ilgili Türk Ceza Kanunu hükümleri

"İşten atıldım"
→ İş sözleşmesinin feshi, haksız fesih ve işçinin hakları

"Araba çaldılar"
→ Araç hırsızlığı suçu ve ilgili Türk Ceza Kanunu hükümleri

Kullanıcı sorusu:
{question}

Arama sorgusu:
"""

    try:

        response = ollama_client.chat(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            options={
                "temperature": 0.1
            },
        )

        transformed = (
            response
            .message
            .content
            .strip()
        )

        if not transformed:
            return question

        logger.info(
            "Query Transformation | '%s' -> '%s'",
            question,
            transformed,
        )

        return transformed

    except Exception as error:

        logger.warning(
            "Query Transformation başarısız: %s",
            error,
        )

        return question


# =========================================================
# Retrieval
# =========================================================

def retrieve_documents(
        
    question: str,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    

    
    
    t_start = time.time()

    if collection.count() == 0:
        return []
    # -----------------------------------------
    # Query Transformation
    # -----------------------------------------

    legal_query = transform_query(question)

    logger.info(
        "Query Transformation: %.2fs",
        time.time() - t_start
    )
    
    search_query = f"{question} {legal_query}"
    
    logger.info(
    "Search query: %s",
    search_query,
)

    
    

    # -----------------------------------------
    # Semantic Search
    # -----------------------------------------
    t_semantic = time.time()
    query_embedding = embedding_model.encode(   
        search_query,
        normalize_embeddings=True,
    ).tolist()
    

    candidate_count = min(
        top_k * 3,
        collection.count(),
    )

    sem_results = collection.query(
        query_embeddings=[
            query_embedding
        ],
        n_results=candidate_count,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    logger.info(
        "Semantic Search: %.2fs",
        time.time() - t_semantic
    )

    sem_docs = (
    sem_results[
        "documents"
    ][0]
)

    sem_metas = (
    sem_results[
        "metadatas"
    ][0]
)

    sem_dists = (
    sem_results[
        "distances"
    ][0]
)

    sem_ids = (
    sem_results[
        "ids"
    ][0]
)

    # -----------------------------------------
    # BM25
    # -----------------------------------------

    bm25_top_idx = []

    if (
        _bm25_index is not None
        and _bm25_ids
    ):

        bm25_scores = (
            _bm25_index
            .get_scores(
                search_query
                .lower()
                .split()
            )
        )

        bm25_top_idx = (
            bm25_scores
            .argsort()[
                -candidate_count:
            ][::-1]
        )

    # -----------------------------------------
    # RRF
    # -----------------------------------------

    rrf_scores: dict[
        str,
        float,
    ] = {}

    doc_map: dict[
        str,
        dict,
    ] = {}

    # Semantic Results

    for rank, (
        document,
        metadata,
        distance,
        document_id,
    ) in enumerate(
        zip(
            sem_docs,
            sem_metas,
            sem_dists,
            sem_ids,
        ),
        start=1,
    ):

        rrf_scores[
            document_id
        ] = (
            rrf_scores.get(
                document_id,
                0.0,
            )
            + 1 / (60 + rank)
        )

        doc_map[
            document_id
        ] = {
            "text": document,
            "metadata": (
                metadata or {}
            ),
            "distance": float(
                distance
            ),
            "score": 0.0,
        }

    # BM25 Results

    for rank, index in enumerate(
        bm25_top_idx,
        start=1,
    ):

        document_id = (
            _bm25_ids[index]
        )

        rrf_scores[
            document_id
        ] = (
            rrf_scores.get(
                document_id,
                0.0,
            )
            + 1 / (60 + rank)
        )

        if (
            document_id
            not in doc_map
        ):

            doc_map[
                document_id
            ] = {
                "text": (
                    _all_docs_list[
                        index
                    ]
                ),
                "metadata": (
                    _all_metadatas[
                        index
                    ]
                    or {}
                ),
                "distance": None,
                "score": 0.0,
            }

    # -----------------------------------------
    # Sort RRF candidates
    # -----------------------------------------

    ranked = sorted(
        rrf_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    max_rrf = (
        max(
            rrf_scores.values()
        )
        if rrf_scores
        else 1.0
    )

    retrieved = []

    # ناخد مرشحين أكثر قبل reranking

    for (
        document_id,
        rrf_score,
    ) in ranked[
        : top_k * 3
    ]:

        item = doc_map[
            document_id
        ]

        distance = item.get(
            "distance"
        )

        # إذا نتيجة Semantic:
        # طبق MAX_DISTANCE.
        #
        # إذا BM25 فقط:
        # distance = None
        # لا نحذفها بسبب threshold.

        if (
            distance is not None
            and distance > MAX_DISTANCE
        ):
            continue

        item["score"] = round(
            rrf_score / max_rrf,
            3,
        )

        retrieved.append(
            item
        )

    if not retrieved:
        return []

    # -----------------------------------------
    # Reranking
    # -----------------------------------------
    t_rerank = time.time()

    retrieved = rerank_documents(
        question,
        retrieved,
        top_n=top_k,
    )
    logger.info(
        "Reranker: %.2fs",
        time.time() - t_rerank
    )

    logger.info(
        "TOTAL RETRIEVAL: %.2fs",
        time.time() - t_start
    )

    return retrieved
    

# =========================================================
# Context
# =========================================================

def build_context(
    documents: list[dict[str, Any]],
) -> str:

    sections = []

    for index, item in enumerate(
        documents,
        start=1,
    ):

        metadata = (
            item.get(
                "metadata"
            )
            or {}
        )

        madde = metadata.get(
            "madde",
            "",
        )

        madde_str = (
            f"Madde {madde} | "
            if madde
            else ""
        )

        law_name = metadata.get(
            "law_name",
            "?",
        )

        law_number = metadata.get(
            "law_number",
            "-",
        )

        score = item.get(
            "score",
            0.0,
        )

        text = item.get(
    "text",
    "",
)[:1800]

        sections.append(
            f"[KAYNAK {index}] "
            f"{madde_str}"
            f"Kanun: {law_name} | "
            f"No: {law_number} | "
            f"Eşleşme: %{score * 100:.0f}\n"
            f"{text}"
        )

    return (
        "\n\n---\n\n"
        .join(
            sections
        )
    )


# =========================================================
# Prompt
# =========================================================

SYSTEM_PROMPT = """
Sen Türk kamu kurumlarında görev yapan deneyimli bir hukuk müşavirisinin rolünü üstleniyorsun.
Görevin: Gelen evrak ve yazışmaları analiz etmek, ilgili mevzuatı tespit etmek ve net hukuki yanıtlar üretmek.

SADECE hukuki sorulara cevap ver.
Hukuki olmayan sorulara: "Ben yalnızca Türk kamu mevzuatı ile ilgili sorulara yardımcı olabilirim." de.

━━━ YANIT FORMATI ━━━

**ÖZET**
Soruyu kendi cümlelerinle 1-2 cümlede yanıtla.
Madde metnini AYNEN kopyalama — özetle.

**YASAL DAYANAK**
- Kanun adı ve numarası
- İlgili madde numarası
- Maddenin tam adı

**DETAYLAR**
- Temel hüküm ve ceza miktarı
- Ağırlaştırıcı haller (varsa)
- Hafifletici haller (varsa)
- İstisnalar (varsa)

**SONUÇ**
Kısa ve net bir değerlendirme.

⚠️ Bu yanıt genel bilgi amaçlıdır. Kesin hukuki işlemler için yetkili makama başvurunuz.

━━━ KURALLAR ━━━

1. YALNIZCA verilen kaynaklardaki bilgileri kullan — asla uydurma.
2. Kaynaklarda bulunmayan madde numarasını kesinlikle yazma.
3. Birden fazla kaynak varsa en güncel ve ilgili olanı önceliklendir.
4. Kaynaklar soruyla ilgili değilse: "Bu bilgi mevcut belgelerde bulunamadı." de.
5. Ceza miktarlarını tam ve doğru yaz — "birkaç yıl" gibi belirsiz ifadeler kullanma.
6. Yanıtta [KAYNAK X] gibi iç referanslar kullanma — sadece kanun ve madde adını yaz.
7. Kullanıcı ayrıntılı açıklama istemedikçe orta uzunlukta, açık ve öz cevap ver.

━━━ KAYNAKLAR ━━━

{context}

━━━ KAYNAKLARIN SONU ━━━
"""

# =========================================================
def compress_history(history: list[dict]) -> list[dict]:
    if len(history) <= 2:
        return history

    old_history = history[:-2]
    recent      = history[-2:]

    old_text = "\n".join(
        f"{h['role'].upper()}: {h['content'][:200]}"
        for h in old_history
    )

    prompt = f"""Aşağıdaki konuşmayı 1-2 cümlede özetle. Sadece özeti yaz.

{old_text}

Özet:"""

    try:
        response = ollama_client.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.1},
        )
        summary = response.message.content.strip()

        compressed = [
            {"role": "user",      "content": f"[Önceki konuşma özeti: {summary}]"},
            {"role": "assistant", "content": "Anladım."},
        ] + recent

        logger.info("History sıkıştırıldı: %d → %d mesaj", len(history), len(compressed))
        return compressed

    except Exception:
        return history[-2:]
# =========================================================

def build_messages(
    question: str,
    context: str,
    history: list[dict] | None = None,
) -> list[dict]:

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(context=context),
        }
    ]

    if history:
        compressed = compress_history(history)
        for history_item in compressed:

            if hasattr(history_item, "model_dump"):
                history_item = history_item.model_dump()

            if not isinstance(history_item, dict):
                continue

            role    = history_item.get("role")
            content = history_item.get("content")

            if role not in {"user", "assistant"}:
                continue

            if not isinstance(content, str) or not content.strip():
                continue

            messages.append({
                "role":    role,
                "content": content.strip(),
            })

    messages.append({
        "role":    "user",
        "content": question,
    })

    return messages

# =========================================================
# Generate answer
# =========================================================

def generate_answer(
    question: str,
    documents: list[dict[str, Any]],
    history: list[dict] | None = None,
) -> str:

    context = build_context(
        documents
    )

    messages = build_messages(
        question,
        context,
        history,
    )

    start_time = time.time()

    response = ollama_client.chat(
        model=LLM_MODEL,
        messages=messages,
        options={
    "temperature": 0.1,
    "num_ctx": 8192,
    "num_predict": 800,
},
    )

    elapsed = round(
        time.time()
        - start_time,
        2,
    )

    answer = (
        response
        .message
        .content
    )

    if not answer:
        raise ValueError(
            "LLM boş cevap döndürdü."
        )

    logger.info(
        "LLM yanıtı: %.2fs",
        elapsed,
    )

    return answer.strip()


# =========================================================
# Streaming
# =========================================================

def generate_answer_stream(
    question: str,
    documents: list[dict[str, Any]],
    history: list[dict] | None = None,
) -> Generator[
    str,
    None,
    None,
]:

    context = build_context(
        documents
    )

    messages = build_messages(
        question,
        context,
        history,
    )

    stream = ollama_client.chat(
        model=LLM_MODEL,
        messages=messages,
        stream=True,
        options={
            "temperature": 0.1,
        "num_ctx": 8192,
        "num_predict": 1200,
        },
    )

    for chunk in stream:

        token = (
            chunk
            .message
            .content
        )

        if token:
            yield token