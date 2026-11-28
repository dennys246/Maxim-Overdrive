# NPC inspector design review: Bio-faithful integration

**Lens:** Bio-faithful integration (`docs/code_review.md`, "The situational lenses" and "Design reviews"). **Read:** `docs/design/npc_inspector.md` and its row in `docs/design/contracts.md`, staged in the `phase3/npc-inspector` worktree (staged tree `00b97665`, against Overdrive `origin/main` `e6d6a7f`), plus `CLAUDE.md`, `docs/code_review.md`, `npcs_and_sem.md` §6.6, `sem_stimuli.md` §6.2, `docs/maxim_upstream/embeddable_agent_DRAFT.md` §6, and `reviews/foundations_v1/delta1_trust_boundary.md`. **Maxim** `main` `b90800e` in `<maxim-clone>`: `CLAUDE.md`, `docs/plans/bio_faithful_roadmap.md`, `maxim_ui.md`, `deferred/maxim_console.md`, `deferred/reachy_app_maxim_seams.md` (EVENT seam), `deferred/annotation_context_and_provenance.md`, `deferred/decision_provenance.md`, `archive/introspection_api_plan.md`, `archive/deliberation_observability.md`, `reviews/grounding_gl3/bio-faithful.md`, and in `src/maxim/`: `simulation/sim_logger.py`, `simulation/introspection.py`, `simulation/tools.py`, `simulation/bio_telemetry.py`, `agents/prompt_builder.py`, `memory/hippocampus*.py`, `memory/strategies.py`, `tools/explain.py`, `embodied_runtime/agentic_runtime.py`, `console/server.py`, `decisions/nac.py`, and the six state classes §6 names. I searched plans, `DECISIONS.md` and `src/` for observer, introspection, telemetry, snapshot, provenance, console, readout, digest, confabulation and self-report. Maxim-pulse at `a1ba1d4` (`<pulse-clone>`) was not needed for this lens. I checked the four cited studies by web search. Line numbers are at these revisions. I edited nothing.

## Summary

The core rule in §1 is sound, and Maxim's code confirms it: an inspector that queried memory would strengthen what it showed. Maxim's own read path does exactly that today (S1). But the §6 ask rests on a false premise and missed the Maxim decision that governs observation (B1). The "instrument, not a percept" claim is right as a goal, but nothing enforces it on Maxim's side, and Maxim's current code breaks it in three places the design doesn't name (S1). The split between readout and self-report is the right instinct. Its "readout" channel, though, mixes host-made inputs with agent-made values (S4). One citation is wrong (S6). Totals: 1 BLOCKER, 8 SHOULD-FIX, 2 NIT.

## Findings

### B1. BLOCKER: §6's premise is false, and the search missed the decision that governs Maxim's observation stream

**Location:** `docs/design/npc_inspector.md::§6 "Why"` and `::§6 "Searched first"`.

**Claim vs tree.** §6 says the state a player would want ("attention, salience, valence, drives, prediction error, and why one action beat another") "never leaves the agent", and "none reaches `sim_log`". The six classes listed are indeed silent. But at `b90800e` most of the quantities named in that sentence are already emitted, per agent:
- **Prediction error:** `sim_nac(sig, valence, last_rpe, confidence)`, called from `runtime/tool_dispatch.py:197`.
- **Why one action beat another:** `NAc_RECOMMEND` (`decisions/nac.py:358-370`) logs the gate, the margin, `n_candidates`, `visit_count` and the per-modality bias consulted.
- **Drives, gates, reflexes, thoughts and deliberation salience:** `sim_drive`, `sim_gate`, `sim_reflex`, `sim_thought` and `sim_deliberation_update(salience=…)` (`sim_logger.py:1371-1910`).
- **Per agent:** every record carries an `agent_id`, set explicitly or through the `sim_agent_context` context variable (`sim_logger.py:186`).
- **Other channels exist too:** `bio_telemetry.py` persists 19 bio subsystems, and `api.on()` has typed events (`api.py:1873-1943`).

More important, the search missed the governing decision. Maxim's EVENT seam (`deferred/reachy_app_maxim_seams.md` §EVENT, decisions 4 to 6, 2026-07-28) rules on this exact topic:
- the live event stream rides `sim_log` records through `register_sim_sink`;
- "do NOT invent a new event system";
- `kind` stays an open string, and `data` stays a documented bare-dict carve-out;
- `ts` is epoch time.

`maxim_console.md:63` and `:84` follow that ruling, and `console/server.py:2095-2105` ships it. The design cites the console's "Observer + `on()`" line, which the EVENT seam explicitly reversed.

