from pathlib import Path
import re
import sys
import time
import os

from dotenv import load_dotenv
load_dotenv()

from langchain_openai import ChatOpenAI

from agents.ocr.main_pipeline import MultiPageOCRPipeline
from agents.evrak_analiz.service import EvrakAnalysisService
from agents.classification_agent.hybrid_classifier import (
    HybridDocumentClassifier,
)

from agents.mevzuat_rag.rag_service import (
    normalize_question,
    retrieve_documents,
    generate_answer,
    generate_answer_stream,
)

from agents.birim_yonlendirme.agent import route_unit
from orkestrasyon.router import detect_route
from orkestrasyon.state import create_state


# =====================================================
# PROJECT PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]


# =====================================================
# DOGRULAMA AGENT IMPORT
# =====================================================

validation_agent_dir = (
    BASE_DIR
    / "agents"
    / "dogrulama_agent"
)

if str(validation_agent_dir) not in sys.path:
    sys.path.insert(
        0,
        str(validation_agent_dir),
    )

from validator_service import DocumentValidationService


# =====================================================
# REAL OCR SERVICE
# =====================================================

ocr_pipeline = MultiPageOCRPipeline(
    lang="tr"
)


# =====================================================
# SHARED QWEN LLM (FIXED URL & TIMEOUT)
# =====================================================

EVREN_KEY = os.getenv("EVREN_API_KEY", "sk-evren-team03-6409be56daaf89d55f82a4a9f12b10f1")
EVREN_URL = os.getenv("EVREN_BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1/")
if not EVREN_URL.endswith("/"):
    EVREN_URL += "/"

evrak_llm = ChatOpenAI(
    model="llm-fast",
    api_key=EVREN_KEY,
    base_url=EVREN_URL,
    temperature=0.0,
    timeout=20.0,
    max_retries=1,
)


# =====================================================
# REAL EVRAK ANALIZ SERVICE
# =====================================================

evrak_service = EvrakAnalysisService(
    llm_client=evrak_llm,
)


# =====================================================
# REAL CLASSIFICATION SERVICE
# =====================================================

classifier = HybridDocumentClassifier(
    model_dir=str(
        BASE_DIR
        / "agents"
        / "classification_agent"
        / "berturk_classifier_v1"
    ),
    eval_dir=str(
        BASE_DIR
        / "agents"
        / "classification_agent"
        / "evaluation"
    ),
)


# =====================================================
# REAL DOGRULAMA SERVICE
# =====================================================

validation_service = DocumentValidationService(
    llm_client=evrak_llm,
)


# =====================================================
# REAL RAG
# =====================================================
def build_rag_sources(
    documents: list[dict],
) -> tuple[list[dict], float | None]:

    sources = []
    scores = []

    for doc in documents:

        metadata = (
            doc.get(
                "metadata",
                {},
            )
            or {}
        )

        score = doc.get(
            "score"
        )

        if isinstance(
            score,
            (int, float),
        ):
            scores.append(
                score
            )

        title = metadata.get(
            "law_name",
            metadata.get(
                "document_name",
            ),
        )

        law_number = metadata.get(
            "law_number"
        )

        article = metadata.get(
            "madde"
        )

        if article is not None:

            article = str(
                article
            )

            if not article.lower().startswith(
                "madde"
            ):
                article = (
                    f"Madde {article}"
                )

        content = (
            doc.get("text")
            or doc.get("page_content")
            or doc.get("content")
            or doc.get("document")
            or ""
        )

        sources.append({
            "source_type": "kanun",
            "title": title,
            "law_number": law_number,
            "article": article,
            "content": content,
        })

    confidence = (
        round(
            max(scores),
            3,
        )
        if scores
        else None
    )

    return (
        sources,
        confidence,
    )

