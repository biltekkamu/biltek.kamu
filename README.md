# 🏛️ BİLTEK KAMU

**Yapay Zekâ Destekli Çok Ajanlı Kamu Belge Analiz ve Mevzuat Asistanı**

BİLTEK KAMU; kamu kurumlarında kullanılan belge ve yazışmaların yapay zekâ destekli olarak okunması, sınıflandırılması, analiz edilmesi, ilgili mevzuatla ilişkilendirilmesi, doğru birime yönlendirilmesi, doğrulanması ve gerektiğinde resmi yazı oluşturulması amacıyla geliştirilen çok ajanlı bir yapay zekâ sistemidir.

Proje, **TEKNOFEST** kapsamında kamu süreçlerinde belge yönetimini daha hızlı, izlenebilir ve akıllı hale getirmek amacıyla geliştirilmiştir.

---

## 📌 Projenin Amacı

Kamu kurumlarında günlük olarak çok sayıda belge işlenmektedir.

Bu belgelerin:

- okunması,
- türünün belirlenmesi,
- içeriğinin analiz edilmesi,
- ilgili mevzuatın bulunması,
- doğru birime yönlendirilmesi,
- içerik tutarlılığının kontrol edilmesi,
- resmi cevap veya yazı hazırlanması

gibi işlemler manuel olarak ciddi zaman ve iş gücü gerektirebilir.

**BİLTEK KAMU**, bu süreci birbirinden bağımsız fakat orkestrasyon katmanı üzerinden birlikte çalışan yapay zekâ ajanlarıyla otomatikleştirmeyi hedeflemektedir.

---

# 🚀 Sistem Nasıl Çalışır?

Sistem hem **belge** hem de **doğrudan kullanıcı sorusu** kabul edebilir.

## Belge İşleme Akışı

```text
Belge Yükleme
      │
      ▼
┌───────────────┐
│   OCR Agent   │
└───────┬───────┘
        │
        ▼
┌───────────────────────┐
│ Classification Agent  │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Evrak Analiz Agent    │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│    Mevzuat RAG        │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Birim Yönlendirme     │
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│ Doğrulama ve Kontrol  │
└───────────┬───────────┘
            │
            ▼
       Nihai Sonuç
            │
            ▼
┌───────────────────────┐
│ Resmi Yazı On-Demand  │
└───────────────────────┘
```

Resmi yazı üretimi otomatik olarak her belge için çalışmaz.

Kullanıcı ihtiyaç duyduğunda **“Resmi Yazı Oluştur”** seçeneği üzerinden ilgili ajan çağrılır.

---

# 🤖 Multi-Agent Mimari

## 1. OCR Agent

OCR Agent, sisteme yüklenen belge veya görüntünün dijital metne dönüştürülmesinden sorumludur.

Temel görevleri:

- Görüntüden metin çıkarma
- PDF ve görüntü işleme
- Sayfa bazlı OCR
- Belge metadata çıkarımı
- Tarih tespiti
- Belge sayı/no tespiti
- Konu tespiti
- Muhatap tespiti
- İmza tespiti
- Kaşe/mühür tespiti
- Tablo algılama

OCR katmanında temel olarak **PaddleOCR** kullanılmaktadır.

Örnek çıktı:

```json
{
  "text": "...",
  "parsed_metadata": {
    "sayi": "F.T.2024/2",
    "tarih": "30/05/2024",
    "konu": "İfade İstemi",
    "recipient": "Burcu KÖKSAL"
  },
  "vision": {
    "has_signature": true,
    "has_stamp": false
  }
}
```

---

## 2. Classification Agent

Classification Agent, OCR tarafından çıkarılan belge metnini analiz ederek belgenin hangi belge türüne ait olduğunu belirler.

Sınıflandırma modeli olarak Türkçe dil yapısına uygun **BERTurk** tabanlı encoder-only model kullanılmaktadır.

Temel model:

```text
dbmdz/bert-base-turkish-cased
```

Sistem içerisinde kullanılan temel belge sınıfları:

```text
izin_belgesi
onay_belgesi
beyan_beyanname
tutanak
bildirim_tebligat
sozlesme_protokol
form
rapor
basvuru_belgesi
```

