# 🛡️ Doğrulama Agent (Comprehensive Validation & Verification Subsystem)

نظام التحقق الشامل (**Doğrulama Agent**) هو الطبقة المركزية المسؤولة عن تدقيق كافة مخرجات النظام (التصنيف، استخراج الحقول الإلزامية، صحة التوجيه الإداري، والتطابق مع نصوص الـ OCR و RAG). يهدف هذا الـ Agent إلى ضمان عدم تمرير أي معلومة خاطئة أو "هلوسة" إلى النظام النهائي عبر سلسلة من المدققات المتخصصة (Modular Validators).

---

## 🏗️ معمارية الـ Validators المدمجة

يتكون المجلد من المدققات التالية التي تعمل بتسلسل متكامل عبر `validator_service.py`:

┌────────────────────────────────────────┐
                       │      Agent Output / Pipeline JSON      │
                       └───────────────────┬────────────────────┘
                                           │
                                           ▼
                              ┌───────────────────────────┐
                              │   validator_service.py    │
                              │   (Orchestration Engine)  │
                              └─────────────┬─────────────┘
                                            │
     ┌───────────────────┬──────────────────┼───────────────────┬───────────────────┐
     ▼                   ▼                  ▼                   ▼
     ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ schema_validator│ │classification_  │ │confidence_      │ │required_fields_ │ │grounding_       │
