import os
import sys
from pathlib import Path

# Windows / Paddle stability flags
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"

from dotenv import load_dotenv

load_dotenv()

import cv2
import json
import numpy as np
import re

from paddleocr import PaddleOCR
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Tuple

# =====================================================
# PDF ENGINES (PyMuPDF / pdf2image)
# =====================================================

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False


# =====================================================
# 1. Pydantic Models
# =====================================================

class DocumentInfo(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    page_count: int
    language: str = "tr"


class MetadataInfo(BaseModel):
    sayi: Optional[str] = None
    tarih: Optional[str] = None
    konu: Optional[str] = None
    recipient: Optional[str] = None


class TableItem(BaseModel):
    page_number: int
    headers: List[str]
    rows: List[List[str]]


class VisionInfo(BaseModel):
    has_signature: bool = False
    has_stamp: bool = False


class StandardInput(BaseModel):
    clean_text: str
    metadata: MetadataInfo
    tables: List[TableItem] = []
    vision: VisionInfo


class StandardAgentOutput(BaseModel):
    success: bool = True
    document_info: DocumentInfo
    input: StandardInput


# =====================================================
# 2. Text Normalizer
# =====================================================

class OCRPostProcessor:

    def __init__(self):
        self.glitch_map = {
            "gimenize": "girmenize",
            "ragmen": "rağmen",
            "Türkye": "Türkiye",
            "işlemierine": "işlemlerine",
            "aracge": "aracılığıyla",
            "yapti": "yaptırım",
            "Tã¼rkiye": "Türkiye",
            "tebliÄŸ": "tebliğ",
            "Cüzdani": "Cüzdanı",
            "BAKANLIGI": "BAKANLIĞI",
            "BAŞKANLIGI": "BAŞKANLIĞI",
            "ÍCIN": "İÇİN",
            "GEREKLI": "GEREKLİ",
            "DEČIŞİKLİK": "DEĞİŞİKLİK",
            "DEČİŞÍKLİK": "DEĞİŞİKLİK",
            "YÜRÜRLÜČE": "YÜRÜRLÜĞE",
            "TARİHLERİNi": "TARİHLERİNİ",
            "GETÍREN": "GETİREN",
        }

    def clean_text(self, text: str) -> str:
        for bad, good in self.glitch_map.items():
            text = text.replace(bad, good)

        text = re.sub(r"^(\d+)([A-Za-zĞÜŞİÖÇğüşiöç])", r"\1. \2", text)
        return re.sub(r"\s+", " ", text).strip()


# =====================================================
# 3. Vision Detector
# =====================================================

class VisionDetector:

    @staticmethod
    def detect_stamp_and_signature(images: List[np.ndarray]) -> Tuple[bool, bool]:
        stamp_detected = False
        sig_detected = False

        for img in images:
            if img is None:
                continue

            h, w = img.shape[:2]
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV) if len(img.shape) == 3 else None

            if hsv is not None:
                lower_red1 = np.array([0, 70, 50])
                upper_red1 = np.array([10, 255, 255])
                lower_red2 = np.array([170, 70, 50])
                upper_red2 = np.array([180, 255, 255])

                red_mask = cv2.inRange(hsv, lower_red1, upper_red1) | cv2.inRange(hsv, lower_red2, upper_red2)
                if cv2.countNonZero(red_mask) > 1500:
                    stamp_detected = True

                lower_blue = np.array([90, 50, 50])
                upper_blue = np.array([135, 255, 255])
                blue_mask = cv2.inRange(hsv, lower_blue, upper_blue)

                bottom_blue_mask = blue_mask[int(h * 0.35):h, :]
                if cv2.countNonZero(bottom_blue_mask) > 300:
                    sig_detected = True

            if not sig_detected:
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
                bottom_region = gray[int(h * 0.40):int(h * 0.85), :]
                blur = cv2.GaussianBlur(bottom_region, (5, 5), 0)
                thresh = cv2.adaptiveThreshold(
                    blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
                )
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                for cnt in contours:
                    area = cv2.contourArea(cnt)
                    if 1200 < area < 15000:
                        x, y, cw, ch = cv2.boundingRect(cnt)
                        if ch == 0:
                            continue
                        ratio = float(cw) / ch
                        if 0.6 < ratio < 3.5:
                            sig_detected = True
                            break

        return stamp_detected, sig_detected


