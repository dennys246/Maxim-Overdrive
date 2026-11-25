# Bio-faithful integration review: `phase3/upstream-sync`, `1ed9caa..71bb320`

Reviewer: Bio-faithful integration lens, read-only. Maxim read through git only: `f145e27b` (origin/main) and
`29dda704` (#1787 head); #1305 comments and GHSA-rjg9-f5r9-7x7p read through `gh`.

**Verdict:** 2 BLOCKER, 5 SHOULD-FIX, 1 NIT. The quotes of Maxim's decisions check out, and so does the channel
for each ask. Two things are wrong. One ask's search missed sampler support that Maxim already has. And the diff
records #1787's departures without following them through to Overdrive's own contracts (O29, npcs_and_sem §3.2,
§3.3, §12.2, OD-A9).

**What checks out (verified):** the §(g) rows quoted in draft §4 match `experience_clock_decay.md:287-288` at
`f145e27b` word for word. `pain_bus.py` rejects the ContextVar back channel (docstring `:43-50`). UP1's routing
matches `SECURITY.md:15` ("Do NOT open a public issue") and `CONTRIBUTING.md:183-199` (issues are for verified
defects). #1787 places OD-I8 in #1361 S4 (Q4) as stated. `Hippocampus.sleep` reads `time.time()`
(`memory/hippocampus_consolidation.py:117`), so lesson 42's main mechanism holds in code. The #1305 comment names its
search terms.

---

### BLOCKER 1: `docs/roadmap.md::OD-I13`, and the #1305 comment it records, miss the sampler support Maxim already has (B22, B15)

**Defect.** The row and the posted comment say `complete_with_usage` takes no seed, `top_p`, `top_k`,
`repeat_penalty` and so on, and that a search found "nothing live". At `f145e27b`, Maxim already has:
- `models/language/config.py` (about `:733-738`): `top_p`, `top_k`, `repeat_penalty` and `seed` on the LLM config,
  each with an environment knob (`MAXIM_LLM_SEED` and others, about `:1006-1010`);
- `llama_backend.py:176`, which applies `cfg.top_p`; `llama_kwargs(..., seed=)` (`:21`), shared with
  `closed_local.py` (`:279`, `:298`);
- `router.py:1245` and `call_accounting.py::ServedCall` (`seed`, `seed_honoured`): each call records the backend's
  seed and whether the backend honours it.

The search covered `docs/plans` and issues. It did not cover `src/` or the briefs (`docs/agents/llm-routing.md:47`
documents the seeded closed backend), which B22 names. The comment also asks that "a backend that can't honour a
field it was given refuses, rather than ignoring it". That argues against Maxim's existing record-not-refuse design
(`seed_honoured`) without naming it, as B15 requires.

**Failure scenario.** Maxim's maintainer either builds per-call sampler fields alongside `LLMConfig`'s (two sources
for one parameter, the duplication B22 exists to prevent), or closes the ask as already covered. Either way, the
real gaps are never stated: per-call rather than per-config values, the OpenAI-compatible backend (where
`seed_honoured` is False), and refusing versus recording. The posted comment holds a claim that is incomplete
outside its narrow reading.

**Fix (unverified as wording; the facts verified with `git grep -nE "seed|top_p|top_k|min_p|repeat_penalty"
f145e27b -- src/maxim/models/language/`).** Restate OD-I13 to cite what exists, narrow the ask to those three gaps,
and name `ServedCall.seed_honoured` as the decision the refusal rule argues against. A correcting comment on #1305
reaches outside this repo, so the owner decides whether to post one.

### BLOCKER 2: `docs/roadmap.md::Tier A (O29 subset)` contradicts the OD-A12 status this diff adds

**Defect.** The diff records that #1787 (D-WC6) moves OD-A4's stamp half (Hippocampus capture and access stamps,
`SensorReading` stamps) to "land with" `AgentHome` (OD-A12), behind a clock-domain marker in the home. OD-A4 is in
O29's subset. The O29 paragraph (about `:211-222`) and Phase 4's start (about `:363-366`) still say that "OD-A12's
store routing ... don't block it". The OD-A12 row defines AgentHome as that routing ("one per-agent object over
`persistence_dir`, routing the ten still-global store families"). The diff states the dependency in one row and
leaves the contradiction elsewhere. It raises no owner question and asks #1787 nothing.

**Failure scenario.** Phase 4's first NPC starts on "the O29 subset shipped" with the stamps still on the wall. Then
§12.2's "two clocks reach one agent" stays open, and wall-clock forgetting stays open too. The other way round, the
first NPC blocks on an item the roadmap told the owner doesn't block. Either way the owner finds out at Phase 4, not
now.

**Fix (unverified).** Name the conflict in the O29 paragraph as an open owner question. Then ask #1787 whether the
clock-domain marker and the stamp half need AgentHome's store routing, or only a home-level marker that could land
without it.

### SHOULD-FIX 1: "consistent with OD-A20's decline" (`roadmap.md::OD-A5`; draft §3.5, §4) goes beyond what OD-A20 ruled, and leaves Overdrive's SCN contracts stale

**Defect.** OD-A20's decline covers event similarity for NAc credit (`overdrive_refactor_candidates.md:438`). Keeping
the phase source on the host calendar (D-WC2 revised) also keeps two other readers on host-local time:
- SCN registration;
- `SituationSignature.from_memory`'s persisted EC `temporal_hash` (`similarity/signature.py:126`,
  `datetime.fromtimestamp`, local time zone).

