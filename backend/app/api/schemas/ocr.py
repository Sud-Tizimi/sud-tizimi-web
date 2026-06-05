from __future__ import annotations

from pydantic import BaseModel, Field


class OcrBox(BaseModel):
    text: str
    bbox: list[float] = Field(default_factory=list, description="[x1, y1, x2, y2] normalised 0..1")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class OcrResultOut(BaseModel):
    text: str = ""
    boxes: list[OcrBox] = Field(default_factory=list)
    confidence: float = 0.0
    engine: str = "stub"
    lang: str | None = None
    page_number: int = 1


class OcrImageRequest(BaseModel):
    lang: str | None = None


class OcrEngineStatus(BaseModel):
    real_engine: bool
    active_engine: str


class OcrProcessResponse(BaseModel):
    pages: list[OcrResultOut] = Field(default_factory=list)
    parser: str
    metadata: dict = Field(default_factory=dict)
