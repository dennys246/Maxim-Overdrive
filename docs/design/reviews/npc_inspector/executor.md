# NPC inspector design, v1 draft: Executor review

**Lens:** Executor. I checked whether the design's claims about the existing code, designs and numbers are true at the revisions it names, whether each test it proposes can fail, and whether those tests are concrete enough to write. **Read:** the staged diff (tree `00b9766`) against Overdrive `origin/main` `e6d6a7f`: `docs/design/npc_inspector.md` (2,874 words) and the new `contracts.md` row. **Sources checked:**
- Overdrive at `e6d6a7f`: `npcs_and_sem.md`, `boundaries.md`, `sem_stimuli.md`, `inference_placement.md`, `client_rendering.md`, `tile_and_client.md`, `fire_solid.md`, `decisions/boundaries.md`, `decisions/npcs_and_sem.md`, `roadmap.md`, `plans/checklists.md`, `plans/next_steps/4_records_build.md`, `maxim_upstream/embeddable_agent_DRAFT.md`, `reviews/foundations_v1/delta1_trust_boundary.md`, `src/simcore/core/schema.py`, `src/simcore/host/server.py`, `pyproject.toml`.
- `origin/phase3/joint-plan` `20ada4e`, for the PR #81 citations.
- Maxim `b90800e` in `<maxim-clone>`.
- Maxim-pulse `a1ba1d4` in `<pulse-clone>`.

**Ran:**
- `scripts/lint_standards.py`, which passes.
- Three mutations of the new contract, run in memory through `lint_contracts.check_contracts`.

## Summary

| Id | Severity | Where | In one line |
|---|---|---|---|
| E-B1 | BLOCKER | §1, §2 (percept, receipt) | Two entry kinds hold values that never reach the host, against §1's own rule |
| E-S1 | SHOULD-FIX | §2 "The format" | `simcore.core.schema`'s `Format` refuses any field named for ticks, and every entry has one |
| E-S2 | SHOULD-FIX | §4 "Replay" | Which entries are re-derived and which are recorded is wrong in both directions |
| E-S3 | SHOULD-FIX | §6 "Why", "Searched first" | Maxim already persists bio-system events per session (`BioTelemetryCollector`), and NAc logs why an action won |
| E-S4 | SHOULD-FIX | §3 "Nothing in the engine reads it" | The proposed import rule can't fail, and it leaves out the modules that could read the record |
| E-S5 | SHOULD-FIX | §5 | One rule about what a player learns of an NPC already exists, and the claim about today's client is false |
| E-S6 | SHOULD-FIX | §2 "The format", "One record per agent per run" | The header names one segment, but a run with a restart spans several |
| E-S7 | SHOULD-FIX | §2 `write`, §3 | `boundaries.md` already plans an agent-side audit record of memory writes |
| E-N1 to E-N6 | NIT | various | A wrong file for `ts`, tests not concrete enough, citation details |

## BLOCKER

### E-B1. Percepts "as the agent received them" and receipt valence never cross into the host

**Location:** `npc_inspector.md::§1` (the rule) and `::§2` (percept, receipt).

**The claim.**
- §1: the inspector "reads only values the host already holds because they crossed the membrane", and "never adds a codec kind".
- §2, percept: "the frame values the agent's pulls read at its last `step` … region, receptor, site and value, as the agent received them".
- §2, receipt: "its outcome and the valence the adapter reported".

**What I found.**
- **Pulls run in the worker.** They are Maxim's sensor reads against the frame the adapter pins (`npcs_and_sem.md:903-907`). Maxim is imported only in workers and inference gateways (`boundaries.md:647-649`).
- **Percept noise is applied in the worker.** It is keyed by `(npc, stream, tick, sensor)`, and the host only hands the streams to `engine.adapters.agents` (`npcs_and_sem.md:262-266`).
- **Transduction is Maxim's.** Thresholds, gain and adaptation happen there (`sem_stimuli.md:16-17`).
- **So the host never learns which pulls an agent made.** What it holds is the frame it sent and, on the push path, the `BoundFrame` values per binding (`sem_stimuli.md:172-182`). It never sees which sensors were read, or the noised and transduced values "as the agent received them".
- **Valence never reaches the host either.** The worker-to-host codec kinds are `step_output`, `pending`, `thought_output`, `ack` and `error(code)` (`npcs_and_sem.md:707-711`). `settle(receipts, writes) -> ack` returns only an ack (`:748`). The receipt is `(pid, kind)` (`sem_stimuli.md:315`), and `execute` returns a fixed `pending` with "no name, no metadata" (`sem_stimuli.md:219-220`). D53's valence self-report (`npcs_and_sem.md:586`) happens inside the worker, between the adapter and Maxim.
- **"D53's tiers" is a loose label.** §6.1 names D53 as the valence self-report rule. The word "tier" appears only in "the D53 NEUTRAL tier" (`npcs_and_sem.md:594`).

