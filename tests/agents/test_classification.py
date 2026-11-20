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
# CLASSIFICATION IMPORT
# =====================================================

from agents.classification_agent.hybrid_classifier import (
    HybridDocumentClassifier,
)


# =====================================================
# PATHS
# =====================================================

MODEL_DIR = (
    PROJECT_ROOT
    / "agents"
    / "classification_agent"
    / "berturk_classifier_v1"
)

EVAL_DIR = (
    PROJECT_ROOT
    / "agents"
    / "classification_agent"
    / "evaluation"
)

DEFAULT_OCR_JSON = (
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
# MAIN
# =====================================================

def main():

    # -------------------------------------------------
    # OCR JSON PATH
    # -------------------------------------------------

    if len(sys.argv) >= 2:

        input_file = Path(
            sys.argv[1]
        ).resolve()

    else:

        input_file = DEFAULT_OCR_JSON


    if not input_file.exists():

        print("OCR JSON bulunamadı:")

        print(
            input_file
        )

        print(
            "\nÖnce OCR testini çalıştır:"
        )

        print(
            "python .\\tests\\agents\\test_ocr.py .\\test.jpeg"
        )

        return


    print_section(
        "CLASSIFICATION AGENT TEST"
    )


    print(
        f"OCR JSON: {input_file}"
    )


    # =================================================
    # LOAD OCR RESULT
    # =================================================

    with open(
        input_file,
        "r",
        encoding="utf-8",
    ) as f:

        ocr_data = json.load(f)


    clean_text = (
        ocr_data
        .get(
            "input",
            {}
        )
        .get(
            "clean_text",
            ""
        )
    )


    if not clean_text.strip():

        print(
            "\nHATA: OCR clean_text boş."
        )

        return


    # =================================================
    # SHOW INPUT
    # =================================================

    print_section(
        "1. CLASSIFICATION INPUT"
    )


    print(
        clean_text
    )


    # =================================================
    # LOAD CLASSIFIER
    # =================================================

    print_section(
        "2. MODEL"
    )


    print(
        f"Model: {MODEL_DIR}"
    )

    print(
        f"Evaluation: {EVAL_DIR}"
    )

    print(
        "\nModel yükleniyor..."
    )


    classifier = (
        HybridDocumentClassifier(
            model_dir=str(
                MODEL_DIR
            ),
            eval_dir=str(
                EVAL_DIR
            ),
        )
    )


    # =================================================
    # RUN CLASSIFICATION
    # =================================================

    start_time = (
        time.perf_counter()
    )


    raw_result = (
        classifier.predict(
            clean_text
        )
    )


    elapsed = (
        time.perf_counter()
        - start_time
    )


    # =================================================
    # RAW RESULT
    # =================================================

    print_section(
        "3. RAW CLASSIFICATION RESULT"
    )


    pretty_print(
        raw_result
    )


    # =================================================
    # NORMALIZED RESULT
    # نفس orchestrator
    # =================================================

    classification_result = {

        "label": (
            raw_result.get(
                "final_label"
            )
            or raw_result.get(
                "label"
            )
            or raw_result.get(
                "bert_raw_label"
            )
            or "unknown"
        ),

        "confidence": float(
            raw_result.get(
                "confidence",
                0.0,
            )
            or 0.0
        ),

        "bert_raw_label": (
            raw_result.get(
                "bert_raw_label"
            )
        ),

        "decision_reason": (
            raw_result.get(
                "decision_reason"
            )
        ),

        "matched_rules": (
            raw_result.get(
                "matched_rules",
                [],
            )
        ),

        "top_probabilities": (
            raw_result.get(
                "top_probabilities",
                raw_result.get(
                    "top_probs",
                    {},
                ),
            )
        ),
    }


    # =================================================
    # FINAL RESULT
    # =================================================

    print_section(
        "4. FINAL CLASSIFICATION"
    )


    print(
        f"Label      : "
        f"{classification_result['label']}"
    )

    print(
        f"Confidence : "
        f"{classification_result['confidence']:.4f}"
    )

    print(
        f"BERT Label : "
        f"{classification_result['bert_raw_label']}"
    )

    print(
        f"Reason     : "
        f"{classification_result['decision_reason']}"
    )


    # =================================================
    # MATCHED RULES
    # =================================================

    print_section(
        "5. MATCHED RULES"
    )


    matched_rules = (
        classification_result[
            "matched_rules"
        ]
    )


    if matched_rules:

        for rule in matched_rules:

            print(
                f"- {rule}"
            )

    else:

        print(
            "Kural eşleşmesi yok."
        )


    # =================================================
    # TOP PROBABILITIES
    # =================================================

    print_section(
        "6. TOP PROBABILITIES"
    )


    top_probs = (
        classification_result[
            "top_probabilities"
        ]
    )


    for label, probability in (
        top_probs.items()
    ):

        print(
            f"{label:<25} "
            f"{probability:.4f}"
        )


    # =================================================
    # TIMING
    # =================================================

    print_section(
        "7. TIMING"
    )


    print(
        f"Classification süresi: "
        f"{elapsed:.2f} saniye"
    )


    # =================================================
    # SAVE RESULT
    # =================================================

    output_dir = (
        PROJECT_ROOT
        / "tests"
        / "agents"
        / "output"
        / "classification"
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    output_file = (
        output_dir
        / "test_classification.json"
    )


    output_file.write_text(

        json.dumps(
            classification_result,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),

        encoding="utf-8",
    )


    # =================================================
    # COMPLETED
    # =================================================

    print_section(
        "CLASSIFICATION TEST COMPLETED"
    )


    print(
        "Sonuç kaydedildi:"
    )

    print(
        output_file
    )


if __name__ == "__main__":
    main()