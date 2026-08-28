def mock_ocr(file_path):
    return {
        "raw_text": "Uyuşturucu madde ticareti yapıldığına ilişkin ihbar bulunmaktadır."
    }


def mock_analysis(raw_text):
    return {
        "document_type": "İhbar",
        "subject": "Uyuşturucu madde ticareti",
        "summary": "Uyuşturucu madde ticareti yapıldığı bildirilmektedir.",
        "missing_information": []
    }


def mock_rag(analysis, question=None):
    return {
        "answer": "Belge uyuşturucu madde ticareti kapsamında değerlendirilmiştir.",
        "sources": [
            {
                "law_name": "Türk Ceza Kanunu",
                "article": "Madde 188"
            }
        ]
    }


def mock_resmi_yazi(analysis, rag_result):
    return {
        "letter_type": "Bilgilendirme Yazısı",
        "draft": "İlgili mevzuat kapsamında gerekli değerlendirme yapılmıştır."
    }


def mock_birim_yonlendirme(analysis, rag_result):
    return {
        "recommended_unit": "Ceza İşleri Birimi",
        "reason": "Belge ceza hukuku kapsamında uyuşturucu madde ticareti ile ilgilidir.",
        "confidence": 0.95
    }


if __name__ == "__main__":

    ocr = mock_ocr("test.pdf")
    print("OCR:")
    print(ocr)

    analysis = mock_analysis(ocr["raw_text"])
    print("\nANALYSIS:")
    print(analysis)

    rag = mock_rag(analysis)
    print("\nRAG:")
    print(rag)

    resmi = mock_resmi_yazi(analysis, rag)
    print("\nRESMI YAZI:")
    print(resmi)

    birim = mock_birim_yonlendirme(analysis, rag)
    print("\nBIRIM:")
    print(birim)