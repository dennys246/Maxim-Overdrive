# Tile and client spec, v1: Wire integrity and Trust boundary

Target: `docs/design/tile_and_client.md` at f6afd66, read against `world_model.md` §8, `boundaries.md` §5.3–§6.2 and
§9.1, architecture.md (Transport), `origin/phase1/realtime-design`'s `realtime_lanes_coop.md` §2–§7 and TB-7, and
`origin/phase1/act-validation`'s `bridge.py`, `actions.yaml` and `scene.py`.

## Contracts the design touches

| Contract | Producers before → after | Consumers before → after | What each consumer gets, before → after |
|---|---|---|---|
| `act` / `ignite` params | client, NPC tool call, LLM → same, plus `point_m`, `duration_s` | `parse_action`, `StructureModulator.affordances` (advertised to Maxim), log `params` | `{power_w, radius_m}` → `{point_m, power_w, duration_s}`; `radius_m` fate unstated; no vocabulary version |
| `move`, `move_to`, `move_result` | none → client | none → network lane, stage 1, applier, log | new kinds; no final reply for `move`; no `seq`; ordering key cited is superseded |
| `time` | client (host) | `TimeAuthority` | unchanged shape; presets vs free dial unclear |
| `tick` message | server → server, plus actors | client | gains an actor list (schema change to v0) |
| snapshot frame | server | Godot decoder, golden `.bin` frames | adds `fire` (scale in header), an actor table; no region channel; `crack`/`glow` scales hard-coded |
| `welcome` | server | client | must now also carry region geometry or a region channel (see WT-B4); `role` used to hide HUD |
| scene YAML | author | `Scene.from_dict` (v0 only), save embed (step 9) | v0 → v1 with `spawns`; collides with world_model F13's v1 |
| `data/world/player.yaml`, reach, rate limits | none → author | stage 1, stage 2 | new world-affecting data; not in the log header list |
| refusal codes | `ActionRefused` free text → five named codes | client HUD, tests | codes not produced by any existing code path |
| intent log / scenario | host → hand-written `tests/scenarios/alley_exit.log` | replay reader (strict, header-matching) | a committed log the strict reader would refuse |
| transport caps | architecture.md "raise both ends" | Godot `inbound_buffer_size`, server `max_size` | client 4 MiB; server inbound unstated |

## BLOCKERS

### WT-B1 BLOCKER: `move` and `move_to` fork protocol v0 and the log record instead of joining them

`tile_and_client.md::§4.1, §4.2, §4.5`

- realtime §7: "Every client message gets exactly one final reply" (W-F1). §4.1 sends `move {heading}` with no reply
  of any kind. A client that sends `move {heading: 9}` gets either nothing (it cannot tell refusal from success) or a
  reply the spec never names. Its rate refusal (> 30/s) has no reply kind either.
- §4.2 invents `move_result {tick_applied, success, error, path_mm}` beside `act_result`, while boundaries §7.2 makes
  every intent's answer one receipt keyed `(actor_id, seq)`. Later path events (`path_blocked`, arrival, the one
  replan) are described as outcomes of the same `move_to` but have no message kind: a second "final" reply, or none.
- §4.5 logs "`(tick, host_seq)` (realtime §4.2)". boundaries §6.2 explicitly supersedes that with one ordering key
  `(apply_tick, kind_rank, apply_us, actor_id, seq)` and a record carrying `schema_version`, `seq`, `observed_tick`,
  `issued_tick`, typed canonical `params`. The tile's messages carry no `seq`; `move`/`move_to` have no `kind_rank`
  and no row in boundaries §6.1's authority table (Phase 4 NPCs will need to walk through the same door).
- Failure: step 7 builds `move` with no reply and arrival-order `host_seq`; step 5's log uses the boundaries key; the
  §4.5 replay test is written against one, the log against the other, and same-tick `move` + `act` order differs
  between live and replay.

