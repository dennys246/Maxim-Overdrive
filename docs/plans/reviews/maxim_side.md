# Review: the Maxim side of the foundations plan (2026-11-17)

Lens: the Maxim side. Read against `phase1/design-v2` at `72bf36c` (`docs/plans/foundations_plan.md` §4, `docs/roadmap.md`
Phase 3 and 4, `docs/maxim_upstream/embeddable_agent_DRAFT.md`, `docs/design/reviews/maxim_response_1/correction_1.md`)
and Maxim `origin/main` `6fee7377`: `docs/plans/overdrive_refactor_candidates.md` (#1688; written 2026-11-16, its
citations pinned to `98c6889c`, three-lens review folded), #1687 (`_offline.py`), #1396 (router consent), #1657/#1659,
and the `roadmap_1_4.md`, `roadmap_1_3_x.md`, `baseline_floors.md`, `outstanding.md`, `DECISIONS.md` diffs since
`7084f561`. Every finding below was checked on `6fee7377` with `git show`/`git grep`. Read only; nothing else edited.

Maxim's candidates doc uses its own ids (A1–A5, B1–B3, C1–C5). Below, "cand. A3" means the candidates doc's A3, never
our pre-`OD-` "Was" ids (which also say A1, B1, C1: see N4).

## 1. Item-by-item reconciliation

