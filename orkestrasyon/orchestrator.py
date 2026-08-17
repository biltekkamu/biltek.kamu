from router import detect_route
from state import create_state
from mock_agents import (
    mock_ocr,
    mock_analysis,
    mock_rag,
    mock_resmi_yazi,
    mock_birim_yonlendirme,
)


def process_input(text=None, file=None):
    # 1. Girdi türünü belirle
    route = detect_route(text=text, file=file)

    if route == "invalid":
        return {
            "status": "error",
            "message": "Geçerli bir giriş bulunamadı."
        }

    # 2. State oluştur
    state = create_state(
        input_type=route,
        document_id="doc_001" if file else None,
        user_question=text,
        file_path=file
    )

    # ------------------------------------------------
    # CASE 1: Sadece soru
    # ------------------------------------------------
    if route == "question":
        state.current_step = "mevzuat_rag"

        rag_result = mock_rag(
            analysis={},
            question=text
        )

        state.rag_result = rag_result
        state.status = "completed"

        return {
            "status": state.status,
            "route": route,
            "rag": rag_result
        }

    # ------------------------------------------------
    # CASE 2 + 3: Belge / Belge + Soru
    # ------------------------------------------------

    # OCR
    state.current_step = "ocr"

    ocr_result = mock_ocr(file)
    state.raw_text = ocr_result["raw_text"]

    # Evrak Analiz
    state.current_step = "evrak_analiz"

    analysis_result = mock_analysis(state.raw_text)
    state.analysis = analysis_result

    # Eksik bilgi kontrolü
    missing_info = analysis_result.get(
        "missing_information",
        []
    )

    state.missing_information = missing_info

    if missing_info:
        state.status = "waiting_for_information"
        state.current_step = "missing_information"

        return {
            "status": state.status,
            "route": route,
            "document_id": state.document_id,
            "missing_information": missing_info
        }

    # RAG
    state.current_step = "mevzuat_rag"

    rag_result = mock_rag(
        analysis=analysis_result,
        question=text if route == "document_question" else None
    )

    state.rag_result = rag_result

    # Resmî Yazı
    state.current_step = "resmi_yazi"

    resmi_yazi_result = mock_resmi_yazi(
        analysis_result,
        rag_result
    )

    state.official_letter = resmi_yazi_result

    # Birim Yönlendirme
    state.current_step = "birim_yonlendirme"

    routing_result = mock_birim_yonlendirme(
        analysis_result,
        rag_result
    )

    state.routing_result = routing_result

    # Final
    state.current_step = "completed"
    state.status = "completed"

    return {
        "status": state.status,
        "route": route,
        "document_id": state.document_id,
        "analysis": state.analysis,
        "rag": state.rag_result,
        "official_letter": state.official_letter,
        "routing": state.routing_result
    }


if __name__ == "__main__":

    print("\n===== TEST 1: QUESTION =====")
    result1 = process_input(
        text="Uyuşturucu madde ticaretinin cezası nedir?"
    )
    print(result1)

    print("\n===== TEST 2: DOCUMENT =====")
    result2 = process_input(
        file="test.pdf"
    )
    print(result2)

    print("\n===== TEST 3: DOCUMENT + QUESTION =====")
    result3 = process_input(
        text="Bu evrak hangi suçla ilgili?",
        file="test.pdf"
    )
    print(result3)

    print("\n===== TEST 4: INVALID =====")
    result4 = process_input()
    print(result4)