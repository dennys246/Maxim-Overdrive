# NPC inspector: the mind record and the views over it (design, v2 draft, 2026-11-27)

**Status:** DRAFT v2. It folds round 1's six lenses (`reviews/npc_inspector/`): Executor, Architecture, Wire
integrity, Bio-faithful, Trust boundary, and Determinism and replay. The owner asked on 2026-11-27 for a way for
players, and us, to explore what an NPC is internally experiencing, possibly through Maxim-pulse. This note holds the
contract on Overdrive's side, one question for Maxim, and the choices only the owner can make (§10). Nothing here is
decided.

**What it owns** (one owner per contract, B36):
- the mind record: what it holds, its clock, its versions, its lane, who writes it and who may read it (§2–§4);
- the rule that observation never calls into an agent (§1);
- the views' rendering and transport rules (§7);
- the upstream question's shape (§6), until a draft in `docs/maxim_upstream/` takes it (§9).

Every other contract it touches is linked to its owner, and §8 lists each change it needs elsewhere.

**Sources:**
- Overdrive `origin/main` `e6d6a7f`.
- Maxim `main` `b90800e` (2026-11-27).
- Maxim-pulse `main` `a1ba1d4`.
- Text cited from `phase3/joint-plan` (PR #81, `20ada4e`) is unmerged and is marked so.

Line numbers are at these revisions.

**Tags:**
- **[agents]:** buildable in `phase1/agents` against the scripted test double, if the owner adds it to that step (§10).
- **[Phase 4]:** real NPCs.
- **[later]:** named so the contract leaves room for it, and not built.

## 1. The rule: record at the membrane, never ask the agent

Three facts decide the shape:
- **Agent state has no read path.** Each real agent runs in its own worker (O13). The codec's kinds are closed, and
  none reads state (`npcs_and_sem.md` §6.6). Nothing writes agent state from anywhere else (§6.3).
- **In Maxim, looking changes the mind.** A recall returns a `retrieval` write applied at `settle`
  (`npcs_and_sem.md` §6.6). Maxim's own read paths touch what they read. `Observer` calls itself "snapshot-style (no
  mutations)" (`simulation/introspection.py:27`), but its recall goes through `hippocampus.recall`. That bumps
  `access_count` and `accessed_at` under a write lock (`memory/hippocampus.py:2549-2554`), and both fields drive
  retention and consolidation.
- **Replay never runs the agents.** It reproduces the world, and agent homes are saved as state
  (`boundaries.md` §6.2).

So **[agents]**:
- **The inspector never calls `AgentPort`**, never adds a codec kind or field, and never runs anything in a worker.
- **It never runs Maxim over an agent home.** Browsing a saved home means reading a copy through a reader that is
  shown not to touch it. No such reader exists yet, so until one does, the record and the logs are the only sources.
- **The record is an output, never an input.** The `Simulation`, every law, every agent and the host's restore path
  never read it. It is not a log input (`boundaries.md` §6.2).

**What the invariant promises, by tier** (`boundaries.md` §6.3):
- **Tiers 1 and 2:** a run with the record on and the same run with it off give bit-identical world digests and
  agent-home digests. That holds through a save, a load and a continue.
- **Tier 3:** wall time reaches the world there, through floor-holding lateness, `reply_landed` and the per-park
  ceiling (`npcs_and_sem.md` §4.4, §6.6). So the record is held to a cost instead: the simulation lane does no record
  IO (§3), and its per-barrier time with the record on stays within the copy budget, measured on `phase1/lanes`'
  meters.

The tests for both are in §9.

**Its clock.** Every entry is stamped with the world-time event it reports, never with when the host saw it:
- a delivery's tick;
- a barrier's tick for a refusal;
- a thought's modelled landing tick, or the tick its `reply_landed` record names.

An arrival tick is wall data in an integer's clothing, so it is never a stamp. The record holds no wall time, epoch
or Maxim timestamp, and the writer reads no clock, including for file names.

## 2. What it holds

