import json
import os
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
# =====================================================

ENV_FILE = (
    PROJECT_ROOT.parent
    / ".env"
)

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True,
)


# =====================================================
# DOGRULAMA AGENT PATH
#
# validator_service.py kendi klasöründeki
# "models", "schema_validator" vb. dosyaları
# doğrudan import ettiği için bu klasörü
# sys.path'e ekliyoruz.
# =====================================================

VALIDATION_AGENT_DIR = (
    PROJECT_ROOT
    / "agents"
    / "dogrulama_agent"
)

if str(VALIDATION_AGENT_DIR) not in sys.path:
    sys.path.insert(
        0,
        str(VALIDATION_AGENT_DIR),
    )


# =====================================================
# IMPORTS
# =====================================================

from langchain_openai import ChatOpenAI

from validator_service import (
    DocumentValidationService,
)


# =====================================================
# INPUT FILES
# =====================================================

OCR_JSON = (
    PROJECT_ROOT
    / "tests"
    / "agents"
    / "output"
    / "ocr"
    / "test_ocr.json"
)

CLASSIFICATION_JSON = (
    PROJECT_ROOT
    / "tests"
    / "agents"
    / "output"
    / "classification"
    / "test_classification.json"
)

EVRAK_ANALYSIS_JSON = (
    PROJECT_ROOT
    / "tests"
    / "agents"
    / "output"
    / "evrak_analysis"
    / "test_evrak_analysis.json"
)

RAG_JSON = (
    PROJECT_ROOT
    / "tests"
    / "agents"
    / "output"
    / "rag"
    / "test_rag.json"
)

