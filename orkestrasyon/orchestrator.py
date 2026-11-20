import asyncio
import os
from pathlib import Path
import re
import sys
import threading
import time

import torch
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# =====================================================
# LIGHTWEIGHT NON-BLOCKING TELEMETRY HOOK (SSE)
# =====================================================

_event_subscribers: set[tuple[asyncio.AbstractEventLoop, asyncio.Queue]] = set()
_event_lock = threading.Lock()


def subscribe_events(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
    with _event_lock:
        _event_subscribers.add((loop, queue))


def unsubscribe_events(loop: asyncio.AbstractEventLoop, queue: asyncio.Queue) -> None:
    with _event_lock:
        _event_subscribers.discard((loop, queue))


def emit_event(agent: str, status: str, task: str = "") -> None:
    if not _event_subscribers:
        return
    payload = {
        "agent": agent,
        "status": status,
        "task": task,
    }
    with _event_lock:
        subscribers = list(_event_subscribers)
    for loop, queue in subscribers:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, payload)
        except Exception:
            pass

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")
if os.getenv("EVREN_API_KEY") in (None, "", "API_KEY"):
    load_dotenv(BASE_DIR / ".env", override=True)

from agents.ocr.main_pipeline import MultiPageOCRPipeline
from agents.evrak_analiz.service import EvrakAnalysisService
from agents.classification_agent.hybrid_classifier import (
    HybridDocumentClassifier,
)

from agents.mevzuat_rag.rag_service import (
    normalize_question,
    retrieve_documents,
    generate_answer,
)

from agents.birim_yonlendirme.agent import route_unit

from orkestrasyon.router import detect_route
from orkestrasyon.state import create_state


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
# SHARED QWEN LLM
# =====================================================

