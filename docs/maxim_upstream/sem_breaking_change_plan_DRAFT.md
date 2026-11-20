# DRAFT for Maxim: refining SEM for embedded worlds, additive in 1.x

**Status:** a proposal drafted in Maxim Overdrive on 2026-11-16, revised the same day after a seven-lens review.
The file keeps its name because Overdrive documents link to it, but **its content is no longer a breaking-change
plan**. Read correctly, Maxim's CC3 rule makes every item below additive. It is for Maxim's process as a **plan**
(three-lens plan review, three-lens code review per PR). Items that claim behaviour need an experiment and are
marked. Read against `origin/main` `7084f561`.

- **Overdrive ids:** OD-C1 to OD-C10 (tier C, "SEM additive, after tier A").
- **The authority it cites:** a `DECISIONS.md` entry the first plan PR proposes (`decisions_entry_DRAFT.md`), not a
  decision recorded only in Overdrive.
- **Depends on:** OD-I2 (the CC3 declaration on `ModulatorResult`), and tier A for anything about timestamps.

## 1. The major-version question, read correctly

The first draft quoted `CouplingSpec`'s docstring ("Adding any new field post-1.0 is a major-version-bump change")
and applied it to every SHAPE-FROZEN type. That was wrong.

- **The canonical rule** (`docs/agents/persistence-config.md` §3, path (b)): "adding a *required* field post-1.0 is
  a major-version bump; an optional trailing defaulted field is non-breaking but still review-gated".
- **`AffordanceSchema`'s own docstring:** "All fields have defaults, so additive fields appended at the end stay
  non-breaking."
- **Precedent:** two defaulted fields were added to `AffordanceSchema` after 1.0, both in non-major releases:
  `always_active: bool = False` (#403) and `speech_param: str | None = None` (#1261).
- **Renames** follow Maxim's alias-plus-`DeprecationWarning` practice, kept through 1.4.x and removed in 1.5.0 (the
  `apply_decay=` precedent, Q7). That is not a major.
- **The one change that would be a true break** is a new parameter on `Modulator.execute`, a `Protocol` signature.
  OD-C4 makes it opt-in, so it doesn't break.
- **So no 2.0 is proposed.** If one were ever needed, it would come after 1.4.0, whose number is research-gated
  (`release_gates.json`). 1.3.3's breaking patch was for security changes, which is not a licence to break SEM shapes
  in a patch. Pulse pins `pymaxim[console,reachy,tts]>=1.3.3,<2.0` (pulse `apps/reachy/pyproject.toml`), which none
  of this disturbs.

## 2. The items

Every item enters `[engineering]`. Those that claim behaviour say what would earn them.

### OD-C1. Drive drift states its time base

- **What:** `drift_rate` is documented "per second" (`HomeostaticDriveSpec`, `EntropicDriveSpec`) with no clock
  named, so today it means wall seconds.
- **Path:** #1361 S4 already makes drift happen "ONLY through `Embodiment.advance(dt)` on the experience clock" (Q4).
  This item states that in the specs' docstrings, with a test that drift is per experience second. A rename (for
  example `drift_rate_per_s`) is optional, as an alias with a `DeprecationWarning`.

### OD-C2. `SensorReading.timestamp` is the body's clock, never a percept

- **What:** `timestamp: float` is required and unitless; it is stamped with the wall epoch.
- **Path:** stamped from the injected clock (tier A). The docstring says it is machinery for ordering and credit,
  never rendered verbatim into a prompt. Overdrive's schema test exempts it by name, and a value-level test checks
  what a modulator puts in `metadata`.

### OD-C3. A declared affordance direction: done to, or done by

- **What:** Maxim's actor tool reads every scene affordance as something the entity does. A world's structure
  affordances (`strike` or `ignite` on a crate) are done **to** it.
- **Path:** a trailing defaulted field on `AffordanceSchema`, `acts_on: str = "by"`, under CC3 path (b) and the
  `always_active`/`speech_param` precedent. This replaces the first draft's duck-typed attribute, which Maxim's "push
  invariants into types" rule would refuse.
- **Bio basis:** affordances (Gibson) are relations between an actor and an object.
- **Evidence,** through Maxim's real tools: `actor(entity="crate", affordance="ignite")` is refused (default target
  "player"), `target="crate"` succeeds, `target="wall"` is refused (Overdrive
  `tests/test_act_validation.py::test_maxims_actor_tool_must_name_the_region_as_its_own_target`); through
  `ModulatorAffordanceTool`, no target or "crate" succeed and "wall" or "self" are refused
  (`::test_maxims_affordance_tool_accepts_only_the_region_itself_as_a_target`; both tests run on the locked
  pymaxim release). Argues against `scene_actor_affordances.md` invariant 5 (`OrchestratorActorTool`'s docstring
  rule 2) and the schema default `"target": (str, "player")` (read on `f0b1cea4`), which make every scene affordance
  an act by the entity on a target. A refusal for the wrong direction is OD-A16's
  `wrong_target`. Making a strike the NPC's own affordance with a `target_effect` can't work: that is sensor deltas, so
  it can't run the region's modulator.

