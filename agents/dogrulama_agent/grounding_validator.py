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

    @staticmethod
    def _normalize_text(text: str) -> str:
      
        if not text:
            return ""
        text = str(text).lower()
        
        tr_map = {
            "ı": "i", "i̇": "i", "İ": "i", "I": "i",
            "ğ": "g", "Ğ": "g",
            "ü": "u", "Ü": "u",
            "ş": "s", "Ş": "s",
            "ö": "o", "Ö": "o",
            "ç": "c", "Ç": "c",
        }
        for tr_char, eng_char in tr_map.items():
            text = text.replace(tr_char, eng_char)

        text = re.sub(r"\b0(\d)", r"\1", text)
        
        text = re.sub(r"[^\w\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _is_item_in_ocr(cls, clean_item: str, clean_ocr: str) -> bool:
   
        if not clean_item:
            return True

        if clean_item in clean_ocr:
            return True

        words = [w for w in clean_item.split() if len(w) > 2]
        if not words:
            return True

        matched_words = [w for w in words if w in clean_ocr]
        return (len(matched_words) / len(words)) >= 0.65

    @classmethod
    def validate(cls, ocr_text: str, evrak_analysis: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not ocr_text or not isinstance(evrak_analysis, dict):
            return issues

        clean_ocr = cls._normalize_text(ocr_text)
        entities = evrak_analysis.get("entities", {})

        if isinstance(entities, dict):
            for key, val in entities.items():
                if not val:
                    continue

                for raw_str in cls._flatten_strings(val):
                    item = raw_str.strip()
                    if len(item) <= 2 or item.lower() in [
                        "mevzuat belirtilmemiş",
                        "unknown",
                        "none",
                        "yok",
                        "belirtilmedi",
                    ]:
                        continue

                    clean_item = cls._normalize_text(item)

                    if not cls._is_item_in_ocr(clean_item, clean_ocr):
                        issues.append(
                            ValidationIssue(
                                field=f"evrak_analysis.entities.{key}",
                                type=IssueType.ENTITY_GROUNDING_ERROR,
                                severity=Severity.MEDIUM,
                                message=f"Çıkarılan '{raw_str}' değeri OCR metninde doğrulanamadı.",
                            )
                        )

        return issues