This stays true after A-post: #1787 folds that binning into `TemporalSignature`, which stays on the host calendar.
So with world-second stamps, retrieval binning still depends on the host's time zone. §12.2 records only credit
(OD-A20) and forgetting. Meanwhile `npcs_and_sem.md` §3.3 ("Tier A only moves the phase's *source*"), §12.2 ("exact
world phase after tier A") and `realtime_lanes_coop.md` row 10 state results that no plan now delivers. #1787 itself
lists row 10 as unmet.

**Failure scenario.** A save replayed on a machine in another time zone recalls different memories, because the EC
hashes bin differently. Phase 4's replay exit carries only OD-A20 and forgetting, so nobody owns this divergence, and
§3.3 tells readers it closes in tier A.

**Fix (unverified).** Ask #1361 or #1787 whether OD-A20's decline extends to the phase source and EC binning. Record
the answer as a Phase 3 row, and send the stale §3.3 and §12.2 lines to their design owner. The brief's file list
excludes `npcs_and_sem.md`, so this branch can only name them.

### SHOULD-FIX 2: no Overdrive row tracks the gaps #1787 handed back

**Defect.** #1787's "What Overdrive still does not get" says it is written "so the upstream lane can track them".
Two of its items are not tracked:
- **Salience and gaze moved to OD-A9.** The OD-A9 row is unchanged, and `default_network_stepped_DRAFT.md` never
  mentions salience or gaze (grep: no hits).
- **The coarse interim readout.** `npcs_and_sem.md` §3.2 marks it "[after A]". BF2-7 argues that having no time sense
  is worse than a coarse one, because the LLM invents a precise time. Under D-WC2 revised, A-pre's port is host or
  none, so no tier-A path delivers the readout. The draft says only "(OD-B9)", and OD-B9 is a tier-B row reading
  "interim bins now for embedders". It is not in O29. Nothing raises this: no pushback, and no owner question.
  Options would include a coarse port mode for recency, or an Overdrive-side time-of-day percept. Both are
  unverified.

**Failure scenario.** OD-A9's plan is written without salience and gaze, and nobody migrates them. Phase 4's first
NPC runs with no time sense, the case §3.2 calls worse than coarse, against a design that still says "[after A]".

**Fix (unverified).** Add salience and gaze to OD-A9's row. Add the readout gap, with its tier conflict, to OD-B9's
row as an owner question.

### SHOULD-FIX 3: `world_clock_release_DRAFT.md::§3.5` misreads PainBus's bio-mapping tag

**Defect.** The draft calls the refractory "an `[engineering]` de-duplication gate" and cites
`pain_bus.py: "Bio-mapping: FUNCTIONAL"` as its support. The docstring (`:52-56`) tags the module FUNCTIONAL, sharing
"the nociceptive-pathway role ... with refractory gating". Refractory gating belongs to that role. Only "the
severity latch is an engineering analog". The quote does not back the label. The bio-faithful argument also runs the
other way: a nociceptive refractory counts the body's time, and an embedded body's time is world time.

**Failure scenario.** A Maxim reviewer checks the quote, finds the tag misread, and discounts the section. Or
§(g)'s amendment (D-WC3) records the refractory as engineering and loses the FUNCTIONAL mapping.

**Fix (verified against `git show f145e27b:src/maxim/proprioception/pain_bus.py`).** Quote the docstring accurately,
and argue from FUNCTIONAL: a refractory counts body time.

### SHOULD-FIX 4: `lessons_maxim_in_games.md::42` overstates part of its evidence, and its consequence has no owner

**Defect.**
- **The evidence is a proposal.** It is #1787, unmerged, and the lesson isn't marked "recorded from a plan and code,
  not a run", as §12.2 marks its own entries (B44). The core holds: `sleep` reads `time.time()`, which I verified.
- **The reader set is described wrongly.** It says the readers "subtract `time.time()`". SCN registration and the EC
  `temporal_hash` bin by calendar; they don't subtract. Their hazard is a shifted calendar, not a decades-old age.
- **The arithmetic is right, but nothing goes back to Maxim.** The wall epoch on 2026-11-24 is about
  1.7955e9 s ≈ 56.9 years, against #1787's "about 54". No note to Maxim records the difference.
- **The consequence has no owner.** "An Overdrive save that holds an agent home has to say which clock its stamps
  count, and refuse a mismatch" is a save-format contract. No row, backlog item (B52 to B54 are free) or design
  owner holds it.

**Failure scenario.** The save-format work starts from its owner design and never sees lesson 42. A home written on
world time loads under defaults, and only Maxim's schema bump catches it, if A-post lands as proposed.

**Fix (unverified).** Mark the evidence's kind, and correct the reader description. Record the consequence where the
save-format owner will see it.

### SHOULD-FIX 5: `world_clock_release_DRAFT.md::§3.1` says A-pre "matches" §3.1's no-time-to-cognition contract

**Defect.** #1787's placements keep `exec_agent.py`'s SCN phase dict and anomaly score rendering under `NO_CALENDAR`
until A-post (`pending:A-post`; the hot-file rule, D-WC7). So A-pre leaves one SCN-derived render in place. "Matches"
overstates it.

**Failure scenario.** Overdrive or Maxim counts OD-A3 as done at A-pre, and expects the real-Maxim prompt gate (§3.1)
to flip. It stays red on the phase dict, and the cause looks like a regression.

**Fix (unverified).** Write "matches, except `exec_agent.py`'s SCN phase dict, A-post (#1787 Placements)".

### NIT 1: `roadmap.md::OD-I11` says "Filed" for an unpublished advisory, and mixes citations

`gh api .../security-advisories/GHSA-rjg9-f5r9-7x7p` returns state `draft`. The row should say so. It also cites
`router.py:467-474` at `b98954f7`, while the advisory cites `LLMRouter._provider_type` (`router.py:404-406` at
`f145e27b`; verified). Use the current symbol.
