# Inference placement: where an NPC's model calls run (design, v2, 2026-11-21)

**Status:** DRAFT v2. It folds round 1 (`reviews/inference_placement/`, eight lenses on v1 at 04ab810), and the fold
table, with the author's claimed location for each finding, is `reviews/inference_placement/fold_round1.md`. A delta
round sets the statuses (O25). After that round the paper rounds stop: mechanism findings move to `phase1/agents`'
checklist, and contract blockers still fold (CLAUDE.md, "Review finds; it doesn't design").

**What it covers.** The host's thinking lane executes every model request an NPC makes (`npcs_and_sem.md` O6a, §4.4,
§6.2; `boundaries.md` §7.1). This part says **where** each request runs: on this machine, on another of the player's
machines, or on a cloud API such as Claude. It covers the selection contract, the processes that make the calls, the
outcome vocabulary and where each outcome goes, what each reply records, consent and credentials, and what placement
may change in the world. It builds no remote agents (§7).

**Sources:** Maxim `origin/main` at **043eab8f**, read with `git show`; line numbers are at that revision. Facts the
round-1 readers or the author checked against it are marked *verified*. The locked release is pymaxim 1.3.3. The LLM
spike (`research/llm_spike.md`).

**Tags:** **[now]** is built in `phase1/agents` against the scripted test double and a scripted transport.
**[Phase 4]** lands with real NPCs. **[later]** is named so the contract leaves room for it, and is not built.

## 0. Decisions (owner, 2026-11-21)

| # | Decision | Where |
|---|---|---|
| O46 | **The host's thinking lane owns placement.** It decides which model serves each request, by function, consent, health, capacity and budget. Maxim's `LLMRouter` is not built on the NPC path, and Maxim's backends are the transports. This argues against Maxim's recorded rule that placement "rides on `LLMRouter`" (§1.2), and the pushback is OD-A24 (§9). | §1, §2 |
| O47 | **The calls run in host-owned inference gateway processes, not in the world server.** O13's "the LLM gateway stays in the host" reads as host-side: the host decides, and its gateways call. | §3 |
| O48 | **Each function is pinned to its first eligible placement by default; `spill` is an opt-in per function.** | §2.4 |
| O49 | **A model on another of the player's machines counts as remote under O18.** | §5.1 |
| O50 | **No streaming until Maxim's backends can stream to their caller.** The gateway calls with `stream=False`, and the `chunk` kind stays reserved. The first word of a reply arrives with the whole reply, which is a Known gap with its number (§6.3). The ask is OD-A25 (§9). | §3.3, §6.3 |
| O51 | **Consent is per speaker and outlives the session.** An NPC holding words from a speaker who has not accepted a class is ineligible for that class until those words are purged from it (§5.1). | §5.1 |
| O52 | **O46 goes to Maxim as a pushback, with this design's evidence.** | §9 |
| O53 | **One gateway process per placement**, so each placement is its own fault boundary and a process the host can kill at a hard time limit. | §3 |

## 1. What Maxim offers, and what this pushes against

### 1.1 The infrastructure

Maxim moves inference, not agents. `maxim/peer/` sends a machine's model calls to a "leader" (llama.cpp behind an
auth proxy with one shared cluster key). The router gives each lane an ordered list of providers, each `LOCAL`,
`CLOUD` or `PEER` (`runtime/worker_pool.py:72`). `maxim/mesh/` is in-process only: its networked modules were deleted
on 2026-04-12 (`mesh/__init__.py`). Hivemind bundles (Phase 5's rumour) are unchanged here. *Verified.*

### 1.2 Maxim's placement rule, and why O46 departs from it

Maxim has already split capability from placement:
- `docs/plans/archive/lane_capability_placement_split.md`, shipped, makes the capability tier (`large`, `medium`,
  `small`) a property of the task, assigned by `FunctionRouter`, and makes placement a separate ordered axis
  (`ProviderPlacement`).
- Its recorded rule (`docs/agents/llm-routing.md`, the "Lane = capability tier" invariant): "Placement rides on
  `LLMRouter`'s existing `provider_priority`/`_try_provider` failover — NOT a new resolver (a second resolver
  re-introduces the multi-call hazard the one-HTTP-call invariant kills)." *Verified.*

Overdrive keeps Maxim's split and its vocabulary where it fits: a request names a **function**, `FunctionRouter`'s
term (§2.1). It departs on who resolves placement, for these reasons:
- **The router fails over inside one call.** It records which provider served (`router.py` `last_served_*`,
  `call_accounting.ServedCall`), but the caller didn't choose that provider and isn't told unless it asks. A host that
  books deadlines, slots, consent and spend per placement needs the choice to be its own.
- **The router reads process state:** an environment variable (`router.py:77`), its own `CostTracker` (`:201`), and
  an injected drain constraint.
