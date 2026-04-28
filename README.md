# nen-desktop

Python SDK for the [Nen Desktop API](https://getnen.ai). Create cloud desktops, execute computer-use tools, and manage RDP sessions programmatically.

## Installation

```bash
pip install nen-desktop
```

## Quick Start

```python
from nen_desktop import NenDesktop

client = NenDesktop(api_key="sk_nen_...")

# Create a desktop
desktop = client.create_desktop()
print(f"Created: {desktop.desktop_id} (status: {desktop.status})")

# Check its status
desktop = client.get_desktop(desktop.desktop_id)
print(f"Status: {desktop.status}, IP: {desktop.public_ip}")

# Clean up
client.delete_desktop(desktop.desktop_id)
```

## Configuration

```python
client = NenDesktop(
    api_key="sk_nen_...",
    base_url="https://desktop.api.getnen.ai",  # default
    timeout=30.0,                                # default (seconds)
)
```

The `execute()` method uses a 120-second timeout regardless of the client timeout, since tool execution can be slow.

## API Reference

### Desktop CRUD

| Method | Description |
|--------|-------------|
| `create_desktop(desktop_type="sandbox")` | Create a new desktop. Returns `Desktop`. |
| `list_desktops()` | List all active desktops. Returns `list[Desktop]`. |
| `get_desktop(desktop_id)` | Get a single desktop. Returns `Desktop`. |
| `update_desktop(desktop_id, *, name)` | Update desktop name. Returns `Desktop`. |
| `delete_desktop(desktop_id)` | Delete a desktop. Returns `DeleteResponse`. |

### Computer-use actions

Typed helpers that build the correct wire format automatically:

| Method | Description |
|--------|-------------|
| `screenshot(desktop_id)` | Capture a screenshot. Returns `ExecuteResult` with `base64_image`. |
| `left_click(desktop_id, x, y)` | Left-click at `(x, y)`. |
| `right_click(desktop_id, x, y)` | Right-click at `(x, y)`. |
| `double_click(desktop_id, x, y)` | Double-click at `(x, y)`. |
| `middle_click(desktop_id, x, y)` | Middle-click at `(x, y)`. |
| `mouse_move(desktop_id, x, y)` | Move the cursor to `(x, y)` without clicking. |
| `type_text(desktop_id, text)` | Type a string at the current cursor position. |
| `key_press(desktop_id, key)` | Send a key or chord (e.g. `"Return"`, `"ctrl+c"`). |
| `scroll(desktop_id, x, y, *, direction, amount=3)` | Scroll at `(x, y)`. `direction` is `"up"` or `"down"`. |
| `cursor_position(desktop_id)` | Return the current cursor coordinates. |

```python
# Take a screenshot
result = client.screenshot(desktop.desktop_id)
# result.base64_image contains a PNG encoded as base64

# Click, type, scroll
client.left_click(desktop.desktop_id, 512, 384)
client.type_text(desktop.desktop_id, "hello world")
client.scroll(desktop.desktop_id, 512, 384, direction="down", amount=5)

# Key combos
client.key_press(desktop.desktop_id, "ctrl+c")
client.key_press(desktop.desktop_id, "Return")
```

### Low-level execute

| Method | Description |
|--------|-------------|
| `execute(desktop_id, *, tool, action, params=None)` | Execute any tool action with a raw params dict. Returns `ExecuteResult`. |
| `list_tools(desktop_id)` | List available tools and their schemas. Returns `list[ToolSchema]`. |
| `get_tool_logs(desktop_id)` | Get tool execution logs. Returns `list[dict]`. |

### Sessions

| Method | Description |
|--------|-------------|
| `create_session(desktop_id)` | Create or reconnect an RDP session. Returns `SessionInfo`. |
| `get_session(desktop_id)` | Get session status. Returns `SessionInfo`. |
| `delete_session(desktop_id)` | Disconnect the session. Returns `None`. |

## Error Handling

All API errors raise a subclass of `NenDesktopError`, which carries `status_code` and `response_body`:

```python
from nen_desktop import NenDesktop, NotFoundError, AuthenticationError

client = NenDesktop(api_key="sk_nen_...")

try:
    client.get_desktop("dsk_nonexistent")
except NotFoundError as e:
    print(f"Not found: {e.status_code}")
except AuthenticationError as e:
    print(f"Auth failed: {e.status_code}")
```

| Exception | Status Code |
|-----------|-------------|
| `AuthenticationError` | 401 |
| `NotFoundError` | 404 |
| `ConflictError` | 409 |
| `ServerError` | 5xx |
| `NenDesktopError` | anything else >= 400 |

## Context Manager

The client supports context manager usage to automatically close the underlying HTTP connection:

```python
with NenDesktop(api_key="sk_nen_...") as client:
    desktop = client.create_desktop()
    # ...
```

## Examples

See the full agent example in [`cmd/nen/templates/anthropic-computer-use/agent.py`](../../cmd/nen/templates/anthropic-computer-use/agent.py).
