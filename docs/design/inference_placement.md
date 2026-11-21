# Inference placement: where an NPC's model calls run (design, v1 draft, 2026-11-21)

**Status:** DRAFT v1, not reviewed. It changes the architecture (a new process kind, a new data format, a change to
the response cache's key), so it gets a design review before code: Executor, Architecture, Wire integrity, Trust
boundary, Concurrency and lanes, Determinism and replay, Performance and Bio-faithful integration
(`docs/code_review.md`, "Design reviews").

**What it covers.** The host's thinking lane already executes every model request an NPC makes (`npcs_and_sem.md`
O6a, §4.4, §6.2; `boundaries.md` §7.1). This part says **where** each request runs: a model on this machine, a model
on another of the player's machines, or a cloud API such as Claude. It covers the contract for choosing a placement,
the process that makes the calls, what each reply records, consent and credentials, and what placement may and may
not change in the world. It builds no remote agents (§7).

**Sources:** Maxim `origin/main` at **043eab8f**, read with `git show`, never its working tree; the locked release is
pymaxim **1.3.3** (`constraints/py3.12.txt`). Line numbers are at 043eab8f. The LLM spike
(`research/llm_spike.md`). *Verified* means the author read the cited line at that revision.

**Tags:** **[now]** is built in `phase1/agents` against the scripted test double and a scripted transport. **[Phase 4]**
lands with the first real NPCs. **[later]** is named so the contract leaves room for it, and is not built.

## 0. Decisions

| # | Decision | Where |
|---|---|---|
| **O46** | **The host's thinking lane owns placement (owner, 2026-11-21).** The lane decides which model serves each request: by role, consent, health, capacity and budget. Maxim's `LLMRouter` is not on the NPC path. Its failover, cooldowns, drain state and cost downgrades would be a second scheduler under the lane's, and each would override the other without either seeing it (§1). Maxim's **backends** are the transports. | §1, §2 |
| O47 | **The calls run in a host-owned inference gateway process, not in the world server (owner, 2026-11-21; was P1).** O13's "the LLM gateway stays in the host" reads as host-side: the host decides, and a host-owned gateway calls. | §3 |
| O48 | **Each role is pinned to its first eligible placement by default; spilling under load is an opt-in per role (owner, 2026-11-21; was P2).** | §2.4 |
| O49 | **A model on another of the player's machines counts as remote under O18, so a guest's words reach it only after a disclosure (owner, 2026-11-21; was P3).** | §5.1 |

## 1. What Maxim offers, and why its router is not the scheduler

Maxim's distributed infrastructure moves **inference**, not agents:
- **`maxim/peer/`** sends a machine's model calls to a "leader". A leader is llama.cpp behind an auth proxy with one
  shared cluster key. The configuration lives in `~/.config/maxim/peer.yml` and `mesh.yml` (`peer/config.py`,
  `peer/mesh_config.py`).
- **The router** gives each lane an ordered list of providers, each `LOCAL`, `CLOUD` or `PEER`
  (`runtime/worker_pool.py:72`).
- **`maxim/mesh/`** runs inside one process only. Its networked modules were deleted as dead code on 2026-04-12
  (`mesh/__init__.py` docstring, *verified*). Spreading calls across several peers is a deferred plan, revived on
  2026-10-18 and not built (`docs/plans/deferred/llm_path_multi_peer_dispatch.md`, *verified*).
- **Hivemind** exchanges learned substrate as offline bundles. Overdrive's Phase 5 rumour uses it (`roadmap.md`
  Phase 5), and nothing here changes that.

