# The merge round, Architecture lens (2026-11-23)

**Lens:** Architecture (`docs/code_review.md`). **Head read:** afdb849 on `phase1/torch-pilot`.
**Summary:** 1 BLOCKER, 3 SHOULD-FIX, 2 NIT.

Scope: the resolutions in 88a410a (main at 7500a85), 2728425 (main at b578761) and afdb849 (the parked row and
`fold4.md`). The torch-pilot design itself was not re-reviewed; the findings below are places where text main brought
in now disagrees with merged torch-pilot text, or where the new row misstates its source.

## What holds (checked, not findings)

- **`fire_solid.md` §1.3, contact.** The resolution keeps main's text (present geometry in µm, `subcell_solids.md`
  §4.1, authored primitives before S1) and the branch's ending. Main's "(6.2, or `kindle` in 6.4)" is stale under
  the torch pilot, so the branch's "6.1b's `kindle` uses geometry" is right in meaning, not only by side. Nothing in
  `subcell_solids.md` names `holds_fuel`.
- **`fire_solid.md` §2.** Main's S0 text plus "from 6.1b". It reads correctly against 5b: before 6.1b, 5b's sphere
  `kindle` reaches cell parts only, which is what `docs/plans/checklists.md` step 5b and `torch_pilot.md` §10's tile
  row say. `fuel_only_region` is gone from every live design. It remains only in review reports and research notes,
  which are records.
- **One owner per contract.** I found no contract stated twice. `subcell_solids.md` §7.1's `kindle` row links
  `torch_pilot.md` §3 and doesn't restate it, and the strike row cites §3's shared ranked query, which §3 defines
  ("One query, two policies"). `fire_model.md` §5.4 and `client_objects.md` §7.3 link here. `contracts.md`'s
  `pilot.fields` row is the branch's alone. Every section number that `torch_pilot.md` cites in `fire_solid`,
  `sim_core`, `tile_and_client`, `client_objects`, `sem_stimuli`, `fire_model` and `boundaries` still exists:
  between the merge base aaebc1b and HEAD their headings are unchanged, apart from `client_objects.md` §9 losing its
  date suffix. `torch_pilot.md` doesn't cite §9. `sim_core.md` §9's member 6 (pilots) doesn't collide with anything
  main added.
- **Known gaps' owner.** `torch_pilot.md` §7's heading and §10's row now send their entries to `docs/known_gaps.md`.
  No live design on the branch still sends a gap to `docs/architecture.md`; older research notes do, and they are
  records. `known_gaps.md` says "a gap is added here, never in a design document", while §7 stages its entries for
  6.1b's commit. `inference_placement.md` §6.3 and `subcell_solids.md` §12 on main follow the same pattern, so I don't
  count §7 as a second owner.
- **Roadmap resolutions.** Phase 1 keeps main's write-window bullet (PR 4a/4b), the frame-0 bullet from #59 and the
  port bullet, plus the branch's TP6 sentence. Phase 2's late-burn bullet has main's `known_gaps.md` link and the
  branch's TP6 sentence. OD-A16 carries both sides' evidence, main's citing §37 and the branch's citing lesson 38.
