# Delta review of v3.1 (f839075): Executor and Wire integrity lenses

Reviewer: Executor + Wire integrity. Read: `git show f839075` (all eight files), every lens file in
`reviews/npcs_v3/`, `correction_1.md`, `reply.md`, `response_2.md`. Maxim was read only through
`git -C ../Maxim show origin/main:<path>` at 7084f561. `foldtable.py` was run on a `git archive f839075` copy in a
scratch directory, never on the worktree. Nothing in either repo was written except this file.

**Counts: 2 BLOCKER, 9 SHOULD-FIX, 8 NIT.**

**The verdict first.** The fold is substantial and mostly honest: §6.6 is real work, the generator works, and the NAc
correction is right about the traces. The table still overstates the fold, though, and by more than one or two rows.
Of the 8 BLOCKERs, 4 fully landed and 4 landed partially. Of the 26 SHOULD-FIX rows I sampled, 20 landed and 6 are
partial. That re-marks 10 "folded" rows, so the table's **165 / 9 / 1 becomes at most 155 / 19 / 1**. In the
sample, 10 of 34 rows were overstated (about 30%). At that rate the round-3 rows I didn't check hide more, though the
NITs are probably cleaner. Two new defects came with the fold. The worker command line `-I` silently cancels the
`PYTHONHASHSEED` pin (B1). And the resume-on-arrival test can't go red against the scripted double as §6.2
describes it (B2).

---

## 1. Fold faithfulness

### The eight BLOCKERs

| Id | Claimed | Honest | What I found |
|---|---|---|---|
| Arch3 B1 (no `apply`) | folded | **partial** | §6.1, §6.6, `boundaries.md` §7.1 and the draft have `apply`. But **§6.2, the `phase1/agents` PR spec, still says "`AgentPort`: `step`, `think` and `settle`, all called by the host"** (line 680), and §11.3's row repeats it. §6.2 doesn't point to §6.6, though §6.6's preamble says "the earlier text points here". `boundaries.md` §2's layer 5b still omits `ThoughtOutput` and the header type, which the fix asked for. That PR spec is exactly where B1's failure scenario starts (S1 below). |
| Arch3 B2 (continuation owner) | folded | **partial** | The header/body split is in §6.6 and the draft. But **where the header and host-held replies are saved is never stated.** Arch B2's fix said "host state *and the save*". §4.4 says only "the header lives in the host" and "never in the world log". §6.1's continuation row still lists budget counters and cancel status in one value, without the split. See S2. |
| Exec3 B1 / TB3-B1 (worker channel) | folded | folded | Subprocess plus socketpair, closed-kind JSON codec, budgets, one actor per channel, re-validation in the host, a planted pickle frame, and the double behind the channel are all in §6.6 and the `boundaries.md` §5.3 row. The new defect is B1, and the leftovers are S3 and S5. |
| BF3-1 (NAc mechanism) | folded | folded | §6.1, §6.6, OD-A18 ("after OD-A19"), OD-A19, draft PR 4a, OD-EA12 and `correction_1.md` all carry it. The correction leaves something out (S6). |
| DET-B1 (resume tick) | folded | **partial** | The rule is in (§4.4, §6.6). But the guard can't fail as written (B2). §3.1's dial-invisibility test still compares only "percepts, receipts and kinds", with no agent-state digest, and still says "a threaded host as shipped". The fix's "say where held replies are saved" didn't land (S2). |
| DET-B2 (cancelled prefix) | folded | folded | The prefix is the speech already delivered in world time, and streamed tokens are discarded (§6.6, draft §2, OD-EA8). The cache rule and the 1×/20× test are missing (N3). |
| DET-B3 (sentinel clock) | folded | **partial** | §6.1, §6.6 and OD-EA11 are right. **Roadmap OD-A2, the row Maxim reads as the ask, still says "a planted-render test (a sentinel time, TZ pinned, checked in raw, clock and date forms)"**: no clock named, no duration form, no offset-and-scale test. The commit touched that row to add the static ban, but didn't fix this part. |

**BLOCKERs: 4 folded, 4 partial.**

### SHOULD-FIX sample (26 of 43)

Folded as claimed (20): Arch3 S1, S2, S3, S6, S7, S8, S9, S10; DET-S2, S4, S6, S7, S8; Exec3 S2, S4, S5, S6; TB3-S1,
S7, S9.

Partial (6):
- **Arch3 S4.** `PYTHONHASHSEED` is "pinned", but the command line cancels the pin (B1). §5.2's registry sentence
  ("in-process objects from Maxim … covered without an input primitive") is unchanged. An amending paragraph was added
  elsewhere, so the two sentences now contradict each other.
