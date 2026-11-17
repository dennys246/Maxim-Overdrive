# npcs_and_sem.md v3.1 (f839075): delta review, Determinism and replay + Bio-faithful integration

**Reviewed:** commit f839075, the fold of `reviews/npcs_v3/` into `npcs_and_sem.md` v3.1 (§0, §2.3, §3.1, §4.3–§4.6,
§5.1, §6.1, §6.6, §12), `boundaries.md` §6–§7 as changed, `maxim_upstream/embeddable_agent_DRAFT.md` v2.1, roadmap
OD-A1/OD-A2/OD-A18/OD-A19, `reviews/maxim_response_1/correction_1.md` and the fold table. This round judges only the
fold and what it opens. Maxim read at `origin/main` 7084f561 with `git show`: `decisions/nac.py`,
`decisions/temporal_credit.py`, `runtime/agent_loop.py`, `time/temporal_signature.py`,
`docs/plans/experience_clock_decay.md`.

**Counts:** 3 BLOCKER, 10 SHOULD-FIX, 7 NIT.

**The headline.** I found no path that makes a tier-1 replay diverge, and no path where exact time reaches cognition
under dilate. The three new host records (`reply_landed`, `floor_event`, `agent_failed`) never feed `Simulation`.
On the determinism side the fold mostly holds. The defects are in the guards meant to prove it, which as specified
can pass against the plant, and in records that `boundaries.md` never registered.

The NAc correction is the serious problem. Its citations check out: `nac.py:3707` is `decay_eligibility(factor=0.9)`,
"Called on each tick". `:1162` is `record_event`'s `time.time()` for the 300 s buffer. `agent_loop.py:800-840` is
`_NAC_PER_TICK_DECAYS` plus `_loop_bio_tick_maintenance`, called at `:3194`. But the conclusion built on them is
wrong in three ways:
- OD-A19 duplicates a Maxim plan that already exists, and that Overdrive's own roadmap lists as OD-A1;
- the "13×" number ignores that NAc normalises credit;
- the proposed exit test passes on today's code.

All three are in the correction we are about to send Maxim.

---

## BLOCKER

### DB-B1: OD-A19 re-proposes Maxim's own #1361 S3a/S3b, and correction_1 argues against a contract Maxim has already decided to delete

**Where:** roadmap OD-A19 and OD-A18 ("After OD-A19"); `correction_1.md` §1; §6.6 "Credit's real dependency";
§12.2; embeddable draft PR 4a and OD-EA12; fold rows BF3-1 and BD-19 ("folded").

**What Maxim already has.** `docs/plans/experience_clock_decay.md` (PROPOSED 2026-10-17, #1361; owner decisions
taken) plans exactly this. Its §(b) says `_loop_live_tick` passes `dt_us` to `nac.advance_experience(dt_us)`, which
applies `exp(−dt_us/τ_us)` to `_eligibility`, `_reward_bias`, `_goal_reward_bias`, `_cluster_reward_bias`,
`_percept_valences` and exploration visits, and "§8.5's `_loop_bio_tick_maintenance` is deleted". Its gates are the
exit test OD-A19 asks for:
- **G2:** a fake latency of 0.05 vs 1.0 s gives identical maps;
- **G3:** a realtime loop at 2 Hz vs 20 Hz over the same 60 s gives the same key set, within 1e-12;
- **G2b:** the same credit sequence at two poll rates gives an identical link set and the same split between trace
  and anchor.