- **Lesson renumbering.** `docs/lessons_maxim_in_games.md` has 37 (main's, the port read-back) and then 38 (the
  branch's, call-window credit). The only places that cite the branch's lesson are `torch_pilot.md` §12 ("Lesson 38")
  and the OD-A16 row ("lesson 38"). Both moved. Every remaining "lesson 37" or "§37" in the tree is main's lesson:
  the OD-A16 row's step-5a evidence and the `reviews/sim_tick/` reports. I grepped every spelling, `lesson(s) N`,
  `§N` and `Lesson N`, over the whole tree. No torch-pilot review report, decision log or upstream draft cites the
  lesson by number.

## BLOCKER

**A-B1. `torch_pilot.md::§3 The target` (candidates) and `::§7` (the crater gap): candidacy is decided by "no solid
cell left", the predicate main's owner ruling retired because it flips with grid spacing.**
§3 says "A cell region with no solid cell left is no candidate", and §7 repeats it ("a cell region is its authored
primitives until it has no solid cell left"). The merge brought in main's evidence and ruling against exactly that
predicate:
- `docs/plans/checklists.md`, step 6, "Added by step 5a PR 4a's review": "no solid cell left" flips with the grid
  spacing. On a 1.2 m wood cube, strike 29 empties it at 0.2 m and strike 30 at 0.1 m.
- `sim_core.md` §5.1: "'gone' is authored geometry only, so a strike on a destroyed region destroys nothing (owner,
  2026-11-22)".
- `src/simcore/core/applier.py::_check_region` was reverted to that rule, with a comment that deciding on destruction
  "would refuse at one spacing and accept at another".

*Failure scenario:* strike that cube 29 times, then `kindle` at a point on its authored top face. At 0.1 m the cube
is still a candidate, so the act is applied to a cell target and is fruitless. At 0.2 m it is no candidate and
nothing else lies within 50 mm, so the act is refused `not_on_surface`. Put a fuel slab 20 mm from that point and
the 0.2 m run targets and deposits on the slab, while the 0.1 m run deposits nothing. The outcome class changes with
the grid spacing, which breaks the resolution rule (CLAUDE.md). The merged tree now holds both the measurement
proving this and the design text relying on it. Nothing on the branch reconciles the two.

*Fix (unverified):* align §3's candidacy with main's ruled meaning of "gone" (authored geometry), so that a destroyed
region stays a candidate by its primitives. Candidacy then never reads a destruction count. That is a contract
change to §3 and §7, so the owner may want to rule. The destruction-based rule already has its own row in step 6
("decided in metres … gated with an outcome margin across grids"), which §3 could cite instead.

## SHOULD-FIX

**A-S1. `torch_pilot.md::§9.4` (the four `ignite` gates and what 6.1b deletes) names a test and a function that main
renamed or removed.**
- The fourth gate is listed as `test_the_crate_is_badly_burned_at_the_same_turn_at_every_rig`. Main's 336eee8 (PR
  4a, brought in by the merge) renamed it `test_the_crate_is_badly_burned_at_the_same_time_at_every_rig`
  (`tests/test_cross_tier.py`). `docs/known_gaps.md` uses the new name. No test of the old name exists.
- `test_a_fire_that_has_burned_its_fuel_stops_heating` "guards `World._power_field`'s fallback into air", and "with it
  `HeatSource`, `sources`, `source_exposure` and `_power_field`" are deleted at 6.1b. `World._power_field` no longer
  exists. `sim_core.md` §2 lists `World` "minus … `_power_field`", and the deposit now lives in
  `src/simcore/core/deposit.py::Deposit`, reached through `heat.py::HeatLaw.prepare`. No other live design names
  `_power_field`.

*Failure scenario:* TP6 closes each gate "by that deletion, recorded". The 6.1b author follows §9.4 to name the
deleted gate and the deleted mechanism in the commit, and finds neither name. One gate's deletion record then cites a
test that never existed under that name, and the "fallback into air" subject points at code that has moved. The
deletion proof §9.4 promises can then name the wrong mechanism. Separately, `torch_pilot.md` §10's `tests/` row
("each named in 6.1b's commit") depends on these names.

