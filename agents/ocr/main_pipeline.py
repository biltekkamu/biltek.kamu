import os

# Windows / Paddle stability flags
os.environ["FLAGS_use_onednn"] = "0"
os.environ["FLAGS_enable_pir_api"] = "0"

from dotenv import load_dotenv

load_dotenv()

import cv2
import json
import numpy as np
import re

from pathlib import Path
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

    def clean_text(
        self,
        text: str,
    ) -> str:

        for bad, good in self.glitch_map.items():
            text = text.replace(
                bad,
                good,
            )

        text = re.sub(
            r"^(\d+)([A-Za-zĞÜŞİÖÇğüşiöç])",
            r"\1. \2",
            text,
        )

        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()


# =====================================================
# 3. Vision Detector
# =====================================================

class VisionDetector:

    @staticmethod
    def detect_stamp_and_signature(
        images: List[np.ndarray],
    ) -> Tuple[bool, bool]:

        stamp_detected = False
        sig_detected = False

        for img in images:

            if img is None:
                continue

            h, w = img.shape[:2]

            hsv = (
                cv2.cvtColor(
                    img,
                    cv2.COLOR_BGR2HSV,
                )
                if len(img.shape) == 3
                else None
            )

            if hsv is not None:

                lower_red1 = np.array(
                    [0, 70, 50]
                )

                upper_red1 = np.array(
                    [10, 255, 255]
                )

                lower_red2 = np.array(
                    [170, 70, 50]
                )

                upper_red2 = np.array(
                    [180, 255, 255]
                )

                red_mask = (
                    cv2.inRange(
                        hsv,
                        lower_red1,
                        upper_red1,
                    )
                    |
                    cv2.inRange(
                        hsv,
                        lower_red2,
                        upper_red2,
                    )
                )

                if (
                    cv2.countNonZero(
                        red_mask
                    )
                    > 1500
                ):
                    stamp_detected = True

                lower_blue = np.array(
                    [90, 50, 50]
                )

                upper_blue = np.array(
                    [135, 255, 255]
                )

                blue_mask = cv2.inRange(
                    hsv,
                    lower_blue,
                    upper_blue,
                )

                bottom_blue_mask = (
                    blue_mask[
                        int(h * 0.35):h,
                        :
                    ]
                )

                if (
                    cv2.countNonZero(
                        bottom_blue_mask
                    )
                    > 300
                ):
                    sig_detected = True

            if not sig_detected:

                gray = (
                    cv2.cvtColor(
                        img,
                        cv2.COLOR_BGR2GRAY,
                    )
                    if len(img.shape) == 3
                    else img
                )

                bottom_region = gray[
                    int(h * 0.40):
                    int(h * 0.85),
                    :
                ]

                blur = cv2.GaussianBlur(
                    bottom_region,
                    (5, 5),
                    0,
                )

                thresh = cv2.adaptiveThreshold(
                    blur,
                    255,
                    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                    cv2.THRESH_BINARY_INV,
                    11,
                    2,
                )

                contours, _ = (
                    cv2.findContours(
                        thresh,
                        cv2.RETR_EXTERNAL,
                        cv2.CHAIN_APPROX_SIMPLE,
                    )
                )

                for cnt in contours:

                    area = cv2.contourArea(
                        cnt
                    )

                    if 1200 < area < 15000:

                        x, y, cw, ch = (
                            cv2.boundingRect(
                                cnt
                            )
                        )

                        if ch == 0:
                            continue

                        ratio = (
                            float(cw) / ch
                        )

                        if (
                            0.6
                            < ratio
                            < 3.5
                        ):
                            sig_detected = True
                            break

        return (
            stamp_detected,
            sig_detected,
        )


# =====================================================
# 4. Deterministic Table Extractor
# =====================================================

