"""The Godot client's connection against real listeners (boundaries §5.3; client_rendering §4.3, §7.5).

Two facts no Python test can show, because they are Godot's: the upgrade request Godot's WebSocketPeer sends carries
no ``Origin`` header (a raw listener captures the request bytes), and the client's NetClient, with its own strict
decoders, completes the handshake against the real host, reads ``welcome`` and finds its catalogue hash equal to the
server's; with a wrong token it records the host's ``bad_token``. Godot runs ``res://tests/net_check.gd`` through
``godot_check.run_godot`` in a worker thread while the listener serves on port 0 in this event loop; the token
reaches Godot by environment variable, never argv. Slow, behind ``MAXIM_OVERDRIVE_GODOT`` like the gate fixtures.
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

import pytest

from simcore.host.server import BIND, HostConfig, start
from simcore.host.sessions import Session, Sessions
from simcore.host.tokens import Tokens
from simcore.protocol.messages import ClientMessage
from tests.test_godot_check import gc

CLIENT = Path(__file__).resolve().parents[1] / "client"
TIMEOUT_S = 60.0

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not os.environ.get("MAXIM_OVERDRIVE_GODOT"), reason="slow: runs Godot; set MAXIM_OVERDRIVE_GODOT=1"
    ),
]


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> tuple[str, Path, Path]:
    """Godot, and the client imported once in a work directory of its own, with its home beside it."""
    godot = gc.find_godot(os.environ, sys.platform)
    if godot is None:
        pytest.fail("no Godot: install 4.7.2 (ci/install_godot.sh) or set GODOT; the gate needs it (B6)")
    work = tmp_path_factory.mktemp("net")
    imported = gc.copy_project(CLIENT, work / "client")
    assert gc.import_step(godot, CLIENT, imported, home=work / "home", timeout_s=TIMEOUT_S) == []
    return godot, imported, work / "home"


async def _net_check(project: tuple[str, Path, Path]) -> list[str]:
    godot, imported, home = project
    args = ["--headless", "--path", str(imported), "-s", "res://tests/net_check.gd"]
    run = await asyncio.to_thread(gc.run_godot, godot, "net", args, home=home, timeout_s=TIMEOUT_S)
    assert gc.error_findings(run) == []
    return [line for line in run.lines if line.startswith("net-check:")]


def test_godot_s_upgrade_request_carries_no_origin_header(project, monkeypatch):
    captured: list[bytes] = []

    async def capture(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        captured.append(await reader.readuntil(b"\r\n\r\n"))
        writer.close()  # no upgrade: the client sees a closed socket

    async def go() -> list[str]:
        server = await asyncio.start_server(capture, BIND, 0)
        async with server:
            monkeypatch.setenv("MAXIM_OVERDRIVE_NET_PORT", str(server.sockets[0].getsockname()[1]))
            monkeypatch.setenv("MAXIM_OVERDRIVE_TOKEN", "unused")
            return await _net_check(project)

    lines = asyncio.run(go())
    assert len(captured) == 1, lines
    headers = [h.split(b":", 1)[0].strip().lower() for h in captured[0].split(b"\r\n")[1:] if b":" in h]
    assert b"upgrade" in headers  # the capture saw a real WebSocket upgrade, so the next line can fail
    assert b"origin" not in headers
    assert lines == ["net-check: refused closed -1"]  # a TCP close with no WebSocket close frame: no code, no reason


def _reply(session: Session, message: ClientMessage) -> Mapping[str, object]:
    return {"type": "error", "code": "unknown_kind"}  # the client sends only hello here


def _with_host(
    project: tuple[str, Path, Path], monkeypatch: pytest.MonkeyPatch, token_of: Callable[[Tokens], str]
) -> list[str]:
    async def go() -> list[str]:
        tokens = Tokens.fresh(guests=1)
        server = await start(HostConfig(Sessions(tokens, cap=2), (2, 2, 2), _reply))
        try:
            monkeypatch.setenv("MAXIM_OVERDRIVE_NET_PORT", str(next(iter(server.sockets)).getsockname()[1]))
            monkeypatch.setenv("MAXIM_OVERDRIVE_TOKEN", token_of(tokens))
            return await _net_check(project)
        finally:
            server.close()
            await server.wait_closed()

    return asyncio.run(go())


def test_the_client_joins_the_real_host_and_shares_its_catalogue(project, monkeypatch):
    assert _with_host(project, monkeypatch, lambda t: t.guests[0]) == ["net-check: welcome guest catalogue same"]


def test_the_client_records_the_host_s_refusal_of_a_wrong_token(project, monkeypatch):
    assert _with_host(project, monkeypatch, lambda t: "x" * 43) == ["net-check: refused bad_token"]
