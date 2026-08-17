def detect_route(text=None, file=None):
    """
    Kullanıcının giriş tipine göre hangi akışın çalışacağını belirler.
    """

    has_text = text is not None and str(text).strip() != ""
    has_file = file is not None

    if has_text and not has_file:
        return "question"

    if has_file and not has_text:
        return "document"

    if has_file and has_text:
        return "document_question"

    return "invalid"


if __name__ == "__main__":
    print(detect_route(
        text="Uyuşturucu madde ticaretinin cezası nedir?"
    ))

    print(detect_route(
        file="test.pdf"
    ))

    print(detect_route(
        text="Bu evrak hangi suçla ilgili?",
        file="test.pdf"
    ))

    print(detect_route())