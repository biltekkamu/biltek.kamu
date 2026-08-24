from typing import Dict, Any, List
from models import ValidationBlock, ValidationIssue
from schema_validator import SchemaValidator
from required_fields_validator import RequiredFieldsValidator
from grounding_validator import GroundingValidator
from classification_validator import ClassificationValidator
from routing_validator import RoutingValidator
from rag_validator import RAGValidator
from semantic_validator import SemanticValidator
from confidence_validator import ConfidenceCalculator

class DocumentValidationService:
    def __init__(self, llm_client=None):
        self.schema_validator = SchemaValidator()
        self.required_fields_validator = RequiredFieldsValidator()
        self.grounding_validator = GroundingValidator()
        self.classification_validator = ClassificationValidator()
        self.routing_validator = RoutingValidator()
        self.rag_validator = RAGValidator()
        self.semantic_validator = SemanticValidator(llm_client=llm_client)

    def validate_document(self, final_json: Dict[str, Any]) -> ValidationBlock:
        issues: List[ValidationIssue] = []

        # 1. فحص البنية والحقول المطلوبة
        issues.extend(self.schema_validator.validate(final_json))
        issues.extend(self.required_fields_validator.validate(final_json))

        # 2. فحص مطابقة الكيانات
        ocr_block = final_json.get("ocr", {}) if isinstance(final_json.get("ocr"), dict) else {}
        ocr_text = ocr_block.get("text", "")
        evrak_analysis = final_json.get("evrak_analysis", {}) if isinstance(final_json.get("evrak_analysis"), dict) else {}

        if evrak_analysis and ocr_text:
            issues.extend(self.grounding_validator.validate(ocr_text, evrak_analysis))

        # 3. فحص التصنيف والتوجيه والـ RAG
        issues.extend(self.classification_validator.validate(ocr_text, evrak_analysis))
        issues.extend(self.routing_validator.validate(final_json.get("routing", {}), evrak_analysis))
        issues.extend(self.rag_validator.validate(final_json.get("rag", {})))

        # 4. الفحص الدلالي بواسطة LLM
        issues.extend(self.semantic_validator.validate(final_json))

        # 5. الحساب النهائي للثقة والحالة
        confidence, status = ConfidenceCalculator.calculate(issues)

        return ValidationBlock(
            status=status,
            issues=issues,
            confidence=confidence
        )