# NPC inspector: the mind record and the views over it (design, v1 draft, 2026-11-27)

**Status:** DRAFT v1, not reviewed. The owner asked on 2026-11-27 for a way for players (and us) to explore what an
NPC is internally experiencing, possibly through Maxim-pulse. This note holds the contract that feature needs on
Overdrive's side, the one thing it asks of Maxim, and the questions only the owner can answer. Nothing here is
decided. It changes the architecture (a new host output, a new purge reach, an upstream ask), so it gets a design
review with the Bio-faithful lens before any code (CLAUDE.md).

**What it owns** (one owner per contract, B36):
- the mind record: what it holds, its clock, its versions, who writes it and who may read it (§2, §3);
- the rule that observation never calls into an agent (§1);
- the shape of the upstream ask for a per-agent state readout (§6), until a draft in `docs/maxim_upstream/` takes it.

It owns no codec kind, log record or wire message. Each one it touches is linked to its owner.

**Sources:**
- Overdrive `origin/main` `e6d6a7f`.
- Maxim `main` `b90800e` (2026-11-27), read in a fresh clone.
- Maxim-pulse `main` `a1ba1d4` (2026-11-21), read in a fresh clone.

Line numbers are at those revisions. *Verified* means the author read the line there.

**Tags:**
- **[agents]:** buildable in `phase1/agents` against the scripted test double, if the owner puts it in that step's scope (§8).
- **[Phase 4]:** real NPCs.
- **[later]:** named so the contract leaves room for it, and not built.

## 1. The rule: record what crosses the membrane, never ask the agent

Three facts in the tree decide the shape. Each is *verified*:
- **Agent state has no read path.** Each real agent runs in its own worker (O13). Its codec's kinds are closed per
  direction, and none of them reads or inspects state (`npcs_and_sem.md` §6.6). "Nothing writes agent state from
  anywhere else" (§6.3).
- **Asking an agent what it remembers changes it.** A recall returns a `retrieval` write, applied at `settle`, so
  the testing effect holds (`npcs_and_sem.md` §6.6, "Retrieval strengthening survives a host-called `think`"). An
  inspector that queried memory would strengthen what it showed.
- **Replay never runs the agents.** It reproduces the world, and agent homes are saved as state (`boundaries.md`
  §6.2). Why an NPC chose something needs a tier-2 rerun.

So the inspector's one rule, **[agents]**:
- **The inspector never calls `AgentPort`**, never adds a codec kind, and never runs anything in a worker. It reads
  only values the host already holds because they crossed the membrane in the normal course of a tick.
