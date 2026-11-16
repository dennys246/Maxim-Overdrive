# Trust boundary review: realtime_lanes_coop (design v0, commit 52e64f0)

Lens: Trust boundary (`docs/code_review.md`), extended to multi-session co-op and the thinking lane. Reader read
CLAUDE.md, the charter, `docs/architecture.md` ("Transport"), `docs/standards_backlog.md` (B3, B14),
`sem_env/bridge.py`, `world/damage.py`, `world/world.py`, `world/heat.py`, `imagination/spec.py` and the design.

**Evidence.** The `act` findings (TB-1 to TB-3) are measured, not guessed. A scratch script (not committed) called
`StructureModulator.execute` on the laptop profile with the test wall from `tests/test_sem_bridge.py`, then ran
`World.advance()` for `ignite`:

| Input | Result today |
|---|---|
| `json.loads('{"e": NaN, "f": Infinity, "g": 1e400}')` | `{'e': nan, 'f': inf, 'g': inf}`: Python's json accepts these by default |
| `strike {energy_j: NaN}` | `success=True`; all 360 wall cells get NaN integrity, and stay solid forever (`NaN <= 0` is False) |
| `strike {energy_j: inf}` or `"inf"` (a string) | `success=True`; 24 cells get NaN integrity: an indestructible patch |
| `strike {sigma_m: NaN}` / `point_m: [NaN, 1, 1]` | `success=True`; 360 NaN-integrity cells |
| `strike {point_m: [1.0]}` | **raises `IndexError`**, which the modulator doesn't catch (it catches only KeyError, ValueError and TypeError) |
| `strike {energy_j: 1e300, sigma_m: 100}` | `success=True`; the whole wall is destroyed with one valid-looking intent |
| `strike {energy_j: true}` | accepted as 1.0 J |
| `ignite {power_w: NaN}` | `success=True`; after one advance, **every** cell's temperature (1800 of 1800) is NaN |
| `ignite {power_w: -1e9}` | `success=True`; minimum temperature −29,300 °C, below absolute zero |
| `ignite {power_w: 1e300}` | `success=True`; maximum 3.3×10²⁹⁸ °C, 132 cells degraded to air, overflow warnings |
| `ignite {radius_m: -0.3}` | `success=True`: `radius**2` makes a negative radius act as a positive one |
| `ignite {power_w: 1e4, radius: 50}` (typo) | `success=True`; the unknown key is silently ignored |

## Findings

### TB-1 BLOCKER: `act` params reach the world without finiteness, sign or range checks
**Location:** design §5 `act` ("validated before anything is applied", with no validator specified);
`sem_env/bridge.py::StructureModulator.execute`; `world/damage.py::strike`; `world/world.py::World._power_field`.
**Scenario:** any client, or the thinking lane, sends `{"type":"act","region":"wall","action":"ignite","params":
{"power_w":NaN}}`. Python's json decodes `NaN`. The modulator accepts it. On the next physics tick the heat solver
spreads NaN through every cell of the tile, for every session, permanently. The snapshot then casts NaN to `uint8`
(undefined) and `float16`. `strike` with NaN or inf energy makes permanently indestructible NaN-integrity cells. A
negative `power_w` cools cells below absolute zero. This is a world-corruption attack through a message that is
well-formed under the design's current wording.
**Fix:** the protocol layer decodes `act` into a frozen, typed intent (`StrikeIntent`, `IgniteIntent`,
`ExtinguishIntent`), validated field by field the way `scene.finite_vector` and `imagination.spec._read` already
are:
- `json.loads(..., parse_constant=<refuse>)`, plus an explicit `math.isfinite` check (since `1e400` decodes to inf
  without going through `parse_constant`);
- `bool` refused where a number is expected;
- strings never coerced to numbers (`float("inf")` accepts a string);
- `point_m` through `finite_vector(…, 3, …)`;
- signs and ranges from `data/` YAML: `0 < sigma_m ≤ max`, `0 ≤ energy_j ≤ max`, `0 < power_w ≤ max`,
  `0 < radius_m ≤ max`, each cap physically motivated (a grenade, a thermite charge) and documented;