def run_real_rag(
    question: str,
    mode: str = "normal",
    top_k: int = 5,
) -> dict:

    normalized_question = normalize_question(
        question
    )

    documents = retrieve_documents(
        normalized_question,
        top_k=top_k,
    )

    if not documents:
        return {
            "query": normalized_question,
            "answer": None,
            "sources": [],
            "confidence": None,
        }

    # =============================================
    # MODE-BASED ANSWER STYLE
    # =============================================
    if mode == "expert":

        generation_question = f"""
Aşağıdaki soruyu uzman/hukukçu seviyesinde cevapla.

Kurallar:
- Hukuki değerlendirmeyi detaylı açıkla.
- İlgili kanun ve madde numaralarını belirt.
- Varsa şartları, istisnaları ve farklı durumları açıkla.
- Teknik ve resmi hukuk dili kullan.
- Cevabı açık başlıklarla düzenle.
- Kaynaklarda bulunmayan bilgileri uydurma.

Soru:
{normalized_question}
"""

    else:

        generation_question = f"""
Aşağıdaki soruyu normal bir vatandaşın kolayca anlayacağı şekilde cevapla.

Kurallar:
- Kısa, açık ve sade Türkçe kullan.
- Gereksiz hukuk terimlerinden kaçın.
- Önce sorunun doğrudan cevabını ver.
- Mümkünse 3-5 kısa cümlede açıkla.
- Kanun ve madde detaylarını cevabın içine gereksiz yere doldurma.
- Kaynaklarda bulunmayan bilgileri uydurma.
- Kullanıcı kaynakları ayrı olarak görüntüleyebileceği için kaynak listesi yazma.

Soru:
{normalized_question}
"""

    answer = generate_answer(
        generation_question,
        documents,
        history=None,
        mode=mode,
    )

    sources = []
    scores = []

    for doc in documents:

        metadata = doc.get(
            "metadata",
            {},
        )

        score = doc.get(
            "score"
        )

        if isinstance(
            score,
            (int, float),
        ):
            scores.append(
                score
            )

        title = metadata.get(
            "law_name",
            metadata.get(
                "document_name",
            ),
        )

        law_number = metadata.get(
            "law_number"
        )

        article = metadata.get(
            "madde"
        )

        if article is not None:

            article = str(
                article
            )

            if not article.lower().startswith(
                "madde"
            ):
                article = (
                    f"Madde {article}"
                )

        content = (
            doc.get("text")
            or doc.get("page_content")
            or doc.get("content")
            or doc.get("document")
            or ""
        )

        sources.append({
            "source_type": "kanun",
            "title": title,
            "law_number": law_number,
            "article": article,
            "content": content,
        })

    confidence = (
        round(
            max(scores),
            3,
        )
        if scores
        else None
    )

    return {
        "query": normalized_question,
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
    }


def run_real_rag_stream(
    question: str,
    mode: str = "citizen",
    top_k: int = 5,
):

    normalized_question = (
        normalize_question(
            question
        )
    )

    documents = retrieve_documents(
        normalized_question,
        top_k=top_k,
    )

    sources = []

    for doc in documents:

        metadata = (
            doc.get(
                "metadata",
                {},
            )
            or {}
        )

        title = metadata.get(
            "law_name",
            metadata.get(
                "document_name",
            ),
        )

        law_number = metadata.get(
            "law_number"
        )

        article = metadata.get(
            "madde"
        )

        if article is not None:

            article = str(article)

            if not article.lower().startswith(
                "madde"
            ):
                article = (
                    f"Madde {article}"
                )

        content = (
            doc.get("text")
            or doc.get("page_content")
            or doc.get("content")
            or ""
        )

        sources.append({
            "source_type": "kanun",
            "title": title,
            "law_number": law_number,
            "article": article,
            "content": content,
        })

    if not documents:

        yield {
            "type": "token",
            "token":
                "Bu bilgi mevcut mevzuat kaynaklarında bulunamadı.",
        }

        yield {
            "type": "done",
            "sources": [],
        }

        return

    if mode == "expert":

        generation_question = f"""
Aşağıdaki soruyu uzman/hukukçu seviyesinde cevapla.

Kurallar:
- Hukuki değerlendirmeyi detaylı açıkla.
- İlgili kanun ve madde numaralarını belirt.
- Varsa şartları ve istisnaları açıkla.
- Teknik ve resmi hukuk dili kullan.
- Kaynaklarda bulunmayan bilgileri uydurma.

Soru:
{normalized_question}
"""

    else:

        generation_question = f"""
Aşağıdaki soruyu normal bir vatandaşın kolayca
anlayacağı şekilde cevapla.

Kurallar:
- Kısa ve sade Türkçe kullan.
- Doğrudan cevabı ilk cümlede ver.
- Mümkünse 3-5 kısa cümlede açıkla.
- Kaynaklarda bulunmayan bilgileri uydurma.

Soru:
{normalized_question}
"""

    for token in generate_answer_stream(
        generation_question,
        documents,
        history=None,
        mode=mode,
    ):

        yield {
            "type": "token",
            "token": token,
        }

    yield {
        "type": "done",
        "sources": sources,
    }
