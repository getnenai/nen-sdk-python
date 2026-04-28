from __future__ import annotations

import os
import uuid

import pytest

from nen_desktop import (
    AuthenticationError,
    Desktop,
    NenDesktop,
    NotFoundError,
)

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


# -- 11. Action helper: drag --


def test_helper_drag(client: NenDesktop, desktop: Desktop) -> None:
    result = client.drag(desktop.desktop_id, 100, 100, 200, 200)
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
