from typing import Any

from .schemas import BirimYonlendirmeResult


ALLOWED_DEPARTMENTS = [
    "Ceza İşleri Birimi",
    "Hukuk İşleri Birimi",
    "Mali Hizmetler Birimi",
    "İnsan Kaynakları Birimi",
    "Evrak Kayıt Birimi",
    "Bilgi İşlem Birimi",
]


def route_unit(
    evrak_analysis: dict[str, Any],
    rag_result: dict[str, Any],
) -> BirimYonlendirmeResult:

    document_type = evrak_analysis.get(
        "document_type",
        {},
    )

    if isinstance(document_type, dict):
        document_type_label = str(
            document_type.get(
                "label",
                "",
            )
        ).lower()
    else:
        document_type_label = str(
            document_type
        ).lower()

    topic = str(
        evrak_analysis.get(
            "topic",
            "",
        )
    ).lower()

    purpose = str(
        evrak_analysis.get(
            "purpose",
            "",
        )
    ).lower()

    intent = str(
        evrak_analysis.get(
            "intent",
            "",
        )
    ).lower()

    summary = str(
        evrak_analysis.get(
            "summary",
            "",
        )
    ).lower()

    rag_answer = str(
        rag_result.get(
            "answer",
            "",
        )
    ).lower()

    combined_text = " ".join(
        [
            document_type_label,
            topic,
            purpose,
            intent,
            summary,
            rag_answer,
        ]
    )

    # İnsan Kaynakları
    if any(
        keyword in combined_text
        for keyword in [
            "izin",
            "yıllık izin",
            "personel",
            "memur",
            "işçi",
            "özlük",
        ]
    ):
        return BirimYonlendirmeResult(
            selected_department="İnsan Kaynakları Birimi",
            reason=(
                "Belge personel veya izin işlemleriyle ilgilidir."
            ),
            confidence=0.95,
        )

    # Ceza İşleri
    if any(
        keyword in combined_text
        for keyword in [
            "uyuşturucu",
            "suç",
            "ceza",
            "hırsızlık",
            "yaralama",
            "dolandırıcılık",
        ]
    ):
        return BirimYonlendirmeResult(
            selected_department="Ceza İşleri Birimi",
            reason=(
                "Belge ceza hukuku kapsamında değerlendirilmiştir."
            ),
            confidence=0.95,
        )

    # Mali Hizmetler
    if any(
        keyword in combined_text
        for keyword in [
            "vergi",
            "ödeme",
            "borç",
            "mali",
            "bütçe",
            "harcama",
        ]
    ):
        return BirimYonlendirmeResult(
            selected_department="Mali Hizmetler Birimi",
            reason=(
                "Belge mali işlemlerle ilgilidir."
            ),
            confidence=0.90,
        )

    # Bilgi İşlem
    if any(
        keyword in combined_text
        for keyword in [
            "yazılım",
            "sistem",
            "sunucu",
            "ağ",
            "bilgi işlem",
        ]
    ):
        return BirimYonlendirmeResult(
            selected_department="Bilgi İşlem Birimi",
            reason=(
                "Belge bilgi işlem veya teknik sistemlerle ilgilidir."
            ),
            confidence=0.90,
        )

    # Hukuk İşleri
    if any(
        keyword in combined_text
        for keyword in [
            "dava",
            "itiraz",
            "hukuk",
            "hukuki",
            "sözleşme",
        ]
    ):
        return BirimYonlendirmeResult(
            selected_department="Hukuk İşleri Birimi",
            reason=(
                "Belge hukuki değerlendirme gerektirmektedir."
            ),
            confidence=0.85,
        )

    return BirimYonlendirmeResult(
        selected_department=None,
        reason=(
            "Belge güvenilir şekilde bir birime "
            "yönlendirilemedi."
        ),
        confidence=0.0,
    )
if __name__ == "__main__":

    neutral_analysis = {
        "document_type": {
            "label": "belge",
            "confidence": 0.90,
        },
        "topic": "Genel başvuru",
        "purpose": "Başvurunun değerlendirilmesi",
        "intent": "genel_basvuru",
        "summary": "Belge genel bir başvuru içermektedir.",
        "missing_information": [],
        "analysis_confidence": 0.90,
    }

    criminal_rag = {
        "answer": (
            "Belge uyuşturucu madde ticareti ve ceza hukuku "
            "kapsamında değerlendirilmiştir."
        ),
        "sources": [
            {
                "law_name": "5237 Türk Ceza Kanunu",
                "article": "Madde 188",
            }
        ],
        "retrieved_chunks": 5,
    }

    result = route_unit(
        evrak_analysis=neutral_analysis,
        rag_result=criminal_rag,
    )

    print("\n===== RAG DEPENDENCY TEST =====")
    print(result.model_dump())