│ .py             │ │validator.py     │ │validator.py     │ │validator.py     │ │validator.py     │
│ (Pydantic types)│ │(Label consistency)│(Threshold checks)│ │(Missing checks) │ │(OCR match check)│
└─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘ └─────────────────┘
│                   │                  │                   │                   │
└───────────────────┼──────────────────┴───────────────────┼───────────────────┘
│                                      │
▼                                      ▼
┌─────────────────┐                    ┌─────────────────┐
│semantic_        │                    │routing_         │
│validator.py     │                    │validator.py     │
│(Embedding match)│                    │(Department rules│
└─────────────────┘                    └─────────────────┘
│
▼
┌───────────────────────────────────┐
│ rag_validator.py                  │
│ (Citation & Context Faithfulness) │
└─────────────────┬─────────────────┘
│
▼
┌───────────────────────────────────┐
│    Final Validation Result        │
│    (is_valid, errors, warnings)   │
└───────────────────────────────────┘





[ملف مدخل: PDF / صور / DOCX / XLSX]
│
▼
┌────────────────────────────────────────────────────────┐
│ 1. طبقة الاستخراج والتطبيع (OCR & Ingestion)            │
│  - PaddleOCR + Python-Docx + Pandas                     │
│  - تصحيح الأخطاء المطبعية التركية (OCRPostProcessor)     │
└─────────────────────────┬──────────────────────────────┘
│
▼
┌────────────────────────────────────────────────────────┐
│ 2. طبقة التصنيف الدلالي الهجين (Hybrid Classification) │
│  - نموذج BERTurk (dbmdz/bert-base-turkish-cased)       │
│  - تقطيع التوكنز: Head (128) + Tail (380) = 512       │
│  - فحص القواعد الصارمة وفض الاشتباه                    │
└─────────────────────────┬──────────────────────────────┘
│
▼
┌────────────────────────────────────────────────────────┐
│ 3. طبقة التحليل واستخراج الكيانات (Evrak Analiz & RAG) │
│  - تلخيص المستند، تحديد الهدف والنية (Summary/Intent) │
│  - توجيه المستند للقسم المختص (Routing)                │
│  - توليد الإجابات القانونية والمصادر (RAG System)      │
└─────────────────────────┬──────────────────────────────┘
│
▼
┌────────────────────────────────────────────────────────┐
│ 4. طبقة التحقق والاعتماد (Doğrulama Agent)             │
│  - تدقيق البنية، الكيانات، التوجيه، والاتساق الدلالي   │
│  - حساب معامل الثقة والخصومات (Confidence Calculation) │
│  - إصدار القرار النهائي (valid / warning / invalid)     │
└────────────────────────────────────────────────────────┘


## 🛡️ تفاصيل طبقة التحقق والاعتماد (Doğrulama Agent)

تتولى هذه الطبقة مهمة "المراجع والمدقق الآلي" المستقل الذي يفحص المخرجات الحقلية (`Field-by-Field`) والتقاطعية (`Cross-Field`) لضمان صحتها قبل الاعتماد[cite: 1, 3].

### 1. وحدات الفحص (Modular Validators):

* **`SchemaValidator` (`schema_validator.py`):**
  * يتحقق من صحة بنية الـ JSON الأساسية وكون الكتل الجذرية (`document_info`, `ocr`, `evrak_analysis`) كائنات صحيحة وليست نصوصاً تالفة[cite: 10].
  * يتأكد من أن مقياس `analysis_confidence` يقع ضمن المجال الرياضي `[0.0, 1.0]`[cite: 10].

* **`RequiredFieldsValidator` (`required_fields_validator.py`):**
  * يضمن عدم فقدان البيانات الإلزامية الأساسية مثل نص الـ OCR الخام (`ocr.text`) ونوع المستند (`evrak_analysis.document_type`)[cite: 9].

* **`GroundingValidator` (`grounding_validator.py`):**
  * يتحقق من تأصيل ومطابقة الكيانات المستخرجة (`entities`) حرفياً داخل نص الـ OCR بعد تنظيف وتجريد علامات الترقيم، لمنع اختلاق أرقام أو أسماء غير موجودة في الوثيقة[cite: 8].

* **`ClassificationValidator` (`classification_validator.py`):**
  * يفحص درجة ثقة نموذج التصنيف؛ فإذا كانت أقل من `0.60` يسجل تنبيهاً[cite: 7].
  * يتحقق من احتواء النص على المؤشرات اللفظية الخاصة بالفئات المعتمدة (`fatura`, `dilekce`, `sozlesme`, `tutanak`)[cite: 7].

* **`RoutingValidator` (`routing_validator.py`):**
  * يحتوي على خريطة دلالية لأقسام المؤسسة (`ogrenci isleri`, `personel isleri`, `bilgi islem`, `hukuk musavirligi`, `mali isler`)[cite: 2].
  * يطابق موضوع المعاملة والنية مع القسم الموجه إليه، وفي حال توجيه معاملة شؤون موظفين (مثل طلب إجازة) إلى قسم آخر يتم تسجيل `routing_mismatch`[cite: 2].

* **`RAGValidator` (`rag_validator.py`):**
  * يمنع الهلوسة في الإجابات الاسترجاعية؛ إذا وُجدت إجابة في `rag.answer` وكانت مصفوفة المصادر `rag.sources` فارغة، يطلق تنبيهاً عالي الخطورة (`MISSING_SOURCE`)[cite: 6].

* **`SemanticValidator` (`semantic_validator.py`):**
  * مدقق دلالي ذكي عبر LLM يفحص الترابط المنطقي بين نص الـ OCR والملخص والهدف المكتوب[cite: 1].
  * يدعم الفحص عبر `structured_output` مع خطة استرجاع احتياطية (`Regex Fallback`) لقراءة الـ JSON الخام في حال حدوث خطأ أثناء الاستدعاء[cite: 1].

* **`ConfidenceCalculator` (`confidence_validator.py`):**
  * يحسب معامل الثقة النهائي انطلاقاً من ثقة أساسية `0.98` ويطبق الخصومات التالية[cite: 5]:
    * خطأ عالي الخطورة (`HIGH`): خصم **-0.35** لكل مشكلة[cite: 5].
    * خطأ متوسط الخطورة (`MEDIUM`): خصم **-0.15** لكل مشكلة[cite: 5].
    * خطأ منخفض الخطورة (`LOW`): خصم **-0.05** لكل مشكلة[cite: 5].
  * **تحديد الحالة:** 
    * `invalid`: في حال وجود أي خطأ `HIGH` أو نزول الثقة تحت `0.50`[cite: 5].
    * `warning`: في حال وجود مشاكل أو ثقة تحت `0.85`[cite: 5].
    * `valid`: في حال سلامة المستند بالكامل[cite: 5].

---

## 📋 هيكل مخرجات التحقق (JSON Output Schema)

```json
{
  "status": "valid | warning | invalid",
  "confidence": 0.48,
  "issues": [
    {
      "field": "Özet",
      "type": "analysis_mismatch",
      "severity": "high",
      "message": "Özet, OCR metnindeki talep edilen mazeret izinine uymuyor..."
    },
    {
      "field": "routing.selected_department",
      "type": "routing_mismatch",
      "severity": "medium",
      "message": "Belge konusu 'personel isleri' ile ilişkili görünmektedir ancak 'İçişleri Bakanlığı' birimine yönlendirilmiştir."
    }
  ]
}


التثبيت والإعداد (Installation & Setup)
1. المتطلبات الأساسية
Python 3.10 أو 3.11




أداة Poppler لمعالجة الـ PDF مضافة إلى الـ PATH أو المسار المباشر.

2. إعداد البيئة الافتراضية

# إنشاء البيئة وتفعيلها
python -m venv venv
.\venv\Scripts\Activate.ps1

# تثبيت الحزم
pip install -r requirements.txt



