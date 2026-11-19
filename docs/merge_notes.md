# Merge notes for the phase 1 branches

A checklist for whoever merges `phase1/act-validation` with `phase1/realtime-design`. Each item comes from a review
round's merge check (see the named commits). The `phase1/standards` and `phase1/design-v2` items were done when
`main` was merged into this branch (O21), after PRs #1, #4 and #5 landed. Delete this file in the merge below.

## `phase1/act-validation` into `phase1/realtime-design`

- [ ] **Delete `tests/test_closed_schemas.py`.** Its strict red gates held the "loaders ignore unknown keys" defect
  that act-validation fixed (`35fcbdb` onward), so they now pass and turn red. Act-validation's refusal tests in
  `tests/test_validation.py` replace them.
- [ ] **`docs/standards_backlog.md` B12:** take act-validation's row. Drop realtime-design's "Today all five ignore
  unknown keys", its pointer to `tests/test_closed_schemas.py`, and its closed-schemas "Lands with" wording.
- [ ] **`docs/design/ip_and_licensing.md` §6, item 3:** "On this branch `_read` still ignores them" is no longer true.
  Reword it to say the reader refuses unknown keys (`checks.known_keys`, `imagination.spec.SPEC_KEYS`).
- [ ] **`src/maxim_overdrive/imagination/spec.py::SPEC_KEYS`:** its comment cites "the IP note on
  phase1/realtime-design"; make it a plain path.
- [ ] **`scripts/lint_standards.py::check_guards`:** keep the duplicate backlog-id check, computed before anything
  else; `standards_bullets` returning `(bullets, missing)` is already in from `main`. Act-validation's format-versions
  row is B21, free on `main` (which holds B16 to B20 and B22 to B24).

## After every merge

- [ ] `scripts/prepush.sh` prints `prepush: PASS <sha>` on the merged commit.