*Fix (verified by grep over `tests/` and `src/` at afdb849):* use the renamed test, and name the deposit's fallback
by its present home (`core/deposit.py`, via heat's `prepare`).

**A-S2. `docs/roadmap.md::Phase 1` "Parked: one file per record": it says round 1 found three BLOCKERs. It found
eleven.** I read `origin/phase1/records-layout` at 35cec7b with `git show`:
- `round1_architecture_bio.md` lists A-B1 to A-B4;
- `round1_concurrency.md` lists C1 to C3;
- `round1_wire_executor.md` lists W1 to W4.

None is folded, and their statuses are unset. The row names A-B1, C1 and W1 as if they were the whole list, and so
does afdb849's commit message ("its three unfolded round-1 BLOCKERs"). The omitted ones are not variants of the
named three:
- A-B2: immutable lessons contradict CLAUDE.md's "add or update";
- A-B3: decisions have no single id namespace;
- A-B4: a derived status loses recorded information;
- C2: a duplicate already on `main` can't be fixed under the design's own immutability;
- C3: `renumber` moves another branch's citations;
- W2: the renumber test can't fail on its real case;
- W3 and W4: the id grammar fails on day one, and "family" is undefined.

*Failure scenario:* at the trigger, the session that picks the design up sizes the work from the roadmap, plans to
fold three BLOCKERs, and finds eleven. The row exists only to carry that state forward, and it understates it. This
is a reported number that came out smaller than the source, which the first principle forbids.

*Fix (verified against the three reports):* state eleven BLOCKERs, or name them all, or say "eleven, among them …".
Everything else in the row checks out against the branch: the design path, the four families, "pushed, no PR"
(`gh pr list --state all --head phase1/records-layout` returns nothing) and the A-B1, C1 and W1 descriptions. The
owner's ruling is the author's claim; I couldn't check it.

**A-S3. `docs/design/generation_harness.md::U4 fire` (main's) against `torch_pilot.md::§5`: U4's bar is that
"`kindle` on the object ignites if and only if it is fuel", citing §3. Under the merged pilot, a fuel object ignites
only when a piloted part's profile reaches m''_flash while the pilot is live (§5).**
Main wrote U4 against the then-unmerged torch pilot, and the merge makes the link live. U4 cites §3, the target rule,
which decides what is hit, not whether it ignites. The outcome is decided by §5's pilot condition and §6's ceiling.
And §3's candidates include burnt-out objects, which never ignite.

*Failure scenario:* at 6.1b, U4 kindles a generated fuel object with a hold shorter than its `t_flash`, or kindles a
burnt-out object. Nothing ignites, which is correct physics, and U4 books "an engine defect (§6)". The harness's own
`world_outcome` class names "not igniting" as a world outcome, so the harness contradicts itself here.

*Fix (unverified):* this is main's text, so the fold here is a pointer, not a rewrite. Put a row in the 6.1b
checklist, or a note to the harness's owner, that U4's predicate needs §5's hold condition and live state, and that
its citation should read §5 and not §3 alone. Trigger: U4 leaves `not_run` at 6.1b.

## NIT

- **A-N1. `docs/roadmap.md::Phase 1` "Parked": the trigger names an event no document defines.** "The first step
  after the tag and its planning session … before the fan-out." The tree never says which tag (nothing names
  `v0.1.0` or a base-tag plan; I grepped `docs/`, `README.md` and CLAUDE.md), and never says what the fan-out is. A
  reader with only the repository can't tell when the trigger fires.
- **A-N2. `docs/design/reviews/torch_pilot/fold4.md::What changed`** says "three conflicts" and then lists four
  bullets: two hunks in one file, the lessons file and the roadmap. Three files, four resolutions.

## Outside this round's scope, noted

- `torch_pilot.md` §10's `fire_solid` row describes TP1 as an exception "from the object-only refusal". Under main's
  S0 text, §2 no longer refuses acts on object-only regions; they reach cell parts only. The row matches TP1's
  recorded wording (`decisions/torch_pilot.md`), so I don't count it as a defect.
- `subcell_solids.md` §4.3 ("gone when it has no live cell and no object …") reads as destruction-based, against
  `sim_core.md` §5.1's ruling. That is main's own inconsistency, but it bears on A-B1's fix: after S1, §3 follows
  `subcell_solids.md` §4.3's "gone" (its §12 row), so the two need one meaning.

## What I ran

- `git show 88a410a --cc`, plus diffs `0c3f30b..88a410a`, `aaebc1b..7500a85`, `7500a85..b578761` and
  `88a410a..afdb849`.
- A heading diff over seven designs, merge base against HEAD.
- Greps over `docs/`, `src/` and `tests/` for the lesson citations, `fuel_only_region`, `_power_field`, the gate test
  names and "gone".
- `git show` of the three round-1 reports on `origin/phase1/records-layout`.
- `gh pr list` for that branch.
- `scripts/lint_contracts.py` through the waiter. It was still queued behind other sessions after more than six
  minutes, so it produced no result, and this report claims none for it. The one-owner findings above come from
  reading the text.

Nothing was edited except this file.
