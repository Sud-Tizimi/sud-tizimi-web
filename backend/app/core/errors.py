"""Domain-level exceptions raised by services / API handlers."""


class SessionNotFound(Exception):
    """Raised when a session_id is unknown to the SessionManager."""


class WsProtocolError(Exception):
    """Raised on malformed / unknown WebSocket messages."""
