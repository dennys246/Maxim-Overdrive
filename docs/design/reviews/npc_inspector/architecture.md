# NPC inspector design v1: Architecture review (round 1)

**Lens:** Architecture (design review). **Read:** the staged tree `00b97665` in the `phase3/npc-inspector` worktree, diffed against `origin/main` `e6d6a7f`. The diff adds `docs/design/npc_inspector.md` (2,874 words) and the `mind_record.kinds` row in `docs/design/contracts.md`. Context read at `e6d6a7f`: CLAUDE.md; `docs/code_review.md` (lens table, "Design reviews"); `docs/design/boundaries.md` §6.1–§6.4, §7.1–§7.4, §8.1, §13; `docs/design/npcs_and_sem.md` §5.2, §6.2–§6.6, §7; `docs/design/sem_stimuli.md` §4.2–§4.5; `docs/design/decisions/npcs_and_sem.md` (O6, O6a, O10, O13, O14, O18, O26); `docs/design/decisions/boundaries.md` (O79, O81); `docs/plans/next_steps/4_records_build.md`; `docs/design/records_layout.md` §3 and §7 (the `lint_contracts` scope); `docs/roadmap.md` (save v1, OD-A15); `src/simcore/host/server.py`. **Ran:** `scripts/lint_contracts.py` (exit 0) and `scripts/lint_paths.py` (no output) on the worktree, whose unstaged diff is empty. I did not read Maxim or Maxim-pulse, so the design's claims at `b90800e` and `a1ba1d4` are not checked here.

## Findings

### A1. BLOCKER: `npc_inspector.md::§2 "write"` and `§3` duplicate the agent-side audit record that `boundaries.md` §6.1 already places, and don't say so

`boundaries.md` §6.1 (the `memory_write` bullet) already decides where memory writes are recorded: "Memory writes are agent-side values in `StepOutput`, recorded in an agent-side audit record after OD-A15, and saved with the agent home." The inspector adds a host-side `write` entry holding "memory writes and `retrieval` writes … with provenance as stamped". §3 then says its record is written "never inside an agent home". Neither section links to §6.1 or reconciles with it. One of two things follows, and the design must say which:

- **Same record.** Then the design moves the audit record's owner and its placement (from the agent home to beside the world log) without saying so, which silently amends a `boundaries.md` contract.
- **Two records.** Then the same writes, guest-derived text included, live in two places, in two formats, with two owners.

**Failure scenario:** `phase1/agents` builds both records. O26's purge is wired to the stores, the agent home (which holds the §6.1 audit record) and saves. The mind record's `write` text is a second copy, so a guest's line survives the purge in one of the two. O14 gate 5's exit test ("leaves no trace after a purge") passes only if it happens to check the record that was purged. The one-owner rule says: "When a change touches a contract stated in two places, move it to one owner in the same branch."

**Fix (unverified):** state in §2 whether the mind record replaces, contains or links to the §6.1 audit record, and make one section own the record of memory writes. The other section links to it.

### A2. SHOULD-FIX: `npc_inspector.md::§2 "percept"` cites a superseded pull model; the stimulus contract that owns frames is `sem_stimuli.md` §4.2

The percept entry is "the frame values the agent's pulls read at its last `step` (`npcs_and_sem.md` §7.3): region, receptor, site and value, as the agent received them". The delivery contract is now `sem_stimuli.md` v5 §4.2–§4.4, and it works differently:

- The host builds a host-only `BodyFrame`, which holds world values at sites.
- What crosses the channel is a `BoundFrame` with one value per binding.
- The worker pushes it with `world_set_axis`, and "a push is never logged".
- The worker clamps each value to the declared range before Maxim stores it (§4.4, "One writer, checked by value").

So the host doesn't hold "what the pulls read". It holds two different things: `BodyFrame` (world truth at the site) and `BoundFrame` (the values sent, before the worker's clamp). The design names neither and doesn't link to the owner.

**Failure scenario:** a builder takes the first per-NPC frame the host holds, which is `BodyFrame`, and records it under `percept`. That puts the world's true value under a sensor's name, which is exactly what the same bullet forbids. Or the builder records `BoundFrame` values, and the view shows a value the agent never stored, because the clamp happens in the worker.

