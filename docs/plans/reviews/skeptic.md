# Skeptic review of the foundations plan (72bf36c)

Reviewer: the Skeptic lens, one of seven independent readers. I read `docs/plans/foundations_plan.md`,
`docs/roadmap.md`, `docs/design/{boundaries,world_model,npcs_and_sem,world_v2}.md`, the review directories, and the
code on `phase1/design-v2`, `phase1/act-validation`, `phase1/standards` and `phase1/transport`. Every number below
comes from `wc` or `git` on those branches at the time of review.

## The numbers

| Measure | Value |
|---|---|
| Words under `docs/` on `phase1/design-v2` | **371,864** (about four or five novels) |
| of which review records (`docs/design/reviews/`, 63 files, 8 series) | about 235,000 |
| of which research (`docs/design/research/`) plus Maxim drafts (`docs/maxim_upstream/`) | about 74,000 |
| The two largest design docs | `npcs_and_sem.md` 23,043; `boundaries.md` 13,433 |
| `src/` lines, the most code on any branch (`phase1/act-validation`) | **1,688** (1,058 on design-v2) |
| Tooling: `scripts/lint_standards.py` plus its test | 396 + 472 lines, about half the size of `src/` |
| Godot or client code on any branch | **0 lines** |
| Commits merged to `main` | **0** (`main` is still `d02c0a2`, the initial commit) |
| Open, stacked draft PRs that need rebases | 4 |
| Design review series | 8 (world_v2, world_model, boundaries, foundations_v1 and its delta, realtime_lanes_coop and its delta, maxim_response_1, npcs_v3, npcs_v3_1) |
| Code delta rounds on PR 1 alone | at least 6, plus 5 on the closed-schema work and 2 on format versions |
| Features a player can see | **0** |
| Calendar time | 4 days (2026-11-14 to 11-17), about 85 commits across branches |

That is about 220 words of design and review for each line of shipped code. The calendar is short, and agents
write fast, so "designing forever" is not yet true in days. It is true in direction. The plan in front of me
(§3) has eleven steps, and **none of them puts a pixel on screen**. The steps it does have (boundaries, gates,
agents, a Part 3 design doc, a calibration ledger) produce more structure, more process or more paper.

## What is genuinely good

- **O19 is the right call, with the right diagnosis.** Three rounds found "blockers of new kinds at ever finer
  implementation grain ... divergence, which paper can describe and only code can prove." That sentence is the most
  important one in the corpus, and the owner acted on it.
- **The physics discipline pays.** E1 (`world_model.md` §10) found that PR 1's red gate burns at most about 2.5 kg of
  a 130 kg crate in a sealed room, so the gate "would pass under any burn law." Review caught a test that could not
  fail. That is the charter working.
- **The plan is honest about its own process.** §5.3 says plainly that fold tables overstated five times in a row,
  and that three upstream asks duplicated Maxim's own work. The search-Maxim-first rule (B22) is a cheap fix to a
  real cost.
- **Refusing to build an interim mode (a)** for real Maxim agents instead of hacking around the host-driven contract
  is principled, and §4 tracks the Maxim side clearly.
- **The plan as an index** (decisions, blockers, ownership) is useful to a cold session, and `check_plan.py` keeps it
  from silently losing ids.

## Findings

### BLOCKER

**S-B1. The plan never mentions Phase 1's exit, and none of its steps moves toward it.**
`foundations_plan.md` §3. The roadmap's Phase 1 is "the first visible tile". Its exit is: walk into the alley, set
a crate on fire, watch it crack, glow and burn away. `grep -i "exit|godot|client|tile|transport"` over the plan
finds nothing but the transport decision in PR #1's description. The Godot client, the WebSocket transport, the
authored tile, save v0 and the fire-burnout red gate (all Phase 1 bullets in the roadmap) appear in none of the
eleven steps. Failure scenario: every step in §3 completes as written, and the owner still can't see anything. The
next plan is then written from the same place. Fix: §3 must name the exit and the critical path to it, and every
step must say whether it is on that path.

**S-B2. On the path the plan inherits, the Godot client is the last of about 16 PRs, so the visible tile is months
away, not weeks.**
`world_model.md` §10 puts `phase1/lab` (the lab tile "and the Godot client") at row 12, after boundaries, gates,
verify, sim-clock, material v1, protocol, zones, fuel-surface, fuel-combustion, phase change, **agents, lanes** and
save v0. At the rate observed (PR 1 is still unmerged after more than a dozen delta rounds), each PR costs days of
review. Phase 1 grew from a client plus a tile into a full engine re-architecture, a zone gas model with O₂, a
pyrolysis and combustion model, bound-water phase change, an agent port with worker processes, and threaded lanes.
Phase 1 "has no NPCs" (roadmap), yet rows 9b and 10 build the NPC runtime inside it. Failure scenario: the owner,
who is new to game development, spends Phase 1 without opening Godot once. The engine's biggest unknown for this
phase (3-D texture upload, a shader reading `crack` and `glow`, the frame rate at the rig profile) is found last,
after the protocol has frozen around a fixture reader that is "minimal" by design.

