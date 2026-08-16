# Kamu Hukuk Asistanı — Kısa Proje Raporu

## Proje Özeti

Bu proje, Türkiye'deki kamu mevzuatı üzerinde soru-cevap hizmeti sunan RAG (Retrieval-Augmented Generation) tabanlı bir yapay zekâ uygulamasıdır. Kullanıcıların kanunlar ve maddeler hakkında Türkçe sorular sormasını, ilgili mevzuat parçalarının bulunmasını ve kaynaklı yanıt üretilmesini amaçlar.

## Kullanılan Teknolojiler

- **FastAPI:** REST API ve Swagger dokümantasyonu
- **ChromaDB:** Mevzuat metinlerinin vektör veritabanı
- **Sentence Transformers:** Çok dilli metin embedding modeli
- **BM25:** Anahtar kelime tabanlı arama
- **CrossEncoder:** Arama sonuçlarının yeniden sıralanması
- **Ollama / Gemma:** Yerel dil modeli ile yanıt üretimi
- **HTML, CSS, JavaScript:** Sohbet arayüzü

## Çalışma Mantığı

1. Kanun metinleri maddelere göre küçük parçalara ayrılır.
2. Bu parçalar embedding'e dönüştürülerek ChromaDB'ye kaydedilir.
3. Kullanıcı bir soru gönderdiğinde soru gerekirse hukuki arama sorgusuna dönüştürülür.
4. Vektör araması ve BM25 sonuçları RRF yöntemiyle birleştirilir.
5. En ilgili sonuçlar reranker ile yeniden sıralanır.
6. Seçilen mevzuat parçaları bağlam olarak Gemma modeline gönderilir.
7. Sistem kaynaklara dayalı cevabı ve kullanılan kaynak bilgilerini döndürür.

## Temel API Uç Noktaları

| Metot | Adres | Açıklama |
|---|---|---|
| GET | `/health` | Sistem ve indeks durumunu gösterir. |
| POST | `/query` | Kaynaklı normal soru-cevap isteği. |
| POST | `/query/stream` | Cevabı parça parça (streaming) gönderir. |
| GET | `/cache/stats` | Önbellek istatistiklerini verir. |
| DELETE | `/cache/clear` | Önbelleği temizler. |
| GET | `/chat` | Web sohbet arayüzünü açar. |

## Proje Yapısı

- `reda_RAG/app.py`: FastAPI uygulaması ve API uç noktaları
- `reda_RAG/rag_service.py`: Arama, sıralama, bağlam oluşturma ve LLM işlemleri
- `reda_RAG/ingest_chunks.py`: Chunk verilerini ChromaDB'ye aktarma
- `reda_RAG/rechunk.py`: Mevzuat metinlerini yeniden parçalara ayırma
- `reda_RAG/chunks/`: Kanunlara ait parçalanmış kaynak veriler
- `reda_RAG/chroma_db/`: Yerel vektör veritabanı
- `reda_RAG/chat.html`: Tarayıcı tabanlı sohbet arayüzü

## Çalıştırma

```bash
cd reda_RAG
pip install -r requirements.txt
python ingest_chunks.py
python app.py
```

Uygulama varsayılan olarak `http://localhost:8000` adresinde çalışır. API dokümantasyonuna `/docs`, sohbet arayüzüne `/chat` üzerinden erişilebilir.

## Notlar

- Sistem hukuki danışmanlık yerine mevzuata dayalı bilgi sunmak için tasarlanmıştır.
- Yanıt kalitesi, güncel ve doğru mevzuat verilerinin indekslenmesine bağlıdır.
- Üretim ortamında CORS ayarları, erişim kontrolü, loglama ve hata yönetimi ayrıca sıkılaştırılmalıdır.
