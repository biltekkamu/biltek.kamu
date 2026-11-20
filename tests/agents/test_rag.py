import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv


# =====================================================
# PROJECT ROOT
# =====================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


# =====================================================
# ENV
# rag_service
# =====================================================

ENV_FILE = (
    PROJECT_ROOT.parent
    / ".env"
)

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True,
)


if not os.getenv("EVREN_API_KEY"):

    print(
        "EVREN_API_KEY bulunamadı."
    )

    print(
        f"ENV: {ENV_FILE}"
    )

    sys.exit(1)


# =====================================================
# RAG IMPORTS
# =====================================================

from agents.mevzuat_rag.rag_service import (
    normalize_question,
    retrieve_documents,
    generate_answer,
)


# =====================================================
# INPUT FILES
# =====================================================

EVRAK_ANALYSIS_JSON = (
    PROJECT_ROOT
    / "tests"
    / "agents"
    / "output"
    / "evrak_analysis"
    / "test_evrak_analysis.json"
)

OCR_JSON = (
    PROJECT_ROOT
    / "tests"
    / "agents"
    / "output"
    / "ocr"
    / "test_ocr.json"
)


# =====================================================
# HELPERS
# =====================================================

def print_section(title):

    print("\n")
    print("=" * 70)
    print(title)
    print("=" * 70)


def pretty_print(data):

    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


# =====================================================
# EXPLICIT LEGAL REFERENCES
# =====================================================