The record holds only what neither the world log nor the agent's own audit record holds. It holds **no free text**.
Anything the log already carries (intents, speech, thought cancels and failures, `reply_landed`, worker lifecycle) a
view reads from the log itself, joined on actor and tick. Memory writes are recorded agent-side, after OD-A15
(`boundaries.md` §6.1), and the record only points at them. So there is one owner per fact. Guest words live only
where O26's purge already reaches (the log, the agent home, saves), and a bug report has no new text to drop.

<!-- contract: mind_record.kinds: stimulus refusal thought_state write_ref gap tick_end readout -->
| Kind | Holds | Channel | On replay |
|---|---|---|---|
| `stimulus` **[agents]** | one delivery as it crossed to the worker: its tick, bindings digest, one value per binding, the receipts it carried, and the bindings' receptor and site resolved from the binding table it names | input | re-derived, and compared with the recorded copy |
| `refusal` **[agents]** | an intent the host refused at stage 1: the intent's kind if it parsed, the refusal code, its byte length; never its parameters | host verdict | recorded only (the log holds stage-1-accepted intents) |
| `thought_state` **[agents]** | the host-owned continuation header's counters: thought id and kind, triggering input id, cycle index and cap, each segment's modelled landing tick, cancel status | recording | recorded only |
| `write_ref` **[after OD-A15]** | a pointer to one entry of the agent-side audit record: the write's sequence number and kind, and the count of reactivated trace ids | recording | recorded only |
| `gap` **[agents]** | a span the record doesn't cover, from tick to tick, with a closed reason (below) | — | recorded only |
| `tick_end` **[agents]** | the end of one tick's entries for this agent | — | recorded only |
| `readout` **[later]** | Maxim's per-agent state readout (§6); reserved and refused until then | recording | recorded only |

The gap reasons are closed:
- `dropped`: the queue overflowed (§3);
- `stopped`: the writer stopped after an error;
- `torn`: the file was trimmed after a crash;
- `rewound`: a worker restarted from an earlier home, and the gap names the home's snapshot tick;
- `off`: the record was switched off.

A view shows a `rewound` span's write pointers as lost, since the agent no longer holds those writes.

**Excluded by name:**
- the host-only body frame, which holds world truth at the site (`sem_stimuli.md` §4.2);
- the continuation's held reply and its agent-owned body;
- prompts and raw model text;
- anything decoded from a refused frame;
- the gateway's outcome detail;
- paths, exception text, process ids, the host environment.

A failure is shown only by its closed reasons, which `inference_placement.md` §2.6 and `npcs_and_sem.md` §6.6 own.

**A stimulus is not a percept.** The worker clamps a delivered value, adds its noise, and Maxim transduces it
(`sem_stimuli.md` §0, §4.4; `npcs_and_sem.md` §3.4). The host sees none of that. A view labels this channel
"delivered", never "perceived".

**Three channels, labelled apart:**
- **input:** what the world delivered;
- **host verdicts:** refusals, and the receipts inside a delivery;
- **recording:** what the agent computed or emitted (thought counters, write pointers, the readout).

What the agent says about itself (its speech, in the log) is a fourth channel, **report**, and a view never presents
a report as a recording. Memory provenance is stamped by the producer, so it is host ground truth, not something the
agent inferred (Maxim `reviews/grounding_gl3/bio-faithful.md:182-184`). Self-reports can misdescribe what produced
them:
- People's accounts of why they acted were no more accurate than outsiders' guesses from the stimulus alone (Nisbett
  & Wilson 1977, *Psychological Review* 84; Ericsson & Simon 1980 is the standing critique).
- With GPT-3.5 and Claude 1.0, chain-of-thought explanations left out the biasing features that drove the answers.
  Those features cost up to 36% accuracy across 13 BIG-Bench Hard tasks (Turpin et al. 2023, NeurIPS).

So where a report and a recording disagree, a view shows the disagreement.

**When a report has read the recording.** Maxim's agent-callable introspection tools can read the same state
(`embodied_runtime/agentic_runtime.py:754-759`, `explain` and others). Once the host can see which ones ran in a cycle
(cognition tools as follow-ups, `npcs_and_sem.md` §6.1), the thought counters name them. A report from that cycle is
then marked tool-informed. Until then a view says it can't tell.

