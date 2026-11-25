# Decisions of the upstream lane (`phase3/upstream-sync`)

<!-- A record (O79 part 3): owner rulings taken by the upstream lane. Rulings are never edited; a new ruling is a new
row. The first run (step 3, 2026-11-24) took UP1 to UP6. -->

| Id | Ruling | Who, date | Owner section | Status |
|---|---|---|---|---|
| UP1 | **OD-I11 goes to Maxim as a private security advisory, and OD-I13 as a comment on #1305.** The owner first said to file both as issues. Then the lane pointed out two of Maxim's rules: its `SECURITY.md` ("Do NOT open a public issue for security vulnerabilities") covers OD-I11's fail-open egress, and its `CONTRIBUTING.md` keeps issues for discrete defects, while OD-I13 is a feature ask that Maxim's world-clock session already placed on #1305. The owner chose the advisory and the comment. | owner, 2026-11-24 | `docs/roadmap.md` Phase 3, Issues now | live |
| UP2 | **Maxim's D9 session (maxim-46) is told the world-clock draft is current only after this step's PR merges,** so the notice cites `main`, not a branch under review. | owner, 2026-11-24 | `docs/maxim_upstream/world_clock_release_DRAFT.md` | live |
| UP3 | **The OD-I13 comment on #1305 is corrected in a follow-up comment, not edited in place.** The first comment searched only `docs/plans` and the issues, and missed the samplers Maxim already has in `src/` (round 1, Bio-faithful BLOCKER 1). The correction cites them and narrows the ask to three gaps. | owner, 2026-11-24 | `docs/roadmap.md` OD-I13 | live |
| UP4 | **The three Phase 4 gaps that Maxim's A-pre plan opens are recorded as open questions beside O29, and one is asked on #1787.** (a) The stamp half lands with OD-A12, which the subset leaves out (asked on #1787); (b) OD-WC1 can't pass before the 1.4.0 cut; (c) Phase 4's first NPC has no coarse time readout. O29 itself waits for the owner. | owner, 2026-11-24 | `docs/roadmap.md` tier A, open questions | live |
| UP5 | **OD-I11's row keeps its text,** which was public before the advisory, and says the advisory is a draft. | owner, 2026-11-24 | `docs/roadmap.md` OD-I11 | live |
| UP6 | **Keeping the SCN's phase source on the host calendar is not described as covered by OD-A20's decline.** Our wording is corrected, the stale design lines (`npcs_and_sem.md` §3.3 and §12.2, `realtime_lanes_coop.md` row 10) become an open item for those documents' next session, and #1787 is asked which calendar SCN registration and the EC hash bin on once the stamps move. | owner, 2026-11-24 | `docs/roadmap.md` tier A, open question (d) | live |