- **Arch3 S5 / DET-N2.** The draft and §6.1 say the host stamps priority and deadline. **Roadmap OD-A14 still lists
  "priority and deadline fields" on the request**, and still says only `cancelled` and `truncated` "bypass the
  parse-failure template", which TB3-S1's fold contradicts.
- **DET-S1.** The fix asked for lateness decisions as host records **so that live sessions rerun at tier 2**, and for
  floor-holding in `boundaries.md` §6.3's tier rule. v3.1 instead says "a run with any lateness-caused event is tier 3
  for reruns". That rejects the fix without saying so. It also contradicts its own `reply_landed` line ("a host record
  a rerun consumes"). `boundaries.md` §6.3 is unchanged.
- **DET-S3.** §3.1 still says "threaded host". The pin doesn't work (B1). "Recorded in the log header" has no
  `boundaries.md` §6.3 counterpart, and no rerun-manifest entry for the worker environment. No two-hash-seed test is
  named for the worker path.
- **DET-S5.** The resume-equivalence test landed. The **agent-save contents list** didn't: the machinery clock's
  value, host-held replies, in-flight cancel state, and decay-on-load forced off (`nac.py:4321`). Only stream state is
  named.
- **Exec3 S3.** §3.4 and §6.6 now give one derivation, but **roadmap OD-A7 still says
  `random.Random(stable_hash_64(seed, agent, stream))`**, the function §6.6 says doesn't exist. This is the
  upstream-facing row.

I didn't sample the NIT rows. The round-1 rows the commit re-marked (TBR-4/5/12, Exec N5/N7, BD-6/19) check out where
I read them.

---

## 2. `foldtable.py`

- **Regenerates byte-identically.** On a `git archive f839075` copy it prints `175 ids (93 round 1, 82 round 3:
  {'architecture.md': 19, 'bio_faithful.md': 13, 'determinism.md': 16, 'executor.md': 17, 'trust_boundary.md': 17});
  {'folded': 165, 'partial': 9, 'not folded': 1}`. `diff` against the committed `npcs_and_sem.md` is empty.
- **The per-file counts match each lens file's own totals** (2+10+7, 1+7+5, 3+8+5, 1+6+10, 1+12+4 = 8 / 43 / 31), so
  extraction is complete for round 3.
