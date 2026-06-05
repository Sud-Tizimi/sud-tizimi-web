"""Service layer — business logic, side effects, state machines.

Plain functions (not classes) to keep imports flat and the call sites
explicit. Each module is a single resource; ``case_service`` orchestrates
``activity_service`` and ``notification_service``.
"""
from . import (
    activity_service,
    auth_service,
    case_service,
    classification_service,
    document_service,
    notification_service,
)

__all__ = [
    "activity_service",
    "auth_service",
    "case_service",
    "classification_service",
    "document_service",
    "notification_service",
]