- the world refusing in depth: `damage.strike` and `HeatSource` (in `__post_init__`) also refuse non-finite
  values, so the thinking lane and future callers are covered even if they bypass the codec.

Tests: a Hypothesis property test that no `act` payload ever raises or produces a non-finite cell (B9).

### TB-2 BLOCKER: `execute` can raise past its own error handling; a lane crash takes down every session
**Location:** `sem_env/bridge.py::StructureModulator.execute` (`except (KeyError, ValueError, TypeError)`); design
§2 (the simulation lane holds `World` alone).
**Scenario:** `point_m: [1.0]` raises `IndexError` inside the simulation lane. In a single-owner design an
unhandled exception there kills the tick loop for all sessions (a co-op DoS by a guest), or, if the host wraps the
lane in a broad `except`, it becomes a silent swallow (CLAUDE.md, B13).
**Fix:** make the typed intent from TB-1 the only thing that reaches `execute`, so the modulator's dict-of-`Any`
parsing isn't the trust boundary. State in the design that the simulation lane never sees an unvalidated value, and
that an exception inside `tick()` is a server bug: the host stops, the error is logged and every session gets
`error{code:"internal"}`. It is never swallowed. Test: an `IndexError`-shaped payload is refused at the codec.

### TB-3 SHOULD-FIX: unknown params, fields and message types are not specified as refusals
**Location:** design §5 (message tables); `StructureModulator.execute` ignores extra keys.
**Scenario:** `{"power_w":1e4,"radius":50}` (a typo, or an LLM's paraphrase) succeeds with the default radius. The
player or NPC believes it set a 50 m radius. For the thinking lane, a silent drop hides the model's mistake from the
log. Unknown top-level fields (`"actor": 2`, `"tick": 0`) aren't refused either, so a client can't tell that they
had no effect.
**Fix:** a closed schema per message type. An unknown `type`, an unknown top-level field, an unknown param, a
missing required field or a wrong JSON type each gives `error{code:…}` with the world unchanged. `actor`, `tick`,
`role` and `session` are named in the spec as fields a client must never send, and they are refused, not ignored.

### TB-4 BLOCKER: roles, tokens and "who is host" are undefined; a guest can become host
**Location:** design §4 ("Each connection is a `Session` with its own token, actor and role"), §5 `hello` (only
`protocol` and `token`), `docs/architecture.md` ("a per-launch token").
**Scenario:** the design gives each session "its own token", but the architecture has one per-launch token, and
`hello` carries nothing that decides the role. So the role must come from connection order: "first `hello` is
host". Then:
- (a) any local process that reads the token, or that races the launcher, connects first and holds time authority;
- (b) when the host disconnects, either nobody is host (time is stuck at its last scale forever, perhaps 30×) or the
  next session is promoted, and a guest becomes host by waiting, or by provoking the host's disconnect (TB-8's slow
  reader, for instance);
- (c) a second connection presenting the host's token is either refused (a stale socket then locks the real host
  out) or accepted (two hosts, or a takeover).

**Fix:** decide it in the design.
- The launcher mints two secrets with `secrets.token_urlsafe(32)`: a host token, and a guest token (or one guest
  token per invite slot). **The role is a property of the token, never of order.**
- The token is compared with `hmac.compare_digest` against each known token, every one compared, without stopping
  at the first match.
- At most one live session per token. A second `hello` with a live token is refused, unless takeover is designed
  explicitly. If it is, the old session is closed first, and the takeover is logged.
- **No promotion.** When the host leaves, the `TimeAuthority` gets a "host absent" event and the world pauses. That
  pause is a logged decision at a host-assigned tick. Policy can change this later, but a guest never inherits host.
- Role and actor are fixed for a session's life. `TimeAuthority.decide` receives a frozen view of the sessions
  taken in the simulation lane at the decision tick, so a role change can't race a decision.

