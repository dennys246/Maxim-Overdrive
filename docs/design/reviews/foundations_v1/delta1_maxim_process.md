# Maxim process fit, delta round 1: the upstream drafts at 18623ce

- **Lens:** Maxim process fit (delta round). Would these drafts now survive Maxim's process and its maintainers?
- **Design commit:** 18623ce (`phase1/design-v2`).
- **Date:** 2026-11-16.
- **Counts:** 2 BLOCKER, 12 SHOULD-FIX, 9 NIT.
- **Previous round:** `maxim_process.md` (3 BLOCKER, 14 SHOULD-FIX, 8 NIT at 4f7a754). Closure is tabled at the end.
- **Under review:** `docs/maxim_upstream/` (README, issues_now, decisions_entry, embeddable_agent, world_clock_release
  (WC), default_network_stepped (DN), propose_settle_amendment (PS), time_sense (TS), sem_breaking_change_plan (SEM),
  hybrid_1_5_line (HY)) and `docs/roadmap.md` Phase 3.
- **Maxim read:** only `origin/main` `7084f561` (2026-11-16 09:13), through `git show` and `git grep`. Nothing in
  Maxim was modified. Files read: `CLAUDE.md`, `CONTRIBUTING.md` §Issues, `docs/CODE_REVIEW.md`, `DECISIONS.md`
  (2026-11-11 hybrid; BF1/BF2; OD1–OD5; TR1/TR2; #1180/SCN; G3, G4, G17), `docs/plans/README.md`,
  `roadmap_1_3_x.md` (the fence, the 1.3.4 session table, the atonia gate, the embodied device, 1.3.5, 1.3.6,
  Sequence, Risks), `roadmap_1_4.md` (Groundwork, the divergence rule, What is NOT in 1.4), `outstanding.md` (M72,
  M76, M83, M89), `experience_clock_decay.md` (front gate, §(g)), `advisor_mode.md`, `learned_hold_window.md`,
  `foreign_advice_layer.md`, `hybrid_arbitration.md`, `bio_faithful_roadmap.md`, `baseline_floors.md`,
  `behavioral_graduation_candidates.md` (BF2, T1-13), `deferred/hybrid_substrate_reflex_runtime.md`,
  `deferred/scn_event_producer_gap.md`, `docs/agents/persistence-config.md` §3, `docs/agents/embodiment.md`.
- **Code read:** `advisor/` (`__init__`, `_session.py`), `tools/base.py::Effect`, `runtime/tool_policy.py`,
  `runtime/bootstrap.py`, `runtime/thought_gate.py`, `energy/llm_tracker.py`, `embodiment/sem.py`
  (`ModulatorResult`, `AffordanceSchema`, `Modulator`, `FailureMode`), `embodiment/body.py`,
  `embodiment/reflex.py`, `attention/salience_map.py`, `salience/salience_network.py`,
  `models/language/cost_tracker.py`, `similarity/semantic.py`, `integration/memory_hub.py`, `utils/paths.py`,
  `memory/hippocampus.py`, `agents/context_pool.py`, `proprioception/pain_bus.py`,
  `default_network/{config,network}.py`, `tests/unit/_loop_harness.py::_StepClock`,
  `utils/function_length_baseline.json`.
- **Spot checks that held:** the fence text (verbatim); M72's allowlist; G4's "NOT re-keyed … a question at GL3's
  start"; G17; §(g)'s three rows; `learned_hold_window.md`'s waiting-cost line; `foreign_advice_layer.md`'s "whatever
  the LLM latency or host load"; HA-O4, HA-O12, HA-O14; M89's four rules; BF2's wording; `persistence-config.md` §3
  path (b); `AffordanceSchema`'s "additive fields appended at the end stay non-breaking"; `always_active` and
  `speech_param`; Q7's `apply_decay=` through 1.4.x; `ENTITY_FORMAT_VERSION = "1.1"`; the PainBus docstring ("collapsing
  into one dispatch", the retired `ContextVar`, "FUNCTIONAL"); the pinned lengths (502, 392, 357, 224); 36
  `default_factory=time.time` stamps in 19 files; 14 and 5 `time.time()` reads; `context_pool`'s `[HH:MM:SS]`;
  `dedup_window_s = 30.0` and `uuid4` memory ids; `allow_pickle=True`; `update_hz = 30.0`; `1305.owned-rng` and
  `1263.thread-guard`. A-pre's file list touches none of the three fenced files (checked file by file).

## Verdict

The round-1 fold is real. Most of what a maintainer would have caught first is fixed: WC has a front gate, the
oscillator has moved to tier B, CC3 is read correctly, the fenced sites are in A-post, G4 and M72 are named, the ids
carry a prefix, and the drafts are split by venue. A reviewer would now read the WC and SEM drafts charitably.

The new **embeddable agent** draft, which the README calls "the heart of tier A", repeats round 1's first failure
in a worse form. Its front gate doesn't mention the atonia gate, which **shipped on `origin/main` in the last few
weeks**. `maxim.advisor` is a host-called composition: "No loop, no autonomy controller, no prefetch, no data home,
and no router is built". It comes with a sealed registry, a required `ToolPolicy`, a `Tool.effect` ceiling and
`AdvisorLimits`. That is most of OD-A11, OD-A12's "no `data_home`" and §4.6's budgets, already built, reviewed and
owned by Session V. The second problem is structural. A-pre's eight PRs, and the embeddable plan's PRs 0–4, have no
caller on a shipped path until after 1.3.6, which makes them capability under Maxim's "a fix ships with a CALLER"
rule. The maxim.advisor precedent is also the way out: an unfenced composition gives A-pre its caller.

## BLOCKER

### MPD-B1. The embeddable agent's front gate omits the shipped atonia gate (embeddable §3, §4.3, §4.4, §4.6, §5 PRs 1–3)

The front-gate table's "Closed tool roster" row cites only "`build_tool_registry` with mode-based containment
(`OperationalMode`…, `allowed_dirs`)". §7 argues against "mode-based containment as the security model". On
`7084f561` that is no longer Maxim's security model for tools:

- **`tools/base.py::Effect`** is a set of seven flags (`READ`, `SELF_SCOPE`, `WRITE_LOCAL`, `NETWORK`, `COMMS`,
  `ACTUATE`, `GOVERN`; V2), and an undeclared tool counts as the top class.
- **`runtime/tool_policy.py::ToolPolicy`** is required on `Executor`, `build_executor` and `AgentConfig` (V3).
  `bootstrap.py` imports `require_policy`.
- **`tools/registry.py::EffectAdmission`** is the registry ceiling (advisor_mode item 2's "one admit path").
- **`maxim.advisor`** (#1579, item 1) is a closed builder, a `SealedToolRegistry`, an in-process `closed_local`
  backend instead of `LLMRouter` (V4), and "one bounded turn per `ingest()`, not the agent loop" (V1). Its module
  docstring says: "No loop, no autonomy controller, no prefetch, no data home, and no router is built".
- **`AdvisorLimits`** caps calls per turn (`max_calls`, from 1 to 32), prompt tokens and turn time. Those are §4.6's
  budgets.
- **`MAXIM_OFFLINE`** with an audit-hook latch (V5, V8) is the refusal of every fetch.

Five of the table's seven rows have an existing answer the draft never weighs:
- the roster is a `ToolPolicy` with an effect ceiling;
- the construction refusal is the closed builder's;
- "no `data_home`" is the advisor's composition;
- one host-called turn with no loop is V1;
- the budgets are `AdvisorLimits`.

There is also a file-fence collision. PR 1 touches `runtime/bootstrap.py` and `runtime/agent_factory.py`, and PR 3
touches `similarity/semantic.py`. All three are in Session V's "Owns" column (roadmap_1_3_x.md, 1.3.3 table, carried
into 1.3.4 "as in 1.3.3"). The draft's "Owning session" line covers only the fence.

**Failure scenario:** the Architecture lens returns "this is `maxim.advisor`'s composition plus a world: ride on
V1–V8". If it is missed instead, PR 1 ships a second containment mechanism beside `ToolPolicy`, the thing advisor_mode
§"What rides on existing infrastructure" spent two review rounds removing ("It is not a third gate"). It would also
collide with Session V's open items 4, 7, 8, 11, 12, 13 and 14.

**Fix:** rewrite §3 against `advisor_mode.md`, `atonia_gate_approach_notes.md` and `advisor/_session.py`:
- **The roster:** `ToolPolicy.pinned(...)` (or narrowed) with an effect ceiling of `READ | SELF_SCOPE`, plus
  whatever a world modulator declares. Decide whether a world's acting affordance is `ACTUATE`; the `Effect`
  docstring scopes `ACTUATE` to physical output, so this is an owner question.
- **The composition:** a sibling closed builder.
- **Budgets:** `AdvisorLimits`.
- **The model gateway:** the `closed_local` precedent for a backend that isn't the router.
- **Ownership:** name Session V as owner or co-owner of PRs 1–3.
- **§7:** argue against what is actually there, which is effect classes declared by the tool, not prompt-content
  trust.

### MPD-B2. A-pre, and the embeddable PRs 0–4, ship with no caller on a shipped path (WC §6 A-pre, §7; embeddable §5)

A-pre PR 2 wires `AgentTime` "from the embedded entry point to `LLMWorker`, `PromptBuilder` and each subsystem".
That entry point is embeddable PR 5, which comes "after 1.3.6". Every exit test (OD-WC1 to OD-WC7) needs an embedded
turn, and they flip only in PR 10, which is in A-post. So for its whole life as "its own clock, the next free patch
number", A-pre is injected collaborators that nothing except tests ever injects. Maxim's `CLAUDE.md` says:
"[engineering] A fix ships with a CALLER, or it has not shipped … zero non-test callers means capability, not a fix".
The Wire integrity lens's probe 1 (the no-op caller rule) asks exactly this. The same holds for embeddable PRs 0–4,
which "can ship on their own clock". The tool roster, the home and the backend capabilities have no embedded agent
to serve.

**Failure scenario:** the A-pre release goes to review claiming "embedded agents read time only from injected
collaborators". The reviewer greps for non-test callers of the injected path, finds none, and sends it back. Or it
ships, and Maxim carries an untested seam for months while 1.3.5 and 1.3.6 move the code under it. That is the
`shipped-the-pieces-not-the-composition` lesson again.

**Fix:** give A-pre a caller outside the fence. The advisor shows that one exists: a host-called, one-turn
composition built without `run_agentic_loop` (MPD-B1). Alternatively, use a `scripts/` caller (Maxim counts
`scripts/` in the caller grep), such as a lockstep survival harness that drives a stepped world. A-pre's exit tests
become OD-WC1 to OD-WC7 on that composition. If no unfenced caller is acceptable, A-pre shrinks to red gates, the
census and the host-default identity tests, and everything else moves to A-post.

## SHOULD-FIX

### MPD-S1. A-pre isn't wholly on its own clock, and its precedent is misattributed (WC header, §5, §6 PR 6)

- **PR 6 isn't independent.** PR 6 (the reaction and pain gates) is "sequenced after #1200's PainBus rewiring", and
  #1200 rides 1.3.6 (roadmap_1_3_x.md §1.3.6, "the dispatch and credit issues … and #1200"). So A-pre can't finish
  before 1.3.6.
- **The quote isn't the atonia gate's.** WC calls the quote ("touches no decomposition-fenced file … holds nothing")
  "the atonia-gate precedent". It is the **embodied device's** text (§The embodied device: "it ships as a patch when
  ready and holds nothing, and it touches no decomposition-fenced file"). The atonia gate has an AD8 fence exception
  for `orchestrator.py` and `agent_loop.py`, so it is the counter-example.

**Fix:**
- Move PR 6 to A-post, or split it into the reaction-bus half (A-pre) and the PainBus half (after #1200).
- Cite the embodied device as the precedent.

### MPD-S2. SEM omits the invariant that requires a breaking-change plan (SEM §1; README)

`docs/agents/embodiment.md` carries an `[engineering]` invariant on the drive types: "Do NOT add fields to these
frozen dataclasses post-1.0 without a breaking-change plan". `AffordanceSchema`'s own docstring quotes it as the
sentence right after the one SEM §1 quotes ("Per CLAUDE.md: 'Do NOT add fields … without a breaking-change plan.'").
`HomeostaticDriveSpec`, `EntropicDriveSpec` and two other specs repeat it.

SEM now says it is "no longer a breaking-change plan", and the README says the name is kept only for links. A
maintainer who reads the invariant will ask where the plan is that the rule requires for OD-C3 (`acts_on`) and OD-C5
(`settles`).

**Failure scenario:** the Architecture lens quotes the next sentence of the docstring, and §1's argument looks
selectively quoted, which is the impression round 1 worked to remove.

**Fix:**
- Quote the whole docstring.
- State that this document **is** the breaking-change plan that invariant requires: additive under CC3 path (b),
  review-gated, one plan for every field it adds.
- Keep the file name, which turns out to be the right one, and correct the README line.

### MPD-S3. OD-I2 isn't clearly a defect under Maxim's own CC3 scope (issues_now OD-I2)

`persistence-config.md` §3 scopes CC3 to types that persist or cross a wire, and lists "runtime-ephemeral …
dataclasses … that never cross a wire or session boundary" as out of scope. `ModulatorResult` is built and consumed
in-process, between a modulator and `tool_bridge`. The issue asserts the MUST without showing that the type
persists or crosses a wire. It also has no repro, no expected and no actual, only "Where", "The defect" and
"Done when".

**Failure scenario:** the reply is "out of scope by §3: append defaulted fields freely". That is good for OD-C5,
but the issue closes as not-a-defect, and the SEM plan loses the dependency it cites.

**Fix:** either argue the boundary, or fold OD-I2 into the SEM plan as its first doc PR. The argument would be that
it is the return type of the public `Modulator` `Protocol`, implemented outside Maxim by pulse and Overdrive, and that
its promoted `metadata` keys reach persisted causal links and `side_effects`. Either way, write it as Actual (no CC3
path declared) and Expected (path (b) and its rationale).

### MPD-S4. OD-I1 is latent, not a live defect, and its siblings are known (issues_now OD-I1)

`CONTRIBUTING.md` says: "File one when an audit *verifies* a live defect."
- **No live repro in the tree.** The one in-tree caller, `default_network/network.py`, passes `current_time=now` from
  the wall. `_StepClock` starts at `t = 0.0`, but it patches `time.time`, so `0.0 or time.time()` still returns 0.0
  under the golden, and the bug is masked.
- **The siblings are already countable.** The same pattern exists on `7084f561` at
  `salience/salience_network.py::update_from_detections` (`timestamp or time.time()`) and three times in
  `models/language/cost_tracker.py`. The issue tells the PR to grep for them instead of listing them.

**Fix:**
- Either fold OD-I1 into A-pre PR 5 as hygiene, or file it with a repro on a real path: the stepped world in
  `scripts/survival_world/scripted_water.py`, if it starts at zero without patching.
- List all five sites, each marked in scope or out.
- Add Repro, Expected and Actual.

### MPD-S5. The pickle load is a live security defect, buried in an L plan (embeddable §2, §4.4, PR 3)

`integration/memory_hub.py` loads `util/semantic_embeddings.npz`, resolved through `resolve_user_state`, on session
start, via `EmbeddingStore.load` → `np.load(path, allow_pickle=True)`. `EmbeddingStore.save` writes an object array
(`hashes_json`, `dtype=object`), so the fix is a format change with a migration, not a one-line flip. This is a
discrete defect, actionable now, with a definite done state. That is an issue (OD-I3), not PR 3 of a nine-PR plan
that is "maybe its own issue". `similarity/semantic.py` is in Session V's item-10 file fence, so V is the natural
owner.

**Failure scenario:** a maintainer files it themselves from the plan review and asks why the plan sat on it.
Alternatively, it waits behind the embeddable plan for months.

**Fix:** move it to `issues_now` with:
- the threat path that makes it live: which flows put a foreign file in a home, such as hivemind bundles,
  `migrate_agent_state` or a shared bug-report home;
- the format change and its loader migration.

### MPD-S6. "After 1.3.6" is the busiest window, and A-post must not grow 1.3.6 (Overdrive roadmap Phase 3; WC header and §5; embeddable §5; DN §2; PS §4)

**1.3.6 is the 1.4.0 critical path.** Overdrive's roadmap says that A-post "lands with Maxim's 1.3.6, Session A".
1.3.6 is the T0 gate's release, and Risk 1 in roadmap_1_3_x.md is "the decomposition can hold 1.4 for a long time".
A maintainer won't add 3 PRs to it. WC itself says "with or after", so the roadmap should say "after".

**Everything lands in the same window.** All of the following land after the fence lifts:
- embeddable PRs 5–6 (step, and generate vs apply, on the 1.3.6 loop builder);
- A-post;
- the stepped Default Network;
- OD-A16.

That is the window in which roadmap_1_4's Phase 0 instrument is built on `agent_loop.py`, E1 (may-fail) runs, and
B2 → B3 → B4 runs serially. roadmap_1_4 §Groundwork's divergence rule applies: "a may-fail result measured on a loop
mid-refactor cannot tell a null from the refactor". None of the drafts' Order sections goes past "after 1.3.6".

**Fix:**
- For each post-fence PR, say whether it touches a path an E1-to-E3 or B2-to-B4 arm runs on. If it touches none
  (the embedded path is a separate composition, MPD-B2), say so, and make that a guard.
- If it touches one, sequence it after E1's run or after the 1.4.0 cut, the default the coding world and the hybrid
  line already take.

### MPD-S7. Impact by ledger row is still deferred to the reviewers (WC §8, embeddable §6, DN, PS; round 1 MP-S8)

House plans name the rows themselves (`experience_clock_decay.md` §Impact). The drafts still say "the plan review
checks this by row id". Candidates the drafts can name now:
- **T1-13.** Its path is the PainBus `drive:oxygen` → Wire-4 fear chain. Its `Re-run on:` includes "`run_agentic_loop`
  idle-gate or autonomy handling change", which A-post's tick replacement and embeddable PR 6 come near.
- **T1-16.** Hippocampus record shape and the ranker, for A-pre PR 5 and the uuid swap.
- **The Exp 62 row** (`time_of_day`; #899's wrap), for `TemporalSignature`'s phase source.
- **Each row whose harness loads `semantic_embeddings.npz`,** for the pickle migration.

**Fix:** list each row with "fires", "does not fire, because …", or "host default identical, guard X".

### MPD-S8. time_sense's front gate misses three existing pieces (TS §2, §3.5, OD-X1)

- **`runtime/thought_gate.py::ThoughtGate` already has an "Energy" stage,** "don't think below
  `min_energy_fraction` of budget". It is fed by `energy/llm_tracker.py::LLMEnergyTracker`, "cognitive energy", which
  is estimated from tokens, model size and **wall** latency. That is the depleting-reserve model OD-B12 says it
  rejects. It is the first thing a maintainer names, and it is also a wall-time site the WC census must include.
- **`DECISIONS.md` 2026-10-10, "#1180 parked; the SCN-coupling stub demoted":** "the behavioural test cannot succeed
  by construction: every live reward reaching `distribute` is negative". OD-X1's task (food that appears at a fixed
  time of day, with anticipation) must say which path carries the anticipation. If it is `TemporalCreditDistributor`,
  OD-X1 fails by construction until GL2c, and the experiment must wait for it.
- **`deferred/scn_event_producer_gap.md`:** five of six SCN event categories have no producer. A light percept is
  either a new producer for that plan, or it entrains the oscillator directly. Which one decides what OD-B8 builds on.

**Fix:** add these three rows to the front gate, and argue OD-B12 against `ThoughtGate`'s energy stage by name.

### MPD-S9. Several experiment drafts carry the wrong BF2 floors (TS OD-X2; HY OD-HX3, OD-HX4)

- **OD-X2 is an LLM-path claim.** It modulates deliberation latency and thought cost. BF2 makes its floor `bare_llm`
  (and `llm_notes` if it is cross-session), not `tabular_q` and `random`. Under BF2, "no new LLM-path claim can be
  EARNED until the bare loop exists", and B2 waits on 1.3.6.
- **OD-HX3 and OD-HX4 name no floors.** The hybrid line also requires the claim to be "non-inferior to llm-primary"
  and to beat substrate-primary, and "BF2 binds every claim of the line, so none EARNs before B2".

**Fix:** state each experiment's path (substrate or LLM), its BF2 floors, and its B2 dependency.

### MPD-S10. The decisions entry's item 4 contradicts Maxim's ledger and OD-H1 (decisions_entry; HY OD-H1)

"Game runs never go on the results ledger" can't be asked of Maxim as written. Its EARNED rows are Minecraft game
runs (Exp 60–62). The rule is Overdrive's, about Overdrive's sessions. OD-H1 also proposes experiments "against an
Overdrive world exposed through a Maxim simulation bridge", so the entry and the contribution disagree.

The entry also carries no decision ids. House entries number theirs: TF1–TF3, HA-O1–HA-O16, G17.

**Fix:**
- Scope the rule: an Overdrive session is never ledger evidence by itself. An experiment on an Overdrive world counts
  only as a Maxim-owned, pre-registered harness whose apparatus Maxim holds (the Minecraft precedent).
- Answer OD-H1's venue question with that rule.
- Give the items ids.

### MPD-S11. OD-H3's anchor has passed (HY OD-H3; roadmap OD-H3)

G4 says that whether to re-read the gate "is a question at GL3's start". GL3 started: `DECISIONS.md` 2026-10-09 TR1
and TR2 were "Asked at GL3.B0's start". The draft aims the argument at a moment that has passed. It also doesn't
engage the 2026-11-11 decision's item 2. That item says the hybrid line "does not reverse the 2026-07-17 HYBRID
decision or its deferred plan … The two compose", and it is the newest statement on that deferred plan.

**Fix:** aim at a live anchor, either GL3.B1 (registry and provenance, the perception half's re-key trigger) or an
owner question now, and argue with the 2026-11-11 item 2 as well as G4.

### MPD-S12. The "per-agent home" row misstates what exists (embeddable §3 row 3, §4.4)

"A process global can't serve several agents" undersells Maxim's position:
- per-agent homes exist (`agents/<id>/`; `create.agent` refuses an existing home; `AgentFactory.create_npc_agent`);
- #985 (`create_npc_agent` over an existing home) is filed;
- #984, "shared learned state outside any home", is homed in Session H's 1.3.4 line.

The real residue is `resolve_user_state("util/...")` state, which includes the embeddings file of MPD-S5, plus the
process-cached `data_home()`.

**Fix:** build on agent homes, cite #984 and #985 with their owner, and narrow OD-A12 to what they don't cover.

## NIT

- **MPD-N1. `OD-` sits beside Maxim's OD1–OD5** (DECISIONS 2026-10-11, B1's owner decisions; OD1 is "the binding BF2
  tabular floor for Exp 60 is Q_EXPLORE"). TS's floors cite exactly that area. The hyphen separates them for a lint,
  but not for a reader. Consider `MO-`, or ask Maxim to assign ids at intake.
- **MPD-N2. Volatile counts and line hints remain.** WC still carries "36 … in 19 files", "14 `time.time()` reads"
  and "5 `strftime`", despite its own "plans don't carry volatile counts". DN's hints (`:561`, `:836`) have already
  drifted: `start` is at `:565` and `_run_loop` at `:900`.
- **MPD-N3. Overdrive's `CLAUDE.md` still says** every Maxim change follows "pre-registration, four-lens design
  review, ledger". The roadmap preamble is fixed; `CLAUDE.md` isn't (round 1 MP-N5, half open).
- **MPD-N4. OD-C4 names two mechanisms.** It names a class attribute `accepts_actor` and "a second optional
  `Protocol` checked with `isinstance`". A `runtime_checkable` `isinstance` checks only that members are present,
  never `execute`'s signature. Pick one: the attribute, or a distinctly named method (`execute_as`).
- **MPD-N5. OD-C1's optional rename isn't the Q7 precedent.** Q7 was a function keyword. Renaming a field on a
  frozen, slotted, SHAPE-FROZEN dataclass that a YAML key also names needs a custom constructor and a loader alias.
  Drop the rename, since the docstring and test do the job.
- **MPD-N6. Two items say "unverified" where a grep settles them.** `embodiment/audio_localization.py::world_set_axis`
  exists (OD-C10). `runtime/agent_factory.py::AgentFactory.create_npc_agent` exists (OD-A10's parenthetical). Cite
  them.
- **MPD-N7. §(g)'s row is "PainBus refractory, reflex cooldowns".** WC §4 argues only the PainBus half.
  `embodiment/reflex.py`'s `_last_fired` cooldown needs a line: does it go on the wall, or on the injected clock
  under embedding?
- **MPD-N8. The Exp 64 draft is listed but unrevised.** It is an LLM-path, cross-session claim, so BF2's floors are
  `bare_llm` and `llm_notes`. Its arm E, a backstory prompt, is neither. It can't EARN before B2. The README row
  should say so.
- **MPD-N9. Quote fidelity, small.** TS §4 swaps the bio roadmap's em-dash for a colon inside a quoted gate. HY OD-H2
  asks about "`learned_hold_window.md` v1's frozen hold", but v1's hold is `hybrid_arbitration.md`'s, frozen per world
  in the prereg; `learned_hold_window.md` is v2 by its own title.

## Round-1 closure

| Round 1 | Status | Note |
|---|---|---|
| MP-B1 front gate | **Closed** for WC and SEM | It recurs in the new drafts (MPD-B1, MPD-S8, MPD-S12) |
| MP-B2 oscillator | **Closed** | Moved to tier B, opt-in |
| MP-B3 CC3 | **Closed** | One adjacent invariant omitted (MPD-S2) |
| MP-S1 fenced sites | **Closed** | A-post PR 8; OD-WC4 flips in PR 10 |
| MP-S2 1.3.6 collisions | **Closed** for WC | Session V and H file fences are unaddressed for the embeddable plan (MPD-B1) |
| MP-S3 own clock | **Partial** | PR 6 waits on #1200 (MPD-S1); no caller (MPD-B2) |
| MP-S4 SEM S3/S4 sequencing | **Closed** | PS §4 |
| MP-S5 decisions named | **Closed** | G4, G17, M72 and the ANALOG row are quoted accurately; OD-H3's anchor is stale (MPD-S11) |
| MP-S6 hash evidence | **Closed** | |
| MP-S7 clock units and scope | **Closed** | |
| MP-S8 house sections | **Partial** | Impact still deferred (MPD-S7); A-pre's owning session is unnamed |
| MP-S9 ids and BF2 | **Partial** | Prefix fixed; OD-X2 and HX floors wrong (MPD-S9); OD1–OD5 adjacency (MPD-N1) |
| MP-S10 1.3.3 and 2.0 framing | **Closed** | |
| MP-S11 venue split | **Closed** | OD-I1 is latent (MPD-S4); the pickle load should be an issue (MPD-S5) |
| MP-S12 `actor` key | **Closed** | Mechanism doubled (MPD-N4) |
| MP-S13 DECISIONS entry | **Closed** | Entry needs scoping and ids (MPD-S10) |
| MP-S14 stale tree | **Closed** | One sha, `7084f561`, fresh |
| MP-N1 to MP-N4, MP-N6, MP-N7 | **Closed** | |
| MP-N5 roadmap wording | **Partial** | Overdrive `CLAUDE.md` still wrong (MPD-N3) |
| MP-N8 volatile counts | **Partial** | MPD-N2 |

## The checks the brief asked for

- **Front-gate sections:** present in every plan. Complete in WC, SEM, PS and DN. Incomplete in embeddable (the
  atonia gate, agent homes, #984) and TS (`ThoughtGate` energy, the #1180/SCN decision, the producer gap).
- **Issue texts:** not ready to file. Neither has Repro, Expected and Actual. OD-I1 is latent, OD-I2 needs its scope
  argued, and one live defect (the pickle load) is missing.
- **Plan/issue split, fence, 1.3.6 and M89:** A-pre touches no fenced file (verified). It does touch Session V's
  and #1200's timing, and it has no caller. A-post must ride after 1.3.6, not in it. Nothing proposes `src/` in the
  hybrid family before 1.4.0, so M89 holds. OD-H2's "declaration on the embedded entry point" must stay paper until
  the cut.
- **Decisions quoted:** G4, M72, §(g), HA-O4, HA-O12, HA-O14, the hold's waiting-cost line and the advice layer's
  latency line are all accurate. The one stale anchor is GL3's start (MPD-S11).
- **Evidence:** WC, PS and embeddable take strict red gates in Maxim's own tree, which is acceptable. The decisions
  entry's ledger sentence needs scoping (MPD-S10).
- **Experiment ids and floors:** no collision with Maxim's experiments, thresholds or slices. OD-X1 carries the right
  floors; OD-X2, OD-HX3 and OD-HX4 don't. Every mechanism enters `[engineering]` with `[behavioral]` earned through
  `behavioral_graduation_candidates.md`, so the two-tier rule is honoured.
- **DECISIONS format:** the headings match (`## date — title`, `### Decision (owner, …)`, `### Reason`,
  `### Tradeoffs`). The entry is missing decision ids.
- **Review tier:** right everywhere. Engineering plans get a three-lens plan review, an adversarial approach note for
  their gates and no prereg. OD-X1, OD-X2 and the HX experiments get a four-lens design review and a frozen prereg.

## What a Maxim maintainer would reject first now

1. **The embeddable agent's front gate** (MPD-B1): "`maxim.advisor` already is a host-called agent with no loop, no
   data home, a sealed roster and turn limits. Ride on it."
2. **A-pre's missing caller** (MPD-B2): "Grep for non-test callers of the injected path: zero. This is capability."
3. **The pickle load** (MPD-S5): "This is a security defect. Why is it PR 3 of a plan?"