**S-B3. The Phase 1 exit test is itself unsettled, and the proposed replacement pulls half of Phase 2 into Phase 1.**
`world_v2.md` §9 Q1 proposes replacing the alley crate with a sealed lab fire that starves and a vented bay fire
that burns its fuel away. That needs O₂, zones, vents and combustion products, which is why rows 7, 8a and 8b
exist. The roadmap still says alley plus crate plus ripperdoc clinic. The plan lists neither the question nor the
answer. E1 is correct that a sealed room needs vents *once O₂ exists*. But O₂ does not need to exist in Phase 1:
the roadmap's own fix is "fires that go out when their fuel is gone," whose red gate already exists
(`tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating`). Fix: the owner decides the exit
test explicitly. I recommend the roadmap's alley crate with a fuel-mass burnout law, a closed-form test and a
cross-tier test. Defer O₂ and zones to Phase 2, where the roadmap already put gas, and record the missing
oxygen limit as a known gap with numbers, as CLAUDE.md requires.

**S-B4. The premise that would sink the game is unmeasured, and a decision forbids the cheapest measurement.**
The game's premise is that every NPC is an LLM-driven Maxim agent with a lived life. Neither the design corpus nor
the plan contains a measured number for model latency per thought, tokens per NPC per minute, cost per play hour,
or how many concurrent NPCs a laptop's local model can serve. `npcs_and_sem.md` §12.2 lists "a shared router
serialises inference" as an open divergence, with no number. O10 forbids a developer mode with real Maxim before
tier A, and tier A plus the 1.4.0 cut (O15a) have no date. Failure scenario: months of AgentPort, lanes,
floor-holding and dilation machinery get built. Then the first real measurement shows that five NPCs on a local
model each speak every eight seconds, or that cloud inference costs dollars per hour. The dilation design
(O4, O11, O11a, O16) is one answer to this risk, but it is designed, not measured. Fix: a throwaway spike that
touches no world code and no Maxim code: N concurrent persona prompts against the candidate local and remote
models, measuring p50 and p95 latency and tokens, with the results recorded as numbers in `docs/architecture.md`
("Known gaps"). O10 restricts Maxim, not raw model calls, so the spike doesn't violate it. Keep it out of `src/`
so the determinism rules don't apply.

### SHOULD-FIX

**S-S1. Build `phase1/agents` (step 7) and `phase1/lanes` later, not now.** Phase 4's real NPCs wait for Maxim's
1.4.0 cut and a stepped `think` that Maxim hasn't designed yet (`response_2.md`: "lands after the 1.4.0 cut").
Maxim's ranked candidates document is still pending and "re-checks every citation". Building `AgentPort`, the
continuation header, receipts, a worker process, a codec and hash-seed probes against a scripted double means
writing to a contract that hasn't been negotiated. When Maxim's real API lands it will differ, and the work turns
over. The five red-first tests are good tests; put them in the backlog against the PR that first spawns a real
worker. Move steps 7 and 10 out of Phase 1, as the roadmap's "Phase 1 has no NPCs" implies.

**S-S2. The agent-half freeze is real against review rounds, not against change, and the plan should say so.**
Evidence: the very next commit after O19 (`72bf36c`) edits `npcs_and_sem.md` again (14 lines in, 10 out). §5.2 still
records stale text ("§12.2 still says this closes with OD-A19"). `boundaries.md` §11.2 still says the
determinism allowlist "admits `Philox`", while plan §4 records keyed `random.Random` over Philox as accepted.
Three triggers will reopen the design: Maxim's ranked candidates document, the 1.4.0 `think` API, and the first
measured latency (S-B4). Fix: state the reopen triggers in O19, and say that until one fires, edits to
`npcs_and_sem.md` are limited to errata. Otherwise "frozen" becomes "frozen except for every fold".

**S-S3. Owner bandwidth is the real critical path, and the plan treats it as free.** One person reviews and merges
everything. Nothing has merged, four PRs are stacked, and three need rebases (steps 2–4). At 370k words, the
owner cannot have read the corpus the decisions rest on. Many O-decisions are presumably made from summaries,
which is where overstated fold tables (§5.3) do real damage. Fix: make merging PRs #1 and #2 and closing (or
merging as archive) #3 and #4 the explicit gate before any new design text. Give each future design a word budget
(for example 4,000 words), with reviews summarised in a single table rather than kept verbatim in full.

**S-S4. The boundaries refactor is sized for an engine, not for 1,688 lines.** `boundaries.md` §11.1 re-homes
the code into 12 layers (`checks`, `materials`, `geometry`, `cells`, `laws`, `scene`, `intents`, `imagination`,
`sim`, `loaders`, `tiers`, `adapters.sem`), with import-linter contracts, TEMPORARY markers scheduled across three
future PRs, and a section on what the rename must get right. Enforcing the engine/game boundary early is cheap
and valuable. Twelve layers for about ten modules is not. Fix: do 2b at three or four layers (engine core,
adapters, game, client protocol) and let the layers split when a module passes the 500-line tripwire that
already exists.