**Fix (unverified):** define `percept` as the `BoundFrame` content per binding (`sem_stimuli.md` §4.2), by link. Say that the stored value can differ by the worker's clamp. Say that `BodyFrame` never enters the record.

### A3. SHOULD-FIX: `npc_inspector.md::§6` and `§4 "Cost"`: the readout amends `StepOutput` and the `step_output` frame, and the cost claim doesn't hold for it

§6's ask is that "Maxim's `step` returns, beside its intents, an optional, frozen, versioned readout". That changes two things that other sections own:

- `StepOutput`'s contents (`boundaries.md` §7.1: intents, `speak` acts, thought requests and memory writes; the types are `npcs_and_sem.md` §6.2's);
- the codec's `step_output` frame schema (`npcs_and_sem.md` §6.6, `codec.kinds`).

§1's "never adds a codec kind" is technically true, since the readout would be a new field rather than a new kind, but neither owner is linked as the section to amend. §4 also says "No extra round trip: the record copies values the barrier already decoded". That holds for the [agents] kinds, not for `state`. A readout adds bytes to every park's frame and compute to every worker `step`. That load lands on the barrier whose cost `npcs_and_sem.md` §6.6 already estimates at 0.2–0.8 wall seconds per second at 20 NPCs.

**Failure scenario:** the ask is drafted upstream as "an optional readout". Maxim adds it to its embedded `step`, and the adapter then needs a new `step_output` field. Nothing in `npcs_and_sem.md` §6.6 or `boundaries.md` §7.1 points to it, and nothing budgets it, so the barrier meter regresses with no owner for the change.

**Fix (unverified):** in §6, name `StepOutput` and `step_output` as the contracts the readout would amend, by link. Scope §4's cost claim to the [agents] kinds, and give `state` a separate line on the barrier budget.

### A4. SHOULD-FIX: `npc_inspector.md::§3`: the record's layer and package are never named, and the import rule contradicts the reader's placement

- §3 says "no module under `simcore.core`, the laws or `simcore.adapters` imports the record's writer or reader". The next bullet says a view reads it "through a file gate (`adapters/loaders.py`'s pattern)". The file gates live in `simcore.adapters`. Either the reader isn't a file gate in `adapters`, or the import rule bans its own home.
- The writer's package is never stated. The layering is game > host | verify > protocol > adapters > core, and the writer is presumably in `simcore.host`.
- Engine vs game is never split. The record is engine machinery, while §5's audiences and fiction gating belong to the game.
- "If the gate is in Python" leaves a Godot or static-page reader (§7 option b) with no counterpart to the gate registry. A save from someone else is the "strictest gate" class (`boundaries.md` §5.3, "strangers' machines").

**Failure scenario:** `phase1/agents` puts the reader in `simcore.adapters.loaders` to follow the pattern, and the new import contract fails it. Or the reader goes into the game package, which then has no gate-registry row, and an untrusted mind record from a shared save is parsed outside any registered gate.

**Fix (unverified):** name the writer's package and layer, the reader's package and its gate-registry row, and what is engine versus game. Then restate the import rule so it is consistent with those placements.

### A5. SHOULD-FIX: `npc_inspector.md::§3 "Guest text"` and `§9 item 4`: the O26 question is framed as optional, but O14 and O26 already decide it

§3 says "the purge path must reach it", and then §9 asks the owner "does the mind record join the list a guest's purge reaches? The author recommends yes." O14 gate 5 requires a purge that leaves no trace. O26 already lists saves in the purge's reach, and §3 says a save carries the record. So once the record holds guest-derived text (`thought` speech, `write` text), a "no" would break O14's exit test. The owner's real choice is between two options:

- (a) the record holds guest-derived text, and O26's reach is widened to name it explicitly;
- (b) the record holds only lengths and ids for guest-derived spans, so there is nothing to purge.

The question as written offers a "no" that is not a valid option.

**Failure scenario:** the owner answers "no" to the question as posed. The record ships with guest text that the purge doesn't reach, and O14's gate fails in Phase 4.

**Fix (unverified):** reframe item 4 as the choice between (a) and (b), citing O14 gate 5 and O26's current reach.

