# Executor review: step 3, `phase3/upstream-sync`, round 1 (`1ed9caa..71bb320`)

Reviewer lens: Executor. Read only; nothing in either repo was edited. Worktree HEAD is `ec2adbe` (adds only
`docs/design/reviews/upstream_sync/README.md` on top of `71bb320`). `origin/main` is `1ed9caa`, and its copy of the
draft is the same as `1ed9caa`'s, so the word-count baseline is the right one.

## 1. The exit test, run from the worktree

I ran the brief's block as written, in `bash -c` with `set -e`. Output, verbatim:

```
check_plan: PASS (0 finding(s))
exit=0
```

Word counts: draft 3,146 on `origin/main`, 2,272 now. It shrank by 874 words.

## 2. Can each check go red? (mutations on scratch copies, never the tree)

I copied the block into a scratch script that takes `F` (a scratch copy of the draft) and keeps the baseline as
`git show origin/main:<draft>`. The `check_plan`/`lint_standards` line is skipped for the copies, since it reads the
tree and not `F`. The unmutated copy exits 0.

| Mutation | Result |
|---|---|
| `OD-A4` renamed to `OD-AX` everywhere | `missing OD-A4`, exit 1 |
| `#1769` removed | `missing #1769`, exit 1 |
| `OD-I8` removed | `missing OD-I8`, exit 1 |
| the "read at Maxim `origin/main`" line dropped | exit 1 (silent: the bare `grep -qE` fails under `set -e`) |
| `sys.setprofile` added under a new `## Plain section` | `setprofile outside a superseded section: 189`, exit 1 |
| 900 words appended | exit 1 (silent, from the `test`) |
| `OD-H6` removed | `missing OD-H6`, exit 1 |
| the old draft (`origin/main`) run as `F` | `missing OD-I8`, exit 1 |

So each check can fail. I also counted the supersession tokens in the old draft: `OD-H6`, `OD-A20`,
`perceived-time port`, `machinery clock`, `1.4.0` and `#1305` each appear 0 times on `origin/main` and at least once
now. The five supersession greps are therefore not satisfied by the old text. (`OD-A3` to `OD-A8` were already in the
old draft, so those greps check coverage only.)

There are two false greens, both shown below (findings E3 and E4).

## 3. The brief's Order, checked against the diff

- **The five supersessions.**
  1. The split clock is applied in §1 and §3.1.
  2. The AST ban is in §3.3, which is marked *Superseded*. The one remaining `setprofile` (line 85) sits under that
     heading.
  3. OD-A7 is applied in §3.6 ("after the 1.4.0 cut, not a widened `1305.owned-rng`").
  4. OD-H6 is marked superseded in the §4 table.
  5. OD-A20 is marked declined in §4, with the calendar recast as perceived time.

  OD-A4's tool duration (§3.2) and OD-I8 (§3.7) were added. All five supersessions are applied or marked, and the two
  gaps are filled.
