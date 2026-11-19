# Drafts for Maxim

These are drafts written in Maxim Overdrive for Maxim's own process. None of them is filed, built or claimed, and
nothing here is ever patched into Maxim from this repo (CLAUDE.md, "Keep Maxim untouched"). Each one moves to Maxim
only through Maxim's process:
- **an issue** for a discrete defect, actionable now, with a definite done state;
- **a plan** with a three-lens plan review (Executor, Architecture, Wire integrity) and a three-lens code review per PR;
- **an experiment** with a four-lens design review, a frozen pre-registration and a ledger row.

Game runs never go on Maxim's ledger.

**Maxim tree read:** `origin/main` at `7084f561` (2026-11-16, fetched that day). Every citation in these drafts is to
that tree, as `file::symbol` where a symbol exists, with line numbers only as a hint (Maxim's rule: line numbers drift,
symbols hold). Re-check against a fresh fetch before filing anything.

**Ids.** Everything Overdrive proposes carries an `OD-` prefix (`OD-A3`, `OD-X1`), because Maxim already uses `T1`,
`T2` (1.4.0 release thresholds), `E1`–`E3` (experiments), `S0`–`S6` (#1361's slices), `B1`–`B4` (the floor chain) and
`A1`/`A2` (1.3.3's NAc audit). Maxim may reassign them when it accepts an item.

## What goes where

| Draft | Venue | Overdrive roadmap ids | Status |
|---|---|---|---|
| [issues_now_DRAFT.md](issues_now_DRAFT.md) | two issues | OD-I1, OD-I2 | ready to file after a re-check |
| [embeddable_agent_DRAFT.md](embeddable_agent_DRAFT.md) | plan | OD-A10 to OD-A15 | the heart of tier A; Phase 4 waits on it |
| [world_clock_release_DRAFT.md](world_clock_release_DRAFT.md) | two plans: A-pre (own clock) and A-post (with 1.3.6) | OD-A1 to OD-A8 | tier A |
| [default_network_stepped_DRAFT.md](default_network_stepped_DRAFT.md) | plan, coordinated with #1263's remainder | OD-A9 | tier A, A-post |
| [propose_settle_amendment_DRAFT.md](propose_settle_amendment_DRAFT.md) | amendment to `tool_failure_credit.md` (#1200) | OD-A16 | tier A, after #1200 and 1.3.6 |
| [time_sense_DRAFT.md](time_sense_DRAFT.md) | plan, plus two experiment drafts (OD-X1, OD-X2) | OD-B8 to OD-B13 | tier B, earned by experiment |
| [sem_breaking_change_plan_DRAFT.md](sem_breaking_change_plan_DRAFT.md) | plan (SEM refinement, additive in 1.x) | OD-C1 to OD-C10 | tier C |
| [hybrid_1_5_line_DRAFT.md](hybrid_1_5_line_DRAFT.md) | Overdrive's contribution to Maxim's hybrid arbitration line | OD-H1 to OD-H4 | tier C |
| [decisions_entry_DRAFT.md](decisions_entry_DRAFT.md) | a `DECISIONS.md` entry for Maxim's owner | none | filed with the first plan PR |
| [exp64_cradle_conduct_prereg_DRAFT.md](exp64_cradle_conduct_prereg_DRAFT.md) | experiment (Exp 64) | Phase 4 exit | earlier draft, not revised in this pass |

`sem_breaking_change_plan_DRAFT.md` keeps its file name because other Overdrive documents link to it. Its content is
now an additive SEM refinement plan: under Maxim's own CC3 text, only one change needs a breaking path, and that one
is offered opt-in.

## The one sentence behind all of it

Overdrive needs a Maxim agent that **a host drives**: the host calls it with world time and a frame, it returns what
it wants to do as values, and it never runs a loop, a thread, a clock, a model call or a tool of its own. Today
Maxim's agent owns all of those. The world clock drafts give it the host's time; the embeddable agent draft gives
the host its loop, its model calls, its tools and its storage.