evrak_llm = ChatOpenAI(
    model=os.getenv("EVREN_MODEL", "qwen3.8-flash-next"),
    api_key=os.getenv("EVREN_API_KEY"),
    base_url=os.getenv("EVREN_BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1"),
    temperature=0.0,
    timeout=90.0,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
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

def process_input(
    text=None,
    file=None,
    mode="citizen",
):

    total_start = time.perf_counter()

    # -------------------------------------------------
    # ROUTER
    # -------------------------------------------------

    route = detect_route(
        text=text,
        file=file,
    )

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

        emit_event("orchestrator", "delegating", "Soru Mevzuat RAG ajanına yönlendiriliyor...")

        state.current_step = (
            "mevzuat_rag"
        )

        rag_start = time.perf_counter()

        emit_event("mevzuat_rag", "working", "Mevzuat taranıyor ve hukuki yanıt üretiliyor...")

        rag_result = run_real_rag(
    question=text,
    top_k=5,
        mode=mode,

        )

        emit_event("mevzuat_rag", "done", "Mevzuat yanıtı hazırlandı.")
        emit_event("orchestrator", "done", "Soru yanıtlama süreci tamamlandı.")

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

    emit_event("orchestrator", "delegating", "Belge OCR ajanına iletiliyor...")
    state.current_step = "ocr"

    ocr_start = time.perf_counter()
    emit_event("ocr", "working", "Belge metni ve görsel veriler çıkarılıyor...")

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
    emit_event("ocr", "done", f"OCR tamamlandı ({ocr_time:.1f} sn)")

    print(
        f"\n[TIMING] OCR: "
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

    emit_event("orchestrator", "delegating", "Belge Sınıflandırma ajanına yönlendiriliyor...")
    state.current_step = (
        "classification"
    )

    classification_start = (
        time.perf_counter()
    )
    emit_event("classification_agent", "working", "Belge türü BERTurk ile sınıflandırılıyor...")

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
    emit_event("classification_agent", "done", f"Tür: {classification_result.get('label')}")

    # =================================================
    # 3. REAL EVRAK ANALIZ
    # =================================================

    emit_event("orchestrator", "delegating", "Evrak Analiz ajanına yönlendiriliyor...")
    state.current_step = (
        "evrak_analiz"
    )

    evrak_start = time.perf_counter()
    emit_event("evrak_analiz", "working", "Evrak konusu, amacı ve varlıkları analiz ediliyor...")

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
    emit_event("evrak_analiz", "done", "Evrak analizi tamamlandı.")

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

    emit_event("orchestrator", "delegating", "Mevzuat RAG ajanına yönlendiriliyor...")
    state.current_step = (
        "mevzuat_rag"
    )

    rag_start = time.perf_counter()
    emit_event("mevzuat_rag", "working", "İlgili kanun ve maddeler taranıyor...")

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
    emit_event("mevzuat_rag", "done", "Mevzuat analizi tamamlandı.")

    state.rag_result = (
        rag_result
    )

    # =================================================
    # 5. REAL BIRIM YONLENDIRME
    # =================================================

    emit_event("orchestrator", "delegating", "Birim Yönlendirme ajanına iletiliyor...")
    state.current_step = (
        "birim_yonlendirme"
    )

    routing_start = (
        time.perf_counter()
    )
    emit_event("birim_yonlendirme", "working", "Yetkili kamu birimi belirleniyor...")

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
    emit_event("birim_yonlendirme", "done", f"Birim: {routing_result_dict.get('selected_department') or 'Belirlenemedi'}")


    # =================================================
    # 6. RESMI YAZI — ON DEMAND
    # =================================================

    # Resmi yazı artık ana workflow sırasında
    # otomatik oluşturulmaz.
    # Kullanıcı "Resmi Yazı Oluştur" butonuna
    # bastığında /official-writing endpoint'i çalışır.

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

    emit_event("orchestrator", "delegating", "Doğrulama ajanına iletiliyor...")
    state.current_step = (
        "dogrulama"
    )

    validation_start = (
        time.perf_counter()
    )
    emit_event("dogrulama_agent", "working", "Şema, kaynak ve anlamsal tutarlılık denetleniyor...")

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
    emit_event("dogrulama_agent", "done", f"Doğrulama: {validation_result_dict.get('status')}")
    emit_event("orchestrator", "done", "Belge analizi tamamlandı.")

    # =================================================
    # COMPLETE + TOTAL TIMING
    # =================================================

    state.current_step = "completed"
    state.status = "completed"

    total_time = (
        time.perf_counter()
        - total_start
    )

    print(
        "\n=============================="
    )

    print(
        f"[TIMING] OCR: "
        f"{ocr_time:.2f} sec"
    )

    print(
        f"[TIMING] Classification: "
        f"{classification_time:.2f} sec"
    )

    print(
        f"[TIMING] Evrak Analysis: "
        f"{evrak_time:.2f} sec"
    )
    emit_event("evrak_analiz", "done", "Evrak analizi tamamlandı.")

    print(
        f"[TIMING] RAG: "
        f"{rag_time:.2f} sec"
    )

    print(
        f"[TIMING] Routing: "
        f"{routing_time:.2f} sec"
    )



    print(
        f"[TIMING] Validation: "
        f"{validation_time:.2f} sec"
    )

    print(
        f"[TIMING] TOTAL: "
        f"{total_time:.2f} sec"
    )

    print(
        "==============================\n"
    )

    final_json["timing"] = {

        "ocr": round(
            ocr_time,
            2,
        ),

        "classification": round(
            classification_time,
            2,
        ),

        "evrak_analysis": round(
            evrak_time,
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

    return final_json


# =====================================================
# TESTS
# =====================================================

if __name__ == "__main__":

    print(
        "\n===== TEST 1: QUESTION ====="
    )

    result1 = process_input(
        text="Hırsızlık suçunun cezası nedir?"
    )

    print(
        result1
    )

    print(
        "\n===== TEST 2: DOCUMENT ====="
    )

    result2 = process_input(
        file="test.jpeg"
    )

    print(
        result2
    )

    print(
        "\n===== TEST 3: DOCUMENT + QUESTION ====="
    )

    result3 = process_input(
        text="Bu belgenin amacı nedir?",
        file="test.jpeg",
    )

    print(
        result3
    )

    print(
        "\n===== TEST 4: INVALID ====="
    )

    result4 = process_input()

    print(
        result4
    )