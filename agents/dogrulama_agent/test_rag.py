import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from validator_service import DocumentValidationService
from models import IssueType, Severity

def test_full_rag_and_grounding_error():
    service = DocumentValidationService()

    payload = {
        "success": True,
        "document_info": {
            "document_id": "DOC-2026-HUKUK",
            "file_name": "savunma_yazisi.pdf",
            "file_type": "pdf",
            "page_count": 1,
            "language": "tr"
        },
        "ocr": {
            "text": "HUKUK MÜŞAVİRLİĞİNE\nKonu: Disiplin soruşturması savunmamdır. Belirtilen tarihte görev yerimdeydim. Arz ederim.\n\nAd Soyad: Mehmet Demir",
            "pages": [1],
            "parsed_metadata": {},
            "tables": [],
            "vision": {"has_signature": True, "has_stamp": False}
        },
        "evrak_analysis": {
            "document_type": {"label": "dilekce", "confidence": 0.88},
            "topic": "Disiplin Soruşturması Savunması",
            "purpose": "Hakkındaki iddialara karşı savunma sunmak",
            "intent": "savunma_verme",
            "summary": "Mehmet Demir disiplin soruşturması kapsamında savunmasını sunmuştur.",
            "entities": {
                "name": "Mehmet Demir",
                "fake_tc_kimlik": "99998888777"
            },
            "analysis_confidence": 0.85
        },
        "routing": {
            "selected_department": "Hukuk Müşavirliği",
            "reason": "Disiplin savunması hukuki inceleme gerektirir.",
            "confidence": 0.90
        },
        "rag": {
            "query": "Disiplin cezası itiraz süresi kaç gündür?",
            "answer": "Disiplin cezalarına itiraz süresi tebliğden itibaren 7 gündür.",
            "sources": [] 
        },
        "official_writing": {
            "generated": True,
            "text": "Savunma dosyasına eklenmiştir."
        }
    }

    result = service.validate_document(payload)
    print("\n--- 4. FULL RAG & GROUNDING TEST RESULT ---")
    print(result.model_dump_json(indent=2))

    rag_source_issues = [i for i in result.issues if i.type == IssueType.MISSING_SOURCE and i.severity == Severity.HIGH]
    grounding_issues = [i for i in result.issues if i.type == IssueType.ENTITY_GROUNDING_ERROR]

    assert len(rag_source_issues) > 0
    assert len(grounding_issues) > 0
    assert result.status in ["warning", "invalid"]
    print("✅ test_full_rag_and_grounding_error PASSED!")

if __name__ == "__main__":
    test_full_rag_and_grounding_error()