| Our id | In the candidates doc? | Where, line | What changed or disagrees |
|---|---|---|---|
| OD-I1 | Yes, filed **#1684** (open) | cand. A3, 1.3.x | Done; our plan §4 still lists it as "pending filing" |
| OD-I2 | No | — | Consistent with our downgrade to a docstring nit |
| OD-I3 | Yes, filed **#1685** (open) as cand. A5 | 1.3.x, order step 1 | Done. Cites `similarity/semantic.py::EmbeddingStore.load:662` (verified) |
| OD-I4 | Yes, filed **#1686** (open) | — | Done |
| OD-I5 | Yes, as a **private security advisory** (per Maxim's `SECURITY.md`), not an issue | "Filed alongside" | Maxim proved it end to end, more broadly than we framed it (details redacted 2026-11-17; private notes). Our public repo spelled out the mechanism (B2 below) |
| OD-A1 (#1361) | Yes: cand. A3 "rides on" #1361 and disclaims decay, eligibility and windows | A-post with 1.3.6 | Agrees. #1361 S3b (not S3a) moves anchor age/expiry/prune; S3a moves trace decay |
| OD-A2 | Yes, cand. A3 (perceived-time port + host injection into `ExperienceClockDriver`) | A-pre own clock; A-post 1.3.6 | **Disagrees (S4):** on a robot the machinery clock **is** the driver, not the wall clock; no new `AgentTime` type (rides on `ExperienceClockDriver`); M72 extended rather than a second static ban. "One plan or two" is in its *Not decided* list |
| OD-A3 | Yes, cand. A3 prompt guards | A-pre | Wider than ours: **seven** prompt sites (adds `_build_engage_prompt` `:2400/:2417`, `exec_agent.py:1189` `time.localtime`, `tools/http_fetch.py`, `tools/reachy.py`), plus recall timing (`retrieval/temporal_signal.py:101`, TZ-dependent `fromtimestamp` in `temporal_signature`/`similarity/signature.py`). Lint list adds `datetime.fromtimestamp` |
| OD-A4 | Partly, cand. A3 machinery reads | A-post | `SensorReading` stamping not named; adds tool duration (S5), hippocampus consolidation pressure, memory-agent salience decay, stale-proposal age, `time.monotonic` stamps saved across restart |
| OD-A5 | Split | — | The 30 s window and temporal windows are #1361's (cand. A3 "does not own"); `TemporalSignature` similarity stays on the host calendar **by design** (#1361 §(g)). Our "phase source" half needs a named argument against §(g) (B1 below) |
| OD-A6 | **No** | — | Reaction/pain gates on the injected clock (after #1200) is absent; #1361 §(g) keeps "PainBus refractory, reflex cooldowns" on the wall on purpose. Unacknowledged |
| OD-A7 | Yes, cand. A2 **= #1305 widened** (a 1.4.0 release gate, `1305.owned-rng`) | 1.4.0 | Derivation is `random.Random(stable_hash_64_signed(f"{base_seed}:{agent_id}:{stream}"))` by Maxim, vs our §6.6 (host hands an integer per `(npc_key, stream_key)` from a `SeedSequence`) (S6). Adds: `seed_all` never on the embedded path, and every `get_global_seed()` consumer needs an explicit seed (`similarity/semantic.py:205` silently becomes `42`). Our roadmap row still cites the non-existent `stable_hash_64(seed, agent, stream)` |
| OD-A8 | Partly: cand. A3 (NAc ids `:1163`, event time `:1162`, uuid4) and B2 | A-post | `FailureMode.last_fired` not named |
| OD-A9 | **No** | — | `DefaultNetwork.step(now)` / #1263 absent |
| OD-A10 | Named only in cand. B1's heading ("OD-A10–A15") | 1.5 hybrid src phase | The heading lumps OD-A11/A12 into B1 while A1/A4 place them on their own clock (N3). Gated by the **front gate SF-2** (B3 below) |
| OD-A11 | Yes: cand. A4 "embedded roster" (engineering); robot default is cand. C4 (prereg) | own clock | Agrees |
| OD-A12 | Yes, cand. A1, **merged with #984** | 1.3.x/1.4, own clock | Scope is the checked registry `cli_utils.py::_GLOBAL_PATHS` (`:608`, verified), not "ten families"; adds writers outside it, cwd-resolved paths (`models/language/config.py` reads `llm.json` from `cwd/data/util`: collides with Overdrive's own `data/`), and the process-global `filesystem_policy.get_effective_cwd`. ConceptExtractor thread not mentioned |
| OD-A13 | = OD-I3 | — | — |
| OD-A14 | Yes, cand. B1 + B3 (priority/deadline on the request value; router priority queue withdrawn) | after 1.4.0, 1.5 hybrid src phase | Agrees. Cut at `LLMRouter._complete_text` and the `LLMProposal` parse; ride on `utils/cancellation` + `_complete_text_abandonable` first |
| OD-A15 | Yes, cand. B1 | **"the 1.5 hybrid line's src phase"**, one design with hybrid §A.1b, with the decomposition slices | Our O15a says Phase 4 waits for "1.4.0"; Maxim's line is later (S1). Parity guard adds recorded replies from Exp 49 and Exp 60 |
| OD-A16 | Yes, inside cand. B2's A6 | with #1150 | Adds: it **changes credit, so it fires T1-4's re-run trigger walk** |
| OD-A17 | Yes, cand. A4 | own clock, after the front gate; cancel bypass with B1 | **Front gate SF-2** owed by us (B3). "Fix at the root where the robot path has the defect too": prefetch's swallowed `find` refusal is a robot defect; the shortcut on any `triggering_input` is an open owner question. Adds `exec_agent.py:1495` `time.sleep` in `_propose_goal`, `tools/base.py:811`, the exec agent's ungated WORKSPACE section. Parse-failure bypass moves to B1 (ours: tier A). Our "model calls outside `think`" (AdaptivePlanner, ToolPainBridge, FearAgent) is not in it: it predates `correction_1.md` |
| OD-A18 | Yes, cand. B2 **= #1150** | 1.3.6 or after | Three callers, four booking paths; full side-effect digest; **two blockers we lack**: tool duration on the wall clock feeds an NAc valence (S5), and `environment.step` runs inside dispatch (`tool_dispatch.py:1516`). Depends on **cand. A3 A-post**, not on OD-A19 (our row still says "After OD-A19") |
| OD-A19 | Not present (correctly) | — | The candidates doc never carried the error |
| OD-B1–OD-B13 | **No** | — | None of the 1.4-line items, including Exp 64a's prerequisites OD-B1–B7, which our Phase 3 exit requires (S9) |
| OD-X1, OD-X2 | No | — | — |
| OD-C1–OD-C10 | **No** | — | No SEM additive item. O5 calls SEM refinement a priority; Maxim hasn't acknowledged one (S9) |
| OD-H1 | Indirectly: §Cautions (transfer checks, the OD-HX5 pattern; venue is the hybrid owner's decision) | tier C | — |
| OD-H2 | Yes, cand. C2 | tier C, prereg | Agrees |
| OD-H3 | No | — | — |
| OD-H4/H5 | Yes, cand. C5, "agreed shape" with our citations | tier C; "drafted now or after v1 evidence" not decided | Agrees on shape |
| OD-H6 | Only the escalation half, as cand. C3 | tier C | **Disagrees (S10):** #1361 §(g) keeps `llm_submit_interval` on the wall "on purpose", so Maxim reads it as a design change, not a clock fix; our "machinery clock now" half is not accepted |
| OD-HX1–HX5 | HX2 and HX5 cited | — | — |
| OD-WC1, OD-EA* | Guards differ in form | — | cand. A1 guard ≈ OD-EA2; B1 parity ≈ OD-EA5; A2 ≈ OD-EA6; A3 planted-render ≈ OD-EA11 but without "the sentinel goes in the machinery clock" (our correction covers it). OD-EA12 has no counterpart and is to be replaced anyway |

**What the candidates doc has that our plan lacks**, beyond the rows above: the front gate SF-2 (B3); two limits on the
replay gain (LLM pairing ends at the first diverging token, so replies must be recorded; a paired analysis estimates
d_z, not d); sequencing B2 with R4's routing audit and the 1.4.0 function gate `1323.functions-1000`; touch-it-shrink-it
on four pinned functions; CC3 docstrings and `changelog.d` fragments; M89 slug rules; "scope pressure" items that need a
written reason (the port, the entry point and static ban, the continuation, the write-proposal values); its five
*Not decided* items; #1687 filed because "Overdrive's workers depend on the latch".

**Errors `correction_1.md` corrects:** the candidates doc carries **none** of them. It has no OD-A19, no 13× figure, and
no wall-clock trace-decay claim; its B2 cites `nac.py:1162` as NAc's **event time** (correct: `now = time.time()` in
`record_event`). It names neither the model calls outside `think` nor the `stable_hash_64` error, which the
correction adds. But the correction has errors of its own (B1).

## 2. Findings

### BLOCKER

**B1. `correction_1.md`, just sent, has a duplicate question and a wrong number.**
`correction_1.md::What is still true` asks "Is [the anchor host-clock read] in S3a's scope?". Maxim's own #1361 already
answers it. `experience_clock_decay.md` §(c), **S3b**, "Eligibility and temporal anchors on ONE clock", moves pending
events and anchors, and the age checks in `record_event`, `_record_outcome_locked` and the anchor prune (`nac.py:3714`'s
`time.time()`), onto NAc's `_experience_us`. §(c) and §(g) then keep `TemporalSignature` similarity (`nac.py:3625-3640`'s
`TemporalSignature.now()`) on the host calendar **by design**. Our own `world_clock_release_DRAFT.md:132` and `:204`
already say "after #1361 S3b moves its windows to experience time". So this is a fourth upstream ask that duplicates
Maxim's plan, from the line that just made "search Maxim first" a standard (B22). Separately, "about 4.75 s on the 10 Hz
figures" is wrong: 4.75 s is τ_eff 9.49 passes × the **0.5 s step of the 2 Hz** fixture regime (#1361 §Tau
conversion; our `npcs_v3_1/determinism_bio.md:323` has it right). At 10 Hz it would be 0.95 s.
*Failure scenario:* Maxim spends a design round re-answering S3b and reads a time constant that is off by 5×, and our
credibility on the next correction falls further.
*Fix:* send a short erratum before Maxim acts. (1) S3b covers age, expiry and prune; withdraw the question. (2) The
remaining half is a recorded Maxim decision. If we object, argue against #1361 §(g)'s row "SCN phases,
`TemporalSignature` similarity | host calendar by design" by name: for an embedder, delayed credit then depends on the
host's time of day, which contradicts O4 and OD-B13. Make it a Phase 3 item. (3) Change "10 Hz" to "2 Hz fixture".
Update plan §4 "Owed to Maxim" and `npcs_and_sem.md:1207` to match.

**B2. OD-I5 is a security issue Maxim holds privately, and our public repo spells out how to exploit it.**
The candidates doc files the cloud-redaction defect as a draft private advisory under `SECURITY.md`: "the details stay
in the advisory until the owner publishes it". Both repos are public (checked: `gh repo view`). Our pushed branch
publishes the mechanism in `docs/design/reviews/maxim_response_1/trust_boundary.md` and `docs/roadmap.md` OD-I5
(redacted 2026-11-17). Plan §4 lists OD-I5 as "pending filing" and roadmap
Phase 3 as "to file now", which invites a public issue.
*Fix:* the owner decides on disclosure; this review can't. At least: (1) re-word OD-I5 everywhere as "reported privately
(advisory); details withheld", and stop repeating the mechanism in new documents. (2) Tell the advisory that the
mechanism is already public on Overdrive PR #4, so its timeline accounts for that. (3) Note that the defect is wider
than guest text: `\n` reproduces it too.

**B3. The candidates doc puts a front gate on the embedded mode, and nothing of ours answers it.**
Cand. A4: "A host-driven agent is a **new runtime mode**, not a refactor. Before any of this is built, Overdrive's
embeddable-agent plan must answer: why can't the 1.1.4 world seam (`archive/world_seam_1_1_4.md`), with Maxim owning
the loop, serve Overdrive?" Order step 3 makes A4 wait on it. No document on `72bf36c` mentions the 1.1.4 world seam
(`grep` finds none). O6, which drops mode (a), is our own decision. It is not an answer Maxim has accepted under its
process.
*Failure scenario:* OD-A17, and with it the embeddable plan, OD-A10 and Phase 4's start, stall at Maxim's plan review.
*Fix:* add a "Why not the 1.1.4 world seam" section to `embeddable_agent_DRAFT.md`. Base it on O3/O6/O6a's evidence:
host-owned time, a world-time clock, no agent thread, determinism, the guest trust boundary. Add it to plan §3 as a
step before Phase 3 filing and to §4 as "owed to Maxim".

### SHOULD-FIX

**S1. Phase 4's timing is later than the plan says.** O15a, plan §3 step 11, §4 and roadmap Phase 3/4 say real NPCs
wait for "the 1.4.0 cut". Cand. B1's line is "**the 1.5 hybrid line's src phase**", as one design with hybrid §A.1b,
sequenced with the decomposition slices, gated on parity with Exp 49/60 recorded replies. Cand. B2 (#1150) is "1.3.6 or
after", after cand. A3 A-post. 1.4.0 itself still waits on B4 (T1-2's re-fire) and the `1305.owned-rng` gate. The
`roadmap_1_4.md` and `roadmap_1_3_x.md` diffs only change T1-16's status and move no release date. *Fix:* restate the
dependency as "1.4.0, then cand. B1 in the 1.5 hybrid src phase", and record it as the Phase 4 critical path.

**S2. The plan's Maxim-side state is stale.** Plan §4 "Pending from Maxim" lists the candidates doc and the filing of
OD-I1/I3/I4/I5. All of that landed: #1688 merged; #1684, #1685, #1686 open; the advisory drafted; #1687 filed and
**closed**. Roadmap Phase 3 says "the rows below are proposals until it lands", and it has landed. *Fix:* add a
mapping column (our id → Maxim id/issue/line) from §1 above, re-pin Phase 3 to `6fee7377`, and move the plan's
§4 entries to "done".

**S3. OD-A19 is withdrawn but still referenced.** Roadmap OD-A18 still says "After OD-A19". Phase 4 still says "OD-A1 to
OD-A19". `embeddable_agent_DRAFT.md` lists OD-A19 in its ids and v2.1 line, has PR 4a, and has OD-EA12 "(OD-A19)".
`npcs_and_sem.md:1004` still has "OD-A17–OD-A19". *Fix:* make OD-A18 depend on "#1361 S3a/S3b and cand. A3 A-post"
(the candidates doc's own dependency), delete PR 4a, and replace OD-EA12 as plan §3 test 5 says.

**S4. The machinery-clock design disagrees with Maxim's.** OD-A2 says "robots default both to the wall clock" and adds
an `AgentTime` type and its own static AST ban. Cand. A3 says the robot's machinery clock **is**
`ExperienceClockDriver`, adds only an injection point and the perceived-time port, and extends M72 "rather than adding
a second lint". *Fix:* revise OD-A2 and `world_clock_release_DRAFT.md` to ride on the driver and M72, or argue the
difference by name. The second option is weak: Maxim's version is less new surface.

**S5. A determinism blocker we don't list: tool duration on the wall clock.** `runtime/tool_dispatch.py:1343`
(`exec_elapsed = time.time() - exec_start`) feeds `_observe_energy_cost` (`:620-633`), which sets the NAc valence to
NEGATIVE above 2.0 s. On a real NPC, NAc state and a valence sign then depend on host speed, which breaks OD-EA5 and our
bit-identical promise. Maxim says cand. B2's parity guard "cannot pass until this is resolved". `environment.step`
(`:1516`) inside dispatch also conflicts with host-owned stepping. Neither appears in our documents (`grep`). *Fix:* add
both to OD-A4/OD-A18 (a host-supplied, modelled duration in world time), to `npcs_and_sem.md` §12.2's divergences, and
to `phase1/agents`' red-first list as a test the scripted double can already pin.

**S6. Keyed substreams: two derivations.** Ours (§6.6, about `:322-338`): the host hands one integer per
`(npc_key, stream_key)` from a `SeedSequence` tree. Maxim's (cand. A2 = #1305): Maxim derives
`stable_hash_64_signed(f"{base_seed}:{agent_id}:{stream}")`. *Fix:* pick one with Maxim inside #1305's scope change
(whether A2 widens #1305 before 1.4.0 is in its *Not decided* list). Fix roadmap OD-A7's non-existent
`stable_hash_64(seed, agent, stream)`. Add `semantic.py:205`'s `or 42` to the worker's required explicit seeds.

**S7. #1687 makes real NPCs POSIX-only.** On `6fee7377`, `engage()` raises `OfflineUnsupportedPlatform` off POSIX
(`docs/agents/llm-routing.md`; guard `test_offline_latch_unit.py::test_engage_refuses_on_an_unsupported_platform_and_changes_nothing`).
O13's worker "engages the latch after the channel opens" (`npcs_and_sem.md` §6.6), so on Windows no real-NPC worker can
start at all, single-player included, not only guest sessions. Windows is the main Steam platform. Also, the worker
channel relies on a documented latch residual ("connections opened before the latch"); if Maxim closes it, every worker
loses its pipe. *Fix:* (1) Record a known gap: real NPCs on macOS/Linux only until Maxim verifies a Windows refusal set.
(2) The host refuses to spawn a worker off POSIX with a typed error, tested. (3) Add a worker test pinning that the
pre-opened `socketpair` survives `engage()`, and tell Maxim that residual is load-bearing. (4) A Phase 3 item if Windows
NPCs are wanted before Phase 8.

**S8. #1396 changes what O18's local-only default must guard.** If the host's thinking lane builds its model through
Maxim (the plan doesn't say; `npcs_and_sem.md` §4.5 and §6 leave the backend open):
- a router with a cloud or peer tail "keeps serving from it when its local file is missing, as before, without
  asking", which silently breaks O18;
- `build_primary_router`'s preflight `_ensure_lane_profiles_available` "still asks wherever stdin is a terminal, on any
  thread" (a filed residual), so a world server started from a terminal can block a lane thread on a prompt;
- a named missing model now refuses with the typed `LocalModelUnavailable`;
- `load_llm_config` reads `llm.json` from `cwd/data/util` (cand. A1).

*Fix:* specify the lane's construction: `models/download.py::consented_router` (never asks), no cloud or peer tail in
guest sessions by construction, the model provisioned before play, stdin not a terminal. Make O18's gate test "a missing
local model with guests present refuses (typed, shown in the client), never falls to a remote tail".

**S9. Large parts of Phase 3 have no answer from Maxim.** OD-B1–B13 (Exp 64a's prerequisites OD-B1–B7 are a Phase 3
exit condition), OD-C1–C10 (O5's "priority"), OD-A6, OD-A9, OD-H3, OD-X1/X2 and the model calls outside `think` appear
nowhere in the candidates doc. *Fix:* plan §4 should say so, and say how each reaches Maxim: a second candidates round,
direct issues, or the drafts as plans.

**S10. OD-H6 against #1361 §(g).** Maxim kept `llm_submit_interval` on the wall on purpose ("loop scheduling") and
treats our change as tier C. Under host-called `think`, the submit cadence is the host's anyway. *Fix:* drop OD-H6's
"machinery clock now" half into cand. B1, where `embeddable_agent_DRAFT.md` PR 5 already puts it, or argue against
§(g)'s row by name. Don't leave it as an engineering ask Maxim has already declined.

**S11. Smaller mismatches to align.**
- The parse-failure bypass: ours is in OD-A17 (tier A); Maxim's lands with cand. B1. Harmless, since Phase 4 waits for
  B1, but the rows should agree.
- The short-question shortcut: Maxim asks whether it is a robot defect. Our evidence that it fires on any input (TBR-13)
  says yes. Say so, since the no-band-aid rule favours a root fix over an embedded-only bypass.
- `exp64_cradle_conduct_prereg_DRAFT.md:13` still calls T1-16 STALE. It is EARNED (narrow) as of 2026-11-13, on Exp 63c,
  with `floor: not measured`, an owner reading of BF2 that "is not a precedent" (`DECISIONS.md` 2026-11-16 BF2-R1;
  `outstanding.md` M91). Exp 64 should not lean on that row's floor.

### NIT

- **N1. Citations moved on `6fee7377`.**
  - `models/language/router.py:185` → `:192` (`_inference_lock` creation) and `:1080` → `:1094` (acquire): in
    `embeddable_agent_DRAFT.md:24` and `npcs_and_sem.md:661`.
  - `runtime/lane_backends.py:1246` → `:1249` (`_maybe_inject_cloud_fallback`): in `embeddable_agent_DRAFT.md:91`.
  - `agents/agent_factory.py:1168-1172` is a path that never existed (it is `runtime/agent_factory.py`;
    `persistence_dir_for` is at about `:1168`): in `embeddable_agent_DRAFT.md:27` and `npcs_and_sem.md:665`.
  - Verified unchanged: `nac.py:1162/1163/3625-3640/3707/3714`, `agent_loop.py:521/800-840/3194`,
    `loop_controller.py:157`, `api.py:113`, `semantic.py:662`, `cli_utils.py:608`;
    `orchestrator.py` still has 5 `strftime`. The other cited `src/` files are untouched since `7084f561`.
- **N2. Errors in the candidates doc itself,** to tell Maxim: `_resolve_persistence_dir` is at `:1174`, not `:770`; its
  router lines are stale after #1657 (`:945/:985/:186/:1081` → `:958/:998/:192/:1094`); `exec_agent.py:1495` is right on
  `98c6889c` and later, but `:1470` on `7084f561`.
- **N3.** Cand. B1's heading "Overdrive's OD-A10–A15" includes OD-A11/A12/A13, which the doc itself places in A4/A1/A5.
  It should read OD-A10, OD-A14, OD-A15.
- **N4.** Maxim's new A1–A5, B1–B3 and C1–C5 collide with our roadmap's "Was" column (A1, B1, C1…). Prefix Maxim's as
  `cand. A3` (or `MX-A3`) in our documents.
- **N5.** `correction_1.md`'s header still says "Not yet sent"; plan §3 step 1 is done.
- **N6.** `correction_1.md` calls `nac.py:1162` "the 300 s causal-link buffer". It is the event's wall stamp in
  `record_event`; the buffer prunes at 2 × 300 s (`:1167`). Close enough to stand, but cand. A3's wording ("event
  time") is the more exact one.