class DeterministicTableExtractor:

    @staticmethod
    def _fix_mixed_rows(
        rows: List[List[str]],
    ) -> List[List[str]]:

        fixed_rows = []

        date_pattern = re.compile(
            r"\b\d{1,2}/\d{1,2}/\d{4}\b"
        )

        for i, row in enumerate(rows):

            col1 = row[0]
            col2 = row[1]
            col3 = row[2]

            found_dates = (
                date_pattern.findall(
                    col3
                )
            )

            if (
                len(found_dates) == 2
                and "7533" not in col1
            ):

                date1 = found_dates[0]
                date2 = found_dates[1]

                row[2] = (
                    col3.replace(
                        date2,
                        "",
                    ).strip()
                )

                parts = col2.split()

                if len(parts) >= 2:
                    row[1] = parts[0]
                    extra_mat = " ".join(
                        parts[1:]
                    )
                else:
                    extra_mat = col2

                if (
                    i + 1 < len(rows)
                    and "7533"
                    in rows[i + 1][0]
                ):
                    rows[i + 1][1] = (
                        extra_mat
                    )

                    rows[i + 1][2] = (
                        date2
                    )

            if (
                "Anayasa Mahkemesi Kararının Numarası"
                in col1
                and
                "İptal Edilen Maddeleri"
                in col2
            ):

                mat_match = re.search(
                    r"(\d+.*Geçici.*)",
                    col2,
                )

                if (
                    mat_match
                    and
                    i + 1 < len(rows)
                    and
                    "7148"
                    in rows[i + 1][0]
                ):

                    rows[i + 1][1] = (
                        mat_match.group(1)
                        + " "
                        + rows[i + 1][1]
                    ).strip()

                continue

            fixed_rows.append(
                row
            )

        return [
            r
            for r in fixed_rows
            if (
                any(r)
                and not (
                    r[0] == "7533"
                    and not r[1]
                    and not r[2]
                )
            )
        ]

    @staticmethod
    def extract(
        boxes: List[
            Tuple[
                float,
                float,
                float,
                float,
                str,
            ]
        ],
        img_w: float,
        page_num: int,
    ) -> Tuple[
        List[TableItem],
        List[str],
    ]:

        full_text_upper = " ".join(
            [
                b[4].upper()
                for b in boxes
            ]
        )

        if not any(
            k in full_text_upper
            for k in [
                "GÖSTERİR LİSTE",
                "GÖSTERİR TABLO",
                "DEĞİŞTİREN KANUN",
            ]
        ):
            return (
                [],
                [
                    b[4]
                    for b in boxes
                ],
            )

        header_bottom_y = 0.0
        table_start_idx = -1

        for idx, (
            ymin,
            xmin,
            ymax,
            xmax,
            text,
        ) in enumerate(boxes):

            t_up = text.upper()

            if any(
                k in t_up
                for k in [
                    "DEĞİŞTİREN KANUN",
                    "KHK'NİN",
                    "KHK’NİN",
                    "İPTAL EDEN",
                ]
            ):

                if table_start_idx == -1:
                    table_start_idx = idx

                header_bottom_y = max(
                    header_bottom_y,
                    ymax,
                )

        if table_start_idx == -1:

            return (
                [],
                [
                    b[4]
                    for b in boxes
                ],
            )

        non_table_lines = [
            b[4]
            for b in boxes[
                :table_start_idx
            ]
        ]

        table_boxes = [
            b
            for b in boxes
            if (
                b[0]
                >= header_bottom_y - 5
            )
        ]

        col1_limit = (
            img_w * 0.32
        )

        col2_limit = (
            img_w * 0.66
        )

        clean_boxes = []

        for b in table_boxes:

            t_up = (
                b[4].upper()
            )

            if any(
                h in t_up
                for h in [
                    "DEĞİŞTİREN KANUNUN",
                    "İPTAL EDİLEN MADDELERİ",
                    "YÜRÜRLÜĞE GİRİŞ TARİH",
                ]
            ):
                continue

            clean_boxes.append(
                b
            )

        clean_boxes.sort(
            key=lambda b: b[0]
        )

        law_starter_regex = re.compile(
            r"^(\b\d{4}\b|\bKHK[-/]\d+\b|Anayasa\s+Mahkemesinin)",
            re.IGNORECASE,
        )

        rows = []
        current_row = [
            "",
            "",
            "",
        ]

        for (
            ymin,
            xmin,
            ymax,
            xmax,
            text,
        ) in clean_boxes:

            clean_t = text.strip()

            is_new_row_start = (
                xmin < col1_limit
                and
                law_starter_regex.match(
                    clean_t
                )
                and not re.search(
                    r"^\d{4}/",
                    clean_t,
                )
            )

            if is_new_row_start:

                if any(
                    current_row
                ):
                    rows.append(
                        [
                            c.strip()
                            for c
                            in current_row
                        ]
                    )

                current_row = [
                    clean_t,
                    "",
                    "",
                ]

                continue

            if xmin < col1_limit:

                current_row[0] = (
                    current_row[0]
                    + " "
                    + clean_t
                ).strip()

            elif xmin < col2_limit:

                current_row[1] = (
                    current_row[1]
                    + " "
                    + clean_t
                ).strip()

            else:

                current_row[2] = (
                    current_row[2]
                    + " "
                    + clean_t
                ).strip()

        if any(current_row):

            rows.append(
                [
                    c.strip()
                    for c
                    in current_row
                ]
            )

        clean_rows = (
            DeterministicTableExtractor
            ._fix_mixed_rows(
                rows
            )
        )

        headers = [
            (
                "Değiştiren Kanunun/KHK'nin "
                "veya İptal Eden Anayasa "
                "Mahkemesi Kararının Numarası"
            ),
            (
                "Kanunun Değişen veya "
                "İptal Edilen Maddeleri"
            ),
            (
                "Yürürlüğe Giriş Tarihi"
            ),
        ]

        tables = (
            [
                TableItem(
                    page_number=page_num,
                    headers=headers,
                    rows=clean_rows,
                )
            ]
            if clean_rows
            else []
        )

        return (
            tables,
            non_table_lines,
        )


