import cv2
import numpy as np
from paddleocr import PaddleOCR
from pydantic import BaseModel
from typing import List

class OCRBlock(BaseModel):
    text: str
    confidence: float
    bbox: List[List[float]]

class OCRPageResult(BaseModel):
    document_id: str
    page: int
    average_confidence: float
    ocr_quality: str
    blocks: List[OCRBlock]

ocr_engine = PaddleOCR(lang='tr', use_gpu=False)

def sort_reading_order_advanced(blocks: List[OCRBlock], y_threshold: float = 15.0) -> List[OCRBlock]:
  
    if not blocks:
        return []

    items = []
    for b in blocks:
        y_coords = [pt[1] for pt in b.bbox]
        x_coords = [pt[0] for pt in b.bbox]
        
        y_center = sum(y_coords) / len(y_coords)
        x_min = min(x_coords)
        
        items.append({
            'block': b,
            'x_min': x_min,
            'y_center': y_center
        })

    items.sort(key=lambda item: item['y_center'])

    lines = []
    for item in items:
        matched_line = None
        for line in lines:
            avg_y = sum(i['y_center'] for i in line) / len(line)
            if abs(item['y_center'] - avg_y) <= y_threshold:
                matched_line = line
                break
        
        if matched_line is not None:
            matched_line.append(item)
        else:
            lines.append([item])

    lines.sort(key=lambda line: sum(i['y_center'] for i in line) / len(line))
    
    sorted_blocks = []
    for line in lines:
        line.sort(key=lambda item: item['x_min'])
        for item in line:
            sorted_blocks.append(item['block'])

    return sorted_blocks

def process_pipeline_ocr(image_path: str, doc_id: str = "doc_001", page_num: int = 1) -> OCRPageResult:
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"تعذر قراءة الصورة من المسار: {image_path}")

    
    results = ocr_engine.ocr(image_path, cls=False)
    
    raw_blocks = []
    total_confidence = 0.0
    
    if results and len(results) > 0 and results[0] is not None:
        for line in results[0]:
            bbox = line[0]
            text, conf = line[1]
            
            raw_blocks.append(
                OCRBlock(
                    text=text,
                    confidence=round(float(conf), 4),
                    bbox=bbox
                )
            )
            total_confidence += conf

    ordered_blocks = sort_reading_order_advanced(raw_blocks, y_threshold=15.0)

    block_count = len(ordered_blocks)
    avg_confidence = (total_confidence / block_count) if block_count > 0 else 0.0
    avg_confidence = round(avg_confidence, 4)

    if avg_confidence >= 0.85:
        quality = "GOOD"
    elif avg_confidence >= 0.65:
        quality = "ACCEPTABLE"
    else:
        quality = "LOW"

    return OCRPageResult(
        document_id=doc_id,
        page=page_num,
        average_confidence=avg_confidence,
        ocr_quality=quality,
        blocks=ordered_blocks
    )

if __name__ == "__main__":
    sample_image = r"C:\Users\manbe\Downloads\chatbot data\ocr-agent pro\images\test1.jpg"
    
    try:
        result = process_pipeline_ocr(sample_image)
        print(result.model_dump_json(indent=2))
    except Exception as e:
        print(f"حدث خطأ أثناء التشغيل: {e}")