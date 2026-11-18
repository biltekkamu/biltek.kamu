import json
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage

from .schema import EvrakAnalysisResult, DocumentTypeResult
from .prompt import EVRAK_ANALYSIS_SYSTEM_PROMPT
from .context_builder import ContextBuilder

class EvrakAnalizAgent:
    def __init__(self, llm_client):
        """
        تهيئة الوكيل وربط الـ LLM مع Structured Output لضمان مخرجات Pydantic مطابقة للمخطط
        """
        self.llm_client = llm_client
        self.llm_structured = llm_client.with_structured_output(EvrakAnalysisResult)

    def analyze(self, ocr_data: Dict[str, Any], classification_result: Optional[Dict[str, Any]] = None) -> EvrakAnalysisResult:
        clean_text = ocr_data.get("text", "").strip()

        # معالجة استباقية في حال كان النص فارغاً أو تالفاً
        if len(clean_text) < 15:
            return EvrakAnalysisResult(
                document_type=DocumentTypeResult(
                    label=classification_result.get("label", "unknown") if classification_result else "unknown",
                    confidence=0.0
                ),
                topic="Okunamayan / Boş Belge",
                purpose="Metin içeriği tespit edilemedi.",
                intent="gecersiz_belge",
                summary="Belge içeriği okunamadı veya metin uzunluğu analiz için yetersiz.",
                entities={},
                key_information={},
                important_points=[],
                missing_information=["Tam Belge Metni"],
                analysis_confidence=0.0
            )

        # بناء سياق التحليل المنظم
        context = ContextBuilder.build_analysis_context(ocr_data, classification_result)

        # استدعاء النموذج اللغوي
        try:
            response: EvrakAnalysisResult = self.llm_structured.invoke([
                SystemMessage(content=EVRAK_ANALYSIS_SYSTEM_PROMPT),
                HumanMessage(content=context)
            ])
        except Exception as err:
            print(f"⚠️ [EvrakAnalizAgent Fallback]: {err}")
            metadata = ocr_data.get("parsed_metadata", {}) or {}
            response = EvrakAnalysisResult(
                document_type=DocumentTypeResult(
                    label=classification_result.get("label", "resmi_yazi") if classification_result else "resmi_yazi",
                    confidence=float(classification_result.get("confidence", 0.75)) if classification_result else 0.75,
                ),
                topic=metadata.get("konu") or "Resmi Belge Analizi",
                purpose="Belge içeriğinin değerlendirilmesi",
                intent="resmi_islem",
                summary=clean_text[:300],
                entities={k: v for k, v in metadata.items() if v},
                key_information={},
                important_points=[],
                missing_information=[],
                analysis_confidence=0.70,
            )

        # مواءمة نوع الوثيقة مع تنبؤ BERTurk إذا كانت ثقة BERTurk أعلى
        if classification_result and classification_result.get("confidence", 0) > 0.85:
            response.document_type.label = classification_result.get("label", response.document_type.label)
            response.document_type.confidence = classification_result.get("confidence", response.document_type.confidence)

        return response