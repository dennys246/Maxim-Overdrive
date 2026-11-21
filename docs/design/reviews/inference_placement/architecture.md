**Verdict:** the core split holds: the host's lane decides and a host-owned process calls, with Maxim's backends as transports and the router off the dispatch path. But the design never says where the gateway's code lives in the package and layer scheme, or who may import `maxim` there. That is a contract gap, and the import contracts will be loosened to fill it. Several interfaces are also left open: outcome classification, the envelope's channel, which process reads endpoints, and gateway liveness. 1 BLOCKER, 9 SHOULD-FIX, 5 NIT.

## Findings

### BLOCKER

**A1. `inference_placement.md::§3` (and `§10`): the gateway, its channel and the placement loaders have no package, layer or `maxim` importer.**
- **What the design leaves unsaid.** §3 says the gateway "imports `maxim.models.language` and the backend modules". It never names the module the gateway runs, the package that holds it, or its layer in `boundaries.md` §2.2.
- **What the existing contracts say:**
  - `boundaries.md` §8.1: "Maxim is imported only by named adapters, each declaring the Maxim surface it uses". Its table has rows for the membrane, agent stepping, NPC authoring and experiments, and no inference row.
  - `pyproject.toml` `maxim-through-adapters` is a `protected` contract with `allowed_importers = ["simcore.adapters.sem"]`.
  - `npcs_and_sem.md` §6.6 still says the host imports "`maxim` itself only in workers". The gateway is explicitly not a worker ("beside the agent workers"), and §10 doesn't list §6.6 as changed.
  - `boundaries.md` §5.3 has a row for the worker channel, but none for the gateway channel or the two placement loaders. §8 says both loaders are "registered gates".
  - Who decides the "per-user config directory" path is also unsaid. `boundaries.md` §3 and `pyproject.toml` say the engine has no default path into data. `maxim_overdrive.data` owns data paths, and a home-directory read is a new input source for `scripts/lint_inputs.py`.
- **Failure scenario.** The `phase1/agents` builder needs a home for `gateway_main`.
  - Under `engine.host` (natural, since "host-owned"): the protected contract goes red. The only way to green is adding `engine.host` to `allowed_importers`. The host package then statically imports `maxim`, which reverses O47's own reason 1, and the gate is green.
  - Under `engine.adapters.agents`: the adapter whose §8.1 surface says "model calls run by the host, never injected into Maxim" gains the backends. The §6.6 test that "the worker holds no model backend" then has to except a module in the same package the worker entry lives in.
  - Either way the decision is made at build time, by the builder, under gate pressure. That is the outcome the "a design document holds the contract" rule exists to prevent.
- **Fix (unverified):** name a separate adapter, for example `engine.adapters.inference`, with its layer. Add its §8.1 row with its Maxim surface and its `allowed_importers` entry. Add §5.3 rows for the gateway channel and both placement gates. State which package resolves the per-user path. Amend §6.6's sentence.

### SHOULD-FIX

**A2. `inference_placement.md::§2.6`, `§1` fact 1, `§8`, `§3` channel: outcome classification is assigned to the lane, but only the gateway can do it.**
- **The contradiction.** §1 says "the lane therefore maps empty content to the outcome `empty`". §8 builds "the outcome mapping in the lane". §2.6 says "`BackendError` subtypes … each map to exactly one" outcome. But those exceptions are raised in the gateway process and can't cross a closed-schema JSON channel. And §3's `reply(attempt_id, outcome, …)` already carries the outcome *from* the gateway.
- **Why it matters for the split.** Either Maxim's exception taxonomy and the empty-content quirk (transport detail) leak into the lane, or the design is wrong about where mapping lives.
- **Health attribution is mixed in too:**
  - §2.6: "a failure starts that placement's cooldown". §3: when the gateway dies, "every attempt in flight ends as `transport_down`". So a gateway crash puts every in-flight placement into cooldown although none of them failed.
  - Under `pinned`, every role then fails over to its second placement, possibly `third_party` in single-player, for a fault in our own process.
  - `context_overflow` and `refused(policy)` are caused by the request, yet they also cool down a healthy placement and push other NPCs off it.
- **Fix (unverified):** the gateway classifies (doing), and the lane decides from a closed outcome set that marks each outcome as placement-attributable or not. A gateway death is its own outcome that starts no placement cooldown.

