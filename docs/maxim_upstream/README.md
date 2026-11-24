# Drafts for Maxim

These are drafts written in Maxim Overdrive for Maxim's own process. Nothing in them is built or claimed here, and
nothing here is ever patched into Maxim from this repo (CLAUDE.md, "Keep Maxim untouched"). Each one moves to Maxim
only through Maxim's process:
- **an issue** for a discrete defect, actionable now, with a definite done state;
- **a plan** with a three-lens plan review (Executor, Architecture, Wire integrity) and a three-lens code review per PR;
- **an experiment** with a four-lens design review, a frozen pre-registration and a ledger row.

Game runs never go on Maxim's ledger.

**Maxim tree read:** each draft names the `origin/main` it was read against (first `7084f561`, 2026-11-16); the statuses
below were read at `f145e27b` (2026-11-24). Citations are `file::symbol` where a symbol exists, with line numbers only
as a hint (Maxim's rule: line numbers drift, symbols hold). Re-check against a fresh fetch before filing anything.

**Ids.** Everything Overdrive proposes carries an `OD-` prefix (`OD-A3`, `OD-X1`), because Maxim already uses `T1`,
`T2` (1.4.0 release thresholds), `E1`–`E3` (experiments), `S0`–`S6` (#1361's slices), `B1`–`B4` (the floor chain) and
`A1`/`A2` (1.3.3's NAc audit). Maxim may reassign them when it accepts an item.

## What goes where

| Draft | Venue | Overdrive roadmap ids | Status |
|---|---|---|---|
| [issues_now_DRAFT.md](issues_now_DRAFT.md) | two issues | OD-I1, OD-I2 | OD-I1: #1684, fixed by #1773, in no release; the lock gets it at the release holding #1773. OD-I2: not filed (a docstring nit, Maxim's answer) |
| [embeddable_agent_DRAFT.md](embeddable_agent_DRAFT.md) | plan | OD-A10 to OD-A12, OD-A14, OD-A15, OD-A17, OD-A18, OD-I3 | Maxim's candidates A1, A4, B1, B2 (`overdrive_refactor_candidates.md`); no plan, nothing in a release |
| [world_clock_release_DRAFT.md](world_clock_release_DRAFT.md) | two plans: A-pre (own clock) and A-post (with 1.3.6) | OD-A1 to OD-A8 | A-pre: Maxim plan PR #1787, open; A-post after the fence; nothing in a release |
| [default_network_stepped_DRAFT.md](default_network_stepped_DRAFT.md) | plan, coordinated with #1263's remainder | OD-A9 | not filed; A-post |
| [propose_settle_amendment_DRAFT.md](propose_settle_amendment_DRAFT.md) | amendment to `tool_failure_credit.md` (#1200) | OD-A16 | in cand. B2 (#1150), open; after #1200 |
| [time_sense_DRAFT.md](time_sense_DRAFT.md) | plan, plus two experiment drafts (OD-X1, OD-X2) | OD-B8 to OD-B13 | not filed; tier B |
| [sem_breaking_change_plan_DRAFT.md](sem_breaking_change_plan_DRAFT.md) | plan (SEM refinement, additive in 1.x) | OD-C1 to OD-C10 | not filed; tier C |
| [hybrid_1_5_line_DRAFT.md](hybrid_1_5_line_DRAFT.md) | Overdrive's contribution to Maxim's hybrid arbitration line | OD-H1 to OD-H4 | not filed; OD-H2 is cand. C2 |
| [decisions_entry_DRAFT.md](decisions_entry_DRAFT.md) | a `DECISIONS.md` entry for Maxim's owner | none | not filed; its question answered yes (Maxim's owner, 2026-11-19) |
| [exp64_cradle_conduct_prereg_DRAFT.md](exp64_cradle_conduct_prereg_DRAFT.md) | experiment (Exp 64) | Phase 4 exit | not filed |

`sem_breaking_change_plan_DRAFT.md` keeps its file name because other Overdrive documents link to it. Its content is
now an additive SEM refinement plan: under Maxim's own CC3 text, only one change needs a breaking path, and that one
is offered opt-in.

## The one sentence behind all of it

Overdrive needs a Maxim agent that **a host drives**: the host calls it with world time and a frame, it returns what
it wants to do as values, and it never runs a loop, a thread, a clock, a model call or a tool of its own. Today
Maxim's agent owns all of those. The world clock drafts give it the host's time; the embeddable agent draft gives
the host its loop, its model calls, its tools and its storage.
