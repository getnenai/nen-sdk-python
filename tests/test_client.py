from __future__ import annotations

import io
import os
import uuid

import httpx
import pytest

from nen_sdk import (
    AuthenticationError,
    Desktop,
    NenDesktop,
    NotFoundError,
)
from nen_sdk.models import File

# ---------------------------------------------------------------
# Tests using the shared session-scoped desktop are placed first
# so the fixture is resolved before heavier tests run.
# ---------------------------------------------------------------

# -- 1. Low-level execute: screenshot --


def test_execute_screenshot(client: NenDesktop, desktop: Desktop) -> None:
    result = client.execute(desktop.desktop_id, tool="computer", action="screenshot")
    assert result.status == "ok"
    assert result.base64_image


# -- 2. Low-level execute: key --


def test_execute_with_params(client: NenDesktop, desktop: Desktop) -> None:
    result = client.execute(
        desktop.desktop_id,
        tool="computer",
        action="key",
        params={"text": "a"},
    )
    assert result.status == "ok"


# -- 3. Action helper: screenshot --


def test_helper_screenshot(client: NenDesktop, desktop: Desktop) -> None:
    result = client.screenshot(desktop.desktop_id)
    assert result.status == "ok"
    assert result.base64_image


# -- 4. Action helper: left_click --


def test_helper_left_click(client: NenDesktop, desktop: Desktop) -> None:
    result = client.left_click(desktop.desktop_id, 512, 384)
    assert result.status == "ok"


# -- 5. Action helper: right_click --


def test_helper_right_click(client: NenDesktop, desktop: Desktop) -> None:
    result = client.right_click(desktop.desktop_id, 512, 384)
    assert result.status == "ok"


# -- 6. Action helper: double_click --


def test_helper_double_click(client: NenDesktop, desktop: Desktop) -> None:
    result = client.double_click(desktop.desktop_id, 512, 384)
    assert result.status == "ok"


# -- 7. Action helper: mouse_move --


def test_helper_mouse_move(client: NenDesktop, desktop: Desktop) -> None:
    result = client.mouse_move(desktop.desktop_id, 100, 100)
    assert result.status == "ok"


# -- 8. Action helper: type_text --


def test_helper_type_text(client: NenDesktop, desktop: Desktop) -> None:
    result = client.type_text(desktop.desktop_id, "hello")
    assert result.status == "ok"


# -- 9. Action helper: key_press --


def test_helper_key_press(client: NenDesktop, desktop: Desktop) -> None:
    result = client.key_press(desktop.desktop_id, "Escape")
    assert result.status == "ok"


# -- 10. Action helper: scroll --


def test_helper_scroll(client: NenDesktop, desktop: Desktop) -> None:
    result = client.scroll(desktop.desktop_id, 512, 384, direction="down", amount=3)
    assert result.status == "ok"


# -- 12. List tools --


def test_list_tools(client: NenDesktop, desktop: Desktop) -> None:
    tools = client.list_tools(desktop.desktop_id)
    assert len(tools) > 0
    for tool in tools:
        assert tool.name
        assert tool.description
        assert isinstance(tool.parameters, dict)


# -- 13. Tool logs --


def test_tool_logs(client: NenDesktop, desktop: Desktop) -> None:
    client.screenshot(desktop.desktop_id)
    logs = client.get_tool_logs(desktop.desktop_id)
    assert isinstance(logs, list)


# -- 14. Session lifecycle --


def test_session_lifecycle(client: NenDesktop, desktop: Desktop) -> None:
    session = client.create_session(desktop.desktop_id)
    assert session.active is True

    got = client.get_session(desktop.desktop_id)
    assert got.active is True

    client.delete_session(desktop.desktop_id)

    with pytest.raises(NotFoundError):
        client.get_session(desktop.desktop_id)


# -- 15. Session idempotency --


def test_session_idempotency(client: NenDesktop, desktop: Desktop) -> None:
    session1 = client.create_session(desktop.desktop_id)
    assert session1.active is True

    session2 = client.create_session(desktop.desktop_id)
    assert session2.active is True


