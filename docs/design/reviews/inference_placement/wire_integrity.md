**Verdict: 1 BLOCKER, 12 SHOULD-FIX, 7 NIT.** The new contracts are mostly named, but the closed outcome set has no defined mapping to the things that consume it. Several changed contracts also disagree with neighbouring text that the diff left alone.

Scope: `git diff 814dea9..04ab810`. I read `inference_placement.md` in full, and the affected sections of `npcs_and_sem.md` (§1, §4.1, §4.4, §4.7, §4.8, §5.2–5.4, §6.1–6.3, §6.6, §12.2), `boundaries.md` (§5.3, §6.1–6.3, §7.1, §8.4 and the fold tables), `realtime_lanes_coop.md` §4.3, `world_model.md` §10, `world_v2.md`, `sem_stimuli.md`, `tile_and_client.md`, `docs/plans/checklists.md`, `foundations_plan.md`, `docs/maxim_upstream/embeddable_agent_DRAFT.md`, the roadmap rows and lessons entry 29. I read Maxim at `origin/main` 043eab8f with `git show` only: `types.py` (`LLMResponse` and the `BackendError` subclasses), `router.py::_complete_text`, `prompt_budgeter.py::PromptBudgeter.__init__`, `prompt_builder.py:1215-1240` and `worker_pool.py::Origin`. No code exists yet for any of these contracts: a grep of `src/`, `tests/`, `scripts/` and `data/` finds nothing, and there is no `data/agents/`.

## Wire-integrity table

| Contract | Producers (before → after) | Consumers (before → after) | What each consumer gets, before → after |
|---|---|---|---|
| Placement table (`data/agents/placement.yaml` + `placement.local.yaml`), merged value, digest | none → two loaders | none → lane selection, eligibility, the gateway's `open(table)`, the rerun manifest, meters | new. Merge rules and the local file's version are unspecified (S8). Where the endpoint lives is ambiguous (S7) |
| Role envelope (`context_tokens`, `max_output_tokens`, `token_counter`) | bound model's `n_ctx`/tokenizer → placement.yaml | `PromptBudgeter` (worker), the canonical request (as a "version"), the manifest, the loader's fit check | budgeter gets "the role's envelope", but the field names and meaning don't match Maxim's `total_budget`/`response_reserve` (S4). Nothing carries it to the worker at spawn (S5). The version is undefined (S4) |
| Closed outcome set (`ok`…`cancelled`) | none → gateway `reply` / lane | none → `Reply` to `think`, `thought_failed` log record, cache entry, cooldown keys, meters | **no mapping to any consumer (B1)**. `BackendError` mapping is not in the contract (S2) |
| `thought_failed` reason vocabulary (log record) | thought gate: budget, timeout, "model error" (boundaries §6.1), parse, reloaded → + `unavailable` | world log decoder, replay, bug reports | gets a word not in boundaries §6.1. "Model error" is never spelled. `timeout` now names two things (S1) |
| Gateway channel kinds | none → host and gateway | host lane, gateway | new. Lifecycle gaps: no ack to `open`, `error` has no attempt id, chunk/reply text, late replies, who stamps provenance (S6) |
| Provenance record | none → gateway (reported fields) + lane | cache entry, manifest summary, spend arithmetic, meters | new. Bounds on server- and user-supplied strings are unspecified. Who may read it on a rerun is unspecified (S9) |
| Canonical request (npcs §4.8) | model id + digest → role + "envelope version" | cache gate (hash), rerun lookup | key loses the model. Gains a version field that nothing defines (S4). `thinking` is a request field at the cut but not in the key (S10) |
| Cache entry (npcs §4.8, boundaries §5.3) | raw output + request → + provenance | rerun, manifest summary | gets provenance without a decoder rule or a defined failure encoding (B1, S9) |
| Rerun manifest (boundaries §6.3) | model profile (refused) → table digest + envelopes ("reported, never refused") | rerun start check | contradicts the `data/agents/` digests' refuse rule, and the envelope is in the key (S3) |
| Thinking lane (boundaries §7.1), O13 "gateway in the host" | lane = "gateway" → lane decides, separate gateway process calls | readers of O13, npcs §6.1/§6.3, supersession notes | one word now means two things (S12) |
| `PromptBudgeter` inputs (npcs §6.1, OD-A14) | bound model → role envelope | Maxim (upstream ask) | `embeddable_agent_DRAFT.md` still asks for the bound model's `n_ctx` (S10) |
| Host status messages (protocol → Godot) | dilation by cause → + spend cap reached, typed "no local model" refusal | client | new kinds with no place in the protocol vocabulary (S11) |
| Ledger record (boundaries §8.4) | "the model profile" → unchanged text | Maxim ledger / experiments | pins a value that no longer exists as one thing (N2) |