## 3. The format, the lane, and failure

- **The format.** It follows the intent log's pattern (`sim_core.md` §14):
  - one c14n-1 record per line after a header record;
  - a declared `Format`, held by others, so it migrates or refuses;
  - a gate-registry row and golden fixtures.

  `simcore.core.schema` refuses fields named for ticks today, the same tension the intent log has. The amendment is
  one shared dependency, made in `schema.py` and `tile_and_client.md` §3.2, the rule's owner (§8).
- **One record per agent per log segment.** Each restore and each restart opens a segment (`boundaries.md` §6.3;
  `npcs_and_sem.md` §6.6). The header carries:
  - the log root id;
  - its own segment and the parent segment;
  - the scene digest;
  - the bindings digest;
  - the record's version.

  A save carries each record truncated at the save's barrier, and a load opens a child record. This follows the
  response cache's rule (`inference_placement.md` §4.2), which it links rather than restates. Whether the record was
  on is a field of the log header (§8), so a missing record reads as "off", not as "lost".
- **The lane.** The simulation lane builds each entry as a frozen value, in the record's order, and puts it on a
  bounded queue. It never blocks and never does IO. A record lane drains the queue and writes whole ticks, each
  closed by a tick end. This is the pattern of `realtime_lanes_coop.md` §4.1's record lane. The order within a tick
  is the record's own key: kind in the table's order, then actor id, then the entry's sequence.
- **Failure never stops the world.** On overflow, the record lane writes a `dropped` gap when it catches up. On a
  write error it writes a `stopped` gap if it can, and then stops. Either way it raises a typed host status and a
  meter, never a swallow. Whether a record failure should instead stop the run is the owner's call (§10).
- **No worker can make the writer refuse.** Each field's bound is derived from the codec's bound for the value it
  copies, and a test asserts that they're equal. So any value the codec accepted fits the record. A value that
  somehow fails anyway becomes a `stopped` gap, never an exception at the barrier.
- **Crashes.** The reader trims a torn final tick, reports it as a `torn` gap, and refuses any other corruption. A
  view reads the record and the world log only up to the last tick complete in both.
- **Size.** It holds no text, so its rate is set by deliveries and refusals. The meter is bytes per agent per world
  minute, measured with the double at the 20-NPC load `npcs_and_sem.md` §6.6's cost estimate uses. The rotation unit
  is the segment. The reader's budgets (bytes per line, entries per file, values per delivery) are contract, derived
  from the codec's size budgets and measured at the build step.

## 4. Who reads it, and where the code lives

- **The writer** lives in `simcore.host`, the layer that owns the barrier and saves.
- **The reader** is one Python gate module in `simcore.host`. It is the only reader in any language: a Godot or web
  view reads only that gate's validated output, never the raw file. It gets a gate-registry row and an input-gate
  entry. A mind record from someone else's save is the strictest class of input (`boundaries.md` §5.3, §5.4).
- **The import rule** names that module. Only the view's entry point and the save-copy path may import it. Every
  other module is refused, the host's restore path included, which an import contract enforces.
- **The writing scan:** no function outside the writer's module opens a record for writing.
- **Engine and game.** The record, its lane and its gate are engine. The audiences, the fiction and any player view
  are the game's (§5, §7).

## 5. Who may see what: the information rules this feature needs

- **What exists today.** One rule already governs what a player learns of an NPC: the thinking NPC's pause, shown
  diegetically through a host status channel (`npcs_and_sem.md` §5.4). A player view joins that rule. It doesn't
  become a second owner of it.
- **Stimuli reveal more than the client sees, from the first real NPC.** The client's snapshot carries display
  quantization of a few channels (`client_rendering.md` §4.2). Body-site tissue values never reach it. So a player
  view needs its rule at Phase 4, not later: delay, coarsen, or gate the view by the fiction.
