# generate_mocks.py
import json
from schemas import StandardAgentOutput, DocumentInfo, StandardInput, MetadataInfo, TableItem, VisionInfo

# Mock 1: إخطار تجنيد رسمي (طابق الصورة المطلوبة تماماً)
mock_resmi_yazi = StandardAgentOutput(
    success=True,
    document_info=DocumentInfo(
        document_id="mock_doc_02",
        file_name="askerlik_tebligati.jpg",
        file_type="jpg",
        page_count=1,
        language="tr"
    ),
    input=StandardInput(
        clean_text="T.C. MİLLÎ SAVUNMA BAKANLIĞI ASKERALMA GENEL MÜDÜRLÜĞÜ\n1. Askerlik çağına girmenize rağmen son yoklamanızı yaptırmamanız nedeniyle yoklama kaçağı durumunda bulunmaktasınız...\nBilgilerinize rica ederim.",
        metadata=MetadataInfo(
            sayi="1111",
            tarih="04.02.2016",
            konu="Askerlik Yoklama Bildirimi",
            recipient="İlgili Şahıs"
        ),
        tables=[],
        vision=VisionInfo(
            has_signature=True,
            has_stamp=True
        )
    )
)

# Mock 2: قانون مع جدول تعديلات
mock_kanun = StandardAgentOutput(
    success=True,
    document_info=DocumentInfo(
        document_id="mock_doc_01",
        file_name="7068_Sayili_Kanun.pdf",
        file_type="pdf",
        page_count=1,
        language="tr"
    ),
    input=StandardInput(
        clean_text="7068 SAYILI KANUNA EK VE DEĞİŞİKLİK GETİREN MEVZUATIN VEYA ANAYASA MAHKEMESİ İPTAL KARARLARININ YÜRÜRLÜĞE GİRİŞ TARİHLERİNİ GÖSTERİR LİSTE",
        metadata=MetadataInfo(
            sayi="7068",
            tarih="26/10/2018",
            konu="7068 SAYILI KANUNA EK VE DEĞİŞİKLİK GETİREN MEVZUAT LİSTESİ",
            recipient=None
        ),
        tables=[
            TableItem(
                page_number=1,
                headers=[
                    "Değiştiren Kanunun/KHK'nin veya İptal Eden Anayasa Mahkemesi Kararının Numarası",
                    "Kanunun Değişen veya İptal Edilen Maddeleri",
                    "Yürürlüğe Giriş Tarihi"
                ],
                rows=[
                    ["7148", "8, 10, 14, 19, 20, 21, 26, 27, 34, Geçici Madde 1, Ekli (3) Sayılı Çizelge", "26/10/2018"],
                    ["7161", "8, Geçici Madde 2", "18/1/2019"],
                    ["7196", "17, 18, 21, 24, Ekli (3) Sayılı Çizelge", "24/12/2019"],
                    ["Anayasa Mahkemesinin 26/1/2022 tarihli ve E.:2021/22; K.:2022/6 sayılı kararı", "8", "1/4/2022"],
                    ["7533", "8, 29", "30/11/2024"]
                ]
            )
        ],
        vision=VisionInfo(
            has_signature=False,
            has_stamp=False
        )
    )
)

with open("mock_resmi_yazi.json", "w", encoding="utf-8") as f:
    f.write(mock_resmi_yazi.model_dump_json(indent=2))

with open("mock_kanun.json", "w", encoding="utf-8") as f:
    f.write(mock_kanun.model_dump_json(indent=2))

print("✅ تم إنشاء وتحديث ملفات الموك لتطابق الهيكل المطلوب تماماً.")