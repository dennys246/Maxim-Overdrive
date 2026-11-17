# npcs_and_sem.md v3 (3db82a8): Determinism and replay lens

**Reviewed:** `npcs_and_sem.md` v3, `boundaries.md` (§6.2, §6.3, §7 as changed), `embeddable_agent_DRAFT.md` v2,
roadmap Phase 3 (OD-A2, OD-A3, OD-A7, OD-A15, OD-A18, OD-H6), against `reviews/maxim_response_1/` (response.md,
response_2.md, reply.md, bio_determinism.md, synthesis.md, foldtable.py). Maxim cited at 7084f561, not re-read here.

**Counts:** 3 BLOCKER, 8 SHOULD-FIX, 5 NIT.

**The headline answer.** I found **no path that makes a tier-1 replay diverge.** The log carries every
`Simulation` input (intents with host-stamped times, `thought_failed`, `thought_cancelled`, controls). Replay never
runs an agent or opens the cache. Floor-holding fillers and yields enter as logged intents. Tier 1 holds.

The breaks are all in **tier 2 (rerun) and in O4 (time into cognition).** v3 made `think` a resumable function
but never says *when* the host resumes it, or *what* a cancelled reply contains. Both are now decided by wall
arrival. The O4 guard also checks the wrong clock and only checks instants.

---

## BLOCKER

### DET-B1: the tick at which `think` resumes is unspecified, and §4.4 implies "on arrival"

