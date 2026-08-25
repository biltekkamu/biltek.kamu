## Yapılan Değişiklikler

- Evrak Analiz Agent, yerel `qwen2.5:7b` yerine TEKNOFEST `llm-fast` servisine bağlandı.
- BERTurk 512 token uyarısı düzeltildi.
- Head + Tail tokenizasyonu aktif olarak kullanılmaktadır.
- Evrak Analiz ve Validation süreleri önemli ölçüde hızlandırıldı.

Son test:

```text
OCR: 204.27 sec
Classification: 4.13 sec
Evrak Analysis: 7.96 sec
RAG: 105.22 sec
Validation: 2.07 sec
TOTAL: 323.66 sec
```

## Çalıştırma

```powershell
cd C:\Users\mousa\Desktop\github_work\biltek.kamu

.\.venv\Scripts\Activate.ps1

$env:EVREN_API_KEY="API_KEY"

uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Frontend için yeni terminal:

```powershell
cd C:\Users\mousa\Desktop\github_work\biltek.kamu\frontend

python -m http.server 5500
```

Arayüz:

```text
http://127.0.0.1:5500
```

> `EVREN_API_KEY` GitHub'a yüklenmemelidir.