**A3. `inference_placement.md::§1` fact 1, `§2.6` `empty`: mapping empty content to failure is a workaround that isn't marked.**
- **The design's case.** It argues this is "Maxim's documented contract, not a special case of ours". `llm_routing.md` keeps it as the *legacy* path, and Maxim's own lesson (`llm_path_fast_failover.md:771`, as cited) says the opposite. So we are reproducing a Maxim defect at our call site. CLAUDE.md says never to work around Maxim in this repo; the exemption is a marked, scheduled band-aid.
- **It also misclassifies.** At `origin/main` 043eab8f, the failure path is `return LLMResponse(content="")` (`anthropic_backend.py:333-335`) with `stop_reason` defaulting to `""` (`types.py`, `LLMResponse.stop_reason: str = ""`). A real completion that is empty, say an NPC choosing silence, has a non-empty `stop_reason`.
- **Failure scenario.** A model legitimately returns `""` with `stop_reason="end_turn"`. The lane records `empty`, cools the placement down and re-dispatches to the next one. Which model answers now depends on what the reply said, and a healthy placement is marked unhealthy.
- **Fix (partly verified: I read the two lines above at 043eab8f; I did not check that every real completion sets `stop_reason`):**
  - Define `empty` narrowly (empty content *and* empty `stop_reason`).
  - Record it as a scheduled stand-in tied to OD-I9's landing, with a tracked marker and a roadmap listing once code exists.
  - Treat a genuine empty completion as `ok`, and let the agent's parse decide.

**A4. `inference_placement.md::§2.6` "Retries follow the existing policy": this is a policy change, not the existing policy.**
- **What exists.** `npcs_and_sem.md` §1 says "Under the dilate policy **a timeout** retries". §4.4 records machine-decided failures (error, refusal) as first-class cached responses.
- **What the design says.** §2.6 re-dispatches "a failed attempt" of any class, including `refused(policy)`, `context_overflow` and `empty`, to "the next eligible placement".
- **Failure scenario 1.** A deterministic policy refusal is re-dispatched across every placement in the role until the host ceiling. The world is dilated the whole time, and the thought's reply ends up from whichever placement didn't refuse.
- **Failure scenario 2 (orphaned text).** `boundaries.md` §8.4 says a ledger record pins "the model profile". With failover across placements, one experiment arm silently mixes models, recorded only per reply. Per-reply provenance is now the only record of which model answered, and the pre-registration contract is unchanged and not listed in §10.
- **Fix (unverified):** state which outcomes retry and which become the reply. Say whether experiments require a single-placement role with failover off. Update §8.4.

**A5. `inference_placement.md::§2.4` "the request at the head of the queue": one deadline queue with per-placement slots blocks the head of the line.**
- **The problem.** Selection runs for the head of a single deadline-ordered queue, and under `pinned` "if its slots are full, the request waits".
- **Failure scenario.** Role `speech` is pinned to loopback with `max_in_flight: 1`, and its slot is busy for 3 s. Role `plan` is pinned to a cloud placement with free slots. The head is a `speech` request, so every `plan` request waits 3 s behind it although its own placement is idle. Under dilate that wait lowers the dial.
- **Fix (unverified):** the design should say whether "head" means the earliest-due request whose chosen placement has a free slot. That ordering is contract: §4.4's "dispatch by deadline" invariant is restated here, not left to the builder.

**A6. `inference_placement.md::§2.1` "The host gives the worker each role's envelope at spawn": that interface has no channel.**
- **Why there is no channel.** `npcs_and_sem.md` §6.6 closes the host-to-worker message kinds (`step`, `resume`, `settle`, `consolidate`, `save`, `load`, `shutdown`) and closes the environment to an allowlist (`PYTHONHASHSEED`, the thread-count variables, `PATH`). Neither carries an envelope, and §10 doesn't list §6.6's codec as changed.
- **Failure scenario.** The builder adds an environment variable (breaking the allowlist) or an ad-hoc argument. Or the worker falls back to the bound model's `n_ctx`, which is exactly what §2.1 says it must no longer do.
- **Fix (unverified):** name the message or field and its version.