# -- 15b. Files round-trip (reuses shared desktop) --


def test_files_round_trip(client: NenDesktop, desktop: Desktop) -> None:
    name = f"round-trip-{uuid.uuid4().hex[:12]}.txt"
    payload = f"nen-sdk-python round-trip {uuid.uuid4()}\n".encode()

    up = client.upload_file(
        desktop.desktop_id,
        name,
        payload,
        content_type="text/plain",
    )
    assert up.success
    assert up.size == len(payload)
    assert up.filename == name

    files = client.list_files(desktop.desktop_id)
    found = next((f for f in files if f.name == name), None)
    assert found is not None, f"uploaded file {name} not in listing of {len(files)}"
    assert found.size == len(payload)

    got = client.download_file(desktop.desktop_id, name)
    assert got == payload

    # Same round-trip via the file-like (IO[bytes]) upload path so both
    # supported body shapes stay covered.
    name_io = f"round-trip-io-{uuid.uuid4().hex[:12]}.txt"
    payload_io = f"nen-sdk-python round-trip io {uuid.uuid4()}\n".encode()
    up_io = client.upload_file(
        desktop.desktop_id,
        name_io,
        io.BytesIO(payload_io),
        content_type="text/plain",
    )
    assert up_io.success
    assert up_io.size == len(payload_io)
    assert up_io.filename == name_io
    assert client.download_file(desktop.desktop_id, name_io) == payload_io


# -- 15c. Files API guards: empty name --


def test_files_reject_empty_name() -> None:
    """upload_file / download_file must fail fast on empty name (would
    otherwise hit the /files/ list endpoint and return a confusing error).

    No live API call here — the guard fires client-side. Runs without
    NEN_API_KEY so the contract stays covered even in unauthenticated CI.
    """
    offline = NenDesktop("sk_nen_dummy_for_offline_guard_test")
    try:
        with pytest.raises(ValueError, match="non-empty"):
            offline.upload_file("dsk_x", "", b"x", content_type="text/plain")
        with pytest.raises(ValueError, match="non-empty"):
            offline.download_file("dsk_x", "")
    finally:
        offline.close()


# -- 15d. Files model: is_dir wire compatibility (offline) --


def test_file_model_accepts_is_dir_field() -> None:
    """File deserializes a populated is_dir, and missing is_dir
    defaults to False so older servers stay compatible."""
    with_dir = File.model_validate(
        {"name": "Documents", "size": 0, "modified": 1.5, "is_dir": True}
    )
    assert with_dir.is_dir is True

    legacy = File.model_validate({"name": "a.txt", "size": 3, "modified": 1.0})
    assert legacy.is_dir is False


# -- 15e. list_files forwards ?path= (offline, httpx.MockTransport) --


def _offline_client(handler) -> NenDesktop:
    """Return a NenDesktop that routes every request to ``handler``.

    Uses httpx.MockTransport so the test exercises real URL building
    and parameter encoding without hitting the network.
    """
    client = NenDesktop("sk_nen_dummy_offline")
    # Dispose the real httpx.Client NenDesktop opened in __init__ before
    # swapping in the MockTransport one — otherwise the connection pool
    # the real client allocated stays open for the lifetime of the test.
    client._client.close()
    client._client = httpx.Client(
        base_url=client._base_url,
        headers={"Authorization": f"Bearer {client._api_key}"},
        transport=httpx.MockTransport(handler),
    )
    return client


def test_list_files_forwards_path_query() -> None:
    captured: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url)
        return httpx.Response(200, json={"files": []})

    client = _offline_client(handler)
    try:
        client.list_files("dsk_x", path="Documents")
    finally:
        client.close()

    assert len(captured) == 1
    url = captured[0]
    assert url.path == "/desktops/dsk_x/files"
    assert url.params.get("path") == "Documents"


def test_list_files_no_path_omits_query() -> None:
    captured: list[httpx.URL] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.url)
        return httpx.Response(200, json={"files": []})

    client = _offline_client(handler)
    try:
        client.list_files("dsk_x")
    finally:
        client.close()

    assert len(captured) == 1
    assert captured[0].raw_path.endswith(b"/desktops/dsk_x/files")
    assert "path" not in captured[0].params


