from typing import List, Dict, Any
from models import ValidationIssue, IssueType, Severity

class RequiredFieldsValidator:
    REQUIRED_ROOT_BLOCKS = ["document_info", "ocr", "evrak_analysis"]

    @classmethod
    def validate(cls, payload: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        for block in cls.REQUIRED_ROOT_BLOCKS:
            if block not in payload or payload[block] is None:
                issues.append(
                    ValidationIssue(
                        field=block,
                        type=IssueType.MISSING_DATA,
                        severity=Severity.HIGH,
                        message=f"Temel blok eksik: '{block}'."
                    )
                )

        ocr = payload.get("ocr")
        if isinstance(ocr, dict):
            text = ocr.get("text")
            if not text or not str(text).strip():
                issues.append(
                    ValidationIssue(
                        field="ocr.text",
                        type=IssueType.MISSING_DATA,
                        severity=Severity.HIGH,
                        message="OCR metni bulunamadı."
                    )
                )

        analysis = payload.get("evrak_analysis")
        if isinstance(analysis, dict):
            if not analysis.get("document_type"):
                issues.append(
                    ValidationIssue(
                        field="evrak_analysis.document_type",
                        type=IssueType.MISSING_DATA,
                        severity=Severity.HIGH,
                        message="Belge türü (document_type) bilgisi eksik."
                    )
                )

        return issues