# DRAFT for Maxim: refining SEM for worlds where effects arrive later, additive first, one break at most

**Status:** a proposal drafted in Maxim Overdrive on 2026-11-16, for Maxim's own process: an issue, this plan, a
three-lens plan review, a four-lens design review for each experiment it names, and a pre-registration per
experiment. Nothing is built, run or claimed. It moves to Maxim's `docs/plans/` if Maxim accepts it.

- **The owner's decision (2026-11-16):** Overdrive is a vehicle for refining Maxim's SEM, including types Maxim marks
  `SHAPE-FROZEN at 1.0 (CC3)`, as long as changes stay bio-faithful and go through Maxim's process. SEM refinement is a
  priority of the foundations work Overdrive runs in parallel with Maxim.
- **The rule this plan follows:** take every additive path first. Batch only what truly cannot be additive into
  **one** breaking-change plan, and only once Overdrive's use shows the additive version is not enough.
- **Prerequisite:** the world-clock release (`world_clock_release_DRAFT.md`, tier A). Several items below are
  meaningless while SEM timestamps are host wall time.
- **Maxim tree read:** `main` at `4b773ef8` (2026-11-16).

## 1. The major-version question, honestly

- **What Maxim's rules say.** CC3 (Maxim `CLAUDE.md`): every frozen dataclass that persists or crosses a wire declares
  either an `extra` escape hatch or a `SHAPE-FROZEN at 1.0 (CC3)` marker. On the marked types: "Adding any new field
  post-1.0 is a major-version-bump change" (`embodiment/sem.py`, e.g. `CouplingSpec` `:146-160`).
- **Which SEM types are which** (verified on `main`):

  | Type | Path | Where |
  |---|---|---|
  | `SensorReading` | `extra` escape hatch | `embodiment/sem.py:39-65` |
  | `ModulatorResult` | **none declared**: one-line docstring, but it has a free `metadata: dict` | `:69-79` |
  | `AffordanceSchema` | `SHAPE-FROZEN at 1.0` | `:82-125` |
  | `CouplingSpec`, `ModulationSpec`, `HomeostaticDriveSpec`, `EntropicDriveSpec` | `SHAPE-FROZEN at 1.0` | `:146-244` |
  | `Modulator` | a `Protocol`, so a new parameter breaks implementers | `:785-811` |

  `ModulatorResult` crosses the tool boundary and has no CC3 declaration. That is a CC3 gap on its own (Overdrive
  `world_v2.md` P6 asked for the marker); this plan's first PR closes it by declaring `metadata` as its escape hatch.
- **Precedent for breaking in a patch.** 1.3.3 shipped "Breaking in places, a patch release by owner decision
  (2026-10-23)" (`roadmap_1_3_x.md:851-852`). So Maxim's owner can choose either way, but CC3's text says major.
- **The cost of a 2.0 to other users.** Released pulse pins `pymaxim>=1.3.3,<2.0` (`outstanding.md` M79), so a 2.0
  forces a pulse release before pulse can follow. Embodiment YAMLs on Reachy parse drive specs: a new field with a
  default doesn't break them, but **changing what an existing field means** (for example the units of `drift_rate`)
  breaks them silently, which is worse than a loud break.
- **Recommendation.** Ship every item below additively in 1.x. Open the breaking batch (§3) only if Overdrive's use
  of the additive versions shows a concrete failure, and then do it once, as SEM 2, with pulse told in advance.

## 2. The items

Each row says what it is, why (Overdrive lessons from `docs/lessons_maxim_in_games.md`, review findings, research),
whether it can be additive, its bio-faithful basis, and what earns it. Every new mechanism enters `[engineering]`.

### S1. A stated time base for drive drift

- **What:** `drift_rate` is documented "per second" (`sem.py:205`, `:240`) with no clock named, so today it means
  wall seconds (`body.py:294-295`).
- **Why:** lesson 11; Overdrive Bio-1 (paused NPCs get hungry).
- **Path: additive.** #1361 S4 already makes drift happen "ONLY through `Embodiment.advance(dt)` on the experience
  clock" (owner answer Q4). This item only states it in the specs' docstrings and adds a test that `drift_rate` is
  per experience second. No field or unit changes, so no YAML author is surprised.
- **Bio basis:** metabolism runs on the body's own time, which in a world is world time.

### S2. `SensorReading.timestamp` is the body clock, never a percept

- **What:** `timestamp: float` is required and unitless (`sem.py:64`); it is stamped with the wall epoch
  (`embodiment/spec.py:837`).
- **Why:** lessons 5 and 11; the time research (`docs/design/research/time/maxim_time_audit.md` §5.2): a body has no
  timestamp on its percepts, only "now", order and a coarse sense of recency.
