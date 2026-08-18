import urllib.request
import os

def generate_turkish_dictionary():
    dict_filename = "frequency_dictionary_tr.txt"
    print("⏳ جاري تحميل معجم الكلمات التركية الأكثر شيوعاً...")

    # رابط مباشر لمعجم معتمد للكلمات التركية مع الترددات الإحصائية
    url = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/tr/tr_50k.txt"
    
    try:
        urllib.request.urlretrieve(url, dict_filename)
        print(f"✅ تم تحميل وتجهيز ملف القاموس بنجاح باسم: '{dict_filename}'!")
    except Exception as e:
        print(f"❌ حدث خطأ أثناء التحميل: {e}")
        # خيار بديل: إنشاء قاموس محلي خفيف يحتوي على مفردات تركية أساسية
        basic_tr_words = """
bir 100000
bu 90000
ve 85000
icin 80000
için 80000
son 50000
veya 45000
yoklama 40000
askerlik 35000
kanunu 30000
geregi 25000
gereği 25000
tarihi 20000
durumu 20000
hakkinda 18000
hakkında 18000
karsi 15000
karşı 15000
belge 12000
belgesi 12000
nüfus 10000
cüzdanı 10000
öğrenci 9000
sağlık 8000
        """
        with open(dict_filename, "w", encoding="utf-8") as f:
            f.write(basic_tr_words.strip())
        print(f"✅ تم إنشاء قاموس محلي أساسي بديل: '{dict_filename}'")

if __name__ == "__main__":
    generate_turkish_dictionary()