from __future__ import annotations


class NenDesktopError(Exception):
    """Base error for all Nen Desktop API errors."""

    def __init__(self, status_code: int, response_body: str) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(f"API error {status_code}: {response_body}")


class AuthenticationError(NenDesktopError):
    """Raised on 401 Unauthorized responses."""


class NotFoundError(NenDesktopError):
    """Raised on 404 Not Found responses."""


class ConflictError(NenDesktopError):
    """Raised on 409 Conflict responses."""


class ServerError(NenDesktopError):
    """Raised on 5xx responses."""