**Failure scenario.** An implementer in `phase1/agents` builds the `percept` and `receipt` entries and finds the data isn't in the host. There are two ways out, and both break the design:
- add a worker-to-host field that reports pulls and valence, which is the new codec surface §1 forbids; or
- have the host recompute "what the pull would have read" from the pinned frame and label it as received. That puts a host-computed value under the agent's name, which is the confusion §2's "sensed, not handed" line exists to prevent. With the double, both paths pass every proposed test.

The contract has to say which values it means: the host-sent frame and binding values, with no valence, or a codec addition decided openly. As written, it promises both things at once.

## SHOULD-FIX

### E-S1. "Through `simcore.core.schema` like every data format" fails when the format is declared

**Location:** `::§2` "The format".

**What I found.** `Format.__post_init__` raises `TypeError("content stores time in seconds, never ticks …")` for any field whose name contains the word `tick` or `ticks`, at any nesting depth (`src/simcore/core/schema.py:399-402, 422-424`). Every mind-record entry carries "the integer tick" (§1). No tick-bearing `Format` exists in `src/` today. The intent record's `apply_tick` is a frozen dataclass in `intents.py:177`, and the wire messages use `protocol/messages.py`, not `Format`.

**Failure scenario.** The writer's `Format(...)` raises at import. The builder then either renames the tick field, or amends tile §3.2's rule, which `schema.py` enforces and this design doesn't own. The design should say which path the record's schema takes and who amends what.

### E-S2. §4 sorts entries into re-derived and recorded incorrectly

**Location:** `::§4` "Replay".

**The claim.** On replay, "intents, speech and receipts" are rebuilt from the world log. "Percepts, writes, the state readout and thought lifecycles come from the saved record."

**What I found.**
- **Lifecycle and thought records are in the world log.** `thought_cancelled`, `thought_failed`, `agent_ready` and `agent_failed` are world-log kinds (`boundaries.md:380`, and `:428-429` for thoughts). So the `lifecycle` kind (which §4 never mentions) and part of each thought's lifecycle can be re-derived.
- **Percepts re-derive too.** Body frames are built in the core and digested per tick, "independent of delivery" (`sem_stimuli.md:189-190`). Replay reproduces the world bit for bit (`boundaries.md:449-452`), so the host-sent values re-derive on replay.
- **Receipts are not carried in the log at all.** They are "Derived, never input" and recomputed (`boundaries.md:431`). "Re-derived" is right for them; "the world log carries it" is not.

**Failure scenario.** The explorer marks re-derivable entries as "recorded only", so a save carries redundant data. Worse, nothing compares recorded percepts against replayed ones, so a writer bug that records the wrong frame goes unseen. That comparison is a free test the design leaves unwritten.

### E-S3. Maxim already emits and persists part of this state; the search missed it

**Location:** `::§6` "Why" ("never emitted"; "none reaches `sim_log`") and "Searched first".

**What I found.**
- **The narrow claim holds.** I grepped the six listed modules for `sim_log`: none calls it. The single match is a docstring in `decisions/valence_signal.py:8`, which itself says `source` exists for "bio_telemetry JSONL, sim_log traces".
- **NAc logs "why one action beat another".** `decisions/nac.py:355-380` sends `sim_log("NAc_RECOMMEND", …)` carrying `best_tool`, `current_clusters`, `consulted_bias_by_modality` and `cluster_reward_bias_consulted`, with a wall-derived `tick` (`:361`).
- **Maxim already persists bio-system events per session.** `simulation/bio_telemetry.py::BioTelemetryCollector` filters the `sim_log` record stream for 19 bio subsystems (NAc, HIPPOCAMPUS, SENSOR, FEAR, PAIN, DELIBERATION, MOTOR and others) and writes `bio_telemetry.jsonl` per session. `simulation/report.py:686-690` calls it.
- **The search list names neither.**

**Failure scenario.** The ask goes upstream saying "nothing found plans a per-agent, clock-free readout". Maxim's reviewers point to `BioTelemetryCollector` as the existing channel, and the ask reads as a duplicate under B22. That collector is in fact process-global (`_log_records`), wall-stamped and untyped, which strengthens the case for the ask's per-agent and clock-free constraints. The design should cite it, and the NAc channel, and argue from them.

### E-S4. The proposed import rule can't fail, and it leaves out the modules that matter

**Location:** `::§3` "Nothing in the engine reads it".

