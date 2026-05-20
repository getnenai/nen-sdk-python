from __future__ import annotations

from typing import IO, Any, Literal
from urllib.parse import quote

import httpx

from nen_sdk.exceptions import (
    AuthenticationError,
    ConflictError,
    NenDesktopError,
    NotFoundError,
    ServerError,
)
from nen_sdk.models import (
    DeleteResponse,
    Desktop,
    ExecuteResult,
    File,
    SessionInfo,
    ToolSchema,
    UploadFileResponse,
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

    # -- Computer-use action helpers --
    # These build the correct Anthropic-native params format so callers don't
    # need to know the wire representation.

    def screenshot(self, desktop_id: str) -> ExecuteResult:
        return self.execute(desktop_id, tool="computer", action="screenshot")

    def left_click(self, desktop_id: str, x: int, y: int) -> ExecuteResult:
        return self.execute(
            desktop_id,
            tool="computer",
            action="left_click",
            params={"coordinate": [x, y]},
        )

    def right_click(self, desktop_id: str, x: int, y: int) -> ExecuteResult:
        return self.execute(
            desktop_id,
            tool="computer",
            action="right_click",
            params={"coordinate": [x, y]},
        )

    def double_click(self, desktop_id: str, x: int, y: int) -> ExecuteResult:
        return self.execute(
            desktop_id,
            tool="computer",
            action="double_click",
            params={"coordinate": [x, y]},
        )

    def middle_click(self, desktop_id: str, x: int, y: int) -> ExecuteResult:
        return self.execute(
            desktop_id,
            tool="computer",
            action="middle_click",
            params={"coordinate": [x, y]},
        )

    def mouse_move(self, desktop_id: str, x: int, y: int) -> ExecuteResult:
        return self.execute(
            desktop_id,
            tool="computer",
            action="mouse_move",
            params={"coordinate": [x, y]},
        )

    def type_text(self, desktop_id: str, text: str) -> ExecuteResult:
        return self.execute(
            desktop_id, tool="computer", action="type", params={"text": text}
        )

    def key_press(self, desktop_id: str, key: str) -> ExecuteResult:
        return self.execute(
            desktop_id, tool="computer", action="key", params={"text": key}
        )

    def scroll(
        self,
        desktop_id: str,
        x: int,
        y: int,
        *,
        direction: Literal["up", "down"],
        amount: int = 3,
    ) -> ExecuteResult:
        return self.execute(
            desktop_id,
            tool="computer",
            action="scroll",
            params={"coordinate": [x, y], "direction": direction, "amount": amount},
        )

    def cursor_position(self, desktop_id: str) -> ExecuteResult:
        return self.execute(desktop_id, tool="computer", action="cursor_position")

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

    # -- Files --

    def list_files(self, desktop_id: str) -> list[File]:
        """List files on the desktop's shared drive."""
        resp = self._client.get(f"/desktops/{desktop_id}/files")
        self._raise_for_status(resp)
        # No silent default — a missing "files" key signals a contract
        # regression we want to surface, not paper over as "empty drive".
        return [File.model_validate(f) for f in resp.json()["files"]]

    def upload_file(
        self,
        desktop_id: str,
        name: str,
        body: bytes | IO[bytes],
        *,
        content_type: str = "application/octet-stream",
    ) -> UploadFileResponse:
        """Upload ``body`` to the desktop's shared drive as ``name``.

        Accepts a ``bytes`` blob or any binary file-like (``open(..., "rb")``).
        The server caps the body at 100 MiB. ``content_type`` is sent verbatim
        and defaults to ``application/octet-stream``.
        """
        resp = self._client.post(
            f"/desktops/{desktop_id}/files/{quote(name, safe='')}",
            content=body,
            headers={"Content-Type": content_type},
            timeout=_EXECUTE_TIMEOUT,
        )
        self._raise_for_status(resp)
        return UploadFileResponse.model_validate(resp.json())

    def download_file(self, desktop_id: str, name: str) -> bytes:
        """Download ``name`` from the desktop's shared drive and return its bytes."""
        resp = self._client.get(
            f"/desktops/{desktop_id}/files/{quote(name, safe='')}",
            timeout=_EXECUTE_TIMEOUT,
        )
        self._raise_for_status(resp)
        return resp.content

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
