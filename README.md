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

### Tool Execution

| Method | Description |
|--------|-------------|
| `execute(desktop_id, *, tool, action, params=None)` | Execute a tool action. Returns `ExecuteResult`. |
| `list_tools(desktop_id)` | List available tools. Returns `list[ToolSchema]`. |
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

See the full agent example in the [Nen documentation](https://docs.getnen.ai/examples/anthropic).
