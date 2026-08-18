Input (PDF / Image)
├── 1. Document Loading & PDF Rasterization (pdf2image + Poppler)
├── 2. OCR Inference (PaddleOCR)
├── 3. Post-Processing & Text Cleaning (Regex Normalization)
├── 4. Deterministic Table Extractor (Coordinate-based alignment)
├── 5. Metadata Parser (Regex & Keyword Routing)
└── 6. Vision Detector (HSV Color Thresholding + Contour Geometry)
↓
StandardAgentOutput (Validated Pydantic JSON)

Create and activate a virtual environment:
python -m venv venv
.\venv\Scripts\Activate.ps1


Install dependencies:

pip install --upgrade pip
pip install -r requirements.txt


requirements.txt:

paddlepaddle>=2.5.0
paddleocr>=2.7.0
opencv-python>=4.8.0
numpy>=1.24.0
pydantic>=2.0.0
pdf2image>=1.16.3


1. Configure the Poppler Path (Windows Users)
In the pipeline script (pipeline.py), update the Poppler binary path if running on Windows:
poppler_bin = r"C:\path\to\poppler\Library\bin"


Sample Output JSON:


{
  "success": true,
  "document_info": {
    "document_id": "DOC_2026_001",
    "file_name": "sample_document.pdf",
    "file_type": "pdf",
    "page_count": 1,
    "language": "tr"
  },
  "input": {
    "clean_text": "T.C. İÇİŞLERİ BAKANLIĞI...",
    "metadata": {
      "sayi": "E-12345678-010.06.01-9999",
      "tarih": "15/04/2026",
      "konu": "Yetkilendirme ve İzin Belgesi Hk.",
      "recipient": "DAĞITIM YERLERİNE"
    },
    "tables": [],
    "vision": {
      "has_signature": true,
      "has_stamp": true
    }
  }
}