- **The draft shrank** (3,146 to 2,272 words).
- **No lock version in a draft.** I grepped `docs/maxim_upstream/` for `1.3.3`. The only hits are historical (1.3.3's
  breaking patch, the pulse pin, and the README's id note), none of them the lock. The world-clock draft never
  mentions the lock. OD-I1 reads "the lock gets it at the release holding #1773", which is the form the brief asks for.
  `constraints/py3.12.txt` pins `pymaxim==1.3.3`, and nothing in the diff restates that.
- **Ids.**
  - Lesson 42 is new and was unused on `origin/main`. It sits in the "Time" section, and the file groups lessons by
    topic, so that placement is consistent.
  - `docs/standards_backlog.md` is untouched, so B52 to B54 are unused. The brief says to release unused ids in the PR
    body. That can't be checked yet.
  - The decision log uses UP1 and UP2 as the brief says.
- **Files touched:** `docs/design/decisions/upstream_sync.md`, `docs/lessons_maxim_in_games.md`,
  `docs/maxim_upstream/README.md`, `docs/maxim_upstream/issues_now_DRAFT.md`, the world-clock draft, and
  `docs/roadmap.md`. All four roadmap hunks fall between lines 159 and 266, inside Phase 3 (lines 148 to 357). After
  `71bb320` the branch also adds `docs/design/reviews/upstream_sync/README.md`. Every file is on the brief's list.
  OD-I1, I3, I5, I6 and I7 are untouched, which respects step 2's ownership.
- **Spot checks of Maxim citations at `f145e27b`.** All of these match:
  - `tool_dispatch.py`: `execute_and_learn` at `:1436`, `exec_start` at `:1515`, `_observe_energy_cost` at `:698`;
  - `body.py:293` `time.time()`;
  - `prompt_builder.py:1202` `datetime.now()`;
  - `context_pool.py:468/:493` `localtime`;
  - `openai_backend.py:273`;
  - `make_agent_rng(base_seed, agent_id)`;
  - `semantic.py:205` `or 42`;
  - `nac.py:1163` `time_ns`.

  #1787's head `29dda704` exists and carries D-WC1 to D-WC7 and the "~54 years" line that lesson 42 cites. #1787's
  table records `llm_fallback`'s canned time answers as gone with #1689.

## 4. Budgets

- World-clock draft: 3,146 to 2,272 words (it shrank).
- New documents: `decisions/upstream_sync.md` is 188 words and `reviews/upstream_sync/README.md` is 152, both far under
  6,000.
- Existing documents that grew:
  - `maxim_upstream/README.md`: 521 to 564 (+43);
  - `issues_now_DRAFT.md`: 379 to 429 (+50);
  - `roadmap.md`: 9,349 to 9,713 (+364);
  - `lessons_maxim_in_games.md`: +262 (lesson 42, which the brief asks for).

  See E5.

## Findings

### E1. SHOULD-FIX: `docs/roadmap.md::Phase 3, tier A, OD-A4` and `world_clock_release_DRAFT.md::§3.7` against §3.2 and §5

**Defect.** The OD-A4 row still has Plan = **A-pre**, and its text still opens "Live-path stamps outside the fence".
Yet the same row includes the tool duration in `runtime/tool_dispatch.py`.

The draft says that file is fenced, in §5: "This plan also treats `runtime/tool_dispatch.py` as fenced … which is why
OD-A4's tool duration is A-post". §3.2 says the same: "it lands in A-post". Lesson 42, in this same commit, calls the
row's A-pre placement a blind spot. Even so, §3.7's "Plan (tier A)" column copies **A-pre** for OD-A4.

The draft's own header rule ("Where this draft and a row differ, the row wins") then makes the wrong placement win.

**Failure scenario.** Maxim's D9 session, or the next lane rerun, reads the Plan column as tier A's ruling. It sees
OD-A4, the tool duration included, as an A-pre item that touches no fenced file. That contradicts the A-pre definition
in the draft's own header, and contradicts #1787's placement. The roadmap now holds a placement that its own lesson
says is wrong.

**Fix (unverified).** Split OD-A4's Plan cell, for example "A-pre (stamps: A-post per #1787); duration: A-post
(fenced)". Or move the duration part into OD-A8, which already owns the fenced `tool_dispatch` items. Then make §3.7
match. If the owner wants the column to wait until #1787 merges, record that as the lane's decision, and change at
least "outside the fence" for the duration clause.

### E2. SHOULD-FIX: `docs/roadmap.md::Phase 3, tier A, OD-A2 to OD-A7 "Status"`

**Defect: statuses not in O76's form.** O76 says a row "states only which release holds the fix and which release
the lock is on. It never restates Maxim's discussion, which drifts within a day (lesson 39)".

The new statuses restate the discussion on #1787, an open PR:
- D-WC6's "whole reader sets with a clock-domain marker";
- D-WC2's port modes;
- D-WC5's `CostTracker` proposal;
- the placement of the PR 0 gate.

OD-A4's status alone runs to about 80 words. The draft's §3.7 "Placement proposed in #1787" column already holds these
placements, so the roadmap now says the same thing twice. Order 3 also asks for "and nothing more".

**Failure scenario.** #1787 is open and under review. Its head moved during review (the `29dda704` commit message
lists three re-taken decisions). The next fold changes, say, D-WC6. The roadmap rows and the draft then disagree with
Maxim in two places, and the next rerun has to fix both. This is the drift that O76 was written to prevent.

**Fix (unverified).** Cut each Status to one line: "#1787 (open, read at `29dda704`) places it in <A-pre | A-post |
1.3.6>; in no release". Leave the detail to §3.7 of the draft.

### E3. SHOULD-FIX: `docs/plans/next_steps/3_upstream_sync.md::Exit test`, the `awk` heading check

**Defect.** `/^#/` treats any line that starts with `#` as a heading, and that includes wrapped prose that begins with
an issue number. The draft already has such a line: line 178, "#1787 takes OD-WC5 …".

