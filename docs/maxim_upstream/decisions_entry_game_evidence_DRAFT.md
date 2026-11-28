# DRAFT for Maxim: a `DECISIONS.md` entry, game evidence through Maxim's process

**Status:** drafted in Maxim Overdrive on 2026-11-26 for Maxim's owner to edit and file (link JP1 of
[joint_plan_DRAFT.md](joint_plan_DRAFT.md)), folded 2026-11-27 after one review round and its delta. Read against
Maxim `github/main` `a584c4d0`. Not filed.

**Whose words.** The owner ruled on 2026-11-26:
- game evidence counts through Maxim's process;
- only when pinned to valid commits of both repositories;
- four safeguards (pre-registered with a confounding review of the scenario; pinned before data, including scene
  digest and spacing; sensed, not handed; a verified world).

On 2026-11-27 the owner ruled:
- condition 3 keeps the listed-values route with a named sign-off, and Overdrive amends `boundaries.md` §13;
- content defaults to Apache-2.0 fixtures, with the owner's own content as a later ablation arm.

The author's are:
- the reading of "valid" (public `main` or a release tag, clean trees);
- the "from 1.3.6" scope;
- the rule that a content arm counts only once its content is published;
- the wording.

The owner may strike any of these.

## The entry

> **2026-11-26 — An Overdrive world can be a rung's evidence venue, through this repository's process.**
>
> A run in an Overdrive world counts toward a rung when all of the following hold:
> 1. **Pre-registered.** The rung's pre-registration names the Overdrive venue and is frozen on `main` before data.
>    It passes the four-lens design review, and the confounding lens reviews the world's scenario itself, so the
>    contingency is not built for the floor to lose (`baseline_floors.md`).
> 2. **Pinned before data.** The pre-registration pins the ledger record Overdrive defines for any run against its
>    world (its `docs/design/npcs_and_sem.md` §10, the one owner of that list). That record includes the Maxim and
>    Overdrive commits, each reachable from its repository's public `main` or a release tag, with both trees clean
>    at run time, plus the scene digest and the grid spacing. A run that misses any pin does not count.
> 3. **Sensed, not handed.** The agent reads no value that a declared receptor model at a body site did not produce:
>    no identity, no field's true value under a sensor's name. Either every value reaches the agent through
>    Overdrive's membrane (its SEM adapter and stimulus contract), or the pre-registration lists each value with
>    the receptor and site that produced it, and Maxim's Bio-faithful and Environment lenses sign off on that list
>    before data.
> 4. **Verified world.** The pre-registration cites the verification status of every world field the run depends
>    on, and Overdrive's Known gaps for those fields.
> 5. **Licensed content.** By default the run uses only Overdrive's engine and Apache-2.0 fixtures. An arm using
>    the game's own content compares content against that default (a content ablation). It counts only once that
>    content is published and pinned by digest; until then it is exploratory.
>
> The run is driven by a Maxim-owned harness and recorded on the ledger like any other run. **Today nothing in Maxim
> can assert which `simcore` a harness imported:** `_provenance.py` and `lint_harness_provenance.py` cover Maxim's
> own tree only. A harness check that asserts the imported `simcore` is the pinned commit is a Maxim item, needed
> before the first such run.
>
> **What does not change.** Every adoption still needs a transfer check before it moves a claim
> (`overdrive_refactor_candidates.md` §Cautions). Where that transfer check may run stays open. §Cautions gives
> that decision to the hybrid line owner, and `release_1_3_5.md` D8 to the owner; this entry decides neither. A
> game-earned result stays PARTIAL until its transfer check passes, as Overdrive's `npcs_and_sem.md` §10 says.
>
> **What it amends**, from 1.3.6 on (1.3.5 stays engineering), to "except as this entry allows":
> - the opening rule of `overdrive_refactor_candidates.md` ("game runs never go on Maxim's ledger");
> - `release_1_3_5.md` D8/D13;
> - §Line 3's harness items 2 and 3: its SEM-adapter bypass and commit stamp, which conditions 2 and 3 replace for
>   evidence runs;
> - the rules line "the harness runs under O10's strict red gates";
> - the line in "Answers to Overdrive" that repeats it.
>
> It also supersedes decision 4 of Overdrive's earlier draft entry ("Game runs never go on the results ledger",
> `decisions_entry_DRAFT.md`, answered yes on 2026-11-19 but not filed). File the two together, or this one after
> it.

## Overdrive's side of the same ruling

The first session after step 4 merges records these in `docs/design/decisions/`. Step 4 runs as briefed (owner,
2026-11-27):
- **O10's exception.** O10 reads "No developer mode with real Maxim before tier A, except inside strict red-gate
  tests". A ledger run is not a red gate. Proposed wording: "…or inside a Maxim-owned evidence harness under Maxim's
  2026-11-26 entry". The wording is the owner's.
- **`boundaries.md` §13's matching exception.** It keeps real Maxim behind the adapter a strict red gate until the
  embeddable contract ships. Without the exception, the listed-values route is the only one open before 1.4.x.
- **`npcs_and_sem.md` §10** gains condition 2's additions: the clean, public commits, the scene digest and the grid
  spacing. It already pins engine and pymaxim versions, membrane and agent contract versions, placement digests and
  world-only affordances.
- **The old rule's other statements** get the exception:
  - `CLAUDE.md` (the owner's edit);
  - `docs/roadmap.md`'s standing rules;
  - `docs/design/boundaries.md` §8.4;
  - `docs/maxim_upstream/hybrid_1_5_line_DRAFT.md`;
  - `docs/maxim_upstream/decisions_entry_DRAFT.md` item 4;
  - this directory's README, which already points at the ruling.

  The research notes `fire_ladder/6b_maxim_perception.md` and `time/skeptic.md` state the rule too. They stay as
  written, because research records aren't amended.
