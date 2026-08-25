import json
import re
from pathlib import Path
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class HybridDocumentClassifier:

    def __init__(
        self,
        model_dir: str = "./berturk_classifier_v1",
        eval_dir: str = "evaluation",
    ):
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = (
            AutoModelForSequenceClassification.from_pretrained(
                model_dir
            ).to(self.device)
        )
        self.model.eval()

        with open(
            Path(eval_dir) / "label2id.json",
            "r",
            encoding="utf-8",
        ) as f:
            self.label2id = json.load(f)
        self.id2label = {v: k for k, v in self.label2id.items()}

        # قواعد دقيقة للعناوين الرئيسية والكلمات الدلالية المحددة فقط
        self.rules_patterns = {
            "tutanak": [
                r"\bTUTANAK\b",
                r"\bTUTANAKTIR\b",
                r"\bİHBAR TUTANAĞI\b",
                r"\bDURUM TESPİT TUTANAĞI\b",
                r"\bOLAY TUTANAĞI\b",
            ],
            "sozlesmeprotokol": [
                r"\bSÖZLEŞME\b",
                r"\bPROTOKOL\b",
                r"\bSÖZLEŞMESİDİR\b",
                r"\bİŞ SÖZLEŞMESİ\b",
                r"\bKİRA SÖZLEŞMESİ\b",
            ],
            "beyanname": [
                r"\bBEYANNAME\b",
                r"\bBEYANNAMESİ\b",
                r"\bMAL BİLDİRİMİ\b",
                r"\bVERGİ BİLDİRİMİ\b",
            ],
            "izin_belgesi": [
                r"\bİZİN BELGESİ\b",
                r"\bİZİN FORMU\b",
                r"\bMAZURET İZNİ\b",
                r"\bYILLIK İZİN FORMU\b",
            ],
            "onay_belgesi": [
                r"\bMAKAMINA\b[\s\S]{0,100}\bOLUR\b",
                r"\bONAY BELGESİ\b",
                r"\bUYGUNDUR\b",
            ],
            "bildirim_tebligat": [
                r"\bTEBLİĞ-TEBELLÜĞ\b",
                r"\bTEBLİGAT ZARFI\b",
                r"\bBİLDİRİM FORMU\b",
            ],
            "basvuru_belgesi": [
                r"\bBAŞVURU FORMU\b",
                r"\bBAŞVURU DİLEKÇESİ\b",
                r"\bTALEP FORMU\b",
            ],
            "rapor": [
                r"\bDENETİM RAPORU\b",
                r"\bİNCELEME RAPORU\b",
                r"\bFAALİYET RAPORU\b",
                r"^\s*RAPOR\s*$",
            ],
            "form": [
                r"\bKAYIT VE BAŞVURU FORMU\b",
                r"\bBİLGİ GÜNCELLEME FORMU\b",
            ],
        }

    def _tokenize(
        self,
        text: str,
        max_len: int = 512,
        head_len: int = 128,
        tail_len: int = 380,
    ):
        cls_id = self.tokenizer.cls_token_id
        sep_id = self.tokenizer.sep_token_id
        pad_id = self.tokenizer.pad_token_id

        token_ids = self.tokenizer.encode(
            text,
            add_special_tokens=False,
            verbose=False,
        )

        if len(token_ids) <= (max_len - 2):
            combined = [cls_id] + token_ids + [sep_id]
        else:
            combined = (
                [cls_id]
                + token_ids[:head_len]
                + token_ids[-tail_len:]
                + [sep_id]
            )

        pad_len = max_len - len(combined)
        input_ids = combined + [pad_id] * pad_len
        attention_mask = [1] * len(combined) + [0] * pad_len

        return {
            "input_ids": torch.tensor(
                [input_ids], dtype=torch.long
            ).to(self.device),
            "attention_mask": torch.tensor(
                [attention_mask], dtype=torch.long
            ).to(self.device),
        }

    def _apply_rule_verification(
        self,
        text: str,
        bert_label: str,
        bert_confidence: float,
        all_probs: dict,
    ) -> dict:
        text_upper = text.upper()
        matched_rules = []

        # استخراج المطابقات من النص
        for label, patterns in self.rules_patterns.items():
            for p in patterns:
                if re.search(p, text_upper):
                    matched_rules.append(label)
                    break

        # 1. إذا كان الموديل واثقاً جداً (ثقة >= 75%) -> اعتمد قراره دائماً
        if bert_confidence >= 0.75:
            return {
                "final_label": bert_label,
                "bert_raw_label": bert_label,
                "confidence": round(float(bert_confidence), 4),
                "decision_reason": "Model Confident: High BERT confidence retained",
                "matched_rules": matched_rules,
                "top_probabilities": all_probs,
            }

        # 2. إذا كانت ثقة الموديل متوسطة وهناك تأكيد مطابق من القواعد
        if bert_label in matched_rules:
            boosted_conf = min(0.95, bert_confidence + 0.15)
            return {
                "final_label": bert_label,
                "bert_raw_label": bert_label,
                "confidence": round(float(boosted_conf), 4),
                "decision_reason": f"Hybrid Agreement: BERT prediction confirmed by [{bert_label}] keyword",
                "matched_rules": matched_rules,
                "top_probabilities": all_probs,
            }

        # 3. التدخل بالقواعد فقط عند انخفاض ثقة الموديل تماماً (< 50%) ووجود قاعدة صريحة لمرشح قوي
        if bert_confidence < 0.50 and len(matched_rules) == 1:
            rule_candidate = matched_rules[0]
            # يجب أن يكون الموديل قد وضع احتمالاً معتبراً لنفس الفئة
            if all_probs.get(rule_candidate, 0.0) >= 0.20:
                return {
                    "final_label": rule_candidate,
                    "bert_raw_label": bert_label,
                    "confidence": round(
                        float(all_probs[rule_candidate] + 0.20),
                        4,
                    ),
                    "decision_reason": f"Rule Fallback: Low BERT confidence, guided by explicit keyword [{rule_candidate}]",
                    "matched_rules": matched_rules,
                    "top_probabilities": all_probs,
                }

        # 4. الحالة الافتراضية: الاعتماد على نموذج BERTurk
        return {
            "final_label": bert_label,
            "bert_raw_label": bert_label,
            "confidence": round(float(bert_confidence), 4),
            "decision_reason": "BERT Prediction (No rule override applied)",
            "matched_rules": matched_rules,
            "top_probabilities": all_probs,
        }

    def predict(self, text: str) -> dict:
        if not text.strip():
            return {"error": "النص فارغ"}

        inputs = self._tokenize(text)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = (
                torch.softmax(outputs.logits, dim=-1)[0]
                .cpu()
                .numpy()
            )

        pred_idx = np.argmax(probs)
        bert_label = self.id2label[pred_idx]
        confidence = float(probs[pred_idx])

        top_3_indices = np.argsort(probs)[-3:][::-1]
        top_probs = {
            self.id2label[idx]: round(float(probs[idx]), 4)
            for idx in top_3_indices
        }

        return self._apply_rule_verification(
            text, bert_label, confidence, top_probs
        )


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