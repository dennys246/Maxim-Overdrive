"""The slice's wire, ``slice-0``: length-prefixed JSON frames over TCP on 127.0.0.1 (plan §3.2).

A frame is a 4-byte big-endian length, then that many bytes of UTF-8 JSON holding one object. The reader refuses,
and the server then closes the connection:

- a frame over ``MAX_FRAME`` bytes;
- a stream that starts like HTTP. A browser can't open a raw socket, but it can send a request to any local port,
  and that is what the protocol's ``Origin`` refusal is for; here the request's first bytes are refused outright;
- a body that isn't JSON, or holds NaN or Infinity, or isn't an object.

Cell arrays travel zlib-compressed and base64-encoded inside the JSON (Godot inflates them with
``PackedByteArray.decompress``). Not versioned beyond its name on purpose: step 7 designs the real protocol.
"""

from __future__ import annotations

import base64
import json
import struct
import zlib
from collections.abc import Iterator

import numpy as np
import numpy.typing as npt

MAX_FRAME = 1 << 20  # client frames are small intents; a megabyte is a generous ceiling
HTTP_STARTS = (b"GET ", b"POST", b"PUT ", b"HEAD", b"OPTI", b"DELE", b"PATC", b"CONN", b"TRAC")
_LENGTH = struct.Struct(">I")


class WireRefused(ValueError):
    """The peer sent something the wire refuses; ``code`` names it for the error reply and the log."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _no_constants(name: str) -> object:
    raise WireRefused("bad_json", f"{name} is not a finite number")


def decode(body: bytes) -> dict[str, object]:
    try:
        value = json.loads(body.decode("utf-8"), parse_constant=_no_constants)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WireRefused("bad_json", str(exc)) from None
    if not isinstance(value, dict):
        raise WireRefused("bad_json", f"a frame holds an object, got {type(value).__name__}")
    return value


def encode(message: dict[str, object]) -> bytes:
    body = json.dumps(message, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return _LENGTH.pack(len(body)) + body


class FrameReader:
    """Splits a byte stream into decoded frames. Feed it what ``recv`` returned; it yields every complete frame."""

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._first = True

    def feed(self, data: bytes) -> Iterator[dict[str, object]]:
        self._buffer += data
        if self._first and len(self._buffer) >= 4:
            self._first = False
            if bytes(self._buffer[:4]) in HTTP_STARTS:
                raise WireRefused("http_refused", "this port speaks slice-0, not HTTP")
        while len(self._buffer) >= 4:
            (length,) = _LENGTH.unpack_from(self._buffer)
            if length > MAX_FRAME:
                raise WireRefused("frame_too_large", f"{length} bytes, over {MAX_FRAME}")
            if len(self._buffer) < 4 + length:
                return
            body = bytes(self._buffer[4 : 4 + length])
            del self._buffer[: 4 + length]
            yield decode(body)


def pack_cells(array: npt.NDArray[np.uint8]) -> dict[str, object]:
    """A uint8 cell array, C order, as the JSON a client inflates: its byte count and the compressed bytes."""
    raw = np.ascontiguousarray(array, dtype=np.uint8).tobytes()
    return {"n": len(raw), "z": base64.b64encode(zlib.compress(raw, 6)).decode("ascii")}
