from __future__ import annotations  # السماح باستخدام Type Hints بشكل مرن

from typing import Any, Mapping, Optional  # أنواع البيانات المستخدمة

from .schema import OfficialWritingInput  # الـSchema الموحد الذي سيرسل للـLLM


def _clean(value: Any) -> Any:
    # تنظيف أي قيمة قبل وضعها داخل الـStructured Data

    if value is None:
        return None  # تجاهل القيم الفارغة

    if isinstance(value, str):
        value = value.strip()  # إزالة المسافات الزائدة
        return value or None  # إذا أصبحت فارغة نرجع None

    if isinstance(value, Mapping):
        cleaned = {}  # إنشاء Dictionary جديد للقيم المنظفة

        for key, item in value.items():
            cleaned_value = _clean(item)  # تنظيف كل قيمة داخله

            if cleaned_value is not None:
                cleaned[str(key)] = cleaned_value  # الاحتفاظ بالقيم الموجودة فقط

        return cleaned  # إرجاع الـDictionary المنظف

    if isinstance(value, (list, tuple)):
        return [
            cleaned_value
            for item in value
            if (cleaned_value := _clean(item)) is not None
        ]  # تنظيف عناصر القوائم وإزالة الفارغ منها

    return value  # إرجاع باقي أنواع البيانات كما هي


def _compact_rag(
    rag_result: Optional[Mapping[str, Any]],
) -> Optional[dict[str, Any]]:
    # تقليل RAG إلى المعلومات القانونية المفيدة فقط

    if not rag_result:
        return None  # إذا ما في RAG نرجع None

    answer = _clean(rag_result.get("answer"))  # أخذ نتيجة RAG الأساسية

    sources = rag_result.get("sources") or []  # أخذ المصادر القانونية

    compact_sources = []  # قائمة للمصادر بعد تنظيفها

    for source in sources:
        # المرور على كل مصدر قانوني

        if not isinstance(source, Mapping):
            continue  # تجاهل أي مصدر غير منظم

        item = {
            key: _clean(source.get(key))
            for key in (
                "document_name",
                "law_number",
                "madde",
            )
            if _clean(source.get(key)) is not None
        }  # الاحتفاظ فقط بمعلومات المصدر الموجودة

        if item:
            compact_sources.append(item)  # إضافة المصدر إذا كان يحتوي بيانات

    if answer is None and not compact_sources:
        return None  # إذا RAG فارغ فعلياً لا نرسله

    return {
        "answer": answer,
        "sources": compact_sources,
    }  # إرجاع RAG المنظم