- **The tiers bind display, not confidentiality.** The developer, player and guest views (§10) filter what a view
  shows. The file holds everything the record holds.
- **The record never leaves the host's machine** except in a save or a bug report the host chooses. A guest's client
  receives only a slice the server cuts. Handing a save to another person is a disclosure under O54 and O55's consent
  rules. The record adds no guest text to that, because it holds none.
- **Host data never enters**, by the closed field schema in §2. Maxim's stock surfaces do carry host data:
  - `energy_status`'s wall windows (`tools/introspection.py:415, 437`);
  - memory timestamps (`:745`);
  - the console envelope's epoch `ts` (`console/server.py:1872`).

  None of them is a source.
- **A player who acts on what they saw** files an ordinary logged intent, and world replay holds.

## 6. The question for Maxim: a typed, per-agent projection of what a step already emits

**What exists, and the decision that governs it.** Maxim's main already emits, per agent, much of what a viewer wants:
- prediction error (`sim_nac`, `runtime/tool_dispatch.py:197`);
- why one action won (`NAc_RECOMMEND`, `decisions/nac.py:355-380`);
- drives, gates, reflexes, thoughts and deliberation salience (`simulation/sim_logger.py`);
- a per-session bio log (`simulation/bio_telemetry.py`);
- `api.on()` for embedders.

The EVENT seam governs this stream (`deferred/reachy_app_maxim_seams.md`, decisions 4 to 6; shipped in
`console/server.py`):
- it rides `sim_log` records through `register_sim_sink`, and there is to be no new event system;
- `kind` stays an open string, with untyped `data`;
- `ts` is epoch time.

Six objects are silent: `SalienceMap`, `AttentionNetwork`, `ValenceSignal`, `EnergyBudget`, `OscillatorNetwork` and
`ProvenanceCollector`.

**Why that stream can't serve an embedded, deterministic, multi-agent host.** The evidence, each item read at
`b90800e`:
- **The sink is process-global** (`sim_logger.py:657`), and its SENSOR sampling gate is keyed by entity and sensor,
  not by agent (`:1702-1709`).
- **Timing is wall time.** The envelope stamps epoch time, NAc's tick is wall-based (`nac.py:361`), and the SENSOR
  gate samples on wall time. So what is recorded depends on latency.
- **The values themselves are computed on wall time,** not only the stamps: salience decays on `time.time()`
  (`attention/salience_map.py:227`), and so do energy and valence stamps and retention (`memory/strategies.py:199`).
- **Observing changes the agent.**
  - Turning sim logging on sets `_sim_active`, which adds "You are in a controlled simulation for testing and
    evaluation…" to the prompt (`agents/prompt_builder.py:83-90, 217-222`). Interactive mode adds "A human user is
    present and watching".
  - `Observer`'s recall touches what it reads (§1).
  - `explain` hands provenance back to the agent.

**The question,** as a question to that seam and not a new system: can `step` return, beside its intents, an
optional, frozen, versioned projection of what the step already computed or emits? It would be:
- **Per agent**, with no process-global sink.
- **Clock-free in value as well as stamp.** This depends on Maxim's world-clock work (`docs/plans/world_clock_a_pre.md`)
  and Overdrive's draft (`docs/maxim_upstream/world_clock_release_DRAFT.md`). Until then, comparing `readout` entries
  across reruns means nothing.
- **Typed and bounded**, with no free-form dict.
- **Observation-neutral.** With the projection on and off, prompts are byte-identical and the stores are identical,
  `access_count` and `accessed_at` included. That test needs a state digest Maxim doesn't have. The one proposed is
  Overdrive's (OD-EA5, OD-EA6 in `embeddable_agent_DRAFT.md`), and it must cover those touch fields.

Which values it holds, and how they map to Maxim's objects, is Maxim's design. The phrase is "the decision variables
the step already computes", not a choice made here.

**It is an instrument, not a percept.** The agent never receives the projection, never reads it, and never learns it
is observed. Maxim's code today breaks that in the three ways above, so the projection can't be built by reusing
`Observer`, `ProvenanceCollector` or the sim-logging switch.

