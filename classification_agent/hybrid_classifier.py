import os
import sys
from pathlib import Path

# =====================================================
# WINDOWS DLL & PYTORCH FIX (MUST BE AT THE VERY TOP)
# =====================================================
torch_lib_path = Path(sys.prefix) / "Lib" / "site-packages" / "torch" / "lib"
if torch_lib_path.exists():
    try:
        os.add_dll_directory(str(torch_lib_path))
        os.environ["PATH"] = str(torch_lib_path) + ";" + os.environ.get("PATH", "")
    except Exception:
        pass

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import re
import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

CURRENT_DIR = Path(__file__).resolve().parent


class HybridDocumentClassifier:

    def __init__(
        self,
        model_dir: str | None = None,
        eval_dir: str | None = None,
    ):
        self.model_path = Path(model_dir) if model_dir else (CURRENT_DIR / "berturk_classifier_v1")
        self.eval_path = Path(eval_dir) if eval_dir else (CURRENT_DIR / "evaluation")

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_path))
        self.model = (
            AutoModelForSequenceClassification.from_pretrained(
                str(self.model_path)
            ).to(self.device)
        )
        self.model.eval()

        label2id_file = self.eval_path / "label2id.json"
        if not label2id_file.exists():
            label2id_file = self.model_path / "label2id.json"

        with open(
            label2id_file,
            "r",
            encoding="utf-8",
        ) as f:
            self.label2id = json.load(f)
        self.id2label = {int(v) if str(v).isdigit() else v: k for k, v in self.label2id.items()}
        self.id2label.update({int(k): v for k, v in self.id2label.items() if str(k).isdigit()})

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

        for label, patterns in self.rules_patterns.items():
            for p in patterns:
                if re.search(p, text_upper):
                    matched_rules.append(label)
                    break

        if bert_confidence >= 0.75:
            return {
                "final_label": bert_label,
                "bert_raw_label": bert_label,
                "confidence": round(float(bert_confidence), 4),
                "decision_reason": "Model Confident: High BERT confidence retained",
                "matched_rules": matched_rules,
                "top_probabilities": all_probs,
            }

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

        if bert_confidence < 0.50 and len(matched_rules) == 1:
            rule_candidate = matched_rules[0]
           
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

        return {
            "final_label": bert_label,
            "bert_raw_label": bert_label,
            "confidence": round(float(bert_confidence), 4),
            "decision_reason": "BERT Prediction (No rule override applied)",
            "matched_rules": matched_rules,
            "top_probabilities": all_probs,
        }

    def predict(self, text: str) -> dict:
        if not text or not text.strip():
            return {
                "final_label": "unknown",
                "bert_raw_label": None,
                "confidence": 0.0,
                "decision_reason": "Metin boş olduğu için sınıflandırma yapılamadı.",
                "matched_rules": [],
                "top_probabilities": {},
            }

        inputs = self._tokenize(text)
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = (
                torch.softmax(outputs.logits, dim=-1)[0]
                .cpu()
                .numpy()
            )

        pred_idx = int(np.argmax(probs))
        bert_label = self.id2label.get(pred_idx, str(pred_idx))
        confidence = float(probs[pred_idx])

        top_3_indices = np.argsort(probs)[-3:][::-1]
        top_probs = {
            self.id2label.get(int(idx), str(idx)): round(float(probs[idx]), 4)
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