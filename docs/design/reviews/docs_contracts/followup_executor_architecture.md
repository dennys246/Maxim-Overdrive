# phase1/b36-followup: Executor and Architecture review

Reviewer: independent, lenses Executor and Architecture. Diff: `origin/main..HEAD` (fb54d29, f181445, 5394e3e;
merge base 98e2342). Read-only; probes ran on temporary copies in the scratchpad.

**Counts: 2 BLOCKER, 3 SHOULD-FIX, 6 NIT.**

## What was verified (no finding)

- **Red first, fb54d29.** With 98e2342's `scripts/lint_contracts.py` under HEAD's tests,
  `test_mentions_scattered_through_a_list_are_references` and `test_a_registry_count_below_one_fails[0]` fail;
  `test_a_copy_one_member_per_bullet_fails`, `test_a_list_whose_items_lead_with_members_restates` and
  `test_one_list_item_holding_the_count_restates` pass. The claim is true.
- **Red first, 5394e3e.** With f181445's lint, the partial-banner, both bulleted/bare ruling cases and the bare-bar
  test fail. The lead test and the stale-exclusion test pass (see N3).
- **Mutants** (14, in a tmp copy): killed are heads dropped, LEAD without `(?:\*\*)?`, `< 1`→`< 0`, the `in part`
  lookahead removed, the ruling prefix made required, `Ruled` dropped, lead 3→2 and 3→4, the bare-bar check removed,
  whole-run counting restored (killed only by `test_the_real_tree_passes`), `max(key=len)` replaced, the stale check
  against all spans, per-line paragraph counting. One survives (N2).
- **Counts in `docs/design/contracts.md`.** Re-derived on this tree with the new counting as max(3, largest
  reference outside the owner + 1): all 13 rows match. `record.kinds`: largest reference 4 (`boundaries.md:427`,
  `sem_stimuli.md:237`, `checklists.md:113` item), so 5; under the old counting `checklists.md:113` held 5, so 6, which
  confirms the 6→5 change is caused by the counting. `agent_failed.reasons`: largest 2 (`client_rendering.md:78`,
  `protocol`, `build`), so 3, as 5394e3e says.
- Tests: `tests/test_lint_contracts.py` and `tests/test_scene_v1.py` 164 passed; `test_lint_standards.py`,
  `test_check_plan.py`, `test_validation.py` 371 passed. mypy clean on the lint and its tests. `lint_standards` PASS.
  `scripts/lint_contracts.py` is 100% branch-covered by `test_lint_contracts.py` plus `test_lint_standards.py`.

## BLOCKER

### F1. BLOCKER: `tests/test_scene_v1.py::test_the_phase_2_keys_are_refused_by_path_with_the_reason`, the gate's ruff steps fail

**Failure scenario.** `scripts/prepush.sh` runs `ruff check src tests scripts` then `ruff format --check`. Line 116 is
127 characters: `E501 Line too long (127 > 120)`, and `ruff format --check` reports the file "would be
reformatted". The gate cannot print `prepush: PASS` for HEAD. f181445's message reports 347 tests passing but no lint
run; the message string was lengthened without rewrapping the `pytest.raises(...)` call.

**Fix (unverified):** the wrapped `pytest.raises(` form that `ruff format --check` printed in its diff. I ran
`ruff check` and `ruff format --check` to see both errors; I did not apply the fix.

### F2. BLOCKER: `docs/design/inference_placement.md`, `sem_stimuli.md`, `tile_and_client.md`, existing designs grew

**Failure scenario.** CLAUDE.md (O22): "an existing design document doesn't grow". Word counts by `str.split()`, the
counter `scripts/check_plan.py::over_budget` uses, with contract-marker lines excluded (round 1 ruling 2), merge base
98e2342 → HEAD:

| Document | Base | HEAD | Δ |
|---|---|---|---|
| `inference_placement.md` | 4,607 | 4,626 | +19 |
| `sem_stimuli.md` | 5,888 | 5,898 | +10 |
| `tile_and_client.md` | 5,351 | 5,354 | +3 |

(`boundaries.md` −7, `npcs_and_sem.md` −10, `fire_model.md` −26.) f181445's message says "No design grew past its
origin/main count", which is false for three documents. The growth is all from f181445: §4.2's new rerun bullet
(+19, and redundant: N4), §6.2's stale sentence (+10), tile's "Zones take a later scene version" (+3). B24 is
unchecked, so only review catches this; the commit claim is what makes it a defect of record, not just a size slip.

**Fix (unverified):** cut the words in the same documents, or move the new sentences to links; recount with
`split()`.

## SHOULD-FIX

### F3. SHOULD-FIX: `docs/design/boundaries.md` §7.2 and §13, `npcs_and_sem.md` §6.4, ruling 1 folded halfway: the stale texts still contradict it

**Failure scenario.** Follow-up ruling 1: stale credit is host-side, "the host withholds credit from a stale intent
... so v1 receipts need no `stale` kind", owner `sem_stimuli.md` §6.2. The fold dropped "the receipt goes to the next
thought's context" but kept, unchanged:
- boundaries §7.2 and npcs §6.4: "**Stale is context, never credit** (lesson 9). Until Maxim promotes a
  refusal-kind key ... stale refusals are an OPEN divergence with a strict red gate."
- boundaries §13: "**Stale refusals** stay an OPEN divergence until Maxim promotes a `stale` refusal kind (OD-A16)
  ... Roadmap Phase 3's exit now requires OD-A16 before Phase 4."

Under the ruling, a stale intent never reaches Maxim as `success=False` (the new checklist line says its receipt reads
`accepted`), so the divergence these bullets gate, Maxim booking a stale refusal NEGATIVE, has no v1 producer. The
agent PR author reads three documents and must pick: write the strict red gate §7.2 demands for a path that no longer
exists, or follow §6.2. "Stale is context" now names no context mechanism. "Never credit" is now stated in three
places (sem_stimuli §6.2, boundaries §7.2, npcs §6.4) where the ruling named one owner, so the fold added a
restatement rather than removing one. The ruling did not say whether OD-A16's stale half closes; that is for the
owner, and the texts must not contradict each other meanwhile.

Also: "Each receipt is credited exactly once ... a stale intent's credit is §6.2's" says once and then zero for stale
in one sentence.

### F4. SHOULD-FIX: `scripts/lint_contracts.py::counted_spans`, item-plus-head counting is strictly weaker than whole-run counting, and the texts still claim the old strength

**Failure scenario.** Every set `counted_spans` returns (the heads, each item's spans) is a subset of the old
whole-run set, so the new rule never catches a copy the old one missed. It now misses these, each probed against
98e2342's lint and HEAD's in a plan (old FAIL → new pass):
- `- Over: \`budget\`` / `- Late: \`timeout\`` / `- Bad: \`parse\`` (member not first in the item);
- `- **Budget** (\`budget\`): …`, one per bullet (a bold label first: a common glossary shape);
- `- *\`budget\`*`, one per bullet (italic, LEAD only allows `**`);
- nested sub-bullets under two parents (`- A:` / `  - over \`budget\`` / `- B:` / two more), since LEAD is anchored
  at column 0.

Each is round 1 A1's failure (a bulleted copy goes stale unseen), in shapes other than A1's exact `- \`a\`: …`.
fb54d29's message says "a copy written one member per bullet is still caught"; true only when each bullet starts with
the member. Reader-facing text overstates the guard, which is what A1 also cited:
- module docstring, lines 16–17: "a run of list items, so a copy one member per bullet counts";
- `blocks` docstring: "a vocabulary spread over its rows or bullets is a restatement";
- `docs/design/contracts.md`'s limits sentence lists "a copy below a row's count" but not "a copy whose bullets don't
  lead with the member".

Vice versa: a list glued to a lead-in line with no blank line (`Steps:` then three items with scattered mentions)
starts with a non-item line, so it is still counted whole-run and fails. contracts.md says "A list counts item by
item"; the code does that only for a block whose first line is an item. Nothing on the tree trips it today.

Choosing item counting traded a false positive in one checklist (`record.kinds`' 40-item list) for a class of false
negatives. That trade is a guard-strength decision; I found no ruling or review row that asked for it
(`rulings.md`, `delta2_executor.md`, `round1_architecture.md` searched for "item", "bullet", "scattered").

### F5. SHOULD-FIX: `docs/plans/checklists.md`, agent-line PR, the `BoundFrame` test's first half cannot fail

**Failure scenario.** "a rerun with every push stripped from the record matches each per-tick digest". Ruling 5 and
`sem_stimuli.md` Q8 say a push is unlogged, so the record holds no pushes and stripping them removes nothing: the
rerun is identical to an unstripped one, and the assertion holds whether or not the digests cover the pushed values.
As written it is a test that cannot fail. The second half (a planted push of a value the world didn't produce turns a
digest red) is the one that discriminates. Note the mechanism under test (a stub's push log, T16a) is a test stub, not
the replay log, which the line should not conflate.

## NIT

### N1. NIT: `scripts/lint_contracts.py::RULING`, the widened pattern adds false positives, and D2-2's remainder is unrecorded

Making the bullet prefix optional flags any design line that opens with a bold id followed by `**`, `.` or `:`.
Probed: `**D14** holds the push rate here.` and `**T4** gates receipt bytes.` pass on 98e2342 and fail on HEAD as "a
list of rulings". Designs bold ids inline routinely (`sem_stimuli.md`'s `**T16, three gates,**` escapes only by its
comma). Fail-closed, so a NIT. D2-2 also named `- **OD-A1.** x` (still passes) and the `- **D1** deliverable` false
positive (still fails); 5394e3e records neither.

### N2. NIT: `scripts/lint_contracts.py::counted_spans`, `or not items` is dead

The early return guarantees `lines[0]` is an item, so `not items` is never what makes the condition true. Mutant
`if ITEM.match(ln):` survives all 63 tests.

### N3. NIT: 5394e3e's message, "Each fold below is pinned by a test that failed first"

`test_the_lead_of_a_design_without_sections_is_its_first_three_paragraphs` (D2-3) and
`test_an_exclusion_outside_a_tables_first_column_is_stale` (D2-4) pass on f181445's lint. They pin existing behaviour
and kill mutants (verified above), which the bullets also say; the header overclaims red-first for those two.

### N4. NIT: `docs/design/inference_placement.md` §4.2, the new rerun bullet is subsumed

"A rerun reads and never dispatches" two bullets above already forbids a rerun from running any model; "never re-runs
a model on purged text: it reads the recorded replies" is a narrower restatement inside the same list. Its 19 words
are F2's largest share. Pointing O26 at the existing bullet would carry ruling 3 at no growth.

### N5. NIT: `docs/design/fire_model.md` §10.2, the 6.0 row still states the scene-version slot

The row reads "6.0 formats | … the next scene version …" while `fire_solid.md` §5.2 puts fuel entries in "the scene
version after the one on `main` when 6.0b lands". The §7 list became a link (ruling 4), but this row keeps a copy of
the slot in a different sub-step's row, and "next" reads as fixed where the ruling says versions go to whichever change
lands first.

### N6. NIT: small

- `tests/test_lint_contracts.py::test_a_registry_count_below_one_fails` is parametrized over one value, `"0"`.
- The edited CLAUDE.md lines ("Reconstruct …", the handshake line) and `tile_and_client.md`'s scene-v1 bullet and
  `npcs_and_sem.md` §6.6's lifecycle line now run past the 120-column wrap the files use elsewhere (not gated).
- `sem_stimuli.md` §6.2's fold drops ruling 1's "which its log names"; harmless, but the host-side log is the only
  place a stale intent is visible to anyone.

## Rulings check (Architecture)

| Ruling | Folded as ruled? |
|---|---|
| 1 stale credit | In part: clauses dropped and §6.2 named, but contradictory OPEN-divergence text kept (F3) |
| 2 run seed | Yes: npcs §3.4 and boundaries §11.2; root id stays in boundaries §6 and npcs §6.6's replay ids |
| 3 O26 rerun | Yes, as a redundant bullet (N4); "Tier-1 replay calls nothing" is already §4.2's "Replay never opens the cache" |
| 4 scene versions | Yes for fire_model §7, scene.py, schema.py, tile; the §10.2 row keeps a copy (N5) |
| 5 Q8 | Yes in sem_stimuli §11.2; the checklist test's first half can't fail (F5) |
| 6 CLAUDE.md owners | Yes: `world_model.md` §3 and `boundaries.md` §5.3 exist and own the rules |

The checklist's "its receipt still reads `accepted`" is the author's derivation from §6.2's D15 (stage-2 results are
`accepted`), not in the ruling; it is consistent only if staleness is decided at stage 2, which no live text says
outright.
