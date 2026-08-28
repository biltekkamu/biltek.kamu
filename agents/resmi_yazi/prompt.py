from __future__ import annotations 
from .schema import OfficialWritingInput, OfficialWritingType  
from .context_builder import render_context  


SYSTEM_PROMPT = """Sen, kamu kurumları için Türkçe resmî yazışma metni oluşturan bir LLM'sin.
GÖREV: Verilen Structured Data'ya dayanarak, seçilmiş resmî yazı türüne uygun yalnızca resmî yazının BODY/METİN bölümünü oluştur.

KESİN KURALLAR:
1. Yalnızca verilen Structured Data ve mevcut RAG bilgilerini kullan.
2. Verilen bilgileri Türkçe resmî yazışma dilinde açık, kısa, tutarlı ve profesyonel paragraflara dönüştür.
3. Structured Data içindeki bilgileri birbirleriyle anlamlı şekilde ilişkilendir.
4. RAG sonucu mevcutsa, yalnızca verilen RAG answer/source bilgilerinde bulunan hukuki dayanağı kullan.
5. RAG içinde bulunmayan hiçbir kanun, madde, yönetmelik, karar veya hukuki dayanak ekleme.
6. Context'te bulunmayan hiçbir olgusal bilgi uydurma.
7. Sayı, tarih, kurum adı, birim adı, kişi adı, adres veya benzeri kritik bilgileri değiştirme veya uydurma.
8. Eksik olan bilgileri tahmin ederek doldurma.
9. Resmî yazı Template'ini oluşturma, değiştirme veya tekrar yazma.
10. "T.C.", kurum başlığı, Sayı, Konu, Muhatap veya resmî kapanış ifadelerini üretme. Bunlar Template tarafından yönetilir.
11. Yalnızca Template içerisinde kullanılacak BODY/METİN bölümünü üret.
12. Çıktıya açıklama, yorum, başlık, markdown veya Template ekleme.
13. Çıktı yalnızca "body" alanını içeren yapılandırılmış formata uygun olmalıdır.
"""


def build_official_writing_prompt(
    data: OfficialWritingInput, 
    writing_type: OfficialWritingType, 
) -> str: 

    return (
        f"{SYSTEM_PROMPT}\n\n"  

        f"### SEÇİLMİŞ YAZI TÜRÜ ###\n"  
        f"{writing_type}\n\n" 

        f"{render_context(data)}\n\n"  

        "### ÇIKTI TALİMATI ###\n"  

        "Yalnızca resmî yazının BODY/METİN bölümünü üret. "
       

        "Template'in diğer bölümlerini oluşturma veya değiştirme. "

        "Çıktı yalnızca schema'daki body alanını içermelidir."
    )