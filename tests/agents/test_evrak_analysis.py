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
    sys.path.insert(0, str(PROJECT_ROOT))


ENV_FILE = PROJECT_ROOT.parent / ".env"

load_dotenv(
    dotenv_path=ENV_FILE,
    override=True,
)


# =====================================================
# IMPORTS
# =====================================================

from langchain_openai import ChatOpenAI

from agents.evrak_analiz.agent import (
    EvrakAnalizAgent,
)


# =====================================================
# PATHS
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
# MAIN
# =====================================================

def main():

    print_section(
        "EVRAK ANALIZ AGENT TEST"
    )


    # =================================================
    # CHECK INPUT FILES
    # =================================================

    if not OCR_JSON.exists():

        print(
            "OCR sonucu bulunamadı:"
        )

        print(
            OCR_JSON
        )

        return


    if not CLASSIFICATION_JSON.exists():

        print(
            "Classification sonucu bulunamadı:"
        )

        print(
            CLASSIFICATION_JSON
        )

        return


    # =================================================
    # LOAD OCR
    # =================================================

    with open(
        OCR_JSON,
        "r",
        encoding="utf-8",
    ) as f:

        raw_ocr = json.load(f)


    # =================================================
    # LOAD CLASSIFICATION
    # =================================================

    with open(
        CLASSIFICATION_JSON,
        "r",
        encoding="utf-8",
    ) as f:

        classification_result = json.load(f)


    # =================================================
    # CONVERT OCR FORMAT
    #
    # OCR Agent output:
    # input.clean_text
    # input.metadata
    # input.tables
    # input.vision
    #
    # Evrak Analiz expects:
    # text
    # parsed_metadata
    # tables
    # vision
    # =================================================

    ocr_input = raw_ocr.get(
        "input",
        {},
    )


    ocr_data = {

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
    # SHOW INPUT
    # =================================================

    print_section(
        "1. OCR INPUT"
    )


    print(
        ocr_data["text"]
    )


    print_section(
        "2. CLASSIFICATION INPUT"
    )


    pretty_print(
        classification_result
    )


    # =================================================
    # CHECK API KEY
    # =================================================

    api_key = os.getenv(
        "EVREN_API_KEY"
    )


    if not api_key:

        print_section(
            "ERROR"
        )

        print(
            "EVREN_API_KEY bulunamadı."
        )

        print(
            ".env dosyasını kontrol et."
        )

        return


    # =================================================
    # CREATE SAME LLM AS ORCHESTRATOR
    # =================================================

    print_section(
        "3. LLM"
    )


    print(
        "Model: llm-fast"
    )

    print(
        "Evrak Analiz Agent hazırlanıyor..."
    )


    evrak_llm = ChatOpenAI(

        model="llm-fast",

        api_key=api_key,

        base_url=(
            "https://evren-llmapi.ssyz.org.tr/v1"
        ),

        temperature=0.0,
    )


    # =================================================
    # CREATE AGENT
    # =================================================

    agent = EvrakAnalizAgent(
        evrak_llm
    )


    # =================================================
    # RUN ONLY EVRAK ANALIZ AGENT
    # =================================================

    start_time = (
        time.perf_counter()
    )


    result = agent.analyze(

        ocr_data=ocr_data,

        classification_result=(
            classification_result
        ),
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
    # RESULT
    # =================================================

    print_section(
        "4. EVRAK ANALIZ RESULT"
    )


    pretty_print(
        result_dict
    )


    # =================================================
    # IMPORTANT FIELDS
    # =================================================

    print_section(
        "5. SUMMARY"
    )


    document_type = (
        result_dict.get(
            "document_type",
            {},
        )
    )


    print(
        "Document Type :",
        document_type.get(
            "label"
        ),
    )


    print(
        "Type Confidence:",
        document_type.get(
            "confidence"
        ),
    )


    print(
        "Topic         :",
        result_dict.get(
            "topic"
        ),
    )


    print(
        "Purpose       :",
        result_dict.get(
            "purpose"
        ),
    )


    print(
        "Intent        :",
        result_dict.get(
            "intent"
        ),
    )


    print(
        "Confidence    :",
        result_dict.get(
            "analysis_confidence"
        ),
    )


    # =================================================
    # TIMING
    # =================================================

    print_section(
        "6. TIMING"
    )


    print(
        f"Evrak Analiz süresi: "
        f"{elapsed:.2f} saniye"
    )


    # =================================================
    # SAVE OUTPUT
    # =================================================

    output_dir = (
        PROJECT_ROOT
        / "tests"
        / "agents"
        / "output"
        / "evrak_analysis"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_file = (
        output_dir
        / "test_evrak_analysis.json"
    )


    output_file.write_text(

        json.dumps(
            result_dict,
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
        "EVRAK ANALIZ TEST COMPLETED"
    )


    print(
        "Sonuç kaydedildi:"
    )

    print(
        output_file
    )


if __name__ == "__main__":
    main()