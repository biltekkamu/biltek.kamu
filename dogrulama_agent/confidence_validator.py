from typing import List, Tuple
from models import ValidationIssue, Severity

class ConfidenceCalculator:
    BASE_CONFIDENCE = 0.98
    HIGH_PENALTY = 0.35
    MEDIUM_PENALTY = 0.15
    LOW_PENALTY = 0.05

    @classmethod
    def calculate(cls, issues: List[ValidationIssue]) -> Tuple[float, str]:
        confidence = cls.BASE_CONFIDENCE
        has_high_severity = False

        for issue in issues:
            if issue.severity == Severity.HIGH:
                confidence -= cls.HIGH_PENALTY
                has_high_severity = True
            elif issue.severity == Severity.MEDIUM:
                confidence -= cls.MEDIUM_PENALTY
            elif issue.severity == Severity.LOW:
                confidence -= cls.LOW_PENALTY

        confidence = max(0.0, min(1.0, round(confidence, 2)))

        if has_high_severity or confidence < 0.50:
            status = "invalid"
        elif len(issues) > 0 or confidence < 0.85:
            status = "warning"
        else:
            status = "valid"

        return confidence, status