- **A host can bound a call only by killing a process (§2.5),** and the router's failover loop runs inside the call.

The "multi-call hazard" Maxim names is what the lane avoids by construction: one dispatch is one backend call, and
retries are the lane's decision, made in the open (§2.6).

### 1.3 Backend facts the contract rests on

| # | Fact (043eab8f, *verified*) | Consequence here |
|---|---|---|
| F1 | No backend can stream to its caller. With `stream=True` each one collects the text and returns one `LLMResponse` (`anthropic_backend.py:473-480`, `openai_backend.py:547-559`, `maxim_peer_backend.py:987`), and `LLMBackend` has no callback or iterator. | O50 |
| F2 | The cloud backends return `LLMResponse(content="")` on a missing client, on shutdown, and after their retries are exhausted, for any exception (`anthropic_backend.py:223-241`, `:377`, `:384-409`; `openai_backend.py:358-360`, `:505`). Maxim's router treats empty content as failure (`llm_routing.md`, `_try_provider`). | `empty`, §2.6 |
| F3 | Streamed OpenAI calls return partial text as success when the stream breaks (`llm_routing.md:686`), leaving `stop_reason` empty (`openai_backend.py:559`). | `stream=False` (O50); `truncated`, §2.6 |
| F4 | Timeouts bound each socket read, not the whole call (`utils/http.py::TimeoutPolicy`). The cloud backends retry (`max_retries` 2, `capacity_max_retries` 6, about 90 s), `_OpenAIBackend` adds 4 hard-coded gateway retries (`:391`), and neither passes `max_retries` to its SDK client (`anthropic_backend.py:237`, `openai_backend.py:276-305`). That the SDKs retry by default is *unverified*. | the kill ceiling, §2.5 |
| F5 | The peer backend checks a per-context cancellation event before the call, after a non-streamed call returns, and between chunks (`maxim_peer_backend.py:566`, `:937`, `:1093`), and raises `BackendDown`. | cancel semantics, §2.5 |
| F6 | No backend takes a seed, top-p, top-k or per-call deadline (`backend_protocol.py:72-84`). | the cache is the only reproduction path (§4) |
| F7 | `BackendError` has seven subclasses (`types.py:146-270`). | §2.6's table |
| F8 | The Anthropic backend logs the tokens it writes to the prompt cache but leaves them out of `LLMResponse`, and its `uncached_input_tokens` subtracts cached tokens from a count that already excludes them (`anthropic_backend.py:546-571`). | spend, §5.5; OD-I9 |
| F9 | `utils/http.py` mounts proxies from `httpx`'s environment lookup (`:839-843`), and a proxied request "bypass[es] the connect-time address check (#921)" (owner decision 2026-09-28). On macOS that lookup falls back to System Settings' proxies when the environment is empty. | §5.3 |

## 2. The contract

### 2.1 Functions and envelopes **[now]**

- **A request names a function, never a model or a tier.** The function is the caller's *declared* need (Maxim's
  `FunctionSpec` name, such as `agent_inference`). It is never `FunctionRouter.resolve`'s result, because which tiers
  exist depends on the machine's hardware (`runtime/lane_models.py:412`, `detect_tiers`). Falling back to a smaller
  model is the lane's decision, made through the table. Asked of B1 as part of OD-A14 (§9).
- **The function vocabulary is closed,** and is whatever B1's request value ships, measured at OD-A14. Until then, the
  test double's functions stand in. The table must cover every function, and the loader refuses one it doesn't.
- **Each function has an envelope,** in Maxim's own terms:
  - `total_budget`;
  - `response_reserve`;
  - `token_counter`;
  - `thinking` (whether a reasoning budget is requested).

  These go to `PromptBudgeter(total_budget, response_reserve, token_counter, …)` (`agents/prompt_budgeter.py:73`,
  *verified*). A request's `max_tokens` is the smaller of `response_reserve` and `thought_budget.yaml`'s tokens per
  call. The loader refuses a thought budget above the reserve.
- **The envelope's identity is the digest of its canonical value** (`boundaries.md` §6.3's canonicalizer), never a
  number bumped by hand.
- **Token counters are a closed vocabulary.** Each is pure, runs in the worker with no model loaded and no network,
  and carries its implementation version in the envelope's identity. Maxim's lazy counter, which upgrades after a
  background load, is not one of them (`token_counter.py::_LazyTokenCounter`).
- **Every placement in a function must fit its envelope:** its context per slot must be at least `total_budget`, and
  it must honour `thinking`. Otherwise the loader refuses the table. A prompt rendered once therefore fits every
  placement, and moving a request to another placement needs no new render.