- **Refuses a missing id:** deleting the `DET-S7` row exits 1 with `id with no row: DET-S7`.
- **Refuses a placeless row:** `"DET-S7": (F, "fatigue counts")` exits 1.
- **It does not check that a place exists.** `"DET-S7": (F, "§99.9 nowhere")` exits 0, and so does
  `(F, "see roadmap someday")`. I wrote a separate check that resolves every `§n[.m]` in `MAP` against the headings of
  the file it names. All of them resolve, but two are attributed ambiguously: Arch3 S10 ("`world_model.md` §10 …,
  §6.5", meaning npcs §6.5) and TB3-S3 ("`boundaries.md` §5.3, §6.6", meaning npcs §6.6; `boundaries.md` has no §6.6).
  See N1.
- **It always writes the target**, so no gate can run it as a check without dirtying the tree (Exec3 N8 is honestly
  partial).

---

## 3. `correction_1.md`

- **The NAc claim is now right about the traces.** `nac.py:1162` is `record_event`'s `now = time.time()` for the
  pending-event buffer (`temporal_window_seconds: 300.0` at `:439`, used at `:1327`). `nac.py:3707`
  `decay_eligibility(factor=0.9)` multiplies every trace by 0.9 per call. `agent_loop.py:806-840` holds
  `_NAC_PER_TICK_DECAYS` (six names: eligibility plus five siblings) and `_loop_bio_tick_maintenance`, called once per
  loop tick at `:3194`. The 13× figure checks: 0.9^6 / 0.9^30 ≈ 12.5.
- **But it overcorrects (S6).** The same credit path still reads the wall clock. `decay_eligibility` itself reads
  `now = time.time()` (`:3714`) to prune temporal anchors by wall age. `distribute_reward`'s temporal fallback credits
  through `TemporalSignature.now()` against each anchor (`:3625-3640`), normalised together with the fast traces.
  "Don't decay on the wall clock" is true of the traces only.
- **The other corrections are true.**
  - The template echo: `llm_fallback.py:395-400` quotes `'{question}'` built from the input, with wake words stripped.
  - The model doors: `bootstrap.py:623-631` builds `AdaptivePlanner(llm=llm)`, `adaptive_planner.py:487` calls
    `generate_structured`, and `tool_pain_bridge.py:806` calls `generate` and swallows the error at debug level.
  - The hash names: `utils/seeding.py` has `stable_hash_32` (`:105`) and `stable_hash_64_signed` (`:121`), and no
    `stable_hash_64`.
  - "Read-only think, which you accepted": `reply.md` §2 said every write leaves through apply/settle, and
    `response_2.md` §8 put generate-vs-apply into tier A. Fair.

---

## 4. Internal consistency

- **Deleted mechanisms still described:**
  - The 3-method port in §6.2 and §11.3 (S1).
  - O13's owner row: "scrubbed environment", "a pipe", "`spawn`" (S4).
  - §6.3, line 712: "latch engaged after the host pipe is open", and line 726: "pipe round trip per park". Both are
    flagged as superseded but left in place.
  - §3.1: "threaded host as shipped".
  - Roadmap OD-A7 (`stable_hash_64`), OD-A14 (request-carried deadline), OD-A2 (unnamed sentinel clock).
  - `boundaries.md` §6.1: "`memory_write` … recorded … after OD-A15" (now OD-A18).
  - No live `request_thought`, intent sink or in-process double remains outside superseded rows. The foundations fold
    rows are annotated in both files.
  - No wall-clock trace decay remains outside the correction's own quotes.
- **Roadmap Phase 4 vs O15a:** consistent. The entry needs OD-A1 to OD-A19 plus 1.4.0 and the decomposition slice.
  NIT N5 covers the range.
- **New ids:** OD-A19 and OD-EA9 to OD-EA13 are all defined. OD-EA3 is referenced only as "moved to OD-I3". OD-EA13
  is defined but is not in Phase 3's exit (N6). Five new **record kinds** are used in §6.6 but defined nowhere in the
  log schema (S3).

---

## BLOCKER

### B1. `python -I` ignores `PYTHONHASHSEED`, so the "pinned" worker hash seed is random (§6.6 "The process", "The environment"; `boundaries.md` §5.3 worker-channel row)

§6.6 specifies `Popen([sys.executable, "-I", "-m", <worker entry>], env=<allowlist>, …)` and puts `PYTHONHASHSEED`
("pinned per run and recorded in the log header") in that allowlist. `-I` implies `-E`, which ignores every
`PYTHON*` environment variable, `PYTHONHASHSEED` included. I checked this on the installed CPython 3.14.6: two runs of
`env -i PYTHONHASHSEED=7 python3 -c 'print(hash("abc"))'` agree, and the same two runs with `-I` print different
values (`4779385920746488553`, `-8364227347697631518`).

*Failure scenario:* `phase1/agents` builds the worker exactly as written. Every spawned worker draws a fresh hash
seed, so set-of-string iteration in Maxim differs per spawn (BD-14.7, Arch S4, DET-S3). Tier-2 reruns diverge
intermittently, while the log header records a seed that had no effect. The fix for Arch S4 and DET-S3 is defeated by
the line that claims it. A reader can't catch this from the text.

*Fold:* drop `-I` for `-s -P` (3.11+) and rely on the allowlisted `env` to exclude every other `PYTHON*` variable.
Alternatively, have the worker assert `sys.flags.hash_randomization == 0` and a known `hash()` value at start-up and
refuse otherwise. Add a test: two spawned workers with the same pinned seed agree on `hash("…")`, and a plant that
restores `-I` goes red. Say this in the engine-choice line.

### B2. The resume-on-arrival guard can't go red against the double as specified (§6.6 "Determinism at the edges", §6.2 test double, §3.1)

§6.6's test is "a plant that resumes on arrival makes a rerun with instant cached replies diverge, and goes red". It
diverges only if `think`'s output depends on agent state that changes between arrival and landing. DET-B1 said this
outright: "the test double is scripted, so its `think` output ignores agent state", and asked for a double whose
`think` output depends on the step sequence number, plus an agent-state digest in the compared set. Neither landed.
§6.2's double is "a real state machine" driven "from a script". §3.1 still compares "percepts, receipts and kinds".

*Failure scenario:* the host resumes on arrival (the natural implementation). A scripted double returns the same
`ThoughtOutput` whichever step it resumes at, so both runs match and the test is green. Real Maxim later reads the
recalled memory, frame and basis at resume, and its cognition depends on the dial. That is a test that cannot fail on
what it guards, a BLOCKER by the charter.

*Fold:* state that the double's `think` folds the agent's step sequence number and basis into its output. Add an
agent-state digest to §3.1's compared set. Prove the guard by planting resume-on-arrival and watching it go red.

---

## SHOULD-FIX

### S1. §6.2, the `phase1/agents` spec, still builds the three-method port (§6.2 line 680, §11.3)

§6.6 says "where it and an earlier section differ, this section wins, and the earlier text points here". §6.2 doesn't
point there, and it lists no `apply`, no header type and no worker channel. *Scenario:* Arch B1 again. The
implementer works from §6.2's bullet list (it is the PR's scope), and the adapter applies writes inside `think`.
*Fold:* rewrite §6.2's first two bullets to the §6.6 signature and types, and correct §11.3's row.

