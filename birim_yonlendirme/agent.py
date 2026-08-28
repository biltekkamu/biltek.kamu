import re
from typing import Any, Dict, List, Tuple


class IntelligentUnitRouter:
    

    TAXONOMY = {
        "Ceza İşleri Birimi": {
            "priority_phrases": [
                "agir ceza", "asliye ceza", "sulh ceza", "cumhuriyet bassavciligi",
                "ceza muhakemesi kanunu", "cmk", "turk ceza kanunu", "tck",
                "uyusturucu maddelerin murakabesi", "uyusturucu ticareti", "kenevir ekimi sucu",
                "suc duyurusu", "iddianame", "kamu davasi", "ceza infaz", "sorusturma evresi",
                "kovusturma evresi", "adli kontrol", "tutuklama karari", "yakalama emri",
                "araca elkoyma", "musadere karari", "hapis cezasi", "adli para cezasi"
            ],
            "keywords": [
                "suc", "ceza", "uyusturucu", "esrar", "morfin", "kokain", "kenevir", "hirsizlik",
                "yaralama", "dolandiricilik", "yagma", "cinayet", "ruhsatsiz", "kovusturma",
                "sorusturma", "hukumlu", "tutuklu", "gozalti", "sanik", "magdur", "musteki",
                "fezleke", "infaz", "adli tip", "kacakcilik sucu", "orgutlu suc"
            ],
            "scope": "Ceza Hukuku, Suç Soruşturmaları, Adli Kovuşturma ve İnfaz İşlemleri",
            "base_conf": 0.96,
        },
        "Hukuk İşleri Birimi": {
            "priority_phrases": [
                "hukuk mahkemesi", "hukuk mahkemeleri", "asliye hukuk", "sulh hukuk",
                "asliye ticaret", "ticaret mahkemesi", "icra hukuk", "aile mahkemesi",
                "is mahkemesi", "tuketici mahkemesi", "fikri sinai haklar", "adli yargi ilk derece",
                "hukuk muhakemeleri kanunu", "hmk", "turk ticaret kanunu", "ttk", "borclar kanunu",
                "alacak davasi", "tazminat davasi", "istisnai harb", "tebaa", "mutekabiliyet",
                "kanun metni", "kanun hukmunde kararname", "khk", "mevzuat degisikligi",
                "anayasa mahkemesi", "danistay", "yargitay", "hukuki gorus", "ihtarname"
            ],
            "keywords": [
                "dava", "itiraz", "hukuk", "hukuki", "sozlesme", "mahkeme", "mahkemeleri",
                "icra", "ihtar", "mutalaa", "kanun", "tazminat", "yargilama", "arabuluculuk",
                "adli yargi", "vekalet", "istinaf", "temyiz", "hakimlik", "savunma", "vekil", "protokol"
            ],
            "scope": "Hukuk ve Ticaret Mahkemeleri Mevzuatı, Genel Hukuk ve Müşavirlik İşlemleri",
            "base_conf": 0.94,
        },
        "Gümrük ve Dış Ticaret Birimi": {
            "priority_phrases": [
                "gumruk kanunu", "gumruk idaresi", "gumruk bolgesi", "serbest bolge",
                "gumruk vergisi", "gumruk tarifesi", "ozet beyan", "dahilde isleme",
                "haricte isleme", "transit rejimi", "antrepo rejimi", "kacakcilikla mucadele",
                "dis ticaret mustesarligi", "mense sahadaetnamesi", "gumruk muhafaza"
            ],
            "keywords": [
                "gumruk", "ithalat", "ihracat", "tarife", "transit", "kacakcilik",
                "antrepo", "beyanname", "mense", "esya", "dis ticaret", "konusimento",
                "tasfiye", "gumruk musaviri", "cif", "fob", "navlun", "dolasim belgesi"
            ],
            "scope": "4458 Sayılı Gümrük Mevzuatı, İthalat/İhracat ve Dış Ticaret Rejimleri",
            "base_conf": 0.95,
        },
        "Mali Hizmetler Birimi": {
            "priority_phrases": [
                "kamu ihale kanunu", "4734 sayili", "5018 sayili", "kamu mali yonetimi",
                "kesin hesap", "butce tertibi", "hakedis raporu", "vergi usul kanunu",
                "vuk", "harcama yetkilisi", "dogrudan temin", "muhasebe kaydi", "gelir idaresi"
            ],
            "keywords": [
                "vergi", "odeme", "borc", "mali", "butce", "harcama", "fatura",
                "muhasebe", "ihale", "hakedis", "tahsilat", "avans", "teminat",
                "bilanco", "gelir", "gider", "finans", "harcirah", "kesinti", "kdv", "otv"
            ],
            "scope": "Bütçe Yönetimi, Kamu İhaleleri, Muhasebe ve Mali Denetim",
            "base_conf": 0.93,
        },
        "İnsan Kaynakları Birimi": {
            "priority_phrases": [
                "yillik izin", "mazeret izni", "gorevde yukselme", "hizmet ici egitim",
                "devlet memurlari kanunu", "657 sayili", "ozluk dosyasi", "disiplin sorusturmasi",
                "tayin talebi", "nakil islemi", "kidem tazminati", "gorevlendirme", "sozlesmeli personel"
            ],
            "keywords": [
                "personel", "tayin", "terfi", "izin", "disiplin", "ozluk", "maas",
                "kadro", "atama", "staj", "sendika", "istifa", "emeklilik", "sicil",
                "bordro", "ise alim", "mulakat", "performans", "hizmet cetveli"
            ],
            "scope": "Personel Özlük Hakları, İdari İzin, Kadro ve Disiplin Süreçleri",
            "base_conf": 0.94,
        },
        "Sağlık Hizmetleri ve İlaç Birimi": {
            "priority_phrases": [
                "saglik bakanligi", "tibbi mustahzarat", "eczaneler hakkinda kanun",
                "ilac ve tibbi cihaz", "titck", "tibbi urun", "saglik beyani",
                "halk sagligi", "tabip odasi", "hasta haklari", "tibbi izin"
            ],
            "keywords": [
                "saglik", "ilac", "eczane", "eczaci", "recete", "tabip", "hekim",
                "hastane", "tibbi", "tedavi", "ruhsatlandirma", "zehir", "toksik",
                "klinik", "morfin", "afyon", "asi", "tibbi sarf"
            ],
            "scope": "Sağlık Mevzuatı, Eczacılık, Tıbbi Ürünler ve Halk Sağlığı İşlemleri",
            "base_conf": 0.94,
        },
        "Tarım, Orman ve Hayvancılık Birimi": {
            "priority_phrases": [
                "tarim ve orman bakanligi", "toprak mahsullleri ofisi", "tmo",
                "kenevir yetistiriciligi", "tohumculuk kanunu", "ciftci kayit sistemi",
                "cks", "orman kanunu", "zirai mucadele", "gida guvenligi"
            ],
            "keywords": [
                "tarim", "orman", "kenevir", "tohum", "hasat", "ekim", "ziraat",
                "ciftci", "hayvancilik", "mera", "arazi", "zirai", "gida", "veteriner", "bitki"
            ],
            "scope": "Tarımsal Üretim, Orman Mevzuatı, Kenevir Yetiştiriciliği ve Gıda Kontrolü",
            "base_conf": 0.93,
        },
        "Bilgi İşlem Birimi": {
            "priority_phrases": [
                "siber guvenlik", "bilgi guvenligi", "kvkk uyumu", "veri tabani yonetimi",
                "ag altyapisi", "e-devlet entegrasyonu", "sunucu bakimi", "erisim yetkilendirme",
                "yazilim gelistirme", "api entegrasyonu", "guvenlik duvari", "bilgi islem dairesi"
            ],
            "keywords": [
                "yazilim", "donanim", "sunucu", "ag", "bilgi islem", "veritabani",
                "e-devlet", "erisim", "sistem", "api", "entegrasyon", "bilisim",
                "lisans", "kod", "backup", "yedekleme", "firewall", "domain", "ip"
            ],
            "scope": "Bilişim Sistemleri, Ağ Altyapısı, Yazılım ve Bilgi Güvenliği",
            "base_conf": 0.92,
        },
        "Çevre, Şehircilik ve İmar Birimi": {
            "priority_phrases": [
                "imar plani", "yapi ruhsati", "kentsel donusum", "cevre etki degerlendirmesi",
                "ced raporu", "kamulastirma karari", "iskan ruhsati", "yapi denetim",
                "tapu ve kadastro", "tabiat varliklari", "atik yonetimi"
            ],
            "keywords": [
                "imar", "ruhsat", "insaat", "cevre", "atik", "donusum", "harita",
                "kamulastirma", "parsel", "ada", "kacak yapi", "iskan", "hafriyat",
                "tapu", "kadastro", "hava kalitesi", "gurultu"
            ],
            "scope": "İmar Planlama, Yapı Ruhsatları, Çevre Koruma ve Kentsel Dönüşüm",
            "base_conf": 0.93,
        },
        "Nüfus ve Vatandaşlık İşleri Birimi": {
            "priority_phrases": [
                "nufus ve vatandaslik", "turk vatandasligi kanunu", "nufus kayit ornegi",
                "kimlik karti basvurusu", "pasaport islemleri", "yabancilar ve uluslararasi koruma",
                "ikamet izni", "mavi kart", "adres beyani"
            ],
            "keywords": [
                "nufus", "vatandaslik", "pasaport", "kimlik", "dogum", "olum", "evlenme",
                "bosanma", "ikamet", "yabanci", "goc", "tebaa", "kayit duzeltme", "soyadi"
            ],
            "scope": "Nüfus Kayıtları, Vatandaşlık İşlemleri, Pasaport ve Yabancılar Rejimi",
            "base_conf": 0.94,
        },
        "Sosyal Hizmetler ve Yardım Birimi": {
            "priority_phrases": [
                "sosyal yardim", "ihtiyac sahibi", "engelli maasi", "evde bakim ucreti",
                "ogrenci bursu", "sosyal guvenlik kurumu", "sgk", "sosyal hizmet merkezi",
                "sehit ve gazi", "cocuk koruma kanunu", "kadin konukevi"
            ],
            "keywords": [
                "yardim", "engelli", "yasli", "cocuk", "burs", "muhtac", "yoksulluk",
                "sosyal", "bagis", "gida yardimi", "huzurevi", "siginma", "bakim", "sosyal guvence"
            ],
            "scope": "Sosyal Yardımlar, Engelli/Yaşlı Hizmetleri, Aile ve Çocuk Destekleri",
            "base_conf": 0.92,
        },
        "Eğitim ve Öğretim Hizmetleri Birimi": {
            "priority_phrases": [
                "milli egitim bakanligi", "yuksekogretim kurulu", "yok", "ogrenci isleri",
                "denklik belgesi", "diploma tescil", "ogretim programi", "okul oncesi egitim",
                "ozel ogretim kurumlari", "yaygin egitim"
            ],
            "keywords": [
                "egitim", "ogretim", "okul", "universite", "ogrenci", "ogretmen", "akademik",
                "diploma", "denklik", "mufredat", "sinav", "kayit kabul", "tez", "fakulte"
            ],
            "scope": "Milli Eğitim, Yükseköğretim, Denklik ve Akademik Öğrenci İşleri",
            "base_conf": 0.93,
        },
        "Ulaştırma ve Altyapı Birimi": {
            "priority_phrases": [
                "karayollari trafik kanunu", "ulastirma ve altyapi", "karayolu tasima yonetmeligi",
                "k yetki belgesi", "src belgesi", "demiryolu ulasimi", "sivil havacilik",
                "denizcilik mevzuati", "liman baskanligi"
            ],
            "keywords": [
                "ulasim", "tasima", "trafik", "arac tescil", "plaka", "ehliyet", "surucu",
                "otoyol", "kopru", "liman", "gemi", "havalimani", "lojistik", "sefer"
            ],
            "scope": "Ulaştırma Mevzuatı, Trafik Düzenlemeleri, Taşımacılık ve Altyapı",
            "base_conf": 0.92,
        },
        "Destek Hizmetleri ve Evrak Birimi": {
            "priority_phrases": [
                "arac kiralama", "tasinir kayit kontrol", "bina bakim onarim", "fiziki guvenlik",
                "evrak kayit dagitim", "lojistik destek", "genel evrak", "arsivleme yonetmeligi"
            ],
            "keywords": [
                "bina", "bakim", "onarim", "arac", "ulasim", "guvenlik", "temizlik",
                "lojistik", "arsiv", "kiralama", "depo", "fiziki", "tasinir", "yakit", "evrak kayit"
            ],
            "scope": "İdari İşler, Taşınır Mal Yönetimi, Arşiv ve Destek Hizmetleri",
            "base_conf": 0.88,
        }
    }

    @staticmethod
    def normalize_text(text: str) -> str:
        
        if not text:
            return ""
        mapping = {
            'İ': 'i', 'I': 'i', 'ı': 'i', 'i̇': 'i',
            'Ğ': 'g', 'ğ': 'g',
            'Ü': 'u', 'ü': 'u',
            'Ş': 's', 'ş': 's',
            'Ö': 'o', 'ö': 'o',
            'Ç': 'c', 'ç': 'c'
        }
        for tr_char, eng_char in mapping.items():
            text = text.replace(tr_char, eng_char)
        text = text.lower()
        return re.sub(r'[^a-z0-9\s]', ' ', text).strip()

    @classmethod
    def calculate_score(
        cls, 
        config: Dict[str, Any], 
        core_text: str, 
        detail_text: str
    ) -> Tuple[int, List[str]]:
      
        total_score = 0
        matched_indicators = []

       
        for phrase in config.get("priority_phrases", []):
            norm_phrase = cls.normalize_text(phrase)
            pattern = rf"\b{re.escape(norm_phrase)}\b"
            
            core_matches = len(re.findall(pattern, core_text))
            if core_matches > 0:
                total_score += core_matches * 16
                matched_indicators.append(phrase)

            detail_matches = len(re.findall(pattern, detail_text))
            if detail_matches > 0:
                total_score += detail_matches * 5
                if phrase not in matched_indicators:
                    matched_indicators.append(phrase)

     
        for kw in config.get("keywords", []):
            norm_kw = cls.normalize_text(kw)
            pattern = rf"\b{re.escape(norm_kw)}\b"

            core_kw_matches = len(re.findall(pattern, core_text))
            if core_kw_matches > 0:
                total_score += core_kw_matches * 6
                matched_indicators.append(kw)

            detail_kw_matches = len(re.findall(pattern, detail_text))
            if detail_kw_matches > 0:
                total_score += detail_kw_matches * 1
                if kw not in matched_indicators:
                    matched_indicators.append(kw)

        return total_score, matched_indicators