def extract_explicit_legal_references(
    text: str,
) -> list[str]:

    if not text:
        return []

    refs = []

    patterns = [

        (
            r"(\d{4})\s+say[ıi]l[ıi]"
            r".{0,40}?"
            r"(\d{1,4})\s*"
            r"(?:nci|ncı|inci|ıncı|uncu|üncü|madde|maddesi)"
        ),

        (
            r"\b(CMK|TCK|VUK)"
            r"\s*['’]?"
            r"(?:nun|nın|nin|un|ün)?"
            r"\s*(\d{1,4})"
        ),
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


    legal_refs = (
        extract_explicit_legal_references(
            raw_text or ""
        )
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


    return (
        f"{document_context}."
        f"{legal_context}"
    )


# =====================================================
# MAIN
# =====================================================

def main():

    print_section(
        "MEVZUAT RAG AGENT TEST"
    )


    # =================================================
    # CHECK INPUT FILES
    # =================================================

    if not EVRAK_ANALYSIS_JSON.exists():

        print(
            "Evrak Analysis JSON bulunamadı:"
        )

        print(
            EVRAK_ANALYSIS_JSON
        )

        return


    if not OCR_JSON.exists():

        print(
            "OCR JSON bulunamadı:"
        )

        print(
            OCR_JSON
        )

        return


    # =================================================
    # LOAD EVRAK ANALYSIS
    # =================================================

    with open(
        EVRAK_ANALYSIS_JSON,
        "r",
        encoding="utf-8",
    ) as f:

        analysis_result = json.load(f)


    # =================================================
    # LOAD OCR
    # =================================================

    with open(
        OCR_JSON,
        "r",
        encoding="utf-8",
    ) as f:

        raw_ocr = json.load(f)


    raw_text = (
        raw_ocr
        .get(
            "input",
            {},
        )
        .get(
            "clean_text",
            "",
        )
    )


    # =================================================
    # SHOW INPUT
    # =================================================

    print_section(
        "1. EVRAK ANALIZ INPUT"
    )

    pretty_print(
        analysis_result
    )


    # =================================================
    # EXPLICIT LEGAL REFERENCES
    # =================================================

    legal_refs = (
        extract_explicit_legal_references(
            raw_text
        )
    )


    print_section(
        "2. EXPLICIT LEGAL REFERENCES"
    )


    if legal_refs:

        for ref in legal_refs:

            print(
                f"- {ref}"
            )

    else:

        print(
            "Belgede açık mevzuat referansı bulunamadı."
        )


    # =================================================
    # BUILD QUERY
    # =================================================

    rag_question = (
        build_rag_question(
            analysis_result=(
                analysis_result
            ),
            raw_text=raw_text,
        )
    )


    normalized_question = (
        normalize_question(
            rag_question
        )
    )


    print_section(
        "3. RAG QUERY"
    )


    print(
        normalized_question
    )


    # =================================================
    # RETRIEVAL
    # =================================================

    print_section(
        "4. RETRIEVAL"
    )


    print(
        "Chroma + BM25 + Reranker çalışıyor..."
    )


    retrieval_start = (
        time.perf_counter()
    )


    documents = (
        retrieve_documents(
            normalized_question,
            top_k=5,
        )
    )


    retrieval_time = (
        time.perf_counter()
        - retrieval_start
    )


    print(
        f"\nRetrieved document count: "
        f"{len(documents)}"
    )


    print(
        f"Retrieval süresi: "
        f"{retrieval_time:.2f} saniye"
    )


    # =================================================
    # SHOW RETRIEVED DOCUMENTS
    # =================================================

    print_section(
        "5. RETRIEVED DOCUMENTS"
    )


    if not documents:

        print(
            "Mevzuat kaynağı bulunamadı."
        )

        return


    for index, doc in enumerate(
        documents,
        start=1,
    ):

        metadata = doc.get(
            "metadata",
            {},
        )


        print(
            f"\n--- DOCUMENT {index} ---"
        )


        print(
            "Law Name     :",
            metadata.get(
                "law_name",
                metadata.get(
                    "document_name",
                    "-"
                ),
            ),
        )


        print(
            "Law Number   :",
            metadata.get(
                "law_number",
                "-"
            ),
        )


        print(
            "Article      :",
            metadata.get(
                "madde",
                "-"
            ),
        )


        print(
            "Score        :",
            doc.get(
                "score",
                "-"
            ),
        )


        print(
            "Rerank Score :",
            doc.get(
                "rerank_score",
                "-"
            ),
        )


        print(
            "RRF Score    :",
            doc.get(
                "rrf_score",
                "-"
            ),
        )


        print(
            "Distance     :",
            doc.get(
                "distance",
                "-"
            ),
        )


        content = (
            doc.get("text")
            or doc.get("page_content")
            or doc.get("content")
            or doc.get("document")
            or ""
        )


        print(
            "\nContent:"
        )

        print(
            content[:1500]
        )


        if len(content) > 1500:

            print(
                "\n...[content truncated]"
            )


    # =================================================
    # GENERATION QUESTION
    # =================================================

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


    # =================================================
    # GENERATE ANSWER
    # =================================================

    print_section(
        "6. LLM ANSWER GENERATION"
    )


    print(
        "Model: llm-large"
    )

    print(
        "Cevap oluşturuluyor..."
    )


    generation_start = (
        time.perf_counter()
    )


    answer = generate_answer(
        generation_question,
        documents,
        history=None,
        mode="citizen",
    )


    generation_time = (
        time.perf_counter()
        - generation_start
    )


    # =================================================
    # ANSWER
    # =================================================

    print_section(
        "7. RAG ANSWER"
    )


    print(
        answer
    )


    # =================================================
    # SOURCES
    # =================================================

    print_section(
        "8. SOURCES"
    )


    sources = []


    for doc in documents:

        metadata = doc.get(
            "metadata",
            {},
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


        source = {

            "source_type":
                "kanun",

            "title":
                metadata.get(
                    "law_name",
                    metadata.get(
                        "document_name",
                    ),
                ),

            "law_number":
                metadata.get(
                    "law_number"
                ),

            "article":
                article,

            "content":
                content,
        }


        sources.append(
            source
        )


        print(
            f"- {source['title']} | "
            f"{source['law_number']} | "
            f"{source['article']}"
        )


    # =================================================
    # TIMING
    # =================================================

    total_time = (
        retrieval_time
        + generation_time
    )


    print_section(
        "9. TIMING"
    )


    print(
        f"Retrieval  : "
        f"{retrieval_time:.2f} sec"
    )


    print(
        f"Generation : "
        f"{generation_time:.2f} sec"
    )


    print(
        f"Total RAG  : "
        f"{total_time:.2f} sec"
    )


    # =================================================
    # FINAL RESULT
    # =================================================

    scores = []


    for doc in documents:

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


    confidence = (
        round(
            max(scores),
            3,
        )
        if scores
        else None
    )


    final_result = {

        "query":
            normalized_question,

        "answer":
            answer,

        "sources":
            sources,

        "confidence":
            confidence,

        "debug": {

            "retrieved_documents":
                documents,

            "timing": {

                "retrieval":
                    round(
                        retrieval_time,
                        2,
                    ),

                "generation":
                    round(
                        generation_time,
                        2,
                    ),

                "total":
                    round(
                        total_time,
                        2,
                    ),
            },
        },
    }


    # =================================================
    # SAVE
    # =================================================

    output_dir = (
        PROJECT_ROOT
        / "tests"
        / "agents"
        / "output"
        / "rag"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_file = (
        output_dir
        / "test_rag.json"
    )


    output_file.write_text(

        json.dumps(
            final_result,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),

        encoding="utf-8",
    )


    print_section(
        "RAG TEST COMPLETED"
    )


    print(
        "Sonuç kaydedildi:"
    )

    print(
        output_file
    )


if __name__ == "__main__":
    main()