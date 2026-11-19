# DRAFT for Maxim: an amendment to `tool_failure_credit.md` (#1200), credit for effects measured later

**Status:** a proposal drafted in Maxim Overdrive on 2026-11-16, as an **amendment to an ACTIVE plan**
(`docs/plans/tool_failure_credit.md`, owner decisions TF1–TF3, `DECISIONS.md` 2026-10-10). It is not a new
mechanism beside it. It goes through the plan's own review, and every edit is sequenced after #1200's stages and 1.3.6.
Nothing is built, run or claimed. Read against `origin/main` `7084f561`.

- **Overdrive id:** OD-A16 (tier A: embedded NPCs can't learn from their actions without it). It folds Overdrive's
  earlier P3, P2/P7, item 16's credit half and the boundaries reviews' BF-1, BF2-3, X-6 and Wire S12.
- **Depends on:** the embeddable agent plan (`settle`), and #1200's stages.

## 1. The problem, on Maxim's code

- **The cerebellum learns from sensors read during the call.** `embodiment/tool_bridge.py::ModulatorAffordanceTool`
  calls `self._cerebellum.observe_from_action(...)` with the entity's state read in the same call. In a world where an
  action takes effect at the next tick, that teaches "this action changes nothing".
- **Valence isn't a cerebellum input.** An earlier Overdrive draft asked for "the cerebellum honours `neutral`". That
  was the wrong ask. NAc already honours D53's `neutral` (`runtime/tool_dispatch.py::LearningSideEffects`: a neutral
  outcome falls into neither list). The gap is **when** the cerebellum observes.
- **Silence means POSITIVE.** "A tool that reports nothing yields the all-default value, which is the historical
  behaviour: mechanical success means POSITIVE" (`tool_dispatch.py`, D53 block). For a world modulator whose effect is
  measured later, that is the bug class D53 was written to fix ("a refused motion booked a full POSITIVE causal
  link"). Overdrive's own modulator would book a strike on a steel door that did nothing as POSITIVE.
- **Failure metadata never reaches dispatch.** On failure the bridge returns `ToolOutput(success=False,
  error=result.error)` and drops `result.metadata`. On success, keys reach `tool_dispatch` only when explicitly
  promoted into `side_effects`, as `outcome_valence` and `measured_drive_transitions` are. So a refusal kind, or a
  "settles later" marker, put in `metadata` is invisible to learning on the shipped path.

## 2. Front gate

| Need | Existing | Use |
|---|---|---|
| "Nothing changed" or "unverified" isn't harm | D53's `outcome_valence` (`neutral`, `negative`), self-reported by the tool | **Rides on it.** No new valence mechanism. |
| Measured drive changes reach credit | `metadata["measured_drive_transitions"]`, promoted by the bridge (the Reachy backend's precedent, `hardware/reachy/motor_backend.py`) | **Rides on it.** |
| Which failures teach | TF2: "only tools that ran earn failure credit"; `book_refusal`, `book_machine_refusal` | **Extends it** with two kinds that ran but must not teach (§3.3). |
| Timing of cerebellar credit | `bio_faithful_roadmap.md`: cerebellum "Timing (climbing-fiber style eligibility windows) \| EARN (candidate)" | **The bio basis** for observing at settle. |

## 3. The amendment

### 3.1 Propose, then settle

- A modulator whose effect is measured later returns `success=True`, `outcome_valence="neutral"` and a receipt id. The
  id goes in a trailing defaulted field, `ModulatorResult.settles` (OD-C5, after OD-I2's CC3 marker). It is promoted
  into `side_effects` the way `outcome_valence` is, so the bridge and dispatch can read it.
- For such a result, the bridge **skips** its in-call cerebellum observation.
- A new frozen type, `ModulatorReceipt`, carries:
  - the receipt id;
  - an outcome kind: `applied`, `refused_by_world`, `stale` or `cancelled`;
  - the measured sensor deltas, restricted to the sensors the affordance declares it affects;
  - `measured_drive_transitions`.
- The embedded agent's `settle(receipts)` delivers it. The cerebellum observes at settle, and NAc credits through the
  same D53 and measured-transition path as a synchronous tool. Each receipt is credited **exactly once**: a test
  asserts once for `applied`, and zero times for `stale` and `cancelled`.
- **Slow effects.** One settle frame is the right horizon for cerebellar reafference, which takes hundreds of
  milliseconds. Consequences that take seconds stay with NAc's temporal window. Restricting the observed sensors to
  the declared ones keeps an ongoing process (a crate already burning) from training the cerebellum on the world's
  drift instead of the action's effect.

### 3.2 A per-modulator valence default

Additive: a modulator may declare `default_outcome_valence = "neutral"` (a class attribute the bridge reads, default
absent, so today's POSITIVE stays the default for every existing tool). World modulators whose effects are measured
from frames declare it. Overdrive's adapter self-reports either way.

### 3.3 Three refusal kinds that ran but don't teach

Extending TF2's ran/not-ran classification:
- **`stale`**: the action was valid when proposed, but the moment passed (the world changed while the agent
  deliberated). It is context for the next thought, never credit.
- **`call_error`**: a malformed argument. A cognitive error, as TF2 already rules for "a hallucinated or inactive tool
  name". It is not a tool failure. The executor produces it, validating the call against the declared
  `AffordanceSchema` (types, unknown keys, finiteness) and exempting keys it adds itself (`OrchestratorActorTool`'s
  `target`). Today a typo is pain twice over (`origin/main` `f0b1cea4`): `Tool.run` calls `_validate_input`, which
  checks only required keys, inside its own `except Exception`, and `INVALID_INPUT` maps to
  `PainType.TOOL_INVALID_INPUT`. The same catch books a modulator's own exception as the tool's failure, so a host bug
  that fails loudly becomes a false lesson. Evidence: Overdrive PR 1's probes (`tests/test_act_validation.py`).
- **`wrong_target`**: a call aimed where the affordance's direction (OD-C3) doesn't allow. A choice error, booked like
  `call_error`, never against the tool.

All three travel as a kind on the failure path that dispatch reads. That needs the bridge's failure return to carry the
kind, the one wire change in this amendment. A test goes through `ModulatorAffordanceTool.execute`, not only
`tool_dispatch`, so the kind is proven to arrive.

## 4. Order

These edits touch functions pinned at 502 lines (`ModulatorAffordanceTool.execute`), 392 (`record_outcome`) and 357
(`execute_and_learn`, #1150's 1.3.6 slice). So:
1. after #1200's stages and 1.3.6;
2. each edit extracts at least as many lines as it touches ("touch it, shrink it"), and the plan sizes that
   extraction;
3. never mid-decomposition, because a may-fail result measured on a loop mid-refactor can't tell a null from the
   refactor.

| PR | What | Size |
|---|---|---|
| 0 | Red gates: a deferred result books no POSITIVE; a receipt is credited exactly once; a stale refusal books nothing; a call error books nothing | S |
| 1 | `default_outcome_valence`; promotion of the receipt id; the failure kind on the bridge's failure return | M (with extraction) |
| 2 | `ModulatorReceipt`; cerebellum observation at settle; the exactly-once ledger | L (with extraction) |

## 5. What it claims

Nothing behavioural. It is `[engineering]` wiring that stops a known mis-credit. Whether observing at settle
improves what an agent learns in a world with latency is a question for an experiment. Overdrive's hybrid
contribution (`hybrid_1_5_line_DRAFT.md`) proposes one; a calibration sweep can't earn it.
