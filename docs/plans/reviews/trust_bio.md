# Review of `foundations_plan.md` (72bf36c): Trust boundary and Bio-faithful integration

Reviewer: one of seven independent readers. Lens: trust boundary and bio-faithfulness, as they bear on the plan's
ordering and promises. Read: `docs/plans/foundations_plan.md`; `npcs_and_sem.md` v3.1 §0, §1, §2.3, §3, §4, §5,
§6.1–§6.6, §12; `boundaries.md` §5 and §7; `world_model.md` §10; `roadmap.md` Phase 1, 3 and 4; all three files in
`reviews/npcs_v3_1/`; `reviews/maxim_response_1/correction_1.md`; `research/speed/individual_differences.md`; the
headings and contested-evidence sections of `research/time/`. Maxim read only with `git show origin/main:<path>` at
6fee7377 (`docs/plans/experience_clock_decay.md`, `models/language/profile_loader.py`, `tunnel/keys.py`,
`hivemind/signing.py`, `comms/api.py`). I edited nothing except this file.

**Counts: 3 BLOCKER, 9 SHOULD-FIX, 6 NIT.**

## Verdict

Where the plan sets an order, it doesn't expose anything early. No step before step 11 runs real Maxim against a
guest, and step 7 builds against the scripted double behind the real worker channel. That is the right shape. The
bio-faithful commitments survive in the decision rows: three clocks, no time field reaching cognition, the speed trait
in world time, fatigue counted on modelled durations, floor-holding as `[engineering]` behaviour with no
neural claim.

The trouble is in what the plan promises:

- Two of the five red-first tests, as written, can't go red against the double (B1), and a third isn't a
  `phase1/agents` test at all (S3).
- The guest gates have no place in the step table, and step 11's "blocked by" column leaves them out (B2).
- O17 is recorded as decided, but it can't be built without an owner decision the plan never lists (B3).
- Step 1 sends Maxim a correction that carries a new citation error and asks a question Maxim's own plan already
  answers (S1).
- `data/agents/` lands in step 7 with *to verify* numbers, and nothing verifies them first (S6).

---

## BLOCKER

### TB-B1. Red-first tests 2 and 4 pass against the scripted double whatever the code does

