**Verdict: 1 new BLOCKER (contract), 8 new SHOULD-FIX, 9 new NIT. Of round 1: 17 fixed, 3 open (S3, S12, N4).** The outcome table closes B1's mapping gap. But it hands `think` a `truncated` payload that contradicts npcs §6.6, and boundaries §6.3 still says the opposite of the new refuse rule.

Scope: `git diff 274f297..caca211`, all twelve files. I read `inference_placement.md` v2 in full. I also read every consumer section of the changed contracts:
- npcs §1, §4.4, §4.5, §4.8, §5.2, §5.4, §6.1 row, §6.2 build list, §6.3, §6.6 (codec, header, `cancelled`/`truncated`), §12.2;
- boundaries §5.3, §6.1, §6.3 (manifest and tiers), §7.1, §8.1, §8.4;
- `tile_and_client.md` §3.3; `realtime_lanes_coop.md` §4.3; `world_model.md` §10; checklists "The lane's model"; `embeddable_agent_DRAFT.md`; the Exp 64 prereg draft; the roadmap rows.

Maxim was read only at `origin/main` 043eab8f, with `git show` and `git grep`:
- `types.py` (`LLMResponse.stop_reason: str = ""`, `BackendError`);
- `openai_backend.py:535-545`, `anthropic_backend.py:460-470`, `maxim_peer_backend.py:953-958` and `router.py:958-970`;
- a grep for a refusal stop reason in `models/language/`, which found nothing.

Nothing was run, and every fix sketched below is unverified.

## 1. Round-1 statuses (read from the tree at caca211)

| Id | Status | Evidence |
|---|---|---|
| B1 | **fixed** | IP §2.6 table: every outcome has a `think`/log target, a retry flag and a cache column, `max_tokens`→`truncated(length)`, `cancelled` writes nothing (§4.2). The fold introduced the new **B-1** below. |
| S1 | **fixed** | IP §2.6 has one closed list, `model_error` is spelled, and `call_timeout` is separate from `timeout`. boundaries §6.1 points to it (line 380). npcs §4.4 wording drift is **N-6**. |
| S2 | **fixed** | IP §2.6 maps all seven `BackendError` subclasses. Non-`BackendError` exceptions are still unmapped (**S-4**). |
| S3 | **open** | IP §4.3 says envelopes refuse, but `boundaries.md::§6.3` (line 456-457) still says "the placement table's digest and role envelopes (reported, never refused: `inference_placement.md` §4.3)". IP §10 claims boundaries §6.3 changed, but the diff has no hunk there. Same failure scenario as round 1. See **S-1**. |
| S4 | **fixed** | IP §2.1 uses Maxim's names, `max_tokens` = min(reserve, budget), the loader refuses a budget above the reserve, and identity is the digest. Residual: **N-3**. |
| S5 | **fixed** | IP §2.1; npcs §6.6 "`load` (with the function envelopes)". Residual: **N-4**. |
| S6 | **fixed** in part | `ready`/`error`, generation-scoped ids, host-stamped provenance, the kill ceiling, and `chunk` reserved. New defects in the rules: **S-3** and **N-5**. |
| S7 | **fixed** | IP §2.2: endpoints are read by the gateway only. §5.2: the gateway checks loopback and `owner_lan`. |
| S8 | **fixed** | IP §2.2: the player's file replaces the shipped one whole, files are versioned, ids are unique and the path is injected. The endpoints file's replace rule is unstated (**N-5**). |
| S9 | **fixed** | IP §4.1 bounds and ids. The `id` regex and "told it is shared" cover the leak. Provenance never reaches cognition. |
| S10 | **fixed** | OD-A14 and the upstream draft now say "without building an `LLMRouter`", and `thinking` is in the envelope. Residual type mismatch: **N-3**. |
| S11 | **fixed** | IP §5.6 `inference_status`; the session-start refusal matches checklists. The target section is wrong (**N-7**). |
| S12 | **open** (NIT now) | npcs §6.3 is fixed. Still singular or stale: npcs O13 ("The LLM gateway stays in the host"), the npcs §6.1 row ("the gateway sits above the backend, so the router's `_inference_lock` never serialises NPCs", though no router exists now), boundaries §7.1 ("a host-owned gateway") and `embeddable_agent_DRAFT.md:13`. |
| N1 | **fixed** | The cite was removed; §3.3 cites npcs §6.6. |
| N2 | **fixed** | boundaries §8.4 pins "the placement digests". |
| N3 | **fixed** | The npcs §12.2 line was deleted. |
| N4 | **open** | The `egress`/`Origin` note was added (IP §2.2). The `refused`/`cancelled` outcome words still collide with receipt outcomes (`tile_and_client.md` §3.3), as the author states. |
| N5 | **fixed** | IP §2.2 `price` has four rates; §5.5. |
| N6 | **fixed** | The summary item was removed; §4.3 records digests. |
| N7 | **fixed** | `world_model.md` §10 row 10. |