## BLOCKER

**B1. `inference_placement.md::§2.6` (outcomes), against `npcs_and_sem.md::§6.2` (`Reply`) and `boundaries.md::§6.1` (`thought_failed`).** The design creates a closed set of seven outcomes but maps none of them to any consumer, and its central sentence can't be built: "Only the final outcome becomes the thought's reply." `Reply` is closed to `complete(text)`, `cancelled(prefix)` and `truncated(prefix, reason)` (npcs §6.1, §6.2, §6.6). It has no variant for `empty`, `refused(…)`, `context_overflow` or `transport_down`. These are undefined:
- which `thought_failed` reason each failure ends as, under each `latency_policy`. Dilate retries until the ceiling, but floor-holding and `abandon` are never covered;
- what a `cache entry` stores for a machine-decided failure (raw output `""`? the outcome only in provenance?);
- whether a `cancelled` attempt or an intermediate failed attempt is written to the cache, which moves the occurrence indices;
- how `LLMResponse.stop_reason` (`types.py:46`) of `max_tokens` maps: `ok`, or `truncated`?

Failure scenario: live play, floor-holding, pinned `third_party` role. The final attempt is `refused(policy)`, and the lane logs `thought_failed(reason=<model error?>)`. On a tier-2 rerun the lane reads the entry: raw `""`, outcome in provenance. One implementer resumes `think` with `complete("")`. That parses as a failure and logs `thought_failed(reason=parse)`. The logged record differs from the live run's, so the rerun's digest check fails. Or the two implementers who write the producer and the rerun reader pick different rules, which is the same failure later. This is a contract gap, not a mechanism gap: the mapping is what the log, the cache and `think` all depend on. Fix, unverified: a mapping table in §2.6, with one row per outcome giving the `Reply` variant or `thought_failed` reason, the cache encoding, and retry-eligible yes/no.

## SHOULD-FIX

**S1. `boundaries.md::§6.1` (authority table) vs `inference_placement.md::§2.6`.** The `thought_failed` reason is a field of a logged world record with golden fixtures (boundaries §6.2). Its vocabulary is now spread across five places:
- boundaries §6.1: "budget, timeout, model error";
- npcs §4.4: `timeout`;
- npcs §4.7: `budget`;
- npcs §6.6: `parse`;
- checklists and `embeddable_agent_DRAFT.md`: `reloaded`;
- this design adds `unavailable`.