**The router serves one agent loop well, but not a world that schedules many:**
- **It serialises.** Every call on one `LLMRouter` takes `_inference_lock` (`router.py:192`, *verified*: "llama-cpp
  not thread-safe"). Maxim's own architecture document calls this "the concurrency wall"
  (`docs/architecture/llm_routing.md`, *verified*).
- **It fails over silently.** The router catches a failure, notes it, and tries the next provider in the same call
  (`llm_routing.md`, `_try_provider`, *verified*). A reply could then come from a model the lane never chose, and the
  lane's deadline and capacity accounting would be wrong without anything showing it.
- **It reads process-global state:** an environment variable for its lock timeout (`router.py:77`), its own
  `CostTracker` (`:201`), and drain state in `~/.maxim/util/drained_nodes.{role}.txt` (`peer/drain_state.py:10`,
  `:145`), all *verified*. The world server's isolation rules forbid that.

**The backends are what the lane needs.** `models/language/backend_protocol.py::LLMBackend` is a structural protocol.
`complete_with_usage(...)` returns `LLMResponse`, which carries `content`, `model`, `provider`, token counts and
`stop_reason` (`types.py:25-53`, *verified*). There are three transports a placement can name:
- `_AnthropicBackend`. Its retries are configurable to zero (`max_retries` and `capacity_max_retries`,
  `anthropic_backend.py:172-190`, *verified*).
- `_OpenAIBackend`, for any OpenAI-compatible endpoint, which includes local servers.
- `_MaximPeerBackend`. It makes "ONE HTTP call", with no retry, and raises a typed `BackendError`
  (`maxim_peer_backend.py:537-552`, *verified*).

**Three facts about those backends shape the contract:**
1. **A cloud backend can fail with an empty reply instead of an error.** `_AnthropicBackend` returns
   `LLMResponse(content="")` when the client can't be built, for example a missing key (`:223-241`, `:333-335`,
   *verified*). `_OpenAIBackend` does the same, and also on a final call failure (`openai_backend.py:358-360`, `:505`,
   *verified*). Maxim's router treats empty content as failure (`llm_routing.md`, `_try_provider`). The lane
   therefore maps empty content to the outcome `empty`, a failure (§2.6). That is Maxim's documented contract, not a
   special case of ours. Making the backends raise is OD-I9 (§9).
2. **Not every retry can be switched off.** `_OpenAIBackend` retries gateway errors up to a hard-coded
   `max_gateway_retries = 4` (`:391`, *verified*), up to about 50 s by its own comment (`:396-398`). So that transport
   can't promise one call, one outcome. This is OD-I9 (§9).
3. **No backend takes a per-call deadline or a seed.** `complete_with_usage` has neither parameter on the cloud or
   peer backend (`anthropic_backend.py:318-329`, `maxim_peer_backend.py:537-549`, *verified*). The timeout belongs to
   the backend instance (`timeout_s`, `anthropic_backend.py:165-170`), and the peer backend checks for cancellation
   only before it makes the call (`:555-566`, *verified*). Two consequences follow. A cancelled or overdue call holds
   its slot until it returns (§2.5), which is OD-A23 (§9). And live replies can't be reproduced, so the response
   cache stays the only way to reproduce them (§4).

## 2. The contract

### 2.1 Roles and envelopes **[now]**

- **A request names a role, never a model.** The request value carries a model **role** (OD-A14; `npcs_and_sem.md`
  §6.1). The agent never learns which placement serves it, and nothing about placement crosses `AgentPort`.
- **Each role has an envelope:** `context_tokens` (the prompt budget the agent renders to), `max_output_tokens`, and a
  named `token_counter`. The host gives the worker each role's envelope at spawn. Today §6.1 says the bound model's
  context size and tokenizer feed Maxim's `PromptBudgeter`. That becomes **the role's envelope**, so a prompt is
  rendered once and fits every placement in its role. Moving a request to another placement in the same role, after
  a failure or under spill, then needs no new render.
