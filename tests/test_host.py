"""The host's handshake and session loop, against a real server on port 0 with real WebSocket clients (boundaries
§5.3; client_rendering §4.3; tile §3.4). Every client passes ``proxy=None``: websockets reads proxy settings from
the environment otherwise, and a test reaches nothing beyond localhost."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import stat
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import pytest
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidStatus

from simcore.core.refusals import RefusalCode, Refused
from simcore.host.server import BIND, HostConfig, start
from simcore.host.sessions import Decision, HostOnly, Session, Sessions, SessionView, TimeAuthority
from simcore.host.tokens import Role, Tokens, write_token_file
from simcore.protocol.catalogue import V0, catalogue_hash, describe
from simcore.protocol.messages import MAX_MESSAGE_BYTES, ClientMessage
from simcore.protocol.replies import BUILD

SHAPE = (4, 5, 6)


def _echo(session: Session, message: ClientMessage) -> Mapping[str, object]:
    return {"type": "test_echo", "session": session.session_id, "kind": type(message).__name__}


@asynccontextmanager
async def _host(*, guests: int = 1, cap: int = 4, deadline: float = 5.0) -> AsyncIterator[tuple[str, Tokens]]:
    tokens = Tokens.fresh(guests=guests)
    config = HostConfig(sessions=Sessions(tokens, cap=cap), shape=SHAPE, dispatch=_echo, hello_deadline_s=deadline)
    server = await start(config)
    port = next(iter(server.sockets)).getsockname()[1]
    try:
        yield f"ws://{BIND}:{port}", tokens
    finally:
        server.close()
        await server.wait_closed()


def _open(uri: str, **kwargs: Any) -> Any:
    return connect(uri, proxy=None, compression=None, **kwargs)


def _hello(token: str, protocol: int = 0) -> str:
    return json.dumps({"type": "hello", "protocol": protocol, "token": token})


# A bound on each wait, so a guard that breaks fails the test instead of hanging the gate (no reply ever comes, or the
# connection is never closed). It never decides an outcome: each test's answer is a message or a close code.
WAIT_S = 10.0


async def _reply(ws: ClientConnection) -> dict[str, Any]:
    data = await asyncio.wait_for(ws.recv(), WAIT_S)
    assert isinstance(data, str)
    reply: dict[str, Any] = json.loads(data)
    return reply


async def _drain(ws: ClientConnection) -> None:
    while True:
        await ws.recv()


async def _closed(ws: ClientConnection) -> int | None:
    with pytest.raises(ConnectionClosed):
        await asyncio.wait_for(_drain(ws), WAIT_S)
    return ws.close_code


async def _closed_with(ws: ClientConnection) -> tuple[int | None, str | None]:
    """The close code and reason, after any messages before the close."""
    return await _closed(ws), ws.close_reason


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def test_the_server_binds_the_literal_loopback_address():
    async def go() -> list[str]:
        tokens = Tokens.fresh(guests=0)
        server = await start(HostConfig(sessions=Sessions(tokens, cap=1), shape=SHAPE, dispatch=_echo))
        try:
            return [s.getsockname()[0] for s in server.sockets]
        finally:
            server.close()
            await server.wait_closed()

    assert run(go()) == ["127.0.0.1"]


def test_a_hello_with_the_host_token_is_welcomed_with_the_build_the_shape_and_the_catalogue():
    async def go() -> dict[str, Any]:
        async with _host() as (uri, tokens), _open(uri) as ws:
            await ws.send(_hello(tokens.host))
            return await _reply(ws)

    welcome = run(go())
    assert welcome == {
        "type": "welcome", "protocol": 0, "session": 1, "role": "host", "build": BUILD, "shape": list(SHAPE),
        "catalogue": describe(V0), "catalogue_hash": catalogue_hash(describe(V0)),
    }  # fmt: skip


def test_a_guest_token_is_a_guest_and_sessions_are_numbered_in_order():
    async def go() -> list[tuple[int, str]]:
        async with _host(guests=2) as (uri, tokens), _open(uri) as a, _open(uri) as b:
            await a.send(_hello(tokens.guests[1]))
            first = await _reply(a)  # welcomed before the second hello is sent, so the order is the test's
            await b.send(_hello(tokens.host))
            return [(r["session"], r["role"]) for r in (first, await _reply(b))]

    assert run(go()) == [(1, "guest"), (2, "host")]


@pytest.mark.parametrize("origin", ["http://evil.example", "", "null"])
def test_any_origin_header_is_refused_before_the_upgrade(origin):
    async def go() -> int:
        async with _host() as (uri, _):
            with pytest.raises(InvalidStatus) as refused:
                async with _open(uri, additional_headers={"Origin": origin}):
                    pass
            return refused.value.response.status_code

    assert run(go()) == 403


def test_plain_http_to_the_port_gets_a_400():
    async def go() -> bytes:
        async with _host() as (uri, _):
            port = int(uri.rsplit(":", 1)[1])
            reader, writer = await asyncio.open_connection(BIND, port)
            writer.write(b"GET / HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
            await writer.drain()
            status = await reader.readline()
            writer.close()
            await writer.wait_closed()
            return status

    assert run(go()).startswith(b"HTTP/1.1 400")


@pytest.mark.parametrize(
    ("first", "code"),
    [
        (json.dumps({"type": "snapshot", "seq": 1}), "hello_first"),  # anything but hello first
        (b"\x00\x01", "bad_shape"),  # a client binary frame: only the server sends binary
    ],
)
def test_anything_but_a_hello_first_gets_an_error_and_a_close_with_its_code(first, code):
    async def go() -> tuple[dict[str, Any], tuple[int | None, str | None]]:
        async with _host() as (uri, _), _open(uri) as ws:
            await ws.send(first)
            return await _reply(ws), await _closed_with(ws)

    assert run(go()) == ({"type": "error", "code": code}, (1008, code))


def test_no_hello_within_the_deadline_closes_the_connection_with_hello_first():
    async def go() -> tuple[int | None, str | None]:
        async with _host(deadline=0.0) as (uri, _), _open(uri) as ws:
            return await _closed_with(ws)

    assert run(go()) == (1008, "hello_first")


def test_a_client_that_leaves_before_reading_welcome_frees_its_token():
    # The session opens when the hello passes; a client gone before welcome is sent must not keep it (review C1).
    async def go() -> list[str]:
        tokens = Tokens.fresh(guests=0)
        sessions = Sessions(tokens, cap=1)
        server = await start(HostConfig(sessions=sessions, shape=SHAPE, dispatch=_echo))
        uri = f"ws://{BIND}:{next(iter(server.sockets)).getsockname()[1]}"
        outcomes = []
        try:
            for _ in range(3):  # three times over a cap of one: a leak turns the next hello into token_in_use
                async with _open(uri) as ws:
                    await ws.send(_hello(tokens.host))
                await asyncio.wait_for(_until_no_session(sessions), WAIT_S)
                outcomes.append("freed")
            return outcomes
        finally:
            server.close()
            await server.wait_closed()

    assert run(go()) == ["freed", "freed", "freed"]


async def _until_no_session(sessions: Sessions) -> None:
    """Yield to the loop until the server has closed every session (its handlers run between the yields)."""
    while sessions.view().sessions:
        await asyncio.sleep(0)


def test_a_client_that_leaves_mid_handshake_is_not_logged_as_a_server_error(caplog):
    async def go() -> None:
        async with _host() as (uri, tokens):
            async with _open(uri) as ws:
                await ws.send(_hello(tokens.host))
            async with _open(uri) as ws:
                await ws.send("not json")
            await asyncio.sleep(0)

    caplog.set_level(logging.INFO)
    run(go())
    assert not [r for r in caplog.records if r.levelno >= logging.WARNING]


@pytest.mark.parametrize(
    ("hello", "code"),
    [
        (lambda t: _hello("x" * 43), "bad_token"),
        (lambda t: _hello(t.host, protocol=1), "bad_version"),
        (lambda t: '{"type":"hello","protocol":0,"token":"' + t.host + '","role":"host"}', "unknown_field"),
        (lambda t: '{"type":"hello","protocol":0.0,"token":"' + t.host + '"}', "bad_version"),
        (lambda t: '{"type":"hello","protocol":1,"token":"' + t.host + '","compat":[1]}', "bad_version"),
        (lambda t: '{"type":"hello","protocol":1,"token":"' + "t" * 99 + '"}', "bad_version"),
        (lambda t: "not json", "bad_json"),
    ],
)
def test_a_bad_hello_gets_an_error_then_a_close_whose_reason_is_the_code(hello, code):
    # The close reason repeats the code because Godot drops a text packet that arrives with the close
    # (tests/test_godot_net.py), so the close is what the Godot client reads.
    async def go() -> tuple[dict[str, Any], int | None, str | None]:
        async with _host() as (uri, tokens), _open(uri) as ws:
            await ws.send(hello(tokens))
            reply = await _reply(ws)
            return reply, await _closed(ws), ws.close_reason

    reply, close, reason = run(go())
    assert reply["type"] == "error"
    assert reply["code"] == code
    assert (close, reason) == (1008, code)


def test_the_version_error_names_the_protocol_field():
    async def go() -> dict[str, Any]:
        async with _host() as (uri, tokens), _open(uri) as ws:
            await ws.send(_hello(tokens.host, protocol=1))
            return await _reply(ws)

    assert run(go()) == {"type": "error", "code": "bad_version", "field": "protocol"}


def test_one_live_session_per_token_and_the_token_is_free_again_once_it_closes():
    async def go() -> tuple[str, str]:
        async with _host() as (uri, tokens):
            async with _open(uri) as first:
                await first.send(_hello(tokens.host))
                await _reply(first)
                async with _open(uri) as second:
                    await second.send(_hello(tokens.host))
                    refused = (await _reply(second))["code"]
            async with _open(uri) as again:
                await again.send(_hello(tokens.host))
                return refused, (await _reply(again))["type"]

    assert run(go()) == ("token_in_use", "welcome")


def test_the_session_cap_refuses_one_more_with_busy():
    async def go() -> str:
        async with _host(guests=2, cap=1) as (uri, tokens), _open(uri) as a, _open(uri) as b:
            await a.send(_hello(tokens.host))
            await _reply(a)
            await b.send(_hello(tokens.guests[0]))
            code: str = (await _reply(b))["code"]
            return code

    assert run(go()) == "busy"


@pytest.mark.parametrize(
    ("message", "code"),
    [
        ('{"type":"kindle","seq":1,"point_mm":[1,2,3],"duration_ticks":5500.0}', "not_int"),
        ('{"type":"kindle","seq":1,"point_mm":[1,2,3],"duration_ticks":true}', "not_int"),
        ('{"type":"time","seq":1,"op":"set_scale","scale":NaN}', "bad_json"),
        ('{"type":"snapshot","seq":9007199254740993}', "bad_json"),
        ('{"type":"move","seq":1,"dir":[1,0],"actor":2}', "unknown_field"),
        ('{"type":"vote","seq":1}', "unknown_kind"),
    ],
)
def test_after_welcome_a_message_refused_at_decode_or_stage_1_gets_an_error_and_the_session_goes_on(message, code):
    async def go() -> tuple[dict[str, Any], dict[str, Any]]:
        async with _host() as (uri, tokens), _open(uri) as ws:
            await ws.send(_hello(tokens.host))
            await _reply(ws)
            await ws.send(message)
            refused = await _reply(ws)
            await ws.send('{"type":"snapshot","seq":2}')
            return refused, await _reply(ws)

    refused, after = run(go())
    assert refused == {"type": "error", "code": code}
    assert after == {"type": "test_echo", "session": 1, "kind": "Snapshot"}


def test_a_message_past_the_cap_closes_with_1009_and_one_at_it_does_not():
    async def go() -> tuple[str, int | None]:
        async with _host() as (uri, tokens), _open(uri, max_size=None) as ws:
            await ws.send(_hello(tokens.host))
            await _reply(ws)
            head, tail = '{"type":"snapshot","seq":1,"pad":"', '"}'
            at_cap = head + "x" * (MAX_MESSAGE_BYTES - len(head) - len(tail)) + tail
            assert len(at_cap.encode()) == MAX_MESSAGE_BYTES
            await ws.send(at_cap)
            within = (await _reply(ws))["code"]  # decoded and refused for its field, not closed
            await ws.send("x" * (MAX_MESSAGE_BYTES + 1))
            return within, await _closed(ws)

    assert run(go()) == ("unknown_field", 1009)


@pytest.mark.parametrize(("message", "code"), [(b"\x00", "bad_shape"), ("HELLO", "hello_first")])
def test_after_welcome_a_binary_frame_or_a_second_hello_ends_the_session_with_its_code(message, code):
    async def go() -> tuple[dict[str, Any], tuple[int | None, str | None]]:
        async with _host() as (uri, tokens), _open(uri) as ws:
            await ws.send(_hello(tokens.host))
            await _reply(ws)
            await ws.send(_hello(tokens.host) if message == "HELLO" else message)
            return await _reply(ws), await _closed_with(ws)

    assert run(go()) == ({"type": "error", "code": code}, (1008, code))


def test_the_server_negotiates_no_compression():
    async def go() -> str | None:
        async with _host() as (uri, _), connect(uri, proxy=None, compression="deflate") as ws:
            assert ws.response is not None
            return ws.response.headers.get("Sec-WebSocket-Extensions")

    assert run(go()) is None


def test_no_token_reaches_a_log_a_reply_or_a_repr(caplog):
    async def go(tokens_out: list[Tokens]) -> list[str]:
        async with _host(guests=1) as (uri, tokens):
            tokens_out.append(tokens)
            replies = []
            async with _open(uri) as ws:
                await ws.send(_hello(tokens.host[:-1] + "!"))  # a malformed token: refused for its shape
                replies.append(await ws.recv())
            async with _open(uri) as ws:
                await ws.send(_hello(tokens.guests[0], protocol=7))
                replies.append(await ws.recv())
            return [str(r) for r in replies]

    caplog.set_level(logging.DEBUG)
    held: list[Tokens] = []
    replies = run(go(held))
    # The server's records: the test's own client (websockets.client) logs what it sends, which is the test's business
    server_logs = [r for r in caplog.records if not r.name.startswith("websockets.client")]
    text = "\n".join(r.getMessage() for r in server_logs) + "".join(replies) + repr(held[0])
    # Any 8 characters of a token in a row (websockets' DEBUG frame lines show a truncated message, review T-S1)
    pieces = {s[i : i + 8] for s in [held[0].host, *held[0].guests] for i in range(len(s) - 7)}
    assert server_logs  # the server did log, so the check below can fail
    assert not [p for p in pieces if p in text]


def test_a_token_file_is_new_and_readable_only_by_its_owner(tmp_path: Path):
    path = tmp_path / "token"
    write_token_file(path, "t0ken")
    assert path.read_text() == "t0ken"
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    with pytest.raises(FileExistsError):
        write_token_file(path, "other")


def test_tokens_are_fresh_url_safe_and_bound_to_their_role():
    a, b = Tokens.fresh(guests=2), Tokens.fresh(guests=2)
    assert set([a.host, *a.guests]).isdisjoint([b.host, *b.guests])
    assert len(a.host) == 43
    assert (a.match(a.host), a.match(a.guests[1]), a.match(b.host)) == (0, 2, None)
    assert (Tokens.role(0), Tokens.role(1)) == (Role.HOST, Role.GUEST)
    with pytest.raises(Refused, match="0 to 8") as refused:
        Tokens.fresh(guests=9)
    assert refused.value.code is RefusalCode.OUT_OF_RANGE


# --- time authority (WT-S9: HostOnly tested directly, with a guest-role view) ---------------------------------------


def test_host_only_grants_the_host_and_refuses_a_guest_with_a_reason_never_pending():
    view = SessionView((Session(1, Role.GUEST, 1), Session(2, Role.HOST, 0)))
    authority: TimeAuthority = HostOnly()  # held to the interface the host calls
    assert authority.decide(view, 2) == Decision(True, None)
    assert authority.decide(view, 1) == Decision(False, RefusalCode.HOST_ONLY)
    assert authority.decide(view, 99) == Decision(False, RefusalCode.HOST_ONLY)  # a session the view doesn't hold


def test_an_authority_decides_from_a_frozen_view_of_the_sessions():
    tokens = Tokens.fresh(guests=1)
    sessions = Sessions(tokens, cap=2)
    guest = sessions.open(tokens.guests[0])
    view = sessions.view()
    host = sessions.open(tokens.host)
    assert view.role_of(host.session_id) is None  # taken before the host joined: the view doesn't change
    assert sessions.view().role_of(host.session_id) is Role.HOST
    sessions.close(guest)
    assert view.role_of(guest.session_id) is Role.GUEST
    with pytest.raises(AttributeError):
        view.sessions = ()  # type: ignore[misc]  # frozen


def test_a_decision_and_the_session_table_refuse_what_can_t_be():
    with pytest.raises(TypeError, match="no reason"):
        Decision(True, RefusalCode.HOST_ONLY)
    with pytest.raises(TypeError, match="no reason"):
        Decision(False, None)
    with pytest.raises(TypeError, match="at least one"):
        Sessions(Tokens.fresh(guests=0), cap=0)
