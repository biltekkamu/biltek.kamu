from pathlib import Path
import re

from langchain_ollama import ChatOllama

from agents.ocr.main_pipeline import MultiPageOCRPipeline
from agents.evrak_analiz.service import EvrakAnalysisService

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
# REAL OCR SERVICE
# =====================================================

ocr_pipeline = MultiPageOCRPipeline(
    lang="tr"
)


# =====================================================
# REAL EVRAK ANALIZ SERVICE
# =====================================================

evrak_llm = ChatOllama(
    model="qwen2.5:7b",
    temperature=0.0,
)

evrak_service = EvrakAnalysisService(
    llm_client=evrak_llm,
)


# =====================================================
# REAL RAG
# =====================================================

def run_real_rag(
    question: str,
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

    answer = generate_answer(
        normalized_question,
        documents,
        history=None,
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
            scores.append(score)

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

        sources.append({
            "source_type": "kanun",
            "title": title,
            "law_number": law_number,
            "article": article,
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
        # Örnek:
        # 5271 sayılı CMK'nın 147 nci maddesi
        r"(\d{4})\s+say[ıi]l[ıi].{0,40}?(\d{1,4})\s*(?:nci|ncı|inci|ıncı|uncu|üncü|madde|maddesi)",

        # Örnek:
        # CMK 147
        # TCK 188
        # VUK 242
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

    # Tekrarları kaldır
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

    # -------------------------------------------------
    # Belge içindeki açık mevzuat referanslarını çıkar
    # -------------------------------------------------

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

    # -------------------------------------------------
    # DOCUMENT + QUESTION
    # -------------------------------------------------

    if user_question:

        return (
            f"Belge bağlamı: {document_context}."
            f"{legal_context} "
            f"Kullanıcı sorusu: {user_question}"
        )

    # -------------------------------------------------
    # DOCUMENT ONLY
    # -------------------------------------------------

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
):

    # -------------------------------------------------
    # ROUTER
    # -------------------------------------------------

    route = detect_route(
        text=text,
        file=file,
    )

    if route == "invalid":
        return {
            "status": "error",
            "message": "Geçerli bir giriş bulunamadı.",
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
    # CASE 1: QUESTION ONLY
    # =================================================

    if route == "question":

        state.current_step = (
            "mevzuat_rag"
        )

        rag_result = run_real_rag(
            question=text,
            top_k=5,
        )

        state.rag_result = (
            rag_result
        )

        state.status = "completed"
        state.current_step = "completed"

        return {
            "status": state.status,
            "route": route,
            "rag": rag_result,
        }

    # =================================================
    # CASE 2 / 3: DOCUMENT
    # =================================================

    file_path = Path(
        str(file)
    )

    # -------------------------------------------------
    # REAL OCR
    # -------------------------------------------------

    state.current_step = "ocr"

    ocr_result = (
        ocr_pipeline.process_file(
            str(file_path),
            doc_id=(
                state.document_id
                or "doc_001"
            ),
        )
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

    # -------------------------------------------------
    # REAL EVRAK ANALIZ
    # -------------------------------------------------

    state.current_step = (
        "evrak_analiz"
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
                "text": state.raw_text,

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

            classification_result=None,
        )
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

    # -------------------------------------------------
    # MISSING INFORMATION
    # -------------------------------------------------

    missing_info = (
        analysis_result.get(
            "missing_information",
            [],
        )
    )

    state.missing_information = (
        missing_info
    )

    # Test sırasında pipeline devam ediyor.
    # Missing information varsa burada kesmiyoruz.

    # -------------------------------------------------
    # REAL MEVZUAT RAG
    # -------------------------------------------------

    state.current_step = (
        "mevzuat_rag"
    )

    rag_question = build_rag_question(
        analysis_result=analysis_result,

        user_question=(
            text
            if route == "document_question"
            else None
        ),

        # EN ÖNEMLİ EKLEME:
        # OCR metni RAG query builder'a gönderiliyor.
        raw_text=state.raw_text,
    )

    rag_result = run_real_rag(
        question=rag_question,
        top_k=5,
    )

    state.rag_result = (
        rag_result
    )

    # -------------------------------------------------
    # REAL BIRIM YONLENDIRME
    # -------------------------------------------------

    state.current_step = (
        "birim_yonlendirme"
    )

    routing_result = route_unit(
        evrak_analysis=(
            analysis_result
        ),
        rag_result=(
            rag_result
        ),
    )

    state.routing_result = (
        routing_result.model_dump()
    )

    # -------------------------------------------------
    # RESMI YAZI - MOCK
    # -------------------------------------------------

    state.current_step = (
        "resmi_yazi"
    )

    resmi_yazi_result = (
        mock_resmi_yazi(
            analysis_result,
            rag_result,
        )
    )

    state.official_letter = (
        resmi_yazi_result
    )

    # -------------------------------------------------
    # FINAL
    # -------------------------------------------------

    state.current_step = "completed"
    state.status = "completed"

    return {
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
                    "text": state.raw_text,

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

        "evrak_analysis": (
            state.analysis
        ),

        "rag": (
            state.rag_result
        ),

        "routing": (
            state.routing_result
        ),

        "official_writing": (
            state.official_letter
        ),

        "validation": (
            evrak_result_dict.get(
                "validation",
                {
                    "status": "pending",
                    "issues": [],
                    "confidence": None,
                },
            )
        ),
    }


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