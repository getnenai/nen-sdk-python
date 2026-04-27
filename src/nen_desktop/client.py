from __future__ import annotations

from typing import Any

import httpx

from nen_desktop.exceptions import (
    AuthenticationError,
    ConflictError,
    NenDesktopError,
    NotFoundError,
    ServerError,
)
from nen_desktop.models import (
    DeleteResponse,
    Desktop,
    ExecuteResult,
    SessionInfo,
    ToolSchema,
)

_DEFAULT_BASE_URL = "https://desktop.api.getnen.ai"
_DEFAULT_TIMEOUT = 30.0
_EXECUTE_TIMEOUT = 120.0


class NenDesktop:
    """Synchronous client for the Nen Desktop API."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    # -- Context manager --

    def __enter__(self) -> NenDesktop:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    # -- Desktops --

    def create_desktop(self, desktop_type: str = "sandbox") -> Desktop:
        resp = self._client.post(
            "/desktops",
            json={"desktop_type": desktop_type},
        )
        self._raise_for_status(resp)
        return Desktop.model_validate(resp.json())

    def list_desktops(self) -> list[Desktop]:
        resp = self._client.get("/desktops")
        self._raise_for_status(resp)
        return [Desktop.model_validate(d) for d in resp.json()]

    def get_desktop(self, desktop_id: str) -> Desktop:
        resp = self._client.get(f"/desktops/{desktop_id}")
        self._raise_for_status(resp)
        return Desktop.model_validate(resp.json())

    def update_desktop(self, desktop_id: str, *, name: str) -> Desktop:
        resp = self._client.patch(
            f"/desktops/{desktop_id}",
            json={"name": name},
        )
        self._raise_for_status(resp)
        return Desktop.model_validate(resp.json())

    def delete_desktop(self, desktop_id: str) -> DeleteResponse:
        resp = self._client.delete(f"/desktops/{desktop_id}")
        self._raise_for_status(resp)
        return DeleteResponse.model_validate(resp.json())

    # -- Execute / Tools --

    def execute(
        self,
        desktop_id: str,
        *,
        tool: str,
        action: str,
        params: dict[str, Any] | None = None,
    ) -> ExecuteResult:
        resp = self._client.post(
            f"/desktops/{desktop_id}/execute",
            json={"action": {"tool": tool, "action": action, "params": params or {}}},
            timeout=_EXECUTE_TIMEOUT,
        )
        self._raise_for_status(resp)
        return ExecuteResult.model_validate(resp.json())

    def list_tools(self, desktop_id: str) -> list[ToolSchema]:
        resp = self._client.get(f"/desktops/{desktop_id}/tools")
        self._raise_for_status(resp)
        return [ToolSchema.model_validate(t) for t in resp.json()]

    def get_tool_logs(self, desktop_id: str) -> list[dict[str, Any]]:
        resp = self._client.get(f"/desktops/{desktop_id}/tool-logs")
        self._raise_for_status(resp)
        return resp.json()

    # -- Sessions --

    def create_session(self, desktop_id: str) -> SessionInfo:
        resp = self._client.put(f"/desktops/{desktop_id}/session")
        self._raise_for_status(resp)
        return SessionInfo.model_validate(resp.json())

    def get_session(self, desktop_id: str) -> SessionInfo:
        resp = self._client.get(f"/desktops/{desktop_id}/session")
        self._raise_for_status(resp)
        return SessionInfo.model_validate(resp.json())

    def delete_session(self, desktop_id: str) -> None:
        resp = self._client.delete(f"/desktops/{desktop_id}/session")
        self._raise_for_status(resp)

    # -- Error handling --

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code < 400:
            return

        body = resp.text
        status = resp.status_code

        if status == 401:
            raise AuthenticationError(status, body)
        if status == 404:
            raise NotFoundError(status, body)
        if status == 409:
            raise ConflictError(status, body)
        if status >= 500:
            raise ServerError(status, body)
        raise NenDesktopError(status, body)
