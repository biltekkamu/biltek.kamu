# 🏛️ Kurumsal Belge Analizi ve Hibrit Sınıflandırma Sistemi
### (Turkish Document OCR, Hybrid Classification & Information Extraction Pipeline)

نظام متكامل لمعالجة، استخراج وتصنيف الوثائق والمستندات الإدارية الرسمية باللغة التركية. يعتمد النظام على معمارية هجينة (**Hybrid Pipeline**) تجمع بين استخراج النصوص متعدد الصيغ، نماذج اللغة العميقة (**BERTurk**)، وطبقات التحقق الصارمة بالقواعد البرمجية (**Rule-Based Verification & Disambiguation**).

---

## 🏗️ معمارية النظام (System Architecture)

يتكون النظام من 4 طبقات أساسية مترابطة تضمن دقة المعالجة وسرعة اتخاذ القرار:




              ┌─────────────────────────────────┐
              │      الوثيقة المدخلة           │
              │ (PDF, JPG, PNG, DOCX, XLSX...)  │
              └────────────────┬────────────────┘
                               │
                               ▼


┌───────────────────────────────────────────────────────────────────┐
│ الطبقة 1: الاستخراج والتطبيع (Extraction & Normalization)         │
│  - OCR (PaddleOCR) للصور و PDF                                   │
│  - Direct Parsers لملفات Word (DOCX) و Excel (XLSX)               │
│  - Post-Processing: تصحيح الأخطاء المطبعية التركية الشائعة        │
└─────────────────────────────────┬─────────────────────────────────┘
│
▼
┌───────────────────────────────────────────────────────────────────┐
│ الطبقة 2: استخراج البيانات الهيكلية (Structural Information)       │
│  - Metadata Parser: استخراج (Tarih, Sayı, Konu, Dağıtım) عبر Regex│
│  - Table Extractor: استخراج جداول القوانين والتعديلات هندسياً     │
│  - Vision Detector: كشف الأختام الملونة والتواقيع الحية (OpenCV)   │
└─────────────────────────────────┬─────────────────────────────────┘
│
▼
┌───────────────────────────────────────────────────────────────────┐
│ الطبقة 3: التصنيف الدلالي العميق (Deep Semantic Classification)   │
│  - نموذج BERTurk (dbmdz/bert-base-turkish-cased)                  │
│  - استراتيجية تقطيع التوكنز: Head (128) + Tail (380) = 512 Tokens │
│  - حساب مصفوفة الاحتمالات ونسب الثقة لجميع الفئات                 │
└─────────────────────────────────┬─────────────────────────────────┘
│
▼
┌───────────────────────────────────────────────────────────────────┐
│ الطبقة 4: التحقق والتوثيق ( Rule-Based Post-Check)     │
│  - التحقق من تنبؤ BERTurk ومطابقته للكلمات المفتاحية الرسمية      │
│  - فض الاشتباه (Disambiguation) بين الفئات المتشابهة:             │
│    * onay_belgesi  vs  bildirim_tebligat                          │
│    * form          vs  rapor                                      │
│  - إصدار القرار النهائي مع بيان سبب الاعتماد (Decision Reason)    │
└───────────────────────────────────────────────────────────────────┘


├── classification_data/          # مجلدات البيانات الخام مصنفة لكل فئة
│   ├── basvuru_belgesi/
│   ├── beyanname/
│   ├── bildirim_tebligat/
│   ├── form/
│   ├── izin_belgesi/
│   ├── onay_belgesi/
│   ├── rapor/
│   ├── sozlesmeprotokol/
│   └── tutanak/
├── evaluation/                   # مخرجات التقييم وتوزيع الفئات
│   ├── label2id.json
│   ├── metrics.json
│   └── error_analysis.json
├── berturk_classifier_v1/        # مجلد حفظ أوزان نموذج BERTurk المدرب
├── dataset.jsonl                 # الداتا المجمعة والمستخرجة عبر الـ Pipeline
├── data.py                       # سكريبت استخراج النصوص وبناء dataset.jsonl
├── train.py                      # سكريبت تدريب وتقييم نموذج BERTurk
├── hybrid_classifier.py          # كلاس الاستدلال والتحقق الهجين (BERT + Rules)
└── README.md                     # التوثيق الشام

يمكنك استدعاء هذا الكلاس مباشرة داخل أي سكريبت عبر:
from hybrid_classifier import HybridDocumentClassifier
clf = HybridDocumentClassifier()
res = clf.predict(clean_text)
ل
