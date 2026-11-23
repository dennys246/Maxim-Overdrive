"""The host's WebSocket server: the handshake and the session loop (boundaries §5.3; client_rendering §4.3, §7.5).

Why these rules, in game-server terms: the server is authoritative and the only process with the world, and it
listens on a TCP port of the player's machine, where any local program and any web page the player opens can reach
it. So it binds the literal ``127.0.0.1`` (never ``localhost``, which may resolve to another interface), refuses any
request with an ``Origin`` header (browsers always send one; Godot's native WebSocketPeer sends none), answers plain
HTTP with a 400, and admits a connection as a session only after a ``hello`` with a per-launch token.

The handshake: ``hello`` comes first and once, within a deadline. Every refusal the server ends a connection with is
an ``error`` and then close 1008 whose reason is the same code (client_rendering §4.3): ``hello_first`` for no hello
in time, another message first or a second hello, ``bad_shape`` for a client's binary frame (only the server sends
binary), and the hello's own codes. Inbound messages are capped at ``MAX_MESSAGE_BYTES``, past which the transport
closes with 1009 before anything is parsed, and compression is off (v0 has none, and an inflated message could pass
the cap's intent). After ``welcome``, each message goes through decode and stage 1, a refusal answered with
``error``, and a message stage 1 accepts goes to ``dispatch``. ``dispatch`` runs on the network loop, so it may
answer from what it holds but never touch the world: the hand-off to the simulation lane through a bounded queue
(realtime_lanes_coop §4.1) and the replies that need its clock (``intent_result``, ``time_decision``, a ``snapshot``
frame) join with this step's ``intent_result``, after step 5a's clock.
"""

from __future__ import annotations

import asyncio
import http
import logging
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed
from websockets.frames import CloseCode
from websockets.http11 import Request, Response

from simcore.core.refusals import RefusalCode, Refused
from simcore.host.sessions import Session, Sessions
from simcore.protocol.messages import MAX_MESSAGE_BYTES, ClientMessage, Hello, HelloRefused, read_message
from simcore.protocol.replies import error, text, welcome

__all__ = ["BIND", "Dispatch", "HostConfig", "start"]

BIND = "127.0.0.1"  # the literal loopback address (boundaries §5.3)
MAX_QUEUE = 16  # frames received and not yet read, per connection: a bound, never websockets' default by accident

Dispatch = Callable[[Session, ClientMessage], Mapping[str, object]]


@dataclass(frozen=True, kw_only=True)
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
    upgrades = request.headers.get_all("Upgrade")  # get() raises on a repeated header: a 500, not a refusal
    if len(upgrades) != 1 or upgrades[0].lower() != "websocket":
        return connection.respond(http.HTTPStatus.BAD_REQUEST, "this port speaks WebSocket only\n")
    return None


class _Host:
    def __init__(self, config: HostConfig) -> None:
        self._config = config

    async def handle(self, connection: ServerConnection) -> None:
        """One connection's whole life: the hello, then a session from its open to its close on every exit path.

        A session is opened only once the hello has passed, and closed in the same ``finally`` that covers sending
        ``welcome``, so a client that leaves before reading it frees its token. A client that leaves at any point
        ends its connection quietly: leaving is not a server fault."""
        try:
            hello = await self._hello(connection)
            if hello is None:
                return
            try:
                session = self._config.sessions.open(hello.token)
            except Refused as refused:
                await self._refuse(connection, refused.code)
                return
            try:
                reply = welcome(session_id=session.session_id, role=session.role.value, shape=self._config.shape)
                await connection.send(text(reply))
                await self._serve(connection, session)
            finally:
                self._config.sessions.close(session)
        except ConnectionClosed:  # the client went away, or the transport closed it (1009)
            return

    async def _refuse(self, connection: ServerConnection, code: RefusalCode, field: str | None = None) -> None:
        """An ``error`` reply, then the close, whose reason is the same code: a client that drops a message arriving
        with the close (Godot 4.7.2 does) still reads why from the close (client_rendering §4.3)."""
        await connection.send(text(error(code, field)))
        await connection.close(CloseCode.POLICY_VIOLATION, code.value)

    async def _hello(self, connection: ServerConnection) -> Hello | None:
        """The first message, if it is a hello in this protocol, within the deadline; or None, the connection closed."""
        try:
            first = await asyncio.wait_for(connection.recv(), self._config.hello_deadline_s)
        except TimeoutError:
            await self._refuse(connection, RefusalCode.HELLO_FIRST)
            return None
        if not isinstance(first, str):
            await self._refuse(connection, RefusalCode.BAD_SHAPE)  # client frames are text
            return None
        try:
            hello = read_message(first)
        except Refused as refused:
            await self._refuse(connection, refused.code, refused.field)
            return None
        if not isinstance(hello, Hello):
            await self._refuse(connection, RefusalCode.HELLO_FIRST)
            return None
        return hello

    async def _serve(self, connection: ServerConnection, session: Session) -> None:
        async for data in connection:
            if not isinstance(data, str):
                await self._refuse(connection, RefusalCode.BAD_SHAPE)  # client frames are text
                return
            if not await self._answer(connection, session, data):
                return

    async def _answer(self, connection: ServerConnection, session: Session, data: str) -> bool:
        """The reply to one message after welcome; False when the connection is closed instead."""
        try:
            message = read_message(data)
        except HelloRefused:  # a second hello, even a malformed one, ends the session
            await self._refuse(connection, RefusalCode.HELLO_FIRST)
            return False
        except Refused as refused:
            await connection.send(text(error(refused.code, refused.field)))
            return True
        if isinstance(message, Hello):
            await self._refuse(connection, RefusalCode.HELLO_FIRST)  # hello comes once
            return False
        await connection.send(text(self._config.dispatch(session, message)))
        return True


class _QuietLogger(logging.LoggerAdapter[logging.Logger]):
    """The transport's logger, which never logs at DEBUG: websockets logs every frame's text there, a hello and its
    token among them, so the transport's frames can never reach a log whatever level the game sets."""

    def isEnabledFor(self, level: int) -> bool:
        return level > logging.DEBUG and self.logger.isEnabledFor(level)


async def start(config: HostConfig) -> Server:
    """The host's server, listening on ``BIND`` at ``config.port``; the caller closes it."""
    host = _Host(config)
    return await serve(
        host.handle,
        BIND,
        config.port,
        process_request=_gate,
        max_size=MAX_MESSAGE_BYTES,
        max_queue=MAX_QUEUE,
        compression=None,
        logger=_QuietLogger(logging.getLogger("simcore.host.server")),
    )
