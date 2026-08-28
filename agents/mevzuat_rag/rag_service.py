"""
rag_service.py
ChromaDB + BM25 + Query Transformation + RRF + Reranker + Evren LLM-Large
"""

import hashlib
import logging
import os
import time
from typing import Any, Generator

import chromadb
from dotenv import load_dotenv
from openai import OpenAI
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder, SentenceTransformer

from .config import (
    CHROMA_COLLECTION,
    CHROMA_DB_DIR,
    EMBEDDING_MODEL,
    MAX_DISTANCE,
    TOP_K,
)

load_dotenv()

logger = logging.getLogger("rag-service")

# =========================================================
# Evren LLM-Large API Configuration
# =========================================================

LLM_MODEL = "llm-large"
EVREN_API_KEY = os.getenv("EVREN_API_KEY", "")
EVREN_BASE_URL = "https://evren-llmapi.ssyz.org.tr/v1"

if not EVREN_BASE_URL.endswith("/"):
    EVREN_BASE_URL += "/"

evren_client = OpenAI(
    api_key=EVREN_API_KEY,
    base_url=EVREN_BASE_URL,
    timeout=60.0,
)

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
- Soruda veya belge bağlamında açıkça belirtilen kanun ve madde numaralarını aynen koru ve sorgudan çıkarma.
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

        response = evren_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0.0,
            max_tokens=150,
        )

        transformed = (
            response
            .choices[0]
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

    # =====================================================
    # 1. QUERY TRANSFORMATION
    # =====================================================

    legal_query = transform_query(
        question
    )

    logger.info(
        "Query Transformation: %.2fs",
        time.time() - t_start,
    )

    search_query = (
        f"{question} {legal_query}"
    ).strip()

    logger.info(
        "Search query: %s",
        search_query,
    )

    # =====================================================
    # 2. QUERY TOKENS
    # =====================================================

    query_tokens = {
        token.strip(
            ".,:;!?()[]{}\"'"
        )
        for token in search_query
        .lower()
        .split()
        if len(token) > 2
    }

    # =====================================================
    # 3. SEMANTIC SEARCH
    # =====================================================

    t_semantic = time.time()

    query_embedding = embedding_model.encode(
        search_query,
        normalize_embeddings=True,
    ).tolist()

    # Önceden top_k * 3 idi.
    # Daha fazla aday alıyoruz ki temel madde erken kaybolmasın.
    candidate_count = min(
        max(
            top_k * 8,
            30,
        ),
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
        time.time() - t_semantic,
    )

    sem_docs = (
        sem_results["documents"][0]
    )

    sem_metas = (
        sem_results["metadatas"][0]
    )

    sem_dists = (
        sem_results["distances"][0]
    )

    sem_ids = (
        sem_results["ids"][0]
    )

    # =====================================================
    # 4. BM25
    # =====================================================

    bm25_top_idx = []

    if (
        _bm25_index is not None
        and _bm25_ids
    ):

        bm25_scores = (
            _bm25_index.get_scores(
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

    # =====================================================
    # 5. RRF
    # =====================================================

    rrf_scores: dict[
        str,
        float,
    ] = {}

    doc_map: dict[
        str,
        dict,
    ] = {}

    # -------------------------
    # Semantic candidates
    # -------------------------

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

    # -------------------------
    # BM25 candidates
    # -------------------------

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

        if document_id not in doc_map:

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

    if not rrf_scores:
        return []

    # =====================================================
    # 6. RRF SORT
    # =====================================================

    ranked = sorted(
        rrf_scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    max_rrf = max(
        rrf_scores.values()
    )

    retrieved = []

    # Reranker öncesinde de daha geniş aday havuzu.
    pre_rerank_limit = min(
        top_k * 8,
        len(ranked),
    )

    for (
        document_id,
        rrf_score,
    ) in ranked[
        :pre_rerank_limit
    ]:

        item = doc_map[
            document_id
        ]

        distance = item.get(
            "distance"
        )

        if (
            distance is not None
            and distance > MAX_DISTANCE
        ):
            continue

        item["score"] = round(
            rrf_score / max_rrf,
            4,
        )

        retrieved.append(
            item
        )

    if not retrieved:
        return []

    # =====================================================
    # 7. RERANKING
    # =====================================================

    t_rerank = time.time()

    # Final top_k'ya hemen düşürmüyoruz.
    # Önce daha fazla sonucu rerank ediyoruz.
    rerank_count = min(
        top_k * 3,
        len(retrieved),
    )

    retrieved = rerank_documents(
        search_query,
        retrieved,
        top_n=rerank_count,
    )

    logger.info(
        "Reranker: %.2fs",
        time.time() - t_rerank,
    )

    # =====================================================
    # 8. LEGAL + LEXICAL BOOST
    # =====================================================

    for document in retrieved:

        metadata = (
            document.get(
                "metadata",
                {}
            )
            or {}
        )

        text = document.get(
            "text",
            "",
        )

        law_name = str(
            metadata.get(
                "law_name",
                ""
            )
        )

        law_number = str(
            metadata.get(
                "law_number",
                ""
            )
        )

        article = str(
            metadata.get(
                "madde",
                ""
            )
        )

        searchable_text = (
            f"{law_name} "
            f"{law_number} "
            f"{article} "
            f"{text}"
        ).lower()

        document_tokens = {
            token.strip(
                ".,:;!?()[]{}\"'"
            )
            for token
            in searchable_text.split()
            if len(token) > 2
        }

        # Query ile doğrudan kelime örtüşmesi
        overlap = (
            query_tokens
            & document_tokens
        )

        lexical_score = (
            len(overlap)
            / max(
                len(query_tokens),
                1,
            )
        )

        rerank_score = float(
            document.get(
                "rerank_score",
                0.0,
            )
        )

        rrf_score = float(
            document.get(
                "score",
                0.0,
            )
        )

        # Eğer query içinde kanun/madde açıkça geçiyorsa
        # ilgili belgeye ekstra boost.
        explicit_boost = 0.0

        if (
            law_number
            and law_number
            in search_query
        ):
            explicit_boost += 1.0

        if article:

            article_patterns = [
                f"madde {article}",
                f"Madde {article}",
                f" {article} ",
            ]

            if any(
                pattern.lower()
                in (
                    " "
                    + search_query.lower()
                    + " "
                )
                for pattern
                in article_patterns
            ):
                explicit_boost += 1.5

        # Final hybrid skor
        document[
            "final_score"
        ] = (
            rerank_score
            + (rrf_score * 1.5)
            + (lexical_score * 2.0)
            + explicit_boost
        )

    # =====================================================
    # 9. FINAL SORT
    # =====================================================

    retrieved = sorted(
        retrieved,
        key=lambda item: item.get(
            "final_score",
            0.0,
        ),
        reverse=True,
    )

    retrieved = retrieved[
        :top_k
    ]

    logger.info(
        "TOTAL RETRIEVAL: %.2fs",
        time.time() - t_start,
    )

    # Debug için çok faydalı
    for index, document in enumerate(
        retrieved,
        start=1,
    ):

        metadata = (
            document.get(
                "metadata",
                {}
            )
            or {}
        )

        logger.info(
            "TOP %d | Kanun=%s | Madde=%s | "
            "RRF=%.3f | Rerank=%.3f | Final=%.3f",
            index,
            metadata.get(
                "law_number"
            ),
            metadata.get(
                "madde"
            ),
            document.get(
                "score",
                0.0,
            ),
            document.get(
                "rerank_score",
                0.0,
            ),
            document.get(
                "final_score",
                0.0,
            ),
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
EXPERT_SYSTEM_PROMPT = """
Sen Türk kamu kurumlarında görev yapan deneyimli ve kıdemli bir hukuk müşavirisin.
Görevin: Gelen evrakı, belge bağlamını ve sağlanan mevzuat kaynaklarını analiz ederek NET, RESMİ ve SONUÇ ODAKLI bir hukuki değerlendirme üretmektir.

SADECE hukuki ve idari mevzuata ilişkin değerlendirmeler yap.
Hukuki/idari olmayan sorulara: "Ben yalnızca Türk kamu mevzuatı ile ilgili sorulara yardımcı olabilirim." de.

━━━ TEMEL İLKELER ━━━
1. NETLİK VE ÖZLÜLÜK:
   - Yanıtı ASLA gereksiz yere uzatma. Alakasız kaynakları tek tek madde madde sayarak ("Kaynak 1 alakasızdır, Kaynak 2 trafikle ilgilidir..." gibi) vakit ve yer kaybetme.
   - Doğrudan belgedeki talebe ve ilgili yasal dayanağa odaklan.
2. BELGEDEKİ VE KAYNAKLARDAKİ MEVZUAT BİLGİSİ:
   - Belge metninde açıkça belirtilen bir kanun/madde dayanağı varsa (Örn: 2886 sayılı Kanun m. 51/g - Pazarlık Usulü), bunu temel yasal dayanak olarak kabul et ve değerlendir.
3. UYDURMA YASAKTIR:
   - Belgede veya kaynaklarda olmayan varsayımsal hükümleri veya hayali kanunları ekleme.

━━━ ZORUNLU YANIT FORMATI ━━━

**ÖZET**
(Belgedeki talebin ve hukuki durumun amacını açıklayan en fazla 2 net cümle.)

**YASAL DAYANAK**
- Belgedeki Dayanak: [Belgede geçen ilgili Kanun ve Madde numarası]
- Mevzuat Çerçevesi: [Talep edilen usulün yasal tanımı ve kapsamı]

**DETAYLAR**
- Yetki ve Usul: [İşlemin yürütülme usulü, komisyon teşkili ve onay makamının yetki sınırları]
- İdari Şartlar: [İşlemin gerçekleştirilmesi için aranan temel mevzuat kriterleri]

**SONUÇ**
(Makam onayına sunulmasında ve ilgili birimce yürütülmesinde hukuki engel bulunup bulunmadığına dair 2-3 cümlelik net nihai kanaat.)

⚠️ Bu yanıt genel bilgi amaçlıdır. Kesin hukuki işlemler için yetkili makama başvurunuz.

━━━ KAYNAKLAR ━━━

{context}

━━━ KAYNAKLARIN SONU ━━━
"""

CITIZEN_SYSTEM_PROMPT = """
Sen Türk mevzuatı hakkında vatandaşlara açık ve anlaşılır bilgi veren bir asistansın.

SADECE hukuki sorulara cevap ver.
Hukuki olmayan sorulara: "Ben yalnızca Türk kamu mevzuatı ile ilgili sorulara yardımcı olabilirim." de.

YANIT TARZI:
- Sade, anlaşılır ve doğrudan vatandaşın anlayacağı bir dil kullan.
- İlk cümlede doğrudan cevabı ver.
- En fazla 3-5 kısa cümle ile yanıtı tamamla.
- Kaynakları tek tek açıklama; sadece vatandaşın bilmesi gereken işlem sonucunu, nereye başvuracağını veya usulü belirt.
- Başlık (ÖZET, DETAYLAR vb.) kullanma.

KAYNAKLAR:

{context}

KAYNAKLARIN SONU
"""

# =========================================================
def compress_history(history: list[dict]) -> list[dict]:
    if len(history) <= 2:
        return history

    old_history = history[:-2]
    recent = history[-2:]

    old_text = "\n".join(
        f"{h['role'].upper()}: {h['content'][:200]}"
        for h in old_history
    )

    prompt = f"""Aşağıdaki konuşmayı 1-2 cümlede özetle. Sadece özeti yaz.

{old_text}

Özet:"""

    try:
        response = evren_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=150,
        )
        summary = response.choices[0].message.content.strip()

        compressed = [
            {"role": "user", "content": f"[Önceki konuşma özeti: {summary}]"},
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
    mode: str = "citizen",
) -> list[dict]:

    system_prompt = (
        EXPERT_SYSTEM_PROMPT
        if mode == "expert"
        else CITIZEN_SYSTEM_PROMPT
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt.format(context=context),
        }
    ]

    if history:
        compressed = compress_history(history)
        for history_item in compressed:

            if hasattr(history_item, "model_dump"):
                history_item = history_item.model_dump()

            if not isinstance(history_item, dict):
                continue

            role = history_item.get("role")
            content = history_item.get("content")

            if role not in {"user", "assistant"}:
                continue

            if not isinstance(content, str) or not content.strip():
                continue

            messages.append({
                "role": role,
                "content": content.strip(),
            })

    messages.append({
        "role": "user",
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
    mode: str = "citizen",
) -> str:

    # =====================================================
    # 1. Context oluştur
    # =====================================================

    context = build_context(
        documents
    )

    # =====================================================
    # 2. Retrieved kaynakları açık şekilde LLM'e bildir
    # =====================================================

    source_lines = []

    for index, doc in enumerate(
        documents,
        start=1,
    ):
        metadata = doc.get(
            "metadata",
            {},
        )

        law_name = metadata.get(
            "law_name",
            metadata.get(
                "document_name",
                "Bilinmeyen Kaynak",
            ),
        )

        law_number = metadata.get(
            "law_number",
            "",
        )

        article = metadata.get(
            "madde",
            "",
        )

        source_lines.append(
            f"{index}. "
            f"Kanun: {law_name} | "
            f"Kanun No: {law_number} | "
            f"Madde: {article}"
        )

    allowed_sources = "\n".join(
        source_lines
    )

    # =====================================================
    # 3. LLM'e sıkı kaynak kuralları ekle
    # =====================================================

    if mode == "expert":
        mode_rule = """
8. YASAL DAYANAK bölümünde, belge bağlamında açıkça belirtilen kanun/maddeyi ve/veya SOURCES listesindeki ilgili hükümleri temel alarak değerlendirme yap.
"""
    else:
        mode_rule = """
8. Vatandaş modunda ÖZET, YASAL DAYANAK, DETAYLAR ve SONUÇ
   başlıklarını kullanma. Cevabı sade, kısa ve doğrudan ver.
"""

    guarded_question = f"""
KULLANICI SORUSU / BELGE BAĞLAMI:
{question}

KULLANILMASINA İZİN VERİLEN MEVZUAT KAYNAKLARI:
{allowed_sources}

ZORUNLU KURALLAR:

1. Yalnızca yukarıdaki retrieved kaynakları, incelenen belge bağlamını ve verilen CONTEXT'i kullan.

2. Kaynaklarda veya belge bağlamında bulunmayan hiçbir kanun numarası, madde numarası veya hukuki hüküm uydurma.

3. Belge metninde açıkça bir kanun ve madde belirtilmişse (Örn: 2886 sayılı Kanun Madde 51/g), bu dayanağı ve usulü ana hukuki zemin olarak değerlendir.

4. Retrieved kaynaklar arasında soruyla doğrudan ilişkili olan maddelere öncelik ver.

5. Olmayan bilgileri hukuki gerçekmiş gibi yazma.

{mode_rule}
"""

    messages = build_messages(
        guarded_question,
        context,
        history,
        mode=mode,
    )

    # =====================================================
    # 4. LLM çağrısı
    # =====================================================

    start_time = time.time()

    response = evren_client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.0,
        max_tokens=900 if mode == "expert" else 600,
    )

    elapsed = round(
        time.time()
        - start_time,
        2,
    )

    answer = (
        response
        .choices[0]
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
    mode: str = "citizen",
) -> Generator[str, None, None]:

    context = build_context(documents)

    source_lines = []

    for index, doc in enumerate(
        documents,
        start=1,
    ):
        metadata = doc.get(
            "metadata",
            {},
        )

        law_name = metadata.get(
            "law_name",
            metadata.get(
                "document_name",
                "Bilinmeyen Kaynak",
            ),
        )

        law_number = metadata.get(
            "law_number",
            "",
        )

        article = metadata.get(
            "madde",
            "",
        )

        source_lines.append(
            f"{index}. "
            f"Kanun: {law_name} | "
            f"Kanun No: {law_number} | "
            f"Madde: {article}"
        )

    allowed_sources = "\n".join(
        source_lines
    )

    if mode == "expert":
        mode_rule = """
8. YASAL DAYANAK bölümünde, belge bağlamında açıkça belirtilen kanun/maddeyi ve/veya SOURCES listesindeki ilgili hükümleri temel alarak değerlendirme yap.
"""
    else:
        mode_rule = """
8. Vatandaş modunda ÖZET, YASAL DAYANAK, DETAYLAR ve SONUÇ
başlıklarını kullanma. Cevabı sade, kısa ve doğrudan ver.
"""

    guarded_question = f"""
KULLANICI SORUSU / BELGE BAĞLAMI:
{question}

KULLANILMASINA İZİN VERİLEN MEVZUAT KAYNAKLARI:
{allowed_sources}

ZORUNLU KURALLAR:

1. Yalnızca yukarıdaki retrieved kaynakları, incelenen belge bağlamını ve verilen CONTEXT'i kullan.
2. Kaynaklarda veya belge bağlamında bulunmayan kanun veya madde numarası uydurma.
3. Belge metninde açıkça bir kanun ve madde belirtilmişse (Örn: 2886 sayılı Kanun Madde 51/g), bu dayanağı ve usulü ana hukuki zemin olarak değerlendir.
4. Soruyla doğrudan ilişkili kaynaklara öncelik ver.
5. Olmayan bilgileri hukuki gerçekmiş gibi yazma.

{mode_rule}
"""

    messages = build_messages(
        guarded_question,
        context,
        history,
        mode=mode,
    )

    stream = evren_client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        stream=True,
        temperature=0.0,
        max_tokens=900 if mode == "expert" else 600,
    )

    for chunk in stream:

        if not chunk.choices:
            continue

        token = (
            chunk.choices[0]
            .delta
            .content
        )

        if token:
            yield token