### TB-5 SHOULD-FIX: how a token reaches a client, and where it must never appear
**Location:** design §5 `hello` ("the token travels here, not in the URL"); architecture "Transport".
**Scenario:**
- Passed as a command-line argument, the token is visible to every local user through `ps`.
- Written to a world-readable file, any local process gets it.
- If the intent log, the metrics or the `websockets` DEBUG logger record the raw `hello` frame, the token is on
  disk, and a replay log shared as a bug report (the design calls the log "the bug report") leaks it. Replay logs
  and tokens outlive the launch, and if the launcher ever reuses a token, an old log authenticates.
- An `error` that echoes the offending message (`in_reply_to` with the payload) echoes the token too.

**Fix:**
- Hand the token over by environment variable or by a file created with mode 0600 in a per-user runtime directory,
  never through argv.
- The token is fresh on every launch.
- The record lane stores session id, actor and role, never the token. `hello` is not logged verbatim.
- `in_reply_to` carries only `seq`.
- A test greps the log and the captured server logs of an e2e run for the token string.

### TB-6 SHOULD-FIX: handshake lifecycle (pre-`hello`, repeated `hello`, never `hello`) is not specified
**Location:** design §5 (`hello`: "first, and only once").
**Scenario:**
- A local process opens hundreds of sockets and never sends `hello`, holding memory and file descriptors, with no
  limit on sessions.
- A client sends `act` before `hello`. If the network lane queues it and authenticates it later, a pre-auth intent
  slips in.
- A second `hello` with a different token re-roles the session (a guest becomes host).
- A wrong token answered with an `error`, the socket left open, invites unlimited guesses on one socket.

**Fix:**
- Any message before a valid `hello` closes the socket with an error code.
- A second `hello` closes it.
- A wrong token, or an unknown or missing `protocol`, closes it after one error.
- A `hello` deadline of a few wall seconds. The network lane may use the wall clock, since it never reaches `World`.
- A cap on concurrent sessions (data), refused at the handshake.
- A binary frame from the client is refused (the protocol has none client-to-server).

### TB-7 BLOCKER: inbound `max_size` must stay small; the architecture says to raise "both ends"
**Location:** `docs/architecture.md` "Transport" ("Both ends must raise their default caps … Python `websockets`'
`max_size` is 1 MiB"); design §5.
**Scenario:** `websockets`' `max_size` limits *incoming* messages only. The large messages are server-to-client
snapshots, which Godot's `inbound_buffer_size` limits. If the server raises its `max_size` to fit snapshots
(26–52 MB at max), every client may send 50 MB JSON frames. That's 50 MB of buffer, plus json parse time and memory
several times that, per message, in the network lanes. `websockets` also enables permessage-deflate by default, so a
small compressed frame inflates up to `max_size`, and each connection carries deflate state.
**Fix:** state in the design that the server's inbound `max_size` is small (client messages are under 1 KiB today;
proposed 64 KiB, as data), that `max_queue` is bounded, and that `compression=None`, because v0's compression is
application-level in the snapshot header. Only the Godot client raises its inbound buffer. Correct the
architecture's sentence. Tests: an oversized frame closes with 1009 and the world is unchanged; a deep-nesting JSON
(`[[[[…]]]]` within the cap) gives a decode error, not a `RecursionError` crash.

### TB-8 BLOCKER: a client that never reads grows server memory without bound; outbound queues are unbounded
**Location:** design §2 ("Network: … queue depth per client", metered but not bounded), §5 (snapshot "on request",
`tick` "each tick").
**Scenario:** a guest connects, sends `hello`, and never reads. At 10 Hz `tick` messages plus 2 Hz snapshots of
3.2 MB (rig) to 26 MB (max), an unbounded per-session `queue.Queue` grows by 6–52 MB/s. The host runs out of memory
in minutes, and every session dies. If instead the network lane blocks on a full TCP buffer while holding a shared
lock or the publish step, the simulation lane stalls for everyone (dilation caused by one guest).
**Fix:**
- Per-session outbound state is **latest-wins** for snapshots and `tick` status: one slot each, which a newer one
  replaces. It is not a queue.
