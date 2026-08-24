import re
from typing import List, Dict, Any
from models import ValidationIssue, IssueType, Severity

class GroundingValidator:
    @staticmethod
    def _flatten_strings(val: Any) -> List[str]:
        res = []
        if isinstance(val, str):
            res.append(val)
        elif isinstance(val, list):
            for item in val:
                res.extend(GroundingValidator._flatten_strings(item))
        elif isinstance(val, dict):
            for sub in val.values():
                res.extend(GroundingValidator._flatten_strings(sub))
        return res

    @classmethod
    def validate(cls, ocr_text: str, evrak_analysis: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not ocr_text or not isinstance(evrak_analysis, dict):
            return issues

        normalized_ocr = ocr_text.lower()
        clean_ocr = re.sub(r'[^\w\s]', '', normalized_ocr)
        entities = evrak_analysis.get("entities", {})

        if isinstance(entities, dict):
            for key, val in entities.items():
                if not val:
                    continue

                for raw_str in cls._flatten_strings(val):
                    item = raw_str.strip().lower()
                    if len(item) <= 2 or item in ["mevzuat belirtilmemiş", "unknown", "none", "yok", "belirtilmedi"]:
                        continue

                    clean_item = re.sub(r'[^\w\s]', '', item)
                    if clean_item not in clean_ocr:
                        issues.append(
                            ValidationIssue(
                                field=f"evrak_analysis.entities.{key}",
                                type=IssueType.ENTITY_GROUNDING_ERROR,
                                severity=Severity.MEDIUM,
                                message=f"Çıkarılan '{raw_str}' değeri OCR metninde doğrulanamadı."
                            )
                        )

        return issues