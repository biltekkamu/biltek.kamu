import re
from typing import List, Dict, Any
from models import ValidationIssue, IssueType, Severity

class RoutingValidator:
    DEPARTMENT_MAP = {
        "ogrenci isleri": ["burs", "kayit", "ogrenci", "transkript", "harc", "mezuniyet"],
        "personel isleri": ["izin", "maas", "sicil", "istifa", "tayin", "rapor", "kadro"],
        "bilgi islem": ["yazilim", "donanim", "sifre", "internet", "sunucu", "ag", "hesap", "erisim"],
        "hukuk musavirligi": ["dava", "mahkeme", "savunma", "ceza", "hukuki", "ihtar", "disiplin"],
        "mali isler": ["fatura", "odeme", "muhasebe", "butce", "avans", "tahsilat"]
    }

    @staticmethod
    def _normalize_text(text: str) -> str:
        """تحويل النصوص التركية إلى حروف إنجليزية بسيطة لتجنب أخطاء i/İ و ş/s وغيرها"""
        if not text:
            return ""
        mapping = {
            'İ': 'i', 'I': 'i', 'ı': 'i',
            'Ğ': 'g', 'ğ': 'g',
            'Ü': 'u', 'ü': 'u',
            'Ş': 's', 'ş': 's',
            'Ö': 'o', 'ö': 'o',
            'Ç': 'c', 'ç': 'c'
        }
        for k, v in mapping.items():
            text = text.replace(k, v)
        text = text.lower()
        return re.sub(r'[^a-z0-9\s]', ' ', text).strip()

    @classmethod
    def validate(cls, routing_block: Dict[str, Any], evrak_analysis: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not isinstance(routing_block, dict) or not isinstance(evrak_analysis, dict):
            return issues

        raw_selected = str(routing_block.get("selected_department", ""))
        selected_dept = cls._normalize_text(raw_selected)
        
        topic = cls._normalize_text(str(evrak_analysis.get("topic", "")))
        intent = cls._normalize_text(str(evrak_analysis.get("intent", "")))
        combined_context = f"{topic} {intent}".strip()

        if not selected_dept or not combined_context:
            return issues

        # التحقق من التعارض
        for dept_key, keywords in cls.DEPARTMENT_MAP.items():
            if any(kw in combined_context for kw in keywords):
                # إذا كانت الكلمات تدل على هذا القسم ولكن اسم القسم الموجه إليه لا يحتويه
                if dept_key not in selected_dept:
                    issues.append(
                        ValidationIssue(
                            field="routing.selected_department",
                            type=IssueType.ROUTING_MISMATCH,
                            severity=Severity.MEDIUM,
                            message=f"Belge konusu '{dept_key}' ile ilişkili görünmektedir ancak '{raw_selected}' birimine yönlendirilmiştir."
                        )
                    )
                break

        return issues