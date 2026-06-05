from __future__ import annotations

from pydantic import BaseModel, Field


class ASRWord(BaseModel):
    word: str
    start: str = "00:00.000"
    end: str = "00:00.000"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class ASRSegment(BaseModel):
    id: int
    speaker: str
    start: str = "00:00.000"
    end: str = "00:00.000"
    text: str
    words: list[ASRWord] = Field(default_factory=list)


class ASRTranscriptionResponse(BaseModel):
    provider: str
    model: str
    speakersCount: int
    language: str
    duration: str
    fullTranscript: str
    processingTimeS: float
    segments: list[ASRSegment] = Field(default_factory=list)
