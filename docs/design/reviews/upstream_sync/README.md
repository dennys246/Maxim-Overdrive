# Review of step 3, the upstream lane's first run (`phase3/upstream-sync`)

**Lenses** (the brief, `docs/plans/next_steps/3_upstream_sync.md`): Architecture, Wire integrity, Executor and
Bio-faithful integration. Bio-faithful integration asks of every upstream draft whether Maxim was searched first
(CLAUDE.md, B22). Round 1 reads commit `71bb320` against `origin/main` `1ed9caa`.

**The stop rule, written before round 1:**
- A BLOCKER or SHOULD-FIX is folded.
- If a fold changes text, one delta round reads only that fold's diff, and no round follows it. A BLOCKER the delta
  round finds goes to the owner for a ruling, not to another round.
- A NIT is the author's call: fixed in a fold or left. Either way it is recorded here with its reviewer's trigger, and
  it becomes a backlog row only if it is a rule waiting for a check (O80).
- Reviewers, not the author, set each finding's status (O25). The reports are kept verbatim beside this file.

## Round 1 folds (author's claims; the delta reviewer sets each status, O25)

Round 1 read `71bb320`; the reports are `round1_*.md` beside this file. #1787 merged during the round (`5bcc2cf0`, its
plan byte-identical to `29dda704`), so the fold also re-reads at `5bcc2cf0` and drops every "open, proposed".

| Finding | Severity | Author's fold |
|---|---|---|
| Bio B1 (OD-I13 missed Maxim's samplers in `src/`) | BLOCKER | correction posted on #1305 (UP3); OD-I13 row restated |
| Bio B2 (O29 against OD-A12's status) | BLOCKER | open questions (a) to (c) beside O29; (a) asked on #1787 (UP4) |
| E2, Arch SF-1 (statuses restate #1787) | SHOULD-FIX | each status cut to the plan's name, the release and a pointer to draft §3.7 |
| E1, Arch SF-2 (OD-A4 and OD-A7 Plan cells) | SHOULD-FIX | OD-A4 A-post, OD-A7 after the 1.4.0 cut, OD-A5 split; draft §3.7 matches |
| Arch SF-3 (O29 consequences) | SHOULD-FIX | as Bio B2 |
| Arch SF-4 (OD-I11 public row) | SHOULD-FIX | owner ruled keep, noting the draft advisory (UP5) |
| Bio SF-1 (OD-A20's reach) | SHOULD-FIX | wording corrected; open question (d); asked on #1787 (UP6) |
| Bio SF-2 (salience and the coarse readout untracked) | SHOULD-FIX | OD-A9 row names salience and gaze; open question (c) |
| Bio SF-3 (PainBus bio-mapping misread) | SHOULD-FIX | draft §3.5 quotes "with refractory gating" and argues body time |
| Bio SF-4 (lesson 42 overstated; no owner) | SHOULD-FIX | "from a plan and code, not a run"; binning readers named; open question (e) owns the save rule |
| Bio SF-5 (§3.1 "matches") | SHOULD-FIX | `exec_agent.py`'s SCN dict named as the exception |
| W1, E6, Arch N-2 (OD-A3 sites) | SHOULD-FIX | engage prompt and two raw-epoch tool results added; "examples, census authoritative" |
| W2 (OD-WC4 unplaced) | SHOULD-FIX | §7 places it; OD-WC1 after 1.4.0 noted |
| W3 (`LockstepTime`'s file) | SHOULD-FIX | cited at `scripts/survival_world/scripted_water.py` |
| E3 (the brief's awk false green) | SHOULD-FIX | not folded: the brief is outside this step's files. Open item for the next planning session (O79 part 5), which owns `next_steps/`; trigger: the lane's next run from this brief. The verified fix is `/^#+ /{h=$0}` |
| W4, Arch N-4 ("proposed") | NIT | moot after the merge; removed |
| W5 (README's OD-I3) | NIT | A5 added; status points at the roadmap row |
| W6, Bio NIT (OD-I11 "Filed") | NIT | "a draft private security advisory" |
| W7 (one host source as fact) | NIT | "must feed both (OD-A10, A-post)" |
| E4 (token greps can't see a reversal) | NIT | left; review is the guard; no trigger |
| E5, Arch N-1 (status in two places) | NIT | the README and issues draft point at the roadmap rows |
| E7 (stray capital in OD-I8) | NIT | fixed |
| E8 (no row carries its own trigger) | NIT | left: Phase 3's O76/O77 paragraph gives every open row "each Overdrive tag and each Maxim release" |
| E9 (unwrapped line) | NIT | rewrapped |
| Arch N-3 (lesson 42's save rule; `realtime_lanes_coop.md` contradiction) | NIT | open questions (d) and (e) |

B52 to B54 are released unused: no finding is a rule waiting for a check.

## Delta round (`delta.md`, on `858cc2b..e4d4df3`), and its folds

The delta reviewer set the statuses above in `delta.md` §1. Under the stop rule no round follows it. Its findings and
the author's folds, which no reviewer has read:
- **E2, Arch SF-1** (reopened): OD-A4's and OD-A5's statuses cut to the plan's name, the release and the pointer.
- **D1** (SHOULD-FIX): E3's deferral is recorded in the roadmap's tier A open items, with its owner and trigger.
- **NIT 1:** `config.py:733-738`, and the seed set at load; the #1305 comment already says so, and is left.
- **NIT 2:** draft §3.4 names `exec_agent.py`'s phase dict as the exception.
- **NIT 3:** fixed.
- **NIT 4:** the re-ask trigger is recorded beside the open questions.
