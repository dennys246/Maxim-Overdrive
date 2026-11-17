# Merge notes for the phase 1 branches

A checklist for whoever merges `phase1/realtime-design`, `phase1/act-validation`, `phase1/standards` and
`phase1/design-v2`. Each item comes from a review round's merge check (see the named commits). Delete this file in
the last of these merges, once every item is done.

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
- [ ] **`scripts/lint_standards.py::check_guards` conflicts.** Keep both realtime-design's duplicate backlog-id check
  (computed before the "no standards section" return) and act-validation's change to `standards_bullets`.

## `phase1/standards`

- [ ] **Backlog ids:** standards holds B16 to B20 (B20: "Assume other agents are working"). Act-validation's format
  versions are B21. The duplicate-id check in `check_guards` refuses a merge that keeps two rows with one id.
- [ ] **`scripts/lint_standards.py`:** standards splits the marker checks into `_marker_problems` and
  `_pragma_problem`. Realtime-design's Markdown check (`_markdown_problems`, which skips nothing by file) has to sit
  before that call, so Markdown files never reach the per-line marker check.

## `phase1/design-v2`

- [ ] **`docs/design/reviews/foundations_v1/delta1_wire_integrity.md:343`:** quote the bare `TEMPORARY(sim-clock)` in
  backticks. Realtime-design's lint reports a marker in Markdown prose, and a test refuses a directory exemption for
  review documents.
- [ ] **`scripts/lint_standards.py`:** drop design-v2's `MARKER_EXEMPT_DIRS`; Markdown code is quoted, not exempted.

## After every merge

- [ ] `scripts/prepush.sh` prints `prepush: PASS <sha>` on the merged commit.
