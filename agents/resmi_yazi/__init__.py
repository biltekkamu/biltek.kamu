from .agent import (
    ResmiYaziAgent,              # الكلاس الرئيسي للـResmi Yazı Agent
    determine_writing_type,      # تحديد نوع الكتاب من الـStructured Data
    generate_official_writing,   # الواجهة العامة لتشغيل الـAgent
)
from .context_builder import (
    prepare_official_writing_input,  # تحويل بيانات الـAgents السابقة إلى Structured Data
    render_context,                  # تحويل الـStructured Data إلى Context للـLLM
)
from .schema import (
    OfficialWritingAgentResult,    # الشكل النهائي لنتيجة الـAgent
    OfficialWritingInput,          # شكل البيانات الداخلة للـAgent
    OfficialWritingLLMResponse,    # شكل رد الـLLM: body فقط
    OfficialWritingPayload,        # بيانات الكتاب النهائي
    OfficialWritingValidation,     # نتيجة الـValidation
)

__all__ = [
    "ResmiYaziAgent",              # تصدير الـAgent الرئيسي
    "determine_writing_type",      # تصدير تحديد نوع الكتاب
    "generate_official_writing",   # تصدير دالة التوليد

    "prepare_official_writing_input",  # تصدير بناء الـStructured Data
    "render_context",                  # تصدير بناء الـContext

    "OfficialWritingAgentResult",    # تصدير Schema النتيجة النهائية
    "OfficialWritingInput",          # تصدير Schema الإدخال
    "OfficialWritingLLMResponse",    # تصدير Schema رد الـLLM
    "OfficialWritingPayload",        # تصدير Payload الكتاب
    "OfficialWritingValidation",     # تصدير نتيجة التحقق
]