Örnek çıktı:

```json
{
  "label": "bildirim_tebligat",
  "confidence": 0.87
}
```

Sınıflandırma katmanında model çıktısı ile rule-based kontroller birlikte kullanılabilmektedir.

---

## 3. Evrak Analiz Agent

Evrak Analiz Agent, belgenin yalnızca türünü değil, semantik içeriğini de analiz eder.

Üretilen bilgiler arasında:

```text
document_type
topic
purpose
intent
summary
entities
key_information
important_points
missing_information
analysis_confidence
```

alanları bulunmaktadır.

Örnek:

```json
{
  "document_type": {
    "label": "bildirim_tebligat",
    "confidence": 0.87
  },
  "topic": "İfade İstemi ve İfade Verme Çağrısı",
  "purpose": "İlgili kişinin yazılı ifadesinin alınması",
  "intent": "ifade_verme_cagri",
  "analysis_confidence": 0.95
}
```

Ajan ayrıca belge içerisindeki kişi, kurum, tarih, belge numarası ve mevzuat referanslarını çıkarmaya çalışır.

---

## 4. Mevzuat RAG Agent

Mevzuat RAG katmanı, kullanıcı sorularını ve belge içeriğini ilgili mevzuat kaynaklarıyla ilişkilendirir.

Sistem içerisinde:

- Vector Search
- BM25
- Query Transformation
- Reciprocal Rank Fusion
- CrossEncoder Reranking
- LLM tabanlı cevap üretimi

yaklaşımları kullanılmaktadır.

RAG çıktısı:

```json
{
  "query": "...",
  "answer": "...",
  "sources": [
    {
      "title": "...",
      "article": "...",
      "score": 0.91,
      "content": "..."
    }
  ]
}
```

Sistem, cevap üretirken kullanılan kaynakları kullanıcıya ayrıca gösterebilir.

---

## 5. Birim Yönlendirme Agent

Bu ajan, analiz edilen belgenin hangi kamu birimine yönlendirilmesi gerektiğini belirler.

Örnek birimler:

```text
Ceza İşleri Birimi
Hukuk İşleri Birimi
Mali Hizmetler Birimi
İnsan Kaynakları Birimi
Evrak Kayıt Birimi
Bilgi İşlem Birimi
```

Örnek çıktı:

```json
{
  "selected_department": "Hukuk İşleri Birimi",
  "reason": "Belge hukuki değerlendirme gerektirmektedir.",
  "confidence": 0.90
}
```

---

## 6. Doğrulama ve Kontrol Agent

Doğrulama katmanı, diğer ajanların oluşturduğu sonuçların birbiriyle tutarlı olup olmadığını kontrol eder.

Kontrol edilen başlıca alanlar:

```text
Schema Validation
Required Fields Validation
Entity Grounding
Classification Validation
Routing Validation
RAG Grounding
Semantic Validation
Confidence Validation
```

Örnek çıktı:

```json
{
  "status": "invalid",
  "issues": [
    {
      "field": "routing.selected_department",
      "type": "routing_mismatch",
      "severity": "high",
      "message": "Belge içeriği ile yönlendirilen birim arasında uyumsuzluk tespit edildi."
    }
  ],
  "confidence": 0.63
}
```

Bu katman sistemde yalnızca sonuç üretmek yerine, diğer ajanların kararlarının denetlenmesini sağlar.

---

## 7. Resmi Yazı Agent

Resmi Yazı Agent, analiz sonucu kullanılarak kamu yazışma diline uygun resmi metin oluşturur.

Bu ajan **On-Demand** çalışmaktadır.

Desteklenen yazı türleri:

```text
cevap_yazisi
talep_yazisi
bilgilendirme_yazisi
basvuru_cevabi
```

Örnek çıktı:

```json
{
  "generated": true,
  "type": "bilgilendirme_yazisi",
  "subject": "İfade İstemi ve İfade Verme Çağrısı",
  "body": "...",
  "confidence": 0.93,
  "validation": {
    "status": "passed",
    "issues": []
  }
}
```

---

# 🧠 Orkestrasyon

Tüm ajanların koordinasyonu:

```text
orkestrasyon/
```

