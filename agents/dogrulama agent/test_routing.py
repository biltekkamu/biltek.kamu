import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from validator_service import DocumentValidationService
from models import IssueType

def test_full_routing_conflict():
    service = DocumentValidationService()

    payload = {
        "success": True,
        "document_info": {
            "document_id": "DOC-2026-BURS",
            "file_name": "burs_basvuru_formu.pdf",
            "file_type": "pdf",
            "page_count": 1,
            "language": "tr"
        },
        "ocr": {
            "text": "İSTANBUL GELİŞİM ÜNİVERSİTESİ REKTÖRLÜĞÜNE\nÖğrenci No: 220101010. Maddi durum yetersizliğinden dolayı burs başvurusu yapmak istiyorum. Gereğini arz ederim.",
            "pages": [1],
            "parsed_metadata": {"tarih": "01.09.2026"},
            "tables": [],
            "vision": {"has_signature": True, "has_stamp": False}
        },
        "evrak_analysis": {
            "document_type": {"label": "dilekce", "confidence": 0.92},
            "topic": "Burs Başvurusu",
            "purpose": "Eğitim bursu talebi",
            "intent": "burs_talebi",
            "summary": "Öğrenci maddi durumundan dolayı burs başvurusunda bulunmaktadır.",
            "entities": {
                "student_number": "220101010"
            },
            "key_information": {"tur": "burs"},
            "analysis_confidence": 0.90
        },
        "routing": {
            "selected_department": "Bilgi İşlem Dairesi",  # توجيه متناقض صراحة مع موضوع المنحة
            "reason": "Sistem üzerinden yönlendirme yapıldı.",
            "confidence": 0.70
        },
        "rag": {
            "query": "Burs şartları nelerdir?",
            "answer": "Not ortalamasının en az 2.50 olması gerekmektedir.",
            "sources": ["Burs Yönetmeliği Md. 4"]
        },
        "official_writing": {
            "generated": True,
            "text": "Başvuru işleme alınmıştır."
        }
    }

    result = service.validate_document(payload)
    print("\n--- 3. FULL ROUTING CONFLICT TEST RESULT ---")
    print(result.model_dump_json(indent=2))

    assert result.status == "warning"
    routing_issues = [i for i in result.issues if i.type == IssueType.ROUTING_MISMATCH]
    assert len(routing_issues) > 0
    print("✅ test_full_routing_conflict PASSED!")

if __name__ == "__main__":
    test_full_routing_conflict()