### A6. SHOULD-FIX: `npc_inspector.md::§3 "Saves and bug reports"` amends two contracts it doesn't own, without linking their owners

- **Save format.** "A save carries the record with the world log" adds a component to save v1. The roadmap defines save v1 (`roadmap.md`, Phase 4: "the world plus each NPC's agent home, including the agent's `EventSequencer` high-water seq"), and `boundaries.md` §7.1 says the same ("Save v1 persists the world plus each NPC's agent home, separately"). Neither is linked or flagged as amended.
- **Bug reports.** "A bug report drops `thought` speech and `write` text by default" adds a redaction rule to a rule that `npcs_and_sem.md` §5.2 and `boundaries.md` §6.2 own (only `speak` text today). §12.1 item 4 there also leaves that rule open with the owner. The bug-report redaction set would then be stated in three documents.

**Failure scenario:** save v1 is built from the roadmap's definition and has no slot for the mind record. Or the owner rules on `npcs_and_sem.md` §12.1 item 4 (keep `speak` text in bug reports, say), and the inspector's copy of the rule goes stale.

**Fix (unverified):** link both owners and state the change as a proposed amendment to each, or move the bug-report redaction set to a single owner.

### A7. SHOULD-FIX: `npc_inspector.md::§9 item 7`, the branch's relation to step 4, is under-stated

The design is right to ask, and it is right that it touches no record file: `contracts.md` is not a record family, and `records_layout.md` §7 keeps `lint_contracts`' scope on the hand-written designs, so the registry row doesn't collide with R1. Two consequences are missing, though:

- **Step 4's exit test requires no other open PR.** Its command is `gh pr list --state open …` with a count of zero. Any PR from this branch fails step 4's exit unless it merges before step 4 starts, or is closed, or the owner amends the brief the way #80 did for the two late branches.
- **This branch is in neither O79's nor O81's order.** A third late branch therefore needs an owner amendment to the step 4 brief, not only an answer to the question. PR #81 (`phase3/joint-plan`) is in the same position, and this design depends on it (A8).

**Failure scenario:** the owner chooses "third late branch", and this branch opens a draft PR to keep it current. Step 4's exit test goes red at hand-off, and the step stalls on a PR its brief never named.

**Fix (unverified):** in item 7, state the exit-test consequence, and say that "late branch" means the same terms as #80's: no PR, no merge, and the brief amended by the owner.

### A8. NIT: `npc_inspector.md::§2 "percept"` and `§6`: dependencies on unmerged text, and three candidate owners for the ask