**On Overdrive's side** it is a field of the codec's step output, a format change that `npcs_and_sem.md` §6.6 and
`sem_stimuli.md` §5 own. It needs a version bump, a gate row and golden rejection frames. It also gets its own line on
the barrier budget, which §6.6 estimates at 0.2–0.8 wall seconds per second for 20 NPCs before it.

**Also searched** (B22), with nothing found that plans a per-agent, clock-free projection:
- `maxim_ui.md` Phase 5 (pulse's "full dashboard", undated);
- `deferred/maxim_console.md`'s "live observe";
- `deferred/decision_provenance.md` (deferred, and revives on a 1.4 rung);
- `archive/introspection_api_plan.md` Phase 5 (not started);
- `deferred/annotation_context_and_provenance.md` F1;
- `simulation/tools.py::InspectAUTTool`;
- `overdrive_refactor_candidates.md` §A4 (leak closure only);
- Overdrive's embeddable draft v7, which says nothing about observation.

**It serves three consumers:**
- pulse, whose stream is untyped, wall-stamped and single-agent (`console/server.py:1272`);
- this record;
- Maxim's own open question of whether its LLM "just copies whatever tool strings you print" (F1). Measuring
  report-against-recording disagreement over game runs is direct evidence on that.

## 7. The views

- **First: an offline explorer [agents].** It reads a record and the world log after a session, as Dwarf Fortress's
  Legends Viewer reads exported history outside the game. It has three parts:
  - a per-NPC inspector;
  - a timeline scrubber on the world tick;
  - a cause behind every line, joined on `(actor_id, seq)`, the intent id receipts carry (`boundaries.md` §6.1). The
    invocation pid is null until Maxim's G17.
- **Which UI** is the owner's choice (§10):
  - **pulse's kit**, with a client that reads the gate's output. Its interface is 19 methods of a single-agent
    console, and pulse's rule puts capability in pymaxim first (pulse `AGENTS.md:44-47`).
  - **Overdrive's own viewer**, in Godot or a static page.
- **Transport.** An offline view opens a file the user chose, and starts no network listener. Any listener that
  serves record data follows `boundaries.md` §5.3's handshake (`127.0.0.1`, no `Origin`, a per-launch token), or it
  is a design change reviewed on its own. That includes Maxim's console, whose trusted-origin rule differs. The world
  server stays closed to browsers.
- **Everything is drawn as plain text.** The record holds no text, but a view also shows log speech and audit-record
  text. All of it is drawn as plain text: no BBCode, HTML or Markdown. That means a Godot `Label`, or `RichTextLabel`
  with BBCode off, as `npcs_and_sem.md` §5.2 requires for speech, and `textContent` on a page. A terminal view
  escapes C0, C1 and bidi controls. The host's text gates pass markup (`player_text` keeps `[img]…[/img]` and
  `<img …>`, verified in round 1), so each view gets a planted-markup test.
- **Names and tiers.**
  - A developer or science view shows Maxim's own name for each quantity, with its fidelity tier from Maxim's
    `bio_faithful_roadmap.md` (EARN, ANALOG or OPEN).
  - A player view uses in-fiction names, and never a neuroscience term the value doesn't earn. Calling
    `ValenceSignal` "dopamine" would be wrong: the roadmap lists dopamine-like broadcast as OPEN.
  - No view draws a glow that no value drives.
  - Brain images barely change how convincing an explanation seems (Michael et al. 2013, *Psychonomic Bulletin &
    Review* 20, a meta-analysis of about 2,000 subjects; Farah & Hook 2013 is a review). But logically irrelevant
    neuroscience text made bad explanations more satisfying to non-experts (Weisberg et al. 2008, *J. Cogn.
    Neurosci.* 20).
  - The never-colour-alone rule applies.
- **Later: a live in-game view [Phase 4]** through a new host-to-client message carrying a server-cut slice, a wire
  contract `client_rendering.md` §4.1 owns, under §5's rules. A purge can't recall what was already shown. That is a
  known limit beside O26's replay boundary.