boundaries §6.1 wasn't updated, and §10 doesn't list it. "Model error" has no spelled form anywhere. Separately, `timeout` is both a per-attempt outcome (placement `timeout_s`) and a thought reason (the lane's liveness ceiling). A log reader can't tell an attempt timeout from the ceiling. Failure scenario: the log decoder's closed enum is written from boundaries §6.1, and it refuses `unavailable` (or `parse`) on replay of a valid log. Fix, unverified: one closed list in boundaries §6.1, with the others pointing to it.

**S2. `inference_placement.md::§2.6` ("each map to exactly one").** At 043eab8f Maxim has seven `BackendError` subclasses (`types.py:146-270`): `BackendOverloaded`, `BackendDown`, `BackendTimeout`, `BackendAuthFailed`, `BackendModelMissing`, `BackendInferenceBroken` and `BackendContextOverflow`. Only some of them map obviously. `Overloaded` could be `refused(quota)` or `transport_down`, and the difference matters for cooldown and spill. `ModelMissing` and `InferenceBroken` have no home. Cooldowns are keyed "per outcome class in `placement.yaml`", so the mapping is consumed by a data format and is contract. Failure scenario: a 529 maps to `transport_down` in one build and `refused(quota)` in another. The cooldown and retry behaviour then change with no format change.

**S3. `boundaries.md::§6.3` and `inference_placement.md::§4.3` (manifest).**
- §6.3 refuses on a mismatch of "the digests of `data/agents/`", and `placement.yaml` lives in `data/agents/`. The new text says the placement table is "reported, never refused". If the digest covers the directory, both rules apply to the same file.
- The envelopes are listed as reported, but each envelope's version is in the cache key, and the envelope sets the budgeter's truncation, so it is an agent input.

Failure scenario: a rerun machine with a different `context_tokens` passes the start check (reported), then fails at the first request with a cache miss, deep in the run instead of at the start. Fix, unverified: the envelopes refuse on mismatch; only the table digest is reported.

**S4. `inference_placement.md::§2.1`, `npcs_and_sem.md::§6.1` row, `§4.8`.**
- *Names:* the envelope field is `context_tokens` here and `n_ctx` in the npcs row.
- *Meaning:* Maxim's `PromptBudgeter(total_budget, response_reserve, token_counter, …)` computes `prompt_budget = total − reserve − overhead` (`prompt_budgeter.py:65-100`). The design's `context_tokens` is "the prompt budget the agent renders to", with fit defined as placement ≥ context + output. Passing `context_tokens` as `total_budget` subtracts the output reserve twice. Passing it as a prompt budget has no matching parameter.
- *Max output, four sources:* envelope `max_output_tokens`, `thought_budget.yaml`'s tokens per call (npcs §4.7), the request's sampling "max tokens" (§4.8, and `_complete_text(max_tokens=)`), and Maxim's own `mode.max_response_tokens` (`prompt_builder.py:1227`). No rule says which wins.
- *Version:* "its envelope's version" (§4.2) is never defined. An envelope has no version field, and the file's format version is not the same thing.

Failure scenario: envelope max is 512 and the thought budget's is 256. The budgeter reserves 512, generation stops at 256, and the fit check uses 512. Edit `context_tokens` without bumping the undefined version and the key doesn't move.

**S5. `npcs_and_sem.md::§6.6` (worker codec) vs `inference_placement.md::§2.1` ("the host gives the worker each role's envelope at spawn").** The host-to-worker kinds are closed: `step`, `resume`, `settle`, `consolidate`, `save`, `load`, `shutdown`. None carries an envelope, the spawn is argv plus an allowlisted environment, and §10 doesn't list §6.6. Failure scenario: a builder adds an `init` frame or an environment variable. Either is an unregistered codec change, and the env route breaks the allowlist rule.

**S6. `inference_placement.md::§3` (gateway channel).**
- `open(table)` has no reply. The host can't tell a gateway that refused the table (an unknown transport, say) from one that is ready, so dispatches race the open.
- `error(code)` carries no `attempt_id`, and no code list exists. An unmapped exception during one attempt either ends that attempt or the gateway, and the text doesn't say which.
- `chunk(…, text)` and `reply(…, text, …)` both carry text. Which one is the raw output the cache stores and stage 1 validates (the joined chunks, or the reply)? A mismatch between the two has no rule.
- A `reply` for an attempt the lane has already ended (liveness ceiling, cancel) needs a stated drop rule, beyond freeing the slot.
- Who produces `timeout`? The host enforces `timeout_s` ("host-only", §2.2), but Maxim's backend has its own instance `timeout_s`. A host-side timeout followed by a gateway `reply(ok)` gives two outcomes for one attempt.
- "Past its wall ceiling": which ceiling, and in which file?
- Provenance is built in the untrusted gateway. Placement `id`, `transport`, `egress` and the declared model are known to the host, so the host should stamp them. Otherwise a misbehaving gateway relabels a `third_party` call as `loopback` in the record the spend meter and the manifest read. "Everything from the gateway is untrusted input" covers text only, not `outcome` or `provenance`.

**S7. `inference_placement.md::§2.2` vs `§5.1` (endpoint location).** §2.2 puts `endpoint_ref` in the table, "resolved only in the gateway", but also says "the merged table, without endpoints", which implies it holds endpoints. §5.1 says the gateway checks the loopback literal "again", which implies the host checked first. The host can't check a literal it never sees. `egress` itself is declared: only `loopback` is ever checked against an address. Failure scenario: a placement declared `egress: owner_lan` whose endpoint is a cloud provider bypasses the `third_party` opt-in and the spend cap in single-player. With guests, it gets a disclosure naming the wrong class. The contract has to say which process holds the endpoint, and which process checks which `egress` claim.

**S8. `inference_placement.md::§2.2` (two files, merge).** These are unspecified:
- merge precedence;
- placement-id collisions between the files;
- whether the local order may drop the shipped default;
- who holds `spill`: §2.2 puts "each role's policy" in the shipped file, while §2.4 calls spill a per-role opt-in, which reads as the player's.

The local file's format version and refuse-on-unknown are also unstated. "Every format is versioned" covers it, and so does the question of what happens to a player's old local file when the shipped format bumps: refuse or migrate. The per-user path is a new input source for `scripts/lint_inputs.py` and the gate registry, and its location must be injectable so tests never read home (CLAUDE.md isolation).

**S9. `inference_placement.md::§4.1` (provenance) and `boundaries.md::§5.3` (cache row).**
- The reported `model` and `provider` are strings a remote server supplies, and placement ids are strings the player chooses. Both are written into a file that travels with saves. No length or charset bound is stated.
- §5.2 says only placement ids appear in manifests and bug reports, but nothing stops an id like `alice-mini.tailnet`, which is the private-host leak §5.2 forbids.
- The cache gate "recomputes the hash", but provenance is outside the hash, so it is unauthenticated. The design should say no rerun consumer reads it except the manifest summary and meters, and that it never reaches cognition.

**S10. `npcs_and_sem.md::§6.1` row, roadmap `OD-A14`, `embeddable_agent_DRAFT.md`, vs O46 and `checklists.md` ("Maxim's router is never built on this path").**
- The request is still "produced at the `LLMRouter._complete_text` cut (`router.py:958`)". That method exists on a router object in the worker, so either a router is built there or the cut moves. O46's "not on the NPC path" and the checklist's "never built" contradict the request's own source.
- `_complete_text` takes `thinking` and `provider_hint` (verified at 043eab8f, `router.py:958-970`; `exec_agent.py:1544` passes `thinking=`). `thinking` is placement-dependent (Anthropic) and is in neither the canonical request nor the envelope.
- The upstream draft still asks for "the bound model's `n_ctx` and tokenizer". Maxim would read an ask that differs from our OD-A14.

**S11. `checklists.md::The lane's model` vs `inference_placement.md::§2.6`.** The checklist says a missing local model with guests "refuses (typed, and shown in the client)", which reads as a session-level refusal. The design ends each thought as `thought_failed(reason=unavailable)`. The same condition has two behaviours. Both that refusal and "the client is told through a host status message" (§5.3, spend cap) add client-facing message kinds. The only status channel defined is dilation by cause (npcs §5.4), and neither the protocol vocabulary nor the Godot reader is named.

**S12. `npcs_and_sem.md::O13`, `§6.3` ("The model gateway stays in the host"), the `§6.1` row ("the gateway sits above the backend"), and the supersession notes in `boundaries.md` and `npcs_and_sem.md` ("the gateway is the host's thinking lane").** "Gateway" now names a separate child process that the lane is not. O13's text was left unchanged on purpose and "reads as host-side", but a reader of O13 or §6.3 sees "in the host" and builds it in-process. That reverses O47, and nothing in those sections points to the new meaning.

## NIT

- **N1. `inference_placement.md::§3`.** It cites "stream validation (`npcs_and_sem.md` §5.3)". §5.3 is syllable stamps; per-chunk validation is §5.2 and §6.6.
- **N2. `boundaries.md::§8.4`.** "A ledger record pins … the model profile": that is now per placement, per reply. Say what is pinned (the table digest? the provenance summary?).
- **N3. `npcs_and_sem.md::§12.2`.** "the host never shares one [router] across NPCs" is stale: the host builds none.
- **N4. Vocabulary overlap.**
  - `refused` and `cancelled` are outcome words here and receipt kinds in npcs §6.4, with different meanings.
  - Maxim's `Origin` docstring calls LOCAL/CLOUD/PEER "the *placement* axis" (`worker_pool.py:72`), where ours is `egress`, and Maxim's "placement" is not our `placement`. Worth one sentence in §1.
- **N5. `inference_placement.md::§5.3`.** Spend = tokens × `price` (in and out). Maxim's `input_tokens` includes cached tokens (`types.py`, CC12), which providers price differently. The `price` field can't express that.
- **N6. `inference_placement.md::§4.3`.** The "provenance summarised per placement" manifest item has no defined format.
- **N7. `world_model.md::§10`.** Rows 9b and 10 don't mention the gateway process or the placement loaders. Row 10 says `phase1/lanes` brings the meters and threads, while this design builds a threaded gateway and its meters in `phase1/agents` **[now]**.

## Checked and consistent

- The npcs §4.4 no-deadlock invariant vs §2.5: consistent. A slot is held only by a call in flight.
- npcs §1, "a timeout never silently frees a worker", agrees with §2.5. `realtime_lanes_coop.md` §4.3's contrary line ("only frees its worker") was already superseded by npcs §1.
- Replay never opens the cache (npcs §4.8) is unchanged.
- Cache repeats are numbered by thought request id (npcs §6.6), which is independent of placement, so a failover doesn't reorder occurrences, provided only final attempts are written (see B1).
- `sem_stimuli.md`, `tile_and_client.md` and `world_v2.md` use none of the changed contracts.
- Word budgets: `npcs_and_sem.md` 23,788 → 23,786 words, `boundaries.md` 13,983 → 13,982, the new document 4,204 (counted with `wc -w`).
- The Maxim citations I opened match 043eab8f: `PromptBudgeter.__init__`, `_complete_text`'s signature, the `LLMResponse` fields and the `BackendError` subclasses.

No fix above was verified by running anything: every proposed fix is unverified.