**A7. `inference_placement.md::§0` O46 "Maxim's `LLMRouter` is not on the NPC path" disagrees with OD-A14 and `npcs_and_sem.md` §6.1.**
- **The disagreement.** Both still say the request is "produced at the `LLMRouter._complete_text` cut". At `origin/main` 043eab8f, `_complete_text` (`router.py:958`) is the router's dispatch entry, which takes `_inference_lock` (`:1094`) and runs `_try_provider` failover. So the cut sits inside the object O46 says is off the path.
- **Failure scenario.** The worker still constructs an `LLMRouter`: its config load, its `CostTracker`, its drain-state reads under the agent home. Meanwhile the design claims the router's process-global state is gone. The worker also must hold "no model backend at all" (§6.6), while the router builds backends from its provider config.
- **Fix (unverified):** say precisely which half is off the path (dispatch, failover, cooldown, drain) and which is the cut, or reword OD-A14 as a question to cand. B1 about cutting above the router. Also correct §9's "No ask on the router".

**A8. `inference_placement.md::§2.2` `endpoint_ref`, `§5.1` loopback check, `§5.2`: it is not defined which process reads endpoints and secrets.**
- **The contradiction.** §2.2 says `endpoint_ref` and `credential_ref` are "names resolved only in the gateway". §5.1 says a `loopback` endpoint "must be a literal 127.0.0.1 or ::1", checked at load (the host's gate), and "the gateway checks it again". §5.2 says `owner_lan` endpoints never appear in meters or logs, yet if the host's gate reads `placement.local.yaml`, the host holds them.
- **The secrets file.** Credential resolution from "a user secrets file" happens in the gateway, outside any registered gate, contrary to "only the file gates read input".
- **Failure scenario.** The builder puts literal endpoints in `placement.local.yaml`, so the host carries private hostnames into its memory and its error reprs. Or the builder adds a third, endpoint file read by the gateway outside the gate registry.
- **Fix (unverified):** state which file holds the endpoint literal, which process's gate reads it, and that the secrets source is a registered gate in the gateway.

**A9. `inference_placement.md::§3` "Past its wall ceiling it is killed": the gateway has no liveness signal in its closed message set.**
- **The problem.** A worker's hang is defined by a missed park. The gateway multiplexes calls that legitimately run to `timeout_s`, plus `_OpenAIBackend`'s about 50 s of hard-coded retries (§1 fact 2). No message kind lets the host tell "slow" from "hung": the host-to-gateway kinds are `open`, `dispatch`, `cancel`, `shutdown`; the gateway-to-host kinds are `chunk`, `reply`, `error`.
- **Failure scenario.** An idle gateway that deadlocks is never detected until the next dispatch times out. A busy one is killed during a legitimate long call, ending every in-flight attempt as `transport_down` (see A2).
- **Fix (unverified):** message kinds are contract, so either the hang rule is defined from existing kinds (a per-attempt ceiling of `timeout_s` plus a margin) or a liveness kind is added.

**A10. `inference_placement.md::§3` "Its imports are an allowlist: `maxim.models.language` and the backend modules": the allowlist can't exclude what O46 excludes.**
- **What I read, at `origin/main` 043eab8f.** `maxim/models/language/__init__.py` imports `router.LLMRouter`. `router.py` imports `CostTracker`, `CloudAuditLogger`, `CloudRedactionFilter`, `llama_backend._LlamaCppBackend` and `cloud_dispatch` at module level. `maxim/models/__init__.py` imports `maxim.models.download`. Any backend import therefore loads the router, the llama backend, cloud audit and the download module into an unlatched process that has network access and holds keys.
- **Failure scenario.** The allowlist test passes on module names while the router's module-level state and the cloud-audit logger are live in the gateway.
- **Fix (unverified):** say whether the allowlist is meant at the level of the transitive import graph (and what it then admits), and whether import-time side effects of those modules are tested under the gateway's environment, which has no `HOME`.

### NIT

**A11. `npcs_and_sem.md::§6.3`, `§6.1` table, O13, both fold tables, and `boundaries.md` fold tables: "gateway" now names two things.**
- "The model gateway stays in the host" (§6.3) and "the gateway is the host's thinking lane" (the fold tables) use "gateway" for the lane. "The gateway sits above the backend" (§6.1) is ambiguous. `inference_placement.md` §3 uses "gateway" for a child process the lane is *not*.
- O47 deliberately leaves O13's text unchanged, but §6.3's sentence and the §6.1 row aren't in §10's list and now read as the opposite of §3.
- I list it as a NIT because O47 records the intended reading. It still invites a builder to put the transports in the host.

**A12. `inference_placement.md::§3` `open(table)`: what the gateway receives is unspecified.** If it gets the merged table (roles, order, consent classes, caps), deciding data sits in the doer. The gateway's re-check of the loopback address is a second copy of a policy decision. The contract could say the gateway receives per-placement transport configuration only.

**A13. `inference_placement.md::§4.2` "The Executor should confirm…": a design leaves a contract question to a reviewer.** "Live play never reads the cache" is what makes a model-free key safe. It should be stated as the decision and written into `npcs_and_sem.md` §4.8, which §10 already lists.

**A14. `inference_placement.md::§2.2` vs `§2.4`: which file enables `spill` is unclear.** §2.2 puts "each role's policy" in the shipped file and "opt-ins" in the local file.

**A15. `inference_placement.md::§5.3`: abandoned calls and the cap message are not covered.**
- Spend on cancelled or abandoned calls isn't stated. Their tokens still bill, so the cap can be overrun unless `reply(outcome=cancelled)` carries token counts that count toward spend.
- The "host status message" is a new protocol message (`boundaries.md` §9.1's one schema), and §10 doesn't list it.

## What I checked

- **Charter and rules:** `docs/code_review.md` (rounds, lenses, design reviews, agent readers) and CLAUDE.md's engineering standards.
- **The design and the diff:** `docs/design/inference_placement.md` in full, and every edited hunk in `git diff 814dea9..04ab810`.
- **Layers and gates:** `boundaries.md` §2.1, §2.2 (layer table, skip-layer rules), §5.3 gate rows, §6.3 manifest, §7.1, §8.1, §8.4. `pyproject.toml` `[tool.importlinter]` contracts (`maxim-through-adapters` allows only `simcore.adapters.sem`). The present `src/simcore` tree (no `host` package yet).
- **Decisions:** in `npcs_and_sem.md`, O4, O6, O6a, O13, O16 and O18; §1 ("Where wall time remains": only timeouts retry; "never silently frees a worker"); §4.4; §4.8; §6.1 table; §6.2; §6.3; §6.6 (codec kinds, environment allowlist, "maxim only in workers"); §11.1.
- **`realtime_lanes_coop.md` §4.1 and §4.3.** The thinking lane as a worker pool, and CP-4's "timeout only frees its worker". The second is already superseded by `npcs_and_sem.md` §1, so it is not orphaned by this design. The slot-holding rule (§2.5) agrees with §1's "never silently frees a worker". I judged it honest accounting, not a band-aid: it hides no symptom, and it is metered.
- **Orphans:** I searched `docs/` (excluding `reviews/`) for "model profile", "stays in the host", "gateway", `consented_router` and `LLMRouter`. This found A4's §8.4, A7, A11 and the fold rows.
- **Word budgets.** The new document is 4,204 words (limit 6,000). `npcs_and_sem.md` went from 23,788 to 23,786, `boundaries.md` from 13,983 to 13,982, `architecture.md` from 2,829 to 2,828: none grew.
- **Maxim at `origin/main` 043eab8f** (read with `git show` only):
  - `src/maxim/__init__.py` and `models/__init__.py`.
  - `models/language/__init__.py` and the import lines of `router.py`.
  - The method list of `router.py`: `_complete_text` at `:958`, the lock at `:1094`, `_try_provider` at `:1367`.
  - The import lines of `anthropic_backend.py`, `openai_backend.py` and `maxim_peer_backend.py`, and `anthropic_backend.py:223-241`, `:325-335`.
  - The `LLMResponse` fields in `types.py`.
- **Areas with no finding:**
  - Placement never crossing `AgentPort` (§2.1).
  - Consent and eligibility kept in the lane (O18, O49).
  - Spend kept out of cognition (§5.3).
  - Wall time never reaching world time (§6.1, consistent with O4, O11 and O16).
  - The architecture.md edits, which match `npcs_and_sem.md` §11.1.
  - The `checklists.md` move of tests out of the design, which matches the contract rule.
  - The lessons entry, which matches the design.
