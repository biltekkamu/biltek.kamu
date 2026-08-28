import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from validator_service import DocumentValidationService

def test_full_valid_document():
    service = DocumentValidationService()

    payload = {
        "success": True,
        "document_info": {
            "document_id": "DOC-2026-001",
            "file_name": "personel_yillik_izin_dilekcesi.pdf",
            "file_type": "pdf",
            "page_count": 1,
            "language": "tr"
        },
        "ocr": {
            "text": "T.C. İÇİŞLERİ BAKANLIĞINA\nPersonel İşleri Dairesi Başkanlığına\n\nKurumunuzda 54321 sicil numarası ile görev yapmaktayım. 15.08.2026 tarihinden itibaren 10 günlük yıllık iznimi kullanmak istiyorum. Gereğini arz ederim.\n\nAhmet Yılmaz\nİmza",
            "pages": [1],
            "parsed_metadata": {
                "tarih": "15.08.2026",
                "konu": "Yıllık İzin Talebi"
            },
            "tables": [],
            "vision": {
                "has_signature": True,
                "has_stamp": False
            }
        },
        "evrak_analysis": {
            "document_type": {
                "label": "dilekce",
                "confidence": 0.96
            },
            "topic": "Yıllık İzin Talebi",
            "purpose": "10 günlük yıllık izin kullanma talebi",
            "intent": "izin_talebi",
            "summary": "Ahmet Yılmaz, 15.08.2026 tarihinden itibaren 10 gün yıllık izin talep etmektedir.",
            "entities": {
                "name": "Ahmet Yılmaz",
                "sicil": "54321",
                "tarih": "15.08.2026"
            },
            "key_information": {
                "izin_turu": "yillik",
                "gun_sayisi": "10"
            },
            "document_structure": {
                "header_found": True,
                "footer_found": True
            },
            "important_points": [
                "15.08.2026 başlangıç tarihi",
                "10 gün süre"
            ],
            "missing_information": [],
            "analysis_confidence": 0.95
        },
        "routing": {
            "selected_department": "Personel İşleri Dairesi",
            "reason": "Belge personel yıllık izin talebini içermektedir.",
            "confidence": 0.94
        },
        "rag": {
            "query": "Memurların yıllık izin hakkı nedir?",
            "answer": "657 sayılı Devlet Memurları Kanunu Madde 102 uyarınca hizmeti 1 yıldan 10 yıla kadar olanlar için 20 gündür.",
            "sources": ["657 Sayılı DMK Madde 102"]
        },
        "official_writing": {
            "generated": True,
            "text": "İlgili personelin izin talebi kayıt altına alınmıştır."
        }
    }

    result = service.validate_document(payload)
    print("\n--- 1. FULL VALID DOCUMENT TEST RESULT ---")
    print(result.model_dump_json(indent=2))

    assert result.status == "valid"
    assert len(result.issues) == 0
    assert result.confidence >= 0.85
    print("✅ test_full_valid_document PASSED!")

if __name__ == "__main__":
    test_full_valid_document()