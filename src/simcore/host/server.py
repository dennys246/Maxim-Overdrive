"""The host's WebSocket server: the handshake and the session loop (boundaries §5.3; client_rendering §4.3, §7.5).

Why these rules, in game-server terms: the server is authoritative and the only process with the world, and it
listens on a TCP port of the player's machine, where any local program and any web page the player opens can reach
it. So it binds the literal ``127.0.0.1`` (never ``localhost``, which may resolve to another interface), refuses any
request with an ``Origin`` header (browsers always send one; Godot's native WebSocketPeer sends none), answers plain
HTTP with a 400, and admits a connection as a session only after a ``hello`` with a per-launch token.

The handshake: ``hello`` comes first and once, within a deadline; anything else closes the connection. A client's
binary frame is refused (close 1003): only the server sends binary. Inbound messages are capped at
``MAX_MESSAGE_BYTES``, past which the transport closes with 1009 before anything is parsed, and compression is off
(v0 has none, and an inflated message could pass the cap's intent). After ``welcome``, each message goes through
decode and stage 1, a refusal answered with ``error``, and a message stage 1 accepts goes to ``dispatch``, the
caller's: the replies that need the simulation's clock (``intent_result``, ``time_decision``, a ``snapshot`` frame)
join with step 5a.
"""

from __future__ import annotations

import asyncio
import http
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed
from websockets.frames import CloseCode
from websockets.http11 import Request, Response

from simcore.core.refusals import RefusalCode, Refused
from simcore.host.sessions import Session, Sessions
from simcore.protocol.messages import MAX_MESSAGE_BYTES, PROTOCOL, ClientMessage, Hello, read_message
from simcore.protocol.replies import error, welcome
from simcore.protocol.strict_json import encode

__all__ = ["BIND", "Dispatch", "HostConfig", "start"]

BIND = "127.0.0.1"  # the literal loopback address (boundaries §5.3)

Dispatch = Callable[[Session, ClientMessage], Mapping[str, object]]


@dataclass(frozen=True)
class HostConfig:
    sessions: Sessions
    shape: tuple[int, int, int]
    dispatch: Dispatch
    hello_deadline_s: float = 5.0
    port: int = 0  # 0: the OS picks a free port (every test binds 0)


def _gate(connection: ServerConnection, request: Request) -> Response | None:
    """Before the upgrade: no Origin header of any value (an empty one and "null" too), and a WebSocket upgrade only."""
    if "Origin" in request.headers:
        return connection.respond(http.HTTPStatus.FORBIDDEN, "no Origin header is accepted\n")
    if request.headers.get("Upgrade", "").lower() != "websocket":
        return connection.respond(http.HTTPStatus.BAD_REQUEST, "this port speaks WebSocket only\n")
    return None


class _Host:
    def __init__(self, config: HostConfig) -> None:
        self._config = config

    async def handle(self, connection: ServerConnection) -> None:
        session = await self._handshake(connection)
        if session is None:
            return
        try:
            await self._serve(connection, session)
        finally:
            self._config.sessions.close(session)

    async def _refuse(self, connection: ServerConnection, code: RefusalCode, field: str | None = None) -> None:
        """An ``error`` reply, then the close: the end of a handshake that failed."""
        await connection.send(encode(error(code, field)))
        await connection.close(CloseCode.POLICY_VIOLATION, code.value)

    async def _handshake(self, connection: ServerConnection) -> Session | None:
        """A session for the connection's hello, with ``welcome`` sent; or None, the connection closed."""
        hello = await self._hello(connection)
        if hello is None:
            return None
        try:
            session = self._config.sessions.open(hello.token)
        except Refused as refused:
            await self._refuse(connection, refused.code)
            return None
        reply = welcome(session_id=session.session_id, role=session.role.value, shape=self._config.shape)
        await connection.send(encode(reply))
        return session

    async def _hello(self, connection: ServerConnection) -> Hello | None:
        """The first message, if it is a hello in this protocol, within the deadline; or None, the connection closed."""
        try:
            first = await asyncio.wait_for(connection.recv(), self._config.hello_deadline_s)
        except TimeoutError:
            await connection.close(CloseCode.POLICY_VIOLATION, "hello first, within the deadline")
            return None
        if not isinstance(first, str):
            await connection.close(CloseCode.UNSUPPORTED_DATA, "client frames are text")
            return None
        try:
            hello = read_message(first)
        except Refused as refused:
            await self._refuse(connection, refused.code, refused.field)
            return None
        if not isinstance(hello, Hello):
            await connection.close(CloseCode.POLICY_VIOLATION, "hello first")
            return None
        if hello.protocol != PROTOCOL:
            await self._refuse(connection, RefusalCode.BAD_VERSION, "protocol")
            return None
        return hello

    async def _serve(self, connection: ServerConnection, session: Session) -> None:
        try:
            async for data in connection:
                if not isinstance(data, str):
                    await connection.close(CloseCode.UNSUPPORTED_DATA, "client frames are text")
                    return
                await self._answer(connection, session, data)
        except ConnectionClosed:  # the client went away, or the transport closed it (1009): the session ends
            return

    async def _answer(self, connection: ServerConnection, session: Session, data: str) -> None:
        try:
            message = read_message(data)
        except Refused as refused:
            await connection.send(encode(error(refused.code, refused.field)))
            return
        if isinstance(message, Hello):
            await connection.close(CloseCode.POLICY_VIOLATION, "hello only once")
            return
        await connection.send(encode(dict(self._config.dispatch(session, message))))


async def start(config: HostConfig) -> Server:
    """The host's server, listening on ``BIND`` at ``config.port``; the caller closes it."""
    host = _Host(config)
    return await serve(
        host.handle,
        BIND,
        config.port,
        process_request=_gate,
        max_size=MAX_MESSAGE_BYTES,
        compression=None,
    )
