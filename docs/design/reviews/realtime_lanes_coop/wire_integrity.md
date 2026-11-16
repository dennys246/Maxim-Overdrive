# Wire integrity review: real time, lanes and co-op (design v0)

Reviewer lens: Wire integrity. Design: `docs/design/realtime_lanes_coop.md` at 52e64f0. No code yet, so "after" is
what the design says each producer and consumer becomes. Counts: 3 BLOCKER, 11 SHOULD-FIX, 4 NIT.

## Contract tables

### Wire format (protocol v0): all new

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|
| `hello {seq, protocol: 0, token}` | none → Godot client | none → server session / codec | the version and token. No rule for a mismatched version (error code? what does the server advertise?) |
| `welcome` | none → server | none → client | `session, actor, role, tick_s, physics_period_s, day_length_s, epoch, rig, dx, shape`. **Missing:** region list and affordances (needed to build an `act`), the material table (id → name/colour, needed to draw `material`), current tick/scale/paused, `protocol`, `snapshot_hz`, the order of `shape` |
| `act {seq, region, action, params}` | none → client (later NPC substrate) | none → network-lane validation, then the sim lane → `StructureModulator.execute` | **no reply message exists** for success or for a failure found at apply time (F1) |
| `time {seq, request, scale}` | none → client | none → `TimeAuthority` | → `time_decision` granted/refused/pending; how a pending one later resolves is undefined (F9) |
| `snapshot {seq}` request | none → client | none → host | → a binary snapshot with no `seq`/`in_reply_to`, so it can't be told from an unsolicited one (F5) |
| `tick` | none → host | none → client | `tick, world_time_s, time_of_day_s`, requested/effective scale, `paused`. Throttle rate unspecified. JSON can't carry the "unpaced" scale if it is `inf` (F9) |
| binary snapshot `[u32 LE len][JSON header][arrays]` | none → codec over `world.snapshot()` | none → GDScript `PackedByteArray` → `Image` per z-slice → `ImageTexture3D` | header `protocol, tick, world_time_s, shape, axis_order "zyx"`, per array `name, dtype, offset, stored/uncompressed size, compression`. Unspecified: dtype vocabulary, the base of `offset`, the order of `shape`, what a reader does with an unknown `compression`/dtype/protocol, a message-kind field (F4, F6) |
| `error {code, message, in_reply_to}` | none → server | none → client | there's no list of codes, and no rule for `in_reply_to` when the bad message had no parseable `seq` (F5) |
| `time_decision` `pending` (reserved) | none → (future vote policy) | none → v0 client | a v0 client is not told how to treat it, or which message resolves it (F9) |

### Call, payload and gate contracts on existing code

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|
| `RigProfile.min_substeps_per_turn: int` → `max_substep_s: float` | `data/rigs/{laptop,rig,max}.yaml` (4/16/64) → (1.5/0.375/0.094) | `config.py::RigProfile.__post_init__`, `RigProfile.load`, `world.py::World.advance`, `tests/test_heat.py` (lines 23, 44: **positional** 3rd arg), `tests/test_validation.py` (the rejection row `min_substeps_per_turn: 0`, custom YAML at line 202) | per 6 s of world time: substeps 4/16/64 → **12/24/72** at a 0.5 s period (ceil rounding), not "the same precision", not the same cost (F7). Old YAML → bare `KeyError` (F7) |
| `heat.step(grid, seconds, min_substeps=1, ...)` | — | `World.advance`, `tests/test_heat.py` ×4 | if it becomes `max_substep_s` with a default, the positional `4`/`16` in `test_heat.py` silently mean 4 s / 16 s (F7) |
| `World.advance(seconds=None)` (default `turn_seconds=6.0`) | — | `tests/test_cross_tier.py` ×3, `tests/test_determinism.py::run`, `tests/test_validation.py` (asserts `turn == 1`), README line 35 → plus `WorldHost.tick()` every physics tick | no-arg callers keep getting 6 s, which isn't a world-config value any more. `World.turn` now counts physics steps, not ticks (F3) |
| world time | `grid.time_s += seconds` in `heat.step` → plus `tick × tick_s` in the host | `world.snapshot()["time_s"]`, `bridge.RegionSensor.read().timestamp`, `test_determinism::digest`, `test_snapshot` | three clocks (`grid.time_s`, `World.turn`, host `tick`). `grid.time_s` lags world time by up to 0.5 s between physics steps, and that's what Maxim's `SensorReading.timestamp` carries (F3) |
| `world.snapshot(grid)` keys | `world.py::snapshot` | `tests/test_snapshot.py` → plus the codec, the golden fixtures, the GDScript decoder | `shape` (x,y,z), `cell_size_m`, `time_s`, `material u8`, `crack u8`, `glow u8`, `temperature_c f16`, all numpy C-order (z fastest) → the wire wants z,y,x with x fastest, `dx` in place of `cell_size_m`, and `world_time_s` from the tick, not `time_s` (F4, N1) |
| SEM `structure` vocabulary as `act` | `bridge.py::StructureModulator.affordances` (Python-typed `AffordanceSchema.params`: `float`, `(float, default)`, `(list, None)`) | in-process callers → plus the network-lane JSON validator and the client | `point_m` is in server metres, z up; the client works in Godot metres, Y up (F4). Python types need a JSON schema (bool vs int vs float, list length 3). `execute` validates at apply time and returns `success=False`, which has no route back to the client (F1) |