ROUTING_JSON = (
    PROJECT_ROOT
    / "tests"
    / "agents"
    / "output"
    / "routing"
    / "test_routing.json"
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


def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


# =====================================================
# MAIN
# =====================================================

def main():

    print_section(
        "DOGRULAMA AGENT TEST"
    )


    # =================================================
    # CHECK FILES
    # =================================================

    required_files = [
        OCR_JSON,
        CLASSIFICATION_JSON,
        EVRAK_ANALYSIS_JSON,
        RAG_JSON,
        ROUTING_JSON,
    ]


    for path in required_files:

        if not path.exists():

            print(
                "Eksik test çıktısı:"
            )

            print(
                path
            )

            return


    # =================================================
    # LOAD PREVIOUS AGENT OUTPUTS
    # =================================================

    raw_ocr = load_json(
        OCR_JSON
    )

    classification_result = load_json(
        CLASSIFICATION_JSON
    )

    evrak_analysis = load_json(
        EVRAK_ANALYSIS_JSON
    )

    rag_result = load_json(
        RAG_JSON
    )

    routing_test_result = load_json(
        ROUTING_JSON
    )


    # =================================================
    # ROUTING
    #
    # test_routing.json içinde iki sonuç var:
    # routing_with_rag
    # routing_without_rag
    #
    # Gerçek workflow routing_with_rag kullanıyor.
    # =================================================

    routing_result = (
        routing_test_result.get(
            "routing_with_rag",
            routing_test_result,
        )
    )


    # =================================================
    # OCR FORMAT
    #
    # OCR Agent:
    # {
    #   document_info: ...
    #   input: {
    #       clean_text,
    #       metadata,
    #       tables,
    #       vision
    #   }
    # }
    #
    # Validation bekliyor:
    # {
    #   ocr: {
    #       text,
    #       pages,
    #       parsed_metadata,
    #       tables,
    #       vision
    #   }
    # }
    # =================================================

    ocr_input = raw_ocr.get(
        "input",
        {},
    )


    ocr_block = {

        "text": (
            ocr_input.get(
                "clean_text",
                "",
            )
        ),

        "pages": [],

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
    }


    # =================================================
    # BUILD SAME FINAL JSON AS ORCHESTRATOR
    # =================================================

    final_json = {

        "success": True,

        "document_info": (
            raw_ocr.get(
                "document_info",
                {},
            )
        ),

        "ocr": (
            ocr_block
        ),

        "classification": (
            classification_result
        ),

        "evrak_analysis": (
            evrak_analysis
        ),

        "rag": (
            rag_result
        ),

        "routing": (
            routing_result
        ),

        "official_writing": None,

        "validation": {
            "status": "pending",
            "issues": [],
            "confidence": None,
        },
    }


    # =================================================
    # SHOW INPUT
    # =================================================

    print_section(
        "1. VALIDATION INPUT"
    )


    print(
        "Document:",
        final_json[
            "document_info"
        ].get(
            "file_name"
        ),
    )


    print(
        "Classification:",
        classification_result.get(
            "label"
        ),
    )


    print(
        "Evrak Type:",
        evrak_analysis
        .get(
            "document_type",
            {},
        )
        .get(
            "label"
        ),
    )


    print(
        "Routing:",
        routing_result.get(
            "selected_department"
        ),
    )


    print(
        "RAG Sources:",
        len(
            rag_result.get(
                "sources",
                [],
            )
        ),
    )


    # =================================================
    # LLM
    # Semantic Validator için aynı LLM
    # =================================================

    print_section(
        "2. SEMANTIC VALIDATOR LLM"
    )


    api_key = os.getenv(
        "EVREN_API_KEY"
    )


    if not api_key:

        print(
            "EVREN_API_KEY bulunamadı."
        )

        print(
            f"ENV: {ENV_FILE}"
        )

        return


    print(
        "Model: llm-fast"
    )


    llm = ChatOpenAI(

        model="llm-fast",

        api_key=api_key,

        base_url=(
            "https://evren-llmapi.ssyz.org.tr/v1"
        ),

        temperature=0.0,
    )


    # =================================================
    # CREATE VALIDATION SERVICE
    # =================================================

    validation_service = (
        DocumentValidationService(
            llm_client=llm
        )
    )


    # =================================================
    # RUN ONLY VALIDATION
    # =================================================

    print_section(
        "3. VALIDATION RUNNING"
    )


    start_time = (
        time.perf_counter()
    )


    result = (
        validation_service
        .validate_document(
            final_json
        )
    )


    elapsed = (
        time.perf_counter()
        - start_time
    )


    # =================================================
    # PYDANTIC -> DICT
    # =================================================

    if hasattr(
        result,
        "model_dump",
    ):

        result_dict = (
            result.model_dump()
        )

    else:

        result_dict = result


    # =================================================
    # FINAL STATUS
    # =================================================

    print_section(
        "4. VALIDATION RESULT"
    )


    print(
        "Status:",
        result_dict.get(
            "status"
        ),
    )


    print(
        "Confidence:",
        result_dict.get(
            "confidence"
        ),
    )


    issues = (
        result_dict.get(
            "issues",
            [],
        )
    )


    print(
        "Issue Count:",
        len(issues),
    )


    # =================================================
    # SHOW ISSUES ONE BY ONE
    # =================================================

    print_section(
        "5. ISSUES"
    )


    if not issues:

        print(
            "Validation issue bulunamadı."
        )

    else:

        for index, issue in enumerate(
            issues,
            start=1,
        ):

            print(
                f"\n--- ISSUE {index} ---"
            )

            print(
                "Field    :",
                issue.get(
                    "field"
                ),
            )

            print(
                "Type     :",
                issue.get(
                    "type"
                ),
            )

            print(
                "Severity :",
                issue.get(
                    "severity"
                ),
            )

            print(
                "Message  :",
                issue.get(
                    "message"
                ),
            )


    # =================================================
    # GROUP ISSUES BY TYPE
    # =================================================

    print_section(
        "6. ISSUE SUMMARY"
    )


    issue_summary = {}


    for issue in issues:

        issue_type = str(
            issue.get(
                "type",
                "unknown",
            )
        )


        issue_summary[
            issue_type
        ] = (
            issue_summary.get(
                issue_type,
                0,
            )
            + 1
        )


    if issue_summary:

        for issue_type, count in (
            issue_summary.items()
        ):

            print(
                f"{issue_type:<30} "
                f"{count}"
            )

    else:

        print(
            "Issue yok."
        )


    # =================================================
    # TIMING
    # =================================================

    print_section(
        "7. TIMING"
    )


    print(
        f"Validation süresi: "
        f"{elapsed:.2f} saniye"
    )


    # =================================================
    # SAVE
    # =================================================

    output_dir = (
        PROJECT_ROOT
        / "tests"
        / "agents"
        / "output"
        / "validation"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_file = (
        output_dir
        / "test_validation.json"
    )


    output_data = {

        "validation":
            result_dict,

        "timing":
            round(
                elapsed,
                2,
            ),
    }


    output_file.write_text(

        json.dumps(
            output_data,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),

        encoding="utf-8",
    )


    # =================================================
    # FINISH
    # =================================================

    print_section(
        "DOGRULAMA TEST COMPLETED"
    )


    print(
        "Sonuç kaydedildi:"
    )

    print(
        output_file
    )


if __name__ == "__main__":
    main()