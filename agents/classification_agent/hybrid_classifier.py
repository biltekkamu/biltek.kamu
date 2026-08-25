import json
import torch
import numpy as np
import re
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class HybridDocumentClassifier:
    def __init__(self, model_dir: str = "./berturk_classifier_v1", eval_dir: str = "evaluation"):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # 1. تحميل الموديل والـ Tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_dir).to(self.device)
        self.model.eval()

        # 2. تحميل خريطة التصنيفات
        with open(Path(eval_dir) / "label2id.json", "r", encoding="utf-8") as f:
            self.label2id = json.load(f)
        self.id2label = {v: k for k, v in self.label2id.items()}

        # 3. قواعد التحقق والكلمات الدلالية الصريحة (Verification Rules)
        self.rules_patterns = {
            "tutanak": [
                r"\bTUTANAK\b", r"\bTUTANAKTIR\b", r"\bİHBAR TUTANAĞI\b", 
                r"\bDURUM TESPİT TUTANAĞI\b", r"\bOLAY TUTANAĞI\b"
            ],
            "sozlesmeprotokol": [
                r"\bSÖZLEŞME\b", r"\bPROTOKOL\b", r"\bSÖZLEŞMESİDİR\b", 
                r"\bİŞ SÖZLEŞMESİ\b", r"\bKİRA SÖZLEŞMESİ\b"
            ],
            "beyanname": [
                r"\bBEYANNAME\b", r"\bBEYANNAMESİ\b", r"\bMAL BİLDİRİMİ\b", 
                r"\bVERGİ BİLDİRİMİ\b"
            ],
            "izin_belgesi": [
                r"\bİZİN BELGESİ\b", r"\bİZİN FORMU\b", r"\bİZİN TALEP\b", 
                r"\bMAZURET İZNİ\b", r"\bYILLIK İZİN\b"
            ],
            "onay_belgesi": [
                r"\bOLUR\b", r"\bONAY\b", r"\bONAYINA\b", r"\bUYGUNDUR\b", 
                r"\bONAYLANMIŞTIR\b", r"\bMAKAMINA.*OLUR\b"
            ],
            "bildirim_tebligat": [
                r"\bTEBLİĞ\b", r"\bTEBLİGAT\b", r"\bBİLDİRİM\b", 
                r"\bTEBLİĞ-TEBELLÜĞ\b", r"\bDAĞITIM YERLERİNE\b"
            ],
            "basvuru_belgesi": [
                r"\bBAŞVURU FORMU\b", r"\bBAŞVURU DİLEKÇESİ\b", r"\bTALEP FORMU\b", 
                r"\bKAYIT FORMU\b"
            ],
            "rapor": [
                r"\bRAPOR\b", r"\bRAPORU\b", r"\bDENETİM RAPORU\b", 
                r"\bİNCELEME RAPORU\b", r"\bFAALİYET RAPORU\b"
            ],
            "form": [
                r"\bBİLGİ FORMU\b", r"\bKART1\b", r"\bFORMU\b", r"\bDEĞİŞİM FORMU\b"
            ]
        }

    def _tokenize(self, text: str, max_len: int = 512, head_len: int = 128, tail_len: int = 380):
        cls_id = self.tokenizer.cls_token_id
        sep_id = self.tokenizer.sep_token_id
        pad_id = self.tokenizer.pad_token_id

        token_ids = self.tokenizer.encode(
    text,
    add_special_tokens=False,
    verbose=False
)
        
        if len(token_ids) <= (max_len - 2):
            combined = [cls_id] + token_ids + [sep_id]
        else:
            combined = [cls_id] + token_ids[:head_len] + token_ids[-tail_len:] + [sep_id]

        pad_len = max_len - len(combined)
        input_ids = combined + [pad_id] * pad_len
        attention_mask = [1] * len(combined) + [0] * pad_len

        return {
            "input_ids": torch.tensor([input_ids], dtype=torch.long).to(self.device),
            "attention_mask": torch.tensor([attention_mask], dtype=torch.long).to(self.device)
        }

    def _apply_rule_verification(self, text: str, bert_label: str, confidence: float, top_probs: dict) -> dict:
        """
        طبقة تدقيق القواعد:
        1. إذا كانت ثقة BERT عالية وهناك تأكيد من الكلمات المفتاحية -> اعتماد مباشر.
        2. إذا كانت الثقة متوسطة أو حدث اشتباه بين فئتين متداخلتين -> فض الاشتباه بالقواعد.
        """
        text_upper = text.upper()
        matched_rules = []

        for label, patterns in self.rules_patterns.items():
            for p in patterns:
                if re.search(p, text_upper):
                    matched_rules.append(label)
                    break

        final_label = bert_label
        decision_reason = "BERT prediction verified"

        # حالة 1: تأكيد مباشر بنفس الفئة
        if bert_label in matched_rules:
            decision_reason = f"Verified by exact match rule for [{bert_label}]"
            confidence = max(confidence, 0.95)

        # حالة 2: فض الاشتباه الشهير بين (onay_belgesi vs bildirim_tebligat)
        elif bert_label in ["onay_belgesi", "bildirim_tebligat"]:
            if "onay_belgesi" in matched_rules and any(k in text_upper for k in ["OLUR", "UYGUNDUR", "ONAY"]):
                final_label = "onay_belgesi"
                decision_reason = "Rule Override: Found approval keywords ('OLUR/UYGUNDUR')"
            elif "bildirim_tebligat" in matched_rules:
                final_label = "bildirim_tebligat"
                decision_reason = "Rule Override: Found tebligat distribution keywords"

        # حالة 3: فض الاشتباه بين (form vs rapor)
        elif bert_label in ["form", "rapor"]:
            if "rapor" in matched_rules and "RAPOR" in text_upper[:200]:
                final_label = "rapor"
                decision_reason = "Rule Override: Found explicit 'RAPOR' header"
            elif "form" in matched_rules:
                final_label = "form"
                decision_reason = "Rule Override: Found explicit 'FORM' indicator"

        # حالة 4: ثقة الموديل منخفضة ووجدت قاعدة صريحة لفئة أخرى ذات احتمال وصيف عالي
        elif confidence < 0.60 and len(matched_rules) == 1:
            alternative_label = matched_rules[0]
            if top_probs.get(alternative_label, 0) > 0.15:
                final_label = alternative_label
                decision_reason = f"Rule Override: High-priority keyword matched [{alternative_label}]"

        return {
            "final_label": final_label,
            "bert_raw_label": bert_label,
            "confidence": round(float(confidence), 4),
            "decision_reason": decision_reason,
            "matched_rules": matched_rules,
            "top_probabilities": top_probs
        }

    def predict(self, text: str) -> dict:
        if not text.strip():
            return {"error": "النص فارغ"}

        # 1. التمرير على نموذج BERTurk
        inputs = self._tokenize(text)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)[0].cpu().numpy()

        pred_idx = np.argmax(probs)
        bert_label = self.id2label[pred_idx]
        confidence = probs[pred_idx]

        # تجميع أعلى 3 احتمالات
        top_3_indices = np.argsort(probs)[-3:][::-1]
        top_probs = {self.id2label[idx]: round(float(probs[idx]), 4) for idx in top_3_indices}

        # 2. التمرير على طبقة الـ Rules للتدقيق والتأكيد
        return self._apply_rule_verification(text, bert_label, confidence, top_probs)

# =====================================================
# تجربة سريعة (Test Example)
# =====================================================
if __name__ == "__main__":
    classifier = HybridDocumentClassifier()

    sample_ocr_text = """
    T.C. İÇİŞLERİ BAKANLIĞI
    GÖÇ İDARESİ GENEL MÜDÜRLÜĞÜ
    DAĞITIM YERLERİNE
    Tebliğ ve tebellüğ belgesidir. İlgili personelin dikkatine...
    """

    result = classifier.predict(sample_ocr_text)
    print(json.dumps(result, indent=2, ensure_ascii=False))