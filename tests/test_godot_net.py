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
import contextlib
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

import numpy as np
import pytest
from websockets.asyncio.server import ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from simcore.host.server import BIND, HostConfig, start
from simcore.host.sessions import Session, Sessions
from simcore.host.tokens import Tokens
from simcore.protocol.catalogue import DTYPES, V0
from simcore.protocol.grammar import encode_cells
from simcore.protocol.messages import ClientMessage
from simcore.protocol.replies import welcome
from simcore.protocol.strict_json import encode
from tests.test_godot_check import gc

CLIENT = Path(__file__).resolve().parents[1] / "client"
TIMEOUT_S = 60.0
CLOSE_WAIT_S = 5.0  # after Godot exits, how long the server may take to see the close: short, so a miss fails fast

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
    assert lines == ["net-check: refused closed"]  # a TCP close with no WebSocket close frame: no reason to read


def _reply(session: Session, message: ClientMessage) -> Mapping[str, object]:
    return {"type": "error", "code": "unknown_kind"}  # the client sends only hello here


def _with_host(
    project: tuple[str, Path, Path], monkeypatch: pytest.MonkeyPatch, token_of: Callable[[Tokens], str]
) -> list[str]:
    async def go() -> list[str]:
        tokens = Tokens.fresh(guests=1)
        server = await start(HostConfig(sessions=Sessions(tokens, cap=2), shape=(2, 2, 2), dispatch=_reply))
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


def test_godot_may_drop_the_error_that_arrives_with_the_close_and_the_reason_still_says_why(project, monkeypatch):
    # The engine fact NetClient reads the close reason for (review A2, B26): a bare WebSocketPeer may or may not hold
    # the host's error text, which arrives in the poll the close does (0 packets in 14 of 16 runs, 1 in 2; delta 3
    # N-N3). What always holds is the reason, which is what NetClient reads when the text never came.
    monkeypatch.setenv("MAXIM_OVERDRIVE_NET_RAW", "1")
    lines = _with_host(project, monkeypatch, lambda t: "x" * 43)
    assert lines in (["net-check: raw packets 0 reason bad_token"], ["net-check: raw packets 1 reason bad_token"])


def _against(
    project: tuple[str, Path, Path],
    monkeypatch: pytest.MonkeyPatch,
    *,
    replies: list[str | bytes],
    close_reason: str | None = None,
) -> tuple[list[str], int | None, str | None]:
    """The client against a bare WebSocket server that answers its hello with ``replies`` (then closes 1008 with
    ``close_reason``, when given); the lines Godot printed, and the close code and reason the server saw."""
    closed: list[tuple[int | None, str | None]] = []
    done = asyncio.Event()

    async def handle(connection: ServerConnection) -> None:
        try:
            await connection.recv()  # the hello
            for reply in replies:
                await connection.send(reply)
            if close_reason is not None:
                await connection.close(1008, close_reason)
            with contextlib.suppress(ConnectionClosed):
                await connection.wait_closed()
        finally:  # recorded on every exit, so a client that never speaks fails fast with what Godot printed
            closed.append((connection.close_code, connection.close_reason))
            done.set()

    async def go() -> list[str]:
        async with serve(handle, BIND, 0, compression=None, max_size=None) as server:
            monkeypatch.setenv("MAXIM_OVERDRIVE_NET_PORT", str(next(iter(server.sockets)).getsockname()[1]))
            monkeypatch.setenv("MAXIM_OVERDRIVE_TOKEN", "t0ken")
            lines = await _net_check(project)
            with contextlib.suppress(TimeoutError):  # bounded: a client that never connected is reported below
                await asyncio.wait_for(done.wait(), CLOSE_WAIT_S)
            return lines

    lines = asyncio.run(go())
    assert closed, lines  # the client connected and the server saw the connection end
    return lines, *closed[0]


def test_a_frame_past_godot_s_default_buffer_reaches_the_client(project, monkeypatch):
    # 8 x 64 x 128 cells x 6 bytes: 393,216 bytes, six times WebSocketPeer's default 65,535 (client_rendering §4.3)
    shape = (8, 64, 128)
    channels = [(c, np.zeros(shape, np.dtype(DTYPES[c.dtype]))) for c in V0]
    frame = encode_cells(tick=1, regions_version=0, cell_size_um=100_000, origin_um=(0, 0, 0), catalogue=V0,
                         channels=channels)  # fmt: skip
    assert len(frame) > 6 * 65_535
    monkeypatch.setenv("MAXIM_OVERDRIVE_NET_FRAME", "1")
    welcomed = encode(welcome(session_id=1, role="host", shape=shape))
    lines, _, _ = _against(project, monkeypatch, replies=[welcomed, frame])
    assert lines == ["net-check: frame 8 64 128"]


def test_the_client_refuses_a_welcome_of_another_catalogue_and_closes_with_its_code(project, monkeypatch):
    other = dict(welcome(session_id=1, role="guest", shape=(2, 2, 2)), catalogue_hash="sha256/c14n-1:" + "0" * 64)
    lines, code, reason = _against(project, monkeypatch, replies=[encode(other)])
    assert lines == ["net-check: refused bad_version"]
    assert (code, reason) == (1000, "bad_version")  # the client closed, with its refusal as the reason


def test_a_close_reason_that_is_no_code_is_not_taken_as_one(project, monkeypatch):
    # The peer's reason becomes the refusal only in a refusal code's shape (delta review D-S2; delta 2 N-S2, D2-SF2)
    lines, _, _ = _against(project, monkeypatch, replies=[], close_reason="This is prose, not a code!")
    assert lines == ["net-check: refused closed"]
