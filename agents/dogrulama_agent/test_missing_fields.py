import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from validator_service import DocumentValidationService
from models import IssueType, Severity

def test_full_missing_fields():
    service = DocumentValidationService()

    payload = {
        "success": False,
        "document_info": {
            "document_id": "DOC-2026-EMPTY",
            "file_name": "bozuk_tarama.pdf",
            "file_type": "pdf",
            "page_count": 0,
            "language": "tr"
        },
        "ocr": {
            "text": "",  # OCR فارغ
            "pages": [],
            "parsed_metadata": {},
            "tables": [],
            "vision": {}
        },
        "evrak_analysis": {
            "document_type": None,  # نوع الوثيقة مفقود
            "topic": "Bilinmiyor",
            "purpose": "",
            "intent": "",
            "summary": "",
            "entities": {},
            "analysis_confidence": 0.0
        },
        "routing": {
            "selected_department": None,
            "reason": None,
            "confidence": None
        },
        "rag": {
            "query": None,
            "answer": None,
            "sources": []
        },
        "official_writing": {
            "generated": False,
            "text": None
        }
    }

    result = service.validate_document(payload)
    print("\n--- 2. FULL MISSING FIELDS TEST RESULT ---")
    print(result.model_dump_json(indent=2))

    assert result.status == "invalid"
    high_issues = [i for i in result.issues if i.severity == Severity.HIGH and i.type == IssueType.MISSING_DATA]
    assert len(high_issues) >= 2  # ocr.text و document_type
    print("✅ test_full_missing_fields PASSED!")

if __name__ == "__main__":
    test_full_missing_fields()