**Failure scenario (verified).** In a scratch copy I inserted, before §3.2's body, the line "#1787 has superseded
nothing here; the tripwire stays:" and then "a `sys.setprofile` hook on the step path." The check exited 0 (false
green). The pseudo-heading contains "superseded", so the tripwire passes as superseded inside a live section. The rerun
lane runs this block at every tag, so a wrap-at-column-0 edit can silently mask a resurrected tripwire.

**Fix (verified).** Change `/^#/{h=$0}` to `/^#+ /{h=$0}`. I checked it on three files:
- the real draft: exit 0;
- the plain-section mutation: flags line 189, exit 1;
- the pseudo-heading mutation: flags line 71, exit 1.

This edit is to the brief, which is outside this step's file list. It goes to whoever owns `docs/plans/next_steps/`.

### E4. NIT: `docs/plans/next_steps/3_upstream_sync.md::Exit test`, supersession greps

**Defect.** The greps prove a token is present, not that the ruling is in place.

**Failure scenario (verified).** I rewrote §3.6 to "**Widened into #1305 before the 1.4.0 cut,**", which reverses
OD-A7's ruling while keeping both tokens. The block exits 0. Also, `1.4.0` is an unescaped ERE, so it matches `1x4y0`.

**Trigger:** the review round is the guard for content. Record this as a known limit of the exit test; it needs no fold.

### E5. NIT: `docs/maxim_upstream/issues_now_DRAFT.md` (+50 words) and `docs/maxim_upstream/README.md` (+43)

**Defect.** These are existing documents and they grew. CLAUDE.md's budget says an existing design document doesn't
grow, and the brief applies the same rule to "an existing document". Order 3 asks for each status to be restated, which
forces some growth in the table. But `issues_now_DRAFT.md` now carries the OD-I1/I2 status twice: once in its new
header block and once in the README row.

**Failure scenario.** The two copies drift at the next lock move.

**Fix (unverified).** Keep the status in the README row only, and leave a pointer in the draft's header.

### E6. NIT: `world_clock_release_DRAFT.md::§3.4` and `roadmap.md::OD-A3`, an incomplete site list

**Defect.** `prompt_builder.py::_build_engage_prompt` (`:2388-2391` at `f145e27b`) also renders `datetime.now()` into
a prompt, and neither the draft nor the row lists it. #1787 lists it (plan line 63 and its PR 2 row), along with two
tool results that hand the model a raw epoch (`_format_episodic_memory`, `SceneSummaryTool.execute`).

The draft hedges with "PR 0's census … fixes the counts", so this is not a correctness break. But §3.4 introduces the
list as "Sites on `f145e27b`", which reads as a complete list.

**Trigger:** next rerun. Alternatively, reword the line to "examples on `f145e27b`".

### E7. NIT: `docs/roadmap.md::OD-I8`, a typo left by an edit

The row reads "…at `043eab8f`); A question…". Cutting a clause left a capital letter after the semicolon.

### E8. NIT: `docs/roadmap.md::Phase 3`, Order 4's trigger

Order 4 asks that each touched row with no trigger of its own be given "each Overdrive tag and each Maxim release". No
touched row carries one. The existing O76/O77 paragraph ("reconciles them all at each Overdrive tag and each Maxim
release; a row's own trigger … comes first") arguably covers it as a blanket rule.

This is a brief-against-tree mismatch. Either the paragraph satisfies Order 4, and the lane should say so in the PR
body, or each touched row needs the phrase. **Trigger:** the hand-off note.

### E9. NIT: `docs/lessons_maxim_in_games.md::42`, unwrapped line

Line 115 is 197 characters long ("…(#1787 says about 54 years; … about 57). So #1787 …"), where the file otherwise
wraps prose near 120.

## Summary

The exit test passes as written. Every check in it can go red, and I watched each one do so on a scratch mutation. The
Order is carried out:
- all five supersessions are applied or marked;
- the draft shrank by 874 words;
- no lock version appears in a draft;
- only the reserved ids are used;
- every touched file is on the list.

There are three SHOULD-FIXes:
- **E1:** OD-A4 is still A-pre in both the roadmap and §3.7, against the draft's own fence text and lesson 42.
- **E2:** the roadmap Status cells restate #1787's open discussion, against O76.
- **E3:** the `awk` heading check gives a verified false green on a column-0 `#NNNN` line, with a verified one-token
  fix. The fix belongs to the brief.

No BLOCKER.
