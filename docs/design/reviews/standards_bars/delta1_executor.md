# PR 24 delta round (origin/main...af6f255): Executor lens

Commits 32e1ce8 (requires `raises=`) and af6f255 (the fold of PR #21's review). Reader: Executor.
New findings: BLOCKER 1, SHOULD-FIX 0 (S-1 stays open), NIT 2.

## Status of the earlier findings (read from the tree at af6f255)

| Finding | Status | Evidence |
|---|---|---|
| B-1 "verification never deferred" contradicts four red gates | **fixed** | CLAUDE.md now says a verification miss "is a strict red gate plus a Known gap with its numbers, fixed in this repo" (A1 (a)). All four gates have a Known gap in docs/architecture.md (fuel, mid-burn divergence, thin-wall breach, hollow centroid). Each fix is in this repo: the Phase 1 fuel model, the region id array (world_v2 step 3), and the outcome-margin question (world_v2 §3.3). None waits on Maxim |
| S-1 old round-number bars untracked | **open** | B30 now lists some of them, and CLAUDE.md says "older round-number bars are listed in B30". The list is incomplete and misplaces one: (a) `WOOD_FLAME_C = 2000.0` is defined twice, in `tests/test_cross_tier.py` (two tests) and in `tests/test_act_validation.py` (used at the fiercest-fire gate), and B30 names only the first. (b) Missing round bars: `test_cross_tier.py` onset spread `<= 0.1 * min(onsets)` and `integrity < 0.7` / `< 0.5`; `test_act_validation.py` crater `rel=0.25`; `test_heat.py` `_error(...) < 0.02` (a closed form, which is exactly the "scheme's error at the spacing" case the rule now names). What's missing: a complete list, or a sentence scoping B30's list to "examples" |
| S-2 the guard does not guard `strict` | **fixed** (the rule), check **deferred** as B34 | The rule now says "never `strict=False`" and cites B34. B34 covers both `raises=` and `strict=False` via an AST read of the markers. No marker in `tests/` passes `strict=False` today (grepped). Trigger: B34 is `open`, with no step named. Acceptable as a backlog row |
| S-3 the stated reason for `raises=` is wrong | **fixed** in CLAUDE.md | The new text ("any exception counts ... can stay green without ever reaching the bar it names") is correct. The 32e1ce8 message still carries the old reason ("stays green after the fix"). History can't be rewritten without a force-push, so I accept this. The af6f255 message records the correction |
| S-4 dead `long_term_features.md` citation | **fixed** | Gone from CLAUDE.md and docs/code_review.md (grepped) |
| N-1 the burnout gate's precondition is indistinguishable from its bar | **fixed** for that gate | Verified: in a `git archive af6f255` copy, ran the gate (XFAIL). Planted `power_w: -1.0` in both ignite calls and got FAILED with `RuntimeError` at `test_cross_tier.py:87`. The commit's deletion proof holds. The rule it generalised into is broken elsewhere; see D-B1 |
| N-2 the owner's acceptance is not stated as the overrule | **fixed** | docs/code_review.md "When the rounds stop": "the owner accepts it, which is the recorded overrule" |
| N-3 "bar" undefined | **fixed** | "Every outcome bar on physics or NPC behaviour"; process bars and determinism are excluded |

## Checks run

- `scripts/lint_standards.py`: PASS, 0 findings, 19 enforced by a check, 27 by review. This matches the commit.
- `tests/test_tooling_config.py tests/test_lint_standards.py`: 192 passed. This matches the commit.
- Worktree left clean (`git status --short` empty). The scratch tree is under `pr24_delta/scratch/`.

## BLOCKER

**D-B1. CLAUDE.md::"Known-broken behaviour gets a strict red gate": the new clause "a precondition the gate needs
raises something other than its `raises=` type" is broken by two of the four gates the day it lands.**

- `tests/test_act_validation.py::_burn_every_turn` checks its precondition with
  `assert m["structure"].execute("ignite", ...).success`. It serves
  `test_the_fiercest_allowed_fire_has_the_same_outcome_at_every_rig_on_every_turn`.
- `_block_strike` checks `assert res.success`. It serves `test_a_strike_breaches_a_thin_wall_the_same_at_every_rig`.
- Both gates carry `raises=AssertionError`.

Failure scenario, verified: in the scratch copy I planted `power_w: -1.0` in `_burn_every_turn`'s ignite and
`energy_j: -1.0` in `_block_strike`'s strike. Both actions are refused. Both gates still report **XFAIL** with
their original reasons (`2 xfailed`). So if ignite or strike broke on the shipped path, these two gates would stay
green. Each is a test that cannot fail on the bar it names, which the charter rates a BLOCKER, and the diff's own
new rule says so. It is the same pattern as B-1: a rule the tree contradicts on landing. The fold fixed it only in
the gate N-1 named.

The third gate, `test_a_fire_on_a_region_carved_hollow_heats_the_region_not_air`, branches on `if res.success`, so a
refusal turns it into XPASS(strict), which goes red. It complies.

Fix (unverified): in the two helpers, replace each precondition `assert` with
`if not ...: raise RuntimeError(...)`, as the burnout gate now does, and rerun the same plants. The helpers'
passing callers would then fail with RuntimeError instead of AssertionError on a refusal. That is still a failure,
so it is harmless. Alternatively, restrict the clause to gates written from now on and list these two in B34. That
is weaker, and the fix is four lines.

## NIT

**D-N1. docs/standards_backlog.md::B31 lags the rule it guards.** CLAUDE.md now says the reason names "the Phase 3
item (and its issue once filed)". The evidence it requires is "a separate, passing test" at the membrane plus "a note
that Maxim is driven as its brief says". B31 still reads "whose reason names an upstream issue" and "the row cites
the world-side test that passes". Scenario: a lint built from B31 matches red-gate reasons on issue numbers. It
misses a future-bar gate whose Phase 3 item has no issue yet (which the rule allows), and it never checks for the
"driven as briefed" note. Fix (unverified): update B31's text to match.

**D-N2. CLAUDE.md::"A future bar is tracked, never dropped": "a note that Maxim is driven as its brief says" can't
be followed as written.** "Its brief" is undefined: is it Maxim's README, a plan, the bridge's docstring? The rule
also doesn't say where the note lives: the gate reason, the roadmap row, or the test. Scenario: two authors put it
in different places, and B31's eventual lint can find neither. Fix (unverified): name the document and the location,
e.g. "the roadmap row cites the Maxim doc it follows".