- **Every placement in a role must fit the envelope.** Its declared `context_tokens` must be at least the envelope's
  `context_tokens + max_output_tokens`, or the loader refuses the table. If a placement overflows anyway (its
  tokenizer counts more than the role's counter), the outcome is `context_overflow`. It is metered, and the lane never
  retries it with a shorter prompt.
- **The role vocabulary is closed.** It is the set of roles B1's request value ships, measured at OD-A14. The table
  must cover every role. Until that set exists, the test double's roles stand in, and the loader refuses an uncovered
  role.
- **[later]** The table's key may widen from the role alone to role plus an NPC tier. That would be level of detail
  for thought: the NPC in a conversation with the player gets the larger model. The request doesn't change, and the
  tier comes from the roster, never from load.

### 2.2 Placements **[now: format and loader; Phase 4: real transports]**

A placement is one model endpoint the lane may dispatch to:

| Field | Meaning |
|---|---|
| `id` | A stable name. It is the only form in which a placement appears in logs, meters, manifests and the cache. |
| `transport` | `openai_compatible`, `anthropic` or `maxim_peer`: which Maxim backend the gateway builds (§3). |
| `egress` | `loopback` (this machine), `owner_lan` (another of the player's machines) or `third_party` (a cloud provider) (§5). |
| `model` | The declared model id. For `loopback` and `owner_lan`, also a declared weights digest. The host can't verify a remote server's weights, so the digest is declared, not checked. |
| `context_tokens` | The model's context length, checked against each role's envelope (§2.1). |
| `max_in_flight` | Whole number ≥ 1: concurrent calls this placement accepts (§2.5). |
| `timeout_s` | The wall ceiling per call, host-only (`npcs_and_sem.md` §1, "Where wall time remains"). |
| `price` | USD per million input and output tokens; required for `third_party`. |
| `endpoint_ref`, `credential_ref` | Names resolved only in the gateway (§5.2). |

- **Local models are loopback servers,** such as llama.cpp's server or Ollama, reached through `openai_compatible`.
  The spike measured exactly this (Ollama at 127.0.0.1, `research/llm_spike.md`). In-process llama.cpp is not a
  placement:
  - it isn't thread-safe (`router.py:192`);
  - its weights would sit in the gateway's memory;
  - a server batches the requests in flight.

  Whether the host starts the server is the Phase 4 build step's decision, and that is a new spawn site.
- **Two files, both loaded through gates:**
  - **`data/agents/placement.yaml`** (shipped and versioned) holds the roles, their envelopes, each role's policy
    (§2.4) and the default `loopback` placement.
  - **`placement.local.yaml`**, in the game's per-user config directory, never in the repository, holds the player's
    own placements, their order per role, opt-ins and the session spending cap.

  The merged table, without endpoints or credential references, is one canonical value. Its digest goes in the rerun
  manifest (§4.3).

### 2.3 Eligibility **[now]**

A placement is eligible for a request when all four hold:
1. **Consent:** its `egress` is allowed in this session (§5.1).
2. **Health:** it isn't cooling down after a failure (§2.6).
3. **Budget:** for `third_party`, the session's spend is below its cap (§5.3).
4. **Fit:** it meets the role's envelope. This is checked at load, so it can't fail at dispatch.

### 2.4 Selection, the default law **[now]**

- **The order is unchanged:** dispatch goes by deadline (`npcs_and_sem.md` §4.4).
- **Choosing a placement for the request at the head of the queue:**
  - **`pinned`** (the default, O48): the first eligible placement in the role's list. If its slots are full, the
    request waits for one.
  - **`spill`** (opt-in per role): the first eligible placement with a free slot. If none has one, the request waits.
- **Placement is chosen when a slot is granted, not when the request is queued.** The law is simple on purpose, and
  can be replaced behind this contract.
- **Why `pinned` is the default.** Under `spill`, which model answers depends on how busy the host is. The NPC's
  capability would then rise and fall with load, which §4.1 forbids for the thought's *kind* and which is no better
  for its content. A role pinned to one placement changes model only when that placement fails, and a failure is
  metered (§2.6).

### 2.5 Capacity **[now]**

- **A slot is held from dispatch until the backend call returns.** Cancelling or abandoning a request stops the
  lane waiting at once, but the slot stays held until the call returns, because no backend takes a per-call deadline
  (§1, fact 3).
- **The no-deadlock invariant still holds** (`npcs_and_sem.md` §4.4): a slot is held only by a call in flight, never
  by an agent.
- **The liveness ceiling still ends the thought** as `thought_failed(reason=timeout)`. The ceiling is the lane's, not
  the slot's.
- **A placement whose slots are all held by calls already abandoned is effectively down until one returns.** It is
  metered as such, and selection treats it as full.

### 2.6 Outcomes, failure and health **[now]**

- **Every attempt ends in one closed outcome:**
  - `ok`;
  - `empty` (§1, fact 1);
  - `transport_down`;
  - `timeout`;
  - `refused(auth | quota | policy)`;
  - `context_overflow`;
  - `cancelled`.

  `BackendError` subtypes and the empty-content signal each map to exactly one of these. An unmapped exception is a
  gateway protocol error (§3), never a silent failure.
- **A failure starts that placement's cooldown,** a wall-time constant per outcome class in `placement.yaml`,
  host-only.
- **Retries follow the existing policy.** Under dilate, a failed attempt is dispatched again, and selection may
  choose the next eligible placement in the role. Past the host ceiling the thought ends as `thought_failed`
  (`npcs_and_sem.md` §1, §4.4). Each attempt is metered.
- **Only the final outcome becomes the thought's reply.** Machine-decided failures stay first-class responses in the
  cache (§4.4 there).
- **A role with no eligible placement** ends the thought as `thought_failed(reason=unavailable)`: logged, and the run
  is tier 3. With guests present, a request never falls through to a remote placement (O18; the gate test in
  `checklists.md`).

## 3. The inference gateway (O47) **[now: the process with a scripted transport; Phase 4: Maxim's backends]**

**What it is.** A second kind of host-owned child process, beside the agent workers. The lane in the host **decides**
(the queue, deadlines, selection, slots, health, the cache). The gateway **does**: it holds the transports and makes
the calls. It is the only process with credentials and outbound access to model endpoints.

- **Spawned like a worker** (`npcs_and_sem.md` §6.6):
  - `spawn`, `-I`, an allowlisted environment and a working directory at its own home under the session;
  - no `HOME`, no `MAXIM_*`, no `*_API_KEY`;
  - not latched, since it needs the network.
- **Its imports are an allowlist:** `maxim.models.language` and the backend modules its transports name. A test
  holds the list, as the worker's import ban does.
- **The channel uses the worker codec's rules:** length-prefixed, versioned, closed-schema JSON, budgets before
  allocation, nothing pickled. Message kinds are closed per direction:
  - **host to gateway:** `open(table)`, `dispatch(attempt_id, placement_id, request)`, `cancel(attempt_id)`,
    `shutdown`;
  - **gateway to host:** `chunk(attempt_id, seq, text)`, `reply(attempt_id, outcome, text, provenance)`,
    `error(code)`.

  A `reply` frees its slot. After a `cancel`, the gateway stops relaying chunks and sends `reply(outcome=cancelled)`
  when the call returns.
- **Everything from the gateway is untrusted input.** The host's stream validation (`npcs_and_sem.md` §5.3) and
  stage 1 run on what it relays, exactly as they would on direct output.
- **A hung or dead gateway never freezes the world.** Past its wall ceiling it is killed. Every attempt in flight
  ends as `transport_down`, and the lane starts a new gateway; the thoughts then follow §2.6.

**Why a process and not imports in the host:**
1. **The host imports `maxim` nowhere.** §6.6 there says the host imports Maxim's types only through
   `simcore/adapters/sem/_compat.py`, and `maxim` itself only in workers. Calling the backends from the host would
   reverse that.
2. **The world server never holds keys.** The world server accepts client connections, and it never holds an API key
   or opens a socket to a model provider.
3. **A blocked call blocks a gateway thread, not the host.** A call that can't be aborted (§1, fact 3) holds a
   gateway thread, never one of the host's.
4. **It is the seam for later.** A gateway on another machine would be a new transport for this same channel. That
   is **[later]**, and not designed.

**Its cost.** One process, plus one local hop per call: microseconds to a millisecond, against the 0.32–1.40 s median
time to first token the spike measured. The hop is measured as a B5 row before Phase 4 commits to it.

**The alternatives the owner declined (O47):**
- **(a) Import Maxim's backends in the host, from an allowlist.** One process fewer, but it reverses §6.6's rule and
  puts keys in the world server.
- **(c) Write our own HTTP clients.** That duplicates transports Maxim maintains (prompt caching, request-id headers,
  peer probing, the address policy on `base_url`, `openai_backend.py:288`), and loses their fixes. Where those
  transports are wrong, the push-back rule says to fix them in Maxim (§9).

## 4. Provenance, the cache and the manifest

### 4.1 The provenance record **[now]**

Every reply carries a frozen, versioned provenance value with golden fixtures:
- the placement `id`, `transport` and `egress`;
- the declared model and digest;
- the **reported** model and provider (`LLMResponse.model`, `.provider`);
- the token counts, the outcome and the attempt count.

It holds no wall time, cost, endpoint or credential. Wall latency and spend are host meters (§6.3).

### 4.2 The cache key changes **[now; the format lands with the cache]**

`npcs_and_sem.md` §4.8 puts the model id and a weights digest in the canonical request. Under placement, that would
make the key depend on host load and health, which are not the agent's. So:
- **The canonical request drops the model id and the digest,** and carries the role and its envelope's version
  instead.
- **An entry holds the raw output, the canonical request and the provenance.**
- **Live play writes the cache and never reads it. A rerun reads it and never dispatches,** and a miss is a loud
  error (§4.8). A key without a model therefore can't reuse an answer across a change of placement in live play.
  *(The Executor should confirm that the existing text means live play never reads the cache. §4.8 says "per save"
  and "misses on a rerun are loud errors", but doesn't say it outright.)*

### 4.3 The rerun manifest **[with the cache]**

`boundaries.md` §6.3 lists "the model ids, weights or quantisation digests and context lengths (the model profile)".
That becomes:
- the merged placement table's digest (§2.2);
- the role envelopes;
- the set of provenance records the cache holds, summarised per placement.

**A rerun never dispatches, so a table that differs on the rerun machine is reported, not refused.** Every other
manifest item keeps refuse-on-mismatch. The model profile is now **per placement and recorded per reply**, and the
Known gap stands as before: the outcome class is not promised across model profiles (`npcs_and_sem.md` §4.1).

## 5. Consent, credentials and privacy

### 5.1 Consent, by egress class **[now: the check; Phase 4: the disclosure UI]**

- **With guests present (O18):**
  - only `loopback` is eligible, unless each guest has accepted a disclosure naming the class (and, for
    `third_party`, the provider);
  - `owner_lan` counts as remote, because a guest's words leave this machine (O49);
  - a guest who hasn't accepted makes the class ineligible for the whole session, since one prompt may hold several
    speakers' words.
- **Single-player:**
  - `owner_lan` is eligible once the player has configured it;
  - `third_party` needs both an explicit opt-in in `placement.local.yaml` and a session spending cap, and with no cap
    it is ineligible.
- **The loopback check.** A `loopback` endpoint must be a literal 127.0.0.1 or ::1, so the check involves no DNS. The
  gateway checks it again before connecting.

### 5.2 Credentials **[now: references; Phase 4: resolution]**

- **The host handles credential references, never key material.** The gateway resolves each reference, from the OS
  keychain or a user secrets file (the Phase 4 build step chooses).
- **It hands the key to Maxim's backend as an already-resolved entry** (`types.py::resolved_entry_key`;
  `anthropic_backend.py:145-163`, *verified*). That way Maxim's env-first key lookup never reads an environment
  variable, and the gateway's environment holds no keys anyway.
- **Credentials, and the endpoints of `owner_lan` placements, never appear** in `data/`, the intent log, a manifest,
  the cache, meters or bug reports. Only placement ids do. An `owner_lan` endpoint names a private host.
- **The host's text gates are the redaction.** Guest text passes `engine.text.player_text` before it reaches any
  prompt. Nothing here relies on Maxim's cloud redaction, which has an open private advisory (OD-I5).

### 5.3 Spend **[now: the meter and the cap; Phase 4: prices]**

- **Spend is the host's arithmetic:** the tokens in the provenance times the placement's `price`.
- **Reaching the cap** makes every `third_party` placement ineligible for the rest of the session. The client is told
  through a host status message.
- **Spend never reaches cognition.** This is the same rule as `LLMEnergyTracker` (`npcs_and_sem.md` §4.6), since an
  NPC must not tire faster on a pricier model.

## 6. Time: what placement may change

### 6.1 Placement changes wall time, never world time

- **A placement changes wall latency.** That changes only dilation, or lateness under floor-holding (O4, O11, O16).
- **It never changes a thought's modelled time, its kind or its landing tick.** `think` resumes at the modelled
  landing tick whichever model answered (`npcs_and_sem.md` §6.6).

### 6.2 The dial-invisibility test widens **[now]**

The same scene, with the test double, run with different placement mixes and seeded per-placement wall latencies,
gives the same kinds, receipts and percepts (`boundaries.md` §7.3). Under `pinned` the transcript is the same too,
since the double answers by request.

### 6.3 Meters (B5 rows) **[now]**

Per placement:
- calls in flight, and how long requests wait for a slot;
- time to first token and to the whole reply;
- failures by outcome;
- slots held by abandoned calls;
- spend, spills and failovers.

Per role: the placement that served each reply. These join §4.5's meters there.

## 7. Agents stay on this machine; the channel stays transport-neutral

**Remote agents are not designed, and this part argues against them:**
- **The barrier.** The barrier parks every agent each tick (`npcs_and_sem.md` §6.3). §6.6's cost line, 20 NPCs at
  200 ticks per wall second (20×), costs 0.2–0.8 wall seconds per second at 50–200 µs per local round trip. At a LAN
  round trip of about 1 ms (*to measure*), the barrier alone would be about 4 wall seconds per second at 20×, and
  about 0.2 at 1×.
- **The heavy compute is already movable.** It is inference (0.3–1.4 s to first token), and placement moves it.
- **Moving agents wouldn't help the scaling cost we've measured.** The host's sensing costs about 2.5–2.9 wall
  seconds per world second for 100 stationary NPCs (`checklists.md`, cost table), and remote agents wouldn't reduce
  it.

**The one cheap step kept for later: the codec's contract names no property of its transport.**
- The frames, message kinds and size budgets are the contract.
- Each transport checks its own properties at start: the socket-buffer bound on a delivery (`sem_stimuli.md` §4.3)
  and fd passing belong to the local socketpair, not to the codec.
- The same codec serves the gateway channel (§3).
- A networked transport would need its own trust design: authentication, TLS, and what a remote agent home means for
  saves. It is not started.

## 8. What is built when

- **[now], `phase1/agents`:**
  - the placement table's format and both loaders, as registered gates with golden rejection files;
  - selection, slots, health and the outcome mapping in the lane;
  - the gateway process and its channel, with a **scripted transport** (canned replies, delays and failures, chosen
    by the test);
  - the provenance type;
  - the cache key and entry changes, in the cache's format;
  - the consent check and the guest gate test;
  - the meters.

  No test makes a network call (CLAUDE.md, "Tests are deterministic and fast").
- **[Phase 4]:**
  - Maxim's three backends in the gateway, each tested against a fake server on loopback that reproduces their
    failure modes, the empty reply among them;
  - credential resolution;
  - prices;
  - the disclosure UI;
  - whether the host starts the local model server.
- **The tests to write** go to `checklists.md` under the lane's model (moved there from this part, per the
  contract rule).

## 9. Upstream (roadmap Phase 3)

I searched Maxim `origin/main` 043eab8f for the terms "empty content", `content=""`, "deadline", "gateway retries",
"async router" and "multi-peer". I read `docs/architecture/llm_routing.md`, `docs/plans/archive/llm_path_fast_failover.md`,
`docs/plans/deferred/llm_path_multi_peer_dispatch.md`, `docs/plans/overdrive_refactor_candidates.md` (B3) and
`docs/plans/http_deadline_1715.md` (which is about `fetch_url` only).

- **OD-I9 (an issue):**
  - the cloud backends return an empty `LLMResponse` instead of raising a typed `BackendError` (§1, fact 1);
  - `_OpenAIBackend`'s gateway retries are hard-coded at 4 (§1, fact 2).

  Maxim's own lesson asks for typed errors ("Backend failures raise typed exceptions, not return empty content",
  `llm_path_fast_failover.md:771`, *verified*), while `llm_routing.md` keeps the empty signal as the legacy path. The
  ask: typed errors on the cloud backends, and a configurable gateway retry budget, so a host can get one call, one
  outcome. Not in O29's subset.