- Replies (`welcome`, `error`, `time_decision`) go in a small bounded queue. If it overflows, the session is closed,
  never silently dropped.
- The simulation lane publishes an immutable snapshot and never waits on a network lane.
- A session that hasn't drained a snapshot for N wall seconds (data) is closed.
- A test with a client that never reads: server RSS or queue length stays bounded, and the other session's tick
  rate is unaffected.

### TB-9 SHOULD-FIX: snapshot amplification through `snapshot` requests
**Location:** design §5 (`snapshot`, "asks for a full snapshot now"; "on request" bypasses `snapshot_hz`).
**Scenario:** a 30-byte `{"type":"snapshot","seq":n}` returns 26–52 MB at max. A loop of them costs the server one
O(cells) encode per request (if each is encoded on demand), and gigabytes of outbound queue with TB-8.
**Fix:** encode at most once per published tick, shared by all sessions as immutable bytes. A request only marks
"send the latest" in the session's latest-wins slot (coalesced). Requests beyond `snapshot_request_hz` get
`error{code:"rate_limited"}`. Test: 1,000 requests in one tick cause at most one encode and one send.

### TB-10 SHOULD-FIX: no per-session rate limit on `act`; valid intents are O(cells) each
**Location:** design §2 step 1 ("take the intents for this tick"), §5 `act`.
**Scenario:**
- `damage.strike` is O(cells) whatever `sigma_m` is: three `ndtr` calls, then full-grid multiplies, about 5×10⁶
  cells at max. A guest sending 10,000 strikes in one tick, all valid and in range, stalls that tick for seconds,
  and the dial reports dilation that one guest caused.
- `ignite` per region is bounded by the region count (the source key is `fire:{region}`). But `_power_field` runs
  `sphere_overlap` over the whole grid, with 64 samples per cell, for **each** source, and `heat.step` recomputes it
  after every substep that destroys a cell. So igniting every region with a large radius at max profile multiplies
  physics cost by the region count for as long as things burn.
- Each accepted intent is logged, so the record lane grows at the attacker's rate.

**Fix:**
- A per-session token bucket on `act` (data: sustained rate and burst), plus a per-tick cap on intents applied per
  actor. Excess gets `error{code:"rate_limited"}` before the intent is queued or logged.
- A global cap on simultaneous heat sources.
- Cost caps tied to the rig. For example, bound `radius_m` so a sphere can't cover more than K cells, or make the
  radius cap absolute in metres, so the outcome class is the same at every rig (the resolution rule).
- Record the remaining Performance cost as a B5 row.

### TB-11 SHOULD-FIX: `time` requests: value validation and log/decision spam
**Location:** design §4 (`TimeAuthority`, "the log records the decision"), §5 `time`.
**Scenario:**
- `set_scale` with `NaN`, `-1`, `inf`, `1e12` or `true`: the wall pacer computes a sleep from `1/scale`, which
  divides by zero, sleeps forever, spins, or makes "unpaced" (headless) reachable from the wire.
- `pause` carrying `scale: 5` is ambiguous.
- A guest sends 10⁵ `time` requests a second. If refusals are logged as decisions, the log grows at the attacker's
  rate.
- A host flapping `set_scale` every tick does the same.

**Fix:**
- `scale` is required for `set_scale` only, and forbidden otherwise. It is finite, not a bool, and in
  `[0, max_scale]` (data). Unpaced is not a wire value.
- Define `pause` against `set_scale 0`, and what `resume` restores.
- Log only *granted* decisions, which are the ones that change state. Refusals go to metrics, not the replay log.
- `time` gets its own rate limit.
- Test: every bad `scale` gives `error`, the scale is unchanged, and the log is unchanged.