## 2. Wire-integrity table (the fold's contracts)

| Contract | Producers (v1 → v2) | Consumers (v1 → v2) | What each consumer gets, v1 → v2 |
|---|---|---|---|
| Three files: `functions.yaml`, `placements.yaml` ×2, `endpoints.yaml` ×2 | one table + local → three files | lane (functions, placements), gateway (endpoints), rerun manifest, ledger | Ownership is clear. `spill` is declared in two files (**S-6**). Health tunables sit in a refuse-on-rerun file (**S-6**). The endpoints replace rule and restart/ping tunables have no home (**N-5**). |
| Envelope (`total_budget`, `response_reserve`, `token_counter`, `thinking`) and its digest identity | none → `functions.yaml` | `PromptBudgeter` via `load`, canonical request, fit check, manifest | Names match Maxim. The manifest's refuse rule contradicts boundaries §6.3 (**S-1**). `thinking` bool vs Maxim's dict (**N-3**). Fresh spawn (**N-4**). |
| Outcome table → `Reply` / `thought_failed` / cache | none → IP §2.6 | `think`, world log, cache, health, eligibility | The `truncated` payload contradicts npcs §6.6 (**B-1**). Row definitions don't match the backends' `stop_reason` (**S-4**). Cooldown vs pinned (**S-5**). |
| `thought_failed` reasons | scattered → IP §2.6 list | log decoder, boundaries §6.1 | Consistent. npcs §4.4 wording (**N-6**). |
| `truncated` reasons | `validation` (npcs §6.6) → + `length`, `stream_broken`, `transport` | `think`, cache | No closed list; three documents each hold part of it (**B-1**). |
| Gateway channel kinds and rules | none → IP §3.3 | host lane, gateway | "finished" is undefined, so a normal late reply can kill the gateway (**S-3**). `error(code)` has no list; `ready` has no fields (**N-5**). |
| Provenance | gateway → host-stamped + reported | cache, manifest, spend, meters | Bounded and host-stamped. A rerun's failure reason has to come from it (**N-1**). |
| Cache modes, write point, held replies | rerun-only → three modes | rerun lane, save, bug reports | The rerun read point is undefined while `cancelled` writes nothing (**S-2**). The held text has no slot in the npcs §6.6 header list and goes into saves (**S-7**). |
| Rerun manifest and ledger | profile → digests + envelopes refuse | rerun start check, Maxim ledger | boundaries §6.3 still says "reported, never refused" (**S-1**). "Failover off" can't be expressed (**S-8**). |
| Streaming (O50) | host streams → `stream=False`, `chunk` reserved | boundaries §7.1, npcs §5.2, §6.2 build list, §4.5 lever 3 | Consumers still describe a streamed model call (**S-9**). |
| `inference_status` | none → host | client | Points at a client→server section of a frozen document (**N-7**). |
| `load` frame + envelopes | none → host | worker | Fresh-spawn path (**N-4**). |

## 3. New findings

### BLOCKER

**B-1. `inference_placement.md::§2.6` (rows `truncated(length)`, `truncated(stream_broken)`; "once speech has reached the world") vs `npcs_and_sem.md::§6.6` ("`cancelled(prefix)` and `truncated(prefix)` carry the delivered speech"). Contract.**