### OD-C4. The acting entity reaches `execute`, opt-in

- **What:** `Modulator.execute(affordance, params)` has no actor, so a crate entity shared by two NPCs produces results
  nobody can attribute.
- **Path:** a class attribute a modulator declares, `accepts_actor: bool = False`. The bridge passes `actor=` only to a
  modulator that declares it, through a second optional `Protocol` checked with `isinstance`.
  - The first draft injected an `actor` key into `params`. That would make every strict modulator (Overdrive's
    refuses unknown keys) refuse every call after an upgrade, so it was struck.
  - (`target` is passed as a resolved entity only by `OrchestratorActorTool`; `ModulatorAffordanceTool` fills declared
    YAML defaults.)
- **Bio basis:** efference copy: the body knows which actions are its own.

### OD-C5. A deferred-result marker on `ModulatorResult`

- **What:** the propose/settle amendment (`propose_settle_amendment_DRAFT.md`) needs a result to say "this settles
  later".
- **Path:** after OD-I2 gives `ModulatorResult` its CC3 path (b) marker, add a trailing defaulted field `settles: str |
  None = None` (the receipt id). A typed field instead of a `metadata` key, because metadata keys are invisible to
  learning unless promoted, and a field can't be misspelled.

### OD-C6. Reserved membrane keys

- **What:** the bridge builds its tool output as `{"entity": ..., "affordance": ..., "success": True,
  "entity_state": ..., "active_failures": ..., **result.metadata}`
  (`embodiment/tool_bridge.py::ModulatorAffordanceTool.execute`). So a metadata key named `success` overwrites the
  outcome that the model reads.
- **Path:** document the reserved keys, and have the bridge refuse a metadata key that collides with one, loudly.

### OD-C7. `ModulatorResult` and `SensorReading` must not be mutated

- **What:** both are frozen, but `params`, `metadata` and `extra` are plain dicts, so "frozen" is shallow.
- **Path, additive first:** a documented "must not mutate" rule, and a test that the bridge and dispatch never mutate
  them. Wrapping the dicts read-only (`MappingProxyType`) would break callers that mutate, so it is held as the only
  candidate for a later break, and only if a mutation bug is found.

### OD-C8. Percepts and instruments (shrunk)

- **What Overdrive first asked for:** a declared `percept` or `instrument` kind in `SensorReading.extra`, with prompts
  rendering instruments only while in use. Overdrive's bio-faithful review struck that: an omniscient readout behind a
  usage flag is still omniscient.
- **Corrected:** an instrument is an in-world object with a position, its own physical reduction and a display. The
  agent perceives the display like any other percept, through an existing `modality:` (`embodiment/sensory_streams.py`:
  the channel-to-cluster declaration, `world` or `audio`). Adding percept versus instrument to `modality:` would mix two
  axes, so it isn't proposed.
- **Path:** probably nothing new in Maxim. The plan review confirms that a visual percept's `modality:` carries a
  display reading, and if so this item closes with a documented convention.

### OD-C9. A written rule for the SEM vocabulary's versions

- **What:** `embodiment/sem.py` already has `ENTITY_FORMAT_VERSION: str = "1.1"`. What is missing is a written rule
  for what changes the minor and what the major, for affordance and sensor names as well as the entity format.
- **Path:** document the rule on top of the existing constant. No new constant.
- **Why:** names are identities, so a world needs to know which vocabulary an agent learned under.

### OD-C10. Sub-sensor writes from the world

- **What:** `world_set_axis` for sub-sensors such as `arms.thermal` (Overdrive's earlier P4).
- **Unverified on `7084f561`:** whether `world_set_axis` exists in the shape this needs. The plan review checks
  before this item is filed.

### Moved elsewhere

| Item | Now in |
|---|---|
| `FailureMode.last_fired` on world time | world clock A-post (OD-A8), with #1361 S4 |
| Propose and settle; the cerebellum at settle; refusal kinds; a per-modulator valence default | the `tool_failure_credit.md` amendment (OD-A16) |
| Deliberation coupled to fatigue (now a rising mental-fatigue drive), and the `CouplingSpec` graded-coupling ask | `time_sense_DRAFT.md`, OD-B12 |
| The oscillator's weekly, monthly and annual scales | `time_sense_DRAFT.md`, OD-B13 |

## 3. Order

1. OD-I2 (an issue now).
2. OD-C1, OD-C2, OD-C6, OD-C9: documentation and small checks, no behaviour change.
3. OD-C3, OD-C4, OD-C5: additive fields and the opt-in protocol, landing with the propose/settle amendment.
4. OD-C7, OD-C8, OD-C10: after the plan review settles them.

None of it touches a fenced file except where it meets `tool_bridge`'s pinned `execute` (502 lines): OD-C5 and
OD-C6 go with the propose/settle amendment's extraction, after 1.3.6.

## 4. Open for Maxim's review

- Whether `acts_on`'s values are `by`/`to`, or richer.
- Whether OD-C4's second protocol is preferred over a keyword the bridge passes only when declared.
- Whether OD-C9's rule lives in `sem.py` or in `docs/agents/embodiment.md`.
