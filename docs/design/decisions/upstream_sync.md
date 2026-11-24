# Decisions of the upstream lane (`phase3/upstream-sync`)

<!-- A record (O79 part 3): owner rulings taken by the upstream lane. Rulings are never edited; a new ruling is a new
row. The first run (step 3, 2026-11-24) took UP1 and UP2. -->

| Id | Ruling | Who, date | Owner section | Status |
|---|---|---|---|---|
| UP1 | **OD-I11 goes to Maxim as a private security advisory, and OD-I13 as a comment on #1305.** The owner first said to file both as issues. Then the lane pointed out two of Maxim's rules: its `SECURITY.md` ("Do NOT open a public issue for security vulnerabilities") covers OD-I11's fail-open egress, and its `CONTRIBUTING.md` keeps issues for discrete defects, while OD-I13 is a feature ask that Maxim's world-clock session already placed on #1305. The owner chose the advisory and the comment. | owner, 2026-11-24 | `docs/roadmap.md` Phase 3, Issues now | live |
| UP2 | **Maxim's D9 session (maxim-46) is told the world-clock draft is current only after this step's PR merges,** so the notice cites `main`, not a branch under review. | owner, 2026-11-24 | `docs/maxim_upstream/world_clock_release_DRAFT.md` | live |