# =====================================================
# 4. Deterministic Table Extractor
# =====================================================

class DeterministicTableExtractor:

    @staticmethod
    def extract(
        boxes: List[Tuple[float, float, float, float, str]],
        img_w: float,
        page_num: int,
    ) -> Tuple[List[TableItem], List[str]]:
        return [], [b[4] for b in boxes]


# =====================================================
# 5. Metadata Parser
# =====================================================

class DocumentRouter:

    @staticmethod
    def parse_metadata(lines: List[str]) -> MetadataInfo:
        full_top_text = "\n".join(lines[:25])
        meta = MetadataInfo()

        num_m = re.search(
            r"(?:SAYI|SAY1|SA|IY|KANUN NO|KANUN NUMARASI)\s*[:\s]*([0-9A-Z\.\-/]+)",
            full_top_text,
            re.IGNORECASE,
        )
        if num_m:
            meta.sayi = num_m.group(1).strip()
        else:
            law_m = re.search(r"(\d{3,5})\s*SAYILI\s*KANUN", full_top_text, re.IGNORECASE)
            if law_m:
                meta.sayi = law_m.group(1)

        date_m = re.search(r"\b(\d{2}[\./]\d{2}[\./]\d{4})\b", full_top_text)
        if date_m:
            meta.tarih = date_m.group(1)

        for idx, line in enumerate(lines[:12]):
            line_clean = line.strip()
            if re.match(r"^(?:KONU|ONU|NU)\s*[:\s]", line_clean, re.IGNORECASE):
                subject = re.sub(r"^(?:KONU|ONU|NU)\s*[:\s]*", "", line_clean, flags=re.IGNORECASE).strip()
                if idx + 1 < len(lines):
                    next_l = lines[idx + 1].strip()
                    if "hk." in next_l.lower() or (not next_l.isupper() and len(next_l) > 3 and "DAĞITIM" not in next_l):
                        subject += " " + next_l
                meta.konu = subject
                break

        for line in lines[:15]:
            l_up = line.upper().strip()
            if any(k in l_up for k in ["DAĞITIM YERLERİNE", "DAGITIMYERLERINE", "BAŞKANLIĞINA", "MÜDÜRLÜĞÜNE", "VALİLİĞİNE", "KAYMAKAMLIĞINA"]):
                meta.recipient = line.strip()
                break

        return meta


# =====================================================
# 6. Main Pipeline
# =====================================================

