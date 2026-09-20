"""The MCP server must answer its own website.

The spec's DNS-rebinding guidance says to validate the Origin header, and
the first reading of that here produced a loopback-only check. That is
right for a server only a local client talks to, and wrong the moment the
product's own site holds a session: the deployed server answered its own
front page with HTTP 403.

Both sibling projects hit this and fixed it. This one did not, because
until the Alexa+ panel existed nothing here had ever called the server
from a browser. Every conformance test passed and every curl agreed,
because a rule that only wrong callers can trip is indistinguishable from
a correct rule until a right caller turns up. That is the whole reason
this file exists: the check now has a test that a correct caller is
allowed in, not only that an incorrect one is kept out.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bellwether_server.app import build_app
from bellwether_server.mcp import SITE_ORIGIN, is_allowed_origin


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:3000",
        "http://127.0.0.1:8789",
        "https://127.0.0.1",
        "http://[::1]:5173",
        SITE_ORIGIN,
        SITE_ORIGIN + "/",
    ],
)
def test_callers_that_must_be_allowed(origin: str) -> None:
    assert is_allowed_origin(origin)


@pytest.mark.parametrize(
    "origin",
    [
        "https://evil.example.com",
        # The two that a naive substring or prefix check would wave
        # through, which is the mistake this kind of allowlist invites.
        SITE_ORIGIN + ".evil.com",
        "http://localhost.evil.com",
        "https://d1xfuyog8wiuvf.cloudfront.net.attacker.test",
    ],
)
def test_callers_that_must_be_refused(origin: str) -> None:
    assert not is_allowed_origin(origin)


def test_extra_origins_can_be_named_for_a_fork(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BELLWETHER_ALLOWED_ORIGINS", "https://fork.example, https://other.example/")
    assert is_allowed_origin("https://fork.example")
    assert is_allowed_origin("https://other.example")
    assert not is_allowed_origin("https://third.example")


def test_the_deployed_site_can_open_a_session() -> None:
    """End to end through the real route, with the site's own Origin.

    This is the assertion that would have caught the 403. It sends the
    exact request the browser panel sends, including the header a browser
    always attaches and curl never does.
    """
    client = TestClient(build_app())
    res = client.post(
        "/mcp",
        headers={
            "origin": SITE_ORIGIN,
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "bellwether-site", "version": "1"},
            },
        },
    )
    assert res.status_code == 200, res.text
    assert res.headers.get("mcp-session-id")


def test_a_foreign_origin_is_still_refused_through_the_route() -> None:
    client = TestClient(build_app())
    res = client.post(
        "/mcp",
        headers={"origin": "https://evil.example.com", "content-type": "application/json"},
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert res.status_code == 403
