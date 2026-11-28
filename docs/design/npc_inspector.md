# NPC inspector: the mind record and the views over it (design, v3 draft, 2026-11-27)

**Status:** DRAFT v3. It folds round 1's six lenses and their delta round (`reviews/npc_inspector/`): Executor,
Architecture, Wire integrity, Bio-faithful, Trust boundary, and Determinism and replay. The owner ended the paper
rounds here under the charter's stop rule (NI1), and the mechanism findings are deferred to the build steps §9 names.
The owner asked on 2026-11-27 for a way for players, and us, to explore what an NPC is internally experiencing. This
note holds the contract on Overdrive's side and one question for Maxim. The owner's rulings on its questions are
`reviews/npc_inspector/rulings.md` (NI1 to NI9, 2026-11-27).

**What it owns** (one owner per contract, B36):
- the mind record: its kinds, its gap reasons, its stamps, its format, its lane, who writes it and who may read it
  (§1–§4);
- the rule that observation never calls into an agent (§1);
- the views' rendering and transport rules, and the gate's output format for a view (§7);
- the upstream question's shape (§6), until a draft in `docs/maxim_upstream/` takes it (§9).

Every other contract it touches is linked to its owner, and §8 lists each change it needs elsewhere.

**Sources:**
- Overdrive `origin/main` `e6d6a7f`.
- Maxim `main` `b90800e`.
- Maxim-pulse `main` `a1ba1d4`.
- Text on `phase3/joint-plan` (PR #81) is unmerged and is marked so.

**Tags:**
- **[agents]:** buildable in `phase1/agents` against the scripted test double, which it enters (NI3).
- **[lanes]:** needs `phase1/lanes`, which comes after it.
- **[Phase 4]:** real NPCs.
- **[later]:** named, not built.

## 1. The rule: record at the membrane, never ask the agent

Three facts decide the shape:
- **Agent state has no read path.** Each real agent runs in its own worker (O13). The codec's kinds are closed, and
  none reads state (`npcs_and_sem.md` §6.6). Nothing writes agent state from anywhere else (§6.3).
- **In Maxim, looking changes the mind.** A recall returns a `retrieval` write applied at `settle`
  (`npcs_and_sem.md` §6.6). Maxim's own read paths touch what they read. `Observer` calls itself "snapshot-style (no
  mutations)" (`simulation/introspection.py:27`). But its recall takes a write lock and touches every result
  (`memory/hippocampus_retrieval.py:217-221`), setting `access_count` and `accessed_at`
  (`memory/hippocampus.py:2549-2554`). Both drive retention (`memory/strategies.py:199`).
- **Replay never runs the agents** (`boundaries.md` §6.2).

So:
- **The inspector never calls `AgentPort`** and never runs anything in a worker. Its [agents] build adds no codec
  kind or field. The [later] state readout is a field change, which §6 names.
- **It never runs Maxim over an agent home.** Browsing a saved home means reading a copy through a reader shown not to
  touch it. Until one exists, the record and the logs are the only sources.
- **The record is an output, never an input.** The `Simulation`, every law, every agent, replay, and the host's
  restore path never read it (§4).

**What the invariant promises, by tier** (`boundaries.md` §6.3):
- **A live run under tier-1 or tier-2 conditions:** with the record on and off, the world digests and agent-home
  digests are bit-identical, through a save, a load and a continue.
- **Tier 3:** wall time reaches the world there (`npcs_and_sem.md` §4.4, §6.6), so the record makes no promise about
  barrier time. It is host load, like any other: it does no IO on the simulation lane, it runs on its own thread
  (§3), and it has its own B5 row. That row includes a meter of the world log's write time with the record on and
  off, since both share the disk **[lanes]**.

**The stamps.** Each entry is stamped with the tick of the barrier at which the host made the change it reports. That
is a world-time event, known when the entry is built. Each kind's stamp is in §2's table. Future ticks, such as a
thought's modelled landing tick, are fields, never stamps. No arrival tick, wall time, epoch or Maxim timestamp enters
the record, and the writer reads no clock, including for file names.

## 2. What it holds

The record holds no free text. It holds only what neither the world log nor the agent-home audit record holds,
except for one check copy, `stimulus`, which replay compares against and never trusts.
- **From the log:** a view reads everything the world log carries (intents, speech, thought cancels and failures,
  `reply_landed`, worker lifecycle) from the log itself.
