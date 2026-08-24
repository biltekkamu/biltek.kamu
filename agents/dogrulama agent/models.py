from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class IssueType(str, Enum):
    MISSING_DATA = "missing_data"
    SCHEMA_ERROR = "schema_error"
    OCR_ERROR = "ocr_error"
    CLASSIFICATION_MISMATCH = "classification_mismatch"
    ENTITY_GROUNDING_ERROR = "entity_grounding_error"
    ANALYSIS_MISMATCH = "analysis_mismatch"
    ROUTING_MISMATCH = "routing_mismatch"
    MISSING_SOURCE = "missing_source"
    RAG_GROUNDING_ERROR = "rag_grounding_error"
    LOW_CONFIDENCE = "low_confidence"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"

class ValidationIssue(BaseModel):
    field: str = Field(description="İlgili alan yolu")
    type: IssueType = Field(description="Tespit edilen sorun türü")
    severity: Severity = Field(description="Önem derecesi: low, medium, high")
    message: str = Field(description="Sorun açıklaması")

class ValidationBlock(BaseModel):
    status: Literal["valid", "warning", "invalid"] = "valid"
    issues: List[ValidationIssue] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, description="Genel doğrulama güven skoru")