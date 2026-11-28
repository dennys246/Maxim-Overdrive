# NPC inspector delta review: Bio-faithful integration

**Lens:** Bio-faithful integration (`docs/code_review.md`, the lens row and "Design reviews"). **Read:** v2 of `docs/design/npc_inspector.md` (working tree, blob `20b6cbb1`), the fold diff against v1 (`git diff bd0137d`), round 1's `bio_faithful.md`, and the author's `fold.md` (blob `5791d71e`). I read `fold.md` as a set of claims, not as statuses. I also read `CLAUDE.md`, `records_layout.md`, `npcs_and_sem.md` §6.1 and §6.6, and `embeddable_agent_DRAFT.md`. **Maxim** `main` `b90800e` in `<maxim-clone>`. I re-read every Maxim line and passage v2 cites, plus `api.py:1931-2034`, `energy/signal.py`, `valence_signal.py`, `world_clock_a_pre.md` and `overdrive_refactor_candidates.md` §A4, and I grepped `src/` for `def step(`. **Pulse** `a1ba1d4` in `<pulse-clone>`: `AGENTS.md:42-48`. I edited nothing.

**A correction to my own round 1 comes first.** My B1 said the EVENT seam's decisions 4 to 6 "rule on this exact topic" and forbid "a second event system". My S9 item 1 told the author to push back on those decisions. Both overstated what the seam says:
- **Decision 4** (`reachy_app_maxim_seams.md:173`) governs the console's web bridge. It also says `api.on()` "stays the embedder-SDK surface".
- **"Do NOT invent a new event system"** (`:100`) is the front gate for that same bridge.
- **Decision 6's epoch `ts`** (`:175`) is reasoned from the browser's cross-run ordering.

v2 followed my framing, so part of new finding D1 is my error carried into the fold.

**Summary.** Round 1's findings are folded faithfully: 11 fixed, 1 deferred with a trigger, none open. Every Maxim citation v2 adds checks out at `b90800e`, line for line, with the small exceptions in D3. v2 no longer designs Maxim's cognition from outside:
- the projection's fields are left to Maxim;
- "clock-free in value" is delegated to Maxim's accepted world-clock plan, whose A-post row covers salience (`world_clock_a_pre.md:240`).

"A stimulus is not a percept" is faithful. The channel labelling is right in the prose but wrong in the table for one kind that the fold added (D2). The studies are now stated correctly.

There are three new findings in text the fold added: two SHOULD-FIX and one NIT. Neither SHOULD-FIX is a contract blocker. **No new BLOCKER is in text the fold added.**

## Round 1 status (set from the v2 tree)

| Finding | Status | Evidence in v2 |
|---|---|---|
| B1 | fixed | The "never leaves the agent" and "none reaches `sim_log`" sentences are gone (grep: no hits). §6 now opens with "What exists, and the decision that governs it": `sim_nac` `tool_dispatch.py:197`, `NAc_RECOMMEND` `nac.py:355-380`, `bio_telemetry.py`, `api.on()`, decisions 4 to 6. "Also searched" adds `InspectAUTTool`, F1 and the console's live view. How the ask is now aimed is a new finding (D1). |
| S1 | fixed | All three couplings are named in §6 "Observing changes the agent": `_sim_active` prompt text (`prompt_builder.py:83-90, 217-222`, verified), `Observer`'s touching recall (§1, `introspection.py:27`, `hippocampus.py:2549-2554`, verified), and `explain`. The acceptance test is there (byte-identical prompts; identical stores, `access_count` and `accessed_at` included), and so is the Phase 4 "projection-off check against real Maxim" (§9). Reusing `Observer`, `ProvenanceCollector` or the logging switch is ruled out. |
| S2 | fixed | §6: "That test needs a state digest Maxim doesn't have. The one proposed is Overdrive's (OD-EA5, OD-EA6), and it must cover those touch fields." |
| S3 | fixed | §6: "Clock-free in value as well as stamp", depending on `world_clock_a_pre.md` (which exists, accepted 2026-11-24) and Overdrive's draft. "Until then, comparing `readout` entries across reruns means nothing." The wording has a NIT (D3). |
| S4 | fixed | §2 "Three channels, labelled apart" plus report as a fourth. Receipt valence is dropped from the record. Stamped provenance is called host ground truth, citing `grounding_gl3/bio-faithful.md:182-184` (verified). A new kind carries the same defect (D2). |
| S5 | fixed | §2 "When a report has read the recording": tool-informed marking once the host sees which tools ran (`npcs_and_sem.md` §6.1, the follow-up row, "proposed; not adopted"). Until then "a view says it can't tell". It is honest about depending on an unadopted contract. |
| S6 | fixed | §7: Michael et al. 2013 is the meta-analysis (about 2,000 subjects), Farah & Hook a review. Weisberg is limited to logically irrelevant text, bad explanations and non-experts. The hedge is gone. |
| S7 | fixed | §7 "Names and tiers": Maxim's name plus EARN, ANALOG or OPEN; in-fiction names for players. The dopamine example matches `bio_faithful_roadmap.md:29` (verified). |
| S8 | fixed | §1: "It never runs Maxim over an agent home", reading only a copy through a reader shown not to touch it, and until then the record and the logs only. |
| S9 | deferred | **Reason:** the lesson file is a record family that step 4 migrates (`records_layout.md:3, :39`), and O79 bars record edits until step 4 merges. **Trigger:** step 4 merges (§9 "Upstream, after step 4 merges"). The three pushbacks, the `OD-` id, the Phase 3 row and the lesson are named there. Until then the evidence lives in this branch's committed reviews, so it is not lost. Pushback 1 is misaimed (D1). |
| N1 | fixed | §2: Nisbett & Wilson's comparison is spelled out as outsiders' guesses; Ericsson & Simon is named as the critique. |
| N2 | fixed | §2: Turpin is scoped to GPT-3.5 and Claude 1.0, with 36% and 13 BBH tasks. The hedge is gone. |

