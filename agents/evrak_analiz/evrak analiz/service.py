from typing import Dict, Any, Optional

from schema import (
    MasterDocumentPipelineOutput,
    DocumentInfo,
    OCRBlock,
    OCRVision,
    EvrakAnalysisResult,
    ValidationBlock
)
from agent import EvrakAnalizAgent
from validator import EvrakValidator

class EvrakAnalysisService:
    def __init__(self, llm_client):
        """
        تهيئة الخدمة مع الـ LLM المعتمد
        """
        self.agent = EvrakAnalizAgent(llm_client)
        self.validator = EvrakValidator()

    def process_document(
        self,
        document_info_dict: Dict[str, Any],
        ocr_dict: Dict[str, Any],
        classification_result: Optional[Dict[str, Any]] = None
    ) -> MasterDocumentPipelineOutput:
        """
        تنفيذ مسار التحليل الدلالي بالكامل وإنتاج كائن JSON النهائي الموحد
        """
        # 1. تشغيل الوكيل واستخراج المعنى والكيانات
        analysis_result: EvrakAnalysisResult = self.agent.analyze(
            ocr_data=ocr_dict,
            classification_result=classification_result
        )

        # 2. التحقق من صحة وموثوقية التحليل
        raw_text = ocr_dict.get("text", "")
        validation_result: ValidationBlock = self.validator.validate_analysis(
            analysis=analysis_result,
            raw_ocr_text=raw_text
        )

        # 3. تجهيز كائنات الـ OCR و Vision المطابقة للمخطط
        vision_data = ocr_dict.get("vision", {})
        ocr_block = OCRBlock(
            text=ocr_dict.get("text", ""),
            pages=ocr_dict.get("pages", []),
            parsed_metadata=ocr_dict.get("parsed_metadata", {}),
            tables=ocr_dict.get("tables", []),
            vision=OCRVision(
                has_signature=vision_data.get("has_signature", False),
                has_stamp=vision_data.get("has_stamp", False)
            )
        )

        doc_info = DocumentInfo(
            document_id=document_info_dict.get("document_id", "doc_001"),
            file_name=document_info_dict.get("file_name", "unknown.pdf"),
            file_type=document_info_dict.get("file_type", "pdf"),
            page_count=document_info_dict.get("page_count", 1),
            language=document_info_dict.get("language", "tr")
        )

        # 4. بناء النتيجة النهائية الكاملة للمشروع
        return MasterDocumentPipelineOutput(
            success=True,
            document_info=doc_info,
            ocr=ocr_block,
            evrak_analysis=analysis_result,
            rag=None,             # مخصص للمرحلة التالية (RAG Agent)
            routing=None,         # مخصص لوكيل التوجيه (Birim Yönlendirme)
            official_writing=None,# مخصص لوكيل كتابة الخطابات الرسمية
            validation=validation_result
        )