import json
import sys
import time
from pathlib import Path


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
# ROUTING IMPORT
# =====================================================

from agents.birim_yonlendirme.agent import (
    route_unit,
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

RAG_JSON = (
    PROJECT_ROOT
    / "tests"
    / "agents"
    / "output"
    / "rag"
    / "test_rag.json"
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
# DEBUG KEYWORD CHECK
# =====================================================

def find_matching_keywords(
    evrak_analysis,
    rag_result,
):

    document_type = evrak_analysis.get(
        "document_type",
        {},
    )

    if isinstance(
        document_type,
        dict,
    ):

        document_type_label = str(
            document_type.get(
                "label",
                "",
            )
        ).lower()

    else:

        document_type_label = str(
            document_type
        ).lower()


    topic = str(
        evrak_analysis.get(
            "topic",
            "",
        )
    ).lower()


    purpose = str(
        evrak_analysis.get(
            "purpose",
            "",
        )
    ).lower()


    intent = str(
        evrak_analysis.get(
            "intent",
            "",
        )
    ).lower()


    summary = str(
        evrak_analysis.get(
            "summary",
            "",
        )
    ).lower()


    rag_answer = str(
        rag_result.get(
            "answer",
            "",
        )
    ).lower()


    combined_text = " ".join(
        [
            document_type_label,
            topic,
            purpose,
            intent,
            summary,
            rag_answer,
        ]
    )


    rules = {

        "İnsan Kaynakları Birimi": [
            "izin",
            "yıllık izin",
            "personel",
            "memur",
            "işçi",
            "özlük",
        ],

        "Ceza İşleri Birimi": [
            "uyuşturucu",
            "suç",
            "ceza",
            "hırsızlık",
            "yaralama",
            "dolandırıcılık",
        ],

        "Mali Hizmetler Birimi": [
            "vergi",
            "ödeme",
            "borç",
            "mali",
            "bütçe",
            "harcama",
        ],

        "Bilgi İşlem Birimi": [
            "yazılım",
            "sistem",
            "sunucu",
            "ağ",
            "bilgi işlem",
        ],

        "Hukuk İşleri Birimi": [
            "dava",
            "itiraz",
            "hukuk",
            "hukuki",
            "sözleşme",
        ],
    }


    matches = {}


    for department, keywords in rules.items():

        found = [
            keyword
            for keyword in keywords
            if keyword in combined_text
        ]

        if found:

            matches[
                department
            ] = found


    return (
        combined_text,
        matches,
    )


# =====================================================
# MAIN
# =====================================================

def main():

    print_section(
        "BIRIM YONLENDIRME AGENT TEST"
    )


    # =================================================
    # CHECK INPUT FILES
    # =================================================

    if not EVRAK_ANALYSIS_JSON.exists():

        print(
            "Evrak Analysis sonucu bulunamadı:"
        )

        print(
            EVRAK_ANALYSIS_JSON
        )

        return


    if not RAG_JSON.exists():

        print(
            "RAG sonucu bulunamadı:"
        )

        print(
            RAG_JSON
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

        evrak_analysis = (
            json.load(f)
        )


    # =================================================
    # LOAD RAG
    # =================================================

    with open(
        RAG_JSON,
        "r",
        encoding="utf-8",
    ) as f:

        rag_result = (
            json.load(f)
        )


    # =================================================
    # INPUT
    # =================================================

    print_section(
        "1. EVRAK ANALIZ INPUT"
    )

    pretty_print(
        evrak_analysis
    )


    print_section(
        "2. RAG INPUT"
    )

    print(
        rag_result.get(
            "answer",
            ""
        )
    )


    # =================================================
    # DEBUG MATCHES
    # =================================================

    (
        combined_text,
        matches,
    ) = find_matching_keywords(
        evrak_analysis,
        rag_result,
    )


    print_section(
        "3. MATCHED ROUTING KEYWORDS"
    )


    if matches:

        for department, keywords in (
            matches.items()
        ):

            print(
                f"\n{department}:"
            )

            for keyword in keywords:

                print(
                    f"  - {keyword}"
                )

    else:

        print(
            "Hiçbir routing keyword eşleşmedi."
        )


    # =================================================
    # RUN ROUTING
    # =================================================

    print_section(
        "4. ROUTING"
    )


    start_time = (
        time.perf_counter()
    )


    result = route_unit(

        evrak_analysis=(
            evrak_analysis
        ),

        rag_result=(
            rag_result
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
        "5. ROUTING RESULT"
    )


    pretty_print(
        result_dict
    )


    print("\nSelected Department:")

    print(
        result_dict.get(
            "selected_department"
        )
    )


    print("\nReason:")

    print(
        result_dict.get(
            "reason"
        )
    )


    print("\nConfidence:")

    print(
        result_dict.get(
            "confidence"
        )
    )


    # =================================================
    # SECOND TEST — WITHOUT RAG
    # =================================================

    print_section(
        "6. ROUTING WITHOUT RAG"
    )


    no_rag_result = route_unit(

        evrak_analysis=(
            evrak_analysis
        ),

        rag_result={
            "answer": ""
        },
    )


    if hasattr(
        no_rag_result,
        "model_dump",
    ):

        no_rag_dict = (
            no_rag_result.model_dump()
        )

    else:

        no_rag_dict = (
            no_rag_result
        )


    pretty_print(
        no_rag_dict
    )


    # =================================================
    # TIMING
    # =================================================

    print_section(
        "7. TIMING"
    )


    print(
        f"Routing süresi: "
        f"{elapsed:.6f} saniye"
    )


    # =================================================
    # SAVE
    # =================================================

    output_dir = (
        PROJECT_ROOT
        / "tests"
        / "agents"
        / "output"
        / "routing"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_file = (
        output_dir
        / "test_routing.json"
    )


    output_data = {

        "routing_with_rag":
            result_dict,

        "routing_without_rag":
            no_rag_dict,

        "matched_keywords":
            matches,

        "timing":
            round(
                elapsed,
                6,
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
        "ROUTING TEST COMPLETED"
    )


    print(
        "Sonuç kaydedildi:"
    )

    print(
        output_file
    )


if __name__ == "__main__":
    main()