- **Path: additive.** Stamp it from the injected `Clock` (tier A), and state in the docstring that it is machinery
  for ordering and credit, never rendered verbatim into a prompt. A prompt lint checks the second half.
- **Bio basis:** perception carries order and recency, not clock readings.

### S3. Propose and settle: credit for effects that arrive after the call

- **What:** today a tool call's result is judged inside the call. `ModulatorAffordanceTool`
  (`embodiment/tool_bridge.py:394`) trains the cerebellum on sensors read in the same call (`:864-892`,
  `observe_from_action(..., actual=entity_state)`), and `runtime/tool_dispatch.py:370-375` books a mechanical success
  with no self-report as POSITIVE.
- **Why:** lesson 6; boundaries review BF-1 and Architecture B1 (Overdrive `docs/design/reviews/boundaries/`): in a
  world where actions are queued for the next tick, every action looks like it succeeded and changed nothing. P3 and
  item 16 in Overdrive's list.
- **Correction to Overdrive's earlier wording:** "the cerebellum honours `neutral`" was the wrong ask. Valence is not
  an input to the cerebellum at all; it trains on the in-call sensor state. NAc already honours `neutral`: a neutral
  link "falls into NEITHER" outcome list (`tool_dispatch.py:356-364`). The real gap is **when** the cerebellum
  observes.
- **Path: additive.**
  - A tool whose effect is deferred returns `success=True`, `outcome_valence="neutral"` and a `settles: <receipt id>`
    key in `ModulatorResult.metadata`.
  - A new frozen type, `ModulatorReceipt` (receipt id, outcome kind, measured sensor deltas, the world time it
    settled), is delivered later through a new `settle()` path on the bridge.
  - The bridge skips the in-call cerebellum observation for a deferred result, and observes and credits at settle.
- **Breaking alternative (batched only if needed):** a `pending` field on `ModulatorResult`.
- **Bio basis:** the cerebellum learns from the consequence when it arrives (its climbing-fibre error signal follows
  the movement), not from a reading taken at the moment of the command.
- **Earned by:** the hybrid line's H2 latency sweep (`hybrid_1_5_line_DRAFT.md`); until then `[engineering]`.

### S4. A stale refusal is context, not credit