- **The mind record is an output, never an input.** The `Simulation`, every law, every agent and replay never read
  it. It is not a log input (`boundaries.md` §6.2: an NPC's thought is never one). Writing it must not change any
  world or agent digest. Test: the same scene and intents with the record on and off give bit-identical world
  digests and agent-home digests. A plant that feeds one record value back into a frame goes red.
- **It runs on the world's clock.** Every entry is stamped with the integer tick at which the host saw it, and
  nothing else. No wall time, no epoch and no Maxim `ts` enters it. A planted wall-time field is refused at write.

This is how a networked game records a match for kill-cams and replays. The authoritative server records what
crossed into the simulation, and the view is rebuilt from that recording, so viewing can't change the match.

## 2. What the mind record holds

One record per agent per run, append-only. Every entry carries the actor id, the tick, a kind, and the entry's schema
version. The kinds are:

<!-- contract: mind_record.kinds: percept intent thought write receipt lifecycle state -->
- **Entry kinds:** `percept`, `intent`, `thought`, `write`, `receipt`, `lifecycle` and `state`; the record refuses
  any other.

Where each one comes from:
- **percept** **[agents]**: the frame values the agent's pulls read at its last `step` (`npcs_and_sem.md` §7.3):
  region, receptor, site and value, as the agent received them. It never holds the world's true value under a
  sensor's name. That is the same "sensed, not handed" line the game-evidence draft draws (its condition 3, on
  `phase3/joint-plan`, PR #81).
- **intent** **[agents]**: each intent in `step_output` or a thought's output, with its invocation pid when there is
  one (`boundaries.md` §6.2), and its stage-1 result.
- **thought** **[agents]**: a thought's lifecycle as the host's continuation header sees it: kind, triggering input,
  cycle index, landing ticks, and cancel or failure. Its speech is included, as validated. It never holds prompts or
  raw model text. Those stay where `inference_placement.md` keeps them, and the agent-owned body stays opaque.
- **write** **[agents]**: each gated write the host passes to `settle`: memory writes and `retrieval` writes (the
  trace ids reactivated), with provenance as stamped (`npcs_and_sem.md` §6.6).
- **receipt** **[agents]**: each receipt credited at `settle`, with its outcome and the valence the adapter reported
  (`sem_stimuli.md` §6.2; D53's tiers, `npcs_and_sem.md` §6.1).
- **lifecycle** **[agents]**: the agent's lifecycle records as the host logs them (`npcs_and_sem.md` §6.6), and
  consolidation and sleep calls.
- **state** **[later]**: Maxim's per-agent state readout, once Maxim emits one (§6). Until then the kind is
  reserved and the record refuses it.

**Two channels, labelled apart:**
- A **readout** is a value the substrate produced: percepts, writes, receipts, and the state readout.
- A **self-report** is what the agent says about itself: speech, and any thought text a later version admits.

A view shows each under its own label and never presents a self-report as a readout. LLM chain-of-thought often
leaves out what actually drove an answer. Turpin et al. 2023 (arXiv 2305.04388) measured accuracy drops of up to 36%
from biases the explanations never mentioned. People's reports of their own reasons are no better (Nisbett & Wilson
1977). Where the two channels disagree, that disagreement is shown, not reconciled. *Both cited secondary in this
draft; to verify before review.*

**The format.** The record is versioned, closed-schema strict JSON lines, through `simcore.core.schema` like every
data format. It is gzip-free on disk, so a diff stays readable. It carries a header with the run's log root id and
segment, and the scene digest, so a record is tied to the world log it shadows (`boundaries.md` §6.3). A reader
refuses a version it doesn't know.

**Its size** is measured, not guessed (B5). It holds only values that crossed the membrane already, so its rate is
bounded by the codec's own size budgets (`npcs_and_sem.md` §6.6). The meter is bytes per NPC per world minute, at the
20-NPC load `npcs_and_sem.md` §6.6's cost estimate uses, measured with the double.

## 3. Where it is written, and who reads it

- **The host writes it**, at the barrier, after the tick's parks and before T+1, in canonical order
  (`npcs_and_sem.md` §6.3, §9). It writes beside the world log under the save or run directory, never inside an
  agent home. The home is the agent's own, and the record is the host's observation of it.
- **Nothing in the engine reads it.** The import contracts gain a rule: no module under `simcore.core`, the laws or
  `simcore.adapters` imports the record's writer or reader. The ownership scans gain its writer.
- **A view reads it through a file gate** (`adapters/loaders.py`'s pattern). A mind record from someone else's save is
  untrusted input, like any save. If the gate is in Python, it gets a row in the gate registry and every rejection
  path tested.
- **Saves and bug reports.** A save carries the record with the world log. A bug report drops `thought` speech and
  `write` text by default, as it already drops `speak` text (`boundaries.md` §6.2), keeping lengths and ticks.
- **Guest text.** NPC memories and speech can hold a guest's words (`npcs_and_sem.md` §5.2). The record is a new
  place where guest text lives. The purge path must reach it: a guest's purge redacts the record's spans and leaves
  O26's redaction records. That widens O26's reach list, which is the owner's ruling to make (§9).

## 4. Determinism, replay and cost

- **Determinism.** §1's on/off test is the guard. The record's writer draws no randomness and reads no clock. It
  iterates named collections in sorted-key order, as the log does (`boundaries.md` §6.2).
- **Replay.** Replay reproduces the world, not the agents. So a replayed session's mind record is rebuilt only to
  the extent the world log carries it: intents, speech and receipts. Percepts, writes, the state readout and thought
  lifecycles come from the saved record, never from rerunning Maxim. A view of a replay shows which entries are
  re-derived and which were recorded.
- **Rerun.** A tier-2 rerun (`boundaries.md` §6.3) regenerates a full record. Comparing a rerun's record with the
  original is a diagnostic for where agent behaviour diverged. That makes the record useful to verification as well
  as to players. **[Phase 4]**
- **Cost.** No extra round trip: the record copies values the barrier already decoded. The write cost per tick goes
  on B5's agent-lane meters (`npcs_and_sem.md` §6.3), with its own budget.

## 5. Who may see what: the information rules this feature needs

Every leak rule in the tree runs one way: world, host and presentation data must not reach an NPC's cognition
(*verified*: `fire_solid.md`, `npcs_and_sem.md` §1 and §5.4, `inference_placement.md`). None governs what a player
may learn of an NPC. The feature needs that rule. This section names its parts; the choices are the owner's (§9).

- **Audiences.** There are three, with different contracts:
  - the **developer**: everything in the record, out of character, never in a shipped build's player UI;
  - the **player**: a curated, in-fiction view whose reach is earned or gated by the fiction;
  - a **guest or spectator**: the least, and only after the guest gates (O14, O18).
- **World truth through an NPC's senses.** A percept is the world at the NPC's site. Today the client receives whole
  tiles with no visibility culling, so a player sees nothing new through an NPC. Once line of sight exists
  (`tile_and_client.md`, Phase 4/5), an NPC's percepts reveal what the player can't see. The player view needs a
  rule then: delay, coarsen, or gate by the fiction.
- **Host data never enters the record.** Maxim's stock introspection tools carry host data the designs keep from NPCs.
  `energy_status` exposes wall-clock token windows and `memory_recall` exposes epoch timestamps
  (`reviews/foundations_v1/delta1_trust_boundary.md`, the leak findings). Pulse's event envelope stamps wall time
  (Maxim `simulation/sim_logger.py`, `ts`). None of these is a source for the record.
- **The player acting on what they saw** is an ordinary logged intent. World replay holds whatever the player
  learned.

## 6. The one ask of Maxim: a typed, per-agent state readout

**Why.** The record's readout channel is thin without it. What crosses the membrane today is percepts, actions,
writes and receipts. The state a player would want to explore never leaves the agent: attention, salience, valence,
drives, prediction error, and why one action beat another. In Maxim that state exists but is never emitted:
- `attention/salience_map.py::SalienceMap`;
- `attention/attention_network.py::AttentionNetwork`;
- `decisions/valence_signal.py::ValenceSignal`;
- `energy/signal.py::EnergyBudget`;
- `time/oscillator.py::OscillatorNetwork`;
- `provenance/collector.py::ProvenanceCollector`.

All of these are at `b90800e`, *verified* by a reader; none reaches `sim_log`.

**The ask, as a shape, not a design.** Maxim's `step` returns, beside its intents, an optional, frozen, versioned
readout of state the step already computed. It is not the state digest of the embeddable draft's parity tests
(OD-EA5, OD-EA6), which is a hash; this is a typed summary a person reads:
- **Per agent.** It carries no global or process-wide sink, so two agents in one process can't mix (Maxim's
  `sim_logger` SENSOR rate limit is keyed by entity and sensor, not by agent, `sim_logger.py:1702-1709`).
- **Clock-free.** The host stamps the tick. The readout carries no `time.time()`. NAc's recommendation tick is
  wall-based today (`decisions/nac.py:361`).
- **Read-only to compute.** No recall, no strengthening and no model call. Computing it must leave the agent digest
  unchanged, which Maxim can test with its own state digest.
- **Bounded and typed.** Each field is a declared type with a size bound, and nothing is a free-form dict.

Which fields it holds, and how they map to Maxim's objects, is Maxim's design. This note doesn't choose them. Doing
so would be designing Maxim's cognition from here, which the joint plan's review flagged (BF-B2 in
`reviews/joint_plan/bio_faithful.md`, on `phase3/joint-plan`, PR #81, not yet on `main`).

**An instrument, not a percept.** The readout is a recording electrode, not a sense. The agent never receives it,
never reads it and never learns it is observed. It enters no prompt and no store.

**Searched first** (CLAUDE.md, B22), at Maxim `b90800e`:
- `docs/plans/maxim_ui.md` Phase 5 plans the "full dashboard … see the whole bio-stack live" for pulse, with no date.
- `docs/plans/deferred/maxim_console.md` lists "Live observe / telemetry: the `Observer` + `on()` stream as a real
  panel" as not built.
- `docs/plans/deferred/decision_provenance.md` is deferred since 2026-09-19, with stages 1 and 2 shipped. It revives
  only when a 1.4 rung names the gap, and this ask names no rung.
- `docs/plans/archive/introspection_api_plan.md` Phase 5 (the agent's self-introspection tool) is "not started".
- `simulation/introspection.py::Observer` and `memory/snapshot.py::SessionSnapshot` read state after the fact, and
  neither is served.
- `overdrive_refactor_candidates.md` §A4 is leak closure and says nothing about observing an embedded agent.

- Overdrive's own `docs/maxim_upstream/embeddable_agent_DRAFT.md` (v7) covers stepping, writes and parity, and
  says nothing about observation.

Nothing found plans a per-agent, clock-free readout. So this would be a question to `maxim_ui.md` Phase 5 and the
deferred console's "live observe", which already want the data, and a candidate addition to the embeddable draft,
not a new plan beside them.

**It serves three consumers:**
- **pulse:** its `/ws` payloads are untyped, wall-stamped and single-agent (Maxim `console/server.py:1272`,
  "the console fronts ONE persistent agent");
- **Overdrive:** this record;
- **Maxim's research:** decision provenance's open stages.

That is why it belongs in the joint plan (PR #81's `joint_plan_DRAFT.md`) as a link both ways, not a
game-only request. It is drafted upstream only after step 4 merges, because O79 keeps the upstream lane closed
while step 4 runs.

## 7. The views

- **First: an offline explorer [agents].** It reads a saved mind record and the world log after a session, in the
  pattern of Dwarf Fortress's Legends Viewer, which reads exported history outside the game. It has three parts:
  - a per-NPC inspector;
  - a timeline scrubber on the world tick;
  - a cause behind every line: each memory write links to the percepts and receipts around it, and each intent to
    its receipt by pid (entry kinds: §2).

  Live attach, the browser handshake and determinism don't arise.
- **Which UI.** Two candidates, the owner's choice (§9):
  - **(a) pulse's kit with a file-backed client.** `FacadeProvider` takes any `FacadeClient` (pulse
    `packages/kit/src/facade/context.tsx`), but the interface is 19 methods of a single-agent console. Pulse's own
    rule is that capability lands in pymaxim first, so a file-backed client is a pulse decision.
  - **(b) Overdrive's own viewer**, in Godot or a static page over the record format.
- **Later: a live in-game view [Phase 4].** It needs a new host-to-client message carrying a curated slice of the
  record. That is a wire contract (`client_rendering.md` §4.1) and the §5 rules. It is never a browser attached to
  the world server: the host refuses any `Origin` header by design (`src/simcore/host/server.py`), and a web client
  would be a deliberate protocol change (`architecture.md`).
- **Every glow names its quantity.** A view draws no brain-like decoration that no value drives. A meta-analysis
  found that adding brain images barely changes how convincing an explanation seems (Farah & Hook 2013). Adding
  neuroscience-flavoured words did raise satisfaction with poor explanations (Weisberg et al. 2008). *Secondary;
  to verify.* The client's never-colour-alone rule applies.

## 8. When

- **Nothing to inspect yet.** Real NPCs come after Maxim's embeddable contract. Phase 4's first real NPC is after
  mid-2027 at the earliest (`roadmap.md`), and O10 bars a developer mode with real Maxim before tier A.
- **[agents]:** §1 to §4 can be built and tested against the scripted double in `phase1/agents`, as checklist
  items (`docs/plans/checklists.md`, that step's). That is new scope for that step, the owner's call. The explorer
  over the double's records can follow it.
- **[Phase 4]:** the real record, the rerun comparison, and the in-game view under §5's rules.
- **[later]:** the `state` kind, at Maxim's pace.

## 9. For the owner

1. **The information rules (§5).** What may a player learn of an NPC, and when? Is the deep view earned in the
   fiction? What happens to percepts once line of sight exists?
2. **The audience first:** a developer and science view, a player view, or both? Prior art favours curated causal
   lines for players, with raw data a click deeper.
3. **The ethics framing:** is the view witnessing a life or dissecting one? It is worth deciding early.
4. **O26's reach:** does the mind record join the list a guest's purge reaches (§3)? The author recommends yes.
5. **Scope:** do §1 to §4 enter `phase1/agents`' checklist, or wait for Phase 4?
6. **The explorer's UI:** pulse's kit or Overdrive's own (§7)?
7. **This branch and step 4:** step 4 runs alone (O79), naming only two late branches. Should this note be
   reviewed and merged before step 4, or named as a third late branch? It touches no record file.