def prepare_official_writing_input(
    evrak_analysis: Mapping[str, Any] | Any,
    rag_result: Optional[Mapping[str, Any]] = None,
    routing_result: Optional[Mapping[str, Any]] = None,
    ocr_result: Optional[Mapping[str, Any]] = None,
) -> OfficialWritingInput:
    # تجميع نتائج الـAgents السابقة وتحويلها إلى Structured Data واحد

    analysis = (
        evrak_analysis.model_dump()
        if hasattr(evrak_analysis, "model_dump")
        else dict(evrak_analysis or {})
    )  # تحويل Evrak Analysis إلى Dictionary

    routing = (
        routing_result.model_dump()
        if hasattr(routing_result, "model_dump")
        else dict(routing_result or {})
    )  # تحويل Routing إلى Dictionary

    ocr = (
        ocr_result.model_dump()
        if hasattr(ocr_result, "model_dump")
        else dict(ocr_result or {})
    )  # تحويل OCR إلى Dictionary

    # استخراج Metadata من OCR إذا كانت موجودة
    ocr_input = ocr.get("input") or {}
    metadata = ocr_input.get("metadata") or {}

    document_type = analysis.get("document_type")  # أخذ نوع الوثيقة من Evrak Analysis

    if isinstance(document_type, Mapping):
        document_type = document_type.get("label")  # استخراج label إذا كان النوع Object

    selected_department = routing.get("selected_department")  # أخذ الوحدة من Routing

    if selected_department is None:
        selected_department = routing.get("recommended_unit")  # دعم اسم الحقل البديل

    data = {
        # =========================
        # Evrak Analysis
        # =========================

        "document_type": _clean(document_type),  # نوع الوثيقة

        "topic": _clean(
            analysis.get("topic")
            or analysis.get("subject")
            or metadata.get("konu")
        ),  # موضوع الوثيقة

        "purpose": _clean(
            analysis.get("purpose")
        ),  # الغرض من الوثيقة

        "intent": _clean(
            analysis.get("intent")
        ),  # الـIntent

        "summary": _clean(
            analysis.get("summary")
        ),  # ملخص الوثيقة

        "entities": _clean(
            analysis.get("entities") or {}
        ),  # الكيانات المستخرجة

        "key_information": _clean(
            analysis.get("key_information") or {}
        ),  # المعلومات المهمة

        # =========================
        # OCR Metadata
        # =========================

        "sayi": _clean(metadata.get("sayi") or analysis.get("entities", {}).get("sayi")),
        "tarih": _clean(metadata.get("tarih") or analysis.get("entities", {}).get("tarih")),
        "recipient": _clean(metadata.get("muhatap") or analysis.get("entities", {}).get("muhatap")),

        # =========================
        # Routing
        # =========================

        "selected_department": _clean(
            selected_department
        ),  # الوحدة التي حددها Routing

        # =========================
        # RAG
        # =========================

        "rag": _compact_rag(
            rag_result
        ),  # الأساس القانوني القادم من RAG
    }

    # ملاحظة:
    # Sayى / Tarih / Kurum / Muhatap لا يتم توليدها هنا كقيم جديدة.
    # إذا كانت موجودة ضمن بيانات الـAgents، تبقى ضمن الـContext المرسل للـLLM
    # حتى يعرف أنها معلومات موجودة مسبقاً ولا يخترعها.

    return OfficialWritingInput(
        **data
    )  # تحويل البيانات إلى OfficialWritingInput


def render_context(
    data: OfficialWritingInput,
) -> str:
    # تحويل Structured Data إلى نص واضح يدخل إلى الـPrompt

    labels = {
        "document_type": "Belge Türü",  # نوع الوثيقة
        "topic": "Konu",  # الموضوع
        "purpose": "Amaç",  # الغرض
        "intent": "Intent",  # النية
        "summary": "Özet",  # الملخص
        "entities": "Varlıklar",  # الكيانات
        "key_information": "Önemli Bilgiler",  # المعلومات المهمة
        "sayi": "Sayı",  # رقم المعاملة
        "tarih": "Tarih",  # التاريخ
        "recipient": "Muhatap",  # الجهة
        "selected_department": "Yönlendirilen Birim",  # الوحدة المحددة
        "rag": "RAG Legal Basis",  # الأساس القانوني
    }

    lines = [
        "### RESMÎ YAZI İÇİN YAPILANDIRILMIŞ BAĞLAM ###"
    ]  # بداية الـContext

    for key, label in labels.items():
        # المرور على كل حقل موجود في الـStructured Data

        value = getattr(data, key, None)  # أخذ قيمة الحقل

        if value is not None and value != {}:
            lines.append(
                f"- {label}: {value}"
            )  # إضافة الحقل إلى الـContext

    lines.append(
        "### KULLANIM KURALLARI ###"
    )  # بداية قواعد استخدام البيانات

    lines.append(
        "Yalnızca yukarıdaki Structured Data ve mevcut RAG bilgilerini kullan."
    )  # منع اختراع معلومات خارج الـContext

    lines.append(
        "Context'te bulunmayan Sayı, Tarih, Kurum, Birim, kişi veya hukuki referans üretme."
    )  # منع اختراع البيانات الحساسة

    lines.append(
        "RAG mevcutsa yalnızca verilen hukuki dayanağı kullan."
    )  # استخدام الأساس القانوني الموجود فقط

    lines.append(
        "Template'in sabit bölümlerini oluşturma veya değiştirme."
    )  # منع الـLLM من إنشاء الـTemplate

    lines.append(
        "Yalnızca Template içinde kullanılacak BODY/METİN içeriğini üret."
    )  # تحديد مهمة الـLLM بالـBody فقط

    return "\n".join(lines)  # إرجاع الـContext النهائي