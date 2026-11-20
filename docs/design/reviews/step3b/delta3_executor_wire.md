# Third delta round, step 3b(a): Executor and Wire integrity

Range: `git diff a3d7b07 d9b22d8`, run on a `git archive d9b22d8` copy with the worktree's venv. These pass on the
copy: ownership, frames, constructors, sem_bridge, act_validation, imagination, snapshot, validation, extremes,
lint_gates, lint_inputs_corpus and determinism, 910 tests (one `git ls-files` test deselected). The harness is
`_durable/3b_review/delta3_mutate.py`.

## Correction first: my delta-2 report was wrong about the risk from `r*r`

My delta-2 N-d said that across 3,000 random radii and centres at 0.2 m and 0.1 m, no cell changed side, and so
"nothing ships wrong". The measurement was true and the conclusion was false. At r = 0.28284271247461895 m (√0.08)
on the 0.2 m grid, `r*r != r**2` and the barrel mask is 20 cells with `r**2` and 24 with `r*r`. I reproduced this on
the copy. The same radius gives 192 cells either way at 0.1 m, and 1,536 either way at 0.05 m.

Why the random sample missed it:

- A cell changes side only when r² lands within one ulp of a cell centre's exact squared distance from the axis.
  Those distances form a finite set of sums of grid-spaced squares (here 0.2² + 0.2² = 0.08).
- A radius drawn uniformly from [0.05, 1.4] lands within one ulp of one of them with probability about zero. So
  3,000 draws say nothing about the cases that matter.
- Authored radii are exactly the values that land there: √0.08 is a cell diagonal. They are the opposite of random.

The right probe builds the knife edges directly: set r to each centre's distance from the axis, then compare the two
formulas. My sampling measured the reach of a distribution nobody authors from. That is the "measure fuzz reach"
rule, which I did not apply to my own probe.

## Status of my delta-2 NITs (set from the tree)

| id | status | evidence (mutation → result) |
|---|---|---|
| N-d: the cylinder rerun test can't see a geometry change | **fixed** | `Cylinder.mask` returns to `radius_m**2`, as on fa27d5f. The rerun test is renamed `test_a_cylinder_scene_is_repeatable_in_process`, which no longer claims more than it does. The new `test_a_cylinder_mask_squares_its_radius_as_fa27d5f_did` pins the mask at the knife-edge radius. Each of these turns it red: `r*r`; `<=` instead of `<`; `radius*1.001`. Its comment states the limit: where pow rounds exactly, the two formulas agree and the test can't tell them apart (so on another libm the `r*r` mutation could pass). |
| N-e: frames.py "published when they change" | **fixed** | The docstring now says frames are published after each window closes, "whether or not the window changed a cell". That matches `World.writing`. |

## Can the new tests fail?

**`tests/test_lint_inputs_corpus.py`: yes.** Each of these planted lint regressions turned corpus cases red:

| mutation | result |
|---|---|
| `os.environ` dropped from `INPUT` | 7 red |
| `yaml.constructor` dropped from `UNSAFE` | 1 red |
| `recv` dropped from `READ_METHODS` | 1 red |
| `getattr(x, 'name')` no longer resolved | 1 red |
| `sys.modules['pickle']` no longer resolved | 2 red |

`test_the_corpus_holds_every_round_and_both_verdicts` keeps both clean and flagged cases for each rule, so the corpus
can catch an over-flag as well as a miss. My one over-flag mutation (adding a prefix `"j"`) stayed green, but that is
my mutation's fault, not the corpus's: no corpus name canonicalizes to `j`. The flagged-false cases cover the real
over-flag risks (`params.get`, `self.environ`, `re.compile`, `builtins.len`, `sys.modules['json']`).

**The knife-edge test: yes.** Three red mutations are listed above. It holds only the 0.2 m grid, which is the only
spacing where this radius is a knife edge.

**`test_the_opener_scan_counts_holding_as_an_opener`** asserts the scan reports `holding`, and the only-owners test
still passes, so `World.writing`, which calls `holding`, is the listed owner.

## New findings

Counts: **0 BLOCKER, 0 SHOULD-FIX, 1 NIT.**

### N-f. NIT: `tests/test_determinism.py::test_a_cylinder_mask_squares_its_radius_as_fa27d5f_did`: the pin depends on this machine's `pow`

The test compares the mask with a reconstruction that uses the same `r**2`. So it pins the formula, not fa27d5f's
cell count (20). On a platform whose `pow(r, 2)` happens to equal `r*r` at this radius, the `r*r` mutation would pass
silently. The comment admits this.

A second assertion, `mask.sum() == 20` at 0.2 m on this radius, would pin the outcome where the machine allows it. A
`pytest.mark.skipif(r*r == r**2)` with a stated reason, or a radius chosen where the two differ on CI's image, would
make the platform dependence loud instead of silent.

For the Physics lens: a mask that moves 4 cells on a one-ulp change is a binary decision at the cell centre.

## Wire integrity: contracts in this diff

| Contract | Change | Consumers | What they get |
|---|---|---|---|
| `Cylinder.mask` | `r*r` → `radius_m**2` (fa27d5f's) | `Scene.build`, `place`, tests | Cells identical to fa27d5f's on this machine; at the knife edge, 20 cells, as before 8c1de1e. |
| `shown` for `np.bool_` nested | `repr(x)` → `repr(bool(x))` | refusal text | `[True]`, not `[np.True_]` (numpy 2). |
| `lint_inputs` rewritten as one canonicalizer | the API used by `lint_standards` (`check_inputs`) is unchanged | `lint_standards.main`, `lint_gates` (`INPUT_GATES`) | 145 lint tests pass on the copy. I did not run the repository-wide `check_inputs` beyond `test_lint_gates`'s repository test. |
| Docstrings (applier, frames, ownership comments) | the claims were narrowed to "capability passing is the guard; the scans are tripwires" | review | True to the code: the membrane holds no `World` or grid. |
