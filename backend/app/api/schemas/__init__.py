"""Pydantic v2 schemas (request/response DTOs) for the case-management API.

Naming convention: each module mirrors the resource it serves
(``auth.py``, ``case.py``, etc.). All response models use camelCase aliases
so the wire format matches what the frontend expects.
"""
from .auth import LoginResponse, MeResponse, RegisterRequest
from .case import (
    CaseCreateRequest,
    CaseListResponse,
    CaseResponse,
    CaseReturnRequest,
    StatusTransitionResponse,
)
from .activity import ActivityEventResponse, ActivityListResponse
from .notification import (
    NotificationListResponse,
    NotificationResponse,
    ReadAllResponse,
)
from .user import UserListResponse, UserPublic

__all__ = [
    "LoginResponse",
    "MeResponse",
    "RegisterRequest",
    "CaseCreateRequest",
    "CaseListResponse",
    "CaseResponse",
    "CaseReturnRequest",
    "StatusTransitionResponse",
    "ActivityEventResponse",
    "ActivityListResponse",
    "NotificationListResponse",
    "NotificationResponse",
    "ReadAllResponse",
    "UserListResponse",
    "UserPublic",
]