npcs §6.6 says the payload of `truncated` is the **delivered prefix**: "the host-validated syllables already emitted to the world by the cancel tick … Tokens streamed beyond them are discarded and never reach cognition (TB3-S5)". The new table resumes `think` with `truncated(text, reason=length)`. Under O50, `text` is the whole raw reply, and none of it has been delivered when the lane maps it, because the reply is held until its landing tick. Two builders can read this two ways:
- **(a)** Following IP, the agent receives tokens that never reached the world. That breaks TB3-S5's leak rule: cognition holds words no listener heard. It also bypasses the parse-failure template, so the speech field of a length-cut reply is never delivered.
- **(b)** Following npcs, prefix = "" (nothing delivered yet), and a length-cut NPC says nothing, although the cache stored "text and reason".

On a rerun, the two builds produce different `ThoughtOutput`s from the same entry.

The `truncated` reason vocabulary is also now spread over three places:
- `validation` (npcs §6.6);
- `length` and `stream_broken` (IP table);
- `transport` (IP §2.6 bullet, in no row).

Each of these reasons is a field of a value with golden fixtures.

Failure scenario: a P2 reply hits `max_tokens` mid-sentence. Build A resumes `think` with 300 undelivered tokens, and the NPC "remembers" saying them. Build B's NPC goes silent. A tier-2 rerun digest check fails between builds.

What has to be defined: what a `truncated` reply carries when nothing has been delivered yet, how its speech field reaches the world, and one closed list of reasons.

### SHOULD-FIX

**S-1. `boundaries.md::§6.3` (rerun manifest, line 456-457) vs `inference_placement.md::§4.3`. Contract.** This is round-1 S3, still open. boundaries §6.3 says "role envelopes (reported, never refused)", while IP §4.3 says envelopes and the functions digest refuse. IP §10 lists boundaries §6.3 as changed, but it isn't, and it still says "role". boundaries §6.3 is the manifest's owner and the start-check builder's source, so the failure is round 1's: a changed `total_budget` passes the start check and fails at the first cache miss mid-run. The same line also records one "response cache's digest", but IP §4.2 now has one cache per log segment.

**S-2. `inference_placement.md::§4.2` ("`cancelled` writes nothing"; "write point is when the reply arrives"; "a rerun reads … a miss is a loud error"). Contract.** The design never says **when** a rerun reads: at the request's occurrence, or at its landing tick or terminal record. Three cases make that matter:
- A thought cancelled before its reply arrives has no entry. A live run with such a cancel is still tier 2 (a cancel is a world event, boundaries §6.3 tiers).
- A cancel racing the reply's arrival leaves an entry or not, depending on wall time.
- Likewise, `unavailable` and the liveness `timeout` produce no table outcome, so the cache column says nothing about them, and a late reply after the ceiling would still hit "the write point".

Failure scenario: a tier-2 rerun of a valid run reaches a request whose thought was cancelled at tick T, looks the request up at dispatch, misses, and dies with a loud error. The cache format and the rerun reader need one rule: a rerun consults the log's terminal record first, or a cancelled occurrence writes a marker.

**S-3. `inference_placement.md::§3.3` (rules: "a `reply` for an unknown, **finished** or foreign attempt … is a protocol error: that gateway is killed"). Contract.** "Finished" is undefined.
- §2.5 says that on cloud transports a cancelled call "runs until it returns". The gateway then sends its one `reply`, which "each accepted attempt gets exactly one" requires.
- The liveness ceiling ends the thought while the attempt is still in flight, and the design doesn't say whether the host sends `cancel` then.

A builder who marks an attempt finished when the lane ends it (by cancel or by the ceiling) kills the gateway, and every other in-flight call on that placement, on the normal path. If "finished" means "already replied", it duplicates "a second `reply`".

Failure scenario: a guest interrupts an NPC on a `third_party` placement. Four seconds later Anthropic returns, the host calls it a reply to a finished attempt, and it kills the gateway. Three other NPCs' calls end `failed(unreachable)` and are retried, and the abandoned spend is booked at worst case four times.

