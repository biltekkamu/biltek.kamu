from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal

# ----------------------------------------------------
# 1. المخططات الفرعية لمخرجات التحليل الدلالي (Evrak Analysis)
# ----------------------------------------------------
class DocumentTypeResult(BaseModel):
    label: str = Field(description="تصنيف نوع الوثيقة مثل: dilekce, resmi_yazi, basvuru_belgesi, tutanak")
    confidence: float = Field(ge=0.0, le=1.0, description="نسبة الثقة بالتصنيف")

class EvrakAnalysisResult(BaseModel):
    document_type: DocumentTypeResult
    topic: str = Field(description="الموضوع العام للوثيقة بالتركية")
    purpose: str = Field(description="الهدف الرئيسي من إرسال أو إنشاء الوثيقة")
    intent: str = Field(description="النية الإدارية المحددة مثل: izin_talebi, sikayet, itiraz_etme")
    summary: str = Field(description="تلخيص موجز ودقيق لمحتوى الوثيقة من 1 إلى 3 جمل")
    entities: Dict[str, Any] = Field(default_factory=dict, description="الكيانات المستخرجة مثل الأسماء، الأرقام القومية، التواريخ، المؤسسات")
    key_information: Dict[str, Any] = Field(default_factory=dict, description="المعلومات الأساسية المستخلصة من صلب الوثيقة")
    important_points: List[str] = Field(default_factory=list, description="النقاط الهامة والشروط المذكورة")
    missing_information: List[str] = Field(default_factory=list, description="المعلومات أو المرفقات الناقصة المطلوبة في هذا النوع من المعاملات")
    analysis_confidence: float = Field(ge=0.0, le=1.0, description="نسبة ثقة التحليل الدلالي العام")

# ----------------------------------------------------
# 2. المخطط الشامل للبيانات وفق الـ Output المطلوب
# ----------------------------------------------------
class DocumentInfo(BaseModel):
    document_id: str
    file_name: str
    file_type: str
    page_count: int
    language: str = "tr"

class OCRVision(BaseModel):
    has_signature: bool = False
    has_stamp: bool = False

class OCRBlock(BaseModel):
    text: str
    pages: List[Any] = []
    parsed_metadata: Dict[str, Any] = {}
    tables: List[Any] = []
    vision: OCRVision = Field(default_factory=OCRVision)

class RAGSource(BaseModel):
    law_name: str
    article: str

class RAGResult(BaseModel):
    answer: str = ""
    sources: List[RAGSource] = []

class RoutingResult(BaseModel):
    selected_department: str = ""
    reason: str = ""
    confidence: float = 0.0

class OfficialWritingResult(BaseModel):
    generated: bool = False
    letter_type: Optional[str] = None
    text: Optional[str] = None

class ValidationBlock(BaseModel):
    status: Literal["passed", "warning", "rejected", "needs_review"] = "passed"
    issues: List[str] = []
    confidence: float = 1.0

class MasterDocumentPipelineOutput(BaseModel):
    success: bool = True
    document_info: DocumentInfo
    ocr: OCRBlock
    evrak_analysis: EvrakAnalysisResult
    rag: Optional[RAGResult] = None
    routing: Optional[RoutingResult] = None
    official_writing: Optional[OfficialWritingResult] = None
    validation: ValidationBlock