# =====================================================
# 5. Metadata Parser
# =====================================================

class DocumentRouter:

    @staticmethod
    def parse_metadata(
        lines: List[str],
    ) -> MetadataInfo:

        full_top_text = "\n".join(
            lines[:25]
        )

        meta = MetadataInfo()

        num_m = re.search(
            (
                r"(?:SAYI|SAY1|SA|IY|KANUN NO|KANUN NUMARASI)"
                r"\s*[:\s]*([0-9A-Z\.\-/]+)"
            ),
            full_top_text,
            re.IGNORECASE,
        )

        if num_m:

            meta.sayi = (
                num_m.group(1)
                .strip()
            )

        else:

            law_m = re.search(
                r"(\d{3,5})\s*SAYILI\s*KANUN",
                full_top_text,
                re.IGNORECASE,
            )

            if law_m:
                meta.sayi = (
                    law_m.group(1)
                )

        date_m = re.search(
            r"\b(\d{2}[\./]\d{2}[\./]\d{4})\b",
            full_top_text,
        )

        if date_m:
            meta.tarih = (
                date_m.group(1)
            )

        for idx, line in enumerate(
            lines[:12]
        ):

            line_clean = (
                line.strip()
            )

            if re.match(
                r"^(?:KONU|ONU|NU)\s*[:\s]",
                line_clean,
                re.IGNORECASE,
            ):

                subject = re.sub(
                    r"^(?:KONU|ONU|NU)\s*[:\s]*",
                    "",
                    line_clean,
                    flags=re.IGNORECASE,
                ).strip()

                if idx + 1 < len(lines):

                    next_l = (
                        lines[
                            idx + 1
                        ].strip()
                    )

                    if (
                        "hk."
                        in next_l.lower()
                        or (
                            not next_l.isupper()
                            and len(next_l) > 3
                            and
                            "DAĞITIM"
                            not in next_l
                        )
                    ):
                        subject += (
                            " " + next_l
                        )

                meta.konu = subject
                break

        for line in lines[:15]:

            l_up = (
                line.upper()
                .strip()
            )

            if any(
                k in l_up
                for k in [
                    "DAĞITIM YERLERİNE",
                    "DAGITIMYERLERINE",
                    "BAŞKANLIĞINA",
                    "MÜDÜRLÜĞÜNE",
                    "VALİLİĞİNE",
                    "KAYMAKAMLIĞINA",
                ]
            ):

                meta.recipient = (
                    line.strip()
                )

                break

        return meta