class MultiPageOCRPipeline:

    def __init__(self, lang: str = "tr"):
        try:
            self.ocr_engine = PaddleOCR(
                use_angle_cls=False,
                lang=lang,
                enable_mkldnn=False,
                det_limit_side_len=960,  # تقليل الحجم لتسريع المعالجة على CPU
                show_log=False,
            )
        except Exception:
            self.ocr_engine = PaddleOCR(
                lang=lang,
                enable_mkldnn=False,
                show_log=False,
            )

        self.post_processor = OCRPostProcessor()

    def _load_document_images(self, file_path: str) -> List[np.ndarray]:
        path = Path(file_path)
        ext = path.suffix.lower()
        images = []

        if ext == ".pdf":
            if PYMUPDF_AVAILABLE:
                try:
                    doc = fitz.open(file_path)
                    # معالجة أول صفحتين فقط لضمان السرعة الفائقة
                    for page in doc[:2]:
                        pix = page.get_pixmap(dpi=110)
                        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                        if pix.n == 4:
                            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                        elif pix.n == 3:
                            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                        images.append(img_np)
                    doc.close()
                    if images:
                        return images
                except Exception as e:
                    print(f"[OCR WARNING] PyMuPDF conversion failed: {e}")

            if PDF2IMAGE_AVAILABLE:
                poppler_bin = os.getenv("POPPLER_PATH")
                try:
                    pil_images = convert_from_path(
                        file_path,
                        dpi=100,
                        first_page=1,
                        last_page=2,
                        poppler_path=(poppler_bin if poppler_bin else None),
                    )
                    for pil_img in pil_images:
                        image_np = np.array(pil_img)
                        images.append(cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR))
                    return images
                except Exception as error:
                    print(f"[OCR WARNING] pdf2image failed: {error}")

            return []
        else:
            img = cv2.imread(file_path)
            if img is not None:
                images.append(img)
            return images

    def _run_ocr_on_image(self, image_np: np.ndarray) -> List[Tuple[float, float, float, float, str]]:
        if image_np is None:
            return []

        try:
            results = self.ocr_engine.ocr(image_np)
        except Exception as e:
            print(f"[OCR Error in Engine]: {e}")
            return []

        raw_boxes = []
        if results and len(results) > 0 and results[0]:
            for line in results[0]:
                cleaned = self.post_processor.clean_text(str(line[1][0]))
                if cleaned:
                    ymin = line[0][0][1]
                    xmin = line[0][0][0]
                    ymax = line[0][2][1]
                    xmax = line[0][2][0]
                    raw_boxes.append((ymin, xmin, ymax, xmax, cleaned))

        raw_boxes.sort(key=lambda x: x[0])
        return raw_boxes

    def process_file(
        self,
        file_path: str,
        doc_id: str = "doc_01",
        lang: str = "tr",
    ) -> StandardAgentOutput:
        path = Path(file_path)
        ext = path.suffix.lower()

        # مسار سريع جداً لملفات الـ PDF التي تحوي نصوصاً أصلية
        if ext == ".pdf" and PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(file_path)
                pdf_text = ""
                for page in doc[:3]:
                    pdf_text += page.get_text() + "\n"
                doc.close()

                if len(pdf_text.strip()) > 50:
                    cleaned_direct = self.post_processor.clean_text(pdf_text)
                    lines = [l.strip() for l in pdf_text.splitlines() if l.strip()]
                    metadata = DocumentRouter.parse_metadata(lines)
                    return StandardAgentOutput(
                        success=True,
                        document_info=DocumentInfo(
                            document_id=doc_id,
                            file_name=path.name,
                            file_type="pdf",
                            page_count=min(len(doc), 3),
                            language=lang,
                        ),
                        input=StandardInput(
                            clean_text=cleaned_direct,
                            metadata=metadata,
                            tables=[],
                            vision=VisionInfo(has_signature=False, has_stamp=False),
                        ),
                    )
            except Exception:
                pass

        # مسار الرؤية البصرية (OCR) في حال كانت الوثيقة صورة أو PDF ممسوح ضوئياً
        images = self._load_document_images(file_path)
        total_pages = len(images)
        all_document_lines = []
        clean_text_parts = []

        for img in images:
            boxes = self._run_ocr_on_image(img)
            page_clean_str = "\n".join([b[4] for b in boxes])
            all_document_lines.extend([b[4] for b in boxes])
            clean_text_parts.append(page_clean_str)

        combined_clean_text = "\n\n".join(clean_text_parts)
        metadata = DocumentRouter.parse_metadata(all_document_lines)
        stamp_det, sig_det = VisionDetector.detect_stamp_and_signature(images)

        return StandardAgentOutput(
            success=True,
            document_info=DocumentInfo(
                document_id=doc_id,
                file_name=path.name,
                file_type=path.suffix.replace(".", "").lower(),
                page_count=max(total_pages, 1),
                language=lang,
            ),
            input=StandardInput(
                clean_text=combined_clean_text if combined_clean_text.strip() else "Belge metni okunamadı.",
                metadata=metadata,
                tables=[],
                vision=VisionInfo(has_signature=sig_det, has_stamp=stamp_det),
            ),
        )