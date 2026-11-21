**Verdict:** the fold fixes most of round 1: the package and importer, the classify/decide split, per-placement queues, liveness and the endpoint holder are all done. Two things are not done. A1's layer placement is incomplete: there is no layer row for the new adapter, and the channel codec has no home. The fold also adds four contract inconsistencies: cooldown against pinned-waits, ceiling-kill attribution, health tunables in a refused file, and a stale rerun manifest in `boundaries.md` §6.3. None is a BLOCKER. 0 BLOCKER, 5 SHOULD-FIX (all contract), 7 NIT.

## Status of round-1 findings (read from the tree at caca211)

| # | Status | Evidence |
|---|---|---|
| A1 | **open (narrowed)** | Fixed: the package (`inference_placement.md::§3.1` names `engine.adapters.inference`), the `boundaries.md::§8.1` row, the `npcs_and_sem.md::§6.6` sentence ("workers and inference gateways"), the per-user path (`IP::§2.2`) and the gate list (`IP::§3.5`). Not fixed: the layer. `boundaries.md::§2.2`'s committed layer table has no row for `engine.adapters.inference`, and no section says where the host half of the gateway codec lives. See D1. |
| A2 | fixed | `IP::§2.6`: the gateway classifies, the lane decides, and each outcome carries a placement, request or host attribution. Gateway death and kills are host-attributed and start no cooldown (`§2.7`). |
| A3 | fixed | `IP::§2.6`: `ok` now covers empty content with a non-empty `stop_reason`. `failed(empty)` is narrowed to empty content plus empty `stop_reason`, and declared a stand-in until OD-I9. The marker form is unnamed (D8, a NIT). |
| A4 | fixed | `IP::§2.6`: request-attributed outcomes are never retried, and the text says this is a change from `npcs::§1`, which was edited. `IP::§4.3` pins single-placement experiment functions with failover off. `boundaries::§8.4` was edited (but see D5 for §6.3). |
| A5 | fixed | `IP::§2.4`: per-placement queues, and a slot goes to the earliest-due request that may use it. |
| A6 | fixed | `IP::§2.1`: envelopes go in the `load` frame as a versioned field, never through the environment. `npcs::§6.6` lists it. Residual: whether a freshly spawned worker ever gets `load` (D6). |
| A7 | fixed | OD-A14 and the upstream draft now say "without building an `LLMRouter`". `IP::§1.2` and `§9` OD-A24 say the router is entirely off the path. The cut is the call site. |
| A8 | fixed | `IP::§2.2`: three files, and `endpoints.yaml` is read by the gateway only. `§5.2` puts the loopback check in the gateway. `§5.4`: the host holds neither endpoints nor keys. `§3.5`: the credential store is a gate. |
| A9 | fixed | `IP::§3.3` adds `ping`/`pong`. `§3.4` defines a hang: past `call_ceiling_s`, or no `pong` within `ping_ceiling_s` while an attempt is in flight. An idle deadlock is caught at the next dispatch, which is bounded. |
| A10 | fixed | `IP::§3.2`: the allowlist is the transitive module set at the locked pymaxim, with a no-effect test under a test `HOME`. Residual: that test as written contradicts the gateway's own reads (D9). |
| A11 | fixed | `npcs::§6.3` now reads "Model calls stay host-side, in inference gateways (O47)". The fold tables are left as history, which is acceptable. |
| A12 | fixed | `IP::§3.3`: `open(placement)` carries transport settings only, with no function data. |
| A13 | fixed | `IP::§4.2`: live play writes and never reads, with a poisoned-entry test. `npcs::§4.8` was edited. |
| A14 | fixed | `IP::§2.2`: `functions.yaml` holds the default policy, and the player's `placements.yaml` may turn on `spill`. The table text is inconsistent with this (D10, a NIT). |
| A15 | fixed | `IP::§5.5`: abandoned and killed calls count at input plus `response_reserve`, and the cap is soft by a stated bound. `§5.6`: `inference_status`, deferred to `tile_and_client.md` §3 at `phase1/protocol`, as named in `§10`. |

## New findings

### SHOULD-FIX

**D1. `inference_placement.md::§3.1` and `boundaries.md::§2.2`: the new adapter has no layer, and the host half of its codec has nowhere legal to live. (contract)**
- **What the text says.** §3.1 puts `engine.adapters.inference` "in §2.2's adapters layer, beside `engine.adapters.agents`". But §2.2's layer table, which is "the order committed, checked red-first", has no row for it, and §10 doesn't list §2.2 as changed.
- **The conflict.** §3.1 also says "the host never imports it", yet the host must encode `dispatch` and decode `reply` frames (§3.3).
  - If the codec lives in `engine.adapters.inference`, the host imports the `maxim`-importing package.
  - If the codec lives in `engine.host` (layer 8), the gateway (layer 7) imports upward, and the layers contract goes red.
  - "Host never imports it" also has no named contract (a forbidden `engine.host` ↛ `engine.adapters.inference`).
