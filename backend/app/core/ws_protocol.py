"""Pydantic models for ALL WebSocket messages (server ↔ client).

This is the single source of truth for the wire contract.
Server code MUST go through these models — never call `ws.send_json(dict)` with
an untyped payload.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

SpeakerRole = Literal["judge", "plaintiff", "defendant", "witness", "lawyer", "unknown"]


class SpeakerSeed(BaseModel):
    id: str
    label: str
    role: SpeakerRole = "unknown"


# ----------------------- Client → Server -----------------------


class ClientPing(BaseModel):
    type: Literal["ping"] = "ping"
    t: float


class ClientPong(BaseModel):
    type: Literal["pong"] = "pong"


class ClientRegisterSpeakers(BaseModel):
    type: Literal["register_speakers"] = "register_speakers"
    speakers: list[SpeakerSeed] = Field(default_factory=list)


class ClientSubscribeAudioLevel(BaseModel):
    type: Literal["subscribe_audio_level"] = "subscribe_audio_level"
    enabled: bool = True


ClientMessage = Annotated[
    Union[ClientPing, ClientPong, ClientRegisterSpeakers, ClientSubscribeAudioLevel],
    Field(discriminator="type"),
]


# ----------------------- Server → Client -----------------------


class ServerSessionReady(BaseModel):
    type: Literal["session_ready"] = "session_ready"
    sessionId: str
    startedAt: str
    speakers: list[SpeakerSeed] = Field(default_factory=list)


class ServerSpeakerRegistered(BaseModel):
    type: Literal["speaker_registered"] = "speaker_registered"
    speaker: SpeakerSeed


class ServerPartial(BaseModel):
    type: Literal["partial"] = "partial"
    entryId: str
    speakerId: str
    text: str
    atMs: int
    progress: float  # 0..1


class ServerFinal(BaseModel):
    type: Literal["final"] = "final"
    entryId: str
    speakerId: str
    text: str
    rawText: str
    atMs: int
    postProcessed: bool


class ServerAudioLevel(BaseModel):
    type: Literal["audio_level"] = "audio_level"
    level: int  # 0..100
    atMs: int


class ServerSpeakerSpeaking(BaseModel):
    type: Literal["speaker_speaking"] = "speaker_speaking"
    speakerId: str
    speaking: bool


class ServerPing(BaseModel):
    type: Literal["ping"] = "ping"
    t: float


class ServerPong(BaseModel):
    type: Literal["pong"] = "pong"
    t: float


class ServerError(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str


ServerMessage = Annotated[
    Union[
        ServerSessionReady,
        ServerSpeakerRegistered,
        ServerPartial,
        ServerFinal,
        ServerAudioLevel,
        ServerSpeakerSpeaking,
        ServerPing,
        ServerPong,
        ServerError,
    ],
    Field(discriminator="type"),
]


# ----------------------- Parsing helpers -----------------------


_CLIENT_MODELS = (ClientPing, ClientPong, ClientRegisterSpeakers, ClientSubscribeAudioLevel)


def parse_client_message(data: dict) -> BaseModel:
    """Validate a dict into the right ClientMessage subclass.

    Raises ValueError on unknown / malformed payloads — caller should turn
    that into a ServerError reply.
    """
    if not isinstance(data, dict):
        raise ValueError("payload_not_object")
    t = data.get("type")
    if not isinstance(t, str):
        raise ValueError("missing_type")
    for model in _CLIENT_MODELS:
        if model.model_fields["type"].default == t:
            return model.model_validate(data)
    raise ValueError(f"unknown_message_type:{t}")


# ----------------------- Convenience constructors -----------------------


def make_session_ready(
    session_id: str, started_at: datetime, speakers: list[SpeakerSeed]
) -> ServerSessionReady:
    return ServerSessionReady(
        sessionId=session_id,
        startedAt=started_at.astimezone(timezone.utc).isoformat(),
        speakers=speakers,
    )


def make_error(code: str, message: str = "") -> ServerError:
    return ServerError(code=code, message=message or code)
