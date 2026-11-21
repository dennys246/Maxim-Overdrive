# PR 21 (phase1/standards-bars) pre-push review: Executor lens

Diff: `origin/main...7debd5c` (c72fbe2, 7debd5c). Reader: Executor. Counts: BLOCKER 1, SHOULD-FIX 4, NIT 3.

## What I checked

- Read the whole CLAUDE.md, docs/code_review.md, the diff, both commit messages, scripts/lint_guards.py.
- `scripts/lint_standards.py`: PASS, 0 findings; 19 rules enforced by a check, 27 by review only. Every new
  `Guard:` resolves: B30 to B34 are rows in docs/standards_backlog.md, B10 exists,
  `tests/test_tooling_config.py::test_red_gates_are_strict_and_warnings_are_errors` exists, `docs/code_review.md`
  exists. No duplicate row ids.
- Ran `tests/test_cross_tier.py tests/test_act_validation.py tests/test_tooling_config.py` with this tree's `src`
  (pytest's `pythonpath = ["src"]` puts it first; confirmed with `PYTHONPATH=src`): 192 passed, 4 xfailed.
- The burnout gate under `--runxfail`: fails at `tests/test_cross_tier.py:90`,
  `AssertionError: (0.2, 422126.08)`, `assert 422126.08 < 2000.0`. So `raises=AssertionError` matches today's failure,
  and it fails on the bar, not on the ignite precondition. **Correct.**
- Every `xfail` in `tests/`: four, all `strict=True, raises=AssertionError` (three in test_act_validation.py, one in
  test_cross_tier.py). The commit's "three already passed raises=" is true.
- pytest behaviour, in a scratch project (`xfail_strict = true` ini): (a) strict xfail with no `raises=` and an
  in-body `import no_such_module` reports XFAIL; (b) the same with `raises=AssertionError` FAILS
  (ModuleNotFoundError); (c) a strict xfail whose body passes FAILS as `XPASS(strict)`; (d) a marker with
  `strict=False` overrides the ini and reports XPASS without failing; (e) with `raises=AssertionError`, an
  AssertionError from a precondition assert reports XFAIL. Verified (ran it).
- Every path the new text cites: `docs/plans/long_term_features.md` does not exist (below).

## BLOCKER

**B-1. CLAUDE.md::"Every bar is one of three kinds" (and "A future bar is tracked"): "Verification ... required now,
never deferred" is false of the tree the day it lands.** A cross-grid comparison is, by the rule's own definition, a
verification bar ("against ... another grid"). The tree defers four of them as strict red gates:
`test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn`,
`test_a_strike_breaches_a_thin_wall_the_same_at_every_rig`,
`test_a_fire_on_a_region_carved_hollow_heats_the_region_not_air` (test_act_validation.py) and
`test_a_fire_that_has_burned_its_fuel_stops_heating` (test_cross_tier.py), the last given a new `raises=` in this very
diff. Failure scenario: the next author who reads "never deferred" either deletes a red gate to stop deferring it
(losing the tracking), or writes a new failing cross-tier test and cannot follow both this rule and the red-gate rule,
which says known-broken behaviour gets a strict red gate. The rule cannot be followed as written, and the diff
contradicts itself. Fix (unverified): say what "never deferred" means against the red-gate rule, e.g. "a verification
miss is never a future bar and never waits on Maxim: it is a strict red gate plus a Known gap with a scheduled fix
step in this repo", or else list the four gates as the open exceptions with their fix steps.

## SHOULD-FIX

**S-1. CLAUDE.md::"Every bar is one of three kinds": "never a round number" is broken by existing bars, and nothing
tracks them.** `WOOD_FLAME_C = 2000.0` (test_cross_tier.py, two tests) and the integrity spread `<= 0.1`
(test_act_validation.py) are round numbers with no cited uncertainty. B30 covers only "each pre-registration and
design", not tests already in the tree. Scenario: a reviewer holding the new rule must flag every existing
cross-tier test as a breach, or quietly ignore the rule; either way the rule's guard (B30) does not say which. Fix
(unverified): scope the rule to bars written from now on and add the existing ones to B30 as a list, or derive them.

**S-2. CLAUDE.md::"A future bar is tracked, never dropped": its guard does not guard "strict".** The rule cites
`test_red_gates_are_strict_and_warnings_are_errors` "(strict)", but that test only asserts the ini's
`xfail_strict = True`. A marker passing `strict=False` overrides the ini (checked: reports XPASS, run passes). So a
future-bar gate written `xfail(strict=False, reason="Maxim #123")` stays green after Maxim's fix and the test never
"reruns at the original bar". Same hole under the red-gate rule. Fix (unverified): fold "no marker passes
`strict=False`" into B34's AST check, and until then cite B34 next to the test in this rule's guard.

**S-3. CLAUDE.md::"Known-broken behaviour gets a strict red gate" (and the 7debd5c message): the stated reason is
wrong.** "Without `raises=`, a gate whose module doesn't exist yet passes on the `ImportError` and stays green after
the fix." Check (c) above: once the module exists and the behaviour works, the body passes and strict xfail turns the
run red. It stays green only while the import keeps failing (the fix lands under another name or path, or an
unrelated exception keeps firing). The real hazard is that the gate never reaches its assertion, so it is a test that
cannot fail on the behaviour it names. Scenario: a reader trusting the stated reason concludes `raises=` matters only
for not-yet-written modules and omits it elsewhere, e.g. where a `TypeError` from a changed signature keeps a gate
green. Fix (unverified): "without `raises=`, any exception counts as the expected failure (a missing module, a
renamed function), so the gate can stay green without ever reaching the bar it names."

**S-4. CLAUDE.md::"A design document holds the contract": dead reference.** It cites
`docs/plans/long_term_features.md`, which is not in this tree or in origin/main; it exists only on the unmerged
branch `phase1/sem-stimulus` (e381295 and earlier). lint_guards checks only paths inside `Guard:`, so the lint passes.
Scenario: if this PR merges first, main's CLAUDE.md points at a file that does not exist, and the instruction "laws
stay swappable behind the contract" has no definition behind it. Fix (unverified): merge after sem-stimulus, or drop
the citation until then.

## NIT

**N-1. tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating: `raises=AssertionError` can't
tell the precondition from the bar.** The ignite `assert ... .success` also raises AssertionError (check (e)), so if
ignite broke, the gate would stay XFAIL. The rule says "the narrowest `raises=`", but for assert-based tests
AssertionError is the narrowest there is. Fix (unverified): make preconditions raise something other than
AssertionError (e.g. `if not ...: raise RuntimeError`) or check them in a separate passing test. The reason text's
"207,350 C ... by turn 50" also differs from today's 422,126 C peak over the test's 60 turns. That text predates this
diff and isn't wrong as stated, but it's worth refreshing.

**N-2. docs/code_review.md::"Design reviews" vs the new stop rule.** "A BLOCKER stops the build until it is folded or
overruled by the owner with a recorded reason". The new bullet has the author "propose moving the rest into the build
steps". It doesn't say that the owner's acceptance is the recorded overrule, so an author could read the proposal
itself as enough. Add a few words.

**N-3. CLAUDE.md::"Every bar is one of three kinds": "bar" is undefined.** Diff coverage (95%), size limits and word
budgets are bars of none of the three kinds. Add "a physics or behaviour bar".

B34's citation ("SEM design's final round, Executor S-F5") points at a review that is not in this tree. It can't be
checked from here, but the behaviour it claims (a) is true.