- **Failure scenario.** The `phase1/agents` builder puts the frame types in the adapter's `__init__`, and `engine.host` imports them. The `protected` contract stays green, because it checks only direct importers of `maxim`. The host now transitively loads `maxim.models.language` (router, `cloud_audit`) whenever the package's init pulls in the entry module. That reverses O47's reason, with a green gate. This is A1's original failure mode, one level down.
- **Needs:** a §2.2 row (sub-layer) for the adapter. A named maxim-free home for the channel types that both sides may import (for example a sibling module, or `engine.intents`-level values). The forbidden contract that holds "host never imports it".

**D2. `IP::§2.3`, `§2.6`, `§2.7`, `§2.4`: cooldown makes pinned's "wait on load failures" impossible. (contract)**
- **The rules, as written.**
  - `overloaded` and `call_timeout` are placement-attributed (§2.6 table).
  - A placement-attributed outcome starts a cooldown (§2.7).
  - A cooling placement is not eligible (§2.3, item 2).
  - Under `pinned` a request may use only "the first eligible placement" (§2.4).
- **The contradiction.** After one `overloaded`, placement 1 is ineligible, so the first eligible placement is placement 2 and the request moves. §2.6 says it "waits for the same placement until the liveness ceiling". §11 records that the owner kept this default. The two paths give different models for the same NPC under load, which is exactly what O48 and BF-3 exist to prevent.
- **Failure scenario.** A burst overloads the loopback server. Every pinned `speech` request fails over to `third_party` (single-player opt-in) or to `owner_lan`, and capability follows load.
- **Needs:** one rule for whether a load-symptom cooldown removes eligibility for pinned requests. For example: load outcomes delay, they don't make a placement ineligible.

**D3. `IP::§2.5`, `§3.4`, `§2.7`: a ceiling kill is host-attributed, so a hanging provider never cools down, and "down for the session" has two triggers that disagree. (contract)**
- **Attribution.** A call past `call_ceiling_s` kills the gateway, and every attempt ends `failed(unreachable)`, "attributed to the host" (§3.4). The call that caused the kill is a provider symptom, yet it starts no cooldown. §2.6 defines failover under `pinned` only for placement-attributed outcomes, so whether a host-attributed retry moves or waits is undefined.
- **Down for the session.**
  - §3.4: after `max_restarts` restarts in a window, which counts every kill.
  - §2.7: a gateway that "keeps failing to start".
