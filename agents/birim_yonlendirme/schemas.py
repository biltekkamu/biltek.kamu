from pydantic import BaseModel, Field


class BirimYonlendirmeResult(BaseModel):
    selected_department: str | None = None
    reason: str

    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )