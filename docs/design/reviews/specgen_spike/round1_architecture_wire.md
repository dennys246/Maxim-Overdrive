# Spec generator spike, round 1: Architecture, Wire integrity and Bio-faithful (2026-11-22)

This is a condensed record of the reviewer's hand-back message; review agents can't write files. It covers the
branch's diff against `origin/main` 98e2342. Maxim's `origin/main` is 688c4b02 (checked with `rev-parse`).

## BLOCKER

- **B1, `decisions/boundaries.md::O57` (and plan §1 and §2.5, lesson 32 and the tracker): Maxim's provenance terms
  are misused.**
  - In Maxim, provenance is a closed set on body-consequence records (`sem.py:461`,
    `InteroceptiveOutcome.provenance`), and `Entity` has none.
  - `apparatus` (G16) means harness writes to a drive, which are never a training target and never credited.
  - `imagined` is another value in the same set.
  - O57 gives the generator `apparatus` and its objects `imagined`. That is two exclusive values, applied to objects,
    not to outcomes.
  - Failure scenario: what an NPC suffers from an imagined table gets discounted, and the NPC never learns that it
    burns, which defeats D33's exit. Once the object exists, those consequences are `experienced` world events.
  - Fix (unverified): drop both terms, and ask Maxim the labelling question as an open question.
- **B2, `decisions/world_model.md::D32`: false pointer.** `world_v2.md`'s "Not now" list has no buoyancy and no rigid
  bodies. The source is `research/states_of_matter/gameplay.md:225`, under "Drop as scope creep". Fix (verified by
  grep): cite that, or cut the sentence.

## SHOULD-FIX

- **S1, `boundaries.md` §5.3 against O57: the contract stays stale, and the deferral has no trigger.** Step 5a, the
  next reader, builds `imagine` from that row. It is a one-cell edit that adds no words.
- **S2, O57: trust and replay are unstated.** Whatever route Phase 6 chooses, two things must hold:
  - the generator's output stays untrusted and passes stage 1 and `place`;
  - the intent log records the generated spec, never the request, so replay never re-runs the generator (compare
    `ip_and_licensing.md` §3.4 and npcs O26).
- **S3, O57 and lesson 32: the citation is archived and too narrow.** `substrate_plan.md` is archived. Cite Maxim's
  `README.md:28` and `docs/experiments/README.md:7`, with `substrate_plan:766` as history (verified).
- **S4, roadmap Phase 3: the question to Maxim isn't tracked.**
- **S5, foundations index: O57 is filed under npcs §0.** It belongs in the boundaries section (verified).
- **S6, O56's owner is `npcs_and_sem` §4.5, which is about latency.** Fix: owner "—", or boundaries.
- **S7, plan §6:** the go and stop rules can both fire, and no precedence is given.

## NIT

- **N1:** D31 should read "cites §3.2, §4".
- **N2:** O57's status should be plain "live".
- **N3:** "rejection 13" means `TOO_SMALL` and `architecture.md:121`.
- **N4:** `imagine` calls `EntityDesigner.design()`, which routes to `_design_with_llm` or the fallback.
- **N5:** the tracker's "Laws" and "Next" rows lean toward design (owner's taste).
- **N6:** lesson and plan dates (2026-11-21) predate the rulings (2026-11-22).

## Checked and true

- **Maxim paths and quotes:** the paths exist, the quotes match, there are 96 tests, the G6 and G16 kinds are right,
  and there is no geometry in Maxim's imagination.
- **This repo's facts:**
  - the v0 budget and `RefusalCode`;
  - `_ignite` at the centroid;
  - the turn-50 burn-away and both Known gaps;
  - `world_v2.md` §3.2 and §4;
  - `ip_and_licensing.md` §3 and §6;
  - the docstring's date.
- **Fit with the IP gate:** O57 doesn't conflict with it; the generator is the "LLM caller".
- **Format:** the row formats are right, and no design document grew.