### S2. The host-owned header and host-held replies have no save location (§4.4, §6.6, `boundaries.md` §6.2–6.3)

The header "lives in the host … never in the world log". The agent home holds only the body. The save formats are
the world save (scene and log) and the agent home. So a save taken mid-thought persists the body but neither the
header nor any reply held for a later landing tick. *Scenario:* save during PFC cycle 2 with cycle 1's reply held
until tick T+4, then load. Either the header is rebuilt from nothing, which resets the chain budget (the exact Arch B2
attack, by saving and loading), or the request is re-issued live, which breaks the resume-equivalence test and tier 2.
*Fold:* name a host-side save section (a versioned `agent_host_state` beside the log, under the save gate) holding
each header and held reply. Give it golden fixtures, and add it to DET-S5's agent-save contents list along with the
machinery clock value, cancel state and decay-on-load off.

### S3. §6.6 adds record kinds the log schema doesn't have (`boundaries.md` §6.1 authority table, §6.3 tiers and manifest)

`agent_failed(npc, reason)`, `floor_event(…)`, `reply_landed(thought, tick)`, the restart-from-home control record and
`thought_failed(reason=parse)` are all used in §6.6. `boundaries.md` §6.1's table lists `thought_failed` with reasons
"budget, timeout, model error" only, and the other four not at all. §6.3's tier rule and rerun manifest don't mention
`agent_failed`, lateness events, the worker environment or `PYTHONHASHSEED`, all of which §6.6 says are "recorded in
the log header" or flag tier 3. *Scenario:* the sim-clock record decoder is a strict, closed-kind gate. The first
`agent_failed` the host writes is refused by its own log reader, or someone widens the reader without a version bump.
The intro rule says this part "never quietly extends" a boundaries interface. *Fold:* add the five kinds with their
emitters to §6.1, the worker environment and seed to §6.3's header or manifest, and `agent_failed` and lateness to the
tier-3 rule, with a record-format version note.

### S4. O13's owner row is now contradicted without a note (§0 O13 vs §6.6)

O13 says "a scrubbed environment … over a pipe … Workers start with `spawn`". §6.6 replaces all three
(`subprocess.Popen`, an allowlist, a socketpair) and calls "scrubbed" superseded. O6 got "*Its mechanism is corrected
by O6a*". O13 got nothing, and Exec3 N9's lesson, a dated note when an owner row's meaning shifts, applies. *Fold:*
add "*Mechanism pinned in §6.6 (v3.1): subprocess, not `multiprocessing`; an allowlist, not a scrub*" and flag it for
the owner. The intent (a fresh interpreter, no fork) holds.

### S5. The worker channel has no module, and the sealed set bans what it needs (`boundaries.md` §3 "second sealed set", §5.2; §6.6)

`engine.adapters.agents`, "minus one named host-only module (wall timeouts)", is under the core's banned list, which
includes `subprocess`, `socket`, `json` and `os`. §5.2 lets only registered gate modules do a transport receive. The
§5.3 worker-channel row names a contract but, unlike its neighbours, no gate module. *Scenario:* the implementer puts
the spawner and codec in `engine.adapters.agents`. The AST scan goes red, and the "fix" is to widen the one exemption.
Or the codec goes outside the registry and is never held to 100% branch coverage. *Fold:* name the module (for
example `engine.host.agent_channel`), register it in §5.2, list it as the sealed set's second named exemption, and say
which side the per-park wall ceiling lives on.

### S6. `correction_1.md` and OD-A19 leave out the wall-clock half of credit (`correction_1.md` §1; roadmap OD-A19)