The design cites two things that exist only on `phase3/joint-plan` (PR #81, not on `main`): the game-evidence draft's "condition 3" and `reviews/joint_plan/bio_faithful.md` BF-B2. The ask's shape is said to be owned here "until a draft in `docs/maxim_upstream/` takes it", while §6 also calls it "a candidate addition to the embeddable draft" and says it "belongs in the joint plan … as a link both ways". That is three candidate future owners for one ask.

**Scenario:** PR #81 is revised or closed, and this design, once on `main`, cites text that doesn't exist there. Or the ask is drafted in two of the three places.

**Fix (unverified):** name the one future owner. Cite PR #81 only as a pending dependency, or not at all until it merges.

### A9. NIT: `npc_inspector.md::§6`: the ask has no Phase 3 item

CLAUDE.md ("Push back on Maxim") says each proposal to Maxim is an item under Phase 3 in `docs/roadmap.md`. The design defers drafting the ask, which is reasonable under O79 for the duration of step 4 (and taking a new `OD-` id from an unscheduled branch risks a collision). But until a Phase 3 row exists, this design is the only place the ask is tracked.

**Fix (unverified):** say in §8 that the ask gets its `OD-` id and Phase 3 row when step 4 merges, with the trigger named.

### A10. NIT: `npc_inspector.md::§3`: "the ownership scans gain its writer"

The ownership scans (`tests/test_ownership.py`) hold where world writers live. The record writer writes a file, not a world field, so adding it there either misplaces it or means a different scan.

**Scenario:** the builder adds the writer to the world-writer allowlist, which widens the set of functions allowed to write the world.

**Fix (unverified):** name what the scan should assert instead, for example "no function outside the writer's module opens the record for writing".

### A11. NIT: `npc_inspector.md::§2 "The format"`: per run versus per segment, and the on/off switch

"One record per agent per run" has a header that carries the log root id and one segment. A run spans segments: each restore opens one, and so does an agent restart (`npcs_and_sem.md` §6.6). §1's on/off test also implies a switch, but the design doesn't say where the switch is recorded (log header? rerun manifest?), so a save cannot say whether the absence of a record means "off" or "lost".

**Fix (unverified):** state whether a record covers one segment or many, and where the on/off state is recorded.

### A12. NIT: `npc_inspector.md::§4 "Replay"` and `§8`: what replay re-derives, and timing

- **Replay coverage.** The log holds stage-1-accepted intents (`boundaries.md` §6.1, decode → stage 1 → log), but the record's `intent` entries include stage-1 results, refusals among them. Replay cannot re-derive those refused entries, but §4 lists intents as re-derived. In the other direction, `thought_cancelled`, `thought_failed` and `reply_landed` are log records, so part of a thought's lifecycle is re-derivable, while §4 says thought lifecycles come only from the saved record.
- **Timing of the cost meter.** §4 puts the write cost "on B5's agent-lane meters (`npcs_and_sem.md` §6.3)". Those meters arrive with `phase1/lanes`, which comes after `phase1/agents` (`npcs_and_sem.md` §6.2). The [agents] build would therefore have no meter to report the cost on.

## Areas checked and clean

- **The §1 rule against the trust boundary.** "Never call `AgentPort`, never add a codec kind, never run anything in a worker" is consistent with O6, O6a, O13 and the closed `codec.kinds` (`npcs_and_sem.md` §6.6). The output-only rule and the on/off digest test match `boundaries.md` §6.2's "replay reproduces the world, never the agents". The world-clock-only stamping keeps `boundaries.md` §7.3's no-time-to-cognition rule; the record never feeds cognition at all.
- **O10.** Every [agents] item runs on the scripted double, and real NPCs come only in Phase 4 after tier A. No developer mode with real Maxim is implied.
- **Raw model text.** The record keeps prompts and raw model text out, consistent with `boundaries.md` §6.2 and `inference_placement.md`. The agent-owned body stays opaque.
- **Live view.** It is routed through a new host-to-client message owned by `client_rendering.md` §4.1, never a browser. The `Origin` refusal is verified at `src/simcore/host/server.py:59`.
- **Contract registry.** The `mind_record.kinds` marker matches its row, and `lint_contracts.py` exits 0. The design holds no decision or fold table, and §9 is a list of questions, not rulings.
- **Word budget.** 2,874 words, under the 6,000 allowed for a new design. `lint_paths.py` is clean.
- **"Review finds, it doesn't design" and BF-B2.** §6 leaves the readout's fields to Maxim and does not design Maxim's cognition from here.
- **Honesty about status.** The status line ("DRAFT v1 … Nothing here is decided") and §8's timing (nothing to inspect before Phase 4) are accurate. Each choice that belongs to the owner is listed in §9, apart from the framing problems in A5 and A7.
- **Step 4's files.** The diff touches no record family (lessons, decisions, Known gaps, backlog) and no file in step 4's list, `lint_contracts.py` included.

## Summary

| Severity | Findings |
|---|---|
| BLOCKER | 1 (A1) |
| SHOULD-FIX | 6 (A2–A7) |
| NIT | 5 (A8–A12) |

The central idea is sound and fits the architecture: the inspector is an output-only, host-side recording of what already crosses the membrane, stamped on the world clock. The blocker is a second record of memory writes that duplicates `boundaries.md` §6.1's audit record without acknowledging it. Most of the should-fixes are contracts the design amends or relies on without linking their owners:

- `sem_stimuli.md`'s frames;
- `StepOutput` and the `step_output` frame;
- save v1;
- the bug-report redaction set.

The rest are an unnamed layer and package for the writer and reader, O26 framed as optional, and the branch's relation to step 4's exit test. All fix statuses are `open`. Each proposed fix is unverified.
