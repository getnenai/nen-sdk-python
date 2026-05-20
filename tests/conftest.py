from __future__ import annotations

import os

import pytest

from nen_sdk import NenDesktop


@pytest.fixture(scope="session")
def api_key() -> str:
    key = os.environ.get("NEN_API_KEY", "")
    if not key:
        pytest.skip("NEN_API_KEY not set")
    return key


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("NEN_API_URL", "https://desktop.api.getnen.ai")


@pytest.fixture(scope="session")
def client(api_key: str, base_url: str) -> NenDesktop:
    c = NenDesktop(api_key, base_url=base_url)
    yield c
    c.close()


@pytest.fixture(scope="session")
def desktop(client: NenDesktop):
    """Shared desktop for read-only tests (execute, tools, tool-logs)."""
    d = client.create_desktop()
    yield d
    try:
        client.delete_desktop(d.desktop_id)
    except Exception:
        pass