Credit at settle is the fast traces (per tick) plus the temporal-anchor fallback. The fallback is wall-gated inside
the very function cited (`nac.py:3714` `now = time.time()` prunes anchors; `distribute_reward`, `:3625-3640`,
credits by `TemporalSignature.now()` similarity), and the two are normalised together. BF3-1's own fix named "(a) the
clock seam for the causal-link window **and the SCN temporal anchors**". The correction says the dependency is
"different" and gives only the per-tick half. *Scenario:* Maxim lands OD-A19, the exit test OD-EA12 passes on the fast
traces, and credit still varies with dilation through the anchor share. *Fold:* one sentence in the correction and in
OD-A19: the anchor fallback reads the wall clock (`:3714`, `:3625-3640`) and closes with OD-A2/OD-A5. Make OD-EA12
compare total credit under a dilated machinery clock too.

### S7. OD-A19 is a behaviour change on the robot path, presented as engineering (draft header "claims no behaviour"; PR 4a; `correction_1.md`)

×0.9 per tick becoming `exp(−Δt/τ)` on the machinery clock, which defaults to the wall clock for robots (OD-A2),
changes every robot's credit whenever its tick durations vary. Maxim's loop ticks vary with model latency. The
correction's "on a robot at a fixed loop rate nothing changes" is the exceptional case, not the default. PR 4a has no
parity guard, and PR 4's bit-identical guard comes after it. *Scenario:* Maxim's plan review rejects PR 4a as an
unregistered learning-rule change, and OD-A18 then has no dependency to land on. *Fold:* either keep per-tick
semantics on the robot driver (Δt in ticks there, so the robot is bit-identical) and say so, or tag OD-A19 as
behaviour-changing with the experiment Maxim's process requires. State which in the draft and the correction.

### S8. "No `HOME`" doesn't contain `~/.maxim`; it falls back to the real home (§6.6 "The environment"; §12.1 item 1)

With `HOME` unset, `os.path.expanduser("~")` and `Path.home()` fall back to the password database. Run under
`env -i … python3 -I`, both return `<home>`. Maxim has 65 `expanduser`/`Path.home()` sites (for example
`api.py:179`, `Path.home() / ".maxim"`). §12.1 item 1 claims the allowlist closes guests' words reaching the owner's
`~/.maxim` (TBR-13). *Scenario:* a still-global store (one of the ten families) resolves `~/.maxim/...` in the worker
and writes guest-derived provenance to the owner's real home. *Fold:* set `HOME` (and the `XDG_*` variables) to the
agent home rather than unsetting it. Add an O14 no-effect test plant: a `Path.home()` write must land under the agent
home.

### S9. DET-S1's fold reverses its fix without saying so (§6.6 floor events; `boundaries.md` §6.3)

Covered under §1 above. Either adopt the fix (rerun feeds `floor_event` and `reply_landed` records to the agent, so
live sessions reach tier 2) or record the rejection as a decision for the owner ("live floor-holding sessions are
never tier 2") and mark DET-S1 partial. Today the text says both.

---

## NIT

- **N1 (`foldtable.py`).** It accepts any `§` or the word "roadmap". Resolve each `§n[.m]` against the cited file's
  headings, and prefix each file explicitly. Two rows are ambiguous today (Arch3 S10, TB3-S3). Add a `--check` mode
  that diffs without writing, so the gate can rerun it.
- **N2 (`embeddable_agent_DRAFT.md` title).** It says "(v2)", while the status says v2.1.
- **N3 (DET-B2).** Say the cache entry for a cancelled call stores the full output plus the deterministic cut rule.
  Add the test: cancel at one tick under a seeded wall-delay schedule, at 1× and 20×, and the next request is
  byte-identical.
- **N4 (§6.6 port).** `think(handle, …)`: `handle` is never defined (the thought id from the header?).
- **N5 (roadmap Phase 4 entry).** "OD-A1 to OD-A19" spans OD-A13, which moved to OD-I3. OD-I3 itself, which must land
  before PR 2, isn't named.
- **N6 (roadmap Phase 3 exit).** It lists OD-EA5 and OD-EA10 to 12 but not OD-EA13 (model doors fail closed), which
  this fold added.
- **N7 (§12.1 item 1, roadmap Phase 4).** "A strict red gate refuses guest joins" mixes two things. A strict `xfail`
  is a known-broken test. What's described is a runtime refusal (green) plus five tests that are red until they pass.
  Say which. It is also owned by `phase1/protocol` (row 6), before the worker channel exists (row 9b).
- **N8 (§6.6 host latch, TB3-S7).** "The host imports … `maxim` itself only in workers" conflicts with today's
  `sem_env/bridge.py::to_maxim_entity` and with CLAUDE.md's SEM-bridge rule, both of which build Maxim `Entity`
  objects in the host. Say that the bridge moves to the worker side, and when.