**Failure scenario.** The ask goes upstream as "emit state that is never emitted". Maxim's reviewers answer, correctly, that it is already in `sim_log` and that the EVENT seam forbids a second event system. The real defects then go unargued. Those defects are a process-global sink, wall-time stamps, an open `kind` with untyped payloads, a SENSOR sampling gate on wall time (`sim_logger.py:1706-1712`, so what gets recorded depends on wall time), and the prompt coupling in S1. Or Maxim builds a parallel channel against its own ruling. Either way the standing rule "Search Maxim before proposing to it" (B22) is broken.

**Fix (*unverified*).** Recast §6 as a question to the EVENT seam: a typed, per-agent, clock-free projection of what the step already emits, plus the few silent objects. List the gaps above as the evidence. Cite `reachy_app_maxim_seams.md` decisions 4 to 6, `bio_telemetry.py`, `api.on()`, `tools/explain.py` and `simulation/tools.py::InspectAUTTool` in "Searched first". Correct the "never emitted" sentence.

### S1. SHOULD-FIX: nothing enforces "instrument, not a percept" on Maxim's side, and Maxim's code breaks it three ways today

**Location:** `::§6 "An instrument, not a percept"`; `::§1` (the on/off test).

The §1 test guards the host's record writer against a scripted double. It cannot see a perturbation inside Maxim, and that is where the §6 readout would live. Today's Maxim couples observation to cognition in three places:
1. **Turning on the observer tells the agent it is observed.** Every sim harness calls `enable_sim_logging`, which sets `_sim_active` (`cli.py:2626`, `orchestrator.py:979`, `interactive.py:130`). `prompt_builder.py:217-222` then adds `SIMULATION_ENVIRONMENT_TEXT` (`:83-90`): "You are in a controlled simulation for testing and evaluation … Report your genuine reasoning". `:1629-1642` also forces the inner-monologue section whenever `_sim_active` is set. `InteractiveMode.ON` adds "A human user is present and watching" (`:225-230`). The logging switch is a cognition switch: the inspector's "never learns it is observed" fails the moment a host turns sim logging on to collect a readout.
2. **Maxim's "read-only" observer writes.** `simulation/introspection.py::Observer` says "Thread-safe: all reads are snapshot-style (no mutations)". Its `memory_recall` calls `hippocampus.recall`, which takes a write lock, touches every result (`access_count += 1`, `accessed_at = time.time()`, `hippocampus.py:2549-2554`) and runs promotion scoring (`hippocampus_retrieval.py:216-224`). `access_count` and `accessed_at` drive retention (`memory/strategies.py:199-219`) and consolidation (`hippocampus_consolidation.py:376-398`). `InspectAUTTool` lets the orchestrator LLM make these calls mid-campaign (`orchestrator.py:1774`). Inspecting an agent under test changes what it forgets. The design cites `Observer` neutrally, as something that "reads state after the fact".
3. **A named readout source is already an agent percept.** `agentic_runtime.py:754-759` registers `ExplainTool` on the agent's own tool registry. That tool reads `ProvenanceCollector`, one of the six objects §6 lists, and the collector persists under the agent's data directory. `introspection_api_plan.md` Phase 5 recorded that agent-facing introspection "changes AUT capabilities". Maxim's existing state-to-text paths face inward, not outward.

**Failure scenario.** Maxim implements the readout by reusing `Observer` or `ProvenanceCollector`, the cheapest path. Inspector-on runs then consolidate differently from inspector-off runs, or an NPC can call `explain` on the very record the player sees. Or Overdrive turns on sim logging in a Phase 4 developer build, and every NPC's prompt says it is being tested.

**Fix (*verified by reading* the lines above; none run).** Name these three as counterexamples in §6. Give the ask an acceptance test: readout on vs off gives byte-identical prompts and identical stores, `access_count` and `accessed_at` included. Add a **[Phase 4]** item: rerun §1's on/off test against real Maxim with the readout toggled. Open two Phase 3 pushback items (S9).

### S2. SHOULD-FIX: the guard §6 names doesn't exist in Maxim

**Location:** `::§6 "Read-only to compute"`.

"Maxim can test with its own state digest." At `b90800e` no state digest exists in `src/`. `grep -rn state_digest src` finds only `hivemind/entry_index.py`, which is unrelated. The digest is Overdrive's own proposal (`embeddable_agent_DRAFT.md`, OD-EA5, OD-EA6, OD-EA15). Unless that proposal lands, the clause has nothing to test with.

**Fix (*verified*: the grep above).** Say the guard depends on OD-EA's digest, and that the digest must cover the touch fields from S1.

### S3. SHOULD-FIX: "clock-free" covers the stamp, not the values

**Location:** `::§6 "Clock-free"`; `::§4 "Rerun"`.

The named objects compute from wall time:
- `SalienceMap` decays on `time.time()` (`salience_map.py:227`, `:524`);
- `EnergyBudget` reads `time.time()` (`energy/signal.py:111`);
- `ValenceSignal` stamps `time.time()` (`valence_signal.py:69`);
- retention reads `now - accessed_at` (`strategies.py:199`).

