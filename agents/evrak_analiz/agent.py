import json
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage

from .schema import EvrakAnalysisResult, DocumentTypeResult
from .prompt import EVRAK_ANALYSIS_SYSTEM_PROMPT
from .context_builder import ContextBuilder

class EvrakAnalizAgent:
    def __init__(self, llm_client):
      
        self.llm_structured = llm_client.with_structured_output(EvrakAnalysisResult)

    def analyze(self, ocr_data: Dict[str, Any], classification_result: Optional[Dict[str, Any]] = None) -> EvrakAnalysisResult:
        clean_text = ocr_data.get("text", "").strip()

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

        context = ContextBuilder.build_analysis_context(ocr_data, classification_result)

        response: EvrakAnalysisResult = self.llm_structured.invoke([
            SystemMessage(content=EVRAK_ANALYSIS_SYSTEM_PROMPT),
            HumanMessage(content=context)
        ])

        if classification_result and classification_result.get("confidence", 0) > 0.85:
            response.document_type.label = classification_result.get("label", response.document_type.label)
            response.document_type.confidence = classification_result.get("confidence", response.document_type.confidence)

        return response