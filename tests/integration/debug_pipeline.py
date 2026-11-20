from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime


# =====================================================
# PROJECT ROOT
# =====================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]


if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )


from orkestrasyon.orchestrator import process_input


# =====================================================
# HELPERS
# =====================================================

def print_title(
    title: str,
) -> None:

    print("\n")
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def pretty_print(
    data,
) -> None:

    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def save_json(
    path: Path,
    data,
) -> None:

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


# =====================================================
# DEBUG OUTPUT
# =====================================================

def show_document_info(
    result: dict,
) -> None:

    print_title(
        "0. DOCUMENT INFO"
    )

    data = result.get(
        "document_info"
    )

    pretty_print(
        data or {}
    )


def show_ocr(
    result: dict,
) -> None:

    print_title(
        "1. OCR"
    )

    ocr = result.get(
        "ocr"
    ) or {}

    text = (
        ocr.get("text")
        or
        ocr.get("clean_text")
        or
        ocr.get("input", {}).get(
            "clean_text"
        )
        or ""
    )

    print("\n[OCR TEXT]\n")

    print(
        text or
        "OCR metni bulunamadı."
    )

    print("\n[OCR METADATA]\n")

    metadata = (
        ocr.get("parsed_metadata")
        or
        ocr.get("metadata")
        or
        ocr.get("input", {}).get(
            "metadata"
        )
        or {}
    )

    pretty_print(
        metadata
    )


def show_classification(
    result: dict,
) -> None:

    print_title(
        "2. CLASSIFICATION"
    )

    data = result.get(
        "classification"
    ) or {}

    pretty_print(
        data
    )


def show_evrak_analysis(
    result: dict,
) -> None:

    print_title(
        "3. EVRAK ANALYSIS"
    )

    data = result.get(
        "evrak_analysis"
    ) or {}

    pretty_print(
        data
    )


def show_rag(
    result: dict,
) -> None:

    print_title(
        "4. MEVZUAT RAG"
    )

    rag = result.get(
        "rag"
    ) or {}

    print("\n[RAG QUERY]\n")

    print(
        rag.get(
            "query"
        )
        or "-"
    )

    print("\n[RAG ANSWER]\n")

    print(
        rag.get(
            "answer"
        )
        or "-"
    )

    print("\n[RAG SOURCES]\n")

    sources = (
        rag.get(
            "sources"
        )
        or []
    )

    for index, source in enumerate(
        sources,
        start=1,
    ):

        print(
            f"{index}. "
            f"{source.get('title', '-')}"
        )

        print(
            "   "
            f"{source.get('law_number', '')} "
            f"{source.get('article', '')}"
        )

        print()


def show_routing(
    result: dict,
) -> None:

    print_title(
        "5. BIRIM YONLENDIRME"
    )

    data = result.get(
        "routing"
    ) or {}

    pretty_print(
        data
    )


def show_validation(
    result: dict,
) -> None:

    print_title(
        "6. DOGRULAMA"
    )

    data = result.get(
        "validation"
    ) or {}

    pretty_print(
        data
    )


def show_official_writing(
    result: dict,
) -> None:

    print_title(
        "7. RESMI YAZI"
    )

    official = result.get(
        "official_writing"
    )

    if not official:

        print(
            "ON-DEMAND:"
        )

        print(
            "Resmi Yazı ana workflow sırasında "
            "otomatik çalıştırılmadı."
        )

        print(
            "Kullanıcı Resmi Yazı Oluştur "
            "butonuna bastığında çalışır."
        )

        return

    pretty_print(
        official
    )


def show_timing(
    result: dict,
) -> None:

    print_title(
        "TIMING"
    )

    data = result.get(
        "timing"
    ) or {}

    pretty_print(
        data
    )


# =====================================================
# SAVE EACH LAYER
# =====================================================

def save_layers(
    result: dict,
    output_dir: Path,
) -> None:

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    layers = {

        "00_document_info.json":
            result.get(
                "document_info"
            ),

        "01_ocr.json":
            result.get(
                "ocr"
            ),

        "02_classification.json":
            result.get(
                "classification"
            ),

        "03_evrak_analysis.json":
            result.get(
                "evrak_analysis"
            ),

        "04_rag.json":
            result.get(
                "rag"
            ),

        "05_routing.json":
            result.get(
                "routing"
            ),

        "06_validation.json":
            result.get(
                "validation"
            ),

        "07_official_writing.json":
            result.get(
                "official_writing"
            ),

        "08_timing.json":
            result.get(
                "timing"
            ),

        "final.json":
            result,
    }


    for file_name, data in layers.items():

        save_json(
            output_dir /
            file_name,

            data,
        )


# =====================================================
# MAIN
# =====================================================

def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "BILTEK KAMU "
            "step-by-step debug pipeline"
        )
    )


    parser.add_argument(
        "file",
        nargs="?",
        default=None,
        help="Test edilecek belge yolu",
    )


    parser.add_argument(
        "--question",
        "-q",
        default=None,
        help="Belge ile birlikte sorulacak soru",
    )


    parser.add_argument(
        "--mode",
        choices=[
            "citizen",
            "expert",
        ],
        default="citizen",
        help="Yanıt modu",
    )


    args = parser.parse_args()


    # =============================================
    # INPUT CONTROL
    # =============================================

    if (
        not args.file
        and
        not args.question
    ):

        print(
            "HATA:"
        )

        print(
            "Bir dosya veya soru vermelisiniz."
        )

        return


    file_path = None


    if args.file:

        file_path = Path(
            args.file
        ).resolve()


        if not file_path.exists():

            print(
                f"Dosya bulunamadı: "
                f"{file_path}"
            )

            return


    # =============================================
    # INPUT
    # =============================================

    print_title(
        "BILTEK KAMU DEBUG PIPELINE"
    )


    print(
        f"File     : "
        f"{file_path or '-'}"
    )

    print(
        f"Question : "
        f"{args.question or '-'}"
    )

    print(
        f"Mode     : "
        f"{args.mode}"
    )


    print(
        "\nPipeline çalıştırılıyor..."
    )


    # =============================================
    # REAL WORKFLOW
    # =============================================

    result = process_input(

        file=(
            str(file_path)
            if file_path
            else None
        ),

        text=args.question,

        mode=args.mode,
    )


    # =============================================
    # SHOW RESULTS
    # =============================================

    if result.get(
        "document_info"
    ):
        show_document_info(
            result
        )


    if result.get(
        "ocr"
    ):
        show_ocr(
            result
        )


    if result.get(
        "classification"
    ):
        show_classification(
            result
        )


    if result.get(
        "evrak_analysis"
    ):
        show_evrak_analysis(
            result
        )


    if result.get(
        "rag"
    ):
        show_rag(
            result
        )


    if result.get(
        "routing"
    ):
        show_routing(
            result
        )


    if result.get(
        "validation"
    ):
        show_validation(
            result
        )


    show_official_writing(
        result
    )


    show_timing(
        result
    )


    # =============================================
    # SAVE
    # =============================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )


    output_dir = (
        PROJECT_ROOT
        / "tests"
        / "integration"
        / "debug_output"
        / timestamp
    )


    save_layers(
        result,
        output_dir,
    )


    print_title(
        "DEBUG COMPLETED"
    )


    print(
        "Sonuçlar buraya kaydedildi:"
    )

    print(
        output_dir
    )


if __name__ == "__main__":
    main()