### Persisted and config contracts (new)

| Contract | Producers | Consumers | Gap |
|---|---|---|---|
| intent log | record lane | the replay test, saves (B4), bug reports | no format, version, header or record schema (F2) |
| world config: `tick_s, physics_period_s, day_length_s, epoch, snapshot_hz` | `data/` YAML (path and loader unnamed) | host, codec (`welcome`), the Maxim clocks, the replay header | floats where the consumers need exact integers; `epoch` has no type; no loader, version or B12 row (F8, F10) |

### Maxim-facing contracts

| Contract | Maxim reads | What a real-time world gives it |
|---|---|---|
| `ExperienceClockDriver` (`runtime/experience_time.py`) | either the wall-clock monotonic "realtime" kind, or the duck-typed `experience_turns() -> int` plus `experience_us_per_turn: int > 0` | it fits **only** as the "turns" kind with tick = turn and `us_per_turn = tick_s` in µs (100,000). Left as "realtime", NPCs would forget by wall time: 30× slower in world time at 30×, and still forgetting while the thinking lane holds the world (F11) |
| `TemporalSignature.from_timestamp(ts)` | a Unix timestamp through `datetime.fromtimestamp` (**local time zone**, DST), fixed 24 h / 7 d / calendar month / year | any `epoch + world_time` fed to it gets phases that depend on the host's time zone, and a weekday/month calendar the design never defines (F10) |
| `SensorReading.timestamp` | Maxim's own sensors stamp `time.time()` (for example `sem.py` `last_fired`) | the bridge stamps `grid.time_s` (seconds since the world started, physics-lagged), so the two time bases mix inside one agent (F3, F11) |

## Findings