def run_document_rag_stream(
    question: str,
    mode: str = "citizen",
    top_k: int = 5,
):
    """
    Document RAG with true LLM streaming.

    Retrieval is executed once.
    Tokens are streamed while also being collected
    so the final rag_result can later be used by
    routing and validation.
    """

    normalized_question = normalize_question(
        question
    )

    # =============================================
    # RETRIEVAL — ONLY ONCE
    # =============================================

    documents = retrieve_documents(
        normalized_question,
        top_k=top_k,
    )

    sources, confidence = build_rag_sources(
        documents
    )

    # =============================================
    # NO DOCUMENTS FOUND
    # =============================================

    if not documents:

        message = (
            "Bu bilgi mevcut mevzuat "
            "kaynaklarında bulunamadı."
        )

        yield {
            "type": "token",
            "token": message,
        }

        yield {
            "type": "rag_complete",
            "rag_result": {
                "query": normalized_question,
                "answer": message,
                "sources": [],
                "confidence": None,
            },
        }

        return

    # =============================================
    # ANSWER STYLE
    # =============================================

    if mode == "expert":

        generation_question = f"""
Aşağıdaki belge bağlamına ilişkin soruyu
uzman/hukukçu seviyesinde cevapla.

Kurallar:
- Hukuki değerlendirmeyi detaylı açıkla.
- İlgili kanun ve madde numaralarını belirt.
- Şartları ve istisnaları açıkla.
- Teknik ve resmi hukuk dili kullan.
- Yalnızca verilen mevzuat kaynaklarına dayan.
- Kaynaklarda bulunmayan bilgileri uydurma.

Soru:
{normalized_question}
"""

    else:

        generation_question = f"""
Aşağıdaki belge bağlamına ilişkin soruyu
normal bir vatandaşın kolayca anlayacağı
şekilde cevapla.

Kurallar:
- Kısa ve sade Türkçe kullan.
- Doğrudan cevabı ilk cümlede ver.
- Mümkünse 3-5 kısa cümlede açıkla.
- Yalnızca verilen mevzuat kaynaklarına dayan.
- Kaynaklarda bulunmayan bilgileri uydurma.

Soru:
{normalized_question}
"""

    # =============================================
    # TRUE LLM STREAM
    # =============================================

    full_answer = ""

    for token in generate_answer_stream(
        generation_question,
        documents,
        history=None,
        mode=mode,
    ):

        full_answer += token

        yield {
            "type": "token",
            "token": token,
        }

    # =============================================
    # COMPLETE RAG RESULT
    # =============================================

    rag_result = {
        "query": normalized_question,
        "answer": full_answer,
        "sources": sources,
        "confidence": confidence,
    }

    yield {
        "type": "rag_complete",
        "rag_result": rag_result,
    }

# =====================================================
# EXPLICIT LEGAL REFERENCE EXTRACTION
# =====================================================

def extract_explicit_legal_references(
    text: str,
) -> list[str]:

    if not text:
        return []

    refs = []

    patterns = [
        r"(\d{4})\s+say[ıi]l[ıi].{0,40}?(\d{1,4})\s*(?:nci|ncı|inci|ıncı|uncu|üncü|madde|maddesi)",
        r"\b(CMK|TCK|VUK)\s*['’]?(?:nun|nın|nin|un|ün)?\s*(\d{1,4})",
    ]

    for pattern in patterns:

        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        for match in matches:

            ref = " ".join(
                str(value)
                for value in match
            )

            refs.append(
                ref
            )

    return list(
        dict.fromkeys(
            refs
        )
    )


# =====================================================
# RAG QUESTION BUILDER
# =====================================================

def build_rag_question(
    analysis_result: dict,
    user_question: str | None = None,
    raw_text: str | None = None,
) -> str:

    topic = analysis_result.get(
        "topic",
        "",
    )

    purpose = analysis_result.get(
        "purpose",
        "",
    )

    intent = analysis_result.get(
        "intent",
        "",
    )

    summary = analysis_result.get(
        "summary",
        "",
    )

    document_context = " ".join(
        part
        for part in [
            str(topic),
            str(purpose),
            str(intent),
            str(summary),
        ]
        if part
    )

    legal_refs = extract_explicit_legal_references(
        raw_text or ""
    )

    legal_context = ""

    if legal_refs:

        legal_context = (
            " Belgede açıkça geçen mevzuat: "
            + ", ".join(
                legal_refs
            )
            + "."
        )

    if user_question:

        return (
            f"Belge bağlamı: {document_context}."
            f"{legal_context} "
            f"Kullanıcı sorusu: {user_question}"
        )

    return (
        f"{document_context}."
        f"{legal_context}"
    )


# =====================================================
# MAIN WORKFLOW
# =====================================================