### TB-12 SHOULD-FIX: client `seq` in the ordering key lets a client break determinism and collide entries
**Location:** design §2 ("ordered by (tick, actor, seq)"), §5 ("Every message carries `seq`").
**Scenario:** `seq` comes from the client. A client sending the same `seq` twice, a decreasing `seq`, a negative
one, `2**80` or `1.5` makes ties in `(tick, actor, seq)`. Their order then depends on arrival or on sort stability,
and two log entries can't be told apart. A client can also reorder its own intents within a tick against the order
it sent them in.
**Fix:** the host assigns its own per-session arrival counter for ordering and logging. The client's `seq` is only
echoed in replies. `seq` is validated as an int in `[0, 2**53)` and must strictly increase per session, refused
otherwise. Test: a duplicate or decreasing `seq` is refused.

### TB-13 SHOULD-FIX: world-dependent validation must happen in the simulation lane at the tick (TOCTOU)
**Location:** design §2 ("network lanes … decode, validate, stamp the actor, queue").
**Scenario:** a network lane checks `region in world.grid.regions`. That reads `World` from outside its owner, which
breaks the one-owner rule, or else reads a stale copy. Between validation and the tick, `imagination.spec.place`
can add a region, and a strike can empty a region of cells (`centroid_m` raises then). The intent was "valid" when
queued and fails or misbehaves when applied, possibly after the network lane has already said it was accepted.
**Fix:** split validation into two stages:
- **Stage 1, in the network lane:** pure checks of schema, types, finiteness and ranges. These need no world.
- **Stage 2, in the simulation lane at the assigned tick:** world-dependent checks: region exists, region has
  cells, the actor may act on it.

A stage 2 refusal is a deterministic, logged outcome (so a replay reproduces it) and sends an `error` reply. Specify
when the client gets the `ok` (after stage 2), and add a protocol `ack` or `result` message if needed. Region names
are only looked up in a dict, never used as format strings or paths (the source key `fire:{region}` is fine as long
as regions are dict keys).

### TB-14 SHOULD-FIX: a disconnected session's in-flight intents are unspecified
**Location:** design §2, §4.
**Scenario:** a guest sends 50 `act`s and disconnects. Depending on thread timing, some are applied and some are
dropped, so a replay of the log may not match the session (determinism), and a ghost actor keeps acting after it
has left.
**Fix:** the deterministic rule is that an intent counts once the simulation lane has taken it and stamped its
tick. Everything stamped is applied and logged. Everything still in the channel at disconnect is discarded, and the
disconnect itself is a logged event at a host tick, so a replay sees the same cut. Fires a guest started persist,
since they are world state. Actor ids come from a monotonic counter and are never reused within a log; a reconnect
gets a new session id and, per TB-4, keeps its actor only if the design says so explicitly.

### TB-15 BLOCKER: the thinking lane is a trust boundary and the design doesn't say it passes the same validation
**Location:** design §2 "The thinking lane and determinism" ("results apply at a world-time deadline"), §2 step 2.
**Scenario:**
- An NPC's LLM returns `{"action":"ignite","params":{"power_w":"Infinity"}}`, a region it can't perceive, another
  actor's id, or a `time` request. If thought results are applied as "thoughts" through a different path from
  client intents, TB-1 to TB-3 reopen with an LLM as the attacker, and with prompt injection, any player who can put
  text in front of an NPC (dialogue) becomes one.
- Thought results replayed from the log are another loader: a hand-edited or old-version log is untrusted input too.
- An LLM result of arbitrary size gets stored verbatim in the log.

**Fix:** state in the design that a thought result is decoded into the *same* typed intents by the *same* stage 1
validator, and the same stage 2 check at its deadline tick, as a client `act`.
- The actor comes from the request record the host made at tick T, never from the model's output.
- NPCs hold no time role, so their `time` intents are refused.
- Imagined objects still enter only through `imagination.spec.place`.
- A refused thought becomes `thought_failed` with the reason, and is logged.
- Results have a size cap.
- The replay loader validates every log entry and refuses unknown log versions (B3/B4 pattern).
- Each NPC's thinking requests get a rate limit, or a cap on how many it has in flight, so a dialogue loop can't
  flood the pool.