Its §Motivation already names the defect our reviewer found ("a tick is any `pre_tick_gate` pass"; "Two clocks in one
credit computation"). Overdrive's own roadmap carries this as **OD-A1** ("#1361's S3–S6: a dependency, not
duplicated"). `realtime_lanes_coop.md:300` and `maxim_time_audit.md:33` cite it too. So OD-A19 is a duplicate row in
our own roadmap, and the fold breaks the front-gate rule of §6.1 (MP-B1: "build on, not beside").

**Two things the correction then gets wrong in front of Maxim:**
- "It argues against the per-tick decay contract in `_loop_bio_tick_maintenance`." Maxim's owner already decided
  against that contract (decision 1, 2026-10-17). There is nothing left to argue.
- "On a robot at a fixed loop rate nothing changes." Maxim's own Risk 1 says the converted τ is "5–15× slower while
  active" on the 10–30 Hz embodied loop, and its §Tau conversion re-derives every τ from a 2 Hz fixture. The change
  is real for robots, which is why Maxim gave it slices, gates and an Exp 30 re-run. So it can't sit, as the draft
  implies, inside an engineering refactor behind a bit-identical parity guard. §3.3 of our own doc uses the same
  argument to put the SCN `dt` change in tier B (MP-B2).

**Failure scenario.** Maxim receives `correction_1.md`. It reads as a new ask that "argues against" a decision Maxim
already reversed, with the conversion pitched as a no-op for robots. Maxim's process either spends a design round
rediscovering #1361, or a second, parallel decay plan starts. Overdrive's credibility on corrections drops on the
very message whose purpose is to correct a citation error.

**Fix.**
- Delete OD-A19. OD-A18 becomes "after OD-A1's #1361 S3a and S3b", and PR 4a in the draft becomes "#1361 S3a/S3b
  (yours)".
- Rewrite correction_1 §1: "the dependency is #1361 S3a/S3b, which you already planned; its G2, G3 and G2b are the
  exit test we wanted". Then name only what is new from us: the embedded driver supplies `dt_us` from the host's
  world schedule (ExperienceClockDriver's turn-based declaration, #1361 S2/Q8), and DB-B2's anchor point.
- Re-mark BF3-1 and BD-19 in the fold table as "folded to OD-A1".

### DB-B2: the mechanism and numbers in the correction are wrong, and the exit test it proposes passes on today's code

**Where:** §6.6 ("credit the same 3 s-delayed receipt about 13× differently"); `correction_1.md` §1; OD-A19's and
OD-EA12's "crediting one delayed receipt equally at two rate divisors".

**What the code does.** `NAc.distribute_reward` (`nac.py` after `:3586`) and `TemporalCreditDistributor.distribute`
(`temporal_credit.py:203-260`), the path `bio_stack.py:596` uses, both **normalise**:
`credit = reward · strength / Σ strength`. Trace attenuation therefore never changes the credit a lone eligible node
receives. With the act's node the only eligible one:
- at divisor 1 (100 ms), 30 calls leave 0.9³⁰ = 0.042;
- at divisor 5, 6 calls leave 0.53.

Both are above the 0.01 floor, so each NPC books the **full** reward. That is equal credit, not 13× different.
OD-EA12 as written passes on unfixed Maxim, and a test that cannot fail is a BLOCKER (CLAUDE.md, Prove a guard).

**Where the step size actually bites:**
- **The split between eligible nodes.** Take A activated at the act and B a second later. A's share is 0.26 at
  divisor 1 and 0.45 at divisor 5, about 1.7×.
- **The expiry.** Past 44 calls (4.4 s at 100 ms, 22 s at divisor 5) a trace drops out of the fast path. Credit then
  falls to the anchor fallback, `tcw · TemporalSignature.now().similarity(anchor)`. That weight is 0.3, and
  `temporal_signature.py:92` takes `now()` from `time.time()`, which is the **host calendar**.
- **Anchor pruning.** It runs on `time.time()` inside `decay_eligibility` itself (`nac.py:3715`).

So for any delayed receipt past expiry, credit still depends on the wall clock. The v3 claim was right about the
effect for delayed receipts and wrong about the line. The correction overshoots: it says "don't decay on the wall
clock" and drops the wall-clock fallback entirely. #1361 §(c) keeps the anchor *similarity* on host time even after
S3b ("only age and expiry move").

**Failure scenario.** OD-EA12 lands as written with one eligible node and goes green on today's per-tick code. Then
#1361 S3a lands with τ_elig = 4.75 s, so a trace reaches the 0.01 floor after about 22 s of world time. At a
bio-faithful τ (DB-S9) it reaches the floor within about 2 s. Any receipt delayed past that is credited only
through the host-calendar similarity, so the same history credits differently depending on the time of day on the
host's machine. That is an O4 leak into learning, and no guard is red.

**Fix.**
- Replace "13×" with the real mechanisms: the share split, expiry into the fallback, and the fallback's
  host-calendar similarity.
- Respecify the exit test as #1361's G2b (two nodes activated at different world times; the same split between trace
  and anchor at two rates), plus a delay past the expiry at the faster rate.
- Add to the correction the ask #1361 doesn't cover: **anchor similarity from the perceived or machinery time, not
  `TemporalSignature.now()`**. Until then, delayed-settle credit is an OPEN divergence in §12.2.
- Prove the new test by running it against today's `decay_eligibility(0.9)` and watching it go red.

### DB-B3: the resume-on-arrival plant can't go red as specified

**Where:** §6.6 "Test: a plant that resumes on arrival makes a rerun with instant cached replies diverge, and goes
red"; §3.1 dial-invisibility test (unchanged); §6.2 test double.

**The problem.** DET-B1's fix had two load-bearing parts:
- a test-double `think` whose output **depends on agent state** (its step sequence number);
- an agent-state digest in the dial-invisibility compared set.

v3.1 kept neither. §3.1 still compares "percepts, receipts and kinds" and still says "a threaded host" (DET-S3 asked
to fix that). The scripted double's outputs come from a script. Resuming it early produces the same
`ThoughtOutput`, and the host holds intents to their landing ticks anyway, so world digests stay identical. The test
also speaks of "instant cached replies", but the response cache doesn't exist until tier A (§4.8), so it can't be a
[now] test.

**Failure scenario.** `phase1/lanes` ships a lane that resumes `think` on arrival, by mistake or because it is simpler.
Every [now] test stays green. At tier A, real Maxim's cycle-2 prompt depends on the resume tick (frame, recall,
staleness verdict), and every rerun misses the cache. That is DET-B1's original failure, now behind a green guard.

