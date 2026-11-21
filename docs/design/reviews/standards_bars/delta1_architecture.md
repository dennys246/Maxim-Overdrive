# PR 24 delta (phase1/standards-bars-2, origin/main...af6f255): Architecture lens

**Correction first.** My A1 (PR 21) said architecture.md's "coarsest rig lags" gap was carried as a strict red gate.
That was false. It is "Not gated yet" (`tests/test_cross_tier.py::test_fire_outcomes_agree_across_rigs`, the closing
comment) and is scheduled in Phase 2 (`docs/roadmap.md`, Phase 2, "Close the known gap"). That makes D1 below a
BLOCKER.

## Status of PR 21 findings (set from the tree)

| # | Status | Evidence |
|---|---|---|
| A1 | fixed (the wording) | The rule now says "never a future bar ... a strict red gate plus a Known gap ... fixed in this repo". The two readings are gone. The tree still contradicts it: see D1 |
| A2 | fixed | CLAUDE.md now asks for a separate passing test at the membrane (bridge values, on its clock) plus a note that Maxim is driven as briefed. B31 still has the old wording: see D3 |
| A3 | fixed | Scoped to physics and NPC outcome bars; a closed form's source is the scheme's error; older bars in B30. The re-derivation conflicts with "never loosens": see D4 |
| A4 | fixed | The test is "another module depends on it"; a checklist item cites its section. B32 still has the old criterion: see D3 |
| A5 | fixed | Both files: owner accepts, only mechanisms move, reviewer-deferred, contract BLOCKERs fold or are overruled |
| A6 | fixed | The `long_term_features.md` citation is dropped |
| A7 | fixed | The wordings now agree, and the charter is named as the home. CLAUDE.md still restates the procedure: see D5 |
| A8 | fixed | Wire integrity reads every section that uses a changed contract |
| A9 | fixed in CLAUDE.md and B34 | `strict=False` is refused in the rule and in B34. The reason now names "the Phase 3 item (and its issue once filed)". B31 still says "upstream issue": see D3 |

Counts: 9 earlier findings, all fixed in the rule text. New: BLOCKER 2, SHOULD-FIX 2, NIT 1.

## New findings

### BLOCKER

**D1. CLAUDE.md::"Every outcome bar ... three kinds" (Verification): the tree defers a verification miss to a later
phase with no red gate.** The rule says a verification miss "never waits on Maxim or a later phase, and is a strict
red gate plus a Known gap". Three places in the tree break it:
- The late-burn lag (crate integrity 0.55 at 0.2 m against 0.37–0.38 finer, after 150 turns) is a cross-grid miss.
  It is "Not gated yet" (`tests/test_cross_tier.py`), and its fix is a Phase 2 item (`docs/roadmap.md` Phase 2).
- The section header is still "**Known gaps (tracked, not gated yet):**" (`docs/architecture.md`).
- "Whether an imagined object fits ... can depend on the rig" is also a cross-grid miss, with no gate.

The thin-wall breach gate's reason names no fix, and architecture.md calls its treatment "an open decision". The rule
gives such a gap no trigger. Compare the future-bar rule, which needs a trigger, and TEMPORARY, which needs a phase.

Failure scenario: Phase 1 exits with the lag ungated. One session reads "never waits on a later phase" and blocks;
another reads the roadmap and treats it as deferred. Both cite a standing document.

Fix (unverified; the owner must choose one):
- (a) Give the late-burn lag a strict red gate (`raises=AssertionError`, 150 turns, a band derived per B30). Move its
  roadmap item into Phase 1, rename the header to "Known gaps", and require every verification Known gap to name the
  step that closes it.
- (b) Reword the rule to "never waits on Maxim; a later phase only with a strict red gate and a roadmap row naming
  the closing step". Then gate the lag and the imagination-fit gap under (b).

**D2. CLAUDE.md::"Known-broken behaviour gets a strict red gate": two of the four gates break the new precondition
clause.** The clause says "a precondition the gate needs raises something other than its `raises=` type". The fold
applied it only to the burnout gate. Two other gates still check their preconditions with plain `assert`, which
raises the `AssertionError` their markers expect:
- `test_the_fiercest_allowed_fire_...` calls `_burn_every_turn`, whose ignite check is an `assert ... .success`.
- `test_a_strike_breaches_a_thin_wall_...` calls `_block_strike`, whose strike check is `assert res.success`.

Failure scenario: an actions.yaml change makes `ignite` at `LIMITS.max_power_w` / `min_radius_m` refuse, for example
a new radius rule. The fiercest-fire gate then xfails on its precondition and stays green. It never measures the
spread it names. This is the exact failure the clause was written to prevent.

Fix (unverified): in both helpers, replace the precondition `assert` with
`if not ...: raise RuntimeError(...)`, as in `tests/test_cross_tier.py`. Prove it by deletion, as the fold's commit
did for the burnout gate. Non-gate callers of `_block_strike` keep the same behaviour (they still fail).

### SHOULD-FIX

**D3. docs/standards_backlog.md::B31 and B32 still describe the pre-fold rules.** These rows are the specs for future
checks, and they were not updated:
- B31 still says "whose reason names an upstream issue ... cites the world-side test". The rule now names the Phase 3
  item, with the issue once filed, and the membrane test plus a "driven as briefed" note.
- B32 still says "if only running can check it, it moves to the build checklist". That is A4's old criterion, which
  the rule replaced with "another module depends on it".

Failure scenario: someone implements B31's lint from the row. It demands an issue number in each future-bar reason,
so authors file Maxim issues early and skip B22's search (A9's original concern). The lint also accepts a world-side
test as evidence, which reopens A2. Under B32, a reviewer moves a running-only number that a client depends on into
the checklist (A4's scenario).

Fix (verified by reading): reword both rows to match the CLAUDE.md text at af6f255.

**D4. CLAUDE.md::"three kinds": "No band ever loosens" conflicts with re-deriving the B30 bars.** B30 lists "the
integrity spread `<= 0.1` in `tests/test_act_validation.py`" as a round-number bar to derive. That spread is the bar
of a strict red gate on a known miss (peak 0.19). If the derived band comes out wider, deriving it loosens a band and
can flip the gate without fixing the physics. The resolution rule
forbids that; the derivation rule requires it.

Failure scenario: a derived 0.2 band xpasses the gate, it is removed, and the divergence ships as "fixed".

Fix (unverified): "a re-derived bar may tighten. If it would loosen, the owner decides, and a red gate's bar is never
re-derived while it is red."

### NIT

**D5. CLAUDE.md::"Review finds; it doesn't design" names the charter as the home but still restates the whole
procedure.** The two copies agree today. The point of A7 was that two copies drift. Cut the CLAUDE.md sentence down
to "the rounds stop; the charter holds the procedure".

## Checked, no finding

- Each rule does one job: red gates, bar kinds, future bars, the design contract and review each have one home. Every
  rule ends in a Guard and a backlog row (B30–B35).
- The burnout gate's `RuntimeError` precondition passes ruff (ran `ruff check tests/test_cross_tier.py`).
- All four `xfail`s pass `raises=AssertionError`. The doorway gate's `if res.success` is intentional: a refusal
  xpasses and fails strict.