katmanı tarafından gerçekleştirilmektedir.

Orkestratör kullanıcının giriş türünü belirleyerek uygun işlem akışını başlatır.

Temel giriş tipleri:

```text
Question
Document
```

Belge girişlerinde ajan sonuçları ortak bir state üzerinden taşınır.

Örnek state alanları:

```text
document_id
input_type
user_question
file_path

status
current_step

document_info
ocr_result
raw_text

analysis
missing_information

rag_result
routing_result
official_letter

errors
warnings
```

---

# 📦 Standart Sistem Çıktısı

Belge işleme sonunda sistem aşağıdaki yapıya benzer birleşik bir JSON üretebilir:

```json
{
  "success": true,

  "document_info": {
    "document_id": "doc_001",
    "file_name": "example.pdf",
    "file_type": "pdf",
    "page_count": 1,
    "language": "tr"
  },

  "ocr": {
    "text": "...",
    "pages": [],
    "parsed_metadata": {},
    "tables": [],
    "vision": {}
  },

  "classification": {
    "label": "bildirim_tebligat",
    "confidence": 0.87
  },

  "evrak_analysis": {
    "document_type": {},
    "topic": "",
    "purpose": "",
    "intent": "",
    "summary": "",
    "entities": {},
    "key_information": {},
    "important_points": [],
    "missing_information": [],
    "analysis_confidence": 0.95
  },

  "rag": {
    "query": "",
    "answer": "",
    "sources": []
  },

  "routing": {
    "selected_department": "",
    "reason": "",
    "confidence": 0.0
  },

  "official_writing": null,

  "validation": {
    "status": "",
    "issues": [],
    "confidence": 0.0
  }
}
```

---

# 🖥️ Kullanıcı Arayüzü

BİLTEK KAMU'nun kullanıcı arayüzü:

```text
HTML
CSS
JavaScript
```

ile geliştirilmiştir.

Arayüz üzerinden kullanıcı:

- Belge yükleyebilir
- Belge hakkında soru sorabilir
- AI tarafından oluşturulan sonucu görebilir
- Kullanılan mevzuat kaynaklarını inceleyebilir
- İhtiyaç halinde resmi yazı oluşturabilir

---

# 📊 Sistem İzleme Dashboard

Projede ayrıca sistemin çalışma durumunu izlemek için ayrı bir yönetim paneli bulunmaktadır.

Dashboard üzerinden:

```text
Toplam işlem sayısı
Başarılı işlem sayısı
Geçersiz işlem sayısı
Ortalama işlem süresi
Son işlem
Agent Pipeline
Classification Confidence
Analysis Confidence
RAG kaynak sayısı
Yönlendirilen birim
Doğrulama sorunları
İşlem geçmişi
```

izlenebilir.

Agent Pipeline görünümü:

```text
OCR
 ↓
Classification
 ↓
Evrak Analiz
 ↓
Mevzuat RAG
 ↓
Birim Yönlendirme
 ↓
Doğrulama
 ↓
Resmi Yazı (On-Demand)
```

Dashboard üzerinde şu anda:

- **Doğrulama Detayları**
- **Mevzuat RAG Detayları**

interaktif olarak görüntülenebilmektedir.

Dashboard verileri mevcut geliştirme sürümünde backend belleğinde tutulmaktadır ve backend yeniden başlatıldığında sıfırlanır.

---

# ⚙️ Backend API

Backend **FastAPI** ile geliştirilmiştir.

Varsayılan adres:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

Temel endpointler:

| Method | Endpoint | Açıklama |
|---|---|---|
| GET | `/` | Backend durum bilgisi |
| GET | `/health` | Health check |
| POST | `/process` | Belge veya soru işleme |
| POST | `/official-writing` | On-demand resmi yazı üretimi |
| GET | `/dashboard` | Dashboard verileri |

---

# 🛠️ Kullanılan Teknolojiler

| Katman | Teknoloji |
|---|---|
| Backend | FastAPI |
| Dil | Python 3.11 |
| Frontend | HTML / CSS / JavaScript |
| OCR | PaddleOCR |
| Classification | BERTurk |
| LLM | EVREN LLM API |
| Vector Database | Chroma |
| Keyword Retrieval | BM25 |
| Reranking | CrossEncoder |
| Data Validation | Pydantic |
| Version Control | Git / GitHub |