- **OD-A23 (a question to cand. B3):**
  - B3 makes priority and a deadline fields of the request value, "which the host schedules";
  - the ask is whether the backends honour that deadline per call (`complete_with_usage` takes none, §1, fact 3), so
    that an overdue or cancelled call frees its slot.

  Not in O29's subset: until it lands, the gateway holds the slot until the call returns (§2.5).
- **No ask on the router.** Overdrive doesn't use it, so Maxim's deferred async router and multi-peer dispatch are
  not needed by Overdrive. That is worth telling Maxim when it ranks those plans.
- **OD-A14's wording changes:** the `PromptBudgeter` gets the role's envelope (§2.1), not the bound model's context
  size and tokenizer.

## 10. What this changes elsewhere (in this branch)

- `npcs_and_sem.md`:
  - §4.1: the model profile is per placement;
  - §4.8: the canonical request's model fields;
  - §6.1: the budgeter's envelope;
  - §6.2: the router sentence now points here.
  - O13's "the LLM gateway stays in the host" reads as "host-side" under O47; its text is unchanged.
- `boundaries.md`:
  - §5.3's response-cache row (the entry holds the provenance);
  - §6.3's rerun manifest;
  - §7.1's thinking lane (placement and the gateway).
- `checklists.md`: the lane's model block.
- `roadmap.md`: OD-I9, OD-A23, and OD-A14's wording.
- `architecture.md`: the diagram's "AgentPool" and the stale "neither the world nor an NPC waits for a thought".
- `lessons_maxim_in_games.md`: entry 29.

## 11. Open questions for the owner

None. P1–P3 were accepted as recommended on 2026-11-21 and are O47–O49 (§0).