**Where:** §4.4 ("the lane runs it and the host resumes `think` with the reply"; "Early-held results and
deliberation continuations live agent-side"); §6.1 continuation row ("resume must decide staleness against the
current agent"); §6.3 barrier; `embeddable_agent_DRAFT.md` §2, OD-EA5.

**The problem.** Nothing fixes the world tick at which the host calls `think(continuation, reply)`. "Early-held
results live agent-side" only makes sense if `think` has already run to a `ThoughtOutput` before that output's
landing tick. In other words, it resumed when the reply arrived in wall time. Meanwhile `step` keeps running, and on
resume `think` reads the current agent:
- the frame pinned at the last `step` (§7.3);
- the stores, through the proposed in-`think` cognition tools (memory recall);
- drives;
- the staleness check against `basis`.

**Failure scenario.** At 1× a PFC cycle-1 reply arrives 0.4 world seconds in, after 4 steps. At 20× it arrives after
40 steps. Cycle 2's prompt then holds a different recalled memory and frame, so the kind or the output differs. The
`basis` staleness verdict also flips: stale at 20×, fresh at 1×. The NPC's cognition now depends on the dial, which is
exactly what §4.1 removes.

A tier-2 rerun replays cached replies instantly, so every resume moves to a different step. The cycle-2 request
then differs from the cached one, misses, and the rerun fails loudly. Every rerun of any thought longer than one step
breaks this way.

The §3.1 dial-invisibility test doesn't catch it. The test double is scripted, so its `think` output ignores agent
state, and the test checks percepts, receipts and kinds, not agent state. OD-EA5 in the draft is passed trivially by
any host that hides the delay. It constrains Maxim, not when Overdrive resumes.

**Fix.**
- State the rule: **the host holds the `Reply` value and resumes `think` only at the barrier of the segment's
  modelled landing tick** (under dilate: at `T + D`, waiting there if the reply is late). The PFC cycle cost P1c sets
  cycle *n+1*'s resume tick.
- "Early-held" then means host-held replies, not agent-side outputs. Say where they are saved: they are neither world
  log nor agent home today.
- Plant: a test-double `think` whose output depends on the agent's step sequence number. Resume-on-arrival must go red
  at 1× vs 20×.
- Add an agent-state digest to the dial-invisibility test's compared set.

### DET-B2: `cancelled(prefix)` carries a wall-dependent prefix into cognition

**Where:** §4.3 ("The unsaid remainder is kept as an interrupted intention in the next thought's context"); §6.1
request/reply row; the draft's continuation ("cancel status with the delivered prefix") and OD-EA8 ("records the
prefix as said").

**The problem.** The cancel is decided at a world tick C, which is deterministic. The prefix the host has *received*
by then is not: it is however many tokens the model streamed in the wall time before tick C.
- **Speech:** the spoken prefix is deterministic. Under dilate the world waits for each stamped syllable. But the
  "unsaid remainder" is received text minus spoken text, which is wall-dependent.
- **A cancelled PFC or plan call:** the whole prefix is wall-dependent.

**Failure scenario.** A guard is planning when he's addressed by name at tick C.
- At 1× the plan call has streamed 180 tokens by tick C. At 20× it has streamed 12.
- `think` gets `cancelled(prefix)`, and the next thought's context carries "as I was saying: …" with 180 tokens of
  intention in one run and 12 in the other.
- Different prompts follow, so different behaviour: a dial-visible channel into cognition (O4, §4.1).
- In a rerun the cache holds a complete reply or a partial one, but which prefix should be replayed is undefined, so
  the rerun either misses or quietly feeds a different prefix.
- OD-EA8 enshrines "the prefix as said" without saying it must be time-justified.

**Fix.** The prefix handed to `think` must be a pure function of the world timeline:
- the syllables stamped before C for speech, and empty (or a fixed marker) for a non-speech call;
- or the host lets the call finish (cache it whole) and truncates by modelled time.

Either way, the cache entry for a cancelled call stores the full output plus the deterministic cut rule. Test: cancel
at the same tick under a seeded wall-delay schedule, at 1× and 20×, and the next request must be byte-identical.

### DET-B3: the planted-render guard plants in the wrong clock, and can't see durations

**Where:** §6.1 clock-seam row; OD-A2, OD-A3 (roadmap); `embeddable_agent_DRAFT.md` OD-EA11 ("a planted
**perceived-time** sentinel never appears in a rendered prompt"); §3.1.

**The problem, in two parts.**
1. OD-EA11 plants the sentinel in the **perceived-time port**, which by design is the one source a prompt *may*
   contain. On a correct implementation that test is red. Or, if someone "fixes" it by having the port emit bins,
   it checks nothing about the machinery clock, which is the leak BD-12 was about. §6.1 and OD-A2 just say "a
   sentinel time" without naming the clock. The sentinel must go in the **machinery clock**.
2. Even planted in the right clock, a sentinel *instant* (unusual seconds, in raw, clock and date forms) catches only
   rendered instants. A builder that renders a **difference** of machinery reads passes:
   `f"last seen {now - t_seen:.0f}s ago"`, an "elapsed" field, or a recency sort shown with its gap.
   - The lint (`datetime.now`, `strftime`, `localtime`) doesn't touch float arithmetic either.
   - Maxim's own pushback says `f"{t.value}"` defeats a type guard, and the same defeats this one.

**Failure scenario.** After tier A, `context_pool` drops `[HH:MM:SS]` (OD-A3) but a memory summary says "12.4 s
ago", computed on the machinery clock. The planted-render test is green and the lint is green. Every NPC prompt
carries exact world durations, which violates O4 and §3.1's rule, with every guard passing. By CLAUDE.md, a test that
can't fail on the thing it guards is a BLOCKER.

**Fix.**
- Plant in the machinery clock (correct OD-EA11).
- Add a **metamorphic render test**: two runs whose machinery clocks differ by a constant offset *and* by a scaled
  elapsed time, chosen so the perceived-time port's output is identical. The rendered prompts must be byte-identical.
  That catches instants and durations alike, and no regex is needed.
- Keep the TZ-13 h test of §3.1.

---

## SHOULD-FIX

### DET-S1: floor-holding's lateness decisions aren't host records a rerun can consume; the tier rule omits them

**Where:** O11a, §4.4 ("What follows may track real lateness: logged, tier 3"); `boundaries.md` §6.3 (the rerun
manifest flags tier 3 only for machine-decided failures and `abandon`; the tier table lists "live models, abandon,
machine-decided failures").

**The problem.** The account at about 650 ms and the yield at about 1 s fire on whether the reply has *arrived* by a
world tick, which is a wall decision. After a yield the agent takes a different path: the late answer comes as a new
turn ("about what you asked…"), so its prompts differ. "Logged" doesn't say *as what*. The filler and account speech
are logged as world intents, but the host's decision that resumes the agent in "yielded" state is not named as a
record. The manifest's tier-3 rule doesn't mention floor-holding at all.

**Failure scenario.** A live co-op session is rerun with its cache for a bug report.
- With replies served instantly, no yield happens. The agent never enters the "new turn" path, so the next request
  misses and the rerun dies.
- Or the manifest claims tier 2 for a run that can't be one.
- Live play is the main mode, so in practice **no** live session is rerunnable.

**Fix.**
- Log every lateness-driven decision (account issued, yield) as a host control record with its tick, like
  `thought_failed`, and have the rerun feed those records to the agent instead of re-deciding them. Then a live
  session reruns at tier 2 from its log plus cache.
- Name floor-holding in `boundaries.md` §6.3's tier rule either way.

### DET-S2: cache occurrence indices collide across NPCs and follow execution order

**Where:** §4.8 ("Occurrences: keyed by `(content hash, occurrence index)`"; "actor, kind, timing and targets are
recomputed from the request … never read from the entry"); §4.4 ("Dispatch is by deadline").

**The problem.** The canonical request carries no actor, by design. Two templated NPCs (two guards with the same
persona) that see the same event at the same tick produce byte-identical requests. The occurrence index is assigned
as the thinking lane executes or receives them: deadline order, then whatever breaks ties, then arrival over two
pipes.

**Failure scenario.**
- Live: guard A gets occurrence 0 ("raise the alarm") and guard B gets occurrence 1 ("investigate").
- Rerun: B's pipe answers first, so B gets occurrence 0. The two answers swap, the world diverges, and nothing errors,
  because both entries hit.

**Fix.** Assign occurrence indices in canonical order: by thought request id `(tick, actor, n)`, never by lane
order. Test: two identical-request NPCs under reversed pipe latency give the same answers per actor.

### DET-S3: the shipped path (spawned workers, pipes, the merge) is outside every [now] determinism test

**Where:** §3.1 dial-invisibility test ("a threaded host as shipped"); §6.3 ("The test double runs in-process");
O13.

**The problem.** v3 changed the shipped path to one spawned worker per real agent. The dial-invisibility test still
says "threaded host as shipped", and the only agent that exists before Phase 4 runs in-process. So none of these is
exercised by a [now] test:
- the barrier's park and release over pipes;
- the merge of N workers' `StepOutput`s into the canonical key;
- the order the host sends releases and pushes down each pipe relative to a resume;
- the worker's environment.

CLAUDE.md requires a claim to be measured on the shipped path. The scrubbed worker environment is built explicitly,
but nothing pins or records two things in it:
- `PYTHONHASHSEED`: spawned workers get a random one, and Maxim's `set[str]` iteration then varies (BD-14.7);
- the worker's BLAS and OMP thread counts: the header records the *host's*, and the scrub removes `OMP_NUM_THREADS`.

**Failure scenario.** Tier A lands and real agents go into workers. A Maxim step path that iterates a `set[str]`
gives a different order per spawn, so tier-2 reruns diverge intermittently. Nobody wrote the different-hash-seed test
for the agent step, because the in-process double never showed it.

**Fix.**
- Make the test double runnable in a spawned worker over the same pipe protocol, and run the dial-invisibility and
  barrier tests with N workers under a seeded per-pipe delay schedule.
- Run the two-hash-seed test on the worker path.
- Put the worker's constructed environment (or its digest) in the rerun manifest.
- Fix §3.1's "threaded".

### DET-S4: a hung or dead worker freezes the world, and the host's decision is unlogged

**Where:** §6.3 barrier ("steps tick T+1 only when every agent is parked"); §4.4 liveness (the wall ceiling covers
only model calls).

**The problem and the failure.** Maxim's `step` loops forever on some input, or the worker dies (OOM, the latch
killing a forbidden call, a segfault in a native wheel). The barrier waits forever, so v2's "a hung model can no
longer freeze the world" is reopened by O13. Whatever the host then does (kill and freeze the NPC, respawn it from the
last save) changes every later intent of that actor, and no log record or tier flag says so.

**Fix.** A wall ceiling per park (host-only, like the model ceiling), ending in a logged `agent_failed(reason)`
record. Define the NPC's state after it (statue, or reloaded from a named save), flag the run tier 3, and add it to
the liveness test.

### DET-S5: the agent half of a save has no resume-equivalence contract

**Where:** §4.4 ("saved with the agent home (save v1)"); §6.2 ("the continuation as an opaque, versioned blob …
with a save/load round trip"); §6.1 continuation row ("the loop locals that aren't values yet"); fold row BD-14
(partial: decay on load and monotonic stamps "not yet in a design row").

**The problem.** A round trip of the blob only proves the bytes survive. What a save must hold for a load to continue
bit-identically is not listed anywhere:
- the machinery clock's value (BD-14.5: monotonic stamps restart per process, and every load is a fresh `spawn`);
- each keyed stream's `random.Random` state;
- host-held replies (DET-B1);
- in-flight cancel state;
- decay-on-load forced off (BD-14.4: `nac.py:4321` would prune learning by the wall time the game was closed).

Also, "loop locals that aren't values yet" can't be in a pickle-free frozen value. They must be made values first,
which is the census the draft schedules. Say so.

**Failure scenario.** Save during PFC cycle 2 and load a week later in a new worker. NAc decays by a week, the
monotonic stamps are wrong, and the stream state is reseeded. The NPC is a different agent from the one a continuous
run would have.

**Fix.**
- An agent-save contents list in §6.2 or `boundaries.md` §6.2.
- A **resume-equivalence test**: run continuously, versus save at every tick class (idle, mid-cycle, mid-speech,
  cancelled) then load in a fresh spawned worker under a different fake wall time and continue. The agent and world
  digests must be identical.
- Promote BD-14.4 and BD-14.5 from reply.md to design rows.

### DET-S6: listeners store the hesitation's duration, a time field in cognition

**Where:** §5.1 ("A listener stores the hesitation as a feature of the speech percept (a duration, a filler-present
flag)"), against §3.1 ("no … time field reaches cognition"; the schema test's name rule).

**The problem and the failure.** Under live floor-holding, the gap a listener hears *is* hardware lateness (O11a
says so). Storing it as a duration sends the exact gap, in world µs, into the listener's memory and prompts. A slow
GPU then teaches every NPC that its neighbours are reluctant, numerically, with no meter able to bound it. The schema
test would also go red on a field named `duration`, unless someone adds it to the exemption list, which is the wrong
fix.

**Fix.** The listener gets a coarse perceived bin (none, short, long) from the perceived-time port, or only the
filler-present flag. Then BD-4's social cost passes through a coarse sense, not a number.

### DET-S7: under live play, fatigue load counts hardware lateness

**Where:** §2.3 and §4.6 ("Load is world time spent in P1 and Pn × the kind's weight"); O11 ("a yield never feeds
fatigue"); §4.6 ("Never from `LLMEnergyTracker` … an NPC would tire faster on a slower GPU").

**The problem.** Under floor-holding the world keeps real time, so the *actual* world time spent in P1 includes the
GPU's lateness up to the yield. Only the yield itself is excluded. So fatigue, sleep pressure and, once OD-X2 earns
them, deliberation frequency and onset all depend on the host's hardware. That is the O12 and §4.6 bug coming back
through another door.

**Failure scenario.** The same save is played on a laptop and on a desktop. After a world day the laptop's
shopkeeper is measurably more fatigued, sleeps earlier and deliberates less.

**Fix.** Load uses the **modelled** phase durations (`D_gap`, `D_onset`, P1c cycle costs), never elapsed world time
in a phase.

### DET-S8: two fold rows claim more than landed (BD-13, BD-14)

**BD-13 "folded".** Overdrive asked for keyed draws so that "adding an NPC *or changing a cadence* never shifts
another stream" (reply.md §5; BD-13 bullet 1: draws within a stream depend on cadence). Maxim answered that a
`random.Random` per stream suffices. That fixes the cross-stream and cross-NPC isolation, but within a stream it is
still sequential, so cadence-dependence remains. v3 accepted this without saying so, and §3.4 now contradicts §6.1:
- it still says "Maxim's proposed `Rng` is sequential … Keyed substreams are an upstream ask (§8.2)";
- it still argues counter layout for Philox, and says `NUMPY_RANDOM_ALLOWED` is amended for Philox.

The consequence: paired substrate arms (§4.8, the one place pairing is claimed to help) lose correlation within a
stream from the first change in draw count, and §2.1's Δt test keeps bit identity only under fixed schedules.
**Fix:** mark BD-13 partial, record the accepted cost in §3.4 and §4.8, and reconcile §3.4 with §6.1. The keys are
Overdrive's own streams (Philox, keyed) versus Maxim's internal streams (per-stream `Random`, sequential).

**BD-14 "partial".** The row says the rest is "in `reply.md` §5", listing "LLMs at T = 0, file-system order", but
reply.md §5 mentions neither. BD-14.2 (a long-horizon scripted run plus a **static** AST ban on `time.*` and
`datetime.now` in Maxim's step-path set) appears nowhere: not in the row, OD-A2, OD-A3 or reply.md. OD-A3's lint
covers prompt modules only, and §1's sealed set is Overdrive's adapter, not Maxim's step path. **Fix:** list the
missing items honestly and put the static ban in OD-A2.

---

## NIT

- **DET-N1: `step` has three signatures.** §6.1 has `step(world_dt, frame)`, `boundaries.md` §7.1 has
  `step(now_tick, dt_ticks, frame)`, and the draft has `step(agent, world_dt_us, frame)`. §2.1's bit-identity rule
  depends on `dt` being integer ticks from a fixed schedule. Pick one, in integer units.
- **DET-N2: who sets the request's deadline and priority.** §6.1 puts them on the request value that `think`
  returns. §4.2 and TB2-S5 say segment times are host-computed from the cost model. Say the host stamps them from the
  kind, and that they are excluded from the canonical cache key (§4.8 lists neither way).
- **DET-N3: BD-16 is "folded", but two of its asks are absent.** It asked for a divergence tick reported per pair, and
  for the estimand (d_z, a paired JZS) to be pre-registered. §4.8 has d_z and the seed as the unit only. Add both to
  §10's experiment rules.
- **DET-N4: stream keys and state.** `stable_hash_64(seed, agent, stream)` in §6.1 and OD-A7 should say `agent` is
  the persisted `npc_key`, never Maxim's `"agent_0"`-style ordinal (BD-13 bullet 3). Each stream's
  `random.Random.getstate()` must be serialised pickle-free in the agent home.
- **DET-N5: the machinery clock's zero.** OD-A2 keeps "epoch seconds as today" on a float. Say how the host maps world
  integer µs onto it, and that world time 0 must not map to 0.0 until OD-I1 lands, or `x or time.time()` swaps in the
  wall clock at five sites.