## Checks on the fold's new §6 claims

- **Process-global sink:** correct. `_sim_sinks` is a module-level list (`sim_logger.py:658`; v2 says `:657`, which is the blank line before it). The SENSOR gate keys on `(entity, sensor)` and samples on `time.time()` (`:1708-1713`).
- **Wall-time timing:** correct. NAc's tick is `int(time.time() - _sim_start)` (`nac.py:361`). The sink record's `t` is wall-elapsed (`sim_logger.py:1056, 1072`), and the console envelope stamps `time.time()` (`console/server.py:1872`).
- **Observation coupled to cognition:** correct as quoted. `InteractiveMode.ON` adds "A human user is present and watching" (`prompt_builder.py:225-230`), which is a host mode rather than an observer switch, and v2 lists it as such. `ExplainTool` is registered on the agent's registry, and its store sits under the agent's home (`agentic_runtime.py:745-759`).
- **Pulse:** "capability in pymaxim first" matches `AGENTS.md:42-48`, and "fronts ONE persistent agent" matches `console/server.py:1272`.
- **"Also searched":** `maxim_ui.md` Phase 5 (`:66`), the 1.4-rung revive trigger in `decision_provenance.md` (`:4`) and §A4 "leak closure" are each accurate.
- **"A stimulus is not a percept":** faithful. What the host can see is the delivered value; clamping, noise and transduction happen agent-side. "Delivered", never "perceived", is the right label, and it also avoids implying the value was attended to.
- **Designing from outside:** none found. "The decision variables the step already computes" leaves field choice to Maxim. "Observation-neutral" and "clock-free in value" are acceptance properties that depend on Maxim's own plans (world clock, the `_sim_active` pushback), not mechanisms designed here.

## New findings

### D1. SHOULD-FIX: the §6 question and pushback 1 are aimed at a decision that excludes embedders, and at a `step` Maxim doesn't have

**Location:** `docs/design/npc_inspector.md::§6 "The question"`, `::§6 "What exists, and the decision that governs it"`, and `::§9 "Upstream"` pushback 1.

**Defect.**
- **The question.** §6 asks "as a question to that seam and not a new system: can `step` return, beside its intents, an optional … projection". At `b90800e` Maxim has no agent `step` that returns intents. `grep -rn "def step(" src/maxim` finds only environments and `time/oscillator.py`. The `step(agent, world_dt_us, frame)` that returns a `StepOutput` is Overdrive's own proposal (`embeddable_agent_DRAFT.md:48`). So the projection is an amendment to OD-EA's `StepOutput`. It is not a question to the EVENT seam.
- **The seam.** The seam governs the console's web bridge, and decision 4 (`reachy_app_maxim_seams.md:173`) names `api.on()` as "the embedder-SDK surface". Decision 6's epoch `ts` is reasoned for a browser's cross-run ordering (`:175`) and is sound for that consumer.
- **Pushback 1.** It says "the EVENT seam's decisions 4 to 6, for an embedded multi-agent host". That argues against decisions that never claimed the embedded host.

v2 states the digest's ownership honestly (OD-EA5, OD-EA6) but not the `step`'s. This came from my round-1 B1 and S9 framing (see the correction above).

**Failure scenario.** The draft goes upstream after step 4. Maxim's reviewers answer that decisions 4 to 6 are the console wire's, that decision 4 already keeps `api.on()` as the embedder surface, and that `step` is Overdrive's OD-EA proposal, so the question should go there. The real defects in `sim_logger` code then go unargued a second time:
- a module-global sink;
- a SENSOR gate keyed without the agent and sampled on wall time;
- NAc's wall tick.

Alternatively, Maxim reopens a console decision that is correct for the console.

