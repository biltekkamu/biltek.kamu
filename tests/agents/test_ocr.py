import json
import sys
import time
from pathlib import Path


# =====================================================
# PROJECT ROOT
# =====================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =====================================================
# OCR IMPORT
# =====================================================

from agents.ocr.main_pipeline import MultiPageOCRPipeline


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

    if len(sys.argv) < 2:

        print("Kullanım:")
        print(
            "python .\\tests\\agents\\test_ocr.py .\\test.jpeg"
        )

        return


    file_path = Path(
        sys.argv[1]
    ).resolve()


    if not file_path.exists():

        print(
            f"Dosya bulunamadı: {file_path}"
        )

        return


    print_section(
        "OCR AGENT TEST"
    )


    print(
        f"Dosya: {file_path}"
    )


    # =================================================
    # CREATE OCR AGENT
    # =================================================

    print("\nOCR modeli hazırlanıyor...")


    ocr_agent = MultiPageOCRPipeline(
        lang="tr"
    )


    # =================================================
    # RUN OCR
    # =================================================

    start_time = time.perf_counter()


    result = ocr_agent.process_file(
        file_path=str(file_path),
        doc_id="ocr_test_001",
        lang="tr",
    )


    elapsed = (
        time.perf_counter()
        - start_time
    )


    # =================================================
    # PYDANTIC -> DICT
    # =================================================

    if hasattr(result, "model_dump"):

        data = result.model_dump()

    else:

        data = result


    # =================================================
    # SUCCESS
    # =================================================

    print_section(
        "1. STATUS"
    )


    print(
        f"Success: {data.get('success')}"
    )


    # =================================================
    # DOCUMENT INFO
    # =================================================

    print_section(
        "2. DOCUMENT INFO"
    )


    document_info = (
        data.get(
            "document_info",
            {}
        )
    )


    pretty_print(
        document_info
    )


    # =================================================
    # STANDARD INPUT
    # =================================================

    ocr_input = (
        data.get(
            "input",
            {}
        )
    )


    # =================================================
    # CLEAN TEXT
    # =================================================

    print_section(
        "3. OCR TEXT"
    )


    clean_text = (
        ocr_input.get(
            "clean_text",
            ""
        )
    )


    print(
        clean_text
        if clean_text
        else "OCR metni bulunamadı."
    )


    # =================================================
    # METADATA
    # =================================================

    print_section(
        "4. METADATA"
    )


    metadata = (
        ocr_input.get(
            "metadata",
            {}
        )
    )


    pretty_print(
        metadata
    )


    # =================================================
    # TABLES
    # =================================================

    print_section(
        "5. TABLES"
    )


    tables = (
        ocr_input.get(
            "tables",
            []
        )
    )


    if tables:

        pretty_print(
            tables
        )

    else:

        print(
            "Tablo bulunamadı."
        )


    # =================================================
    # VISION
    # =================================================

    print_section(
        "6. VISION"
    )


    vision = (
        ocr_input.get(
            "vision",
            {}
        )
    )


    pretty_print(
        vision
    )


    # =================================================
    # TIMING
    # =================================================

    print_section(
        "7. TIMING"
    )


    print(
        f"OCR süresi: {elapsed:.2f} saniye"
    )


    # =================================================
    # SAVE RESULT
    # =================================================

    output_dir = (
        PROJECT_ROOT
        / "tests"
        / "agents"
        / "output"
        / "ocr"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_file = (
        output_dir
        / f"{file_path.stem}_ocr.json"
    )


    output_file.write_text(
        json.dumps(
            data,
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
        "OCR TEST COMPLETED"
    )


    print(
        "Sonuç kaydedildi:"
    )

    print(
        output_file
    )


if __name__ == "__main__":
    main()