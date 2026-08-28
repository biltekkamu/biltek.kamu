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
# IMPORT
# =====================================================

from agents.resmi_yazi.agent import (
    ResmiYaziAgent,
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
        "RESMI YAZI AGENT TEST"
    )


    # =================================================
    # CHECK FILES
    # =================================================

    required_files = [
        OCR_JSON,
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
    # LOAD RESULTS
    # =================================================

    raw_ocr = load_json(
        OCR_JSON
    )

    evrak_analysis = load_json(
        EVRAK_ANALYSIS_JSON
    )

    rag_result = load_json(
        RAG_JSON
    )

    routing_test = load_json(
        ROUTING_JSON
    )


    routing_result = (
        routing_test.get(
            "routing_with_rag",
            routing_test,
        )
    )


    # =================================================
    # OCR NORMALIZATION
    # Resmi Yazı'nın gerçek workflow'da aldığı yapıya çevir
    # =================================================

    ocr_input = raw_ocr.get(
        "input",
        {},
    )


    ocr_result = {

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
    # SHOW INPUTS
    # =================================================

    print_section(
        "1. EVRAK ANALIZ INPUT"
    )

    pretty_print(
        evrak_analysis
    )


    print_section(
        "2. OCR METADATA"
    )

    pretty_print(
        ocr_result.get(
            "parsed_metadata",
            {},
        )
    )


    print_section(
        "3. RAG INPUT"
    )

    print(
        rag_result.get(
            "answer",
            ""
        )
    )


    print_section(
        "4. ROUTING INPUT"
    )

    pretty_print(
        routing_result
    )


    # =================================================
    # OPTIONAL MANUAL VALUES
    #
    # Kullanım:
    #
    # python test_resmi_yazi.py
    #
    # veya:
    #
    # python test_resmi_yazi.py talep_yazisi "Burcu KÖKSAL"
    # =================================================

    writing_type = None
    recipient = None


    if len(sys.argv) >= 2:

        writing_type = (
            sys.argv[1]
        )


    if len(sys.argv) >= 3:

        recipient = (
            sys.argv[2]
        )


    print_section(
        "5. ON-DEMAND SETTINGS"
    )


    print(
        "Writing Type:",
        writing_type
        or "AUTO",
    )


    print(
        "Recipient:",
        recipient
        or "AUTO / NONE",
    )


    # =================================================
    # CREATE AGENT
    # =================================================

    agent = ResmiYaziAgent()


    # =================================================
    # RUN ONLY RESMI YAZI
    # =================================================

    print_section(
        "6. RESMI YAZI GENERATING"
    )


    start_time = (
        time.perf_counter()
    )


    result = agent.generate(

        evrak_analysis=(
            evrak_analysis
        ),

        ocr_result=(
            ocr_result
        ),

        rag_result=(
            rag_result
        ),

        routing_result=(
            routing_result
        ),

        writing_type=(
            writing_type
        ),

        recipient=(
            recipient
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
    # FULL RESULT
    # =================================================

    print_section(
        "7. FULL RESMI YAZI RESULT"
    )


    pretty_print(
        result_dict
    )


    # =================================================
    # OFFICIAL WRITING PAYLOAD
    # =================================================

    official = (
        result_dict.get(
            "official_writing",
            {},
        )
    )


    print_section(
        "8. RESMI YAZI SUMMARY"
    )


    print(
        "Generated  :",
        official.get(
            "generated"
        ),
    )


    print(
        "Type       :",
        official.get(
            "type"
        ),
    )


    print(
        "Subject    :",
        official.get(
            "subject"
        ),
    )


    print(
        "Confidence :",
        official.get(
            "confidence"
        ),
    )


    # =================================================
    # BODY
    # =================================================

    print_section(
        "9. BODY"
    )


    print(
        official.get(
            "body"
        )
        or "Body oluşturulmadı."
    )


    # =================================================
    # VALIDATION
    # =================================================

    print_section(
        "10. RESMI YAZI VALIDATION"
    )


    pretty_print(
        official.get(
            "validation",
            {},
        )
    )


    # =================================================
    # TIMING
    # =================================================

    print_section(
        "11. TIMING"
    )


    print(
        f"Resmi Yazı süresi: "
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
        / "resmi_yazi"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_file = (
        output_dir
        / "test_resmi_yazi.json"
    )


    output_data = {

        "official_writing":
            official,

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
        "RESMI YAZI TEST COMPLETED"
    )


    print(
        "Sonuç kaydedildi:"
    )

    print(
        output_file
    )


if __name__ == "__main__":
    main()