**S-S5. Co-op and guest privacy are designed before a single player can play.** O14 (five gates), O17 (purging
guest speech), O18 (local model only for guests), the turn-taking substrate in co-op, and
`realtime_lanes_coop.md` with its 43k words of reviews: all of it predates one NPC and one client. These
decisions are mostly sound, and recording them costs little. What costs a lot is the 12 review files they
generated, and any further rounds. Fix: mark co-op Phase 5+ in the roadmap, and make no more review rounds on it
until single-player NPCs exist.

**S-S6. The Maxim dependency is unbounded, and it lands on the same person.** Phase 3 lists about 50 OD items
across tiers A, B and C, plus two experiments and an Exp 64 pre-registration, and Phase 4 waits on all of tier A
plus 1.4.0. None of them has a date. If the same owner drives Maxim, Overdrive has turned itself into a large
backlog for its own author's other project. Fix: name the minimal tier-A subset Phase 4's first NPC actually
needs (from the exit tests, roughly OD-A2, A14, A15, A18), call everything else non-blocking, and ask Maxim for a
date range for 1.4.0.

**S-S7. The core loop and the fun are underweighted.** Part 3 (`lab_and_core_loop.md`) is step 8 and unwritten.
"Overdrive as heat debt" (`world_v2.md` §10) is the only statement of what the player does, and no prototype
tests it. More review on heat-law convergence will not tell anyone whether pushing past limits in a burning bay
is fun. Fix: once the tile renders, put a grey-box heat-debt prototype in the client on top of it before any
further physics breadth.

**S-S8. Step 10 (the calibration ledger) is more process with no caller.** It is "Proposed, not designed". Leave
it out of the plan until a tunable's provenance actually causes a bug.

### NIT

- **S-N1.** §1's table records local heads and "gate run in progress", which go stale within hours. Link to the PRs
  and drop the SHAs, or `check_plan.py` should check them.
- **S-N2.** `check_plan.py` is a lint for a plan document. One more is fine; the pattern (markdown-it parsing, five
  delta rounds on what counts as a blank line in the marker lint) is the warning sign. Tooling about documents
  should be the last thing to get review rounds.
- **S-N3.** §5.1 item 5 (the speed trait's structure) is "taken" by the owner but "not recorded as a decision".
  Record it or drop it; it doesn't block anything for months.
- **S-N4.** The tile has two names: the roadmap's "ripperdoc clinic and alley" and world_model's "lab". Pick one.

## The shortest honest path to something the owner can see and play

1. Merge PR #1 (standards) and PR #2 (act-validation) to `main`. Merge #3 and #4 as an archive, or close them.
   Stop all new design text until step 6 is done.
2. Do a light `phase1/boundaries`: three or four layers and the import contract, no behaviour change.
3. Fuel burnout as a mass budget: the existing red gate flips, with a closed-form test (burn time equals fuel
   energy over release rate) and a cross-tier test. No O₂; record the missing oxygen limit as a known gap with
   numbers.
4. `phase1/protocol` v0: WebSocket on 127.0.0.1, token, `hello`/`welcome`, a versioned binary snapshot frame, the
   `ignite` and `move` intents, a golden fixture, and the Godot reader as the second reader.
5. The Godot client: a 3-D texture from the snapshot, one shader for `glow` and `crack`, a first-person camera, one
   ignite key. Owner-driven, as the place to learn Godot.
6. The alley and crate scene in metres, golden screenshots at laptop and rig, then a human playtest. **Phase 1
   exits.**
7. In parallel, off the critical path: the LLM latency and cost spike (S-B4).

Then, with something on screen: verify, sim-clock, O₂ and zones (Phase 2), Part 3's heat-debt prototype, and the
agent port once Maxim's candidates document and the 1.4.0 API exist.

My estimate for steps 1–6, with agents and one owner learning Godot: two to four weeks of focused work, gated
mainly by owner review. On the plan's inherited path (S-B2), it is a quarter or more, with the Godot unknowns
found last.

## Verdict

The thinking is often excellent. The physics test discipline, the E1 catch, the honesty about overstated folds,
and above all O19's diagnosis that paper can't prove what only code can, are real strengths. But the project has
produced about 372,000 words of design and review against 1,688 lines of code, zero merges and zero pixels. The
plan meant to turn that into building does not name Phase 1's exit at all. It schedules more structure (twelve
layers for ten modules), an agent runtime for NPCs that can't exist until Maxim's unscheduled 1.4.0, and more
process, and it inherits an order that puts the Godot client sixteenth. The freeze on the agent half is real for
review rounds, but it will reopen the moment Maxim's API or a latency number arrives, so building against it now
is premature. The risk that would actually sink the project is not a physics error. It is an owner new to game
development who never opens Godot, an untested LLM cost and latency premise, and a review process that grows
faster than the code it guards. Reorder around the visible tile (the path above): cut agents and lanes from Phase
1, defer O₂ and zones, and measure the LLM premise now. The plan is not ready to execute as written. The fix is a
reorder and a cut, not another design round.