## 8. What this changes elsewhere

Each is a proposed edit to its owner section. It is made in the build step that needs it, or ruled by the owner.
None of them is made here.
- `boundaries.md` §6.3, the log header: whether the record was on.
- `boundaries.md` §5.3, the gate table: the record joins "saves, intent logs, bug reports".
- Save v1 (`roadmap.md` Phase 4; `boundaries.md` §7.1): a save carries the records, truncated at its barrier.
- `simcore.core.schema` and `tile_and_client.md` §3.2: the tick-field rule, shared with the intent log.
- `npcs_and_sem.md` §6.6 and `sem_stimuli.md` §5: the step output's `readout` field [later].
- `boundaries.md` §6.1, the audit record (OD-A15): it gets a sequence number per write, which `write_ref` points at.
- `pyproject.toml`: the import contract (§4).

## 9. When, and the tests

- **Nothing to inspect yet.** Phase 4's first real NPC is after mid-2027 at the earliest (`roadmap.md`), and O10 bars
  a developer mode with real Maxim before tier A.
- **[agents]**, if the owner adds §1–§4 to `phase1/agents`' checklist. Each test is proved by breaking what it guards:
  - **On/off with an echo double.** The double folds every input it receives (deliveries, receipts, resumes) into its
    home. Its home digest is the c14n-1 hash of that home, owned by this design for the double. Planting a recorded
    value into a delivery turns the test red, and so does a restore path that reads the record. The run goes through
    a save, a load and a continue.
  - **A stalled writer.** A record lane that stalls for N wall seconds leaves the simulation lane's per-barrier time
    within the copy budget. Once `phase1/lanes` brings the meters, this test gets a number.
  - **Reproducibility.** Two record-on runs, including under different hash seeds, give byte-identical records.
  - **Replay against the record.** Replay never writes a record. It recomputes the deliveries in memory and compares
    them byte for byte with the recorded ones, so a drifting writer goes red.
  - **Stamps.** A wall-derived integer in a tick field is caught: the writer asserts that each stamp equals the
    world-time event it names. Planted paths, exception text and process ids are refused.
  - **Bounds.** Each record bound equals its codec bound, and an oversized planted value becomes a `stopped` gap with
    the world digest unchanged.
  - **The rest:** torn-tick trimming, segment parent links, and planted markup in every view.
- **[Phase 4]:** the real record; the rerun comparison of deliveries; the projection-off check against real Maxim; the
  in-game view under §5.
- **Upstream, after step 4 merges (O79).** The §6 question is drafted in `docs/maxim_upstream/`, which becomes its one
  owner. It gets an `OD-` id and a Phase 3 row. So do the three pushbacks it carries:
  - the EVENT seam's decisions 4 to 6, for an embedded multi-agent host;
  - `_sim_active` putting observation into the prompt;
  - `Observer`'s "no mutations" docstring, which its code contradicts.

  A lesson records what this round found: in Maxim, observation is coupled to cognition. The joint plan (PR #81,
  unmerged) gets the question as a link both ways.

## 10. For the owner

1. **The information rules (§5).** What may a player learn of an NPC, and when? Is the deep view earned in the
   fiction? Stimuli reveal more than the client sees from Phase 4.
2. **Audiences:** a developer and science view, a player view, or both?
3. **The ethics framing:** witnessing a life, or dissecting one?
4. **A record failure (§3):** does it leave a gap and let the world go on (the author's recommendation), or stop the
   run?
5. **Scope:** do §1–§4 and §9's tests enter `phase1/agents`' checklist, or wait for Phase 4?
6. **The explorer's UI:** pulse's kit or Overdrive's own (§7)?
7. **This branch and step 4.** Step 4 runs alone (O79), and its exit test requires no open PR. This branch is in
   neither O79's nor O81's order. It can be reviewed and merged before step 4, like PR #81. Or the owner can amend
   step 4's brief to name it as a late branch on #80's terms: no PR, no merge and no record edit until step 4 merges.
   It touches no record family; it edits `contracts.md`'s registry.
