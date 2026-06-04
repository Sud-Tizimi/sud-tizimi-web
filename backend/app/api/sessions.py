"""REST endpoints for session lifecycle — start / stop / list / get."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..core.errors import SessionNotFound
from ..core.ws_protocol import SpeakerSeed

router = APIRouter(prefix="/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    caseNumber: str = Field(min_length=1)
    title: str = Field(min_length=1)
    judge: str = Field(min_length=1)
    speakers: list[SpeakerSeed] = Field(default_factory=list)


class StartSessionResponse(BaseModel):
    sessionId: str
    wsUrl: str
    startedAt: str


class StopSessionResponse(BaseModel):
    sessionId: str
    stoppedAt: str
    durationSec: int
    finalEntryCount: int


@router.post("/start", response_model=StartSessionResponse)
async def start_session(req: Request, body: StartSessionRequest) -> StartSessionResponse:
    sm = req.app.state.session_manager
    session = await sm.create_session(
        case_info=body.model_dump(include={"caseNumber", "title", "judge"}),
        speakers=body.speakers,
    )
    return StartSessionResponse(
        sessionId=session.id,
        wsUrl=f"/ws/sessions/{session.id}",
        startedAt=session.started_at.isoformat(),
    )


@router.post("/{session_id}/stop", response_model=StopSessionResponse)
async def stop_session(req: Request, session_id: str) -> StopSessionResponse:
    sm = req.app.state.session_manager
    try:
        return StopSessionResponse(**(await sm.stop_session(session_id)))
    except SessionNotFound:
        raise HTTPException(status_code=404, detail="session_not_found")


@router.get("")
async def list_sessions(req: Request) -> dict:
    return {"sessions": req.app.state.session_manager.list_summaries()}


@router.get("/{session_id}")
async def get_session(req: Request, session_id: str) -> dict:
    sm = req.app.state.session_manager
    sess = sm.get(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail="session_not_found")
    return sess.public_dict()