**The claim.** "No module under `simcore.core`, the laws or `simcore.adapters` imports the record's writer or reader."

**What I found.** §3 puts the writer in the host. The existing layers contract already forbids `simcore.core` and `simcore.adapters` from importing `simcore.host` (`pyproject.toml:107`: `maxim_overdrive` > `simcore.host | simcore.verify` > protocol > adapters > core), and the laws live in `core`. So the new rule adds nothing: delete it and every check stays green. The modules that could actually read the record and feed it back are `simcore.host`'s own restore and load path, `simcore.verify` and the game, and the rule doesn't cover them. §1's on/off test doesn't cover a load path either: with the record off there is nothing to read, and the "on" run only diverges if a save and load sits inside the test.

**Failure scenario.** A later host change reads the saved record's last `thought` entry on load to rebuild a header field. Every proposed test stays green. A rule that can fail would name the record's reader module and forbid every importer except the view's file gate, plus an on/off test that runs through save, load and continue.

### E-S5. §5's two factual premises are wrong

**Location:** `::§5`.

**What I found.**
- **"None governs what a player may learn of an NPC" is false.** `npcs_and_sem.md` §5.4 (`:551-564`) already does. "Dilation by cause" reaches the client through a host status channel (a protocol message and a field-registry channel), and "the cause is shown diegetically on the thinking NPC". That is a designed channel telling the player which NPC is thinking, and the new information rules would become its second owner.
- **"A player sees nothing new through an NPC" today is false.** v1's percept rows are `tissue_temperature` and `core_temperature` at body sites (`sem_stimuli.md:26`). The snapshot carries only `material`, `region`, `crack` and `temperature_c`, at display quantization (`client_rendering.md:111`). Body-site tissue values, at full precision, never reach the client.
- **The line-of-sight citation points at something else.** `tile_and_client.md:468` is NPC perception in Phase 4/5, not culling of what the player sees. I found no source for "no visibility culling".

**Failure scenario.** The player-view rule gets scheduled for "once line of sight exists". The first real NPC's percepts already give the player information the client never receives, and the existing §5.4 channel stays outside the new rules.

### E-S6. The header ties a record to one segment, but a run can span several

**Location:** `::§2` "One record per agent per run" and "The format" (the header carries the log root id and segment).

**What I found.** Restarting a failed agent "is an explicit host control record that opens a new log segment" (`npcs_and_sem.md:727-728`, O45). Each restore opens a segment, too (`boundaries.md:472-473`). One record per agent per run, with one segment in its header, can't describe a run that had a restart.

**Failure scenario.** An NPC's worker dies and is restarted. Entries after the restart shadow segment 1, but the header says segment 0. A view that joins entries to the world log by header segment shows the second life's percepts against the first life's log. The fix is either one record per segment or an entry-level segment field (*unverified*).

### E-S7. The `write` kind overlaps a record `boundaries.md` already plans

**Location:** `::§2` `write` and `::§3` ("never inside an agent home").

**What I found.** `boundaries.md:397-399` says memory writes are "recorded in an agent-side audit record after OD-A15, and saved with the agent home". The design doesn't mention it. The memory writes would then be recorded twice, by two owners, in two places (host-side here, agent-home there), with nothing saying which one the purge reaches or which one replay trusts.

**Failure scenario.** A guest purge redacts the agent-home audit record but misses the mind record's spans, or the other way round. Or the two drift apart and the explorer shows writes the agent home doesn't hold. One of the two records should own the writes, and the other should link to it.

## NIT

### E-N1. The `ts` field is cited to the wrong file

**Location:** `::§5` "Host data never enters the record".

`simulation/sim_logger.py` has no `"ts"` key. Its records carry `t`, the elapsed wall time (`:1056-1057`). The `/ws` envelope's `"ts": time.time()` is at `console/server.py:1872` and `:1904`. The other claim in that bullet still holds at `b90800e`: `energy_status`'s wall window is at `tools/introspection.py:415, 437`, and the memory `timestamp` at `:745`, `simulation/introspection.py:89`.

### E-N2. Several rules have no test anyone could write

**Location:** §2, §3.
- **The two-channel labelling** ("never presents a self-report as a readout") has no stated mapping from entry kind to channel. `write` is labelled a readout, but memory text written by a thought is model-generated, so it's unclear which label a test should assert.
- **No sentinel test is named** for the guest purge reaching the record, or for the bug report dropping `thought` speech and `write` text.
- **`thought` must exclude raw model text, but the source holds it.** The continuation header the entry is copied from carries `held_reply` text (`npcs_and_sem.md:757`; `inference_placement.md:304`). No test plants that text and expects a refusal.
- **"Agent-home digests" for the double are not defined** in the agent line's checklist (`plans/checklists.md:500-692`, which I grepped for "digest").

