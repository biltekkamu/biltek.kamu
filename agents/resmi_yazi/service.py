from __future__ import annotations  # السماح باستخدام Type Hints بشكل مرن

import json  # استخدام JSON لتحويل الرد النصي من الـLLM إلى بيانات منظمة
import os
from typing import Any, Mapping, Optional  # أنواع عامة للبيانات

from .prompt import SYSTEM_PROMPT, build_official_writing_prompt  # استيراد الـSystem Prompt وبناء Prompt النهائي
from .schema import (  # استيراد الـSchemas المستخدمة
    OfficialWritingInput,  # Structured Data الداخل إلى الـLLM
    OfficialWritingLLMResponse,  # شكل رد الـLLM
    OfficialWritingType,  # نوع الكتاب الرسمي
)

# إعداد البيانات الخاصة بالـ API كقيم افتراضية
DEFAULT_EVREN_API_KEY = os.getenv("EVREN_API_KEY", "sk-evren-team03-6409be56daaf89d55f82a4a9f12b10f1")
DEFAULT_EVREN_BASE_URL = os.getenv("EVREN_BASE_URL", "https://evren-llmapi.ssyz.org.tr/v1")


def get_evren_llm_client(
    model_name: str = "llm-large", # اسم الموديل المتاح في Evren API
    api_key: str = DEFAULT_EVREN_API_KEY,
    base_url: str = DEFAULT_EVREN_BASE_URL,
    temperature: float = 0.0,
) -> Any:
    """دالة مساعدة لإنشاء client متوافق مع Evren API عبر LangChain."""
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            timeout=60.0,
        )
    except ImportError:
        raise ImportError(
            "يرجى تثبيت مكتبة langchain-openai باستخدام: pip install langchain-openai"
        )


def _message_payload(system_prompt: str, human_prompt: str):
    # تجهيز الرسائل بالشكل الذي يستخدمه LangChain
    try:
        from langchain_core.messages import HumanMessage, SystemMessage  # استيراد أنواع رسائل LangChain

        return [
            SystemMessage(content=system_prompt),  # إرسال تعليمات النظام للـLLM
            HumanMessage(content=human_prompt),  # إرسال الـContext والطلب الفعلي للـLLM
        ]
    except ImportError:
        return human_prompt  # استخدام النص مباشرة إذا LangChain غير متوفر


def _coerce_response(raw: Any) -> OfficialWritingLLMResponse:
    # تحويل أي شكل يرجع من الـLLM إلى OfficialWritingLLMResponse

    if isinstance(raw, OfficialWritingLLMResponse):
        # إذا كان الرد أصلاً بالـSchema المطلوب
        return raw  # نرجعه مباشرة

    if hasattr(raw, "model_dump"):
        # إذا كان الرد Pydantic أو كائن يدعم model_dump
        return OfficialWritingLLMResponse.model_validate(
            raw.model_dump()  # تحويله إلى Dictionary ثم التحقق منه
        )

    if isinstance(raw, Mapping):
        # إذا كان الرد Dictionary أو Mapping
        return OfficialWritingLLMResponse.model_validate(raw)  # تحويله إلى الـSchema

    if hasattr(raw, "content"):
        # بعض نماذج LangChain ترجع AIMessage فيها content
        raw = raw.content  # استخراج النص الموجود داخل content

    if isinstance(raw, str):
        # إذا كان الرد نصاً عادياً
        text = raw.strip()  # إزالة المسافات الزائدة

        # تنظيف علامات التنسيق (Markdown Triple Backticks) في حال وجودها
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return OfficialWritingLLMResponse.model_validate(
                json.loads(text)  # تحويل JSON النصي إلى Object والتحقق من الـSchema
            )
        except Exception as exc:
            # إذا كان الرد ليس JSON صالحاً
            raise ValueError(
                "LLM yanıtı geçerli JSON/structured output değil."
            ) from exc  # إظهار خطأ واضح

    raise ValueError(
        "LLM yanıtı beklenen formatta değil."
    )  # رفض أي شكل غير مدعوم من رد الـLLM


class OfficialWritingGenerator:
    # هذا الكلاس هو نقطة الاتصال المباشرة مع الـLLM

    def __init__(self, llm_client: Optional[Any] = None):
        # إذا لم يتم تمرير client، يتم إنشاء واحد افتراضياً يتصل بـ Evren API
        if llm_client is None:
            llm_client = get_evren_llm_client()

        self.llm_client = llm_client  # تخزين الـLLM لاستخدامه في التوليد

    def generate(
        self,
        data: OfficialWritingInput,  # الـStructured Data القادم من context_builder
        writing_type: OfficialWritingType,  # نوع الكتاب الذي تم تحديده
    ) -> OfficialWritingLLMResponse:
        # ترجع النتيجة بالـSchema الخاص برد الـLLM

        prompt = build_official_writing_prompt(
            data,
            writing_type,
        )  # بناء الـPrompt اعتماداً على Structured Data ونوع الكتاب

        if hasattr(self.llm_client, "with_structured_output"):
            # التحقق إذا كان الـLLM يدعم Structured Output

            structured_llm = self.llm_client.with_structured_output(
                OfficialWritingLLMResponse
            )  # إجبار الـLLM على الالتزام بالـSchema

            response = structured_llm.invoke(
                _message_payload(
                    SYSTEM_PROMPT,  # تعليمات النظام
                    prompt,  # الـPrompt المبني من البيانات
                )
            )  # إرسال الطلب إلى الـLLM

        else:
            # إذا كان الرد نصياً مباشراً
            response = self.llm_client.invoke(
                _message_payload(SYSTEM_PROMPT, prompt)
            )

        return _coerce_response(response)  # تحويل الرد إلى OfficialWritingLLMResponse


def generate_official_writing(
    input_data: OfficialWritingInput,  # البيانات المنظمة
    writing_type: OfficialWritingType,  # نوع الكتاب
    llm_client: Optional[Any] = None,  # الـLLM (اختياري)
) -> OfficialWritingLLMResponse:
    # واجهة عامة منخفضة المستوى لتوليد الـBody

    return OfficialWritingGenerator(llm_client).generate(
        input_data,
        writing_type,
    )  # تشغيل الـGenerator وإرجاع نتيجة الـLLM