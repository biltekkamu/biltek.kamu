import os
import re
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from langchain_ollama import ChatOllama

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

from orkestrasyon.mock_agents import (
    mock_resmi_yazi,
)


# =====================================================
# PROJECT PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[1]


# =====================================================
# DOGRULAMA AGENT IMPORT
# =====================================================

validation_agent_dir = BASE_DIR / "agents" / "dogrulama_agent"

if str(validation_agent_dir) not in sys.path:
    sys.path.insert(0, str(validation_agent_dir))

from validator_service import DocumentValidationService


# =====================================================
# REAL OCR SERVICE
# =====================================================

ocr_pipeline = MultiPageOCRPipeline(lang="tr")


# =====================================================
# SHARED QWEN LLM (OLLAMA)
# =====================================================

evrak_llm = ChatOllama(
    model="qwen2.5:7b",
    temperature=0.0,
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
        BASE_DIR / "agents" / "classification_agent" / "berturk_classifier_v1"
    ),
    eval_dir=str(
        BASE_DIR / "agents" / "classification_agent" / "evaluation"
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

def run_real_rag(question: str, top_k: int = 5) -> dict:
    normalized_question = normalize_question(question)
    documents = retrieve_documents(normalized_question, top_k=top_k)

    if not documents:
        return {
            "query": normalized_question,
            "answer": None,
            "sources": [],
            "confidence": None,
        }

    answer = generate_answer(normalized_question, documents, history=None)
    sources = []
    scores = []

    for doc in documents:
        metadata = doc.get("metadata", {})
        score = doc.get("score")

        if isinstance(score, (int, float)):
            scores.append(score)

        title = metadata.get("law_name", metadata.get("document_name"))
        law_number = metadata.get("law_number")
        article = metadata.get("madde")

        if article is not None:
            article = str(article)
            if not article.lower().startswith("madde"):
                article = f"Madde {article}"

        sources.append({
            "source_type": "kanun",
            "title": title,
            "law_number": law_number,
            "article": article,
        })

    confidence = round(max(scores), 3) if scores else None

    return {
        "query": normalized_question,
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
    }


# =====================================================
# EXPLICIT LEGAL REFERENCE EXTRACTION
# =====================================================

def extract_explicit_legal_references(text: str) -> list[str]:
    if not text:
        return []

    refs = []
    patterns = [
        r"(\d{4})\s+say[ıi]l[ıi].{0,40}?(\d{1,4})\s*(?:nci|ncı|inci|ıncı|uncu|üncü|madde|maddesi)",
        r"\b(CMK|TCK|VUK)\s*['’]?(?:nun|nın|nin|un|ün)?\s*(\d{1,4})",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        for match in matches:
            ref = " ".join(str(value) for value in match)
            refs.append(ref)

    return list(dict.fromkeys(refs))


# =====================================================
# RAG QUESTION BUILDER
# =====================================================

def build_rag_question(
    analysis_result: dict,
    user_question: str | None = None,
    raw_text: str | None = None,
) -> str:
    topic = analysis_result.get("topic", "")
    purpose = analysis_result.get("purpose", "")
    intent = analysis_result.get("intent", "")
    summary = analysis_result.get("summary", "")

    document_context = " ".join(
        part for part in [str(topic), str(purpose), str(intent), str(summary)] if part
    )

    legal_refs = extract_explicit_legal_references(raw_text or "")
    legal_context = ""

    if legal_refs:
        legal_context = f" Belgede açıkça geçen mevzuat: {', '.join(legal_refs)}."

    if user_question:
        return f"Belge bağlamı: {document_context}.{legal_context} Kullanıcı sorusu: {user_question}"

    return f"{document_context}.{legal_context}"


# =====================================================
# MAIN WORKFLOW
# =====================================================

def process_input(text=None, file=None):
    total_start = time.perf_counter()

    route = detect_route(text=text, file=file)

    if route == "invalid":
        total_time = time.perf_counter() - total_start
        return {
            "status": "error",
            "message": "Geçerli bir giriş bulunamadı.",
            "timing": {"total": round(total_time, 2)},
        }

    state = create_state(
        input_type=route,
        document_id="doc_001" if file else None,
        user_question=text,
        file_path=file,
    )

    # -------------------------------------------------
    # CASE 1 — QUESTION ONLY
    # -------------------------------------------------
    if route == "question":
        state.current_step = "mevzuat_rag"
        rag_start = time.perf_counter()
        rag_result = run_real_rag(question=text, top_k=2)
        rag_time = time.perf_counter() - rag_start

        state.rag_result = rag_result
        state.status = "completed"
        state.current_step = "completed"

        total_time = time.perf_counter() - total_start
        return {
            "status": state.status,
            "route": route,
            "rag": rag_result,
            "timing": {
                "rag": round(rag_time, 2),
                "total": round(total_time, 2),
            },
        }

    # -------------------------------------------------
    # CASE 2 / 3 — DOCUMENT
    # -------------------------------------------------
    file_path = Path(str(file))

    # 1. REAL OCR
    state.current_step = "ocr"
    ocr_start = time.perf_counter()
    ocr_result = ocr_pipeline.process_file(
        str(file_path),
        doc_id=(state.document_id or "doc_001"),
    )
    ocr_time = time.perf_counter() - ocr_start

    if hasattr(ocr_result, "model_dump"):
        ocr_result_dict = ocr_result.model_dump()
    else:
        ocr_result_dict = ocr_result

    document_info = ocr_result_dict.get("document_info", {})
    ocr_input = ocr_result_dict.get("input", {})
    state.raw_text = ocr_input.get("clean_text", "")

    # 2. REAL CLASSIFICATION
    state.current_step = "classification"
    classification_start = time.perf_counter()

    if state.raw_text and state.raw_text.strip():
        classification_raw = classifier.predict(state.raw_text)
        classification_result = {
            "label": (
                classification_raw.get("final_label")
                or classification_raw.get("label")
                or classification_raw.get("bert_raw_label")
                or "unknown"
            ),
            "confidence": float(classification_raw.get("confidence", 0.0) or 0.0),
            "bert_raw_label": classification_raw.get("bert_raw_label"),
            "decision_reason": classification_raw.get("decision_reason"),
            "matched_rules": classification_raw.get("matched_rules", []),
            "top_probabilities": classification_raw.get(
                "top_probabilities",
                classification_raw.get("top_probs", {}),
            ),
        }
    else:
        classification_result = {
            "label": "unknown",
            "confidence": 0.0,
            "bert_raw_label": None,
            "decision_reason": "OCR metni boş olduğu için sınıflandırma yapılamadı.",
            "matched_rules": [],
            "top_probabilities": {},
        }

    classification_time = time.perf_counter() - classification_start

    # 3. REAL EVRAK ANALIZ
    state.current_step = "evrak_analiz"
    evrak_start = time.perf_counter()
    page_count = document_info.get("page_count", 1)

    evrak_result = evrak_service.process_document(
        document_info_dict={
            "document_id": document_info.get("document_id") or state.document_id or "doc_001",
            "file_name": document_info.get("file_name") or file_path.name,
            "file_type": document_info.get("file_type") or file_path.suffix.replace(".", "").lower() or "pdf",
            "page_count": page_count,
            "language": document_info.get("language") or "tr",
        },
        ocr_dict={
            "text": state.raw_text,
            "pages": list(range(1, page_count + 1)),
            "parsed_metadata": ocr_input.get("metadata", {}),
            "tables": ocr_input.get("tables", []),
            "vision": ocr_input.get("vision", {}),
        },
        classification_result=classification_result,
    )
    evrak_time = time.perf_counter() - evrak_start

    if hasattr(evrak_result, "model_dump"):
        evrak_result_dict = evrak_result.model_dump()
    else:
        evrak_result_dict = evrak_result

    analysis_result = evrak_result_dict["evrak_analysis"]
    state.analysis = analysis_result
    state.missing_information = analysis_result.get("missing_information", [])

    # 4. REAL MEVZUAT RAG
    state.current_step = "mevzuat_rag"
    rag_start = time.perf_counter()
    rag_question = build_rag_question(
        analysis_result=analysis_result,
        user_question=(text if route == "document_question" else None),
        raw_text=state.raw_text,
    )
    rag_result = run_real_rag(question=rag_question, top_k=2)
    rag_time = time.perf_counter() - rag_start
    state.rag_result = rag_result

    # 5. REAL BIRIM YONLENDIRME
    state.current_step = "birim_yonlendirme"
    routing_start = time.perf_counter()
    routing_result = route_unit(
        evrak_analysis=analysis_result,
        rag_result=rag_result,
    )
    routing_time = time.perf_counter() - routing_start

    if hasattr(routing_result, "model_dump"):
        routing_result_dict = routing_result.model_dump()
    else:
        routing_result_dict = routing_result
    state.routing_result = routing_result_dict

    # 6. RESMI YAZI (MOCK)
    state.current_step = "resmi_yazi"
    resmi_start = time.perf_counter()
    resmi_yazi_result = mock_resmi_yazi(analysis_result, rag_result)
    resmi_time = time.perf_counter() - resmi_start
    state.official_letter = resmi_yazi_result

    # 7. REAL DOGRULAMA
    final_json = {
        "success": True,
        "document_info": evrak_result_dict.get("document_info", document_info),
        "ocr": evrak_result_dict.get(
            "ocr",
            {
                "text": state.raw_text,
                "pages": list(range(1, page_count + 1)),
                "parsed_metadata": ocr_input.get("metadata", {}),
                "tables": ocr_input.get("tables", []),
                "vision": ocr_input.get("vision", {}),
            },
        ),
        "classification": classification_result,
        "evrak_analysis": state.analysis,
        "rag": state.rag_result,
        "routing": state.routing_result,
        "official_writing": state.official_letter,
        "validation": {
            "status": "pending",
            "issues": [],
            "confidence": None,
        },
    }

    state.current_step = "dogrulama"
    validation_start = time.perf_counter()
    validation_result = validation_service.validate_document(final_json)
    validation_time = time.perf_counter() - validation_start

    if hasattr(validation_result, "model_dump"):
        validation_result_dict = validation_result.model_dump()
    else:
        validation_result_dict = validation_result
    final_json["validation"] = validation_result_dict

    state.current_step = "completed"
    state.status = "completed"
    total_time = time.perf_counter() - total_start

    final_json["timing"] = {
        "ocr": round(ocr_time, 2),
        "classification": round(classification_time, 2),
        "evrak_analysis": round(evrak_time, 2),
        "rag": round(rag_time, 2),
        "routing": round(routing_time, 2),
        "official_writing": round(resmi_time, 2),
        "validation": round(validation_time, 2),
        "total": round(total_time, 2),
    }

    return final_json