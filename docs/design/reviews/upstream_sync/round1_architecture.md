# Architecture review: `phase3/upstream-sync`, diff `1ed9caa..71bb320`

Reviewer lens: Architecture. Read-only. Maxim read through git only: `f145e27b` (origin/main) and `29dda704` (PR #1787 head, still the head per `gh pr view 1787`).

## What I checked and found sound

- **Scope.** The diff touches only `docs/maxim_upstream/{README,issues_now_DRAFT,world_clock_release_DRAFT}.md`, `docs/roadmap.md` (Phase 3 hunks only, lines 162 to 264), `docs/design/decisions/upstream_sync.md` (new, UP1 and UP2) and `docs/lessons_maxim_in_games.md` (lesson 42 only). All are on the brief's list. The roadmap rows OD-I1, OD-I3, OD-I5, OD-I6 and OD-I7 are byte-unchanged (no `^[-+]| OD-I(1|3|5|6|7) ` lines in the diff).
- **Exit-test greps** (run by hand, without the venv steps): draft 2,272 words against 3,146 on base; every id and keyword is present; the `read at Maxim origin/main` line is there; `setprofile` appears only under §3.3 *Superseded*.
- **Statuses against `gh`:** #1305, #1782 and #984 are open with milestone 1.3.5; #1769 is open with no milestone; #1684 is closed; #1787 is open. The `or time.time()` count is 0 in all three OD-I1 files at `f145e27b`. The cited lines check out at `f145e27b`: `tool_dispatch.py:1515` `exec_start`, `:698` `_observe_energy_cost`, `prompt_builder.py:1202`, `context_pool.py:468`/`:493`, `openai_backend.py:273`. The OD-I13 comment exists on #1305 (2026-11-24T16:49Z). #1361 Q4 and D9 are on Maxim main as cited.
- **Supersessions** (OD-H6, OD-A20, the AST ban, the 1.4.0 RNG ruling, the split clock) are applied or marked with pointers. The draft states that "the row wins" over it.

## Findings

### SF-1 (SHOULD-FIX): #1787's discussion is restated in three Overdrive places, beyond O76's form
**Anchors:** `docs/roadmap.md::Phase 3 tier A` (the OD-A2 to OD-A7 status cells, OD-A12), `::Issues now` (OD-I8, OD-I13); `docs/maxim_upstream/world_clock_release_DRAFT.md::§3.1, §3.2, §3.5, §3.7, §7`; `docs/lessons_maxim_in_games.md::42`.

**Defect.** O76 says a Phase 3 row "cites the issue or PR by number and states only which release holds the fix and which release the lock is on. It never restates Maxim's discussion." The brief's steps 3 and 4 repeat this ("and nothing more"). The new status cells restate #1787's content: which halves move where, D-WC2 revised, "SCN registration on the host calendar, so the phase source does not move", D-WC5's reasoning, and #1361 Q4's wording on OD-I8. Maxim's world-clock session also wrote the OD-I13 status. The draft's §3.7 table repeats the same placements. As a result, every placement in #1787 has two Overdrive copies plus Maxim's own, and B48, the only planned check, is deferred.

**Failure scenario.** #1787 is an open plan PR under review, and its D-WC2 was already revised once on 2026-11-24. Suppose a delta round on #1787 moves the `SensorReading` stamp back into A-pre, or splits D-WC6. The roadmap's OD-A4 and OD-A5 cells, draft §3.2, §3.5 and §3.7, and lesson 42 then all describe a plan that no longer exists. Nothing goes red until the next lane run, and that run has to diff the PR against three copies. This is the drift O76 was written to stop (lesson 39).

**Fix (unverified).** In each roadmap cell, keep the O76 form plus a single pointer, for example: "#1787 (open plan PR, read at `29dda704`) proposes: OD-A4 to A-post, see its §Placements; in no release". Keep the placement detail in one Overdrive place, the draft's §3.7, which already says it holds proposals. Move the substance of OD-I13's status (what Maxim's session wrote) out of the row.

### SF-2 (SHOULD-FIX): the tier A Plan column contradicts rulings that are already decided, and the table is the one that "rules"
**Anchors:** `docs/roadmap.md::Phase 3 tier A::OD-A7`, `::OD-A4`; `docs/lessons_maxim_in_games.md::42`.

**Defect.**
- **OD-A7.** Its Plan cell still reads `A-pre`, while the same row records the decided ruling "a new release-gate item after the 1.4.0 cut" (Maxim's owner, 2026-11-19). That ruling is not a #1787 proposal: it predates #1787, and #1787 only cites it. Draft §3.7 prints "Plan (tier A): A-pre | after the 1.4.0 cut", so the draft follows a stale cell while also saying the row wins.
- **OD-A4.** Its tool-duration half is `A-pre`. The roadmap's own definition of A-pre is "touching no fenced file", and OD-A8 in the same table lists `tool_dispatch` among the fenced files. Lesson 42 concedes the point ("Our own OD-A4 row had the same blind spot ... put a tool's duration, a read in the fenced `tool_dispatch.py`, in A-pre"), yet the row still says A-pre. This is Overdrive's own correction, and it does not depend on #1787 merging.

**Failure scenario.** The next lane run, or Maxim's D9 or A-post session, reads the table as authoritative (the draft says "Where this draft and a row differ, the row wins"). It sees OD-A7 and the tool duration as A-pre asks and either re-argues them into A-pre or treats #1787's placement as a deviation to push back on. That is the opposite of the owner's ruling and of our own lesson.

**Fix (unverified).** Set OD-A7's Plan cell to "after the 1.4.0 cut (release-gate item)". Split OD-A4's tool duration into its own Plan value, `A-post` (fenced file, with B2), or a new row. Leave the stamp half `A-pre` with "proposed A-post in #1787" until #1787 merges, so that what is decided and what is only proposed stay distinct.

### SF-3 (SHOULD-FIX): consequences for Phase 4's O29 subset are left unraised
**Anchors:** `docs/roadmap.md::Tier A: "The subset Phase 4's first NPC needs (O29)"`; `world_clock_release_DRAFT.md::§7`.

**Defect (a): OD-A4's stamp half now depends on AgentHome.** #1787 §Placements puts OD-A4's stamp half, which includes the Hippocampus capture and access stamps and the `SensorReading` stamp, "with AgentHome (OD-A12) / A-post ... with a clock-domain marker written into the home" and a `schema_version` bump. O29's subset includes OD-A2 to OD-A11 but only "OD-A12's host-driven ConceptExtractor thread", and it says explicitly that "OD-A12's store routing waits for two agents in one process". The diff records the move in the OD-A4 and OD-A12 cells but never asks whether O29 still holds.

**Defect (b): OD-WC1 has no plan that can pass it.** Draft §7 says "#1787 ... leaves OD-WC1, OD-WC3 and OD-WC7 to A-post". A-post lands with 1.3.6. #1787 excludes WC1 from A-pre because of ids (D-WC1), and ids (OD-A7) land after the 1.4.0 cut. So A-post cannot pass WC1 as written, since WC1 digests ids. Yet O29 names OD-WC1 as a Phase 4 exit dependency.

**Failure scenario.** Maxim ships A-post in 1.3.6. Phase 4 starts on the O29 subset, which it believes is complete. Its first NPC's persisted capture stamps are still on the wall, because the marker rides with AgentHome, which O29 said Phase 4 does not wait for. OD-WC1 is then red for a reason no row names. Alternatively, Maxim's A-post session takes WC1 as its exit and either cannot close it or quietly drops the id half.

**Fix (unverified).** Raise both to the owner as a ruling (UP3) instead of folding them silently:
- either add "OD-A12's clock-domain marker and the stamp half's reader sets" to O29's subset, or push back on #1787 that the marker can land without store routing (a question on the PR, through Maxim's process);
- in draft §7, place OD-WC1 after OD-A7 (after the 1.4.0 cut), or split it into a stamps half (A-post) and an ids half (after the cut), and send that as a comment on #1787's "A-post picks them up".

### SF-4 (SHOULD-FIX, needs an owner ruling): OD-I11 is now a private advisory, but its row in a public repo still gives the whole failure
**Anchors:** `docs/roadmap.md::Issues now::OD-I11`; `docs/design/decisions/upstream_sync.md::UP1`.

**Defect.** UP1 routes OD-I11 to a private advisory because Maxim's `SECURITY.md` says "Do NOT open a public issue for security vulnerabilities". The same diff edits OD-I11's row, in a repo that `gh` reports as PUBLIC, to add the GHSA id, and it leaves in the row the exact trigger: a provider of type `openai` with a blocked `base_url`, keyed on the name rather than the type, falls back to api.openai.com, with file and line, and is still live at `openai_backend.py:273`. OD-I5 sets the house pattern for an advisory: "details in private notes, not here". The row now contradicts itself, and it contradicts UP1's own rationale.

**Failure scenario.** A reader of Overdrive's public roadmap gets a working recipe for an egress fail-open in pymaxim 1.3.4 and in `origin/main`, while Maxim handles it as embargoed.

**Honest limit.** The detail has been on `main` since 2026-11-22, and lesson 36 carries it too, so editing the row now does not unpublish it from history. The owner should decide, possibly with Maxim's advisory, whether to reduce the row to the OD-I5 form. This must not be decided silently either way.

**Fix (unverified).** Bring it to the owner. If approved, rewrite OD-I11 in OD-I5's form ("a security issue in backend egress, held by Maxim as private advisory GHSA-...; details in private notes") and trim lesson 36's line to match. Lesson 36 is outside this step's files, so that part becomes an open item.

### N-1 (NIT): a second copy of OD-I1's status, which step 2 owns
**Anchors:** `docs/maxim_upstream/README.md::table, issues_now row`; `docs/maxim_upstream/issues_now_DRAFT.md::Status (O76)`.

O79(2) gives the OD-I1 row to step 2. The README and the issues draft now restate its status ("the lock gets it when it reaches the release holding #1773"). Today they agree, but when step 2 lands O75's red gate and the 1.3.4 lock, there are two copies to keep in step. **Fix (unverified):** point to the roadmap row instead of restating it.

### N-2 (NIT): draft §3.4 "Sites on `f145e27b`" is incomplete
**Anchor:** `world_clock_release_DRAFT.md::§3.4`.

`agents/prompt_builder.py::_build_engage_prompt` also calls `datetime.now()` (`:2389` at `f145e27b`; verified with `git show f145e27b:src/maxim/agents/prompt_builder.py | grep -n datetime.now`). The section also omits the two raw-epoch tool results #1787 names (`_format_episodic_memory`, `SceneSummaryTool.execute`). PR 0's census is authoritative, but this list claims to be the sites at a given sha. **Fix:** add these sites, or say "examples; #1787's PR 0 census is the list".

### N-3 (NIT): lesson 42's consequence has no owner or trigger, and an Overdrive design rule it touches is now contradicted
**Anchors:** `docs/lessons_maxim_in_games.md::42` (consequence); `docs/design/realtime_lanes_coop.md::§3.2`.

- Lesson 42 says "an Overdrive save that holds an agent home has to say which clock its stamps count, and refuse a mismatch". That is a contract for Overdrive's save format, but it has no roadmap or backlog row with an owner and trigger, so it lives only in the lesson.
- `realtime_lanes_coop.md` §3.2 says "NPCs must not run against the world clock with their SCN on host time". #1787's gap list flags that this stays true (OD-A20 declined, D-WC2 revised), while O29 accepts it as a known divergence. This contradiction predates the diff, but #1787 hands it to "the upstream lane" to track.

Both files are outside this step's list, so each should become an open item (owner and trigger), not an edit. **Fix (unverified).**

### N-4 (NIT): "proposed" is applied unevenly
**Anchors:** `world_clock_release_DRAFT.md::§2 G17 row, §8 Q3`; roadmap OD-A2, OD-A3 and OD-A4 cells.

- The draft labels "G17 stands" as "proposed in #1787". G17 is Maxim's standing decision on `main`, and #1787 only cites it.
- The roadmap cells say "taken by #1787" and "moved out of A-pre by #1787" without "proposed". That reads as decided, while the draft says these moves are proposed until the PR merges.

**Fix:** label decided items as decided, and say "proposed in #1787" in the roadmap cells too (this folds naturally into SF-1).

## Summary
No BLOCKER. Four SHOULD-FIX and four NIT.
- **SF-1:** #1787's discussion restated beyond O76's form, in three Overdrive copies.
- **SF-2:** the Plan column contradicts decided rulings: OD-A7, and OD-A4's tool duration.
- **SF-3:** O29 and OD-WC1 consequences left unraised; this needs an owner ruling, and possibly a pushback on #1787.
- **SF-4:** OD-I11's public detail against UP1's private-advisory route; owner ruling.

Scope, the rows step 2 owns, the exit-test greps and the Maxim statuses all check out against the tree and `gh`.