# =====================================================
# 6. Main Pipeline
# =====================================================

class MultiPageOCRPipeline:

    def __init__(
        self,
        lang: str = "tr",
    ):

        try:
            self.ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang=lang,
                enable_mkldnn=False,
            )
        except Exception:
            self.ocr_engine = PaddleOCR(
                lang=lang,
                enable_mkldnn=False,
            )

        self.post_processor = (
            OCRPostProcessor()
        )

    def _load_document_images(
        self,
        file_path: str,
    ) -> List[np.ndarray]:

        path = Path(file_path)
        ext = path.suffix.lower()
        images = []

        # =============================================
        # PDF
        # =============================================
        if ext == ".pdf":
            # 1. الخيار الأول والأسرع: PyMuPDF (لا يعتمد على Poppler خارجي)
            if PYMUPDF_AVAILABLE:
                try:
                    doc = fitz.open(file_path)
                    for page in doc:
                        pix = page.get_pixmap(dpi=150)
                        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                        if pix.n == 4:
                            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGBA2BGR)
                        elif pix.n == 3:
                            img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
                        images.append(img_np)
                    doc.close()
                    if images:
                        return images
                except Exception:
                    images = []

            # 2. الخيار الثاني: pdf2image
            if PDF2IMAGE_AVAILABLE:
                poppler_bin = os.getenv("POPPLER_PATH")
                try:
                    pil_images = convert_from_path(
                        file_path,
                        dpi=120,
                        poppler_path=(poppler_bin if poppler_bin else None),
                    )
                    for pil_img in pil_images:
                        image_np = np.array(pil_img)
                        images.append(cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR))
                    return images
                except Exception as error:
                    raise RuntimeError(
                        f"PDF dönüştürülemedi. PyMuPDF veya Poppler kurulumunu kontrol edin. Hata: {error}"
                    ) from error

            raise ImportError("PDF işleme için 'pymupdf' veya 'pdf2image' kütüphanesi gerekli.")

        # =============================================
        # IMAGE
        # =============================================
        else:
            img = cv2.imread(file_path)
            if img is None:
                raise ValueError(f"Dosya okunamadı: {file_path}")
            images.append(img)

        return images

    def _run_ocr_on_image(
        self,
        image_np: np.ndarray,
    ) -> List[
        Tuple[
            float,
            float,
            float,
            float,
            str,
        ]
    ]:

        if hasattr(
            self.ocr_engine,
            "predict",
        ):

            results = (
                self.ocr_engine
                .predict(
                    image_np
                )
            )

        else:

            results = (
                self.ocr_engine
                .ocr(
                    image_np
                )
            )

        raw_boxes = []

        if (
            results
            and len(results) > 0
        ):

            first_res = (
                results[0]
            )

            if (
                hasattr(
                    first_res,
                    "json",
                )
                or
                isinstance(
                    first_res,
                    dict,
                )
            ):

                res_dict = (
                    first_res.json.get(
                        "res",
                        {},
                    )
                    if hasattr(
                        first_res,
                        "json",
                    )
                    else first_res.get(
                        "res",
                        {},
                    )
                )

                texts = res_dict.get(
                    "rec_texts",
                    [],
                )

                boxes = res_dict.get(
                    "rec_boxes",
                    [],
                )

                for idx, text in enumerate(
                    texts
                ):

                    cleaned = (
                        self.post_processor
                        .clean_text(
                            str(text)
                        )
                    )

                    if (
                        cleaned
                        and
                        idx < len(boxes)
                    ):

                        box = boxes[idx]

                        ymin = box[1]
                        xmin = box[0]
                        ymax = box[3]
                        xmax = box[2]

                        raw_boxes.append(
                            (
                                ymin,
                                xmin,
                                ymax,
                                xmax,
                                cleaned,
                            )
                        )

            elif isinstance(
                first_res,
                list,
            ):

                for line in first_res:

                    cleaned = (
                        self.post_processor
                        .clean_text(
                            str(
                                line[1][0]
                            )
                        )
                    )

                    if cleaned:

                        ymin = (
                            line[0][0][1]
                        )

                        xmin = (
                            line[0][0][0]
                        )

                        ymax = (
                            line[0][2][1]
                        )

                        xmax = (
                            line[0][2][0]
                        )

                        raw_boxes.append(
                            (
                                ymin,
                                xmin,
                                ymax,
                                xmax,
                                cleaned,
                            )
                        )

        raw_boxes.sort(
            key=lambda x: x[0]
        )

        return raw_boxes

    def process_file(
        self,
        file_path: str,
        doc_id: str = "mock_doc_02",
        lang: str = "tr",
    ) -> StandardAgentOutput:

        path = Path(
            file_path
        )

        images = (
            self._load_document_images(
                file_path
            )
        )

        total_pages = (
            len(images)
        )

        all_document_lines = []
        all_tables = []
        clean_text_parts = []

        for idx, img in enumerate(
            images,
            start=1,
        ):

            boxes = (
                self._run_ocr_on_image(
                    img
                )
            )

            img_w = float(
                img.shape[1]
            )

            (
                detected_tables,
                non_table_lines,
            ) = (
                DeterministicTableExtractor
                .extract(
                    boxes,
                    img_w,
                    idx,
                )
            )

            if detected_tables:

                all_tables.extend(
                    detected_tables
                )

            page_clean_str = (
                "\n".join(
                    [
                        b[4]
                        for b in boxes
                    ]
                )
            )

            all_document_lines.extend(
                non_table_lines
            )

            clean_text_parts.append(
                page_clean_str
            )

        combined_clean_text = (
            "\n\n".join(
                clean_text_parts
            )
        )

        metadata = (
            DocumentRouter
            .parse_metadata(
                all_document_lines
            )
        )

        (
            stamp_det,
            sig_det,
        ) = (
            VisionDetector
            .detect_stamp_and_signature(
                images
            )
        )

        return StandardAgentOutput(
            success=True,

            document_info=DocumentInfo(
                document_id=doc_id,
                file_name=path.name,
                file_type=(
                    path.suffix
                    .replace(
                        ".",
                        "",
                    )
                    .lower()
                ),
                page_count=total_pages,
                language=lang,
            ),

            input=StandardInput(
                clean_text=(
                    combined_clean_text
                ),
                metadata=metadata,
                tables=all_tables,
                vision=VisionInfo(
                    has_signature=(
                        sig_det
                    ),
                    has_stamp=(
                        stamp_det
                    ),
                ),
            ),
        )


# =====================================================
# 7. Execution Test
# =====================================================

if __name__ == "__main__":

    pipeline = (
        MultiPageOCRPipeline(
            lang="tr"
        )
    )

    sample_path = os.getenv(
        "OCR_TEST_FILE"
    )

    if not sample_path:

        print(
            "OCR_TEST_FILE tanımlı değil."
        )

    else:

        try:

            output = (
                pipeline.process_file(
                    sample_path
                )
            )

            print(
                output.model_dump_json(
                    indent=2
                )
            )

        except Exception as error:

            print(
                (
                    "OCR çalıştırılırken hata oluştu: "
                    f"{error}"
                )
            )