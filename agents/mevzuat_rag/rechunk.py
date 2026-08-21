"""
rechunk.py — إعادة تقسيم النصوص القانونية التركية بشكل ذكي

المشكلة القديمة: chunks ثابتة 500 حرف → تقطع المواد في المنتصف
الحل: تقسيم على حدود المواد الحقيقية مع overlap بين الـ chunks

الاستخدام:
    python rechunk.py                        # يعيد معالجة كل الملفات
    python rechunk.py --file tck.json        # ملف واحد فقط
    python rechunk.py --preview              # معاينة بدون حفظ
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("rechunk")

# ─── إعدادات ───────────────────────────────────────────────────────────────────

CHUNKS_DIR     = Path("chunks")
OUTPUT_DIR     = Path("chunks_v2")
MAX_CHARS      = 1200   # أقصى حجم chunk
MIN_CHARS      = 80     # أدنى حجم chunk (نتجاهل ما هو أصغر)
OVERLAP_CHARS  = 150    # تداخل بين الـ chunks للحفاظ على السياق

# أنماط فواصل المواد القانونية التركية
ARTICLE_PATTERNS = re.compile(
    r"""
    (?:^|\n)                          # بداية سطر
    (?:
        (?:Madde|MADDE)\s+\d+\s*[-–] # Madde 86- أو MADDE 86 –
      | (?:Madde|MADDE)\s+\d+\s*\(   # Madde 86 (1)
      | (?:Ek\s+Madde|Geçici\s+Madde)\s+\d+  # Ek Madde / Geçici Madde
      | MADDE\s+\d+\s                 # MADDE 86 (بمسافة)
    )
    """,
    re.VERBOSE | re.MULTILINE,
)

# أنماط الأقسام والفصول
SECTION_PATTERNS = re.compile(
    r"""
    (?:^|\n)
    (?:
        [A-ZÜĞIŞÖÇ]{4,}\s+(?:BÖLÜM|KISIM|BAŞLIK)  # فصل بالأحرف الكبيرة
      | (?:BİRİNCİ|İKİNCİ|ÜÇÜNCÜ|DÖRDÜNCÜ|BEŞİNCİ|
           ALTINCI|YEDİNCİ|SEKİZİNCİ|DOKUZUNCU|ONUNCU)
        \s+(?:BÖLÜM|KISIM|MADDE)
    )
    """,
    re.VERBOSE | re.MULTILINE,
)


# ─── منطق التقسيم ──────────────────────────────────────────────────────────────

def find_split_points(text: str) -> list[int]:
    """
    يجد مواقع الفصل المثلى في النص:
    1. حدود المواد (Madde X)
    2. حدود الأقسام (BÖLÜM / KISIM)
    3. نهاية الفقرات (سطر فارغ)
    """
    points = set()

    # حدود المواد — الأولوية القصوى
    for m in ARTICLE_PATTERNS.finditer(text):
        points.add(m.start())

    # حدود الأقسام
    for m in SECTION_PATTERNS.finditer(text):
        points.add(m.start())

    # فقرات فارغة كبديل إذا لم تكن هناك مواد
    for m in re.finditer(r"\n\n+", text):
        points.add(m.start())

    return sorted(points)


def split_text(text: str, source_name: str) -> list[dict]:
    """
    يقسّم النص إلى chunks ذكية مع overlap.
    """
    text = text.strip()
    if not text:
        return []

    split_points = find_split_points(text)

    # إذا ما في فواصل — قسّم بحجم ثابت مع overlap
    if not split_points:
        return _fixed_split(text, source_name)

    # أنشئ قطع أولية بين نقاط الفصل
    raw_segments: list[str] = []
    prev = 0
    for pt in split_points:
        if pt > prev:
            seg = text[prev:pt].strip()
            if seg:
                raw_segments.append(seg)
        prev = pt
    # آخر قطعة
    if prev < len(text):
        seg = text[prev:].strip()
        if seg:
            raw_segments.append(seg)

    # دمج القطع القصيرة جداً مع التالية، وتقسيم القطع الطويلة
    chunks: list[dict] = []
    buffer = ""
    chunk_index = 0

    for seg in raw_segments:
        # قطعة صغيرة جداً — ادمجها مع الـ buffer
        if len(seg) < MIN_CHARS:
            buffer = (buffer + "\n\n" + seg).strip() if buffer else seg
            continue

        # إذا إضافة القطعة ستجعل الـ buffer كبيراً جداً
        if buffer and len(buffer) + len(seg) > MAX_CHARS:
            # احفظ الـ buffer الحالي
            if len(buffer) >= MIN_CHARS:
                chunks.append(_make_chunk(buffer, chunk_index, source_name))
                chunk_index += 1
            # أضف overlap من نهاية الـ buffer
            overlap = buffer[-OVERLAP_CHARS:] if len(buffer) > OVERLAP_CHARS else buffer
            buffer = (overlap + "\n\n" + seg).strip()
        else:
            buffer = (buffer + "\n\n" + seg).strip() if buffer else seg

        # إذا القطعة الحالية نفسها كبيرة جداً
        while len(buffer) > MAX_CHARS:
            # قسّمها عند أقرب فاصل جملة قبل MAX_CHARS
            cut = _find_sentence_boundary(buffer, MAX_CHARS)
            part = buffer[:cut].strip()
            if len(part) >= MIN_CHARS:
                chunks.append(_make_chunk(part, chunk_index, source_name))
                chunk_index += 1
            # overlap
            overlap = buffer[max(0, cut - OVERLAP_CHARS):cut]
            buffer = (overlap + "\n" + buffer[cut:]).strip()

    # ما تبقى في الـ buffer
    if buffer and len(buffer) >= MIN_CHARS:
        chunks.append(_make_chunk(buffer, chunk_index, source_name))

    return chunks


def _fixed_split(text: str, source_name: str) -> list[dict]:
    """تقسيم ثابت مع overlap — fallback إذا ما في أنماط قانونية."""
    chunks = []
    start = 0
    idx = 0
    while start < len(text):
        end = min(start + MAX_CHARS, len(text))
        if end < len(text):
            end = _find_sentence_boundary(text, end)
        part = text[start:end].strip()
        if len(part) >= MIN_CHARS:
            chunks.append(_make_chunk(part, idx, source_name))
            idx += 1
        start = end - OVERLAP_CHARS
        if start >= len(text):
            break
    return chunks


def _find_sentence_boundary(text: str, pos: int) -> int:
    """يجد أقرب نهاية جملة قبل pos."""
    for boundary in [". ", ".\n", "! ", "!\n", ") ", ")\n"]:
        idx = text.rfind(boundary, max(0, pos - 200), pos)
        if idx != -1:
            return idx + len(boundary)
    # إذا ما لقى — انقطع عند مسافة
    idx = text.rfind(" ", max(0, pos - 100), pos)
    return idx if idx != -1 else pos


def _make_chunk(text: str, index: int, source: str) -> dict:
    return {
        "chunk_id": index,
        "source":   source,
        "text":     text,
        "char_count": len(text),
        # استخرج رقم المادة إذا موجود في بداية الـ chunk
        "madde": _extract_madde(text),
    }


def _extract_madde(text: str) -> str | None:
    """يستخرج رقم المادة من النص."""
    m = re.search(r"(?:Madde|MADDE)\s+(\d+)", text[:300])
    return m.group(1) if m else None


# ─── معالجة الملفات ────────────────────────────────────────────────────────────

def process_file(json_path: Path, output_dir: Path, preview: bool = False) -> dict:
    """يعالج ملف JSON واحد ويعيد إحصائياته."""
    raw = json_path.read_bytes()
    if not raw.strip():
        logger.warning("فارغ/تالف: %s", json_path.name)
        return {"file": json_path.name, "status": "skipped", "old": 0, "new": 0}

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as e:
        logger.error("JSON hatası: %s — %s", json_path.name, e)
        return {"file": json_path.name, "status": "error", "old": 0, "new": 0}

    if not isinstance(data, list):
        logger.warning("Liste değil: %s", json_path.name)
        return {"file": json_path.name, "status": "skipped", "old": 0, "new": 0}

    # جمّع النص الكامل من الـ chunks القديمة
    full_text = "\n".join(c.get("text", "") for c in data)
    source_name = data[0].get("source", json_path.stem) if data else json_path.stem

    # أعد التقسيم
    new_chunks = split_text(full_text, source_name)

    old_count = len(data)
    new_count = len(new_chunks)

    if not preview:
        out_path = output_dir / json_path.name
        out_path.write_text(
            json.dumps(new_chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    logger.info(
        "%-50s | قديم: %4d → جديد: %4d chunk | متوسط: %d حرف",
        json_path.name[:50],
        old_count,
        new_count,
        sum(c["char_count"] for c in new_chunks) // max(new_count, 1),
    )

    return {"file": json_path.name, "status": "ok", "old": old_count, "new": new_count}


def main() -> None:
    parser = argparse.ArgumentParser(description="إعادة تقسيم الـ chunks القانونية")
    parser.add_argument("--file",    help="معالجة ملف واحد فقط")
    parser.add_argument("--preview", action="store_true", help="معاينة بدون حفظ")
    parser.add_argument("--input",   default=str(CHUNKS_DIR), help="مجلد المدخلات")
    parser.add_argument("--output",  default=str(OUTPUT_DIR), help="مجلد المخرجات")
    args = parser.parse_args()

    input_dir  = Path(args.input)
    output_dir = Path(args.output)

    if not args.preview:
        output_dir.mkdir(parents=True, exist_ok=True)

    if args.file:
        files = [input_dir / args.file]
    else:
        files = sorted(input_dir.glob("*.json"))

    if not files:
        logger.error("Hiç JSON dosyası bulunamadı: %s", input_dir)
        sys.exit(1)

    logger.info("%d dosya işlenecek | MAX=%d | OVERLAP=%d", len(files), MAX_CHARS, OVERLAP_CHARS)
    if args.preview:
        logger.info("PREVIEW MODU — dosya kaydedilmeyecek")

    results = [process_file(f, output_dir, args.preview) for f in files]

    # ملخص
    total_old = sum(r["old"] for r in results)
    total_new = sum(r["new"] for r in results)
    ok_count  = sum(1 for r in results if r["status"] == "ok")

    print("\n" + "═" * 55)
    print(f"  ✅ Başarılı : {ok_count}/{len(results)} dosya")
    print(f"  📦 Eski     : {total_old:,} chunk")
    print(f"  📦 Yeni     : {total_new:,} chunk")
    print(f"  📁 Çıktı    : {output_dir}")
    print("═" * 55)

    if not args.preview:
        print(f"\n🚀 Sonraki adım:")
        print(f"   .env dosyasında CHUNKS_DIR={output_dir} olarak güncelle")
        print(f"   Ardından: python ingest_chunks.py")


if __name__ == "__main__":
    main()
