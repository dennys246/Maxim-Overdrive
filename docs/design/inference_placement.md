# Inference placement: where an NPC's model calls run (design, v3, 2026-11-21)

**Status:** DRAFT v3. It folds the delta round (`reviews/inference_placement/delta_*.md`, eight lenses on v2), and
its fold table, with the author's claim for each finding, is `reviews/inference_placement/fold_delta.md`. The paper
rounds stop here (CLAUDE.md, "Review finds; it doesn't design"; owner, 2026-11-21). A short delta check confirms the
folds, and mechanism findings are deferred, each with its trigger, to `phase1/agents`' checklist.

**What it owns** (one owner per contract, B36):
- functions and their envelopes;
- `functions.yaml` and `placements.yaml` (`endpoints.yaml` is IG's);
- eligibility, selection, slots and health;
- the outcome vocabulary and where each outcome goes: the `thought_failed` reasons and the `truncated` reasons;
- provenance;
- the **response cache**, moved here from `npcs_and_sem.md` §4.8;
- the inference items of the rerun manifest;
- what placement may change in the world.

The gateway processes, their channel, per-transport classification, consent and egress are owned by
`inference_gateway.md` (IG below).

**Sources:** Maxim `origin/main` at **043eab8f**, read with `git show`, with line numbers at that revision. *Verified*
means a round's reader or the author read the line there. The locked release is pymaxim 1.3.3.

**Tags:**
- **[now]:** `phase1/agents`, against the scripted test double and a scripted transport.
- **[Phase 4]:** real NPCs.
- **[later]:** named so the contract leaves room for it, and not built.

## 0. Decisions (owner, 2026-11-21)

This document's decisions (11 rulings) are kept as records, with their dates, owner sections and status, in `decisions/inference_placement.md`.

## 1. What Maxim offers, and what this pushes against

### 1.1 The infrastructure

Maxim moves inference, not agents:
- `maxim/peer/` sends a machine's model calls to a leader.
- The router gives each lane an ordered list of providers, each `LOCAL`, `CLOUD` or `PEER`
  (`runtime/worker_pool.py:72`).
- `maxim/mesh/` runs in one process only: its networked modules were deleted on 2026-04-12 (`mesh/__init__.py`).
- Hivemind bundles, which Phase 5's rumour mechanic uses, are unchanged here.

*Verified.*

### 1.2 Maxim's placement rule, and why O46 departs from it

**What Maxim has.** Maxim splits capability from placement:
- `archive/lane_capability_placement_split.md` makes a function's tier a property of the task, assigned by
  `FunctionRouter`.
- Its recorded rule (`docs/agents/llm-routing.md:73`) is that placement "rides on `LLMRouter`'s existing
  `provider_priority`/`_try_provider` failover — NOT a new resolver". *Verified.*

**What Overdrive keeps.** The split, and the term **function** (§2.1).

**Where it departs: who resolves placement.**
- **Failover happens inside one call.** The router fails over within a call. Its `last_used_*` properties
  (`router.py:285-316`) and `call_accounting.ServedCall` record who served, but the caller didn't choose that
  provider.
- **The router reads process state.** `router.py:77` reads an environment variable, and `:201` builds its own
  `CostTracker`.
- **A host can bound a call only by killing a process** (§2.5), and the router's failover runs inside the call.

**The hazard Maxim names is avoided by construction.** One dispatch is one backend call, and retries are the lane's
decision.

### 1.3 Backend facts the contract rests on (043eab8f, *verified*)

| # | Fact | Consequence |
|---|---|---|
| F1 | No backend streams to its caller. Each collects the text and returns one `LLMResponse` (`anthropic_backend.py:473-480`, `openai_backend.py:547-559`, `maxim_peer_backend.py:987`), and Maxim's B1 plans "the token iterator … later" (`overdrive_refactor_candidates.md:268-270`). | O50, OD-A25 |
| F2 | The cloud backends return `LLMResponse(content="")` on a missing key or client, on shutdown and after exhausted retries (`anthropic_backend.py:377`, `:384-409`; `openai_backend.py:358-360`, `:505`). A missing SDK package raises instead (`:230`). Maxim's own lesson says backends should raise typed errors (`llm_path_fast_failover.md:771`). | IG §5, OD-I9 |
| F3 | A broken OpenAI stream now raises into the retry loop (`openai_backend.py:547-627`, `:442`). `llm_routing.md:686`'s "partial text" is stale. This is moot under O50. | — |
| F4 | Timeouts bound each socket read, not a whole call (`utils/http.py::TimeoutPolicy`). The backends retry inside a call, `_OpenAIBackend` has 4 hard-coded gateway retries (`:391`), and the SDK clients retry by default, which Maxim's own comment at `openai_backend.py:450` confirms. | §2.5, OD-I9 |
| F5 | Under `stream=False`, the peer backend checks cancellation only before the call and after it returns (`:566`, `:937`). So no transport frees a slot early on cancel. | §2.5 |
| F6 | No backend takes a seed, top-p, top-k or per-call deadline (`backend_protocol.py:72-84`). | §4 |
| F7 | `BackendError` has seven subclasses (`types.py:146-270`), and none of them is a refusal. | IG §5 |
| F8 | The Anthropic backend logs the tokens it writes to the prompt cache but leaves them out of `LLMResponse` (`anthropic_backend.py:416-422`, `:546-571`). | IG §8, OD-I9 |
| F9 | Proxies are mounted from httpx's environment lookup (`utils/http.py:839-843`; "the proxy wins for operator paths", 2026-09-28). `NO_PROXY=*` turns this off (IG §2), and Maxim also has `HTTPEndpoint.strict_address_check` (`:228`, `:875-881`). | IG §2, OD-I10 |

## 2. The contract

### 2.1 Functions and envelopes **[now]**

- **A request names a function, never a model or a tier.** The function is the caller's *declared* need (Maxim's
  `FunctionSpec.name`). It is never `FunctionRouter.resolve`'s result, which depends on hardware
  (`runtime/lane_models.py:412`).
  - No Maxim call site declares a function today: `submit_function` and `get_backend_for_function` have no callers,
    and `_complete_text` takes no function. So the field is a new ask (OD-A14).
  - Until it lands, the test double's functions stand in.
  - The vocabulary is closed, the table must cover every function, and the loader refuses one it doesn't.
