# Wire protocol v0 (generated)

Generated from `src/simcore/protocol/` by `simcore.protocol.registry.render()`; `tests/test_wire.py`
compares it byte for byte. Edit the code, never this file. The contracts are
`docs/design/client_rendering.md` §4 and `docs/design/tile_and_client.md` §3.3.

- **protocol:** 0.
- **JSON:** integers of magnitude at most 9007199254740991 (2^53 - 1); no NaN or infinity; no repeated key;
  containers nested at most 32 deep; a client message at most 65536 bytes.

## Client messages

A JSON object whose `type` names it.

### `hello`

| Field | Required | Null | Read by |
|---|---|---|---|
| `protocol` | yes | no | `Whole(lo=0, hi=9007199254740991)` |
| `token` | yes | no | `Opaque(max_chars=64)` |

### `move`

| Field | Required | Null | Read by |
|---|---|---|---|
| `seq` | yes | no | `Whole(lo=0, hi=2147483647)` |
| `dir` | yes | yes | `Wholes(n=2, lo=-9007199254740991, hi=9007199254740991)` |

### `move_to`

| Field | Required | Null | Read by |
|---|---|---|---|
| `seq` | yes | no | `Whole(lo=0, hi=2147483647)` |
| `target_mm` | yes | no | `Wholes(n=2, lo=-9007199254740991, hi=9007199254740991)` |

### `kindle`

| Field | Required | Null | Read by |
|---|---|---|---|
| `seq` | yes | no | `Whole(lo=0, hi=2147483647)` |
| `point_mm` | yes | no | `Wholes(n=3, lo=-9007199254740991, hi=9007199254740991)` |
| `duration_ticks` | yes | no | `Whole(lo=-9007199254740991, hi=9007199254740991)` |

### `time`

| Field | Required | Null | Read by |
|---|---|---|---|
| `seq` | yes | no | `Whole(lo=0, hi=2147483647)` |
| `op` | yes | no | `Choice(words=('pause', 'resume', 'set_scale'))` |
| `scale` | no | yes | `Real(lo=None, hi=None, lo_open=False)` |

### `snapshot`

| Field | Required | Null | Read by |
|---|---|---|---|
| `seq` | yes | no | `Whole(lo=0, hi=2147483647)` |

## Cell frame

`[u32 header length][JSON header][arrays]`, little-endian.

### header

| Field | Required | Null | Read by |
|---|---|---|---|
| `protocol` | yes | no | `Whole(lo=0, hi=9007199254740991)` |
| `kind` | yes | no | `Choice(words=('full',))` |
| `tick` | yes | no | `Whole(lo=0, hi=9007199254740991)` |
| `shape` | yes | no | `Wholes(n=3, lo=1, hi=65535)` |
| `regions_version` | yes | no | `Whole(lo=0, hi=9007199254740991)` |
| `catalogue` | yes | no | `Digest()` |
| `compression` | yes | no | `Choice(words=('none',))` |
| `grids` | yes | no | `ListOf(item=Nested(schema=Schema(fields=(Field(name='name', convert=Identity(max_chars=64), required=True, default=None, nullable=False, lookup=None), Field(name='required', convert=Flag(), required=True, default=None, nullable=False, lookup=None), Field(name='shape', convert=Wholes(n=3, lo=1, hi=65535), required=True, default=None, nullable=False, lookup=None), Field(name='cell_size_um', convert=Whole(lo=1, hi=9007199254740991), required=True, default=None, nullable=False, lookup=None), Field(name='origin_um', convert=Wholes(n=3, lo=-9007199254740991, hi=9007199254740991), required=True, default=None, nullable=False, lookup=None)), reserved=mappingproxy({}), wire=False)), max_items=8)` |
| `tables` | yes | no | `ListOf(item=Nested(schema=Schema(fields=(Field(name='name', convert=Identity(max_chars=64), required=True, default=None, nullable=False, lookup=None), Field(name='required', convert=Flag(), required=True, default=None, nullable=False, lookup=None), Field(name='rows', convert=Whole(lo=0, hi=9007199254740991), required=True, default=None, nullable=False, lookup=None)), reserved=mappingproxy({}), wire=False)), max_items=16)` |
| `arrays` | yes | no | `ListOf(item=Nested(schema=Schema(fields=(Field(name='channel', convert=Nested(schema=Schema(fields=(Field(name='name', convert=Identity(max_chars=64), required=True, default=None, nullable=False, lookup=None), Field(name='unit', convert=Identity(max_chars=64), required=True, default=None, nullable=False, lookup=None), Field(name='dtype', convert=Choice(words=('u8', 'u16', 'u32', 'f16', 'f32')), required=True, default=None, nullable=False, lookup=None), Field(name='encoding', convert=Choice(words=('raw', 'linear')), required=True, default=None, nullable=False, lookup=None), Field(name='required', convert=Flag(), required=True, default=None, nullable=False, lookup=None), Field(name='scale', convert=Wholes(n=2, lo=-9007199254740991, hi=9007199254740991), required=True, default=None, nullable=False, lookup=None), Field(name='offset', convert=Wholes(n=2, lo=-9007199254740991, hi=9007199254740991), required=True, default=None, nullable=False, lookup=None)), reserved=mappingproxy({}), wire=False)), required=True, default=None, nullable=False, lookup=None), Field(name='of', convert=Identity(max_chars=64), required=True, default=None, nullable=False, lookup=None), Field(name='offset', convert=Whole(lo=0, hi=9007199254740991), required=True, default=None, nullable=False, lookup=None), Field(name='size', convert=Whole(lo=0, hi=9007199254740991), required=True, default=None, nullable=False, lookup=None), Field(name='uncompressed_size', convert=Whole(lo=0, hi=9007199254740991), required=True, default=None, nullable=False, lookup=None)), reserved=mappingproxy({}), wire=False)), max_items=64)` |