So a readout stamped with the tick still carries values that depend on wall time. §4's rerun comparison ("where agent behaviour diverged") would then flag divergence caused by latency, not by behaviour.

**Fix (*unverified*).** Require the readout to be clock-free in value, not only in stamp. Cite Maxim's world-clock plan (`docs/plans/world_clock_a_pre.md`) and Overdrive's world-clock draft as its dependency. Until then, state that rerun comparison of `state` entries is not meaningful.

### S4. SHOULD-FIX: the "readout" channel mixes host-made inputs with values the agent made

**Location:** `::§2 "Two channels, labelled apart"`.

"A readout is a value the substrate produced: percepts, writes, receipts, and the state readout." Two of those four are not produced by the agent:
- **Percepts** are frame values the host hands the agent's pulls. They are the stimulus, and reaching an NPC's pulls is not the same as being attended to.
- **Receipt valence** is the adapter's own report of the measured effect, under D53 (`sem_stimuli.md` §6.2, the valence row). It is the world's verdict, which the agent then learns from.
- **Provenance "as stamped"** on a write is a producer label, an oracle fact. Maxim's own record says so: "the agent never infers provenance: the producer stamps it as ground truth" (`reviews/grounding_gl3/bio-faithful.md:182-184`, citing Johnson & Raye's reality monitoring).

**Failure scenario.** A player view shows "Felt: positive" for a receipt's valence, and "knows this came from a guest" for a provenance stamp. Neither is a state of the NPC.

**Fix (*unverified*).** Use three labels, as a physiology rig keeps three channels:
- **input:** percepts and receipts (stimulus log);
- **recording:** writes, intents and `state` (what the agent computed or emitted);
- **report:** speech and thought text.

Label stamped provenance and receipt valence as host ground truth. Reserve a separate field for an agent-inferred source, if Maxim earns reality monitoring.

### S5. SHOULD-FIX: introspection tools would let self-reports quote the readout

**Location:** `::§2` (self-report); `::§7` ("Where the two channels disagree").

Maxim ships agent-callable introspection tools: `explain`, `memory_recall`, `energy_status`, `system_stats` (`agentic_runtime.py:759` and the block after it). Overdrive keeps `memory_recall` out for now "until tier A's time rows" (`delta1_trust_boundary.md:141-142`), so admitting it later is a live option. Once an NPC has these tools, its speech can quote ground-truth provenance. That makes it a superhuman-introspection ANALOG, compared with Nisbett & Wilson, and it means the two channels are no longer independent.

**Failure scenario.** The view shows "speech agrees with readout" as faithful self-report, when the agent had just read its own provenance.

**Fix (*unverified*).** For each `thought`, the record notes which introspection tools ran in that cycle, and the view marks a self-report as tool-informed. That is the only honest way to keep showing disagreement.

### S6. SHOULD-FIX: Farah & Hook 2013 is not a meta-analysis

**Location:** `::§7 "Every glow names its quantity"`.

Farah & Hook 2013, "The Seductive Allure of 'Seductive Allure'" (*Perspectives on Psychological Science* 8(1), 88–90), is a critical review. It found little empirical support for the claim that brain images are unusually persuasive. The meta-analysis is Michael, Newman, Vuorre, Cumming & Garry 2013, "On the (non)persuasive power of a brain image" (*Psychonomic Bulletin & Review* 20, 720–725): 10 experiments, about 2,000 subjects, a random-effects estimate of about 0.07 on a 4-point scale, 95% CI [−0.00, 0.14].

Weisberg et al. 2008 (*J. Cogn. Neurosci.* 20(3), 470–477) is characterised correctly in substance, but two qualifiers are missing. It used *logically irrelevant* neuroscience information. The effect was on nonexperts and strongest for bad explanations, and the expert group was not misled. A 2015 follow-up found that length and neuroscience content contributed independently.

**Fix (*verified* by web search).** Cite Michael et al. 2013 for the meta-analysis. Keep Farah & Hook as a review. Add Weisberg's qualifiers and drop the "Secondary; to verify" hedge.

### S7. SHOULD-FIX: views must name each quantity by Maxim's name and its fidelity tier, not by a brain gloss

**Location:** `::§7 "Every glow names its quantity"`.

The rule bans decoration that no value drives. It doesn't ban a real value under a misleading biological name. `bio_faithful_roadmap.md:29` lists a "dopamine-like global broadcast" as OPEN, with `ValenceSignal` as only a partial analog. Many of Maxim's bio names (NAc, SCN, hippocampus) label engineering analogs (`ANALOG` rows throughout the roadmap).