- **From the audit record:** memory writes are recorded agent-side after OD-A15 (`boundaries.md` §6.1), and the
  record only points at them.
- **Where guest words live:** only in places O26's list already names ("agent stores, continuation bodies, the
  response cache's requests, saves and the intent log"). Whether the live audit record counts as an agent store is
  OD-A15's owner's to say (§8).

<!-- contract: mind_record.kinds: stimulus refusal thought_state write_ref gap tick_end readout -->
| Kind | Holds | Stamp | Channel | On replay |
|---|---|---|---|---|
| `stimulus` **[agents]** | one delivered BoundFrame, whole (`sem_stimuli.md` §4.2), receipts in §6.2's form; the reader resolves receptor and site from the bindings digest | the delivery's tick | values: input; receipts: host verdict | per tick, values compared with replay's bound lane |
| `refusal` **[agents]** | an intent refused at stage 1: its kind if it parsed, its sequence number, the refusal code, its byte length; never its parameters | the barrier's tick | host verdict | recorded only (the log holds stage-1-accepted intents) |
| `thought_state` **[agents]** | the host-owned continuation header after one change (a request, a resume, a cancel): thought id and kind, triggering input id, cycle index and cap, each thought segment's modelled landing tick, cancel status | the tick of the change | host bookkeeping | recorded only |
| `write_ref` **[after OD-A15]** | a pointer to one audit-record entry, keyed by (log segment, settle tick, index in the host's canonical write order), and the write's kind | the settle tick | recording | recorded only |
| `gap` **[agents]** | a span the record doesn't cover, its first and last tick as fields, and a closed reason (below) | the tick it is written in | — | recorded only |
| `tick_end` **[agents]** | the end of one tick's entries; always last in its tick | its tick | — | recorded only |
| `readout` **[later]** | Maxim's per-agent state projection (§6); reserved and refused until then | the step's tick | recording | recorded only |

<!-- contract: mind_record.gaps: dropped stopped torn rewound purged -->
- **Gap reasons:** `dropped` (a tick's batch was dropped from a full queue), `stopped` (the writer stopped for this
  agent after an error), `torn` (a crash's torn final tick, trimmed), `rewound` (a worker restarted from an earlier
  home; the gap names the home's snapshot tick, and views show that span's write pointers as lost), and `purged` (a
  pointer whose audit entry O26 removed).

The record is on or off for a whole segment, which the log header says (§8); there is no switching it mid-segment.

**Excluded by name:**
- the host-only body frame (world truth at the site);
- the continuation's held reply and its agent-owned body;
- prompts and raw model text;
- anything decoded from a refused frame;
- the gateway's outcome detail;
- paths, exception text, process ids, the host environment.

Failures are shown only by their closed reasons (`inference_placement.md` §2.6; `npcs_and_sem.md` §6.6). Every string
field in the schema is a registered closed vocabulary, an authored id, or a digest (§9 tests it).

**A stimulus is not a percept.** The worker clamps a delivered value, adds its noise, and Maxim transduces it
(`sem_stimuli.md` §0, §4.4; `npcs_and_sem.md` §3.4). A view labels the channel "delivered", never "perceived".

**Four channels, labelled apart:**
- **input:** what the world delivered;
- **host verdict and bookkeeping:** refusals, the receipts in a delivery, and the thought header (the host's
  scheduler, cap and latency model, which a slow GPU or the dial moves, not the NPC);
- **recording:** what the agent computed or emitted (write pointers, the readout);
- **report:** what the agent says about itself (its speech, read from the log). A view never presents a report as a
  recording.

Memory provenance is the producer's stamp, so it is host ground truth, not the agent's inference (Maxim
`reviews/grounding_gl3/bio-faithful.md:182-184`). Self-reports can misdescribe what produced them:
- People's accounts of why they acted were no more accurate than outsiders' guesses from the stimulus alone (Nisbett
  & Wilson 1977, *Psychological Review* 84; Ericsson & Simon 1980 is the standing critique).
- With GPT-3.5 and Claude 1.0, chain-of-thought explanations left out the biasing features that drove the answers,
  which cost up to 36% accuracy across 13 BIG-Bench Hard tasks (Turpin et al. 2023, NeurIPS).

So where a report and a recording disagree, a view shows the disagreement.

**When a report has read the recording.** Maxim's agent-callable introspection tools can read the same state
(`embodied_runtime/agentic_runtime.py:757-759`, `explain` and others). Routing cognition tools as follow-ups is
proposed, not adopted (`npcs_and_sem.md` §6.1). If it is adopted, the host header gains a field naming which tools
ran in a cycle (§8), and a report from that cycle is marked tool-informed. Until then a view says it can't tell.

**From a stranger's save,** views label every entry the table marks "recorded only" unverifiable, because nothing
re-derives it.

## 3. The format, the lane, and failure

- **The format.** It follows the intent log's pattern (`sim_core.md` §14):
  - c14n-1 lines after a header record;
  - a declared `Format`, held by others, so it migrates or refuses;
  - a gate-registry row and golden fixtures.

  `simcore.core.schema` refuses tick-named fields today, as it will for the intent log. The amendment is one shared
  dependency (§8).
- **One record per agent per log segment.** The header carries:
  - the log root id;
  - its own segment and its parent's;
  - the scene digest;
  - the registry and bindings digests;
  - the version.

  A load opens a child record at the save's header snapshot, the response cache's rule (`inference_placement.md`
  §4.2). A worker restart opens a segment too (`npcs_and_sem.md` §6.6).
- **The lane.** Each tick, the simulation lane builds one frozen batch per agent and puts it on a bounded queue, so a
  tick is queued or dropped whole. The batch holds that tick's entries in order: kind in the table's order, `tick_end`
  last, and within a kind §9 of `npcs_and_sem.md`'s canonical order. A refusal's sequence is the intent's own. The
  simulation lane never blocks and never does IO. Building a batch can't raise: entries hold values the codec already
  bounded, and validation runs on the record's own thread, which the host owns, separate from the world log's flush.
- **Drops are counted where they happen.** When a batch is dropped, the simulation lane records the first and last
  dropped tick and hands that span to the next batch it enqueues, as a dropped gap.
- **Failure never stops the world.** A write error, or a value that fails validation anyway, stops recording for that
  agent alone and writes a stopped gap if it can. It raises a typed host status and a meter, never a swallow.
  The owner ruled this way (NI4).
- **Bounds.** Each field's bound equals the codec's bound for the value it holds, and a test asserts it.
- **Saves.** A save never waits on the record. The record's thread closes the save's copy of each record
  asynchronously, and the save's header records the tick to which each record is complete (§8, save v1). A view reads
  a saved record only up to that tick, and up to the last tick complete in both the record and the world log. The
  reader trims a torn final tick as a torn gap and refuses any other corruption.
- **Size.** The rate is set by deliveries and refusals. The meter is bytes per agent per world minute, at the 20-NPC
  load `npcs_and_sem.md` §6.6's cost estimate uses. The reader's budgets are bytes per line and values per delivery,
  derived from the codec's size budgets, plus bytes per segment. All three are contract and measured at the build
  step.

## 4. Who reads it, and where the code lives

- **The writer** lives in `simcore.host`, which owns the barrier and saves. Truncation for saves lives in its module.
- **The reader** is one Python gate module in `simcore.host`. It has a gate-registry row and an input-gate entry, and
  it is the strictest class of input (`boundaries.md` §5.3, §5.4).
- **The import rule.** Only the view's entry point imports the reader; an import contract refuses every other module,
  replay and the restore path included. The replay comparison (§9) is a test under `tests/`, outside the shipped
  path. So replay never reads a record.
- **The writing scan:** no function outside the writer's module opens a record for writing.
- **Engine and game.** The record, its lane and its gate are engine. The audiences, the fiction and any player view
  are the game's (§5, §7).

## 5. Who may see what: the information rules this feature needs

- **What exists today.** One rule already governs what a player learns of an NPC: the thinking NPC's pause, shown
  diegetically through a host status channel (`npcs_and_sem.md` §5.4). A player view joins that rule.
- **Stimuli reveal more than the client sees, from the first real NPC.** The client's snapshot carries a few channels
  at display quantization (`client_rendering.md` §4.2), and body-site tissue values never reach it. So a player view
  needs its rule at Phase 4. The owner ruled that the deep view is earned in the fiction, as a diegetic tool with
  costs; outside it, players see behaviour only (NI5).
- **The tiers bind display, not confidentiality.** The developer, player and guest views filter what a view shows.
  The file holds everything the record holds.
- **The record leaves the host's machine** only in a save or bug report the host chooses (§8). A guest's client
  receives only a slice the server cuts. A save handed to another person drops other speakers' words unless they
  consented (NI6). It matters because a save carries the log's speech and the audit record's guest text, which
  §7's views display. O54 governs release to a remote inference class, and nothing yet governs a save given to a
  person.
- **Host data never enters**, by §2's closed schema. Maxim's stock surfaces do carry host data:
  - `energy_status`'s wall windows (`tools/introspection.py:415, 437`);
  - memory timestamps (`:745`);
  - the console envelope's epoch `ts` (`console/server.py:1872`).

  None of them is a source.
- **A player who acts on what they saw** files an ordinary logged intent, and world replay holds.

## 6. The question for Maxim: a typed, per-agent projection of what a step already computes

**Where it is aimed.** The step that would carry the projection is Overdrive's proposal, OD-EA's `StepOutput`
(`docs/maxim_upstream/embeddable_agent_DRAFT.md`). Maxim has no agent `step` that returns intents. On Maxim's side,
the embedder surface is `api.on()`, which the EVENT seam keeps for embedders (`deferred/reachy_app_maxim_seams.md`,
decision 4). That surface has four coarse events, two of them unwired (`:100`).

The EVENT seam's own decisions are right for the console's browser bridge:
- the stream rides `sim_log`;
- `kind` is open;
- `ts` is epoch time.

They are the reason `sim_log` can't serve this host. They are not the decision to change.

**What exists.** Maxim emits a good deal per agent:
- prediction error (`sim_nac`, `runtime/tool_dispatch.py:197`);
- the decision variables behind a choice (`NAc_RECOMMEND`, `decisions/nac.py:355-380`);
- drives, gates, reflexes and deliberation salience (`simulation/sim_logger.py`);
- a per-session bio log (`simulation/bio_telemetry.py`).

Silent: `SalienceMap`, `AttentionNetwork`, `ValenceSignal`, `EnergyBudget`, `OscillatorNetwork` and
`ProvenanceCollector`.

**Why `sim_log` can't serve an embedded, deterministic host.** Each item was read at `b90800e`:
- **Timing is wall time.**
  - NAc's tick is wall-based (`nac.py:361`).
  - The SENSOR gate samples on `time.time()` (`sim_logger.py:1702-1709`).
  - So what is recorded depends on latency.
- **Values compute on wall time.**
  - Salience is fed a wall `now` (`attention/salience_map.py:222-227`).
  - Energy recharge integrates wall time (`energy/signal.py:111`).
  - Retention reads wall age (`memory/strategies.py:199`).
  - Valence carries a wall stamp (`decisions/valence_signal.py:69`).
- **Observing changes the agent.**
  - Turning sim logging on sets `_sim_active`, which adds "You are in a controlled simulation for testing and
    evaluation…" to the prompt (`agents/prompt_builder.py:83-90, 217-222`).
  - `Observer`'s recall touches what it reads (§1).
  - `explain` hands provenance back to the agent.
- **The sink is process-global** (`sim_logger.py:658`), and the SENSOR gate is keyed without the agent. That matters
  for multi-agent processes, Maxim's own simulations included. It does not matter for Overdrive's one-agent workers
  (O13).

**The question:** can OD-EA's `StepOutput` carry, beside its intents, an optional, frozen, versioned projection of
the decision variables the step already computes? It would be:
- **Per agent.**
- **Clock-free in value as well as stamp.** That depends on Maxim's world-clock plan (`docs/plans/world_clock_a_pre.md`)
  and Overdrive's draft (`docs/maxim_upstream/world_clock_release_DRAFT.md`). Until then, comparing `readout` entries
  across reruns means nothing.
- **Typed and bounded.**
- **Observation-neutral.** With the projection on and off, prompts are byte-identical and stores are identical,
  `access_count` and `accessed_at` included. That test needs OD-EA's proposed state digest (OD-EA5, OD-EA6), which
  must cover those touch fields. Maxim has none yet.

Which values it holds, and how they map to Maxim's objects, is Maxim's design.

**It is an instrument, not a percept.** The agent never receives the projection, never reads it, and never learns it
is observed. So it can't be built by reusing `Observer`, `ProvenanceCollector` or the sim-logging switch.

**On Overdrive's side** it is a field of the codec's step output (`npcs_and_sem.md` §6.6; `sem_stimuli.md` §5; the
contents list in `boundaries.md` §7.1). It needs a version bump, a gate row and golden rejection frames, and it gets
its own line on §6.6's barrier budget.

**Also searched** (B22), with nothing found that plans a per-agent, clock-free projection:
- `maxim_ui.md` Phase 5;
- `deferred/maxim_console.md`'s "live observe";
- `deferred/decision_provenance.md` (revives on a 1.4 rung);
- `archive/introspection_api_plan.md` Phase 5;
- `simulation/tools.py::InspectAUTTool`;
- `overdrive_refactor_candidates.md` §A4;
- the embeddable draft v7.

**Consumers:**
- **pulse,** whose stream is untyped, wall-stamped and single-agent (`console/server.py:1272`).
- **This record.**
- **Maxim's open F1** (`deferred/annotation_context_and_provenance.md:26`): whether its LLM "just copies whatever tool
  strings you print as rewarding". Game evidence bears on F1 directly only once `readout` carries the step's credit
  values beside the LLM's annotation. Evidence sent upstream comes from single-player runs, or with the speakers'
  consent (O18, O54).

## 7. The views

- **First: an offline explorer [agents].** It reads a record and the world log after a session, as Dwarf Fortress's
  Legends Viewer reads exported history outside the game. It has three parts:
  - a per-NPC inspector;
  - a timeline scrubber on the world tick;
  - a cause behind every line.

  A receipt joins its intent by pid once Maxim's G17 gives one. Until then the join is by delivery tick and kind, and
  the view says so. The two owners of the receipt key disagree (`sem_stimuli.md` §6.2's pid; `boundaries.md` §6.1's
  `(actor_id, seq)`), which §8 lists for them to settle. A `write_ref` resolves to "not readable" until OD-A15 lands
  with a gated reader for the audit record (§8).
- **Which UI.** Under this contract a view runs the Python gate in a child process and reads its output, with no
  network listener. That fits Overdrive's own viewer in Godot.
  - **The gate's output** is a declared `Format` owned here. Its fields are stated at the build step that builds the
    viewer.
  - **A browser view,** pulse's kit or a static page, is out of contract until a reviewed design gives it a transport.
    Browsers always send `Origin`, and `boundaries.md` §5.3's handshake refuses it. A page that parsed an exported
    file would be a second, ungated reader. Pulse's own rule also puts capability in pymaxim first (pulse
    `AGENTS.md:44-47`).
