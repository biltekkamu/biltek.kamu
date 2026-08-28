import re
from typing import List, Dict, Any
from models import ValidationIssue, IssueType, Severity


class RoutingValidator:
    def __init__(self):
        pass

    DEPARTMENT_MAP = {
        "gumruk": {
            "keywords": [
                "gumruk", "ithalat", "ihracat", "tarife", "kacakcilik", 
                "antrepo", "beyanname", "transit", "mense", "esya", "dis ticaret"
            ],
            "valid_dept_names": ["gumruk", "dis ticaret", "hukuk", "gelir"]
        },
        "personel": {
            "keywords": [
                "izin", "maas", "sicil", "istifa", "tayin", "rapor", 
                "kadro", "ozluk", "terfi", "atama", "disiplin", "personel"
            ],
            "valid_dept_names": ["personel", "insan kaynaklari", "idari isler"]
        },
        "bilgi islem": {
            "keywords": [
                "yazilim", "donanim", "sifre", "internet", "sunucu", 
                "ag", "hesap", "erisim", "siber", "veritabani", "bilisim"
            ],
            "valid_dept_names": ["bilgi islem", "bilgi teknolojileri", "yazilim", "sistem"]
        },
        "hukuk": {
            "keywords": [
                "dava", "mahkeme", "savunma", "hukuki", "ihtar", 
                "yargi", "savcilik", "mutalaa", "kanun", "tazminat"
            ],
            "valid_dept_names": ["hukuk", "musavirlik", "adli"]
        },
        "mali isler": {
            "keywords": [
                "fatura", "odeme", "muhasebe", "butce", "avans", 
                "tahsilat", "harcama", "ihale", "hakedis", "kesin hesap"
            ],
            "valid_dept_names": ["mali", "muhasebe", "butce", "finans", "gelir"]
        },
        "destek isleri": {
            "keywords": [
                "bina", "bakim", "onarim", "arac", "ulasim", 
                "guvenlik", "temizlik", "lojistik", "arsiv", "kiralama"
            ],
            "valid_dept_names": ["destek", "idari", "lojistik", "isletme"]
        },
        "ogrenci isleri": {
            "keywords": [
                "burs", "kayit", "ogrenci", "transkript", "harc", 
                "mezuniyet", "staj", "akademik"
            ],
            "valid_dept_names": ["ogrenci", "egitim", "akademik"]
        }
    }

    @staticmethod
    def _normalize_text(text: str) -> str:
       
        if not text:
            return ""
        mapping = {
            'İ': 'i', 'I': 'i', 'ı': 'i', 'i̇': 'i',
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

    def validate(self, routing_block: Dict[str, Any], evrak_analysis: Dict[str, Any]) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []
        if not isinstance(routing_block, dict) or not isinstance(evrak_analysis, dict):
            return issues

        raw_selected = str(routing_block.get("selected_department", ""))
        selected_dept = self._normalize_text(raw_selected)

        topic = self._normalize_text(str(evrak_analysis.get("topic", "")))
        intent = self._normalize_text(str(evrak_analysis.get("intent", "")))
        summary = self._normalize_text(str(evrak_analysis.get("summary", "")))
        combined_context = f"{topic} {intent} {summary}".strip()

        if not selected_dept or not combined_context:
            return issues

       
        scores = {}
        for dept_key, data in self.DEPARTMENT_MAP.items():
            score = sum(1 for kw in data["keywords"] if f" {kw} " in f" {combined_context} ")
            if score > 0:
                scores[dept_key] = score

        if not scores:
            return issues

        top_dept_key = max(scores, key=scores.get)
        valid_targets = self.DEPARTMENT_MAP[top_dept_key]["valid_dept_names"]

        is_compatible = any(target in selected_dept for target in valid_targets)

        if not is_compatible and scores[top_dept_key] >= 2:
            issue_type = getattr(IssueType, "ROUTING_MISMATCH", "routing_mismatch")
            severity = getattr(Severity, "MEDIUM", "medium")
            
            issues.append(
                ValidationIssue(
                    field="routing.selected_department",
                    type=issue_type,
                    severity=severity,
                    message=f"Belge içeriği ağırlıklı olarak '{top_dept_key}' alanı ile ilişkili görünmektedir ancak '{raw_selected}' birimine yönlendirilmiştir."
                )
            )

        return issues