def test_upload_file_forwards_path_query() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200, json={"success": True, "size": 3, "filename": "hi.txt"}
        )

    client = _offline_client(handler)
    try:
        client.upload_file(
            "dsk_x", "hi.txt", b"hi!", content_type="text/plain", path="Documents"
        )
    finally:
        client.close()

    assert len(captured) == 1
    req = captured[0]
    assert req.method == "POST"
    assert req.url.path == "/desktops/dsk_x/files/hi.txt"
    assert req.url.params.get("path") == "Documents"


def test_upload_file_no_path_omits_query() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200, json={"success": True, "size": 3, "filename": "hi.txt"}
        )

    client = _offline_client(handler)
    try:
        client.upload_file("dsk_x", "hi.txt", b"hi!", content_type="text/plain")
    finally:
        client.close()

    assert len(captured) == 1
    assert "path" not in captured[0].url.params


def test_download_file_forwards_path_query() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, content=b"contents")

    client = _offline_client(handler)
    try:
        got = client.download_file("dsk_x", "hi.txt", path="Documents")
    finally:
        client.close()

    assert got == b"contents"
    assert len(captured) == 1
    req = captured[0]
    assert req.method == "GET"
    assert req.url.path == "/desktops/dsk_x/files/hi.txt"
    assert req.url.params.get("path") == "Documents"


def test_download_file_no_path_omits_query() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, content=b"contents")

    client = _offline_client(handler)
    try:
        client.download_file("dsk_x", "hi.txt")
    finally:
        client.close()

    assert len(captured) == 1
    assert "path" not in captured[0].url.params


# ---------------------------------------------------------------
# CRUD lifecycle — creates its own desktop.
# Placed after shared-desktop tests so the pool isn't drained.
# ---------------------------------------------------------------

# -- 16. CRUD lifecycle --


def test_crud_lifecycle(client: NenDesktop) -> None:
    desktop = client.create_desktop()
    try:
        desktops = client.list_desktops()
        ids = [d.desktop_id for d in desktops]
        assert desktop.desktop_id in ids

        got = client.get_desktop(desktop.desktop_id)
        assert got.desktop_id == desktop.desktop_id
        assert got.desktop_type == "sandbox"
        assert got.status == "running"

        new_name = f"sdk-test-{uuid.uuid4().hex[:8]}"
        updated = client.update_desktop(desktop.desktop_id, name=new_name)
        assert updated.name == new_name

        got2 = client.get_desktop(desktop.desktop_id)
        assert got2.name == new_name

        deleted = client.delete_desktop(desktop.desktop_id)
        assert deleted.status == "deleted"

        try:
            got3 = client.get_desktop(desktop.desktop_id)
            assert got3.status == "deleted"
        except NotFoundError:
            pass
    except Exception:
        try:
            client.delete_desktop(desktop.desktop_id)
        except Exception:
            pass
        raise


# ---------------------------------------------------------------
# Error tests — no desktop creation needed.
# ---------------------------------------------------------------

# -- 17. Error: not found --


def test_error_not_found(client: NenDesktop) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        client.get_desktop("dsk_nonexistent_000000000000")
    assert exc_info.value.status_code == 404


# -- 18. Error: auth --


def test_error_auth() -> None:
    base_url = os.environ.get("NEN_API_URL", "https://desktop.api.getnen.ai")
    bad_client = NenDesktop("sk_nen_invalid_key", base_url=base_url)
    try:
        with pytest.raises(AuthenticationError) as exc_info:
            bad_client.list_desktops()
        assert exc_info.value.status_code == 401
    finally:
        bad_client.close()


# -- 19. Error: update nonexistent --


def test_error_update_nonexistent(client: NenDesktop) -> None:
    with pytest.raises(NotFoundError) as exc_info:
        client.update_desktop("dsk_nonexistent_000000000000", name="nope")
    assert exc_info.value.status_code == 404
