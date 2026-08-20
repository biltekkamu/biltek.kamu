from typing import Tuple, List
from schema import EvrakAnalysisResult, ValidationBlock

class EvrakValidator:
    @staticmethod
    def validate_analysis(analysis: EvrakAnalysisResult, raw_ocr_text: str) -> ValidationBlock:
        issues: List[str] = []
        confidence = analysis.analysis_confidence

        # 1. التحقق من وجود ملخص كافٍ وغير مبهم
        if not analysis.summary or len(analysis.summary.strip()) < 15:
            issues.append("Özet metni çok kısa veya yetersiz.")
            confidence -= 0.15

        # 2. التحقق من تحديد الهدف والنية الإدارية
        if not analysis.purpose or analysis.purpose.lower() in ["unknown", "belirtilmedi", ""]:
            issues.append("Belgenin temel amacı (purpose) net olarak tespit edilemedi.")
            confidence -= 0.10

        if not analysis.intent or analysis.intent.lower() in ["unknown", ""]:
            issues.append("Belge idari niyeti (intent) belirlenemedi.")
            confidence -= 0.10

        # 3. فحص التناقض: وجود نص كافٍ لكن تم إرجاع معلومات فارغة
        if len(raw_ocr_text.strip()) > 100 and not analysis.important_points and not analysis.entities:
            issues.append("Belge metni yeterince uzun olmasına rağmen hiçbir varlık veya önemli nokta çıkarılamadı.")
            confidence -= 0.15

        # 4. ضبط مجال الثقة النهائي
        confidence = max(0.0, min(1.0, round(confidence, 2)))

        # 5. تحديد حالة التحقق
        if confidence >= 0.80 and len(issues) == 0:
            status = "passed"
        elif confidence >= 0.50:
            status = "warning"
        else:
            status = "needs_review"

        return ValidationBlock(
            status=status,
            issues=issues,
            confidence=confidence
        )