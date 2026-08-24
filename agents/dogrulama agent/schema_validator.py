from typing import List, Dict, Any
from models import ValidationIssue, IssueType, Severity

class SchemaValidator:
    @staticmethod
    def validate(payload: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        if not isinstance(payload, dict):
            return [
                ValidationIssue(
                    field="root",
                    type=IssueType.SCHEMA_ERROR,
                    severity=Severity.HIGH,
                    message="Ana JSON yapısı bir nesne (dict) olmalıdır."
                )
            ]

        for block in ["document_info", "ocr", "evrak_analysis"]:
            val = payload.get(block)
            if val is not None and not isinstance(val, dict):
                issues.append(
                    ValidationIssue(
                        field=block,
                        type=IssueType.SCHEMA_ERROR,
                        severity=Severity.HIGH,
                        message=f"'{block}' alanı JSON nesnesi olmalıdır."
                    )
                )

        analysis = payload.get("evrak_analysis")
        if isinstance(analysis, dict):
            conf = analysis.get("analysis_confidence")
            if conf is not None and not (isinstance(conf, (int, float)) and 0.0 <= conf <= 1.0):
                issues.append(
                    ValidationIssue(
                        field="evrak_analysis.analysis_confidence",
                        type=IssueType.SCHEMA_ERROR,
                        severity=Severity.MEDIUM,
                        message="analysis_confidence 0.0 ile 1.0 arasında olmalıdır."
                    )
                )

        return issues