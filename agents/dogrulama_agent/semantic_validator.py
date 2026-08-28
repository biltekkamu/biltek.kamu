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

DENETLENECEK KRİTİK NOKTALAR VE İSTİSNALAR:
1. [Belge Türü (evrak_analysis.document_type)]:
   - Belgenin asıl işlevi (örn. 'ihale onay talebi', 'olur', 'karar', 'dilekçe') ile sınıflandırılan tür mantıksal olarak örtüşüyorsa HATA VERME.
   - Sadece bariz zıtlıklarda (Örn: Bir ceza iddianamesine 'Fatura' veya 'İzin Talebi' denmişse) 'classification_mismatch' ver.

2. [Özet, Amaç ve Niyet (evrak_analysis.summary/purpose/intent)]:
   - OCR metnindeki gerçek talebi ve içeriği yansıtıyor mu? OCR'daki tablo bozukluklarından veya harf hatalarından kaynaklanan önemsiz kusurları hata olarak sayma. Anlam saptırması varsa 'logical_inconsistency' ver.

3. [Yönlendirme (routing.selected_department)]:
   - İhale, satın alma, bütçe, ödenek veya harcama süreçlerini içeren onay veya talep belgelerinin 'Mali Hizmetler Birimi' veya 'Destek Hizmetleri Birimi'ne yönlendirilmesi idari teamüllere uygundur. Bu durumlarda KESİNLİKLE 'routing_mismatch' VERME.
   - Sadece tamamen ilgisiz yönlendirmelerde (Örn: Ağır ceza suç duyurusunun 'Park ve Bahçeler'e yönlendirilmesi) hata ver.

4. [RAG Dayanağı (rag.answer)]:
   - İncelenen belgenin kendisinde açıkça geçen kanun maddeleri (Örn: 2886 sayılı Kanun m. 51/g) RAG cevabında veya analizde açıklanmışsa 'rag_grounding_error' VERME.
   - Sadece kaynaklarda ve belgede hiç olmayan tamamen hayali/uydurma maddeler türetilmişse hata ver.

KURALLAR:
- OCR okuma bozukluklarından kaynaklanan anlamsız kelimeleri (Örn: APANIDARENINADI vb.) hata olarak bildirme.
- Kesinlikle yeni bir analiz yapma veya eksik bilgileri tamamlama.
- Yalnızca bariz ve vahim mantıksal çelişki varsa sorun kaydı oluştur.
- Her sorun için 'field' kısmına standart JSON yolunu yaz (Örn: 'evrak_analysis.document_type', 'evrak_analysis.summary', 'routing.selected_department', 'rag.answer').
- Herhangi bir çelişki yoksa boş liste döndür.
- Eğer bir durum için sorun olmadığına veya 'no issue' olduğuna karar verirsen, o durumu 'issues' listesine KESİNLİKLE EKLEME.
- 'message' alanına iç düşüncelerini veya tartışmalarını yazma; yalnızca kesin bir ihlal varsa net sebebi belirt.


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

        def _clean_issues(issues_list: List[ValidationIssue]) -> List[ValidationIssue]:
            filtered: List[ValidationIssue] = []
            for issue in issues_list:
                msg = str(issue.message or "")
                field = str(issue.field or "")
                if "APANIDARENINADI" in msg or "Sayi/No alanindaki hata" in msg:
                    continue
                if field == "routing.selected_department" and any(k in msg.lower() for k in ["mali", "ihale", "2886", "4734"]):
                    continue
                filtered.append(issue)
            return filtered

        try:
            structured_llm = self.llm_client.with_structured_output(SemanticCheckOutput)
            res: SemanticCheckOutput = structured_llm.invoke(messages)
            return _clean_issues(res.issues)
        except Exception as primary_error:
            try:
                raw_response = self.llm_client.invoke(messages)
                content = raw_response.content if hasattr(raw_response, 'content') else str(raw_response)
                
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    output = SemanticCheckOutput(**parsed)
                    return _clean_issues(output.issues)
            except Exception as fallback_error:
                print(f"⚠️ [SemanticValidator Exception]: {primary_error} | Fallback: {fallback_error}")
            
            return []