- **Transport.** A view opens a file the user chose. Any listener that serves record data follows
  `boundaries.md` §5.3's handshake or is reviewed as its own design. That includes Maxim's console, whose
  trusted-origin rule differs. The world server stays closed to browsers.
- **Everything is drawn as plain text.** A view shows log speech and, later, audit-record text, all as plain text:
  - a Godot `Label`, or `RichTextLabel` with BBCode off (`npcs_and_sem.md` §5.2);
  - `textContent` on a page;
  - C0, C1 and bidi controls escaped in a terminal.

  The host's text gates pass markup (`player_text` keeps `[img]…[/img]` and `<img …>`, verified in both rounds), so
  each view gets a planted-markup test.
- **Names and tiers.**
  - A developer or science view shows Maxim's own name for each quantity, with its tier from Maxim's
    `bio_faithful_roadmap.md` (EARN, ANALOG or OPEN).
  - A player view uses in-fiction names, and never a neuroscience term the value doesn't earn. The roadmap lists a
    dopamine-like broadcast as OPEN.
  - No view draws a glow that no value drives, and the never-colour-alone rule applies.
  - The evidence: brain images barely change how convincing an explanation seems (Michael et al. 2013, *Psychonomic
    Bulletin & Review* 20, a meta-analysis; Farah & Hook 2013 is a review). Logically irrelevant neuroscience text made
    bad explanations more satisfying to non-experts (Weisberg et al. 2008, *J. Cogn. Neurosci.* 20).