### TB-16 SHOULD-FIX: Origin refusal and loopback binding need to be pinned for many sessions
**Location:** design §4 ("listening beyond 127.0.0.1" deferred), architecture "Transport".
**Scenario:** with many sessions the check must run per connection, in the handshake hook (`process_request`), not
once at startup. Other failure modes:
- `serve(host="localhost")` can bind `::1` as well. `host=""` or `None` binds every interface.
- An empty `Origin:` header, or `Origin: null` (sandboxed iframes send `null`), might be treated as "no Origin".
- A plain HTTP GET to the port gets an uncaught 500 with a traceback.

DNS rebinding is covered, because browsers always send Origin, but only if "any Origin header, including empty and
`null`" is refused.
**Fix:**
- Bind the literal `"127.0.0.1"`.
- Refuse a handshake on the *presence* of the header, whatever its value.
- Refuse non-WebSocket requests with 400.
- Tests: Origin values `https://evil`, `""` and `null`, each on a second connection while a first session is live;
  the bound socket's address is 127.0.0.1; a guest from a browser page can't connect while the host is connected.

### TB-17 NIT: the reserved vote path needs its refusals now
**Location:** design §4 ("A vote is another `TimeAuthority` … 'pending' reply, which v0 already reserves").
**Scenario:** a client sends `{"type":"vote",…}` or `time` with `ballot`. If v0 ignores it, a future vote policy
inherits an implicit "ignored" behaviour that the client may already depend on. A pending decision also needs an
end: a timeout, a voter leaving, a host override.
**Fix:**
- v0 refuses `vote` as an unknown type, with a test.
- `HostOnly` never returns `pending`. A test proves that, and the GDScript client must still handle `pending`.
- Record now that a vote policy must define quorum against the frozen session view (TB-4), the pending timeout, and
  that a pending decision is logged only when it resolves.

### TB-18 NIT: actor-id ordering gives the host first move in every conflict
**Location:** design §2 ("ordered by tick, then actor id").
**Scenario:** the actor with the lowest id (the host, probably) always wins a same-tick race: both strike the last
cell of a door, or both ignite the same region (only one `fire:{region}` key exists). That isn't a security hole,
but it is a fairness rule baked into the wire contract.
**Fix:** state it as deliberate, or rotate deterministically by tick. Note in any case that same-region `ignite`
from two actors overwrites the first actor's source.

## Rejection paths the 2a and 2b tests must cover

Each one gives an `error` reply or a close, and leaves world state, the intent log and the session's role unchanged,
unless noted otherwise.

**Transport and handshake (2a, B14):**
1. A handshake with an `Origin` header: any value, `""`, `null`; including while another session is live.
2. A non-WebSocket HTTP request to the port gets 400, not 500 and not a traceback.
3. The listener is bound to 127.0.0.1 only; it isn't reachable on `::1` or on other interfaces.
4. An inbound frame over `max_size` closes with 1009. Compression isn't negotiated.
5. A binary frame from the client.
6. Invalid UTF-8 or non-JSON text, JSON that isn't an object, deeply nested JSON within the cap.
7. `NaN`, `Infinity` or `-Infinity` literals, and `1e400` (decodes to inf), anywhere in any message.
8. Any message before `hello`.
9. A second `hello` on a live session.
10. `hello` with a missing or wrong token, a token of the wrong type, the guest token trying to claim host, or a
    token already live on another session.
11. `hello` with a missing, unknown or non-int `protocol` (B3).
12. No `hello` within the deadline: closed.
13. A session beyond the session cap.
14. The token appears in no log, metric, error reply or intent-log entry (an e2e grep).

**Message envelope (2a):**

15. An unknown `type`, including `vote` and `advance` (`advance` is explicitly not in the vocabulary).
16. Missing `seq`; `seq` not an int, negative, ≥ 2⁵³, duplicated or decreasing.
17. Unknown top-level fields, including the client-forbidden `actor`, `tick`, `role` and `session`.

**`act` (2a stage 1; stage 2 in the simulation lane):**

