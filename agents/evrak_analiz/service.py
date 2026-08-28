from typing import Dict, Any, Optional

from .schema import (
    MasterDocumentPipelineOutput,
    DocumentInfo,
    OCRBlock,
    OCRVision,
    EvrakAnalysisResult,
    ValidationBlock,
)

from .agent import EvrakAnalizAgent
from .validator import EvrakValidator

class EvrakAnalysisService:
    def __init__(self, llm_client):
      
        self.agent = EvrakAnalizAgent(llm_client)
        self.validator = EvrakValidator()

    def process_document(
        self,
        document_info_dict: Dict[str, Any],
        ocr_dict: Dict[str, Any],
        classification_result: Optional[Dict[str, Any]] = None
    ) -> MasterDocumentPipelineOutput:
        
        analysis_result: EvrakAnalysisResult = self.agent.analyze(
            ocr_data=ocr_dict,
            classification_result=classification_result
        )

        raw_text = ocr_dict.get("text", "")
        validation_result: ValidationBlock = self.validator.validate_analysis(
            analysis=analysis_result,
            raw_ocr_text=raw_text
        )

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

        return MasterDocumentPipelineOutput(
            success=True,
            document_info=doc_info,
            ocr=ocr_block,
            evrak_analysis=analysis_result,
            rag=None,             
            routing=None,         
            official_writing=None,
            validation=validation_result
        )