- **Failure scenario.** A cloud endpoint accepts connections and then stalls. Each ceiling kill takes down every in-flight call on that placement (up to `max_in_flight`), with no cooldown to steer `spill` away. Then either:
  - the placement stays in rotation for ever (by §2.7's reading); or
  - it goes down for the whole session after a few stalls (by §3.4's reading).

  Two builders will pick different readings.
- **Needs:** the triggering attempt attributed to the placement (the others to the host), and one definition of down-for-session.

**D4. `IP::§2.7` and `§4.3`: the health tunables sit in a file that a rerun refuses on, so a change that can't affect a rerun breaks it. (contract)**
- **The placement.** Cooldowns come "from `functions.yaml`'s table". `functions.yaml` is in `data/agents/`, whose digest "refuses on mismatch" (§4.3, `boundaries::§6.3`). A rerun never dispatches, so health can't change anything in it (§6.1: placement changes wall time only).
- **Failure scenario.** Someone tunes a cooldown, and every recorded tier-2 rerun is refused. The data that is truly placement-side (placements, cooldown, `ping_ceiling_s`, `max_restarts`) is split across a refused file and a recorded file with no stated reason.
- **The table's key is also unclear.** Cooldown is a placement's state, but the table sits in a per-function file. If it is per function, two functions on one placement can start different cooldowns for the same outcome.
- **Needs:** the health table moved to the recorded side (`placements.yaml`), keyed per outcome.

**D5. `boundaries.md::§6.3`: orphaned text contradicts `IP::§4.3`. (contract)**
- **The text.** §6.3's rerun manifest still lists "the placement table's digest and role envelopes (reported, never refused: `inference_placement.md` §4.3)".
- **The conflict.** `IP::§4.3` now says the envelopes and `functions.yaml`'s digest **refuse** on mismatch, and only the placement digest is reported. The text also still says "role". `IP::§10` lists `boundaries.md` §6.3 as changed, but the fold diff has no §6.3 hunk.
- **Failure scenario.** The manifest builder follows `boundaries.md`, the authority for the manifest, and reports envelopes without refusing them. A rerun then runs with different envelopes, so different `max_tokens` and prompt budgets, and stays silent.

### NIT

**D6. `IP::§2.1`, `npcs::§6.6`: envelopes ride on `load`, but nothing says every worker receives `load` before its first `step`.** A freshly authored NPC with no saved home may never be sent `load`, and would then run without envelopes (A6's scenario). One sentence fixes it: every spawn begins with `load`, or the envelopes move to a spawn-time frame. (contract)

**D7. `IP::§2.6`, row `truncated(stream_broken)`: under O50 (`stream=False`) the row fires on any non-streamed reply whose server omits `finish_reason`.** At 043eab8f the peer backend sets `stop_reason = str(first.get("finish_reason") or "")` (`maxim_peer_backend.py:958`). A llama-server-compatible server that leaves the field out would make every successful reply `stream_broken`. That outcome is placement-attributed, so the placement cools down after every reply. Phase 4's fake-server test should cover a missing `finish_reason`. (mechanism, Phase 4 checklist)

**D8. `IP::§2.6`, `failed(empty)`: "marked in code when built" names no marker target.** The lint accepts `TEMPORARY(phase3)` only if its file is listed under Phase 3 in the roadmap. OD-I9 is "not in O29's subset", so nothing guarantees it lands before Phase 3 closes. The checklist should name the marker and the roadmap listing, and say what happens if Phase 3 closes without OD-I9. (mechanism, `phase1/agents` checklist)

**D9. `IP::§3.2`, the no-effect test: "no file reads … outside the gateway's home" forbids the gateway's own gates.** The gateway reads `endpoints.yaml` from `data/placements/` and the player's config directory, the credential store (possibly the OS keychain), and module imports from site-packages. The test has to name those exceptions (or the host stages copies in the home). Otherwise it is either unpassable or written loose. (mechanism, checklist)

**D10. `IP::§2.2`: the files table says `functions.yaml` "holds … each function's policy", and the next bullet lets the player's `placements.yaml` set `spill`.** It then claims "no precedence rule is needed", but that cross-file override is a precedence rule. The table should list the override under `placements.yaml`. The table also doesn't say whether the player's `endpoints.yaml` replaces the shipped one whole, like `placements.yaml`. If it merges instead, a replaced placement table can reference ids whose endpoints come from the shipped file. (contract-adjacent; one line)

**D11. `IP::§2.4`, `spill`'s "in list order" means nothing when selection happens at slot grant.** When placement 2 frees a slot, the earliest-due request takes it, even if placement 1 frees a slot a moment later. Slot assignment within a `server` group is also unstated. (mechanism, checklist)

**D12. `IP::§3.1`: the text mixes `simcore.adapters.sem` with `engine.*`.** The import contract will name the package as it exists then. `ping_ceiling_s`, `max_restarts` and the backoff cap have no data file, against "tunables live in `data/` YAML". This folds with D4. `boundaries::§5.3` lists the new gates only as a pointer inside the response-cache row, so a reader of the registry looking for the gateway channel won't find it. (mechanism, `phase1/agents`)

## What I checked

- **The fold diff.** `git diff 274f297..caca211` over all 12 files. I read `inference_placement.md` v2 in full: 5,988 words against the 6,000 limit, so no headroom for further folds.
- **Round-1 inputs.** My round-1 report and `fold_round1.md`. I read the claims as claims and set each status above from the tree.
- **Layers and contracts.**
  - `boundaries.md` §2.1, §2.2 (layer table and skip-layer rules), §3 (the sealed sets, the agent step path), §5.3, §6.1, §6.3, §8.1, §8.4, §10.
  - `pyproject.toml` `[tool.importlinter]`: layers, sealed-core, and `maxim-through-adapters` as cited.
- **Orphans.** I grepped `docs/` (excluding `reviews/`) for "model role", "role's envelope", "model profile", "budget, timeout, model error", `consented_router`, the bound model's `n_ctx`, and every `inference_placement` cross-reference. That found D5. The other references (`npcs` §1, §4.4, §4.8, §6.1, §6.3, §6.6, §12.2; `boundaries` §5.3, §6.1, §8.1, §8.4; the `world_model` row 10; `architecture.md`; roadmap OD-A14 and OD-A23–A25, OD-I9 and OD-I10; the foundations plan ids; checklists; B5; lesson 29) agree with v2.
- **The band-aid rule.** `scripts/lint_markers.py` (`TEMP_TARGET`, the phase-section rules) for D8.
- **Maxim at `origin/main` 043eab8f** (`git show` only): `stop_reason` assignment in `maxim_peer_backend.py` (`:953-982`, `:1012-1151`), `openai_backend.py` (`:542`, `:559-624`) and `anthropic_backend.py` (`:467`, `:487-568`), for D7 and for A3's `ok` row. The non-streamed paths set `stop_reason` from the provider's field, so A3's narrow `empty` holds wherever the provider fills that field.
- **No finding:** the decide/do split is clean. The gateway classifies and enforces the address checks it alone can see, and reports the proxy in `ready`. The host stamps provenance and decides eligibility, retries and cooldown. One process per placement as the fault boundary (O53) agrees with `npcs::§6.6`'s spawn rules. The per-speaker consent rules (O51) sit wholly in the host. The lessons and roadmap entries match the design.