**Fix.**
- Require the double's `think` to fold the agent's step sequence and the staleness verdict into its output.
- Add the agent digest (from the worker, over the channel) to §3.1's compared set, and fix "threaded".
- Write the plant as: scripted wall-delay schedule, 1× vs 20×, a resume-on-arrival lane. The test must go red.
- Mark DET-B1 partial in the fold table until the plant has been run red.

---

## SHOULD-FIX

### DB-S1: the resume tick of a streamed speech segment is unpinned

**Where:** §6.6 lifecycle ("at the segment's landing tick the host resumes `think`"); §6.1 ("speech is a top-level
field emitted first"); §5.3.

**The problem.** A P2 reply streams speech into the world first, with syllables stamped and, under dilate, waited
for. The remaining fields (intents, writes, `next_actions`) arrive after the last syllable. The landing tick is the
speech *onset*, but `complete(text)` exists only after the stream ends. "Resume at the landing tick" is therefore
impossible for the commonest segment kind. Either the host waits at onset, which freezes speech it has already
started, or it resumes at some unstated later tick.

**Failure scenario.** Two implementations pick different resume ticks: the tick of the complete arrival, or the end
of the stamped speech. One is wall-dependent, so tier-2 reruns diverge on every conversation.

**Fix.** Resume at `max(landing tick, the tick of the last stamped syllable)`. Under dilate, the world waits *there*
for the rest of the reply. Log it as `reply_landed` only under floor-holding. Test it with a stream whose trailing
fields arrive late on the wall.

### DB-S2: the new records aren't registered, and the tier rule contradicts itself

**Where:** §6.6 (`reply_landed` "a host record a rerun consumes"; `floor_event` "a run with any lateness-caused event
is tier 3"; `agent_failed`; restart "an explicit host control record"); `boundaries.md` §6.1 record kinds and
authority, §6.2 `kind_rank`, §6.3 manifest tier rule and tier table, `thought_failed` reasons (`:383`: budget,
timeout, model error).

**The problems:**
- None of the four records appears in `boundaries.md`'s kind and authority table, `kind_rank` or the manifest's tier-3
  rule.
- `thought_failed(reason=parse)` isn't in the reason list.
- The worker's `PYTHONHASHSEED` and BLAS settings are "recorded in the log header", but §6.3's header lists only the
  host's BLAS thread count.
- `reply_landed` is consumed by a rerun, which only makes sense if floor-holding sessions rerun at tier 2. Yet
  `floor_event` declares them tier 3. By BF3-4 every live reply yields, so as written **no live session is ever
  rerunnable**, which is DET-S1's failure scenario. Nowhere is that stated as accepted.

**Failure scenario.** A co-op bug report arrives with log and cache. The rerun tool refuses it as tier 3, although
every wall-decided event is in the log. Or an implementer gives `floor_event` no `kind_rank`, and the log's single
ordering key is undefined for it.

**Fix.**
- Register all four records, with authority, `kind_rank` and reasons, in `boundaries.md` §6.1–§6.3.
- Decide the tier. The recommendation: a rerun **feeds** `reply_landed` and `floor_event` instead of re-deciding
  them, which makes a floor-holding session tier 2. Keep tier 3 for `agent_failed`, `abandon` and machine-decided
  failures.
- Put the worker environment digest in the manifest.

### DB-S3: the offset-and-scale test is red on correct code end to end, and blind to order

**Where:** §6.6, OD-EA11 ("two runs whose machinery clocks differ by an offset and a scale, with identical
perceived-time bins, must render byte-identical prompts … catches … a rendered order"); roadmap OD-A2 (unchanged:
"a sentinel time … raw, clock and date forms").

**The problems:**
1. **Scaling the machinery clock changes legitimate agent state.** Every decay (NAc after #1361, memory strength,
   drives) runs on it, so recalled memories and their order differ, and the prompts differ for a legitimate reason.
   Also, "identical perceived-time bins" can't hold under a scale unless the port is stubbed. End to end, the test
   is red on correct code; someone will "fix" it by loosening it.
2. **Order isn't caught.** A positive affine map preserves order, so a prompt that renders machinery order (an exact
   order between events 5 ms apart, which §3.2 says is unknown below about 30 ms) renders identically in both runs.
   The claim "catches a rendered order" is false.
3. **The roadmap row Maxim implements (OD-A2)** still has the unspecified-clock sentinel and no offset-and-scale test.

**Fix.**
- Split the test in two. End to end, use **offset only** (decays depend on Δt, so offset is invariant with the
  calendar off). At render level, use offset and scale on a frozen store snapshot, with the perceived-time port
  stubbed to fixed outputs.
- Drop the order claim. Add a planted near-simultaneous pair that must render as unordered.
- Update OD-A2.

### DB-S4: resume equivalence is a sentence, its test can't see the real hazards, and the hash seed is per run

**Where:** §6.6 "Resume equivalence … tested with the double [now]"; §6.6 environment (`PYTHONHASHSEED` "pinned per
run"); fold rows DET-S3 and DET-S5 ("folded") against row BD-14 ("decay on load, `monotonic` stamps across saves,
thread and set order … are in no design row").

**The problems:**
- DET-S5 asked for a contents list and promoted design rows. Neither landed, and BD-14's own row says so.
- The hazards are all in real Maxim, so the double can't exercise them:
  - per #1361 §(c), NAc's `_experience_us`, pending events and temporal anchors are session-scoped and "not
    persisted", so a mid-thought save drops the anchors;
  - monotonic stamps restart in a fresh spawn;
  - per-stream `random.Random` states have to be saved.
- A correction to DET-S5's premise: decay-on-load is **dormant by default** (`nac.py:4117`, `offline_wall_decay`
  False since 2026-10-18), so it is a hazard only if the option is set.
- `PYTHONHASHSEED` "per run" means a save loaded in a new session gets a different seed. Set-order paths then diverge
  from a continuous run, while a same-seed resume test stays green. DET-S3's two-hash-seed test on the worker path
  was dropped.

**Failure scenario.** Save during PFC cycle 2 and load tomorrow. The anchors are gone, so a delayed receipt's fallback
credit is zero, where a continuous run gives 0.3× similarity. A set-iteration path also orders differently under the
new seed. The double's resume test is green.

**Fix.**
- Write the agent-save contents list: machinery-clock value, stream states, the host header with held replies,
  cancel state, and anchors with pending events or an explicit "dropped at save" divergence.
- Add a strict red gate for resume equivalence against real Maxim.
- Pin the hash seed **per save**, not per run, and restore the two-seed worker test.
- Mark DET-S3 and DET-S5 partial.

### DB-S5: "only the modelled part of a gap" is the oracle BD-4 warned against

**Where:** §6.6 "No lateness reaches cognition as time … only for the **modelled** part of a gap;
lateness-caused extension is never written into another NPC's memory"; §5.1 (still "a duration"); §7.1 B-13.

**The problem.** The listener's percept is built to separate modelled hesitation from hardware lateness, a
distinction no real listener can make. BD-4 said: "NPC listeners can't tell lateness from hesitation; pretending they
can would be an oracle". The rule also contradicts B-13:
- A lateness-caused account ("let me think") and a yield are **world speech events**, logged as `speak` intents and
  audible on the sound channel. Either the listener perceives them, and lateness enters its memory as words, or the
  adapter censors a sound that physically happened.
- §6.6's "the listener-side rule keeps it out of other NPCs' memories" is true only of the gap category. It is false
  of the account and the late "about what you asked…" turn.

**Failure scenario.** A laptop co-op session. Every live reply yields (BF3-4), and every listener stores the accounts
and the late returns as heard speech. The cross-machine leak O12 forbids is intact, behind a rule whose text says it
is closed.

**Fix.** Choose honestly between two options, and name the cost of the choice:
- (a) Listeners perceive what was said and heard. Lateness enters memory through the account and the yield. It is a
  §12.2 Known gap, metered by BD-4's lateness meter, and the cure is latency.
- (b) Lateness-caused floor events are hidden from other NPCs' percepts. That is an OPEN oracle divergence against
  B-13, named as such.

Fix §5.1's "duration" either way.

### DB-S6: "1 s after the last filler or account" has no ceiling

**Where:** §6.6 "Yield timing (BF3-3)"; §4.7 (holds rate-limited per speaker, no per-hold cap); §12.1 item 5 (filler
propensity).

**The problem.** If each filler resets the 1 s clock, a high-propensity NPC holds the floor for as long as it keeps
filling. Nothing in the design bounds the number of fillers or the total hold in world time, except the host's
*wall* ceiling, which then ends the thought as `thought_failed`. Also, after an account the silence is one the account
has licensed. Applying Jefferson's ~1 s (to verify; about unaccounted silence) there is itself `[engineering]`.

**Failure scenario.** A filler-prone shopkeeper says "uh… um… uh…" for 8 s on a slow GPU, then fails the thought with
no answer and no yield.

**Fix.** Set a cap on floor-holding acts per turn and a total hold ceiling in world time, both in
`thought_budget.yaml`. Tag the post-account hold `[engineering]`.

### DB-S7: the unsaid remainder is discarded, so BF2-11's interrupted intention is lost silently

**Where:** §6.6 ("tokens streamed beyond them are discarded and never reach cognition") against §4.3 ("The unsaid
remainder is kept as an interrupted intention in the next thought's context"), unchanged and unpointed.

**The problem.** DET-B2 offered a deterministic route that keeps the intention: under dilate, let the cancelled call
finish (cache it whole), and give `think` the remainder past the delivered syllables. That is a pure function of the
complete reply. v3.1 took the other route, so the "as I was saying…" behaviour that BF2-11 added for faithfulness is
gone. §4.3 still promises it, and no divergence is recorded.

**Failure scenario.** A guard is interrupted mid-warning. He never resumes it, because the warning's content was
dropped, while §4.3 says he would.

**Fix.** Either adopt the complete-then-cut route under dilate, with floor-holding tier 3 or fed records, or record
the loss in §12.2 and edit §4.3.

### DB-S8: §12.1 item 6 implies floor-holding cures hardware dependence, which by BF3-4 it doesn't

**Where:** §12.1 item 6; §6.6 BF3-4.

**What is fair:** the dilate numbers (0.33×, 0.11×) match §4.5, and abandon's cost and the "statue" correction are
accurate.

**What is missing:**
- (a) "Silent late landing" costs more than listeners' perception. The **speaker's** own cognition becomes
  hardware-dependent: staleness verdicts at a `reply_landed` tick, the new-turn path, follow-up timing. The run is
  tier 3 (or needs DB-S2's fed records).
- (b) Every non-dilate option, OD-H5's floor-holding included, is hardware-dependent at L = 3 s, because every reply
  yields. The options differ in feel, not in whether O4 and O12 hold.
- (c) The dilate figures are the no-lever worst case. §4.5's lead-time and first-token levers aren't mentioned.
- (d) "Silent late landing for co-op" gives up O4 and O12 for co-op until latency improves. That should be named as
  a decision against recorded owner decisions, not a default.

**Fix.** Add (a)–(d) to the item, so the owner chooses with the full cost in view.

### DB-S9: push back on #1361's eligibility τ with Yagishita (the bio-faithful ask the fold missed)

**Where:** #1361 §Tau conversion (eligibility 4.75 s world, from `τ_eff` 9.49 passes × the 0.5 s step of a 2 Hz
fixture); §6.6 BF3-2.

**The point.** The time-based decay is right: eligibility traces are biochemical tags that decay in physical time
(Yagishita 2014, *verified*: 0.3–2 s), not per cognitive cycle. But #1361 converts τ from a fixture's poll rate, an
artifact of the harness, and gets 4.75 s. With a 0.01 floor that is about 22 s of trace, roughly 10× the
dopamine window. At Maxim's default 30 Hz loop, today's ×0.9 gives τ ≈ 0.32 s and an expiry near 1.5 s, which
happens to sit inside Yagishita's window. So "nothing changes" isn't even true of today's nominal robot.

**Fix.** A Phase 3 item under the push-back rule: "τ_elig in seconds from the striatal window, not from a fixture
rate". Bring the evidence (Yagishita 2014; the 30 Hz equivalence) to #1361 through Maxim's process. Once that lands,
delayed credit runs through the fallback or the 300 s buffer, which makes DB-B2's anchor ask load-bearing.

### DB-S10: earlier sections still contradict §6.6, without pointers

The rule "§6.6 wins" is stated once. But implementers of `data/agents/fatigue.yaml` and the OD-H5 draft will read
the sections that define the thing, and these still contradict it:
- §2.3 and §4.6: load is "world time spent in P1 and Pn", with no P1c and not modelled (DET-S7, BF3-5);
- §4.3: the unsaid remainder (DB-S7);
- §4.4 and O11a: "a yield at about 1 s";
- §5.1: "a duration"; Bortfeld *to verify*; the neural evidence for the repertoire ("§6.6: §5.1 is read so" is a
  reading instruction, not an edit);
- §3.1: "threaded", and the compared set;
- roadmap OD-A2: the sentinel.

**Fix:** edit each one in place, as §4.4 was.

---

## NIT

- **DB-N1 (§6.6 cache numbering):** "by thought request id" needs a per-segment id (PFC cycle n and follow-ups share
  a thought), and the order should use `npc_key`, not the allocator integer, so numbering survives a roster edit
  across a save.
- **DB-N2 (§6.6 `agent_failed`):** "its body processes go on". Body time is owned by the agent substrate in the
  worker (§1), and the worker is dead. Say what runs: world-owned body state only, or a host-side stand-in.
- **DB-N3 (§6.6 cancelled prefix):** §4.3 makes the stop a P0 reaction ("within a syllable or two"). The delivered
  prefix should be the syllables stamped before `C + stop latency`, not before C.
- **DB-N4 (§6.6 retrieval writes):** say which stamp applies under floor-holding (modelled or `reply_landed`), and
  what `apply` does with a retrieval write on a trace pruned between the cycle and the apply (drop and count). The
  host's "own memory only" gate can't check opaque trace ids; say that the agent's `apply` checks them.
- **DB-N5 (tags):** O'Connell & Kowal 2005 is untagged in §6.6. Roberts et al. 2006 measured listeners rating
  recordings, so "players hear" is an extrapolation; say so.
- **DB-N6 (P1c and the speed trait):** say which O12 domain scales P1c (decision onset, by the λ form), and whether P1c
  has its own load weight, as BF3-5 asked, or the kind's.
- **DB-N7 (§6.6 wording):** "a sentinel instant … checked in duration form" means nothing for an instant; the
  duration check is the offset-and-scale test's job. "Tier-1 replay reads the records": replay never runs agents, so
  it needs none of them. Say that the records are for reruns and meters.

## Push back on Maxim (CLAUDE.md)

These are owed, replacing OD-A19:
- **(a)** OD-A18 depends on #1361 S3a/S3b (OD-A1), cited as Maxim's plan.
- **(b)** Anchor similarity off `TemporalSignature.now()` (DB-B2). This argues against #1361 §(c)'s "only age and
  expiry move".
- **(c)** τ_elig from the striatal window (DB-S9). This argues against #1361's fixture-rate conversion.

`correction_1.md` should carry (a)–(c) and drop "13×" and "nothing changes on a robot" before it is sent.