**Fix (*verified* by reading `reachy_app_maxim_seams.md:100, 173-175`, `api.py:1931-2034` and `embeddable_agent_DRAFT.md:48`, and by the grep above).**
- Aim the question at OD-EA's `StepOutput`, as a field the OD-EA draft takes, and at Maxim's embedder surface: `api.on()`, which decision 4 keeps for embedders and which carries "4 coarse events (2 dead)" (`:100`).
- Cite the EVENT seam as the reason `sim_log` can't serve this host, not as the decision to change.
- Recast pushback 1 against the code facts: `sim_logger`'s process-global sink and SENSOR gate (`:658`, `:1702-1713`) and NAc's wall tick (`nac.py:361`). Drop decision 6 from it.

### D2. SHOULD-FIX: `thought_state` is host bookkeeping labelled as the agent's recording, and the table's channels disagree with the prose

**Location:** `docs/design/npc_inspector.md::§2` (the kinds table, `thought_state` and `stimulus` rows; "Three channels, labelled apart").

**Defect.**
- **`thought_state`.** Its own row calls it "the host-owned continuation header's counters", but the table puts it in the **recording** channel, which the prose defines as "what the agent computed or emitted". The header is host-owned and never sent (`npcs_and_sem.md:380, :754`). Its fields are host facts:
  - each segment's "modelled landing tick" is the host's latency model;
  - "cycle index and cap" is the host's cap, which governs over Maxim's `deliberation_max_cycles` (`npcs_and_sem.md:574`);
  - cancel status is a host verdict;
  - the triggering input id is host routing.

  This is the S4 defect again, in a kind the fold added.
- **`stimulus`.** The row carries "the receipts it carried" under the channel **input**, while the prose files "the receipts inside a delivery" under **host verdicts**.

**Failure scenario.** A developer view reads each kind's channel from the table and shows "NPC deliberated 3 of 3 cycles, landed at tick 4120, cancelled" as the NPC's recording. That reads as a measure of the agent's effort and timing. It is really the host's scheduler and latency model. A slow GPU or a different dial moves it, not the NPC. Separately, a receipt is labelled "input" in one view and "host verdict" in another.

**Fix (*unverified*).**
- Label `thought_state` **host verdict** (or a fifth label, "host bookkeeping"). Keep **recording** for `write_ref` and `readout`, the only agent-made values.
- Give the `stimulus` row a per-part channel: values are input, carried receipts are host verdict.
- Since a view relies on this per-kind channel, it is contract and belongs in the table.

### D3. NIT: §6's "values computed on wall time" bullet mixes a value with a stamp, and cites only one of its four claims

**Location:** `docs/design/npc_inspector.md::§6 "Why that stream can't serve"`, third bullet.

The bullet reads: "salience decays on `time.time()` …, and so do energy and valence stamps and retention". Against the source:
- **Energy:** a real wall-time value. `EnergyBudget._recharge` integrates `elapsed * recharge_rate` from `time.time()` (`energy/signal.py:109-114`). v2 gives no citation.
- **Valence:** only a stamp. `timestamp=time.time()` (`valence_signal.py:69`), so it doesn't support a bullet about values. No citation either.
- **Salience:** `time.time()` is the default of an injectable `current_time` parameter (`salience_map.py:222-227`). Its wall clock comes from the feeder, which is why the world-clock plan fixes it with OD-A9 (`world_clock_a_pre.md:240`).
- **Retention:** correctly cited (`strategies.py:199`).

A Maxim reviewer would correct this precision on sight. **Fix (*verified* by reading the lines above):** "salience (fed a wall `now`), energy recharge (`energy/signal.py:111`) and retention (`strategies.py:199`) compute on wall time; valence carries a wall stamp (`valence_signal.py:69`)".

### Also checked: the F1 claim

**Location:** `docs/design/npc_inspector.md::§6 "It serves three consumers"`, the third consumer.

v2 quotes F1 as "just copies whatever tool strings you print". The source (`annotation_context_and_provenance.md:26`) continues "**as rewarding**": F1 is about the LLM's valence annotation against the substrate's per-cluster credit. v2 then calls report-against-recording disagreement "direct evidence on that". That only holds once the record holds both the LLM's annotation and the substrate's value. v2's record holds no valence: receipt valence was dropped, and `readout` is **[later]**. My round-1 S9 made the same overclaim.

I file this under D1's upstream-draft scope rather than as a separate SHOULD-FIX. **Fix (*verified* by reading `:24-27`):** quote it whole, and say the evidence becomes direct only once `readout` carries the step's credit values beside the annotation.

**Totals:** round 1 is 11 fixed, 1 deferred (S9, trigger: step 4 merges), 0 open, 0 rejected. New findings: 0 BLOCKER, 2 SHOULD-FIX (D1, D2), 1 NIT (D3). No new BLOCKER is in text the fold added. D1 and D2 are both fold-added text. D2 touches a per-kind label that views depend on, so it should fold. D1 touches the upstream question's aim, which §9 hands to a `docs/maxim_upstream/` draft after step 4, so it may fold there instead, with that draft as its trigger.