- **Later: a live in-game view [Phase 4]**, through a new host-to-client message with a server-cut slice
  (`client_rendering.md` §4.1), under §5's rules. A purge can't recall what was already shown, which is a known limit
  beside O26's replay boundary.

## 8. What this changes elsewhere

Each item is a proposed edit to its owner. The build step that needs it makes the edit, or the owner rules. None is
made here.
- `boundaries.md` §6.3, the log header: whether the record is on for the segment. It is metadata the `Simulation`
  never reads, never refused on and never digested, like dilation by cause.
- `boundaries.md` §5.3, the gate table: the record joins "saves, intent logs, bug reports".
- **The bug-report exporter:** it may carry records. The record holds no text, so it adds nothing for the exporter to
  drop.
- **Save v1** (`roadmap.md` Phase 4; `boundaries.md` §7.1): a save carries the records, with each one's
  complete-to tick in its header.
- `simcore.core.schema` and `tile_and_client.md` §3.2: the tick-field rule, shared with the intent log.
- `npcs_and_sem.md` §6.6, `sem_stimuli.md` §5 and `boundaries.md` §7.1's contents list: the step output's `readout`
  field [later].
- `npcs_and_sem.md` §6.6's continuation header: a field naming the cognition tools that ran in a cycle, if follow-ups
  are adopted.