- **Model requests carry a deadline, not a priority.** The host stamps the deadline from the request's kind, outside
  the cache key (§4.2).
- **A function keeps its spec's restriction on degrading.** Each function declares its tier, and each placement
  declares the tier of its model. A function whose spec has an empty fallback (`agent_inference`: "never degrade",
  `function_router.py:57-58`) may list only placements of its own tier, and the loader checks this.
- **Each function's envelope**, in Maxim's terms (`PromptBudgeter(total_budget, response_reserve, token_counter, …)`,
  `prompt_budgeter.py:73`):
  - `total_budget`;
  - `response_reserve`;
  - `token_counter`;
  - `thinking`, a token budget or none.

  A request's `max_tokens` is the smaller of `response_reserve` and `thought_budget.yaml`'s tokens per call, and the
  loader refuses a budget above the reserve. The host sends the envelope's `thinking`; the agent's own value per call
  is ignored on the embedded path. The canonical request records what was sent.
- **The envelope's identity** is the digest of its canonical value (`boundaries.md` §6.3's canonicalizer).
- **Token counters are a closed vocabulary.** Each is pure, runs in the worker with no model loaded, and carries its
  version in the envelope's identity. Each also declares the tokenizer families it is an upper bound for. A placement
  whose model family isn't covered by its function's counter is refused at load. Maxim's lazy counter is not in the
  vocabulary.
- **Fit.** Each placement's `context_per_slot` must be at least `total_budget`, so a prompt rendered once fits every
  placement in its function.
- **Envelopes reach the worker in its `load` frame.** Every spawn begins with `load`; a fresh NPC's carries an empty
  home (`npcs_and_sem.md` §6.6).
- **[later]** The table's key may widen to function plus NPC tier. That tier comes from the roster, never from load.

### 2.2 Files **[now: formats and loaders; Phase 4: real transports]**

Each file is versioned, refuse-on-unknown, and a registered gate (IG §9).