---

# 📁 Proje Yapısı

```text
biltek.kamu/
│
├── agents/
│   │
│   ├── ocr/
│   │   └── OCR işlemleri
│   │
│   ├── classification_agent/
│   │   └── BERTurk belge sınıflandırması
│   │
│   ├── evrak_analiz/
│   │   └── Semantik belge analizi
│   │
│   ├── mevzuat_rag/
│   │   └── Mevzuat retrieval ve cevap üretimi
│   │
│   ├── birim_yonlendirme/
│   │   └── Birim yönlendirme
│   │
│   ├── dogrulama_agent/
│   │   └── Sonuç doğrulama ve kontrol
│   │
│   └── resmi_yazi/
│       └── Resmi yazı üretimi
│
├── backend/
│   └── app.py
│
├── frontend/
│   ├── index.html
│   ├── dashboard.html
│   ├── dashboard.css
│   └── dashboard.js
│
├── orkestrasyon/
│   └── Orkestrasyon ve workflow yönetimi
│
├── config/
│
├── data/
│
├── docs/
│
├── storage/
│   └── states/
│
├── tests/
│   │
│   ├── agents/
│   │   ├── test_ocr.py
│   │   ├── test_classification.py
│   │   ├── test_evrak_analysis.py
│   │   ├── test_rag.py
│   │   ├── test_routing.py
│   │   ├── test_validation.py
│   │   └── test_resmi_yazi.py
│   │
│   └── integration/
│       └── debug_pipeline.py
│
├── requirements_full.txt
└── README.md
```

---

# 💻 Kurulum

## 1. Projeyi Klonlayın

```bash
git clone <REPOSITORY_URL>
cd biltek.kamu
```

---

## 2. Python Virtual Environment Oluşturun

Windows:

```powershell
python -m venv .venv
```

Aktifleştirin:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 3. Bağımlılıkları Kurun

```powershell
pip install -r requirements_full.txt
```

---

# 🔐 Environment Variables

LLM servisinin çalışması için API anahtarının `.env` içerisinde tanımlanması gerekir.

Örnek:

```env
EVREN_API_KEY=YOUR_API_KEY
```

> API anahtarları GitHub repository içerisine yüklenmemelidir.

`.env` dosyasının `.gitignore` içerisinde olduğundan emin olun.

---

# ▶️ Backend'i Çalıştırma

Proje ana dizinindeyken:

```powershell
.\.venv\Scripts\Activate.ps1
```

Daha sonra:

```powershell
python -m uvicorn backend.app:app --reload --log-level debug
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

# 🌐 Frontend'i Çalıştırma

Yeni bir terminal açın:

```powershell
cd frontend
```

Ardından:

```powershell
python -m http.server 5500
```

Kullanıcı ekranı:

```text
http://127.0.0.1:5500
```

Dashboard:

```text
http://127.0.0.1:5500/dashboard.html
```

---

# 🧪 Test Sistemi

Her ajan bağımsız olarak test edilebilmektedir.

Bu yapı sayesinde bir ajandaki hata tüm pipeline tekrar çalıştırılmadan analiz edilebilir.

## OCR Test

```powershell
python .\tests\agents\test_ocr.py .\test.jpeg
```

---

## Classification Test

```powershell
python .\tests\agents\test_classification.py
```

---

## Evrak Analiz Test

```powershell
python .\tests\agents\test_evrak_analysis.py
```

---

## Mevzuat RAG Test

```powershell
python .\tests\agents\test_rag.py
```

---

## Birim Yönlendirme Test

```powershell
python .\tests\agents\test_routing.py
```

---

## Doğrulama Test

```powershell
python .\tests\agents\test_validation.py
```

---

## Resmi Yazı Test

Otomatik yazı türü:

```powershell
python .\tests\agents\test_resmi_yazi.py
```

Manuel yazı türü ve muhatap:

```powershell
python .\tests\agents\test_resmi_yazi.py talep_yazisi "Burcu KÖKSAL"
```

---

# 🔗 Integration Test

Tüm sistem pipeline'ını uçtan uca test etmek için:

```powershell
python .\tests\integration\debug_pipeline.py .\test.jpeg
```

Integration test sayesinde her katmanın çıktısı ayrı ayrı görüntülenebilir.

```text
OCR
Classification
Evrak Analiz
RAG
Routing
Validation
Resmi Yazı
```

---

# ⏱️ Performans

İşlem süresi belge boyutu, OCR kalitesi, LLM yanıt süresi ve retrieval işlemine göre değişmektedir.

Örnek bir testte yaklaşık çalışma süreleri:

```text
OCR                  ~25-40 sn
Classification       ~1-2 sn
Evrak Analiz         ~6-16 sn
Mevzuat RAG          ~8-13 sn
Birim Yönlendirme    <1 sn
Doğrulama            ~3-8 sn
Resmi Yazı           ~2 sn
```

Bu değerler geliştirme ortamında elde edilen örnek sürelerdir ve donanıma göre değişebilir.

---

# 🔍 İzlenebilir Yapay Zekâ

BİLTEK KAMU'nun temel tasarım prensiplerinden biri yalnızca sonuç üretmek değil, karar sürecini izlenebilir hale getirmektir.

Bu nedenle sistem:

```text
Belge türünü
Confidence değerini
Analiz sonucunu
Mevzuat kaynaklarını
Yönlendirilen birimi
Doğrulama hatalarını
Agent durumlarını
```

ayrı ayrı gösterebilir.

Bu yaklaşım özellikle kamu sistemlerinde yapay zekâ kararlarının kontrol edilebilirliği açısından önemlidir.

---

# 🛡️ Human-in-the-Loop Yaklaşımı

BİLTEK KAMU'nun ürettiği sonuçlar karar destek amacı taşımaktadır.

Özellikle:

- hukuki değerlendirmeler,
- kurum yönlendirmeleri,
- resmi yazılar,
- düşük güvenli sınıflandırmalar

gerektiğinde yetkili personel tarafından kontrol edilebilir.

Doğrulama Agent'ı da bu süreci desteklemek amacıyla geliştirilmiştir.

---

# 📈 Geliştirme Durumu

Projenin mevcut sürümünde temel Multi-Agent mimari, frontend, backend, agent testleri, integration testleri ve sistem izleme Dashboard'u çalışmaktadır.

Aktif iyileştirme alanları arasında:

```text
OCR metadata doğruluğunun artırılması
Classification doğruluğunun geliştirilmesi
RAG retrieval kalitesinin artırılması
Kaynak deduplication
Birim yönlendirme kurallarının iyileştirilmesi
Grounding validator normalizasyonu
Dashboard detay ekranlarının genişletilmesi
Sunucu deployment
Kalıcı dashboard geçmişi
```

bulunmaktadır.

---

# 🎯 Projenin Sağladığı Temel Değer

BİLTEK KAMU tek bir yapay zekâ modeline tüm süreci yaptırmak yerine görevleri uzmanlaşmış ajanlara ayırmaktadır.

```text
OCR → Okur

Classification → Belge türünü belirler

Evrak Analiz → Belgenin anlamını çıkarır

RAG → Mevzuat bilgisini getirir

Routing → Doğru birimi belirler

Validation → Sonuçları kontrol eder

Resmi Yazı → Gerektiğinde resmi metin üretir
```

Bu mimari sayesinde sistem daha:

```text
Modüler
Test edilebilir
İzlenebilir
Geliştirilebilir
Kontrol edilebilir
```

bir yapı sunmaktadır.

---

# 🏆 TEKNOFEST

BİLTEK KAMU, kamu kurumlarındaki belge işleme süreçlerinde yapay zekâ kullanımını daha güvenilir, hızlı ve izlenebilir hale getirmek amacıyla **TEKNOFEST** kapsamında geliştirilmektedir.

---

# 📄 Lisans

Projenin lisanslama modeli ekip ve yarışma gereksinimlerine göre belirlenecektir.

---

<p align="center">
  <b>BİLTEK KAMU</b><br>
  Yapay Zekâ Destekli Çok Ajanlı Kamu Belge Yönetim Sistemi
</p>