18. Unknown `action`; a missing `region`, `action` or `params`; `params` not an object.
19. An unknown param key; a missing required param (`energy_j`, `power_w`).
20. A param of the wrong type: string (`"inf"`, `"1"`), bool, null, list, object.
21. `energy_j`, `sigma_m`, `power_w` or `radius_m` that is non-finite, negative, zero where it must be positive, or
    above its data cap.
22. `point_m` that isn't exactly 3 finite numbers (length 1, length 4, strings, nested, a bool).
23. An unknown region (stage 2); a region with no cells (stage 2); a region added or emptied between queueing and
    the tick (stage 2, deterministic and logged).
24. A rate limit exceeded (per session, and per actor per tick). The heat-source cap exceeded.
25. A Hypothesis property: no `act` payload raises past the codec or leaves a non-finite value in `integrity` or
    `temperature` after `tick()` (B9).

**`time` (2a):**

26. A guest's `pause`, `resume` or `set_scale` is refused with a reason. The scale is unchanged, and the refusal
    isn't in the replay log.
27. `set_scale` with a missing `scale`, NaN, inf, a negative value, a value above `max_scale`, or a bool. `scale` on
    `pause` or `resume`.
28. `time` beyond its rate limit.
29. `HostOnly` never returns `pending`.
30. The host disconnects: the world pauses as a logged decision, and no guest gains the host role. A host reconnect
    with the host token restores it.

**`snapshot` and outbound (2a/2b):**

31. 1,000 `snapshot` requests in one tick cause at most one encode and one send. Requests beyond the rate limit get
    `rate_limited`.
32. A client that never reads: outbound memory stays bounded, the session is closed after the drain timeout, and the
    other sessions' tick rate is unaffected.
33. A reply-queue overflow closes the session, never silently drops.

**Lifecycle and determinism (2a/2b):**

34. A disconnect with intents in flight: stamped intents are applied and logged, unstamped ones discarded, and the
    replay of the log is bit-identical.
35. Actor ids aren't reused after a disconnect.
36. An exception inside `tick()` stops the host loudly. It is never swallowed.

**Thinking lane (2b):**

37. A stub "LLM" returning each `act` refusal above gets `thought_failed` with the reason, logged, and the world is
    unchanged.
38. A thought naming another actor, or a `time` request from an NPC, is refused.
39. A thought result over the size cap.
40. A replay log with an unknown version, a malformed entry, or an entry that fails validation is refused loudly.
41. Thinking requests in flight per NPC are capped.

## What I checked and found sound

- **The actor is never taken from the message** (§4 "The host assigns the actor"). Correct, as long as TB-3 makes a
  client-sent `actor` a refusal rather than a silently ignored field.
- **The token travels in `hello`, not the URL** (§5). Correct: URLs end up in logs and proxies.
- **`advance` is removed from the client vocabulary**, and `tick()` takes no duration (§1, §5; B14). This closes the
  "client chooses dt" path completely. A wall-clock value reaching `World` stays guarded by B14.
- **The host assigns the tick on dequeue, never from a client clock** (§2). Sound; TB-12 covers the `seq` half of
  the key.
- **The log records the time *decision*, not the request** (§4), so a replay never re-runs policy or role state.
  Sound.
- **`imagination.spec.place`** is a good model for the `act` validator. It funnels every malformed shape into
  `SpecRejected`, uses `finite_vector` (which handles bools, numpy scalars and `OverflowError`), and touches nothing
  before every check passes. The `act` codec should copy this pattern (TB-1).
- **LAN, NAT traversal and accounts are deferred** as deliberate protocol and security changes (§4). That keeps the
  attacker model to local processes and browser pages, which the Origin refusal and the token cover once TB-4,
  TB-5 and TB-16 are folded.
- **The `error` reply says "the world is unchanged"** (§5). That is the right contract. `execute` is atomic for the
  exceptions it does catch (`HeatSource` is built only after `float()` succeeds), but TB-1 and TB-2 show inputs that
  break it today.