- **What:** any `success=False` is NEGATIVE (`tool_dispatch.py:370-371`), whatever the reason.
- **Why:** lessons 7 and 9; Overdrive P2 (a call-error kind in the executor) and P7 (refusal metadata for the audit log
  and the LLM's carryover only, never for learning). A thought made stale by deliberation latency, or a malformed
  argument, teaches the agent that the tool is bad.
- **Path: additive.** A refusal-kind key in `ModulatorResult.metadata` (`call_error`, `stale`, `refused_by_world`),
  read by `tool_dispatch` to skip learning for the first two and to carry them into the next thought's context.
- **Bio basis:** an intention abandoned because the moment passed is not a punished action.

### S5. Declared affordance direction: done to, or done by

- **What:** Maxim's actor tool reads every scene affordance as something the entity does to a target; a world's
  structure affordances (`strike`, `ignite` on a crate) are done **to** it.
- **Why:** lesson 8; Overdrive `world_v2.md` P1 (PR 1's item 11).
- **Path: additive first.** An optional attribute on the modulator (`affordance_directions`, read with `getattr`, default
  "by"), since `Modulator` is a `Protocol`. **Breaking alternative:** an `acts_on` field on `AffordanceSchema`, which
  is `SHAPE-FROZEN` (`sem.py:107-110`). Batch it only if the attribute proves too loose.
- **Bio basis:** affordances (Gibson) are relations between an actor and an object, so the direction is part of the
  affordance.

### S6. The acting entity reaches `execute`

- **What:** `Modulator.execute(self, affordance: str, params: dict[str, Any]) -> ModulatorResult` (`sem.py:809`) has no
  actor, so a crate entity shared by two NPCs produces results nobody can attribute.
- **Why:** boundaries review BF-6.
- **Path: additive.** Maxim injects an `actor` key into `params`, the way it already injects `target`. Modulators that
  refuse unknown keys (Overdrive's does) add it to their accepted Maxim keys. **Breaking alternative:** an `actor`
  parameter on the protocol.
- **Bio basis:** efference copy: the body knows which actions are its own.

### S7. Deliberation couples to fatigue

- **What:** thinking takes world time and builds cognitive fatigue, which slows and degrades later thinking until rest
  recovers it.
- **Correction to Overdrive's earlier wording:** `modulated_by` (`ModulationSpec`) exists only on
  `HomeostaticDriveSpec` (`sem.py:209`). Fatigue is entropic, and `EntropicDriveSpec` has `coupled_to: CouplingSpec`
  (`sem.py:244`): "How one drive's state modulates another drive's drift rate … hunger drifts 2x faster when stamina
  drops below 0.4". Both are parsed from YAML (`embodiment/spec.py:278-313`) and **never applied**: "Ships as 1.0
  interface — implementation deferred post-cradle".
- **Path: additive.** Implement the deferred `coupled_to` evaluator, and expose a body sensor that falls while the
  agent deliberates (a cognitive reserve). Fatigue's existing `coupled_to` then makes it drift faster while the reserve
  is low. No field changes.
- **Not this:** charging thoughts to Maxim's `LLMEnergyTracker` (`energy/llm_tracker.py`), which counts tokens and wall
  latency. That is the machine's cost, and an NPC would tire faster on a slower GPU.
- **Bio basis:** effortful thought adds only a few percent to the brain's energy use, so it should not drive hunger;
  sustained cognitive control does build fatigue (prefrontal glutamate after hours of hard work, Wiehler et al. 2022,
  **to verify before it enters `data/`**).
- **Earned by:** T2 below, where fatigue is part of the state that modulates latency.

### S8. Percepts and instruments are different channels

- **What:** today a region sensor reports, for example, a crate's interior maximum temperature to any agent anywhere.
- **Why:** lessons 4 and 5; boundaries review BF-7 (a proposed boundary B-13): percepts are reductions of physical
  channels at the perceiver; anything else is an instrument the agent must look at.
- **Path: additive.** Ride on Maxim's existing `modality:` sensor declarations (1.1.4 PR 2, "`modality:` sensor
  declarations + the world channel"): a declared kind of `percept` or `instrument`, carried in `SensorReading.extra`.
  Prompts render instruments only when the agent is using one. **Unverified:** whether `modality:` can carry this
  without a schema change; the plan review checks.
- **Bio basis:** the receptor-first rule (Overdrive's senses research).

### S9. A versioned SEM vocabulary

- **What:** a `SEM_PROTOCOL_VERSION` constant with a written rule for what is minor and what is major (Overdrive
  `world_v2.md` P6). None exists today (`grep SEM_PROTOCOL_VERSION` on `main`: no match).
- **Path: additive.**
- **Why:** lesson 10: names are identities; a world needs to know which vocabulary an agent learned under.

### S10. Smaller items carried from Overdrive's list (not yet verified against `main`)

- `world_set_axis` for sub-sensors such as `arms.thermal` (P4).
- `FailureMode.last_fired` on world time (P5); joins tier A.

## 3. The breaking batch, if it is ever opened

Only these cannot be additive. Each has an additive version above, used first.

| Change | Type | Instead, first |
|---|---|---|
| `acts_on` on `AffordanceSchema` | SHAPE-FROZEN field | S5's modulator attribute |
| `actor` on `Modulator.execute` | Protocol signature | S6's injected key |
| `pending` on `ModulatorResult` | field (no CC3 declaration yet) | S3's metadata key and `ModulatorReceipt` |
| Renaming `drift_rate` to say its units | SHAPE-FROZEN field, meaning change | S1's docstring and test |

## 4. Experiments that earn the behavioural items

From Overdrive's skeptic brief (`docs/design/research/time/skeptic.md` §5). Both run as Maxim cradles, not game runs,
each with its own pre-registration and four-lens design review.

- **T1: does perceived time carry behavioural weight?** The exact SCN phase, against an oscillator entrained by world
  light, against that oscillator with the light removed, on a food-anticipation task. Prediction: the oscillator arm
  anticipates as well as the exact arm; in the dark it drifts by about (period − 24 h) a day and re-entrains when light
  returns. Kill criterion: if it cannot match the exact arm, the exact phase stays as a marked stand-in.
- **T2: does state-dependent timing change what is learned?** Fixed latency, against latency modulated by fatigue,
  arousal and circadian phase, against a shuffled control with the same latencies but no link to state, on a timed
  hazard with rest available. Prediction: only the state-modulated arm learns to do dangerous things when alert. Kill
  criterion: if it does not beat the shuffled control by a pre-registered effect size, state dependence is game feel
  only.

## 5. Order

1. Tier A, the world-clock release (prerequisite).
2. The CC3 declaration on `ModulatorResult`, S1, S2, S9 (small, additive, no behaviour change).
3. S3, S4, S6 (the propose/settle contract), with Overdrive running them on its tile.
4. S5, S7, S8, each with its experiment where it claims behaviour.
5. §3 only on evidence.

## 6. Open for Maxim's review

- Whether `ModulatorReceipt` belongs in `embodiment/sem.py` or beside the tool bridge.
- Whether the refusal kinds of S4 extend D53's self-report vocabulary or sit beside it.
- Whether S7's cognitive reserve is a body sensor (in the SEM tree) or an internal state of the thought gate.