def prepare_document_for_rag(
    text=None,
    file=None,
):
    """
    Runs document processing only until RAG.

    Steps:
    OCR
    Classification
    Evrak Analysis
    RAG question building

    Does NOT run:
    RAG generation
    Routing
    Validation
    """

    file_path = Path(
        str(file)
    )

    # =================================================
    # 1. OCR
    # =================================================

    ocr_start = time.perf_counter()

    print(
        f"[STREAM] OCR processing "
        f"'{file_path.name}'..."
    )

    ocr_result = (
        ocr_pipeline.process_file(
            str(file_path),
            doc_id="doc_001",
        )
    )

    ocr_time = (
        time.perf_counter()
        - ocr_start
    )

    print(
        f"[TIMING][STREAM] OCR: "
        f"{ocr_time:.2f} sec"
    )

    if hasattr(
        ocr_result,
        "model_dump",
    ):
        ocr_result_dict = (
            ocr_result.model_dump()
        )
    else:
        ocr_result_dict = (
            ocr_result
        )

    document_info = (
        ocr_result_dict.get(
            "document_info",
            {},
        )
    )

    ocr_input = (
        ocr_result_dict.get(
            "input",
            {},
        )
    )

    raw_text = (
        ocr_input.get(
            "clean_text",
            "",
        )
    )

    # =================================================
    # 2. CLASSIFICATION
    # =================================================

    classification_start = (
        time.perf_counter()
    )

    print(
        "[STREAM] Classification..."
    )

    if (
        raw_text
        and raw_text.strip()
    ):

        classification_raw = (
            classifier.predict(
                raw_text
            )
        )

        classification_result = {

            "label": (
                classification_raw.get(
                    "final_label"
                )
                or classification_raw.get(
                    "label"
                )
                or classification_raw.get(
                    "bert_raw_label"
                )
                or "unknown"
            ),

            "confidence": float(
                classification_raw.get(
                    "confidence",
                    0.0,
                )
                or 0.0
            ),

            "bert_raw_label": (
                classification_raw.get(
                    "bert_raw_label"
                )
            ),

            "decision_reason": (
                classification_raw.get(
                    "decision_reason"
                )
            ),

            "matched_rules": (
                classification_raw.get(
                    "matched_rules",
                    [],
                )
            ),

            "top_probabilities": (
                classification_raw.get(
                    "top_probabilities",
                    classification_raw.get(
                        "top_probs",
                        {},
                    ),
                )
            ),
        }

    else:

        classification_result = {

            "label": "unknown",

            "confidence": 0.0,

            "bert_raw_label": None,

            "decision_reason": (
                "OCR metni boş olduğu için "
                "sınıflandırma yapılamadı."
            ),

            "matched_rules": [],

            "top_probabilities": {},
        }

    classification_time = (
        time.perf_counter()
        - classification_start
    )

    print(
        f"[TIMING][STREAM] Classification: "
        f"{classification_time:.2f} sec"
    )

    # =================================================
    # 3. EVRAK ANALYSIS
    # =================================================

    evrak_start = (
        time.perf_counter()
    )

    print(
        "[STREAM] Evrak Analysis..."
    )

    page_count = (
        document_info.get(
            "page_count",
            1,
        )
    )

    evrak_result = (
        evrak_service.process_document(

            document_info_dict={

                "document_id": (
                    document_info.get(
                        "document_id"
                    )
                    or "doc_001"
                ),

                "file_name": (
                    document_info.get(
                        "file_name"
                    )
                    or file_path.name
                ),

                "file_type": (
                    document_info.get(
                        "file_type"
                    )
                    or file_path.suffix
                    .replace(".", "")
                    .lower()
                    or "pdf"
                ),

                "page_count":
                    page_count,

                "language": (
                    document_info.get(
                        "language"
                    )
                    or "tr"
                ),
            },

            ocr_dict={

                "text":
                    raw_text,

                "pages": list(
                    range(
                        1,
                        page_count + 1,
                    )
                ),

                "parsed_metadata": (
                    ocr_input.get(
                        "metadata",
                        {},
                    )
                ),

                "tables": (
                    ocr_input.get(
                        "tables",
                        [],
                    )
                ),

                "vision": (
                    ocr_input.get(
                        "vision",
                        {},
                    )
                ),
            },

            classification_result=(
                classification_result
            ),
        )
    )

    evrak_time = (
        time.perf_counter()
        - evrak_start
    )

    print(
        f"[TIMING][STREAM] Evrak Analysis: "
        f"{evrak_time:.2f} sec"
    )

    if hasattr(
        evrak_result,
        "model_dump",
    ):
        evrak_result_dict = (
            evrak_result.model_dump()
        )
    else:
        evrak_result_dict = (
            evrak_result
        )

    analysis_result = (
        evrak_result_dict[
            "evrak_analysis"
        ]
    )

    # =================================================
    # 4. BUILD RAG QUESTION
    # =================================================

    route = detect_route(
        text=text,
        file=file,
    )

    rag_question = (
        build_rag_question(

            analysis_result=(
                analysis_result
            ),

            user_question=(
                text
                if route ==
                "document_question"
                else None
            ),

            raw_text=(
                raw_text
            ),
        )
    )

    # =================================================
    # RETURN PREPARED CONTEXT
    # =================================================

    return {

        "route":
            route,

        "file_path":
            file_path,

        "document_info":
            document_info,

        "ocr_input":
            ocr_input,

        "raw_text":
            raw_text,

        "page_count":
            page_count,

        "classification":
            classification_result,

        "evrak_result":
            evrak_result_dict,

        "analysis":
            analysis_result,

        "rag_question":
            rag_question,

        "timing": {

            "ocr":
                round(
                    ocr_time,
                    2,
                ),

            "classification":
                round(
                    classification_time,
                    2,
                ),

            "evrak_analysis":
                round(
                    evrak_time,
                    2,
                ),
        },
    }
