from typing import List, Dict, Any
from models import ValidationIssue, IssueType, Severity

class ClassificationValidator:
    # مؤشرات عامة قابلة للتوسع لأي صنف
    INDICATORS_MAP = {
        "fatura": ["fatura", "kdv", "vergi", "toplam", "tutar", "fatura no", "ödeme"],
        "dilekce": ["arz ederim", "talep", "bilgilerinize", "saygılarımla", "dilekçe", "gereğini"],
        "sozlesme": ["sözleşme", "taraf", "madde", "hüküm", "imza", "akdedilmiştir"],
        "tutanak": ["tutanak", "tespit", "imza altına", "saatinde", "tarihinde"]
    }

    @classmethod
    def validate(cls, ocr_text: str, evrak_analysis: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not isinstance(evrak_analysis, dict):
            return issues

        doc_type = evrak_analysis.get("document_type")
        if not isinstance(doc_type, dict):
            return issues

        label = str(doc_type.get("label", "")).lower()
        conf = doc_type.get("confidence", 1.0)

        # 1. فحص الثقة المنخفضة
        if isinstance(conf, (int, float)) and conf < 0.60:
            issues.append(
                ValidationIssue(
                    field="evrak_analysis.document_type.confidence",
                    type=IssueType.LOW_CONFIDENCE,
                    severity=Severity.MEDIUM,
                    message=f"Belge sınıflandırma güven skoru düşük ({conf:.2f})."
                )
            )

        # 2. فحص المؤشرات اللفظية إن وجدت
        if label in cls.INDICATORS_MAP and ocr_text:
            clean_text = ocr_text.lower()
            indicators = cls.INDICATORS_MAP[label]
            if not any(ind in clean_text for ind in indicators):
                issues.append(
                    ValidationIssue(
                        field="evrak_analysis.document_type",
                        type=IssueType.CLASSIFICATION_MISMATCH,
                        severity=Severity.MEDIUM,
                        message=f"Belge '{label}' olarak sınıflandırıldı ancak OCR metninde beklenen göstergeler bulunamadı."
                    )
                )

        return issues