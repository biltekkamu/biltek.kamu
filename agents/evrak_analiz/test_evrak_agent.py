import json
import os
from langchain_openai import ChatOpenAI
from .service import EvrakAnalysisService

def run_test():
    print("🔄 Evrak Analiz için llm-fast servisine bağlanılıyor...")
    
    llm = ChatOpenAI(
    model="llm-fast",
    api_key=os.getenv("EVREN_API_KEY"),
    base_url="https://evren-llmapi.ssyz.org.tr/v1",
    temperature=0.0
)

    service = EvrakAnalysisService(llm_client=llm)

    mock_doc_info = {
        "document_id": "DOC_2026_TEST",
        "file_name": "izin_talebi_ornegi.pdf",
        "file_type": "pdf",
        "page_count": 1,
        "language": "tr"
    }

    mock_ocr = {
        "text": "T.C. İÇİŞLERİ BAKANLIĞINA\nPersonel Genel Müdürlüğü\n\nKurumunuzda 12345 sicil numarası ile görev yapmaktayım. 01.09.2026 tarihinden itibaren 10 günlük yıllık iznimi kullanmak istiyorum. Gereğini arz ederim.\n\nİsim: Ahmet Yılmaz\nTarih: 15.08.2026",
        "pages": [1],
        "parsed_metadata": {
            "tarih": "15.08.2026",
            "konu": "Yıllık İzin Talebi",
            "recipient": "T.C. İÇİŞLERİ BAKANLIĞINA"
        },
        "tables": [],
        "vision": {
            "has_signature": True,
            "has_stamp": False
        }
    }

    mock_classification = {
        "label": "dilekce",
        "confidence": 0.95
    }

    print("🚀 Belge llm-fast modeline gonderiliyor...")
    result = service.process_document(
        document_info_dict=mock_doc_info,
        ocr_dict=mock_ocr,
        classification_result=mock_classification
    )

    print("\n✅ Analiz başarıyla tamamlandı! Nihai JSON çıktısı:")
    print(result.model_dump_json(indent=2))

if __name__ == "__main__":
    run_test()