**S-4. `inference_placement.md::§2.6` ("Produced from" column) vs Maxim 043eab8f. Contract (row definitions); mechanism (per-transport enumeration, deferrable to Phase 4's fake-server tests).** The rows are defined by "empty" versus "non-empty" `stop_reason`, but the backends don't produce that distinction consistently:
- `openai_backend.py:542` writes `str(getattr(choice, "finish_reason", ""))` and `anthropic_backend.py:467` writes `str(getattr(resp, "stop_reason", ""))`. A null reason becomes the string `"None"`, which is non-empty, so the reply is `ok`.
- `maxim_peer_backend.py:958` writes `first.get("finish_reason") or ""`, so the same null becomes `""`, which is `truncated(stream_broken)`. That outcome is placement-attributed and starts a cooldown.
- `stream_broken`'s premise (F3) is a streamed call, but O50 sets `stream=False`, so the row mislabels a server that omits `finish_reason`.
- "A length stop" is not enumerated per transport (Anthropic `max_tokens`, OpenAI `length`).
- `failed(refused)`, "a provider refusal reported as such", has no producer: grepping `models/language/` for a refusal stop reason finds nothing. A provider refusal with a non-empty stop reason falls into the `ok` row.
- Exceptions that are not `BackendError` (an SDK or JSON error escaping a backend) have no row.

Failure scenario: a llama.cpp-compatible peer leader that omits `finish_reason` makes every reply on that placement `truncated(stream_broken)` and starts a cooldown each time. The same server behind `openai_compatible` is always `ok`. The logged outcome and the cache contents then depend on the transport name.

**S-5. `inference_placement.md::§2.6` ("`overloaded` and `call_timeout` don't [move a pinned request]") vs `§2.7` ("a placement-attributed outcome starts that placement's cooldown") and `§2.3` (health: "not cooling down"). Contract.** `overloaded` and `call_timeout` are placement-attributed, so they start a cooldown, and that makes the placement ineligible. Under `pinned`, "the first eligible placement" is then the next one, so the request moves. That is exactly what O48 and §6.2 ("load alone never moves a pinned function") forbid. The fold table claims "request outcomes don't cool", but §2.7 says otherwise.

It is also undefined whether a request with no eligible placement ends at once as `unavailable` or waits to the ceiling and ends as `timeout`. Those are two logged reasons for one condition.

Failure scenario: an experiment function pinned to model A gets one 529. A cooldown starts, the next request is served by model B, and an arm mixes models by accident, which §4.3 says must never happen.

**S-6. `inference_placement.md::§2.2` (files table) and `§2.7`. Contract.**
- **`spill` is declared in two files.** `functions.yaml` holds "each function's policy", and the player's `placements.yaml` "may set `spill`". No schema says which file carries the field, or what the precedence is.
- **Dispatch-only data sits in a refuse-on-rerun file.** The policy and the per-outcome cooldown table live in `functions.yaml`, which is in `data/agents/` and so refuses on a rerun mismatch (§4.3), yet a rerun never dispatches.

Failure scenario: a patch tunes one cooldown. Every recorded run before it now refuses its tier-2 rerun for a value the rerun can't use.

**S-7. `inference_placement.md::§4.2` ("held in the host-owned header with its text, and saved with it") vs `npcs_and_sem.md::§6.6` (header field list) and `boundaries.md::§5.3` (saves are bug-report material; the cache is "excluded from bug reports by default, since it holds players' conversations"). Contract.**
- The header's closed field list in npcs §6.6 has no held-reply slot, so the header format and its fixtures disagree with IP.
- The held text is model output conditioned on guest speech, so it is the same material the cache is kept out of bug reports for, but it now travels in the save.

Failure scenario: a player attaches a save to a bug report and ships a guest's conversation, held mid-reply, that the cache rule was written to keep out.

**S-8. `inference_placement.md::§4.3` ("experiment functions are single-placement with failover off") and `boundaries.md::§8.4`. Contract.** The ledger pins a property no file can express. The policy vocabulary is `pinned` | `spill`, and `pinned` still moves on every non-load failure (§2.6). A one-placement list ends in `unavailable` instead of failing over, but nothing requires an experiment function to have a one-placement list.

Failure scenario: a ledger record claims "failover off" for a run in which `failed(model_missing)` moved a request to the second placement.

**S-9. `boundaries.md::§7.1` ("the host streams the model call itself, reads the speech field first, validates it per chunk"), `npcs_and_sem.md::§6.2` build list ("The host-side stream: chunked speech validation … from a scripted stream", [now]), §5.2 and §4.5 lever 3, vs O50 and IP §3.3 (`chunk` reserved). Contract.** The consumers still describe a streamed model call, and `phase1/agents` is told to build a chunk consumer with no producer on the shipped path ("a fix ships with a caller"). Nothing says that under O50 speech validation and syllable stamping run over the whole held reply.

Failure scenario: the builder wires the scripted transport to emit `chunk` so the npcs §6.2 item has a caller. That violates O50 and the reserved-kind rule, and the channel codec ships a kind that production never sends.

### NIT

- **N-1. `inference_placement.md::§4.2` ("Cache entry: failure").** The failure encoding is unstated. A rerun can get the `thought_failed` reason only from provenance's host-stamped outcome, which §4.1 and round-1 S9 kept out of rerun consumers. The read should be stated, or the reason put in the entry. Such runs are tier 3 (boundaries §6.3 tiers), so this is minor.
- **N-2. `inference_placement.md::§2.6` (`failed(unreachable)` row).** "Produced from" excludes "our kill, or a dead gateway", while Attr. says "host after a kill or crash", and §3.4 assigns kills to this row.
- **N-3. `inference_placement.md::§2.1`.** The envelope's `thinking` is a bool, but Maxim's `_complete_text(thinking: dict[str, Any] | None)` (`router.py:969`) carries a budget, and the agent passes it per call (`exec_agent.py:1544`). No rule says which wins, or whether the canonical request's `max_tokens` is the agent's value or the host-clamped one that was sent.
- **N-4. `npcs_and_sem.md::§6.6` (`load` "with the function envelopes").** `load` is the save-load kind. A freshly created NPC with no save has no stated frame that carries its envelopes.
- **N-5. `inference_placement.md::§3.3`, `§3.4`, `§2.2`.**
  - `error(code)` has no code list.
  - `ready` carries the proxy report (§5.3), but the kinds table gives it no fields.
  - `ping_ceiling_s`, `max_restarts`, the restart window and the backoff cap have no file.
  - An auth failure at `open` is a table outcome, but there is no attempt at `open`, and restart-until-down would retry a missing credential `max_restarts` times.
  - The player's `endpoints.yaml` has no stated replace or merge rule.
- **N-6. `npcs_and_sem.md::§4.4`** still reads "a call past the host's wall ceiling ends as `thought_failed(reason=timeout)`". IP §2.5 counts the liveness ceiling from enqueue and names a separate `call_ceiling_s`, so a reader takes "a call past the ceiling" to be the call bound.
- **N-7. `inference_placement.md::§5.6`.** `inference_status` is to be "added to `tile_and_client.md` §3's message list". That section is client→server (§3.3) in a frozen document; server→client messages live in `client_rendering.md` §4, which the tile document itself says.
- **N-8. `npcs_and_sem.md::§4.5` meters** ("per model and role") and **`exp64_cradle_conduct_prereg_DRAFT.md:76`** ("the model, `n_ctx`") use the retired vocabulary. The prereg should name the function, envelope and placement digest it holds equal.
- **N-9.** S12's stale singular "gateway" sentences, listed in §1.

## Checked and consistent

- boundaries §6.1 → IP §2.6 pointer; boundaries §8.1 row; boundaries §8.4 pins.
- npcs §1 retry sentence; npcs §6.3 "inference gateways (O47)"; npcs §6.3 host-imports sentence.
- OD-A14 and `embeddable_agent_DRAFT.md` envelope names; checklists versus §5.6 on the guest refusal.
- `world_model.md` row 10; the foundations plan ids; the B5 row.
- Host-stamped provenance versus the spend meter; the cancel-as-`cancelled` rule in checklists and §2.5.
- O50's cost and `chunk`'s reserved status are consistent inside IP.
- Word budgets (`wc -w`): IP 5,988 (≤ 6,000), npcs 23,786 → 23,777, boundaries 13,982 → 13,982, world_model 4,667 → 4,666, foundations 2,499 → 2,500 (at the limit).
- Maxim citations I opened match 043eab8f: `LLMResponse.stop_reason` defaults to `""`; `_complete_text`'s signature including `thinking`; the non-streamed `stop_reason` lines cited in S-4.

Per the stop rule, the mechanism halves of S-4 (per-transport stop-reason enumeration) and N-5 (tunables and code lists) can be deferred to `phase1/agents` (S-4's enumeration to Phase 4's fake-server tests). B-1, S-1, S-2, S-3, S-5, S-7 and S-8 are contract findings and should fold.
