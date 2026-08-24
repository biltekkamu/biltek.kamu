from typing import List, Dict, Any
from pydantic import BaseModel, Field
import json
import re
from models import ValidationIssue, IssueType, Severity

class SemanticCheckOutput(BaseModel):
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="Belge analiz alanları arasındaki mantıksal ve anlamsal tutarsızlıklar"
    )

SEMANTIC_PROMPT = """Sen bir Doğrulama ve Kalite Kontrol (Validation) Uzmanısın.
Görevin, OCR metni ile çıkarılan analiz alanlarını (Field-by-Field) tek tek ve çaprazlama (Cross-Field) denetleyerek mantıksal tutarsızlıkları bulmaktır.

DENETLENECEK KRİTİK NOKTALAR:
1. [Belge Türü (evrak_analysis.document_type)]: Belgenin asıl işlevi (örn. 'karar/sonuç/bildirim') ile sınıflandırılan tür ('basvuru_belgesi') uyuşuyor mu? Metin bir değerlendirme sonucu veya karar ise ve tür 'basvuru_belgesi' olarak verilmişse kesinlikle 'classification_mismatch' ver.
2. [Özet, Amaç ve Niyet (evrak_analysis.summary/purpose/intent)]: OCR metnindeki gerçek talebi ve içeriği tam yansıtıyor mu? Anlam saptırması varsa 'logical_inconsistency' veya 'analysis_mismatch' ver.
3. [Yönlendirme (routing.selected_department)]: Belgenin konusu ve içeriği yönlendirilen birim ile mantıksal olarak örtüşüyor mu? Uyuşmuyorsa 'routing_mismatch' ver.
4. [RAG Dayanağı (rag.answer)]: Üretilen cevap ile verilen kaynaklar arasında anlamsal çelişki varsa 'rag_grounding_error' ver.

KURALLAR:
- Kesinlikle yeni bir analiz yapma veya eksik bilgileri tamamlama.
- Yalnızca bariz mantıksal çelişki veya anlamsal zıtlık varsa sorun kaydı oluştur.
- Her sorun için 'field' kısmına standart JSON yolunu yaz (Örn: 'evrak_analysis.document_type', 'evrak_analysis.summary', 'routing.selected_department', 'rag.answer').
- Herhangi bir çelişki yoksa boş liste döndür.

Yanıtını YALNIZCA geçerli bir JSON nesnesi olarak döndür:
{
  "issues": [
    {
      "field": "alan_yolu",
      "type": "sorun_turu",
      "severity": "low|medium|high",
      "message": "aciklama"
    }
  ]
}
"""

class SemanticValidator:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def validate(self, payload: Dict[str, Any]) -> List[ValidationIssue]:
        if not self.llm_client:
            return []

        ocr_block = payload.get("ocr", {}) if isinstance(payload.get("ocr"), dict) else {}
        ocr_text = ocr_block.get("text", "")
        analysis = payload.get("evrak_analysis", {}) if isinstance(payload.get("evrak_analysis"), dict) else {}
        routing = payload.get("routing", {}) if isinstance(payload.get("routing"), dict) else {}
        rag = payload.get("rag", {}) if isinstance(payload.get("rag"), dict) else {}

        if not ocr_text or len(ocr_text.strip()) < 15:
            return []

        doc_type_val = analysis.get("document_type")
        if isinstance(doc_type_val, dict):
            doc_type_label = doc_type_val.get("label", "")
        else:
            doc_type_label = str(doc_type_val or "")

        context = f"""
[1. OCR METNİ]:
{ocr_text}

[2. ALAN ÇIKTILARI (FIELD-BY-FIELD)]:
- evrak_analysis.document_type: {doc_type_label}
- evrak_analysis.topic: {analysis.get('topic')}
- evrak_analysis.purpose: {analysis.get('purpose')}
- evrak_analysis.intent: {analysis.get('intent')}
- evrak_analysis.summary: {analysis.get('summary')}

[3. YÖNLENDİRME (ROUTING)]:
- routing.selected_department: {routing.get('selected_department')}
- routing.reason: {routing.get('reason')}

[4. RAG ÇIKTISI]:
- rag.query: {rag.get('query')}
- rag.answer: {rag.get('answer')}
- rag.sources: {rag.get('sources')}
"""

        messages = [
            {"role": "system", "content": SEMANTIC_PROMPT},
            {"role": "user", "content": context}
        ]

        try:
            # المحاولة الأولى: عبر structured_output
            structured_llm = self.llm_client.with_structured_output(SemanticCheckOutput)
            res: SemanticCheckOutput = structured_llm.invoke(messages)
            return res.issues
        except Exception as primary_error:
            # خطة احتياطية مباشرة لقراءة الـ JSON الخام في حال فشل structured output
            try:
                raw_response = self.llm_client.invoke(messages)
                content = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
                
                # استخراج نص الـ JSON من داخل علامات الترقيم إن وجدت
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    output = SemanticCheckOutput(**parsed)
                    return output.issues
            except Exception as fallback_error:
                print(f"⚠️ [SemanticValidator Exception]: {primary_error} | Fallback: {fallback_error}")
            
            return []