**Where:** plan §3, red-first tests 2 and 4; `npcs_and_sem.md` §6.2 (the double is "a real state machine" driven "from
a script"); `architecture_trust.md` ATR-B2; `determinism_bio.md` DB-B3; `executor_wire.md` B2. Charter: "a test that
cannot fail is a BLOCKER".

**Test 2 (the worker can't reach the owner's home).** The worker in `phase1/agents` runs the scripted double, which is
Overdrive code and never calls `Path.home()`, `expanduser`, `tempfile` or an XDG resolver. A "no-effect test that
covers reads as well as writes" therefore finds nothing outside the agent home, whether or not `HOME` and `XDG_*` are
set. It stays green on exactly the bug it exists to catch: `HOME` unset, falling back to the password database.

The stakes are higher than ATR-B2 says. On 6fee7377, `tunnel/keys.py:52` (`key_file_path`, used by `hivemind/signing.py`
for the signing **private key**) and `profile_loader.py:133` (`profiles_config_path`) both resolve
`XDG_CONFIG_HOME` or else `Path.home()/".config"/"maxim"`. So the fallback reaches the owner's **keys** as well as the
model profiles. This is the "host's keys" exposure, and the test as written can't see it.

**Test 4 (resume at the landing tick).** DB-B3 named two load-bearing parts:
- the double's `think` output must depend on agent state (its step sequence and the staleness verdict at resume);
- an agent-state digest must be in the compared set.

The plan keeps only the digest. If the double's state doesn't record the step at which `think` resumed, resuming on
arrival leaves its digest unchanged. The plant stays green, which is DB-B3's failure scenario again.

**Failure scenario:** `phase1/agents` ships with all five tests green. At tier A, real Maxim in the worker resolves
`~/.config/maxim/` from the password database, builds a llama backend from the owner's `profiles.yml`, and can read
the mesh and signing keys. Separately, a lane that resumes on arrival changes real Maxim's cycle-2 prompt. Both guards
were green from the day they merged.

**Fix:**
- **Test 2:** run a probe in the spawned worker that calls `Path.home()`, `os.path.expanduser("~")`,
  `tempfile.gettempdir()`, and Maxim's own `profiles_config_path()` and `tunnel.keys.key_file_path()`. pymaxim is
  installed in the gate via `[maxim]`, and these are pure path functions. Assert that each result is under the agent
  home. Keep the `open` audit hook, but add a **planted** read of a file under the host's real home that the hook must
  report.
- **Prove test 2:** remove `HOME` from the allowlist and watch it go red; then do the same with `XDG_CONFIG_HOME`.
- **Test 4:** state that the double folds its step sequence at resume and the staleness verdict into its
  `ThoughtOutput` and its digest.
- **Prove test 4:** plant resume-on-arrival under a seeded wall-delay schedule at 1× and 20×, and watch it go red.
  Record the red run in the commit message, as the standard requires.

### TB-B2. The guest gates have no step, and step 11 isn't blocked by them

**Where:** plan §3 (steps 1–11), §5.1 item 1 ("Guest sessions: decided"); `roadmap.md` Phase 4 (the guest-join
refusal is "owned by `phase1/protocol`"); `boundaries.md` §5.3 (the guest-text gate, handshake, token, `Origin` and
joins all land in `phase1/protocol`); `world_model.md` §10 row 6.

**The gaps:**
- The plan's table never mentions `phase1/protocol`, though that PR owns:
  - the loopback bind, `Origin` refusal and per-launch token;
  - `engine.text.player_text`, the line-separator and Cf gate (O14 gate 4);
  - the runtime refusal of guest joins while real-Maxim NPCs are live.
- O18 has no home in any PR. `roadmap.md` Phase 4 still calls remote-egress refusal "proposed for the owner", which is
  stale against O18.
- O17's purge: types are promised in `phase1/agents` (§6.6) but appear in none of step 7's tests.
- Step 11 ("Phase 4's first real NPCs") is blocked only by "Maxim tier A, OD-A1 to OD-A18, and the 1.4.0 cut". Under
  O16, Phase 4 includes co-op. So the plan's dependency graph lets the first real NPCs run in a guest session with
  none of O14's six gates, the OS-sandbox decision, or O17's purge as predecessors.

The plan says the linked document wins. But the plan is the one place that records "what blocks what", and on this
point it is the weakest link.

**Two owner questions the plan silently drops:**
- **The OS sandbox for guest sessions, and refusing guest sessions with real NPCs on Windows** (§6.6, §12.1 item 1,
  TB3-S6). Plan §5.1 item 1 reads "decided (O14, plus O18)", which hides it.
- **ATR-N7:** the worker runs as the user, so it can read the per-install HMAC key that guards agent homes. Without a
  sandbox, a compromised worker can forge a home that a later load trusts. That makes the sandbox question
  load-bearing for agent-home integrity, not only for guests.

**Failure scenario:** a session picks up the plan cold, as its preamble intends, and starts Phase 4's co-op with
real NPCs once 1.4.0 ships. `phase1/protocol` has landed without the join refusal, because nothing in the plan asked
for it. A guest's words then reach a worker that has no purge path, and a remote model if one is configured.

**Fix:**
- Add `phase1/protocol` to the step table, in its `world_model.md` §10 position, with the join refusal, the
  guest-text gate and the O18 default named.
- Split step 11 in two:
  - **11a, real NPCs, single-player:** blocked by tier A and 1.4.0.
  - **11b, guest sessions with real NPCs:** blocked by O14's gates 1–5, O18's disclosure (with its wording, still
    unwritten per §5.1 item 2), O17's purge (B3), and the owner's answer on the OS sandbox.
- Restore the sandbox question (with ATR-N7) to §5.1 as open.

### TB-B3. O17 is recorded as decided, but the purge can't be built without an owner choice the plan never lists

**Where:** O17; plan §5.1 item 7; `npcs_and_sem.md` §5.2 ("replay must reproduce who heard what"; the intent log holds
`speak` text); §4.8 (the response cache holds the canonical request, which contains guests' words, and is
"excluded from bug reports **by default**"); ATR-S6; CLAUDE.md ("Replays are first-class. The intent log plus the
scene and rig reproduce any session").

**Where guests' words live:**
- agent stores;
- the opaque continuation body;
- the response cache;
- saves;
- the immutable intent log.

**Problems with the promise:**
- The log is the backbone of replay and of the save format. Purging a guest's `speak` text from it breaks replay of
  that session. Keeping it breaks O17.
- ATR-S6 asked for this exact choice to go to the owner (redaction records, or refusing replay of purged sessions).
  It isn't among the plan's open questions.
- Two of O17's wordings conflict with the design:
  - "Never shipped in a bug report" is stronger than the cache's "excluded by default".
  - It also conflicts with §12.1 item 4's still-open "should the reporter choose?", unless item 4 is limited to
    non-guest speech.
- The purge has no channel message (`purge` isn't among the closed host-to-worker kinds).
- Provenance is self-reported by the worker. The host needs to compute a lower bound itself (ATR-S6), or a derived
  write that drops the field survives the purge.

**Failure scenario:** a guest asks for a purge. The agent stores are cleaned, but the intent log, the response cache
and the saved continuation body still hold the injected line. A bug report from the "reporter chooses" path ships
it. Or replay of that session silently diverges, which breaks the replay standard.

**Fix:**
- List the purge-versus-replay choice as an open owner question in §5.1, with ATR-S6's two options and their costs.
- Name O17's reach: stores, continuation bodies, cache, saves, log.
- Make "never in a bug report" apply to the cache and agent homes whenever guests were present, not "by default".
- Put the `purge(actor, session)` kind and the host-computed provenance lower bound in step 7's scope, since that PR
  freezes the codec's kinds with golden fixtures. Adding them later costs a version bump.

---

## SHOULD-FIX

### TB-S1. Step 1 sends Maxim a correction with a new citation error and a question Maxim's plan already answers

**Where:** plan §3 step 1 ("blocked by nothing"); `correction_1.md`; Maxim `docs/plans/experience_clock_decay.md` at
6fee7377.

**Errors in the draft:**
- **The τ figure is wrong.** It says S3a's trace constant is "about 4.75 s on the 10 Hz figures". #1361 derives it
  from Exp 30's **2 Hz** fixture: τ_eff 9.49 passes × m = 0.5 s (§Tau conversion; `test_s0_tau_conversion_inputs`).
  A note whose purpose is to correct a citation error shouldn't carry a new one.
- **The anchor question is already answered.** It asks whether the anchor fallback "is in S3a's scope". #1361 §(c)
  answers that: S3b moves anchor age and expiry onto the experience clock, and "`TemporalSignature`'s SCN phases
  still score anchor *similarity* on host time … only age and expiry move", recorded as "host calendar by design".
  The honest message is push-back against that recorded decision, named, with the O4 evidence: delayed credit past
  expiry depends on the host's time of day (DB-B2). A question about scope doesn't do that.
- **The τ point names no decision.** It is framed as a question ("is the longer constant deliberate?") and doesn't
  name the decision it argues against (#1361 Q1, "taus … anchored on Exp 30's fixture regime"). CLAUDE.md's push-back
  rule asks for both.
- **The offset-and-scale test is unsplit.** The planted-render bullet still asks for an "offset-and-scale case"
  without DB-S3's split. End to end, a scaled machinery clock legitimately changes decays and recall, so the test as
  sent is red on correct code. Ask for offset only end to end, and offset and scale only at render level on a frozen
  store.

**Fix:** correct these four points before sending, and make step 1 "blocked by this fix".

### TB-S2. "Credit depends on the tick rate … closes with OD-A1" overstates what #1361 delivers, and the push-backs have no Phase 3 rows

**Where:** plan §5.2 (bold note); `npcs_and_sem.md` §12.2; DB-B2, DB-S9 (push-back items (b) and (c)).

**What #1361 covers and doesn't:**
- S3a fixes the trace decay.
- S3b moves anchor age.
- Anchor similarity stays on the host calendar by design. So for any receipt delayed past trace expiry, credit still
  depends on wall time after OD-A1 lands. That is an O4 leak into learning.

**The bio-faithful case for τ_elig:** τ_elig should come from the striatal window (Yagishita 2014, 0.3–2 s,
*verified*), not from a harness poll rate. Once it does, delayed credit runs through the fallback, which makes the
anchor ask load-bearing.

**Missing rows:** CLAUDE.md says each push-back is "an item under Phase 3". Neither item (b) nor item (c) has a row,
and the plan's §4 lists only `correction_1.md`.

**Fix:**
- Add two Phase 3 rows: "anchor similarity from the perceived or machinery clock, against #1361 §(c)" and "τ_elig
  from the striatal window, against #1361 Q1".
- Rewrite §5.2's note: the tick-rate dependence closes with OD-A1. The host-calendar dependence of delayed credit
  stays OPEN until the anchor row lands.

### TB-S3. Red-first test 5 can't be red-first in `phase1/agents`; it is a strict red gate against Maxim

**Where:** plan §3 test 5; OD-EA12.

The scripted double has no NAc, so a test of credit shares and trace expiry can only run against pymaxim's
`decisions/nac.py`.

**What follows:**
- It can't be made green by any `phase1/agents` code. It flips only when #1361 S3a and S3b land, and its expiry half
  only when TB-S2's anchor row lands.
- Calling it red-first in that PR invites someone to "make it pass", either by stubbing NAc or by loosening it.
- One combined gate would also hide which upstream piece landed.

**Fix:**
- Keep it, as two `xfail(strict=True)` gates against installed pymaxim, each with its reason:
  - shares at two divisors, flipping with S3a;
  - expiry into the fallback at two rates, credit by world time, flipping with the anchor row.
- Prove both red on today's `decay_eligibility(0.9)`.
- Say in the plan that these are compat gates, not tests `phase1/agents` turns green.

### TB-S4. Real-Maxim red gates must run only inside the worker, after test 2 is green

**Where:** §6.2 ("Real Maxim behind `engine.adapters.agents` is a strict red gate"); O10.

**Why it matters:** an `xfail` test still runs its body. If any real-Maxim red gate instantiates an agent
**in the pytest process**, it runs with the developer's real `HOME` and full environment, with no offline latch. That
environment includes any provider key in the shell, `~/.config/maxim/` and its keys (TB-B1), and the in-process llama
path. It also risks an LLM or network call in tests, which CLAUDE.md forbids. Nothing in the plan orders these gates
after the worker allowlist exists.

**Fix:** state in step 7:
- every real-Maxim red gate builds its agent only inside a spawned worker with the allowlist and `MAXIM_OFFLINE`;
- tests 1–3 are green before the first such gate is written;
- a test asserts that `maxim.runtime` and `maxim.agents` are absent from the pytest process's `sys.modules` after the
  agent suite (ATR-N5, extended).

`tests/test_sem_compat.py`'s type-only import stays as it is.

### TB-S5. The precedence rule makes the frozen §6.6 text win over its own known-issues list

**Where:** plan preamble ("where this file and a linked document disagree, the linked document wins"); O19; §6.6.

**What the frozen text still says:**
- `-I` and "no `HOME`";
- "sends a refused frame is killed", which lets a guest switch off any NPC by coaxing a Cf character (ATR-S3);
- inherited stdio, which sends guest words to the host's stderr and terminal (ATR-S1);
- the whole world frame shipped to the worker, so guests' display names reach every NPC's process (ATR-S9);
- no body, home or rlimit budgets (ATR-S10);
- no `hello` or `purge` kinds (ATR-N2, ATR-S6).

**Why this is serious:** `phase1/agents` builds exactly this code, with golden fixtures that freeze the codec. O19
says the SHOULD-FIXes become tests "when `phase1/agents` touches it". It touches all of these.

**Fix:**
- Add one sentence: for the agent half, a finding in `reviews/npcs_v3_1/` overrides the frozen §6.6 text it
  contradicts.
- List the trust findings step 7 must resolve, as a test or a fixed codec kind, before its fixtures freeze:
  ATR-S1, S3, S6 (kind and lower bound), S8 (snapshot save, cancel pending intents), S9 (per-perceiver frame),
  S10, N1, N2.

### TB-S6. *To verify* numbers enter `data/agents/` in step 7, and their verification is scheduled for after it, or never

**Where:** plan step 7 (§6.2: "`data/agents/` timing, speech, fatigue and thought-budget files"); step 10 (the
calibration ledger, "proposed, not designed", blocked by step 5 only, and blocking nothing); the npcs header rule
("*to verify* … to be checked before it enters `data/`").

**Values headed for those files that are still *to verify*:**
- `D_onset` 0.6–2 s;
- speech rate of 4–6 syllables/s, and syllables of 200–250 ms;
- Jefferson's ~1 s yield (O11a; Jefferson 1989);
- the reaction-time "approx." figures (§3.2: "'approx.' there is *to verify* here");
- Schegloff's stop latency;
- the fatigue weights' support (Kurzban 2013, Boksem 2005);
- the Process S load term (Huber 2004, Porkka-Heiskanen 1997).

**Fix:** pick one before step 7:
- (a) a verification pass on exactly the values step 7 writes, blocking step 7;
- (b) step 7 ships each value with a provenance tag (`verified` / `to_verify` / `engineering`), and a loader test
  fails on `to_verify` outside a fixture. That would be the ledger's first lint, so make step 10 block step 7.

`world_model.md` §11's physics numbers need the same treatment in their PRs. The plan doesn't schedule them, which is
outside this lens but worth a row.

### TB-S7. O16 gives up O4 and O12 in co-op, and the plan doesn't say so; §6.6 hides it behind an oracle

**Where:** O16 ("silent late landing in co-op"); O12 ("never reads the hardware"); §6.6 ("only for the **modelled** part
of a gap; lateness-caused extension is never written into another NPC's memory"); DB-S5, DB-S8(d).

**What silent late landing does:**
- **To the speaker:** its reply timing, staleness verdicts and new-turn path depend on the host's GPU. That is O12's
  forbidden channel, by the owner's decision.
- **To listeners:** they hear a silence of the modelled length plus the lateness. §6.6 says only the modelled part
  reaches their memory. No real listener can split those two, so the rule is an oracle against B-13 (BD-4 warned
  against exactly this).

Neither cost is recorded:
- the plan lists O16 as decided, with no note that it overrides O4 and O12 for co-op;
- the DB-S5 choice ((a) listeners perceive the lateness, a Known gap; or (b) hide it, an OPEN oracle divergence) is
  in no owner list.

**Fix:**
- Annotate O16 in the plan: "an explicit exception to O4/O12 for co-op until OD-H5 and latency close it".
- Add DB-S5's choice to §5.1 as open.
- Point §6.6's sentence at it until the choice is made.

### TB-S8. O12 is applied to conversational gaps at full strength while the evidence for that is open

**Where:** O12 ("scales the modelled onset under either latency policy"); §4.2 (P1 in conversation is `D_gap`); plan §5.1
item 5 ("the owner said to take all four but it isn't recorded"); `research/speed/individual_differences.md`.

**The evidence:** the research finds no study linking lab speed to conversational gaps. In the Fisher corpus the pair
explains 41.5% of a speaker's gap variance and the speaker 12.8% (Cavalcanti & Skantze 2025, *verified*).

**The conflict:** as recorded, O12 multiplies `D_gap` by the full trait. Item 5's "weak loading on gaps" is what the
evidence supports, and it isn't a decision yet. So the decided row overstates the science, and step 7's `timing.yaml`
would encode the overstated version.

**Fix:** record item 5 as O20, as the owner's earlier answer implies, before step 7 writes the speed spread. Or have
O12's text defer to item 5 for P1-in-conversation.

### TB-S9. Step 7's order skips the PRs its trust promises rest on

**Where:** plan step 7 ("blocked by step 6"); `world_model.md` §10 (9b comes after 4 sim-clock and 6 protocol; the
thinking lane is in row 10, `phase1/lanes`); `npcs_and_sem.md` §6.2 ("after `phase1/sim-clock`"; puts the thinking lane
in `phase1/agents`); roadmap Phase 1 ("after the clock").

**Why the order matters here:**
- The host's stage 1 for worker speech uses `engine.text.player_text`, which lands in `phase1/protocol`. If step 7
  runs right after `phase1/gates`, "everything re-validated in the host" has no speech gate to call.
- Test 4 needs the thinking lane and a wall-delay schedule. Two documents disagree on which PR owns them, so it isn't
  clear that test 4 can run in step 7 at all.

**Fix:**
- Set step 7's "blocked by" to match `world_model.md` §10: sim-clock and protocol at least.
- Settle which PR owns the thinking lane. If it is `phase1/lanes`, move test 4 there and say so in O19's list.

---

## NIT

- **TB-N1 (O11a row):** "a yield at about 1 s" predates BF3-3's correction (1 s of silence after the last filler or
  account; the account's onset a parameter in 600–1000 ms) and has no ceiling on fillers or total hold (DB-S6).
  Carry the corrected wording, and the `[engineering]` / *to verify* tags, into the plan's row.
- **TB-N2 (O4, OA5 rows):** the mental-fatigue drive and its sleep-pressure load term are `[engineering]`, consistent
  with contested accounts (Wiehler 2022; Kurzban 2013 *to verify*). The plan's rows read as plain decisions. Add the
  tag so no one cites them as biology.
- **TB-N3 (test 1):** "must match the pinned seed" should say what it's compared against (a reference child spawned
  with the same seed; the host's own hash seed may differ) and per what. DB-S4 shows "per run" breaks a save loaded in
  a new session. Pin it per save.
- **TB-N4 (O14 gate 2):** the O14 row and roadmap Phase 4 still say the no-effect test covers "file writes". Test 2
  extends it to reads. Align both, so Phase 4's gate list isn't weaker than step 7's test.
- **TB-N5 (guest-text gate):** ATR-N3 is an owner decision with no place in the plan. Refusing all Cf characters also
  refuses ZWNJ and ZWJ, which Persian and Indic spelling and emoji sequences need, and NFC should run before the
  length cap. Add it to §5.1 for `phase1/protocol`.
- **TB-N6 (plan §5.1, last line):** "The text of items 2, 6 and 7 in §12.1 still reads as open" is stale at 72bf36c.
  All three now say "decided (O18/O16/O17)". Delete the line.

## What holds

- **Nothing scheduled before step 11 exposes players' words, the host's files or keys.** Step 7 runs only the
  scripted double behind the real channel, and real Maxim stays a strict red gate (subject to TB-S4).
- **Every open trust BLOCKER in `npcs_v3_1` maps to a red-first test.** ATR-B1 and Exec B1 map to test 1, ATR-B2 to
  test 2, DB-B3 and Exec B2 to test 4, and DB-B2 to test 5. DB-B1 was closed by withdrawing OD-A19. Test 3 covers
  O13's pickle refusal. The defects are in tests 2, 4 and 5 (B1, S3), not in the coverage.
- **The plan's step shortcuts don't drop any of these:**
  - three clocks;
  - no exact time to cognition (the interim readout is a named ANALOG);
  - perceived time coarse;
  - the speed trait in world time;
  - fatigue on modelled durations;
  - floor-holding as `[engineering]` behaviour from a closed, claim-free vocabulary.

  The two places where one is quietly given up are O16 in co-op (S7) and delayed credit's host-calendar anchor (S2).