**F1. BLOCKER: `act` has no reply, and failures found at apply time have no route back.**
Location: design §5 tables; `sem_env/bridge.py::StructureModulator.execute`.
The design says "every message carries `seq`, and the reply echoes it", but the server-to-client table has no reply
for `act`. `error` covers only refusals at decode. Validation also splits in two. The network lane can't check
`region in world.grid.regions` (it doesn't own `World`, and regions change as imagination places objects), so the
semantic checks run in `execute` on the sim lane at the next tick, which returns `ModulatorResult(success=False,
error=...)`. Scenario: a client sends `extinguish` on a crate that isn't burning, or `strike` on a region another
player destroyed that tick. `execute` returns `success=False, "nothing is burning here"`, nothing reaches the client,
and the client UI shows the action as having happened. A successful `strike` also returns `destroyed_volume_m3` and
`absorbed_j`, which have no route back either.
Fix: add `act_result {in_reply_to, tick_applied, success, error, metadata}`, mirroring `ModulatorResult`, sent at
the tick the act applies. State the rule: every client message gets exactly one terminal reply (`welcome`,
`act_result`, `time_decision`, a snapshot with `in_reply_to`, or `error`). Say whether the log records failed
applications.

**F2. BLOCKER: the intent log is a persisted format with no specification.**
Location: design §2 ("Every result … goes into the intent log"), §4 ("the log records the decision"), §6 (2a ships
"the intent log, with a replay test").
CLAUDE.md: "Every format is versioned … readers refuse versions they don't know". It also calls the log the save
format's backbone. The design names what goes into the log but no version, header or record schema. A replay needs
more than "scene and rig" now: the world config (`tick_s`, `physics_period_s`, `epoch`, `day_length_s`), the
protocol version of the recorded intents, and session joins and actor assignment (§4: actors act through avatars,
and creating one changes the world). Scenario: 2a ships a log without a header. 2b adds `thought_result` records and
world config. A 2a log then replays under a 2b world config with a different `physics_period_s`, and it diverges
silently instead of being refused.
Fix: specify `intent_log v0` in the design. The header holds `format`, `version`, a scene id plus content hash, the
rig name plus hash, the whole world config and the protocol version. Records are `{tick, actor, seq, kind, payload}`,
with kinds `act`, `time_decision`, `session_join`/`session_leave` (with the actor assigned), `thought_result` and
`thought_failed`. Add a golden log fixture (B2/B3) and a reader that refuses an unknown version.

**F3. BLOCKER: time ownership splits across three clocks, against the standing rule.**
Location: design §1 and §5 ("The host's clock moves time"); `world.py::World.advance`, `World.turn`,
`World.turn_seconds`; `grid.py::MaterialGrid.time_s`; `bridge.py::RegionSensor.read`; CLAUDE.md and
architecture.md ("only `World.advance` moves time").
After the change, world time is `tick × tick_s`, owned by `WorldHost`. `World.advance` runs only on physics ticks.
`World.turn` counts physics steps, and `grid.time_s` jumps in 0.5 s steps. Scenario: at tick 7 (world time 0.7 s),
an NPC's `RegionSensor.read().timestamp` is 0.5. The snapshot header says `world_time_s = 0.7`, while `snapshot()`
still emits `time_s = 0.5`. A save of `World` alone loses the tick, because the tick lives in the host. No-arg
`World.advance()` callers (three cross-tier tests, `test_determinism::run`, `test_validation`, README) still step
6 s, a value that no longer exists in world config. The rule "only `World.advance` moves time" is false on non-physics
ticks.
Fix: move the tick into `World`. Add `World.tick()` (no duration argument), which increments `World.tick_count` and
calls the private physics step on period boundaries. `World` holds the world config. Time derives from the tick
(`grid.time_s` becomes derived, or is kept equal at physics ticks and documented as physics time). Remove
`turn_seconds`, the `seconds=None` default and `turn`. `WorldHost` only paces calls to `World.tick()`. Rewrite the
rule as "only `World.tick` moves time" in CLAUDE.md, architecture.md and the bridge docstrings. Set
`SensorReading.timestamp` to world time.

**F4. SHOULD-FIX: axis order is right for the bytes but doesn't fix `shape` or the coordinate frame.**
Location: design §5 ("Axis order is Godot's"); `world.py::snapshot`; `grid.py` (cell `(i,j,k)`, z up).
The bytes are right. Internal arrays are numpy C-order `(nx, ny, nz)`, so z varies fastest. Sending
`a.transpose(2,1,0)` made contiguous (or `a.tobytes(order="F")`) gives x fastest, then y, then z. That matches
`ImageTexture3D.create(format, width=nx, height=ny, depth=nz, …, [Image per z-slice])`, where each `Image` is
row-major with x fastest. Internal consumers (heat, damage, SEM) are unaffected, and the transpose belongs only in
the codec. Two things are left open:
(a) `shape` in `welcome` and in the header has no stated order: `[nx,ny,nz]` (the current `snapshot()["shape"]`) or
`[nz,ny,nx]` (matching `axis_order`). Scenario: the client reads `[nx,ny,nz]` as `[nz,ny,nx]`. On a cubic test scene
nothing looks wrong. On a 16×10×4 m tile the slices are the wrong size, or the image is garbled.
(b) The server is z-up and Godot is Y-up. The texture's depth axis is server z, which is Godot's +Y, and server +y
maps to Godot −Z. "The client never transposes" holds for bytes, but the shader must still swizzle UVW, and nothing
fixes the mapping. `act.params.point_m` has the same frame question.
Fix: send `shape` as named dims `{"x": nx, "y": ny, "z": nz}`, or state `[nz, ny, nx]` explicitly. Define
`axis_order` as "slowest to fastest". Write down the server-to-Godot frame mapping, and say that `point_m` is in
server metres. Make the golden fixture asymmetric (nx ≠ ny ≠ nz, with one marker cell at a known corner) so that a
swapped axis or a flipped sign fails the Python test and the GDScript test.

**F5. SHOULD-FIX: `seq` semantics are incomplete.**
Location: design §5.
The design doesn't say: the type or range of `seq` (Godot's `JSON` parses numbers as float, so values above 2^53
lose precision); whether it is per session and strictly increasing (ordering uses `(tick, actor, seq)`, so two intents
from one actor in one tick with equal or reused `seq` tie, and order then falls back to arrival or queue order, which
the design rules out); what `in_reply_to` holds when the bad message had no parseable `seq` (malformed JSON);
whether server messages carry their own `seq`; and how a requested snapshot is correlated (the binary header has no
`in_reply_to`).
Fix: `seq` is an integer in [0, 2^31), strictly increasing per session, and the server refuses a non-increasing one
with `error` code `bad_seq`. `in_reply_to` is null when there was no seq. The binary header gets `in_reply_to` (null
when unsolicited). Server messages carry no `seq`.