def process_input_stream(
    text=None,
    file=None,
    mode="citizen",
):
    """
    True streaming workflow.

    Question only:
        Normal RAG streaming.

    Document / Document + Question:
        OCR
        Classification
        Evrak Analysis
        RAG Retrieval
        True LLM Streaming
        Routing
        Validation
    """

    total_start = time.perf_counter()

    route = detect_route(
        text=text,
        file=file,
    )

    # =================================================
    # INVALID
    # =================================================

    if route == "invalid":

        yield {
            "type": "error",
            "detail": "Geçerli bir giriş bulunamadı.",
        }

        return

    # =================================================
    # QUESTION ONLY
    # =================================================

    if route == "question":

        yield {
            "type": "status",
            "stage": "rag",
            "text": "Mevzuat kaynakları aranıyor...",
        }

        for event in run_real_rag_stream(
            question=text,
            mode=mode,
            top_k=5,
        ):
            yield event

        return

    # =================================================
    # DOCUMENT / DOCUMENT + QUESTION
    # =================================================

    if route not in (
        "document",
        "document_question",
    ):

        yield {
            "type": "error",
            "detail": "Desteklenmeyen giriş türü.",
        }

        return

    try:

        # =================================================
        # PREPARE DOCUMENT
        # OCR + CLASSIFICATION + EVRAK ANALYSIS
        # =================================================

        yield {
            "type": "status",
            "stage": "ocr",
            "text": "Belge okunuyor...",
        }

        prepare_start = time.perf_counter()

        prepared = prepare_document_for_rag(
            text=text,
            file=file,
        )

        prepare_time = (
            time.perf_counter()
            - prepare_start
        )

        analysis_result = (
            prepared["analysis"]
        )

        classification_result = (
            prepared["classification"]
        )

        evrak_result_dict = (
            prepared["evrak_result"]
        )

        document_info = (
            prepared["document_info"]
        )

        ocr_input = (
            prepared["ocr_input"]
        )

        raw_text = (
            prepared["raw_text"]
        )

        page_count = (
            prepared["page_count"]
        )

        rag_question = (
            prepared["rag_question"]
        )

        # =================================================
        # TRUE RAG STREAM
        # =================================================

        yield {
            "type": "status",
            "stage": "rag",
            "text": "Mevzuat kaynakları aranıyor...",
        }

        rag_start = time.perf_counter()

        rag_result = None

        for event in run_document_rag_stream(
            question=rag_question,
            mode=mode,
            top_k=5,
        ):

            # TOKEN -> frontend'e hemen gönder
            if (
                isinstance(event, dict)
                and event.get("type") == "token"
            ):

                yield event
                continue

            # RAG tamamlandı
            if (
                isinstance(event, dict)
                and event.get("type") == "rag_complete"
            ):

                rag_result = event.get(
                    "rag_result"
                )

        rag_time = (
            time.perf_counter()
            - rag_start
        )

        # Güvenlik fallback'i
        if not rag_result:

            rag_result = {
                "query": rag_question,
                "answer": "",
                "sources": [],
                "confidence": None,
            }

        print(
            f"[TIMING][STREAM] RAG: "
            f"{rag_time:.2f} sec"
        )

        # =================================================
        # ROUTING
        # =================================================

        yield {
            "type": "status",
            "stage": "routing",
            "text": "İlgili birim belirleniyor...",
        }

        routing_start = (
            time.perf_counter()
        )

        routing_result = route_unit(
            evrak_analysis=analysis_result,
            rag_result=rag_result,
        )

        routing_time = (
            time.perf_counter()
            - routing_start
        )

        if hasattr(
            routing_result,
            "model_dump",
        ):

            routing_result_dict = (
                routing_result.model_dump()
            )

        else:

            routing_result_dict = (
                routing_result
            )

        print(
            f"[TIMING][STREAM] Routing: "
            f"{routing_time:.2f} sec"
        )

        # =================================================
        # BUILD FINAL JSON
        # =================================================

        final_json = {

            "success": True,

            "document_info": (
                evrak_result_dict.get(
                    "document_info",
                    document_info,
                )
            ),

            "ocr": (
                evrak_result_dict.get(
                    "ocr",
                    {
                        "text": raw_text,

                        "pages": list(
                            range(
                                1,
                                page_count + 1,
                            )
                        ),

                        "parsed_metadata": (
                            ocr_input.get(
                                "metadata",
                                {},
                            )
                        ),

                        "tables": (
                            ocr_input.get(
                                "tables",
                                [],
                            )
                        ),

                        "vision": (
                            ocr_input.get(
                                "vision",
                                {},
                            )
                        ),
                    },
                )
            ),

            "classification": (
                classification_result
            ),

            "evrak_analysis": (
                analysis_result
            ),

            "rag": (
                rag_result
            ),

            "routing": (
                routing_result_dict
            ),

            "official_writing": None,

            "validation": {
                "status": "pending",
                "issues": [],
                "confidence": None,
            },
        }

        # =================================================
        # VALIDATION
        # =================================================

        yield {
            "type": "status",
            "stage": "validation",
            "text": "Son kontroller yapılıyor...",
        }

        validation_start = (
            time.perf_counter()
        )

        validation_result = (
            validation_service.validate_document(
                final_json
            )
        )

        validation_time = (
            time.perf_counter()
            - validation_start
        )

        if hasattr(
            validation_result,
            "model_dump",
        ):

            validation_result_dict = (
                validation_result.model_dump()
            )

        else:

            validation_result_dict = (
                validation_result
            )

        final_json["validation"] = (
            validation_result_dict
        )

        print(
            f"[TIMING][STREAM] Validation: "
            f"{validation_time:.2f} sec"
        )

        # =================================================
        # TIMING
        # =================================================

        total_time = (
            time.perf_counter()
            - total_start
        )

        prepared_timing = (
            prepared.get(
                "timing",
                {},
            )
        )

        final_json["timing"] = {

            "ocr": (
                prepared_timing.get(
                    "ocr"
                )
            ),

            "classification": (
                prepared_timing.get(
                    "classification"
                )
            ),

            "evrak_analysis": (
                prepared_timing.get(
                    "evrak_analysis"
                )
            ),

            "prepare": round(
                prepare_time,
                2,
            ),

            "rag": round(
                rag_time,
                2,
            ),

            "routing": round(
                routing_time,
                2,
            ),

            "validation": round(
                validation_time,
                2,
            ),

            "total": round(
                total_time,
                2,
            ),
        }

        print("\n==============================")
        print("STREAM PIPELINE COMPLETED")
        print(
            f"Prepare: {prepare_time:.2f} sec"
        )
        print(
            f"RAG: {rag_time:.2f} sec"
        )
        print(
            f"Routing: {routing_time:.2f} sec"
        )
        print(
            f"Validation: {validation_time:.2f} sec"
        )
        print(
            f"TOTAL: {total_time:.2f} sec"
        )
        print("==============================\n")

        # =================================================
        # DONE
        # =================================================

        yield {
            "type": "done",

            "sources": (
                rag_result.get(
                    "sources",
                    [],
                )
            ),

            "result": final_json,
        }

    except Exception as error:

        print(
            "[STREAM ERROR]",
            repr(error),
        )

        yield {
            "type": "error",
            "detail": str(error),
        }