def route_unit(
    evrak_analysis: Dict[str, Any], 
    rag_result: Dict[str, Any] = None
) -> Dict[str, Any]:
   
    if not isinstance(evrak_analysis, dict):
        evrak_analysis = {}
    if not isinstance(rag_result, dict):
        rag_result = {}

   
    doc_type = evrak_analysis.get("document_type", {})
    doc_type_label = str(doc_type.get("label", "")) if isinstance(doc_type, dict) else str(doc_type)
    topic = str(evrak_analysis.get("topic", ""))
    purpose = str(evrak_analysis.get("purpose", ""))
    intent = str(evrak_analysis.get("intent", ""))

    core_raw = f"{doc_type_label} {topic} {purpose} {intent}"
    core_text = IntelligentUnitRouter.normalize_text(core_raw)

    
    summary = str(evrak_analysis.get("summary", ""))
    rag_answer = str(rag_result.get("answer", ""))
    entities = " ".join([str(v) for v in evrak_analysis.get("entities", {}).values()])

    detail_raw = f"{summary} {rag_answer} {entities}"
    detail_text = IntelligentUnitRouter.normalize_text(detail_raw)

    scores: Dict[str, int] = {}
    indicators: Dict[str, List[str]] = {}

    for dept_name, config in IntelligentUnitRouter.TAXONOMY.items():
        score, matches = IntelligentUnitRouter.calculate_score(config, core_text, detail_text)
        if score > 0:
            scores[dept_name] = score
            indicators[dept_name] = matches

    if scores:
        best_dept = max(scores, key=scores.get)
        best_score = scores[best_dept]
        dept_info = IntelligentUnitRouter.TAXONOMY[best_dept]

        confidence = min(
            round(dept_info["base_conf"] + (min(best_score, 50) / 100) * 0.04, 2),
            0.99
        )

        top_terms = indicators[best_dept][:3]
        terms_str = ", ".join([f"'{t}'" for t in top_terms]) if top_terms else "ilgili mevzuat"
        
        reason = (
            f"Belge konusu ve içeriği ({dept_info['scope']}) kapsamında tespit edilmiştir. "
            f"Metinde yer alan {terms_str} gibi temel kavramlar uyarınca işlemlerin ilgili birimce yürütülmesi uygundur."
        )

        return {
            "selected_department": best_dept,
            "recommended_unit": best_dept,
            "reason": reason,
            "confidence": confidence
        }

    return {
        "selected_department": "Hukuk İşleri Birimi",
        "recommended_unit": "Hukuk İşleri Birimi",
        "reason": "Belge genel mevzuat ve hukuki inceleme gerektirdiği için ilgili birime yönlendirilmiştir.",
        "confidence": 0.80
    }