### E-N3. The planted wall-time test only exercises the closed schema

**Location:** `::§1` "It runs on the world's clock".

"A planted wall-time field is refused at write" proves the schema refuses unknown keys. A wall-derived integer written into the allowed `tick` field passes it. Possible fix (*unverified*): the writer asserts that each entry's tick equals the barrier's current tick.

### E-N4. The size bound and meter are loose

**Location:** `::§2` "Its size".

The codec's size budgets are per frame, checked before allocation (`npcs_and_sem.md:708-709`). Without a frame count per tick they don't bound a rate. The meter names neither a budget nor the step that sets one.

### E-N5. Citations in the draft

**Location:** §2, §7.

The draft already marks these as secondary, and I didn't fetch them. From memory (*unverified*):
- Turpin et al. 2023 (arXiv 2305.04388): the "as much as 36%" accuracy drop matches.
- Farah & Hook 2013: this is a critical review, not a meta-analysis. The meta-analytic evidence is in other papers, for example Michael et al. 2013.

### E-N6. A small slip in §9 item 7

**Location:** `::§9` item 7.

"It touches no record file" is true by O81's list (lessons, decisions, Known gaps, backlog). Note that it does edit `docs/design/contracts.md`.

## What checked out

- **Overdrive citations:**
  - O10, O13, O14, O18, O79 (and O81's amendment) and OD-EA5/6 say what the design says. On O26: "O26's reach list" is really O17's reach, which O26 restates.
  - `npcs_and_sem.md` §6.3 (one worker per agent; "nothing writes agent state from anywhere else"), §6.6 (codec kinds closed per direction; 20 NPCs in the cost estimate; retrieval strengthening at `:868-869`; lifecycle records) and §7.3 are as cited.
  - `boundaries.md` §6.2 is as cited: thoughts never a log input, `speak` text redacted in bug reports (lengths and syllable stamps, not "ticks"), the `invocation` pid, sorted-key iteration, and "replay reproduces the world, never the agents". So is §6.3 (log root id and segment; tier-2 rerun).
  - The Origin refusal is at `server.py:58-60`, and `architecture.md:96-100` calls a web export a deliberate protocol change.
  - "After mid-2027 at the earliest" is at `roadmap.md:249`. Step 4's two late branches are at `4_records_build.md:14`.
  - The leak rules in `fire_solid.md:427` and `inference_placement.md:216, 265` run world-to-NPC, as the design says.
  - The embeddable draft v7 says nothing about observation.
  - PR #81's condition 3 ("Sensed, not handed") and BF-B2 exist on `origin/phase3/joint-plan` `20ada4e`.
- **Maxim `b90800e`:**
  - All six classes exist at the paths given (`SalienceMap` :102, `AttentionNetwork` :71, `ValenceSignal` :27, `EnergyBudget` :81, `OscillatorNetwork` :79, `ProvenanceCollector` :35), and so do `Observer` (`simulation/introspection.py:23`) and `SessionSnapshot` (`memory/snapshot.py:458`).
  - The `SENSOR` gate keyed by `(entity, sensor)` is at `sim_logger.py:1707`. The wall-based NAc tick is at `nac.py:361`. "ONE persistent agent" is at `console/server.py:1272-1273`.
  - `maxim_ui.md` Phase 5 has no date. `deferred/maxim_console.md:80` matches the quoted "live observe" line. `decision_provenance.md` is deferred since 2026-09-19, with its 1.4-rung revive trigger and stages 1 and 2 shipped. The introspection plan's Phase 5 reads "Not started" (`:11`). `overdrive_refactor_candidates.md` §A4 is leak closure.
- **Pulse `a1ba1d4`:** `FacadeProvider` takes a `FacadeClient` (`context.tsx:12-16`), whose interface has 19 methods: 18 required plus the optional `onStreamGap` (`types.ts`). The "fix it in pymaxim" rule is at `AGENTS.md:44-47`.
- **The contract registration is live and can fail.** In-memory mutations of the doc:
  - adding `audit` to the kinds bullet → "its block holds ['audit'], which its marker neither names nor excludes";
  - dropping `receipt` → "its marker names ['receipt'], which its block doesn't hold";
  - a three-member copy in §4 → a restatement error.

  "Restates at 3" fits the rule: no reference outside the owner carries three members. *Verified* with `check_contracts` over every `docs/**/*.md`, and `lint_standards.py` passes on the staged tree.
- **Word budget:** 2,874 words, under the 6,000 limit for a new design.
- **§1's on/off digest test** can fail as proposed: the plant (a record value fed back into a frame) turns it red. Its gap is E-S4's load path.