**F6. SHOULD-FIX: the binary header leaves dtype names, `offset` base, unknown values and the message kind unspecified.**
Location: design §5 snapshot row; `world.py::snapshot` (`np.float16` is native byte order).
- dtype: "float16" or `<f2` or `RH`? GDScript needs a closed vocabulary that maps to `decode_*` calls and `Image`
  formats. Fix: the dtypes are `u8` (→ `Image.FORMAT_R8`) and `f16` little-endian (→ `FORMAT_RH`), and the encoder
  calls `.astype("<f2")` explicitly rather than relying on native order.
- `offset`: from the start of the message, the end of the header, or the array block? Fix: bytes from the first
  byte after the header, with no padding.
- Unknown values: the design reserves `compression` but never says that a v0 reader **refuses** anything other than
  `none`, or what it does with an unknown dtype, an unknown array name or an unknown `protocol`. Scenario: a server
  turns on zstd and an older client decodes the compressed bytes as raw cells. Fix: state that the reader refuses
  any `protocol`, `compression` or `dtype` it doesn't know, ignores unknown array names, and refuses a missing
  required array.
- Message kind: delta snapshots are promised for step 3, but the header has no `kind` field. Fix: add
  `kind: "snapshot_full"` now, so a v0 reader refuses a `snapshot_delta` instead of misreading it.
- JSON encoding: say the header is UTF-8 and that the `u32` length counts bytes.

**F7. SHOULD-FIX: `max_substep_s` doesn't keep today's precision or cost, and its readers break silently.**
Location: design §1; `data/rigs/*.yaml`; `config.py::RigProfile`; `heat.py::step`; `tests/test_heat.py`;
`tests/test_validation.py`.
- `n = ceil(seconds / max_substep_s)` per advance. At `physics_period_s = 0.5`, that's 1, 2 and 6 substeps per
  advance, so **12, 24 and 72 per 6 s against today's 4, 16 and 64**. Cost goes up 3×, 1.5× and 1.125×, and dt
  changes. That contradicts "the same precision as today" and the claim that cost per world second doesn't depend on
  `physics_period_s`, and it changes the §1 cost table. 0.094 isn't 6/64 either.
- `heat.step` is called positionally in `test_heat.py` (`heat.step(g, T_S, rig.min_substeps_per_turn)`). If the
  parameter becomes `max_substep_s: float = <default>`, a leftover positional `4` reads as 4 seconds with no error.
- An old rig YAML (`min_substeps_per_turn`) fails in `RigProfile.load` with a bare `KeyError`, and rig files carry
  no version.
Fix: require `physics_period_s / max_substep_s` to be an integer, validated at load (for example 0.5, 0.25 and
0.0625 s, giving 1, 2 and 8 per period), or express the rig field as substeps per physics period, an int. Make the
`heat.step` parameter required and keyword-only. Have the loader refuse unknown or legacy keys with a message that
names the rename. Update the validation row, the custom-rig test YAML and the cost table.