def process_input(
    text=None,
    file=None,
    mode="citizen",
):

    total_start = time.perf_counter()
    print(f"\n[ORCHESTRATOR] START -> text: '{text}', file: '{file}', mode: '{mode}'")

    # -------------------------------------------------
    # ROUTER
    # -------------------------------------------------

    route = detect_route(
        text=text,
        file=file,
    )
    print(f"[ORCHESTRATOR] Detected Route: {route}")

    if route == "invalid":

        total_time = (
            time.perf_counter()
            - total_start
        )

        return {
            "status": "error",
            "message": "Geçerli bir giriş bulunamadı.",
            "timing": {
                "total": round(
                    total_time,
                    2,
                )
            },
        }

    # -------------------------------------------------
    # STATE
    # -------------------------------------------------

    state = create_state(
        input_type=route,

        document_id=(
            "doc_001"
            if file
            else None
        ),

        user_question=text,
        file_path=file,
    )

    # =================================================
    # CASE 1 — QUESTION ONLY
    # =================================================

    if route == "question":

        state.current_step = (
            "mevzuat_rag"
        )

        rag_start = time.perf_counter()
        print("[ORCHESTRATOR] Step: Running Mevzuat RAG for Question...")

        rag_result = run_real_rag(
            question=text,
            top_k=5,
            mode=mode,
        )

        rag_time = (
            time.perf_counter()
            - rag_start
        )

        print(
            f"[TIMING] RAG: "
            f"{rag_time:.2f} sec"
        )

        state.rag_result = (
            rag_result
        )

        state.status = "completed"
        state.current_step = "completed"

        total_time = (
            time.perf_counter()
            - total_start
        )

        print(
            f"[TIMING] TOTAL: "
            f"{total_time:.2f} sec"
        )

        return {
            "status": state.status,
            "route": route,
            "rag": rag_result,

            "timing": {
                "rag": round(
                    rag_time,
                    2,
                ),
                "total": round(
                    total_time,
                    2,
                ),
            },
        }

    # =================================================
    # CASE 2 / 3 — DOCUMENT
    # =================================================

    file_path = Path(
        str(file)
    )

    # =================================================
    # 1. REAL OCR
    # =================================================

    state.current_step = "ocr"

    ocr_start = time.perf_counter()
    print(f"[ORCHESTRATOR] Step: OCR processing '{file_path.name}'...")

    ocr_result = (
        ocr_pipeline.process_file(
            str(file_path),

            doc_id=(
                state.document_id
                or "doc_001"
            ),
        )
    )

    ocr_time = (
        time.perf_counter()
        - ocr_start
    )

    print(
        f"[TIMING] OCR: "
        f"{ocr_time:.2f} sec"
    )

    if hasattr(
        ocr_result,
        "model_dump",
    ):

        ocr_result_dict = (
            ocr_result.model_dump()
        )

    else:

        ocr_result_dict = (
            ocr_result
        )

    document_info = (
        ocr_result_dict.get(
            "document_info",
            {},
        )
    )

    ocr_input = (
        ocr_result_dict.get(
            "input",
            {},
        )
    )

    state.raw_text = (
        ocr_input.get(
            "clean_text",
            "",
        )
    )

    # =================================================
    # 2. REAL CLASSIFICATION
    # =================================================

    state.current_step = (
        "classification"
    )

    classification_start = (
        time.perf_counter()
    )
    print("[ORCHESTRATOR] Step: Classification...")

    if (
        state.raw_text
        and state.raw_text.strip()
    ):

        classification_raw = (
            classifier.predict(
                state.raw_text
            )
        )

        classification_result = {

            "label": (
                classification_raw.get(
                    "final_label"
                )
                or classification_raw.get(
                    "label"
                )
                or classification_raw.get(
                    "bert_raw_label"
                )
                or "unknown"
            ),

            "confidence": float(
                classification_raw.get(
                    "confidence",
                    0.0,
                )
                or 0.0
            ),

            "bert_raw_label": (
                classification_raw.get(
                    "bert_raw_label"
                )
            ),

            "decision_reason": (
                classification_raw.get(
                    "decision_reason"
                )
            ),

            "matched_rules": (
                classification_raw.get(
                    "matched_rules",
                    [],
                )
            ),

            "top_probabilities": (
                classification_raw.get(
                    "top_probabilities",
                    classification_raw.get(
                        "top_probs",
                        {},
                    ),
                )
            ),
        }

    else:

        classification_result = {

            "label": "unknown",

            "confidence": 0.0,

            "bert_raw_label": None,

            "decision_reason": (
                "OCR metni boş olduğu için "
                "sınıflandırma yapılamadı."
            ),

            "matched_rules": [],

            "top_probabilities": {},
        }

    classification_time = (
        time.perf_counter()
        - classification_start
    )

    print(
        f"[TIMING] Classification: "
        f"{classification_time:.2f} sec"
    )

    # =================================================
    # 3. REAL EVRAK ANALIZ
    # =================================================

    state.current_step = (
        "evrak_analiz"
    )

    evrak_start = time.perf_counter()
    print("[ORCHESTRATOR] Step: Evrak Analysis LLM...")

    page_count = (
        document_info.get(
            "page_count",
            1,
        )
    )

    evrak_result = (
        evrak_service.process_document(

            document_info_dict={

                "document_id": (
                    document_info.get(
                        "document_id"
                    )
                    or state.document_id
                    or "doc_001"
                ),

                "file_name": (
                    document_info.get(
                        "file_name"
                    )
                    or file_path.name
                ),

                "file_type": (
                    document_info.get(
                        "file_type"
                    )
                    or file_path.suffix
                    .replace(
                        ".",
                        "",
                    )
                    .lower()
                    or "pdf"
                ),

                "page_count": (
                    page_count
                ),

                "language": (
                    document_info.get(
                        "language"
                    )
                    or "tr"
                ),
            },

            ocr_dict={

                "text": (
                    state.raw_text
                ),

                "pages": list(
                    range(
                        1,
                        page_count + 1,
                    )
                ),

                "parsed_metadata": (
                    ocr_input.get(
                        "metadata",
                        {},
                    )
                ),

                "tables": (
                    ocr_input.get(
                        "tables",
                        [],
                    )
                ),

                "vision": (
                    ocr_input.get(
                        "vision",
                        {},
                    )
                ),
            },

            classification_result=(
                classification_result
            ),
        )
    )

    evrak_time = (
        time.perf_counter()
        - evrak_start
    )

    print(
        f"[TIMING] Evrak Analysis: "
        f"{evrak_time:.2f} sec"
    )

    if hasattr(
        evrak_result,
        "model_dump",
    ):

        evrak_result_dict = (
            evrak_result.model_dump()
        )

    else:

        evrak_result_dict = (
            evrak_result
        )

    analysis_result = (
        evrak_result_dict[
            "evrak_analysis"
        ]
    )

    state.analysis = (
        analysis_result
    )

    # =================================================
    # MISSING INFORMATION
    # =================================================

    missing_info = (
        analysis_result.get(
            "missing_information",
            [],
        )
    )

    state.missing_information = (
        missing_info
    )

    # =================================================
    # 4. REAL MEVZUAT RAG
    # =================================================

    state.current_step = (
        "mevzuat_rag"
    )

    rag_start = time.perf_counter()
    print("[ORCHESTRATOR] Step: Mevzuat RAG...")

    rag_question = (
        build_rag_question(

            analysis_result=(
                analysis_result
            ),

            user_question=(
                text
                if route == "document_question"
                else None
            ),

            raw_text=(
                state.raw_text
            ),
        )
    )

    rag_result = run_real_rag(
        question=rag_question,
        top_k=5,
        mode=mode,
    )

    rag_time = (
        time.perf_counter()
        - rag_start
    )

    print(
        f"[TIMING] RAG: "
        f"{rag_time:.2f} sec"
    )

    state.rag_result = (
        rag_result
    )

    # =================================================
    # 5. REAL BIRIM YONLENDIRME
    # =================================================

    state.current_step = (
        "birim_yonlendirme"
    )

    routing_start = (
        time.perf_counter()
    )
    print("[ORCHESTRATOR] Step: Unit Routing...")

    routing_result = route_unit(

        evrak_analysis=(
            analysis_result
        ),

        rag_result=(
            rag_result
        ),
    )

    routing_time = (
        time.perf_counter()
        - routing_start
    )

    print(
        f"[TIMING] Routing: "
        f"{routing_time:.2f} sec"
    )

    if hasattr(
        routing_result,
        "model_dump",
    ):

        routing_result_dict = (
            routing_result.model_dump()
        )

    else:

        routing_result_dict = (
            routing_result
        )

    state.routing_result = (
        routing_result_dict
    )

    state.official_letter = None

    # =================================================
    # FINAL JSON — VALIDATION ÖNCESİ
    # =================================================

    final_json = {

        "success": True,

        "document_info": (
            evrak_result_dict.get(
                "document_info",
                document_info,
            )
        ),

        "ocr": (
            evrak_result_dict.get(

                "ocr",

                {
                    "text": (
                        state.raw_text
                    ),

                    "pages": list(
                        range(
                            1,
                            page_count + 1,
                        )
                    ),

                    "parsed_metadata": (
                        ocr_input.get(
                            "metadata",
                            {},
                        )
                    ),

                    "tables": (
                        ocr_input.get(
                            "tables",
                            [],
                        )
                    ),

                    "vision": (
                        ocr_input.get(
                            "vision",
                            {},
                        )
                    ),
                },
            )
        ),

        "classification": (
            classification_result
        ),

        "evrak_analysis": (
            state.analysis
        ),

        "rag": (
            state.rag_result
        ),

        "routing": (
            state.routing_result
        ),

        "official_writing": None,

        "validation": {
            "status": "pending",
            "issues": [],
            "confidence": None,
        },
    }

    # =================================================
    # 7. REAL DOGRULAMA
    # =================================================

    state.current_step = (
        "dogrulama"
    )

    validation_start = (
        time.perf_counter()
    )
    print("[ORCHESTRATOR] Step: Validation...")

    validation_result = (
        validation_service.validate_document(
            final_json
        )
    )

    validation_time = (
        time.perf_counter()
        - validation_start
    )

    print(
        f"[TIMING] Validation: "
        f"{validation_time:.2f} sec"
    )

    if hasattr(
        validation_result,
        "model_dump",
    ):

        validation_result_dict = (
            validation_result.model_dump()
        )

    else:

        validation_result_dict = (
            validation_result
        )

    final_json["validation"] = (
        validation_result_dict
    )

    # =================================================
    # COMPLETE + TOTAL TIMING
    # =================================================

    state.current_step = "completed"
    state.status = "completed"

    total_time = (
        time.perf_counter()
        - total_start
    )

    print("\n==============================")
    print(f"[TIMING] OCR: {ocr_time:.2f} sec")
    print(f"[TIMING] Classification: {classification_time:.2f} sec")
    print(f"[TIMING] Evrak Analysis: {evrak_time:.2f} sec")
    print(f"[TIMING] RAG: {rag_time:.2f} sec")
    print(f"[TIMING] Routing: {routing_time:.2f} sec")
    print(f"[TIMING] Validation: {validation_time:.2f} sec")
    print(f"[TIMING] TOTAL: {total_time:.2f} sec")
    print("==============================\n")

    final_json["timing"] = {
        "ocr": round(ocr_time, 2),
        "classification": round(classification_time, 2),
        "evrak_analysis": round(evrak_time, 2),
        "rag": round(rag_time, 2),
        "routing": round(routing_time, 2),
        "validation": round(validation_time, 2),
        "total": round(total_time, 2),
    }

    return final_json


# =====================================================
# TESTS
# =====================================================

if __name__ == "__main__":

    print("\n===== TEST 1: QUESTION =====")
    result1 = process_input(text="Hırsızlık suçunun cezası nedir?")
    print(result1)