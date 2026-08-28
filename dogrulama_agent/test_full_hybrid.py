import json
from langchain_ollama import ChatOllama
from validator_service import DocumentValidationService

def run_hard_case_test():
    llm = ChatOllama(
        model="qwen2.5:7b",
        temperature=0.0
    )

    service = DocumentValidationService(llm_client=llm)

    payload = {
        "success": True,
        "document_info": {
            "document_id": "hard_001",
            "file_name": "burs_karari.pdf",
            "file_type": "pdf",
            "page_count": 1,
            "language": "tr"
        },
        "ocr": {
            "text": "BURS BAŞVURUSU DEĞERLENDİRME SONUCU Ahmet Yılmaz tarafından yapılan burs başvurusu komisyon tarafından değerlendirilmiş ve başvurunun kabul edilmesine karar verilmiştir. Karar Tarihi: 18.08.2026 Karar No: 2026/45",
            "pages": [],
            "parsed_metadata": {},
            "tables": [],
            "vision": {}
        },
        "evrak_analysis": {
            "document_type": {
                "label": "basvuru_belgesi",
                "confidence": 0.91
            },
            "summary": "Ahmet Yılmaz'ın burs başvurusu kabul edilmiştir.",
            "topic": "Burs başvurusu sonucu",
            "purpose": "Burs başvurusuna ilişkin alınan kararı bildirmek",
            "intent": "notification",
            "entities": {
                "name": "Ahmet Yılmaz",
                "decision_number": "2026/45"
            },
            "key_information": {},
            "document_structure": {},
            "important_points": [],
            "missing_information": [],
            "analysis_confidence": 0.94
        },
        "rag": {
            "query": None,
            "answer": None,
            "results": [],
            "sources": []
        },
        "routing": {
            "selected_department": "Öğrenci İşleri",
            "reason": "Burs işlemleriyle ilgilidir.",
            "confidence": 0.9
        },
        "official_writing": {
            "generated": False,
            "text": None
        },
        "validation": {
            "status": None,
            "issues": [],
            "confidence": None
        }
    }


    validation_result = service.validate_document(payload)

    payload["validation"] = validation_result.model_dump()

    print("=================== VALIDATION ===================")
    print(json.dumps(payload["validation"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run_hard_case_test()