**F8. SHOULD-FIX: world-config time values are floats where their consumers need exact integers.**
Location: design §1; config file path and loader unnamed.
`tick_s = 0.1` isn't representable in binary: `0.1*3 = 0.30000000000000004`, `0.3/0.1 = 2.9999999999999996`.
"`physics_period_s` is a multiple of `tick_s`" then becomes a float test that passes or fails by accident.
`world_time_s = tick × tick_s` and `time_of_day_s` come out slightly wrong, and Maxim's `experience_us_per_turn` must
be an `int` (F11).
Fix: store `tick_us: 100000` (int), `physics_every_ticks: 5` (int), `day_length_ticks` or `day_length_us`, and
`epoch_us`, and derive the seconds for display only. Name the file (for example `data/world/default.yaml`), version
it, give it a loader with every rejection tested (B12), and put it in the replay header (F2).

**F9. SHOULD-FIX: the time-control state machine and its wire values are underspecified.**
Location: design §1 "The dial", §4, §5 `time` and `tick`.
- `pause` and `set_scale 0` are two ways to pause. Does `resume` restore the last non-zero scale? What does `tick`
  report as "requested scale" while paused?
- Unpaced (headless) has no wire value. Python's `json.dumps(float("inf"))` emits `Infinity`, which isn't JSON, and
  Godot's parser rejects it. Effective scale while paused is 0/0.
- `pending` is "reserved", but the design never says how a pending request resolves: a second `time_decision` with
  the same `in_reply_to`? Without that, a vote needs a protocol change after all, against the §4 claim.
- Allowed `scale` range and the error codes for it aren't given.
Fix: state the states (`paused`, `paced(scale)`, `unpaced`) and how each `request` moves between them. Report
`requested_scale: number | null` (null meaning unpaced) and `effective_scale: number`, with 0 when paused. Encode with
`allow_nan=False`. Define the pending flow now (a later `time_decision` with the same `in_reply_to`), and say that a
v0 client shows pending as unresolved.

**F10. SHOULD-FIX: `epoch` has no type, and Maxim's calendar clock depends on the host's time zone.**
Location: design §1 "The day", §3; Maxim `time/temporal_signature.py::TemporalSignature.from_timestamp`.
`(epoch + tick × tick_s) mod day_length_s` assumes `epoch` is seconds whose zero is a midnight. The text calls it
"the world's date and time", but no calendar is defined. `TemporalSignature` also needs a weekday, a day of month and
a day of year. `from_timestamp` uses `datetime.fromtimestamp`, which is local time with DST, so feeding it
`epoch + world_time` gives circadian phases that differ between two machines in different time zones, and that jump
at DST. Scenario: the owner's machine and CI disagree on an NPC's circadian bin for the same tick.
Fix: define `epoch_us` as microseconds since a world-calendar origin (day 0 at 00:00, no time zone, no DST), with
the week, month and year derived from `day_length` by stated rules. Add to Phase 3 item 10 that the injected clock
must report phases with no time zone, and that the game never calls `from_timestamp` with a world time.

**F11. SHOULD-FIX: the experience clock fits only through the "turns" duck type, and the design should say so.**
Location: design §3 table, row `ExperienceClock`; Maxim `runtime/experience_time.py::ExperienceClockDriver`.
A real-time world gets the driver's "realtime" kind by default, which reads `time.monotonic` minus the controller's
paused time. With the dial at 30×, an NPC would accrue experience 30× slower than the world. While the sim lane holds
for a thought, or while the host pauses without Maxim's autonomy controller knowing, the NPC still forgets. The fit
is the "turns" kind: the NPC's percept source exposes `experience_turns() -> int` returning the world tick, and
`experience_us_per_turn = tick_us`, an int (F8). `CompositeSource` exposes it only when exactly one child is
turn-based, so the world's source must be that one child. Two more points. The driver reads the tick from the
agent's loop thread, so how experience is chunked between passes depends on scheduling (the total is exact), which
the determinism lens should weigh until Phase 4 steps the substrate from the sim lane. And `SensorReading.timestamp`
(world time, F3) sits next to Maxim's own `time.time()` stamps in the same agent.
Fix: name the duck type, the tick-as-turn mapping and `tick_us` in §3, and list the mixed timestamp bases under
Phase 3.

