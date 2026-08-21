import json
from datasets import load_dataset

print("🔄 جاري الاتصال بمستودع Hugging Face للبدء بسحب البيانات...")

# تحميل الداتاسيت بأسلوب Streaming لعدم استهلاك مساحة القرص
dataset = load_dataset("erdem-erdem/Turkish-Law-Documents-700k-clustered", split="train", streaming=True)

# 1. تحديد الفئات والكلمات المفتاحية القانونية لكل فئة
categories_config = {
    "izin_belgesi": [
        "izin belgesi", "izin belgesinin", "çalışma izni", "faaliyet izin", "ruhsat"
    ],
    "onay_belgesi": [
        "onay belgesi", "onaylanmasına", "onay belgesinin", "uygunluk onayı", "onay yazısı"
    ],
    "beyan_beyanname": [
        "beyanname", "beyannamesi", "mal bildirimi", "vergi beyannamesi", "yeminli beyan"
    ],
    "tutanak": [
        "tutanak", "tutanağı", "duruşma tutanağı", "tespit tutanağı", "zabıt varakası"
    ],
    "basvuru_belgesi": [
        "başvuru belgesi", "başvuru formu", "başvurusu dilekçesi", "müracaat belgesi", "başvuru metni"
    ]
}

# 2. تحديد العدد المطلوب لكل فئة (مثلاً 25 وثيقة لكل فئة لموازنة الداتا)
TARGET_PER_CATEGORY = 25

collected_data = {cat: [] for cat in categories_config}
counts = {cat: 0 for cat in categories_config}

for item in dataset:
    text = item.get("text", "")
    if len(text.strip()) < 120:
        continue

    lower_text = text.lower()

    for cat_name, keywords in categories_config.items():
        if counts[cat_name] < TARGET_PER_CATEGORY:
            # التحقق من تطابق أي من الكلمات المفتاحية
            if any(kw in lower_text for kw in keywords):
                collected_data[cat_name].append({
                    "text": text.strip(),
                    "label": cat_name
                })
                counts[cat_name] += 1
                print(f"✅ [{cat_name}] تم جمع: {counts[cat_name]}/{TARGET_PER_CATEGORY}")
                break  # الانتقال للوثيقة التالية لمنع التكرار بين الفئات

    # التوقف عند اكتمال جميع الفئات بالعدد المطلوب
    if all(count >= TARGET_PER_CATEGORY for count in counts.values()):
        print("\n🎯 اكتمل جمع العدد المطلوب لجميع الفئات بنجاح!")
        break

# 3. حفظ البيانات في ملف منفصل
output_file = "extra_balanced_dataset.jsonl"
with open(output_file, "w", encoding="utf-8") as f:
    for cat_name, docs in collected_data.items():
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

print(f"\n📁 تم حفظ البيانات الجديدة بالكامل داخل: {output_file}")