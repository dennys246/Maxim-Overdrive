import base64
import json
import struct
import zlib

import numpy as np
import pytest
from slice_server.wire import MAX_FRAME, FrameReader, WireRefused, encode, pack_cells


def test_frames_round_trip_even_when_split_across_reads() -> None:
    stream = encode({"type": "move", "n": 1}) + encode({"type": "kindle"})
    reader, got = FrameReader(), []
    for i in range(len(stream)):  # one byte at a time
        got += list(reader.feed(stream[i : i + 1]))
    assert got == [{"type": "move", "n": 1}, {"type": "kindle"}]


def _refusal(data: bytes) -> str:
    with pytest.raises(WireRefused) as caught:
        list(FrameReader().feed(data))
    return caught.value.code


def test_an_oversized_frame_is_refused() -> None:
    assert _refusal(struct.pack(">I", MAX_FRAME + 1) + b"x") == "frame_too_large"


@pytest.mark.parametrize("start", [b"GET / HTTP/1.1\r\n", b"POST /x HTTP/1.1\r\n", b"OPTIONS * HTTP/1.1\r\n"])
def test_http_is_refused_at_the_first_bytes(start: bytes) -> None:
    assert _refusal(start) == "http_refused"


@pytest.mark.parametrize("body", [b"{", b"[1]", b'{"x": NaN}', b'{"x": Infinity}', b"\xff\xfe"])
def test_a_body_that_is_not_a_finite_json_object_is_refused(body: bytes) -> None:
    assert _refusal(struct.pack(">I", len(body)) + body) == "bad_json"


def test_the_server_never_sends_nan() -> None:
    with pytest.raises(ValueError, match="JSON compliant"):
        encode({"x": float("nan")})


def test_packed_cells_inflate_to_the_same_bytes() -> None:
    cells = np.arange(60, dtype=np.uint8).reshape(3, 4, 5)
    packed = json.loads(json.dumps(pack_cells(cells)))
    raw = zlib.decompress(base64.b64decode(packed["z"]))
    assert packed["n"] == len(raw) == 60
    assert raw == cells.tobytes()  # C order: index (i * ny + j) * nz + k, which the client relies on