**F12. SHOULD-FIX: `welcome` lacks what the client needs to act and to draw.**
Location: design §5 `welcome`.
Missing: the region names with their affordances and param schemas (the client can't fill in `act.region` without
them), the material table (id → name and `color_rgb`, needed to colour the `material` channel; today it exists only
server-side in `data/materials/core.yaml`), current `tick`, scale and paused for a guest who joins mid-run,
`protocol`, `snapshot_hz`, and the order of `shape` (F4). Regions change at run time (imagination), so they need an
update message as well, or a field in the snapshot header.
Fix: add `materials: [{id, name, color_rgb}]`, `regions: [{name, affordances}]` and current time state to `welcome`,
plus a `regions` message on change, or a `regions_version` in the snapshot header.

**F13. SHOULD-FIX: session lifecycle and actor identity aren't specified.**
Location: design §4.
`actor` and `session` have no type (int or string). Ordering by actor id needs one, and string order isn't integer
order. Unanswered: what happens when the host disconnects (the world is stuck at its scale, nobody can pause, or a
guest is promoted?), whether a reconnecting guest keeps its actor, and whether joins and leaves reach the log (F2).
Fix: `actor` is an integer assigned in join order and never reused within a run. State the host-departure rule (v0:
the world pauses and `role: host` can be claimed only by the launch token), and log `session_join` and
`session_leave`.

**F14. SHOULD-FIX: the transport claims are stale for real time.**
Location: `docs/architecture.md` "Transport" ("Head-of-line blocking … harmless for a turn-based game", buffer caps);
`docs/standards_backlog.md` B2 ("with its turn"); CLAUDE.md ("only `World.advance` moves time"); README line 35.
At 2 Hz, a 3.2 MB (rig) or 26 MB (max) snapshot sits ahead of every `tick`, `act_result` and `time_decision` on the
same TCP stream, so pausing lags by a snapshot's transfer time. Godot's `inbound_buffer_size` (64 KiB default) must
hold a whole 26 MB message, and `max_queued_packets` must cover the backlog at 2 Hz.
Fix: update these claims in the same change that accepts the design. Name the client buffer settings, or send
`max_message_bytes` in `welcome`.

**N1. NIT:** `snapshot()["cell_size_m"]` vs `welcome.dx`, and `time_s` vs `world_time_s`. Pick one name for each
(`cell_size_m` matches the metres convention) and use it in `snapshot()`, the header and `welcome`.

**N2. NIT:** the "immutable" published snapshot holds writable numpy arrays. Set `flags.writeable = False` on the
copies before they cross a lane.

**N3. NIT:** list the `error.code` vocabulary (`bad_protocol`, `bad_token`, `origin_refused`, `malformed`,
`too_large`, `bad_seq`, `unknown_region`, `unknown_action`, `bad_params`, `not_permitted`) so that the golden
fixtures and GDScript can match on it.

**N4. NIT:** state the policy for unknown JSON keys: the server refuses them on client messages, and the client
ignores them on server messages within one protocol version.

## Checked and found consistent

- Little-endian `u32` length plus JSON header plus array bytes decodes cleanly with `PackedByteArray.decode_u32`,
  `get_string_from_utf8` on a slice, and `decode_half` for `f16`. `FORMAT_R8` and `FORMAT_RH` exist for the four
  current channels, and per-z-slice `Image.create_from_data(nx, ny, false, fmt, slice)` fits x-fastest bytes with no
  client transpose.
- Converting numpy C-order `(x,y,z)` to the wire's z,y,x with x fastest is one transpose in the codec. Heat, damage,
  the SEM sensors and `imagination.spec` keep `(x,y,z)` unchanged.
- The design keeps `advance` out of the client vocabulary, so no wall-clock duration reaches `World` (B14).
- `act` reuses the bridge's three affordance names unchanged, so the SEM vocabulary isn't forked. The `_compat`
  mirror and `test_sem_compat.py` are untouched.
- The tick status reports the effective scale, and the world never steps a longer `tick_s` to catch up, so the dial
  doesn't reach physics.
- `snapshot()` dtypes (`u8` ×3, `f16`) match the 5 bytes per cell in architecture.md's size figures, and the 6.4
  and 52 MB/s figures follow from 3.2 and 26 MB at 2 Hz.
- With a tick count as the turns and an integer µs quantum, `ExperienceClockDriver`'s turns contract can be met, and
  a paused or held world then produces no experience, as §3 intends.
- The `hello` token travels in the message, not the URL, which agrees with architecture.md.
