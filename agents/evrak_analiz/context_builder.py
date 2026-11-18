from typing import Dict, Any

class ContextBuilder:
    @staticmethod
    def build_analysis_context(ocr_data: Dict[str, Any], classification_result: Dict[str, Any] = None) -> str:
        """
        دمج بيانات الـ OCR والتصنيف الأولي في سياق نصي موحد ومنظم للـ LLM
        """
        metadata = ocr_data.get("parsed_metadata", {})
        clean_text = ocr_data.get("text", "").strip()
        
        # معلومات التصنيف الأولي إذا كانت متوفرة من BERTurk
        bert_label = classification_result.get("label", "Belirtilmedi") if classification_result else "Belirtilmedi"
        bert_conf = classification_result.get("confidence", 0.0) if classification_result else 0.0

        context_blocks = [
            "### BELGE BİLGİLERİ VE METADATA ###",
            f"- Sayı / No: {metadata.get('sayi') or 'Mevcut Değil'}",
            f"- Belge Tarihi: {metadata.get('tarih') or 'Mevcut Değil'}",
            f"- Belge Konusu: {metadata.get('konu') or 'Mevcut Değil'}",
            f"- Muhatap / Alıcı (Recipient): {metadata.get('recipient') or 'Mevcut Değil'}",
            f"- Ön Sınıflandırma (BERTurk Öngörüsü): {bert_label} (Güven: {bert_conf:.2f})",
            "",
            "### BELGE TAM METNİ (OCR CLEAN TEXT) ###",
            clean_text if clean_text else "[METİN BULUNAMADI]"
        ]

        return "\n".join(context_blocks)