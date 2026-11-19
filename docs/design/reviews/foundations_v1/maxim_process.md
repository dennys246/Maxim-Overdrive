# Maxim process fit: review of the two upstream drafts (4f7a754)

- **Lens:** Maxim process fit. Would these drafts survive Maxim's own process and maintainers? It checks the plan
  format, release numbering, review and pre-registration rules, ledger vocabulary, the two-tier rule, CC3, deprecation,
  the code fence, and whether the decisions they argue against are named and quoted fairly.
- **Design commit:** 4f7a754 (`phase1/design-v2`).
- **Date:** 2026-11-16.
- **Counts:** 3 BLOCKER, 14 SHOULD-FIX, 8 NIT.
- **Under review:** `docs/maxim_upstream/world_clock_release_DRAFT.md` (WC), `docs/maxim_upstream/sem_breaking_change_plan_DRAFT.md`
  (SEM), plus `docs/roadmap.md` Phase 3 and `docs/design/npcs_and_sem.md` §8 and §10.
- **Maxim read (read-only, nothing modified):** local `main` at `4b773ef8`. That commit is dated 2026-11-04, and the local
  `origin/main` ref, last fetched 2026-11-05, is 32 commits ahead at `bad7b0b1`. Files read: `CLAUDE.md`, `CONSTITUTION.md`,
  `CONTRIBUTING.md`, `docs/CODE_REVIEW.md`, `DECISIONS.md` (G3, G4, G17), `docs/plans/README.md`, `roadmap_1_3_x.md`
  (§Path to 1.4.0, the fence, 1.3.4 to 1.3.6, the atonia gate, the embodied device, Sequence), `roadmap_1_4.md`
  (Groundwork, release thresholds T0 to T9), `outstanding.md` (M72, M76, M79, M83, "Where a thing goes"),
  `experience_clock_decay.md`, `tool_failure_credit.md`, `bio_faithful_roadmap.md`, `behavioral_graduation_candidates.md`
  (BF2), `baseline_floors.md`, `bounded_stop.md` and `advisor_mode.md` (house format), `docs/agents/persistence-config.md` §3
  (CC3), `docs/agents/embodiment.md`, `docs/bugs/README.md` D53, and the glossary.
- **Code read:** `embodiment/sem.py`, `runtime/experience_time.py`, `utils/seeding.py`, `tests/unit/_loop_harness.py`,
  `scripts/survival_world/scripted_water.py`, `time/oscillator.py`, `memory/hippocampus.py`, `attention/salience_map.py`,
  `runtime/tool_dispatch.py`, and `utils/function_length_baseline.json`. I also ran greps over `src/maxim`.
- **Spot checks that held:** 13 of WC's line citations match `main` (`prompt_builder.py:1104`, `:232-236`;
  `llm_fallback.py:330-338`; `body.py:294-295`; `loop_controller.py:157`; `loop_state.py:240`; `agent_loop.py:970`;
  `default_network/config.py:219`; `spec.py:837`; `temporal_signature.py:62`; `oscillator.py:193-194`;
  `salience_map.py:227`; `cerebellum.py:155`). SEM's `tool_dispatch.py:356-375` matches too. The #1361 §(g) rows and G17
  are quoted verbatim. SEM's S7 correction is right: `coupled_to` and `modulated_by` are parsed and applied nowhere, and no
  Maxim YAML declares `coupled_to`. WC's PR 0 does what Maxim accepts as evidence: it turns Overdrive's findings into strict
  red gates inside Maxim's own tree, so no game run goes near the ledger.

## Verdict

The instinct behind both drafts is right, and much of the evidence is accurate. A Maxim maintainer would still send both
back at the plan-review stage, for three reasons, in the order they would be found:

1. **Neither draft answers the front-gate question.** This is Maxim's hard rule before drafting any new mechanism.
   WC adds a fourth clock abstraction beside the `ExperienceClockDriver`, which the very plan it depends on (#1361) chose
   to ride on precisely so that it "adds no clock".
2. **WC's central promise, "robots keep today's behaviour exactly", is false for one of its own rows.** The oscillator
   change alters SCN dynamics under the default clock.
3. **SEM misreads CC3.** Two of its four "breaking" items are additive under Maxim's own written rule and its post-1.0
   precedent. Once that is fixed, the major-version question mostly goes away.

Beyond these, both drafts under-model the fence and the in-flight 1.3.6 work, they omit three recorded decisions they
in fact argue against, and their experiment ids collide with Maxim's release thresholds.

## BLOCKER

### MP-B1. No front-gate section, and existing infrastructure goes unnamed (WC §3.1, §3.3; SEM S3, S4, S9)

Maxim's `CLAUDE.md` says: "**Front-gate scope pressure at design time.** Before drafting any implementation plan for a
new mechanism … force the question: *Does this need to be its own mechanism, or can it ride on existing
infrastructure?* If it needs to be its own, name the specific reason in the plan doc's motivation." Every plan in the
house format carries this section (`experience_clock_decay.md` "Front-gate scope pressure: ride on the existing clock",
`advisor_mode.md` "What rides on existing infrastructure"). Neither draft has one, and each skips infrastructure that a
reviewer will name in the first round.

- **WC `utils/clock.py`:**
  - `runtime/experience_time.py::ExperienceClockDriver` already models "what advances an agent's experience clock: its
    WORLD's time". A world declares itself through duck-typed members (`experience_turns()`, `experience_us_per_turn`).
  - #1361 S2 ("`ScenarioSource` declares step experience") and owner answer Q8 ("a fixture 'turn' is step-clocked")
    are the stepped-world seam a deterministic host would declare against.
  - `experience_clock_decay.md` says of itself: "adds no clock, no bus and no SCN surface".
- **WC `Rng`:** `utils/seeding.py::make_agent_rng(base_seed, agent_id) -> random.Random` already gives per-agent RNG
  derivation, and `seed_all` already exists.
- **WC's tripwire and its stepped-host exit test:** `tests/unit/_loop_harness.py::_StepClock` already "replaces
  `time.time`/`monotonic`/`perf_counter`/`sleep` and the `_ns` variants" to run the loop lockstep under a characterization
  golden. `scripts/survival_world/scripted_water.py::StepClock`/`LockstepTime` (#951) is a second instance. A maintainer
  will ask why the embedding contract is not "patch global `time`, as our golden does".
  - The honest answer is that a process-wide patch cannot serve several agents, a Default Network thread, or co-op
    lanes in one process. That answer belongs in the plan.
- **WC `IdSource`:** G17 records that "choosing the [session-id] source is a decision of its own, so the type waits for
  the stage that needs it". That stage is the post-fence resume stage (`autonomic_layer.md`), which already lists
  "deterministic under `_StepClock` (no uuid, no wall time, G3)" among its questions.
- **SEM S9:** `embodiment/sem.py:30` already has `ENTITY_FORMAT_VERSION: str = "1.1"`. "None exists today" holds only
  for the literal name `SEM_PROTOCOL_VERSION`.
- **SEM S3 and S4:** these overlap two existing pieces of work.
  - `tool_failure_credit.md` (#1200, ACTIVE, owner decisions TF1 to TF3) already owns failure credit and classifies every
    `record_outcome` caller as ran or not ran (`book_refusal`, `book_machine_refusal`). TF2 already rules that "a
    hallucinated or inactive tool name is a cognitive error, not a tool failure".
  - D53's NEUTRAL tier, with `outcome_valence` self-report, is the existing "this is not harm" path.

**Failure scenario:** the Architecture lens of the three-lens plan review returns "rides on X; the plan does not say why
not". The plan goes back before PR 0, and the reviewer reads the rest less charitably.

**Fix:** give each draft a front-gate section that answers each item above by name. For WC, say what
`ExperienceClockDriver` plus a declared stepped world cannot do, namely stamps, Default Network timers, cadence, prompt
time, ids and randomness, and build the `Clock` on that seam rather than beside it. For SEM, recast S4 (and S3's
crediting half) as amendments to `tool_failure_credit.md`.

### MP-B2. The oscillator row breaks "robots unchanged" (WC §1, §3.2 Oscillator row, PR 5, E5)

`time/oscillator.py` advances `integration_steps` fixed steps of `dt = 1/24` (`OscillatorConfig.dt`) on every
observation (`:193-194`). WC moves this to "`step(dt)` with the elapsed `Clock` time since the last observation". Under
`HostClock` the elapsed wall time between observations is not 1/24, so robot and console SCN dynamics change. That
contradicts §1 ("Robots and the console keep today's behaviour exactly") and the tier label ("adds no mechanism and
claims no behaviour").

The change also lands in a bio system with a recorded gate. `bio_faithful_roadmap.md` §SCN + OscillatorNetwork says:
"Gate: front-gate question first: does per-event-type phase learning earn its keep (B2 never behaviorally graduated)?"
The same file marks "entrainment inputs" as ANALOG ("revisiting requires a new argument").

**Failure scenario:** E5 ("existing suite green, no ledger row walks") passes because nothing pins oscillator phase.
Robot SCN anticipation then shifts silently, and the release that promised no behaviour change ships one.

**Fix:** take the oscillator out of tier A. Tier A keeps only the time *source*: `TemporalSignature` phase from the
injected calendar, which is identical under `HostClock`. The elapsed-time oscillator becomes a tier B mechanism with its
own argument against the bio-roadmap row, enters `[engineering]`, and is earned only by experiment.

### MP-B3. SEM's CC3 reading is wrong, so §1 and §3 frame the major-version question on a false premise (SEM §1, §3, S3, S5)

SEM §1 quotes `CouplingSpec`'s docstring ("Adding any new field post-1.0 is a major-version-bump change") and applies it
to every SHAPE-FROZEN type. Maxim's own text, and its record, say otherwise:

- **The canonical CC3 rule:** `docs/agents/persistence-config.md` §3, path (b), says "adding a *required* field post-1.0
  is a major-version bump; an optional trailing defaulted field is non-breaking but still review-gated".
- **`AffordanceSchema`'s own docstring** (`sem.py:107-118`): "All fields have defaults, so additive fields appended at
  the end stay non-breaking. Adding a *required* field post-1.0 is a major-version-bump change."
- **Precedent:** two defaulted fields were added to `AffordanceSchema` after 1.0 (2026-06-17), both in non-major
  releases: `always_active: bool = False` (`92eae365`, 2026-07-19, #403) and `speech_param: str | None = None`
  (`d47936e2`, 2026-10-14, #1261).
- **`ModulatorResult`** has defaulted trailing fields as well (`error`, `metadata`), so a trailing `pending: bool = False`
  is additive for every keyword or positional constructor.

So `acts_on` (a defaulted `AffordanceSchema` field) and `pending` are review-gated additive changes, not members of a
breaking batch. S5's chosen "additive first" path, an attribute read with `getattr` on a `Protocol`, is weaker than the
honest defaulted field, and Maxim would prefer the field. For the `drift_rate` rename, Maxim's practice is an alias plus
a `DeprecationWarning` kept through 1.4.x and removed in 1.5.0 (Q7 for `apply_decay=`, and S3b's "window rename +
alias"), not a major. That leaves one true break, `Modulator.execute`'s signature, and even that has an additive form
(MP-S12).

**Failure scenario:** the Architecture or Wire reviewer cites path (b) and #1261. §1's "CC3's text says major" and the
whole of §3 are struck. S5 ships a duck-typed attribute that Maxim's "push invariants into types" rule would refuse.

**Fix:** rewrite §1 against `persistence-config.md` §3, and cite `always_active` and `speech_param`. Move `acts_on` and
`pending` into the additive items as defaulted fields. Give the rename its alias-and-deprecation path. Shrink §3 to the
`Protocol` question.

## SHOULD-FIX

### MP-S1. PRs 3–5 are labelled unfenced, but the live path runs through fenced files (WC §5 table, §3.2)

Until PR 8 the embedded agent's live path is `run_agentic_loop`. `runtime/agent_loop.py` has 14 `time.time()` reads, 2
`uuid4` calls and 1 `strftime`. `simulation/orchestrator.py` has 5 `strftime` calls, which are G17's session-id sites.
`runtime/tool_dispatch.py`, the 1.3.6 #1150 slice target, has 5 `time.time()` reads. PR 5 ("`uuid4` and global `random`
on the live path") and PR 3/4's stamps reach these, yet the table says "no".

**Failure scenario:** PR 5 needs a fence-touch grant from Session A (the #866 and #1392 precedent records each hunk), or
it cannot be complete. E4's tripwire cannot flip before 1.3.6, so §5's claim that "PRs 0–6 can ship before 1.3.6"
overstates what ships.

**Fix:** list the fenced sites, move them to PR 7/8, and say that E4 passes only after PR 8.

### MP-S2. WC collides with 1.3.6 work in flight (WC §5 PRs 2, 3, 4, 6)

- **PR 6, `DefaultNetwork.step`:** #1263 is in 1.3.6's riders, and roadmap_1_4's T0 list includes "#1263's six parts (the
  DefaultNetwork stop …)", which is a 1.4.0 gate item.
- **PR 4, drift dt:** this edits `Embodiment.evaluate_failures`. That function is #1361 S4's target and is pinned at 224
  lines, so "Touch it, shrink it" applies.
- **PR 4, refractory split:** this touches the PainBus that `tool_failure_credit.md` and #1200 rewire in 1.3.6.
- **PR 2, `llm_fallback`:** this overlaps 1.3.6's exit item "the `_llm_unavailable` fallback leaves `run_agentic_loop`".
- **PR 3, the mechanical sweep:** a 19-file sweep (the 36 `default_factory=time.time` sites live in 19 files) restarts
  every parallel PR's roughly 40-minute CI under M83.
- **The characterization golden:** it depends on `_StepClock` patching the global `time` at call time (`_loop_harness.py`,
  "IMPORT-TIME BINDINGS"). A `HostClock` that binds `time.time` at import would silently stop the golden from seeing time.

**Failure scenario:** each of PRs 2–6 conflicts with a decomposition slice. Alternatively, the golden that guards the
decomposition stops observing time, and nothing turns red.

**Fix:** add an "Order and the fence" section in the `advisor_mode.md` style. Name each overlap, the session that owns it,
and the rule that `HostClock` reads `time.time` through the module attribute at call time, with a test that
`_StepClock.install()` still reaches it.

### MP-S3. "Own clock" fits only half the release (WC header, §3.3, §8)

The atonia gate and the embodied device are own-clock because they "touch no decomposition-fenced file … hold nothing"
(`roadmap_1_3_x.md` §The embodied device). WC's PRs 7–9 depend on 1.3.6 and touch fenced files. As one release, it cannot
take "the next free number" when done, because it is done only after 1.3.6.

**Fix:** answer §8's last question in the draft. Make it two releases: A-pre (PRs 0–6 without the fenced sites, own
clock, the next free patch number) and A-post (PRs 7–9, landing with or after 1.3.6, with Session A as owner).

### MP-S4. SEM S3 and S4 edit pinned long functions that 1.3.6 is splitting (SEM S3, S4, §5 item 3)

S3 changes `ModulatorAffordanceTool.execute` (pinned at 502 lines) and `tool_dispatch`. S4 changes `record_outcome`
(pinned at 392). `execute_and_learn` (357) is #1150's 1.3.6 slice. Under "Touch it, shrink it", each edit must also
extract at least as many lines as it touches, which is a refactor the sizes don't budget for. Those files are also
mid-decomposition, and the 1.4 Groundwork rule is that "a may-fail result measured on a loop mid-refactor cannot tell a
null from the refactor".

**Fix:** sequence S3 and S4 after 1.3.6 and #1200, write them as amendments to `tool_failure_credit.md` (MP-B1), and size
the extraction.

### MP-S5. Three recorded decisions are argued against without being named, and a fourth is named wrongly (WC §4, §3.1; SEM §7; roadmap C10, B8)

- **WC §4 row 5 and roadmap C10 argue against "M76".** M76 is a mechanization backlog row. The decision is owner decision
  G4 (2026-10-07), quoted on the hybrid plan: "this trigger is NOT re-keyed; it is the robot half of the second-body
  gate … Whether to re-read the 'second robot body' gate is a question at GL3's start." The argument has to name G4 and
  aim at GL3's start.
- **Tier B8 and T1 (an SCN entrained by world light)** go against `bio_faithful_roadmap.md`'s "entrainment inputs |
  ANALOG | 4 scales is the deliberate scope", where "revisiting requires a new argument". The drafts never mention it.
- **WC `IdSource`** pre-empts G17's sequencing. The session-id source belongs to the post-fence resume stage. Argue
  against G17, or hand `IdSource` to that stage.
- **WC says "the M72 lint becomes its static half".** M72's recorded allowlist includes "refractories, SCN phases", which
  are exactly the sites WC moves (§4 rows 1–2). M72 is also owned by `experience_clock_decay.md` §Enforcement, so WC must
  propose amending M72, not quietly re-scope it.

**Failure scenario:** a reviewer finds G4 or the ANALOG row first. The draft then looks as if it went around a recorded
decision, which is what Overdrive's own "push back" rule forbids.

### MP-S6. One piece of determinism evidence is wrong (WC §2 bullet 6, §3.2 Hippocampus row)

WC says hippocampus de-duplication on builtin `hash()` is something "Maxim's own CLAUDE.md forbids for values that
persist". `Hippocampus._recent_observations` is an in-memory dict, never persisted, and pruned on a 30-second window.
Inside one process builtin `hash` is consistent, so E1's two-process digest is not affected beyond the odds of a
collision. A maintainer will refute this in one line. The real identity break on that path is the UUID memory id that
`observe` returns.

**Fix:** keep the `stable_hash` swap as hygiene, and drop it as evidence. Cite the UUID ids and `uuid4` instead.

### MP-S7. The `Clock` surface conflicts with persisted stamps, and PR 3's scope contradicts §3.2 (WC §3.1, PR 3)

- **Units:** `now_us()` is "monotonic, in the host's microseconds". The 36 `default_factory=time.time` and
  `SensorReading` stamps are epoch-second floats, and several are persisted (causal links, hippocampus records,
  `saved_at`). Maxim's rule is that "a `Deadline` is a `time.monotonic()` instant, meaningless in another process"
  (`persistence-config.md`). If PR 3 stamps from `now_us`, the persisted units change. That fires the ledger trigger
  "hippocampus persistence schema change" (T1-16's `Re-run on:`), and robots are no longer unchanged. If PR 3 does not
  stamp from `now_us`, the protocol needs a persisted world epoch, and the draft doesn't define one.
- **Mechanism:** a `default_factory` cannot reach an injected per-agent clock without ambient state, either a module
  global or a `ContextVar`. Maxim pushes collaborators into types, and it has already rejected a `ContextVar` back
  channel once (`docs/agents/embodiment.md`).
- **Scope:** PR 3 sweeps "the 36" stamps, which include `mesh/identity.py`, `mesh/message.py`, `utils/web_cache.py`,
  `runtime/worker_pool.py` and `utils/output_watcher.py`. These are infrastructure and cross-node wire stamps, not the
  agent's live path, which contradicts §3.2's "not all 880". A world-time stamp on a mesh message sent to another host
  is a wire bug.

**Fix:** define the clock as world time on a persisted epoch, in seconds as today and microseconds where it is new. Say
how a stamp reaches the clock (explicit construction, never a default). Scope PR 3 to the live-path census.

### MP-S8. House-format sections are missing (both drafts)

Maxim plans carry several sections these drafts lack:

- **Impact, ledger rows by id.** `experience_clock_decay.md` §Impact names T1-6, T1-9, T1-2 and T1-13. WC's E5 defers
  this ("if one would, the plan review lists it"), and SEM has nothing.
- **Enforcement, with a `Regression guard:` per new `[engineering]` invariant.** Maxim's `CLAUDE.md` says "Every
  `[engineering]` invariant … ends its body with `Regression guard: <path>`", and a rule with no check gets an
  `outstanding.md` row in the same commit. Examples here are "embedders get no wall-clock fallback" and "motor dispatch
  never reads an injected clock".
- **Owning session.** For example, Session A for the fenced PRs.
- **Owner decisions asked together at the start** ("Faster without lowering the bar", rule 3).
- **An adversarial approach note.** WC's tripwire and the enforcing M72 lint are gates, so rule 1 of the same section
  requires a one-page adversarial design pass before code. Neither draft mentions one.

### MP-S9. Experiment ids collide, and the experiments miss BF2 (SEM §4, S3; npcs §10; roadmap Phase 3)

- **ID collisions:**
  - "T1" and "T2" are Maxim's 1.4.0 release thresholds ("T1 — E1's instrument shipped and proven", "T2 — Exp 62 has a
    recorded outcome") and the prefix of ledger rows (T1-2, T1-13).
  - "E1–E6" collide with Maxim's E1, E2 and E3 experiments.
  - SEM's "S1–S10" collide with #1361's S0–S6. SEM S1 even cites "#1361 S4" in its own text.
  - Overdrive's tier B "B1–B11" collide with Maxim's B1–B4 floor chain, which sits on the critical path to 1.4.0.
  - "A1/A2" collide with 1.3.3's NAc audit "A1, A2".
  - Maxim's glossary already warns about reused prefixes. Use one Overdrive-scoped prefix (for example `OD-T1`), or ask
    Maxim to assign ids.
- **BF2:** from 2026-10-10, "a NEW substrate-path claim earns only if it beats `tabular_q` and `random`"
  (`behavioral_graduation_candidates.md`). T1 has no floor arm, and T2 has a shuffled control but no floor, so at best
  they reach `PARTIAL (narrow: floor matched)`.
- **H2 cannot earn S3.** SEM S3 says "Earned by: the hybrid line's H2 latency sweep", but npcs §10 calls H2 "calibration,
  not a claim". A calibration cannot graduate anything.
- **Vocabulary:** say `[behavioral]` (Maxim's second tier), not "bio" or "earned", and say that rows go to
  `behavioral_graduation_candidates.md`.

### MP-S10. The 1.3.3 precedent and the 2.0 framing overreach (SEM §1)

`plans/README.md` shows that 1.3.3's breaks were *security* changes ("every spawned llama-cpp-server keyed, the agent
cannot change the operator's internet switch"). That is not a general licence to break SEM shapes in a patch, and citing
it that way invites a correction.

A "SEM 2" release also ignores that Maxim's version numbers are research-gated. 1.4.0 is hard-gated by
`release_gates.json` and `lint_release_gates.py`, and "the name follows the release rule: the highest EARNED rung". A
2.0 would have to come after 1.4.0 or skip its gate.

M79 is cited correctly (`pymaxim>=1.3.3,<2.0`), but M79 is a met 1.3.4 ordering row. Cite pulse's own pin instead.

**Fix:** once MP-B3 is folded, frame the question as "additive in 1.x, with aliases and deprecation; a 2.0 only after
1.4.0, and only if the `Protocol` change cannot be additive".

### MP-S11. Wrong venue, and what to split (both drafts' Status lines)

`CONTRIBUTING.md` says issues are for "a discrete defect, actionable **now**, with a definite done state". Everything
else belongs in a plan or a deferred plan. "An issue, this plan" for a 10-PR line is the wrong venue. Split it:

- **Issues now, each small and outside the fence:**
  - The `salience_map.py:227` `or` bug.
  - The missing CC3 declaration on `ModulatorResult`. Maxim's `CLAUDE.md` says the declaration "MUST" exist before
    merge, so its absence is a defect against Maxim's own rule.
- **Plans:**
  - A-pre and A-post (MP-S3).
  - The externally stepped Default Network, coordinated with #1263.
  - Propose and settle, as a `tool_failure_credit.md` amendment.
  - The prompt-time change. In Maxim's own robot use, host time in the prompt is intended, so it is a plan item for
    embedders, not a defect.
- **Experiment drafts:** T1 and T2 go to `docs/experiments/` only after a four-lens design review, and with BF2 floors.

### MP-S12. S6's injected `actor` key is not additive (SEM S6, §3)

The draft itself notes that Overdrive's modulator refuses unknown keys. Any strict third-party modulator, including
pulse's if it validates `params`, will then start refusing every call after a patch upgrade. Injecting a new key into
`params` changes the contract for every implementer, which is the same class of change as a `Protocol` signature change.

**Fix:** make it opt-in, declared by the modulator. For example, a class attribute such as `accepts_actor: bool = False`
that the bridge checks, or a separate optional `Protocol` checked with `isinstance`. Then the `Protocol` change in §3
also has an additive form.

### MP-S13. The owner decision it rests on is recorded only in Overdrive (SEM header; roadmap Phase 3)

SEM cites "The owner's decision (2026-11-16)" as its authority to refine SHAPE-FROZEN types. Maxim's process cites owner
decisions by their `DECISIONS.md` id, and a decision recorded in another repo neither binds Maxim nor overrides CC3's
text. **Fix:** the plan PR records it in Maxim's `DECISIONS.md`, worded as Maxim's owner would take it, and cites that
id.

### MP-S14. The tree is stale, and the line numbers come from two trees (WC and SEM headers, §2)

"`main` at `4b773ef8` (2026-11-16)" reads as if `main` was current on 2026-11-16. In fact `4b773ef8` is a 2026-11-04
commit, the last-fetched `origin/main` is 32 commits ahead (bounded stop PR 3a, box-quiet, #1538), and the remote is
probably further ahead still. The collision analysis against 1.3.4–1.3.6 rests on that picture. WC also mixes 1.3.3
wheel line numbers with `main` line numbers. Maxim's house style probes "against `origin/main` <sha>"
(`tool_failure_credit.md`). **Fix:** re-read against a fresh `origin/main` before filing, give one sha, and cite
`file::symbol` (MP-N6).

## NIT

- **MP-N1. The refractory argument can be fairer and stronger (WC §4 row 2).** Maxim's own embodiment brief calls
  PainBus's refractory an `(entity, failure_mode)` dispatch-collapse gate ("without it two entities firing embodiment
  pain in one tick collapse into one dispatch"), not a motor rate limit. Quote it. Under Constitution §1, also name the
  guard: a check that no motor-dispatch path reads the injected clock.
- **MP-N2. S3's bio basis has a home.** `bio_faithful_roadmap.md` lists cerebellum "Timing (climbing-fiber style
  eligibility windows) | EARN (candidate)". Cite it as support for observing at settle.
- **MP-N3. `Rng`.** `make_agent_rng` returns `random.Random`, which answers WC §8's first question the house way.
  "Seeded from OS entropy, today's behaviour" ignores `seed_all`.
- **MP-N4. S7's citation.** The draft says "Wiehler et al. 2022, *to verify before it enters `data/`*". Maxim's
  bio-faithful lens will want it verified before the plan.
- **MP-N5. The roadmap misstates Maxim's process.** Overdrive's `docs/roadmap.md` Phase 3 preamble says every item goes
  through "pre-registration, four-lens review, ledger", and so does the matching parenthetical in Overdrive's
  `CLAUDE.md`. In Maxim, an engineering sub-plan gets a three-lens plan review and no pre-registration or ledger entry;
  the four-lens review is the *experiment* design review. Tier A, as the WC draft rightly says, has no pre-registration.
- **MP-N6. Citation style.** Use `file::symbol` over `file:line`. Maxim's `CLAUDE.md` says "audited line numbers all
  drift; symbols hold", and the plans that carry line numbers pin a sha.
- **MP-N7. S8.** `modality:` is the channel-to-cluster declaration (`embodiment/sensory_streams.py`, `modality:
  world|audio`). Adding percept versus instrument to it would mix two axes. Verify this before filing, as the draft
  already flags.
- **MP-N8. Volatile counts.** "About 880 sites in about 215 files" is a grep. Maxim avoids volatile counts in plans.
  Let PR 0's census print the number, and cite the census.

## What a Maxim maintainer would reject first

1. A new `utils/clock.py` with no front-gate section, beside the `ExperienceClockDriver` that #1361 deliberately rode on
   (MP-B1).
2. "Robots unchanged", disproved by the oscillator row (MP-B2).
3. "CC3 says major", disproved by `persistence-config.md` §3, `AffordanceSchema`'s own docstring and #1261 (MP-B3).

## What to split into separate issues or plans

- **Issues now:** the salience `or` bug, and the `ModulatorResult` CC3 declaration.
- **Plans:**
  - World clock A-pre (own clock).
  - World clock A-post (with 1.3.6, Session A).
  - The stepped Default Network, coordinated with #1263.
  - Propose, settle and the refusal kinds, as a `tool_failure_credit.md` amendment after #1200.
  - The elapsed-time oscillator and world-light entrainment (tier B), arguing against the bio-roadmap ANALOG row.
  - Re-keying the hybrid plan's trigger, argued against G4 at GL3's start.
- **Experiment drafts:** T1 and T2, renamed, with BF2 floors, after four-lens design review.