- **Envelopes reach the worker in its `load` frame** (`npcs_and_sem.md` §6.6), as a versioned field. They never go
  through the environment.
- **[later]** The table's key may widen from the function to function plus NPC tier, which is level of detail for
  thought. The tier comes from the roster, never from load.

### 2.2 Files and placements **[now: formats and loaders; Phase 4: real transports]**

Three files, each a registered gate (§3.5), each versioned and refuse-on-unknown:

| File | Read by | Holds | On a rerun |
|---|---|---|---|
| `data/agents/functions.yaml` (shipped) | host | functions, envelopes, each function's policy (`pinned` or `spill`) | in `data/agents/`, so a mismatch refuses (`boundaries.md` §6.3) |
| `placements.yaml` (shipped default in `data/placements/`, the player's in their config directory) | host | placements, each function's placement order | never read; recorded only (§4.3) |
| `endpoints.yaml` (shipped default beside it, the player's in their config directory) | **gateway only** | each placement's endpoint and credential reference | never read |

- **Who may change what.** The player's `placements.yaml` replaces the shipped one whole: there is no merge, so no
  precedence rule is needed. It may set `spill` on a function the shipped file marks `pinned`. Placement ids must be
  unique within the file, or the loader refuses it.
- **The per-user directory** is resolved by `maxim_overdrive.data` and injected. The engine has no default path, and
  tests pass `tmp_path`.
- **A placement:**

| Field | Meaning |
|---|---|
| `id` | `[a-z0-9_-]{1,32}`. The only form in which a placement appears in logs, meters, manifests and the cache. Players are told it is shared in bug reports. |
| `transport` | `openai_compatible`, `anthropic` or `maxim_peer`. |
| `egress` | `loopback`, `owner_lan` or `third_party`: a consent class (§5.1), not Maxim's `Origin` (a build path). |
| `model` | The declared model id, plus a declared weights digest for `loopback` and `owner_lan`. The digest is declared, not checked. |
| `context_per_slot` | Context length per server slot. For example, `llama-server -c 8192 -np 4` gives 2,048 tokens per slot. |
| `max_in_flight` | 1 to 16, no more than the server's real parallelism; at most 10 for `maxim_peer`, its HTTP pool (`utils/http.py:67`). |
| `server` | Optional group name. Placements sharing a `server` share its `max_in_flight`. |
| `call_ceiling_s` | The whole-call wall bound (§2.5). Host-only. |
| `price` | USD per million tokens of uncached input, cache reads, cache writes and output. Required for `third_party`. |
| `cleartext` | `owner_lan` only. Must be `true` to allow `http://` (§5.4). |

- **Local models are loopback servers** (llama.cpp's server, Ollama) via `openai_compatible`; in-process llama.cpp
  isn't thread-safe (`router.py:192`). The spike measured Ollama's native API, so this path is measured at §8.

### 2.3 Eligibility **[now]**

A placement is eligible for a request when all of these hold:
1. **Consent:** the session's present speakers allow its class, and so do the words the NPC holds (§5.1).
2. **Health:** it is not cooling down and its gateway is up (§2.7).
3. **Budget:** for `third_party`, the session's spend is below its cap (§5.5).
4. **Proxy:** a proxied gateway is treated as `third_party` (§5.3).

Fit is checked at load, so it is not part of this list.

### 2.4 Queues and selection **[now]; the law is swappable**

- **Each placement has its own queue, in deadline order.** When a slot frees, it goes to the earliest-due request
  that may use it:
  - **under `pinned` (O48)**, a request may use only the first eligible placement in its function's list;
  - **under `spill`**, it may use any eligible placement in the list, in list order.

  A full placement therefore never blocks a request whose placement has a free slot. That keeps the intent of
  `npcs_and_sem.md` §4.4 (dispatch by deadline) without making one queue head wait on another placement.
- **Placement is chosen when the slot is granted**, so health and consent are read at dispatch.
- **What `pinned` costs:** in a reviewer's queueing model on §4.5's numbers, about 1.03× effective dial pinned to
  one 2-slot placement against 1.34× spilling over two (`reviews/inference_placement/performance.md` S-4). It buys a
  warm prompt cache per NPC and capability that doesn't follow load; §8 meters the wait it adds.

### 2.5 Slots, bounds and cancel **[now]**

- **A slot is held from dispatch until its gateway replies, or until the host kills that gateway.** The host owns the
  slot count, and a reply frees exactly one slot (§3.4).
- **The whole-call bound is `call_ceiling_s`.** No transport bounds a whole call (F4), so the host kills a
  placement's gateway when any of its calls passes this ceiling. Every attempt on it then ends `failed(unreachable,
  host-killed)`, and its slots free. The gateway sets every retry count it can to zero (F4). Retries it can't switch
  off, such as `_OpenAIBackend`'s gateway retries, run inside the ceiling.
- **Cancel.** The host stops waiting at once and sends `cancel`.
  - On `maxim_peer`, the gateway sets the call's cancellation event (F5), and the call ends at its next check.
  - On the cloud transports, the call runs until it returns or the ceiling kills it.

  Either way the outcome is `cancelled`, never `unreachable` (§2.6). Abandoned output tokens are metered per
  placement.
- **The liveness ceiling starts when the request is enqueued,** not when it is dispatched. So a request waiting for a
  slot is bounded too, and past the ceiling it ends as `thought_failed(reason=timeout)` (`npcs_and_sem.md` §4.4).
- **The no-deadlock invariant is unchanged:** a slot is held only by a call in flight, never by an agent.

### 2.6 Outcomes, and where each goes **[now]**

**Classification is the gateway's** (it does): it turns each transport result into one outcome. **Decisions are the
lane's** (it decides): what each outcome does. Each outcome has an attribution:
- **placement:** it starts the placement's cooldown;
- **request:** it says nothing about the placement;
- **host:** our own fault, such as a gateway crash or our kill.

| Outcome | Produced from | Attr. | Retried? | Reaches `think` / the log | Cache entry |
|---|---|---|---|---|---|
| `ok` | content with a non-empty `stop_reason` other than a length stop, or empty content with a non-empty `stop_reason` (the model chose silence) | — | no | `complete(text)` | text |
| `truncated(length)` | `stop_reason` a length stop | request | no | `truncated(text, reason=length)` | text and reason |
| `truncated(stream_broken)` | content with an empty `stop_reason` (F3) | placement | no | `truncated(text, reason=stream_broken)` | text and reason |
| `cancelled` | host cancel, F5's `BackendDown` after our cancel | — | no | `cancelled(prefix)` | none (§4.2) |
| `failed(context_overflow)` | `BackendContextOverflow` | request | no | `thought_failed(reason=context_overflow)` | failure |
| `failed(refused)` | a provider refusal reported as such | request | no | `thought_failed(reason=refused)` | failure |
| `failed(empty)` | empty content and empty `stop_reason` (F2): **a stand-in until OD-I9**, marked in code when built | placement | yes | after retries: `thought_failed(reason=model_error)` | failure |
| `failed(unreachable)` | `BackendDown` not caused by our cancel, our kill, or a dead gateway | placement, or host after a kill or crash | yes | same | failure |
| `failed(overloaded)` | `BackendOverloaded` | placement | yes (§2.7) | same | failure |
| `failed(call_timeout)` | `BackendTimeout` | placement | yes (§2.7) | same | failure |
| `failed(auth)` | `BackendAuthFailed`, or an unresolved credential at `open` | placement | yes | same | failure |
| `failed(model_missing)` | `BackendModelMissing` | placement | yes | same | failure |
| `failed(inference_broken)` | `BackendInferenceBroken` | placement | yes | same | failure |

- **Retries** run under every latency policy, bounded by the liveness ceiling. A retry is a new attempt chosen by
  §2.4. This is a change from `npcs_and_sem.md` §1's "a timeout retries": it now covers every retried outcome in the
  table. Request-attributed outcomes are never retried.
- **Once speech has reached the world, a failure is never retried.** It ends the reply as `truncated(prefix,
  reason=transport)`. Under O50 nothing is delivered before a reply completes, so this can't happen yet. It is
  contract for when OD-A25 lands.
- **One closed list of `thought_failed` reasons**, which replaces `boundaries.md` §6.1's "budget, timeout, model
  error": `budget`, `timeout` (the liveness ceiling), `parse`, `reloaded`, `unavailable` (no eligible placement),
  `model_error`, `refused`, `context_overflow`. The attempt-level `call_timeout` is a different word on purpose.
- **Under `pinned`, which failures move a request to the next placement.** `overloaded` and `call_timeout` don't: the
  request waits for the same placement until the liveness ceiling, because those are load symptoms and moving would
  make capability follow load. Every other placement-attributed failure does move it.

### 2.7 Health **[now]; the law is swappable**

- **A placement-attributed outcome starts that placement's cooldown,** from `functions.yaml`'s table per outcome.
  Request-attributed and host-attributed outcomes don't.
- **After a cooldown, one probe dispatch goes first,** and full traffic resumes only when the probe succeeds.
- **A gateway that keeps failing to start** (§3.4) marks its placement down for the session, and the client is told
  (§5.6).

## 3. The inference gateways (O47, O53)

### 3.1 Where the code lives **[now]**

- **Package:** `engine.adapters.inference`, a new adapter in `boundaries.md` §2.2's adapters layer, beside
  `engine.adapters.agents`.
  - It is the only engine package besides `simcore.adapters.sem` (and, at Phase 4, the agent adapter's worker entry)
    that may import `maxim`.
  - The import contract `maxim-through-adapters` gains it by name.
  - Its Maxim surface is `maxim.models.language`'s backends and types, never `LLMRouter`'s methods.
  - Its row joins `boundaries.md` §8.1.
- **The host never imports it;** it spawns its entry module. The lane lives in `engine.host`, which imports no `maxim`.

### 3.2 Spawning **[now]**

- **One gateway per placement (O53),** spawned like a worker (`npcs_and_sem.md` §6.6): `spawn`, `-I`, an allowlisted
  environment, and a working directory at its home under the session. It is not latched, because it needs the network.
- **`HOME` and `XDG_*` are set to the gateway's home, never left unset.** An unset `HOME` falls back to the real one
  through the password database, which a round-1 reader ran and *verified*.
- **No `MAXIM_*`, `*_API_KEY`, `*_BASE_URL` or proxy variable passes.**
- **`LLMConfig` is built directly** from the gateway's own two files, never through `load_llm_config` or profiles.
- **Imports:**
  - Importing a backend loads more than it names: `maxim.models.language`'s package imports `LLMRouter`, and through
    it `llama_backend`, `cost_tracker`, `cloud_audit` and `cloud_redaction`. The peer backend imports
    `maxim.agents.llm_worker` at call time.
  - The allowlist is therefore the **transitive** module set, recorded at the build step against the locked pymaxim,
    and a test holds it.
  - A **no-effect test** holds what those modules may do: no file reads or writes outside the gateway's home, and no
    socket except to its placement's endpoint. A planted `~/.maxim/config/llm.json` under a test `HOME` must never
    be read.
- **It sends no NPC, actor or session ids:** `request_context=None`, and no context variable is set. A header test
  holds that.
- **Its stdout and stderr go to a gateway log under the session,** which is never bundled into bug reports.

### 3.3 The channel **[now]**

The worker codec's rules apply (`npcs_and_sem.md` §6.6): length-prefixed, versioned, closed-schema JSON, budgets
before allocation, nothing pickled. The kinds:

| Direction | Kinds |
|---|---|
| host → gateway | `open(placement)` (its transport settings only, with no function data), `dispatch(attempt_id, request)`, `cancel(attempt_id)`, `ping(n)`, `shutdown` |
| gateway → host | `ready` or `error(code)` (once, after `open`), `reply(attempt_id, outcome, text, reported)`, `pong(n)`, `chunk(attempt_id, seq, text)` (**reserved**, never sent under O50) |

**Rules (the binding contract):**
- `attempt_id` is `(gateway generation, sequence)`, so a reply from a dead gateway can never match a new attempt.
- Each accepted attempt gets **exactly one** `reply`.
- `cancel` of an attempt that is already finished is a no-op, not an error.
- A `reply` for an unknown, finished or foreign attempt, a second `reply`, or a malformed frame is a protocol error:
  that gateway is killed (§3.4).
- **The host stamps provenance** (§4.1): the placement id, transport, egress and declared model come from the host.
  The gateway supplies only the `reported` fields, and the host bounds them.
- **Each side reads on its own thread, which never blocks on a write,** and writes through a bounded outbox. The
  largest frame is bounded by the largest envelope.

### 3.4 Lifecycle **[now]**

- **Hung** means either of two things:
  - a call past `call_ceiling_s`;
  - no `pong` within `ping_ceiling_s` while an attempt is in flight.

  Either one kills that placement's gateway, and no other placement's.
- **Its attempts end** `failed(unreachable)`, attributed to the host. The old channel is closed before they are
  declared, so no late frame can be read.
- **Restarts** back off exponentially up to a cap, each one metered. After `max_restarts` in a window, the placement is
  down for the session (§2.7).
- **`shutdown`** is a bounded wait, then a kill. A gateway exits on EOF from the host (with `os._exit`), so an orphan
  never keeps spending cloud tokens.

### 3.5 Gates **[now]**

New rows for `boundaries.md` §5.3's registry, each with golden rejection files:
- the gateway channel, in both directions;
- `functions.yaml`;
- both `placements.yaml` files;
- both `endpoints.yaml` files (read in the gateway);
- the credential store (read in the gateway; Phase 4 chooses the OS keychain or a file, but either one is a gate).

Every refusal that names a placement carries its id, never an endpoint.

## 4. Provenance, the cache, the manifest and saves

### 4.1 Provenance **[now]**

Every reply carries a frozen, versioned provenance value with golden fixtures:
- **host-stamped:** placement id, transport, egress, declared model and digest, outcome, attempt count;
- **gateway-reported, bounded:** the model and provider as reported (null where a transport only echoes the request,
  as `_OpenAIBackend` does), and token counts for uncached input, cache reads, cache writes and output, each a whole
  number from 0 to 10⁷. Strings are at most 128 characters, with no control or format characters.

Provenance holds no wall time, cost, endpoint or credential, and it never reaches cognition.

Maxim's hybrid line asks for the same record (`hybrid_arbitration.md:97-98`).

### 4.2 The cache **[now; the format lands with the cache]**

- **The canonical request drops the model and its digest.** It carries the function and its envelope's identity
  (§2.1). Placement depends on load and health, which aren't the agent's, so it can't be in the key.
- **One entry per request occurrence,** and only for the final outcome (§2.6). An entry holds the raw output (the
  `reply` text), the canonical request and its provenance. Attempts and placements live only in provenance.
  `cancelled` writes nothing, because the cancel itself is a logged world event.
- **Three modes, and no fourth.**
  - **Live play writes and never reads.** Test: a live session with a poisoned entry for its first request dispatches
    anyway.
  - **A rerun reads and never dispatches,** and a miss is a loud error.
  - **Replay never opens the cache.**

  There is no read-through mode, so paired experiments whose arms differ in placement or model can't be paired
  through the cache. They pair only on substrate-only arms (`npcs_and_sem.md` §4.8).
- **The write point** is when the reply arrives.
- **A reply that has arrived but not yet landed** is held in the host-owned header with its text, and saved with it.
  A load resumes from the held text and never dispatches again (`npcs_and_sem.md` §6.6, resume equivalence).
- **Branches.** Each log segment (O45) owns its cache. A load opens a new segment whose cache starts as a copy of its
  parent's, so two branches from one save never write each other's entries.

### 4.3 The rerun manifest **[with the cache]**

- **`functions.yaml`'s digest and the envelopes refuse on mismatch,** like the rest of `data/agents/`. A rerun spawns
  its workers with the recorded envelopes, and never loads or reads placements or endpoints.
- **The placement table's digest is recorded per log segment and reported, never refused,** because a rerun never
  dispatches.
- **The ledger record pins** the functions digest, the placement digest per segment, and the fact that experiment
  functions are single-placement with failover off (`boundaries.md` §8.4). Any arm that mixes models is a declared
  arm, never an accident.

## 5. Consent, egress and credentials

### 5.1 Consent, per speaker (O18, O49, O51) **[now: the rule; Phase 4: the disclosure UI]**

- **Consent is recorded per speaker and per class,** saved with the save. With guests present:
  - only `loopback` is eligible unless every present guest has accepted the class (and, for `third_party`, the named
    provider);
  - `owner_lan` counts as remote (O49).
- **Words outlive sessions.** Speech is a world input the host delivers, so the host knows who heard it. An NPC that
  has perceived words from a speaker who has not accepted a class is ineligible for that class until O17's purge has
  removed that speaker's words from it.
  - **Taint passes through speech:** an NPC that hears an NPC holding such words holds them too.
  - The rule is host-computed and conservative. It never relies on the worker's own account of a prompt.
- **Single-player, with no foreign words held:**
  - `owner_lan` is eligible once the player configures it;
  - `third_party` needs both an explicit opt-in and a spending cap.

### 5.2 What each class can promise **[now: checks; Known gaps stated]**

- **`loopback`:** the endpoint is a literal 127.0.0.1 or ::1. The gateway checks this, because the host never sees
  endpoints (§2.2).
  - It promises only the first hop. A local server that forwards elsewhere, such as a cloud-backed proxy or a cloud
    model tag, is out of our sight.
  - The disclosure text says so, and so does a Known gap.
- **`owner_lan`:** the gateway refuses an endpoint whose dialled address is not private, link-local or CGNAT
  (100.64.0.0/10). A rented cloud machine can't be labelled as the player's own.
- **`third_party`:** the provider is the one named in the file. Provenance can attest it only where the transport
  reports it (§4.1).

### 5.3 Proxies (F9) **[now]**

- **The problem.** Maxim's transports honour proxies, including macOS System Settings proxies when the environment is
  empty, and a proxy dials on the gateway's behalf.
- **The check.** At start, each gateway reads `urllib.request.getproxies()` in its own environment and reports it in
  `ready`.
- **What a proxy changes.** A proxied gateway's placement is treated as `third_party` for consent: refused with
  guests, and disclosed in single-player.
- **The real fix** is a way to switch proxies off per backend, which is OD-I10 (§9).

### 5.4 Credentials, endpoints and transport security **[now: references; Phase 4: resolution]**

- **The host holds neither endpoints nor key material.** Both live in `endpoints.yaml` and the credential store,
  which only the gateway reads.
- **Keys go to Maxim's backends as already-resolved entries**, so no environment variable is consulted:
  - for `anthropic` and `openai_compatible`, through `types.py::resolved_entry_key`;
  - for `maxim_peer`, as the entry's literal `api_key` (`maxim_peer_backend.py:791-802`).
- **An unresolved reference** fails at `open` as `failed(auth)`.
- **`owner_lan` over `http://` needs `cleartext: true`.** The guest disclosure then says the traffic is readable on
  the network, and that the cluster key crosses it in the clear (a Known gap).
- **No redaction is applied.** Consent is the control. Guest text still passes `engine.text.player_text`, which
  refuses controls and format characters but removes no names.

### 5.5 Spend **[now: the meter and cap; Phase 4: prices]**

- **Spend is the provenance's four token counts times `price`'s four rates.** Until OD-I9, the Anthropic counts are
  wrong (F8): cache writes are missing. So spend on cache-heavy Anthropic calls is undercounted. The cap is a Known
  gap until then, with that number stated by the build step's fake-server test.
- **Abandoned and killed calls count** at their dispatched input plus `response_reserve`, the worst case, because
  their real counts never arrive.
- **The cap is soft** by at most each placement's `max_in_flight` calls in flight. Reaching it makes `third_party`
  ineligible.
- **Spend never reaches cognition** (`npcs_and_sem.md` §4.6).

### 5.6 What the client is told

One host status kind, `inference_status`, carries:
- the spend cap reached;
- a placement down for the session;
- a proxy found;
- the guest disclosure state.

It joins the protocol's host-status vocabulary beside dilation by cause (`npcs_and_sem.md` §5.4), and is added to
`tile_and_client.md` §3's message list at `phase1/protocol`. A missing local model with guests present refuses the
session at start (`checklists.md`); later, an unavailable function ends its thoughts as `unavailable`.

## 6. Time and capability: what placement may change

### 6.1 Placement changes wall time only

- **A placement changes wall latency.** That changes only dilation, or lateness under floor-holding (O4, O11, O16).
- **It never changes a thought's modelled time, its kind or its landing tick.** `think` resumes at the modelled
  landing tick whichever model answered (`npcs_and_sem.md` §6.6).

### 6.2 What may differ by placement, as OPEN divergences **[stated]**

- **Model capability.** The outcome class is not promised across model profiles (`npcs_and_sem.md` §4.1), and under
  placement the profile can change **within one NPC's life**:
  - on health, through failover;
  - on budget, when the spend cap is reached;
  - on consent, when a guest joins or a foreign speaker's words are held.

  `pinned` bounds this to failure, budget and consent: load alone never moves a pinned function (§2.6). A per-NPC
  meter counts changes of placement within a function.
- **Fatigue.** A weaker model can need more PFC cycles, and their modelled cost loads mental fatigue
  (`npcs_and_sem.md` §4.2, §4.6). So a change of placement can change how fast an NPC tires. This is OPEN.
- **Observed latency** in `learned_hold_window.md`'s waiting cost now varies per reply (`npcs_and_sem.md` §5.1).

### 6.3 The cost of O50

**The first word arrives with the whole reply.** On the spike's numbers that is a median of about 1.29 s at one
call in flight (0.32 s if streamed), and 1.46 s at two. Both are past O11a's account (600–700 ms) and its yield
(about 1 s). §4.5's lever 3 is unavailable until OD-A25. Under dilate, P2 speech pays L(full), not L(first token).

### 6.4 The invariant tests **[now]**, written in the checklist

- **Under `dilate`, the canonical requests are byte-identical** across placement mixes, seeded latencies and a
  scripted failure schedule (failovers, cooldowns, a spend cap crossed). The double echoes a digest of its whole
  input.
- **A schema test:** no provenance field crosses `AgentPort` or the worker codec.
- **A negative control:** a plant that passes the placement id to the agent turns the test red.
- **One injected host wall clock,** the named host-only timeout module (`npcs_and_sem.md` §1), drives the lane,
  cooldowns, ceilings and gateway supervision. The scripted transport is advanced by test messages, never by sleeping.

## 7. Agents stay on this machine; the codec stays transport-neutral

- **The barrier's cost.** The barrier parks every agent each tick (`npcs_and_sem.md` §6.3). Its round trips cost
  0.2–0.8 wall seconds per second for 20 NPCs at 200 ticks per wall second (20×), locally (§6.6 there).
- **What a LAN would cost.** At a LAN round trip of about 1 ms (*to measure*), the barrier would cost about 4 s per
  second with parks sent one after another, or about 0.2 s per second if all parks are sent at once and awaited
  together.
- **The heavy compute already moves:** inference, at 0.3–1.4 s to first token. The derived host sensing cost, about
  2.5–2.9 wall seconds per world second for 100 NPCs (`checklists.md`, derived), would not move.
- **So remote agents are not designed.** The codec's contract names no transport property, and each transport checks
  its own at start (the socket-buffer bound in `sem_stimuli.md` §4.3 is the socketpair's). A networked transport would
  need its own trust design.

## 8. What is built when, and what it is measured by

- **[now], `phase1/agents`:**
  - the three file formats and their gates;
  - per-placement queues, slots, selection, health and the injected clock;
  - `engine.adapters.inference` with a scripted transport;
  - the channel and its rules;
  - kill and restart;
  - the outcome table;
  - provenance;
  - the cache changes;
  - per-speaker consent and taint;
  - the proxy check;
  - the meters.

  No test makes a network call.
- **[Phase 4]:**
  - Maxim's three backends behind the gateway, each tested against a loopback fake server that reproduces F2–F5 and
    F8, and N concurrent calls with an injected auth failure. The instance model (one backend per slot, or one call
    per process where a transport can't take concurrent calls) is chosen by that test;
  - credential resolution;
  - prices;
  - the disclosure UI;
  - whether the host starts the local server.
- **B5 rows** (added to `docs/standards_backlog.md` in this branch):
  - per placement: time to first token and to the whole reply, slot wait, wait while another eligible placement was
    free, failures by outcome, abandoned tokens, spend, prompt-cache hit ratio and prefill tokens per call;
  - gateways: start time, restarts and memory;
  - the shared machine: the channel round trip, host CPU per reply, and turn time and time to first token with a
    loopback model under physics load at the max profile, with one memory budget for weights, KV cache and pinned
    frames.
- **The tests go to `checklists.md`** under the lane's model.

## 9. Upstream (roadmap Phase 3)

Searched at 043eab8f: "placement", `FunctionRouter`, "capability tier", `ProviderPlacement`, "empty content",
"deadline", "gateway retries", "stream", "callback", "proxy", "async router", "multi-peer". Read: both routing
documents, `lane_capability_placement_split.md`, `llm_path_fast_failover.md`, the deferred multi-peer, async-router and
pecking-order plans, the candidates' B1 and B3, `hybrid_arbitration.md`, `http_deadline_1715.md`.

| Id | Kind | Ask |
|---|---|---|
| OD-A24 | pushback against `llm-routing.md`'s rule that placement "rides on `LLMRouter`" (O52) | An embedder that owns scheduling resolves placement outside `LLMRouter`, and calls one backend per dispatch. The evidence is §1.2 and §2.5. The ask is that the invariant allow it, with the one-call-per-dispatch property kept. |
| OD-I9 | pushback against `llm_path_fast_failover.md:43` and `:769` (cloud retries by design) and `llm_routing.md`'s empty-content legacy path | Typed `BackendError`s from the cloud backends. Configurable retry budgets, including the SDK clients' and the gateway retries, with defaults unchanged. Complete usage counts, including cache writes (F8). |
| OD-A25 | new ask | A streaming surface on `LLMBackend`, such as a chunk sink on `complete_with_usage`. Searched: none exists (F1). It lifts O50. |
| OD-I10 | pushback against the 2026-09-28 "the proxy wins for operator paths" decision, for embedders | A per-backend way to switch proxies off, and an `http_client` the Anthropic backend accepts (F9). |
| OD-A23 | question to cand. B1's cancel clause ("ride on `utils/cancellation`") | Does the abandonable path free the transport, or only the caller? This is not a backend capability (OD-A14 says so). |
| OD-A14 | amended | The request value carries the declared function name and the envelope. It is cut at `_complete_text` without building an `LLMRouter` in the worker. Hardware tier detection is kept out of the embedded worker. |

Overdrive needs neither Maxim's async router nor multi-peer dispatch; Maxim should hear that when ranking them.

## 10. What this changes elsewhere (in this branch)

`npcs_and_sem.md` §4.1, §4.8, §6.1, §6.2, §6.3, §6.6, §12.2; `boundaries.md` §5.3, §6.1, §6.3, §7.1, §8.1, §8.4;
`embeddable_agent_DRAFT.md`; `checklists.md`; `standards_backlog.md` B5; `roadmap.md` (OD-A14, OD-A23–A25, OD-I9,
OD-I10); `architecture.md`; lessons entry 29. Later: `pyproject.toml`'s import contract gains the package
(`phase1/agents`), and `tile_and_client.md` §3 gains `inference_status` (`phase1/protocol`).

## 11. Open questions for the owner

None. O46–O53 are decided, and the owner kept this fold's two defaults (2026-11-21):
- `owner_lan` must be a private, link-local or CGNAT address, and `http://` needs `cleartext: true` (§5.2, §5.4);
- under `pinned`, load failures (`overloaded`, `call_timeout`) wait on the same placement instead of failing over
  (§2.6).