**Failure scenario.** The player view labels `ValenceSignal` "dopamine". The game itself then produces the Weisberg effect the section cites.

**Fix (*unverified*).** Developer and science views show Maxim's own name plus its EARN, ANALOG or OPEN tier. Player views use in-fiction names, never a neuroscience term the value doesn't earn.

### S8. SHOULD-FIX: the explorer must never load an agent home with Maxim to answer "what does it remember"

**Location:** `::§7 "First: an offline explorer"`; `::§4 "Replay"`.

The design limits the explorer to the record and the world log, which is correct. The obvious next feature ("browse this NPC's memories") is not ruled out, though. Loading a home and calling `recall` touches traces (S1). `ProvenanceStore` writes under the agent's data directory (`agentic_runtime.py:745-752`), so a saved agent's home would change just because someone looked at it.

**Fix (*unverified*).** One sentence in §7: a view never runs Maxim over an agent home. Browsing a home means a copy, through a reader shown to be non-touching. Until one exists, the record is the only source.

### S9. SHOULD-FIX: the pushbacks this evidence supports are not named

**Location:** `::§6`; `::§9`.

The rule "Push back on Maxim where the game shows it's wrong" applies here. The evidence above argues against three Maxim positions:
1. **The EVENT seam's decisions 4 to 6**, which make a process-global, epoch-stamped, open-`kind` stream the observation path. That is wrong for an embedded, multi-agent, deterministic host.
2. **`_sim_active` gating prompt text.** Observing should not be a cognition input. In this game the evaluation-awareness text would make every observed NPC a different NPC.
3. **`Observer`'s "no mutations" docstring**, which the code contradicts.

There is also positive evidence on offer. Maxim's `deferred/annotation_context_and_provenance.md` (F1) says "today an external reader can say 'your LLM just copies whatever tool strings you print'". Measuring readout-vs-speech disagreement over game runs is direct evidence on that open question.

**Fix (*unverified*).** Add these as Phase 3 items for after step 4 (O79). File the `Observer` docstring and the `_sim_active` coupling as Maxim issues through its own process. Record a lesson in `docs/lessons_maxim_in_games.md`: in Maxim, observation is coupled to cognition, with these numbers.

### N1. NIT: Nisbett & Wilson needs its comparison spelled out

**Location:** `::§2`.

"People's reports of their own reasons are no better" needs its comparison. Nisbett & Wilson 1977 (*Psychological Review* 84, 231–259) found subjects' reports of their own higher mental processes were no more accurate than observers' predictions made from a description of the stimulus and the response. Ericsson & Simon (1980) is the standing critique and is worth one clause.

### N2. NIT: Turpin's numbers are correct but their scope is narrower than the design implies

**Location:** `::§2`.

Turpin et al. 2023 (NeurIPS) checks out: accuracy drops of up to 36% across 13 BIG-Bench Hard tasks, and the biasing features (for example, answer "(A)" always correct in the few-shot examples) are never mentioned in the chain of thought. But it measured GPT-3.5 and Claude 1.0. Say that, so the design doesn't present it as a measured property of the models Overdrive's NPCs will run. Drop "to verify before review" for both studies.

## Checked and sound

- **§1's retrieval rule.** Confirmed by code: Maxim's `recall` touches traces under a write lock, so an inspector that recalls would strengthen what it shows. The design's answer (record only what crossed the membrane, never call `AgentPort`) is the right one.
- **§2 `thought`.** Excluding prompts and raw model text keeps the record off the agent's inference path.
- **§5 "the player acting on what they saw is an ordinary logged intent".** This is the only channel by which an NPC could learn it is observed, and it works through the fiction and its own senses. That is biologically fair: being read by a mind-reader in the story is a percept, not an instrument leak.
- **§6 leaves field choice to Maxim** (BF-B2). It stays an export of state that exists, not a design of Maxim's cognition, apart from the "why one action beat another" phrasing. Phrase that as "the decision variables the step already computes", which `NAc_RECOMMEND` shows exist.
- **Citations checked:** `sim_logger.py:1702-1709` (the SENSOR gate is keyed by entity and sensor, and is also wall-time sampled), `decisions/nac.py:361` (wall-clock tick) and `console/server.py:1272` ("the console fronts ONE persistent agent") are accurate as cited. "Phase 5 not started" in `archive/introspection_api_plan.md` is accurate.

Sources: [Farah & Hook 2013](https://neuroethics.upenn.edu/wp-content/uploads/2015/06/FH-Seductive-Allure.pdf); [Michael et al. 2013](https://www.pubmed.gov/23400855/); [Turpin et al. 2023](https://arxiv.org/abs/2305.04388v2); [Weisberg et al. 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC2778755); [Nisbett & Wilson 1977](https://deepblue.lib.umich.edu/handle/2027.42/92167?show=full).
