from typing import Literal

from pydantic import BaseModel, Field


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=5000)


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    history: list[HistoryMessage] = Field(default_factory=list)


class SourceResponse(BaseModel):
    document_name: str | None = None
    law_number: str | None = None
    madde: str | None = None
    chunk_id: int | None = None
    score: float | None = None


class QueryResponse(BaseModel):
    request_id: str
    answer: str
    sources: list[SourceResponse]
    retrieved_chunks: int
    elapsed: float
    cached: bool = False


class HealthResponse(BaseModel):
    status: str
    collection: str
    document_count: int
    embedding_model: str
    llm_model: str