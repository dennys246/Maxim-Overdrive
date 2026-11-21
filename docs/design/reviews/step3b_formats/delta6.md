# Step 3b part (b), delta round 6, and the review's summary

Diff: `d263c1b..e70941e` (delta round 5's fold) and the merge `d4e1163` with `origin/main`. One reader held Executor,
Trust boundary and Wire integrity. The reader can't write files, so this is the author's condensed record.
**Statuses are the reviewer's (O25).**

## Delta round 5 findings, status set by the reader

All four **fixed**:
- **R5-1:** dropping the upper-cased candidate turns exactly 2 tests red. Probed over every cased code point, it admits
  exactly Cherokee's 86 small letters, and each keys to its capital.
- **R5-2:** dropping the one-system rule turns 30 tests red. Nd digits come in runs of ten, so `ord - digit` names one
  system.
- **R5-3 and R5-4:** the B38 text and the comment above `_NAME_SEPARATORS` are correct.

## The merge

The renumbering is correct:
- This branch's rows B30 and B31 became B37 and B38, byte for byte, because `main` owned B30 to B36.
- Its lesson 25 became §29, because `main` owned §25 to §28.
- A second merge, after this round, moved them again: `main` had since taken B37 and lessons 29 and 30, so the rows
  are B38 and B39 and the lesson §31 (`git log` has the merge commit).
- Every reference to this branch's rows and lesson follows, and none of `main`'s own references changed.
- Both sides of both conflicts are kept.

The merged tree agrees with `main`'s new `simcore.verify` layer: 9 import contracts kept, 0 broken. The standards
lint passes.

## New findings: 0 BLOCKER, 0 SHOULD-FIX, 2 NIT

| Id | Location | Scenario | Fold (author's claim) |
|---|---|---|---|
| N6-1 | `schema.py::_visible_word` | the comment said "as IDNA's CONTEXTO rules ask", but the code is stricter (it refuses `1٢`, which CONTEXTO allows), so a reader could "align" the code with the comment | the comment says the rule is stricter, on purpose |
| N6-2 | B38 | look-alike digit systems split by a separator (`١ ۲`) pass; B38 read as one number only | B38 names the separator case |

The rounds stop here: this round folds nothing in code (CLAUDE.md, "Review before push"; `docs/code_review.md`).

## The review, round by round

| Round | Diff | BLOCKER | SHOULD-FIX | NIT | Record |
|---|---|---|---|---|---|
| 1 (six readers) | `origin/main...951aee4` | 0 | 29 | 31 | `round1.md` |
| Delta 1 (three readers) | `951aee4..f2c180c` | 0 | 12 | 13 | `delta1.md` |
| Delta 2 (two readers) | `f2c180c..d116508` | 0 | 7 | 11 | `delta2.md` |
| Delta 3 | `d116508..7e04987` | 0 | 5 | 5 | `delta3.md` |
| Delta 4 | `7e04987..3dab2b4` | 0 | 4 | 5 | `delta4.md` |
| Delta 5 | `3dab2b4..d263c1b` | 0 | 2 | 2 | `delta5.md` |
| Delta 6 | `d263c1b..e70941e`, merge | 0 | 0 | 2 | this file |

### Deferred, each with its trigger

- **Round 1 Wire S1:** `phase1/client-shader`'s fixture script builds a v0 scene. It is not fixable from this branch;
  that line's session has been told.
- **Architecture A3:** `SCENE` becomes `held_by_others` when step 5a's log header records a scene.
- **A7:** units and provenance on `Field` arrive with 6.0a.
- **A10:** stage-1 intent parsing moves onto the schema in step 7.
- **Wire N6:** today's codes get their reply and logging classes in step 5a.
- **Determinism N7:** spawn-to-cell mapping stays integer at step 5b.
- **R3-7, and B38:** cross-script look-alikes, combining-mark runs, mid-word joiners, look-alike digit systems and the
  apostrophe pair wait for TR39's skeleton, at the first names from outside this repository.
- **B39:** further deliberate input-lint spellings wait until untrusted code can reach `src/`.
- **`Scene.from_dict`:** registered as partial until step 5a's memory budget.
- **Digests:** they have no shipped caller until step 5a.
- **Body archetypes and items:** not built (owner, 2026-11-21).

### Rejected with a reason, reviewer agreeing

Executor N5, Architecture A14, Bio N1, T1-N5, D-N5, D7 (Trust) and R4-8.