| File | Read by | Holds | On a rerun |
|---|---|---|---|
| `data/agents/functions.yaml` (shipped) | host | functions, tiers, envelopes | refuses on mismatch (`data/agents/`) |
| `placements.yaml` (shipped default in `data/placements/`; the player's replaces it whole) | host | placements; each function's ordered list and policy (`single`, `pinned` or `spill`); `servers`; the `health` block (IG §4, §2.7) | recorded per segment, never read |
| `endpoints.yaml` | gateway only | owned by IG §8 | never read |

**A placement's fields:**

| Field | Meaning |
|---|---|
| `id` | `[a-z0-9_-]{1,32}`. It is the only form in which a placement appears outside the gateway, and players are told it is shared in bug reports. |
| `transport` | `openai_compatible`, `anthropic` or `maxim_peer`. |
| `egress` | `loopback`, `owner_lan` or `third_party`: a consent class (IG §6), not Maxim's `Origin`. |
| `model` and `tier` | The declared model id and its tier. For `loopback` and `owner_lan`, also a declared weights digest, which is not checked. |
| `context_per_slot` | Context length per server slot. |
| `max_in_flight` | 1 to 16, and at most 10 on `maxim_peer` (its HTTP pool, `utils/http.py:67`). A placement in a `server` group declares none of its own. |
| `server` | Optional. Names a `servers` entry, which owns one `max_in_flight` for every placement that shares the server. |
| `call_ceiling_s` | The whole-call wall bound (§2.5). Refused at load if it isn't below the smallest liveness ceiling in `thought_budget.yaml`. |
| `price` | USD per million tokens of uncached input, cache reads, cache writes and output. Required for `third_party`. |
| `cleartext` | `owner_lan` only (IG §7). |

**Local models are loopback servers** (llama.cpp's server, Ollama), reached through `openai_compatible`. In-process
llama.cpp isn't thread-safe (`router.py:192`). The spike measured Ollama's native API, not this path, so this path is
measured at §8.

### 2.3 Eligibility **[now]**

A placement is eligible for a request when all of these hold:
1. **Consent:** the session's present speakers allow its class, and so does the NPC's taint (IG §6).
2. **Not down:** it isn't in a placement cooldown (§2.7) and isn't down for the session (IG §4).
3. **Budget:** for `third_party`, the session's spend is below its cap (IG §8).

A placement under a **load delay** (§2.7) stays eligible. Fit, tiers and ranges are checked at load.

### 2.4 Queues and selection **[now]; the law is swappable**

- **One deadline queue per placement**, and one per `server` group across its placements' queues. A freed slot goes
  to the earliest-due request that may use it:
  - **`single`:** only the first placement in the list, ever. Experiment functions use `single` (§4.3).
  - **`pinned`** (O48): the first eligible placement in the list.
  - **`spill`:** any eligible placement in the list, and the first in list order when several have a free slot at
    once.
- **The placement is chosen when the slot is granted.**
- **When no candidate is eligible,** under every policy: if any candidate is ineligible only by a cooldown, the
  request waits for it, bounded by the liveness ceiling; otherwise (consent, budget, down) it ends at once as
  `unavailable`.
- **What `pinned` costs.** In a round-1 reader's queueing model on §4.5's numbers, the effective dial is about 1.03×
  pinned to one 2-slot placement, against 1.34× when spilling over two (`reviews/inference_placement/performance.md`
  S-4). `pinned` buys a warm prompt cache per NPC and capability that doesn't follow load. §8 meters the wait it adds.

### 2.5 Slots, bounds and cancel **[now]**

- **A slot is held from dispatch until its attempt finishes** (IG §3: its one `reply`, or its gateway's death). The
  host owns the slot count.
- **The liveness ceiling** (`thought_budget.yaml`, per kind) starts when the request is enqueued. Past it, the
  request ends as `thought_failed(reason=timeout)`, and the host sends `cancel`.
- **The whole-call bound** is `call_ceiling_s`. No transport bounds a whole call (F4), so the host kills the gateway
  when any call on it passes the bound.
  - The call that passed the bound ends as `failed(call_timeout)`: placement-attributed, and a load outcome (§2.7).
  - The other attempts on that gateway end as `failed(unreachable)`: host-attributed collateral, retried, with no
    cooldown.
  - The gateway sets every retry count it can to zero.
- **Cancel** stops the lane waiting at once. Under O50 no transport frees the slot early (F5), so the slot is held
  until the `reply` or a kill. Abandoned output tokens are metered.
- **The no-deadlock invariant is unchanged:** a slot is held only by a call in flight, never by an agent.

### 2.6 Outcomes, and where each goes **[now]**

The gateway classifies each backend result (IG §5), and the lane decides what it does.

| Outcome | Kind | Retried? | Reaches the agent | Log record | Cache |
|---|---|---|---|---|---|
| `ok` | — | no | `complete(text)` | none | text |
| `truncated(length)` | request | no | `truncated(prefix, reason=length)` | none | text and reason |
| `cancelled` | — | no | `cancelled(prefix)` | `thought_cancelled` (already logged) | §4.2 |
| `failed(context_overflow)` | request | no | `cancelled(prefix)` | `thought_failed(context_overflow)` | failure |
| `failed(refused)` | request | no | same | `thought_failed(refused)` | failure |
| `failed(overloaded)`, `failed(call_timeout)` | placement: **load** | yes, same placement under `pinned` (§2.7) | after the ceiling: same | `thought_failed(timeout)` | failure |
| `failed(empty)` | placement: **load** on `openai_compatible` and `anthropic`, **fault** on `maxim_peer` (§2.7) | yes | after retries: same | `thought_failed(model_error)` | failure |
| `failed(unreachable)` | placement: fault, including a gateway crash during the attempt; host only when collateral of a kill | yes | same | `thought_failed(model_error)` | failure |
| `failed(auth)`, `failed(model_missing)`, `failed(inference_broken)`, `failed(oversized)`, `failed(unclassified)` | placement: fault | yes | same | `thought_failed(model_error)` | failure |

- **What the agent sees.** It sees only the `Reply` variants, as `npcs_and_sem.md` §6.6 defines them:
  - `prefix` is the speech already delivered to the world;
  - a failed thought resumes the agent as `cancelled(prefix)`, as an interruption does (`npcs_and_sem.md` §4.7);
  - no `thought_failed` reason, outcome, attribution or placement ever crosses `AgentPort` (§6.4's schema test).
- **Delivery under O50.** A reply is held until its landing tick. At that tick the host validates its speech field
  and delivers what validates (`npcs_and_sem.md` §5.2–§5.3). Then `think` resumes with:
  - `complete(text)` for `ok` whose speech validated whole;
  - `truncated(prefix, reason=validation)` when the speech fails validation partway (`npcs_and_sem.md` §6.6);
  - `truncated(prefix, reason=length)` for a length cut.

  `prefix` is always what was delivered.

  Text beyond the delivered speech never reaches cognition (TB3-S5).
<!-- contract: thought_failed.reasons: budget timeout parse reloaded unavailable model_error refused context_overflow -->
- **One closed list of `thought_failed` reasons**, owned here: `budget`, `timeout`, `parse`, `reloaded`, `unavailable`,
  `model_error`, `refused`, `context_overflow`. `call_timeout` is an attempt outcome, not a reason. A thought's tier
  is decided by its final outcome only: attempts that a later attempt recovered flag nothing.
<!-- contract: truncated.reasons: validation length transport -->
- **One closed list of `truncated` reasons**, owned here:
  - `validation` (the guest-text gate, `npcs_and_sem.md` §6.6);
  - `length`;
  - `transport`, reserved for when streaming lands. Under OD-A25, a failure after delivered speech ends as
    `truncated(prefix, reason=transport)` and is never retried.
- **Retries** run under every latency policy, bounded by the liveness ceiling, as new attempts. This replaces
  `npcs_and_sem.md` §1's "a timeout retries". Request-attributed outcomes never retry. Outcome names are
  lane-internal; receipt kinds (`sem_stimuli.md` §6.2 for agents, `tile_and_client.md` §3.3 on the wire) are a separate
  vocabulary.

### 2.7 Health **[now]; the law is swappable**

Its tunables are in `placements.yaml`'s `health` block, recorded and never refused on a rerun, because a rerun never
dispatches.

- **A load outcome** (`overloaded`, `call_timeout`, and `empty` on the cloud and OpenAI-compatible transports) starts
  a **load delay** on the placement. The placement stays eligible, and its queue simply waits.
  - Under `pinned` and `single`, requests keep waiting for it until the liveness ceiling, so load never moves a
    pinned function (O48).
  - Under `spill`, other placements may take requests in list order.
- **A fault outcome** starts a **cooldown**, and a cooling placement is ineligible. After the cooldown, one probe
  request goes first. The probe is re-issued until one ends in `ok` or in a fault. Outcomes attributed to the
  request or the host change nothing.
- **Down for the session** comes only from failed starts (IG §4). Kills and start timeouts never count.
- **Until OD-I9, the cloud and OpenAI-compatible transports can't tell load from failure** (F2). A server that is
  hard down therefore looks like load: pinned requests time out instead of failing over. That is a Known gap (§6.3).

## 3. The gateway

Owned by `inference_gateway.md`: package and layer, spawning, environment, channel, lifecycle, classification,
consent, egress, credentials and spend.

## 4. Provenance, the response cache, and the manifest

### 4.1 Provenance **[now]**

A frozen, versioned value with golden fixtures:
- **host-stamped:** placement id, transport, egress, declared model, tier and digest, outcome, attempt count;
- **reported by the gateway, bounded by the host:** model and provider, null where the transport only echoes the
  configuration (both cloud backends do); four token counts, each a whole number from 0 to 10⁷; strings of at most
  128 characters with no control or format characters.

An out-of-bounds value becomes null (IG §3). Provenance holds no wall time, cost, endpoint or credential, and it never
reaches cognition. Maxim's hybrid line asks for the same record (`hybrid_arbitration.md:97-98`).

### 4.2 The response cache (moved here from `npcs_and_sem.md` §4.8) **[after tier A and the agent barrier]**

**Why it waits.** It needs tier A, because a prompt carrying the host time never repeats a key, and the barrier,
because without it the next request depends on thread timing.

**Format.**
- **One cache per log segment** (O45), per save, never global.
- It is a registered gate with the strictest contract: versioned, a strict decoder, size budgets checked before
  allocation.
- It is excluded from bug reports by default, because it holds players' conversations.
- **The canonical request** is a frozen, versioned type with golden fixtures, serialised as canonical JSON (sorted
  keys, a fixed float format, NFC strings, explicit separators). It holds:
  - the function and its envelope's identity, and never the model or placement;
  - the sampling sent (temperature, top-p, top-k, seed, `max_tokens`, stops, `thinking`);
  - the system prompt and the message list;
  - the prompt-template and pymaxim versions;
  - an assertion that `tools is None`.
- **Occurrences** are keyed `(content hash, occurrence index)`. The index is assigned when the request is created, in
  canonical order by thought request id (`boundaries.md` §6.1), not execution order, whether or not an entry is ever
  written, so two NPCs with byte-identical requests can't swap answers on a rerun (DET-S2).
- **An entry** holds the raw output (the `reply` text), the canonical request and the provenance, for the final
  outcome only. On read, the gate recomputes the hash and refuses a mismatch. Actor, kind, timing and targets are
  recomputed, never read from the entry.

**Three modes, and no fourth.**
- **Live play writes and never reads.** An entry is written when its reply arrives, including a late reply for a
  request already cancelled. Test: a poisoned entry for the first request is ignored live.
- **A rerun reads and never dispatches.** It reads an occurrence at its landing tick, where live play would resume
  `think`. A request whose thought ended (a logged cancel or `thought_failed`) before its landing tick is never
  looked up. The rule is keyed to the log: a request whose thought has a terminal record (`thought_cancelled`
  or `thought_failed`) is never looked up, whatever the ticks. Any other miss is a loud error.
- **Replay never opens the cache.** Tested with the cache deleted, or poisoned.

**Pairing.** Two runs that differ in one variable stay paired through the cache only over their shared prefix. An arm
ends at its first miss, and a paired analysis estimates d_z, with the seed as the unit (BD-16, Arch 4.5).

**Saves and branches.**
- A reply that has arrived but not landed is held, with its text and provenance, in the host header's `held_reply`
  field (`npcs_and_sem.md` §6.6), and is saved with it. A load resumes from it and never dispatches it again. The
  bug-report exporter strips held texts, as it excludes the cache.
- A load opens a child segment. Its cache is the parent's cache **as it stood at the save's header snapshot**: an entry
  written after the snapshot is excluded, even if its request was created before. So a reply in flight at the
  save is re-dispatched by the child and never collides. The per-hash occurrence counters are saved with the save,
  so the child continues the parent's count as of the snapshot.

### 4.3 The rerun manifest's inference items **[with the cache]**

- **Refused on mismatch:** `functions.yaml`'s digest and the envelopes, like the rest of `data/agents/`. A rerun
  spawns workers with the recorded envelopes, and never reads `placements.yaml` or `endpoints.yaml`.
- **Recorded, reported and never refused, one entry per log segment:** the placement table's digest and each
  segment cache's digest.
- **The ledger pins** the functions digest and the placement digest per segment. It also pins that every experiment
  function uses `single`, so an arm that mixes models is a declared arm (`npcs_and_sem.md` §10).

## 5. (Consent, egress and credentials: `inference_gateway.md` §6–§8)

## 6. Time and capability: what placement may change

### 6.1 Wall time only

- **A placement changes wall latency.** That changes only dilation, or lateness under floor-holding (O4, O11, O16).
  In co-op's interim late landing, listeners hear the lateness (O27), and placement makes it vary per reply.
- **It never changes a thought's modelled time, kind or landing tick** (`npcs_and_sem.md` §6.6).

### 6.2 OPEN divergences

Owned here, and listed in `npcs_and_sem.md` §12.2:
- **Model capability can change within one NPC's life.** Fault failover, the spend cap, consent, and taint each move
  a function to another model. Load doesn't (§2.7). Tier checks keep a no-degrade function on its tier. A per-NPC
  meter counts changes of placement within a function.
- **Fatigue.** A weaker model can need more PFC cycles, and their modelled cost loads mental fatigue
  (`npcs_and_sem.md` §4.2, §4.6).
- **Observed latency.** `learned_hold_window.md`'s observed latency varies per reply (`npcs_and_sem.md` §5.1).
- **Taint spreads and persists** (IG §6).
- **Phantom interruptions.** A failed thought resumes the agent as `cancelled(prefix)` (§2.6), so how often an NPC is
  interrupted depends on its placement's health. No value crosses `AgentPort`, but the rate does.

### 6.3 Known gaps

Owned here, and listed in `docs/architecture.md`'s Known gaps:
- **O50's cost.** The first word arrives with the whole reply. How long that takes depends on the machine's load
  more than on the model:
  - the spike measured a median of 1.29 s on a quiet M2 (`research/llm_spike.md`);
  - the vertical slice measured 0.23 s warm on a quiet Mac mini, and 8 s warm (48 s cold) with other processes loading the machine
    to 125–142 (`lessons_maxim_in_games.md` 30, "A local model's latency is the machine's").

  On the loaded figures, a reply passes the account and the yield (`npcs_and_sem.md` §4.4). §4.5's lever 3 is
  unavailable until OD-A25.
- **Load versus failure (F2).** On the cloud and OpenAI-compatible transports, a hard-down server looks like load
  until OD-I9 (§2.7).
- **First hops only** (IG §7). Loopback and `owner_lan` promise only their first hop, HTTPS to `owner_lan` has no
  connect-time address check, and a cleartext LAN is readable.
- **Spend** on cache-heavy Anthropic calls rests on the host's floor until OD-I9 (F8).

### 6.4 The invariant tests **[now]**, in the checklist

- **Under `dilate`, the canonical requests are byte-identical** across placement mixes, seeded latencies and a
  scripted failure schedule that always leaves an eligible placement within the ceiling. The test also compares the
  world-log digest, kinds and receipts. The double echoes a digest of its whole input, in a reply it parses.
- **A schema test:** no provenance field, outcome, attribution, `thought_failed` reason or placement crosses
  `AgentPort` or the worker codec.
- **A negative control:** a plant that passes the placement id to the agent turns the test red.
- **One injected host wall clock,** the named host-only timeout module (`npcs_and_sem.md` §1), drives the lane,
  ceilings, delays, cooldowns and gateway supervision. The test waits for each reply before advancing it.

## 7. Agents stay on this machine; the codec stays transport-neutral

- **The cost of the barrier.** The barrier's round trips cost 0.2–0.8 wall seconds per second, locally, for 20 NPCs at
  20× (`npcs_and_sem.md` §6.6).
- **What a LAN would cost.** At a LAN round trip of about 1 ms (*to measure*), the barrier would cost about 4 s per
  second with parks sent one after another, or about 0.2 s with them sent in parallel.
- **What moves and what doesn't.** Inference, the heavy compute, already moves. The derived host sensing cost
  (`checklists.md`) would not move.
- **The codec names no transport property.** Each transport checks its own at start.

## 8. What is built when, and what measures it

- **[now], `phase1/agents`:**
  - the three formats and their gates;
  - queues, the `server` groups, selection, slots, delays, cooldowns and probes, all on the injected clock;
  - the outcome table;
  - provenance and the cache changes;
  - `engine.inference_wire`, and `engine.adapters.inference` on a scripted transport (IG);
  - the meters.

  No test makes a network call.
- **[Phase 4]:**
  - Maxim's three backends behind the gateway, each tested against a loopback fake server that reproduces F2, F4, F5
    and F8, a missing `finish_reason`, refusals, a stall and N concurrent calls with an injected auth failure. That
    test picks the instance model; if it needs more than one process per placement, that goes to the owner before
    it's built (O53).
  - Whether a server aborts a non-streamed generation when the client disconnects. If it doesn't, the rule that frees
    slots after a kill is revisited.
- **B5 rows** (`docs/standards_backlog.md`):
  - **[now]:** gateway start time, failed starts and restarts, the channel round trip, host CPU per reply, collateral
    attempts per kill;
  - **[Phase 4]:** time to first token and to the whole reply, slot wait, wait while another eligible placement was
    free, failures by outcome, abandoned tokens, spend, prompt-cache hit ratio, prefill per call, gateway memory, and
    a loopback model under physics load at the max profile, against one memory budget.
- **The tests** are in `checklists.md` under the lane's model, with the deferred mechanism findings.

## 9. Upstream (roadmap Phase 3)

**Searched at 043eab8f:** "placement", `FunctionRouter`, "capability tier", `ProviderPlacement`, "empty content",
"deadline", "gateway retries", "stream", "callback", "iterator", "proxy", `NO_PROXY`, "strict", "async router" and
"multi-peer". **Read:** both routing documents, the placement-split and fast-failover plans, the deferred multi-peer,
async-router and pecking-order plans, the candidates' B1 and B3, `hybrid_arbitration.md`, `DECISIONS.md:1150-1192`
and `http_deadline_1715.md`.

| Id | Kind | Ask |
|---|---|---|
| OD-A24 | pushback against `llm-routing.md:73` (O52) | Let an embedder that owns scheduling resolve placement outside `LLMRouter`, with one backend call per dispatch kept. Evidence: §1.2 and §2.5. |
| OD-I9 | pushback against `llm_path_fast_failover.md:43` and `:769` and the empty-content legacy path, which breaks Maxim's own `:771` | Typed `BackendError`s, configurable retry budgets including the SDK clients' and gateway retries (defaults unchanged), and complete usage counts (F8). It removes `failed(empty)` and lets the lane tell load from failure. |
| OD-A25 | question to cand. B1's planned token iterator (F1) | When does it come, and at which layer? A chunk sink on `complete_with_usage` lifts O50. |
| OD-I10 | question to the 2026-09-28 proxy decision | Confirm that `NO_PROXY` stays honoured on the backends' path, because it relies on httpx's private `get_environment_proxies` (`DECISIONS.md:1188`). Expose `strict_address_check` to backend callers. |
| OD-A23 | question to cand. B1's cancel clause | Does the abandonable path free the transport? Under `stream=False` none does (F5). |
| OD-A14 | amended | The request value carries a declared function name (a new field: no call site declares one today) and the envelope. B1 tags each call site it lists. The request is cut without building an `LLMRouter`, and hardware tier detection stays out of the embedded worker. |

Overdrive needs neither Maxim's async router nor multi-peer dispatch.

## 10. What this changes elsewhere (in this branch)

- `inference_gateway.md` is new.
- `npcs_and_sem.md`:
  - §4.8 now points here;
  - §1 and §4.4: retries, the liveness ceiling, final outcomes;
  - §4.5: lever 3 and the meters;
  - §6.1 and §6.2: no streaming yet;
  - §6.6: `held_reply`, `load` at spawn, the reason lists;
  - §12.2: a pointer to §6.2 here.
- `boundaries.md`:
  - §2.2: the two modules;
  - §5.3: the cache row, the gates and the thought-budget row;
  - §6.3: the manifest;
  - §7.1: the lane.
- `architecture.md` Known gaps.
- `embeddable_agent_DRAFT.md` and the Exp 64 prereg draft.
- `research/llm_spike.md`.
- `checklists.md`, B5, `roadmap.md`, `foundations_plan.md`, lessons 29.
- **Later:** the import contracts land with the packages (`phase1/agents`), and `client_rendering.md` §4 gains
  `inference_status` (`phase1/protocol`).