**Fix.** Define `move` and `move_to` as intent kinds in `engine.intents` with the boundaries §6.2 record (seq,
observed_tick stamped by the host, typed canonical params), a `kind_rank`, and an authority row ("any actor"). Each
gets exactly one final reply: the standard receipt (`act_result`-shaped, or rename the receipt to `intent_result`
for all kinds), with `path_mm` as receipt metadata for `move_to`. Asynchronous path events go in the actor's entry in
`tick` (a `path_state` enum), never as replies. Cite boundaries §6.2, not realtime §4.2.

### WT-B2 BLOCKER: the ignite redesign changes the shared action vocabulary with no version, no Maxim-facing schema and no code source

`tile_and_client.md::§2.3`, `§4.3`

- `parse_action` is the one gate for clients, NPC tool calls and LLM output (realtime §7, boundaries §5.3).
  `_ALLOWED_PARAMS["ignite"]` is `{power_w, radius_m}` and refuses unknown keys. The tile's
  `{point_m, power_w, duration_s}` does not say whether `radius_m` is dropped, kept or defaulted, nor whether
  `point_m` is required (strike's is optional, defaulting to the centroid the tile is trying to remove).
- `StructureModulator.affordances()` advertises `ignite` to Maxim as "burns until extinguished" with `radius_m`. The
  tile changes the meaning (a bounded pilot, not a fire) under the same name. world_model §8 F1: "A new meaning gets a
  new name." An NPC with a learned affordance for `ignite` gets a different act with no signal.
- No vocabulary version bump is named (world_model §8 logs it). A v0 log's `ignite {power_w: 1e5, radius_m: 0.3}` is
  either refused on the new build or applied as a different act.
- The five refusal codes don't exist: `ActionRefused` carries only free text (`"power_w must be between ..."`), and
  boundaries §5.4 requires a closed code vocabulary. `out_of_reach` needs the acting actor's position, which
  `StructureModulator.apply(action)` has no parameter for.
- "Validated as `strike`'s is" is false: `_on_region` accepts any point inside the footprint grown by `sigma_m`
  (≥ 0.2 m), interior included; the tile wants "within 0.1 m of its surface".

**Fix.** Either name the new act (`kindle`, a pilot) and keep or retire `ignite` explicitly (as world_model §8 did
for `extinguish` → `douse`), or bump the action vocabulary to v1 with `point_m` required, `radius_m`'s fate stated,
and a v0-log migration or refusal test. Give `ActionRefused` a `code` from a closed enum, defined in
`engine.intents`. Move reach into the stage-2 applier with the actor id from the record. Write the surface rule as its
own predicate on authored footprints (metres) with its own tests. Update the `AffordanceSchema` description in the
same PR.

### WT-B3 BLOCKER: the decoder hard-codes `glow` and `crack` scales, which world_model §8 forbids

`tile_and_client.md::§5.1`, `§6.3`

world_model §8 frame rules: "Fixtures include a non-default linear scale, so a decoder that hard-codes 1/255 fails."
The tile puts a linear scale in the header for `fire` only; for `glow` the shader inverts
`T = 525 + 975·g/255`, and §6.3 itself says 525 °C is *from memory, to verify* before material table v1. Failure:
step 6 corrects `GLOW_START_C` to, say, 480 °C; the server's `snapshot()` changes; every frame still decodes, the
shader paints 525 °C where the world is 480 °C, and no version bump or fixture catches it, because the scale was never
part of the format. That is exactly the "name is an identity" failure F1 exists to stop.

**Fix.** Every quantized channel carries `scale`, `offset` and `unit` in its header entry (`glow`: offset 525,
scale 975/255, unit `degC`; `crack`: scale 1/255, unit `1`), from the closed unit vocabulary world_model §8 names.
The shader takes them as uniforms. The wire fixtures include a non-default scale for `glow` and `crack`, and the
Godot decoder test fails if they are ignored.

### WT-B4 BLOCKER: the client cannot turn a pick into a region, so "F on a region" has no input

`tile_and_client.md::§4.2`, `§4.3`, `§6.1`, `§8.4`

The act message needs `region`. The client's pick runs a DDA "through the material bytes it holds", but material is
an id per cell (`wood`), not a region: `crate` and `crate_control` are both wood. `welcome` (realtime §7) carries "the
region list with each region's affordances", no geometry. The §8.4 ID pass "renders region ids as flat colours"
from the same missing data. Failure: the client guesses the region, or step 8 adds an ad-hoc channel after step 7
froze the frame.

**Fix.** Choose now: a `region` channel (u16 key into `welcome`'s region list), or authored footprints in metres in
`welcome`; either goes in step 7's fixtures. Or drop `region` from the client's `act` and let stage 2 resolve it from
`point_m` with the existing ownership rule, so the client decides nothing.

## SHOULD-FIX

### WT-S1: the refusal vocabulary is incomplete, unstaged, and one code collides

`tile_and_client.md::§2.3`, `§4.1–§4.3`, `§7.2`

Named: `out_of_reach`, `not_on_region`, `limit`, `not_finite`, `busy`, `no_path`, `unreachable`, `path_blocked`.
Missing: rate-limited (ignite ≤ 1/s, move ≤ 30/s), bad heading type/range, `move_to` target outside the extent,
region gone (today's "the crate is gone"), unknown region, unknown param, missing `point_m`, `duration_s` out of
range, time refused for role. `busy` already means "inbound queue full" (realtime §4.1); the tile reuses it for "one
live pilot per actor". `not_finite` is unreachable through the socket: the strict decoder (boundaries §9.1,
`parse_constant` raises) refuses NaN and `1e400` before `parse_action`, so §7.2's "NaN (`not_finite`)" variant asserts
an `act_result` that can never be sent.
**Fix.** One table: code, stage (decode / stage 1 / stage 2), reply kind, logged or not, test name. Rename the
pilot code (`pilot_live`). The NaN variant asserts the decoder's `error` code with a golden rejection frame.

### WT-S2: the exit scenario as a committed intent log conflicts with the log's own strictness

`tile_and_client.md::§7.2`

The v0 log header holds the code SHA, pymaxim, numpy and platform, and the reader "refuses a header it doesn't
match" (realtime §7); logged intents are re-validated at load and loading is all-or-nothing (world_model F14). A
hand-written `alley_exit.log` committed today is refused after the next commit. The refusal variants (`limit`,
`not_finite`) can't be log records at all, since stage-1 refusals never enter the log, so the loader would refuse the
whole file.
**Fix.** Split: a versioned scenario *script* (inputs at ticks, fed through the socket and through unpaced
`Simulation.step`) that produces a log; the replay test replays the produced log. State which header fields are
matched (content hashes) versus recorded (SHA, platform). Stage-1 variants are socket tests; stage-2 variants
(`out_of_reach`, `not_on_region`, `pilot_live`) may be log records, since boundaries §6.2 logs refused intents.

### WT-S3: new world-affecting data is not in the log header

`tile_and_client.md::§2.1`, `§2.2`, `§2.3`, `§4.2`

`data/world/player.yaml` (speed, radius, pilot limits), the heading table ("the table is data"), reach (1.5 m, file
unnamed) and the A\* limits change what a replay computes, but neither world_model §8's nor boundaries §6.3's header
list includes them. Failure: someone edits `player.yaml` speed to 1.5 m/s; the committed log replays without
complaint and the body arrives at a different cell, so tick 70's ignite becomes `out_of_reach`. Separately,
"≤ 1 ignite per second per session (`data/server/`)": if that check is wall-clock in the network lane it is fine
(pre-log); if it's in ticks it changes the world and belongs in `data/world/`.
**Fix.** List every new file in the header's content hashes; put reach and pilot limits in `player.yaml`; state that
rate limits are wall-clock, stage 1, never logged.

### WT-S4: `move_to` has no rate limit and an unbudgeted cost in the simulation lane

`tile_and_client.md::§4.2`, `§10`

`move_to` has no rate limit, and each runs up to 10,000 A\* expansions at apply: tens of milliseconds in Python
(*estimate*), against §10's 0.5 ms per tick. 100 `move_to`/s dilates the world, which TB-10 forbids. A burning crate also bumps `topology_version` at every physics step, so the
"replan once" path runs repeatedly.
**Fix.** A `move_to` rate limit and a per-tick planning budget (latest-wins per actor: a newer `move_to` before apply
replaces the queued one), with a test; reconcile §10's budget with the 10,000-expansion cap.

### WT-S5: a stop can be dropped while paused, so the body walks on resume

`tile_and_client.md::§4.1`

While paused, records wait for the next tick on a bounded per-session queue; full means a `busy` refusal (realtime
§4.1). A held-and-released key, or camera rotation with a key held (which changes the world heading on every Q/E),
queues `move` records. If the queue fills, the final `move {heading: null}` is refused while an earlier `move
{heading: 2}` was accepted. On resume the body walks north forever until another key press. "Press-and-release nets to
nothing" holds only when nothing is dropped.
**Fix.** Held heading is latest-wins per session at the network lane (one slot, not a queue entry), so a stop is
never refused; or the client resends its current heading after any `busy`. Test: fill the queue while paused, release,
resume, assert the body is still.

### WT-S6: no frame reaches a client that joins a quiet world

`tile_and_client.md::§5.2`, `§5.3`, `§9.4`

Textures are "made on `welcome`" from bytes the client doesn't have yet; frames publish only on change (O23). A host
that connects to an unlit, unpaused alley gets no cells until something changes, and nothing changes. realtime v0 has
a `snapshot` request for this; the tile never sends it, which leaves that message a capability with no caller.
**Fix.** The client sends `snapshot` after `welcome` (and after any reconnect), with the reply's `in_reply_to`
checked; a test joins a static world and asserts a first frame.

### WT-S7: the actor table and the `tick` actor list are undefined, and one breaks world_model's table rules

`tile_and_client.md::§2.1`, `§5.3`

world_model §8 tables are column-major with an integer key and no strings; the actor table's variable-length `path`
can't be a column. Actors appear in `tick` (≤ 30 Hz) and the frame (≤ 2 Hz) at different ticks; which one the client
interpolates is unstated. Both edit v0 schemas that boundaries §9.1's one registry owns.
**Fix.** Specify columns (`actor_id` u32 key, `pos_mm` 3×i32, `heading` i8, `path_state` u8), keep `path` in the
`move_to` receipt only, name `tick`'s actor fields with dtypes, say the client draws from `tick`, and land both in the
field registry, not in this doc.

### WT-S8: scene `spawns` claims "scene format v1", which world_model F13 already owns

`tile_and_client.md::§1.3`

world_model F13 defines scene v1 as the strict loader (step 3b); the tile defines v1 as "v0 plus `spawns`" (step 8).
Two v1s. The v0 migration's `spawns` value isn't given (F12: a literal, `null` or a registered function); an empty
list means every `join` on a v0 scene fails. Required or optional is unstated. "On free floor" must be decided on
authored primitives in metres, not cells, or a spawn is valid at one grid and refused at another. Save v0 embeds the
new field.
**Fix.** One scene-v1 definition (F13 plus required `spawns`) owned by one step; the v0 migration is a registered
function that refuses (no implicit spawn) or adds a named default; spawn validation in metres, with a body-clearance
check (radius 0.25 m) and rejection tests; golden v0 and v1 fixtures.

### WT-S9: the guest refusal tests have no guest on the shipped path

`tile_and_client.md::§4.3`, `§7.2`

Step 7 ships "the guest-join red gate" (plan §2) and co-op is Phase 5+ (O28). A guest can't join in Phase 1, so "`time`
from a guest token (refused)" exercises the join refusal, not `TimeAuthority`. `HostOnly`'s guest branch is
capability with no caller.
**Fix.** Test `HostOnly` directly against a frozen sessions view with a guest role, and assert the guest join is
refused at the socket; drop the socket-level guest `time` variant until guests exist.

### WT-S10: the pilot's lifetime and identity aren't integers or per-actor

`tile_and_client.md::§2.3`

`duration_s` is a float; the end tick (`apply_tick + duration_s / 0.1`) needs a stated integer rule (wire it as
`duration_ticks`, or ms with a floor), or two builds round differently. Today's source key is `fire:{region}`: a second
ignite on the same region overwrites silently, whereas the tile says "one live pilot per actor". The pilot's expiry is
a source removal at a tick, which needs a test that replay removes it at the same tick.
**Fix.** Integer duration on the wire; key pilots `pilot:{actor_id}`; refusal per actor; an expiry replay test.

### WT-S11: integers on the wire from GDScript aren't pinned

`tile_and_client.md::§4.1`, `§4.2`

`heading` and `target_mm` are integers. GDScript computes positions as `float`; `JSON.stringify(5500.0)` emits a
decimal (*to verify* in 4.7.2), which Python reads as `float`. Python also reads `true` as an `int` subclass. Nothing
says whether `5500.0`, `true` or `1e3` are refused.
**Fix.** Stage 1 requires `type(v) is int` (bool refused); the client casts with `int()` before sending; golden
rejection frames for `heading: true`, `heading: 1.0`, `heading: 8`, `target_mm: [5500.0, 2900]`, a three-element
target, and a target outside the extent.

### WT-S12: transport caps are half-specified

`tile_and_client.md::§5.2`, `§9.4`, corrections list

The server's inbound `max_size` (about 64 KiB, TB-7) isn't restated, and the corrections list omits
`architecture.md`'s "both ends must raise their default caps", which TB-7 called a BLOCKER. Godot's
`inbound_buffer_size` is set before `connect_to_url`, so it can't follow `welcome`'s shape; the 16×10×4 m tile at
0.1 m is 3.2 MB before `fire` and region data, near 4 MiB, unchecked. "Fails the session loudly" names no mechanism.
`max_queued_packets` has no number.
**Fix.** Server inbound `max_size` 64 KiB, tested with a 1009 close; the server refuses at join a shape whose frame
exceeds a `data/server/` client cap, with a test; add the architecture.md line to the corrections; number the queue.

### WT-S13: the frame header list misses the catalogue hash, and the size gate is "exact" for a moving target

`tile_and_client.md::§9.4`, `§10`

world_model §8: "a frame whose catalogue hash differs from `welcome`'s is refused". §9.4's client checks list shape and
offsets, not the hash. §10 gates frame bytes at exactly 1,154,048, but the same doc adds `fire` (230,400 B), a region
channel (WT-B4) and an actor table.
**Fix.** Add the hash check and its rejection fixture; express the size gate as Σ(channel bytes) + header ≤ cap,
derived from the registry.

## NITs

- **WT-N1** `§2.3`, `§4.2`: `move_to` uses integer mm and `ignite` float metres. Fine, but say why, and state reach
  is computed in mm against `point_m` rounded once at stage 1 into the canonical params.
- **WT-N2** `§4.3`: presets 0.25–20 read as server validation; realtime decision 8 keeps the dial free in
  `[min_scale, max_scale]`. Say the presets are client UI and the server checks the range.
- **WT-N3** `§7.2` tick 0: "join host → actor 1 at (600, 2000, 400) mm" reads as if the join record carries a position;
  it must be derived from the scene's spawn, never logged as input. `0.6 × 1000` also needs the integer conversion
  F13 uses.
- **WT-N4** `§5.3`, `§4.4`: at 20× a 30 Hz `tick` throttle skips ticks; say "one received sample behind".
- **WT-N5** `§2.3`: `engine.intents.parse_action` exists only after step 3a/3b; today it is
  `sem_env.bridge.parse_action`. Name the dependency.
- **WT-N6** `§8.1`: `client/tests/goldens/frames/*.bin` are wire-format files, so they are B3 fixtures: they carry the
  protocol version, and old ones stay committed or are bumped deliberately.
- **WT-N7** `§5.1`, `§13`: steps 6 (`fire`) and 7 (v0 freeze) aren't ordered; say whether `fire` is in v0's fixtures or
  arrives under the "unknown channel" rule.
- **WT-N8** `§5.1`: `temperature_c` is 40% of every frame for a debug view; record that cost as a choice.

Verdict: not ready to build; the four BLOCKERs (WT-B1 to WT-B4) are contract choices that step 7 freezes, and each is
cheap to settle in the spec now.