### grid

| Field | Required | Null | Read by |
|---|---|---|---|
| `name` | yes | no | `Identity(max_chars=64)` |
| `required` | yes | no | `Flag()` |
| `shape` | yes | no | `Wholes(n=3, lo=1, hi=65535)` |
| `cell_size_um` | yes | no | `Whole(lo=1, hi=9007199254740991)` |
| `origin_um` | yes | no | `Wholes(n=3, lo=-9007199254740991, hi=9007199254740991)` |

### table

| Field | Required | Null | Read by |
|---|---|---|---|
| `name` | yes | no | `Identity(max_chars=64)` |
| `required` | yes | no | `Flag()` |
| `rows` | yes | no | `Whole(lo=0, hi=9007199254740991)` |

### array

| Field | Required | Null | Read by |
|---|---|---|---|
| `channel` | yes | no | `Nested(schema=Schema(fields=(Field(name='name', convert=Identity(max_chars=64), required=True, default=None, nullable=False, lookup=None), Field(name='unit', convert=Identity(max_chars=64), required=True, default=None, nullable=False, lookup=None), Field(name='dtype', convert=Choice(words=('u8', 'u16', 'u32', 'f16', 'f32')), required=True, default=None, nullable=False, lookup=None), Field(name='encoding', convert=Choice(words=('raw', 'linear')), required=True, default=None, nullable=False, lookup=None), Field(name='required', convert=Flag(), required=True, default=None, nullable=False, lookup=None), Field(name='scale', convert=Wholes(n=2, lo=-9007199254740991, hi=9007199254740991), required=True, default=None, nullable=False, lookup=None), Field(name='offset', convert=Wholes(n=2, lo=-9007199254740991, hi=9007199254740991), required=True, default=None, nullable=False, lookup=None)), reserved=mappingproxy({}), wire=False))` |
| `of` | yes | no | `Identity(max_chars=64)` |
| `offset` | yes | no | `Whole(lo=0, hi=9007199254740991)` |
| `size` | yes | no | `Whole(lo=0, hi=9007199254740991)` |
| `uncompressed_size` | yes | no | `Whole(lo=0, hi=9007199254740991)` |

### channel

| Field | Required | Null | Read by |
|---|---|---|---|
| `name` | yes | no | `Identity(max_chars=64)` |
| `unit` | yes | no | `Identity(max_chars=64)` |
| `dtype` | yes | no | `Choice(words=('u8', 'u16', 'u32', 'f16', 'f32'))` |
| `encoding` | yes | no | `Choice(words=('raw', 'linear'))` |
| `required` | yes | no | `Flag()` |
| `scale` | yes | no | `Wholes(n=2, lo=-9007199254740991, hi=9007199254740991)` |
| `offset` | yes | no | `Wholes(n=2, lo=-9007199254740991, hi=9007199254740991)` |

## Channels (protocol v0)

| Channel | Unit | dtype | Encoding | Required | Scale | Offset |
|---|---|---|---|---|---|---|
| `material` | id | u8 | raw | True | 1/1 | 0/1 |
| `region` | id | u16 | raw | True | 1/1 | 0/1 |
| `crack` | ratio | u8 | linear | True | 1/255 | 0/1 |
| `temperature_c` | celsius | f16 | raw | True | 1/1 | 0/1 |

Catalogue hash: `sha256/c14n-1:0bee15dd6a86c74dda0a9d968425853320cb1b7288ae7d7cace188bf3172f3a7`

- **dtypes** (little-endian): `u8`, `u16`, `u32`, `f16`, `f32`
- **encodings:** `raw`, `linear`
- **units:** `id`, `celsius`, `m`, `ratio`
