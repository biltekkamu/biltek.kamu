# schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional

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