- **`boundaries.md` §6.1, the audit record (OD-A15):**
  - entries keyed by (log segment, settle tick, index in the host's canonical write order), with a join test after a
    save and a load;
  - a gated reader for strangers' saves;
  - a ruling on whether the live audit record is one of O26's agent stores.
- **The receipt key:** `sem_stimuli.md` §6.2 (pid, kind) and `boundaries.md` §6.1 (`(actor_id, seq)`) disagree.
- `npcs_and_sem.md` §5.2: its "receipt carries the spoken prefix" sentences predate `sem_stimuli.md` §6.2.
- **`sem_stimuli.md` §5's bound lane:** it digests a tick's receipts, but stage-1 receipts aren't derivable from the
  log. The same hole §2's replay column avoids.
- **B5:** a row for the record (its copy cost and the world log's write time with it on and off) **[lanes]**.
- `pyproject.toml`: the import contract (§4).
- **NI6's handover rule:** the world log's speech and the audit record's guest text, at their owners, filed as an `O`
  decision after step 4.

## 9. When, and the tests

- **Nothing to inspect yet.** Phase 4's first real NPC is after mid-2027 at the earliest (`roadmap.md`), and O10 bars
  a developer mode with real Maxim before tier A.
- **[agents] tests**, if the owner adds §1–§4 to `phase1/agents`' checklist. Each one is proved by breaking what it
  guards.
  - **On/off with an echo double.** The double folds every input it receives (deliveries, receipts, resumes and gated
    writes) into its home. Its home digest is the c14n-1 hash of that home, and this design owns it, for the double.
    A plant that feeds back a value differing from the true delivery turns the test red, and so does a restore path
    that reads the record. The run goes through a save, a load and a continue.
  - **A record thread that never drains.** The consumer is blocked on an event. The simulation lane still completes N
    ticks; `dropped` gaps and the typed status appear; the world and home digests are unchanged. No wall time is
    measured. The timing bar is B5's **[lanes]**.
  - **Reproducibility.** Two record-on runs with a queue that can't overflow, including runs under different hash
    seeds, give byte-identical records. Reply release is varied in two fixed orders at host hooks, after
    `sem_stimuli.md` §4.1's overlap gate, so a planted arrival stamp goes red.
  - **Replay against the record** (a test under `tests/`). Per tick, the recorded delivery values equal replay's bound
    lane. Stage-1 receipts are checked for consistency with the same tick's `refusal` entries, and that check is
    labelled as consistency, not re-derivation.
  - **Schema.** Every string field is a registered vocabulary, an authored id or a digest. Adding a free `str` field
    turns the test red. Planted paths, exception text and process ids are refused.
  - **Bounds.** Record bounds equal codec bounds. An oversized planted value becomes a `stopped` gap for that agent,
    and the world digest is unchanged.
  - **The rest:** torn-tick trimming, segment parent links, complete-to ticks in saves, and planted markup in every
    view.
- **Deferred mechanism findings,** as round 2's reviewers deferred them: the stamp-assertion and arrival-order legs
  (Determinism D2-S6) and the plant details (D2-N2) go to `phase1/agents`' checklist, and the stalled-writer timing to
  `phase1/lanes`.
- **[Phase 4]:** the real record, the rerun comparison, the projection-off check against real Maxim, and the in-game
  view under §5.
- **Upstream, after step 4 merges (O79).** The §6 question is drafted in `docs/maxim_upstream/` (its one future owner)
  and gets an `OD-` id and a Phase 3 row. So do the two pushbacks:
  - `_sim_active` putting observation into the prompt;
  - `Observer`'s "no mutations" docstring, which its code contradicts.

  The wall-time facts in §6 are evidence for Maxim's world-clock plan, not a new pushback. A lesson records that in
  Maxim, observation is coupled to cognition. The joint plan (PR #81, unmerged) gets the question as a link both ways.

## 10. Rulings

The owner's rulings on this design's questions are `reviews/npc_inspector/rulings.md` (NI1 to NI9, 2026-11-27).
