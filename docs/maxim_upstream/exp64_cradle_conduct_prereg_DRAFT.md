# Exp 64: a written life history changes an NPC's conduct toward a matched cue (pre-registration DRAFT 2026-11-14)

> **Status: DRAFT, not frozen.** It has had no design review: the confounding, bio-faithful and wiring lenses are
> still owed, and no owner decisions have been taken. No harness code and no data exist. It enters the 1.4 line
> through its own plan and four-lens review, as `roadmap_1_4.md` requires of every mechanism. The numbers below
> (N, K, thresholds) are placeholders that the review sets before the freeze.

| | |
|---|---|
| Campaign key / experiment | `64` (provisional; this draft moves to Maxim `docs/experiments/`) |
| Verdict kind | `exp64_verdict` (new) |
| Data directory | `docs/experiments/data/64_cradle_conduct/` |
| Related rows | T1-16 (carried recall, EARNED narrow on Exp 63c as of 2026-11-13, `floor: not measured`; Exp 64 must not lean on its floor), T1-2 (surfaced ≠ rendered ≠ acted), Roy-1a (persona carry-over, NULL) |

## Why

Exp 63/63b asked whether carried memories *surface*. This asks the next question on the path, the one the
Maxim Prime NPCs depend on: does a history written into an agent's memory change **what the agent does** when a
matching situation comes up, compared with a twin whose history differs only in that one event? It also asks
whether Maxim's memory path beats the obvious baseline of pasting the same history into the prompt.

## Claim (suggested wording, narrow)

> Two NPCs that share a persona, body, model and seed, and whose cradles differ in one event (A: betrayed by a
> corporate fixer; B: a matched, neutral dealing with one), choose different actions toward a player who carries a
> corporate cue, on the shipped NPC path. They do not differ when the cue is absent. The difference disappears
> when recall is switched off. One archetype, one model, N seeds.

- **Mechanism:** cradle episodes written through the seed-memory path → Hippocampus → recall into the NPC prompt
  (the new recall step on the NPC path) → affordance choice. Secondary: NAc percept-valence / cluster fear
  written by the betrayal's pain, read by `recommend_action` (H-sub).
- **Not claimed:** that the NPC has a personality; generalization to cues sharing no words with the cradle (the
  ranker is token-overlap, so H5 is expected to fail and is reported, not gated); persistence through
  consolidation beyond the one `sleep()` in the cradle; anything about more than one archetype or model.

## Prerequisites (upstream work, each under its own issue)

1. NPC replies recall memory (`runtime/agent_pool.py::_generate_llm_response`), with the recalled records logged
   per turn.
2. Persona hook: the same persona string reaches the prompt on the path under test.
3. Seed-memory write path: backdated `experience_us`, no 30 s wall-clock de-dupe, salience taken from the event.
4. A cradle writer that produces the event list from an arc plus handcrafted inflection points, deterministic
   under a seed, with the list committed as data.
5. A probe harness that offers the same SEM affordances on every turn.

## Staging (revised 2026-11-14)

One experiment per claim, each gated on the one before it, so the gradient work is not spent on an effect that
does not exist:

- **64a, existence and mechanism split:** a single strong dose (arms below). Gates G0–G5.
- **64b, gradient:** continuous doses of pain, event count, position and interference (§64b). Runs only if 64a's
  G2 passes. Its own claim and pre-registration, sketched here.
- **64c, ordering:** the same events in a different order (§64c). Runs only if 64a passes.

## Lives are assembled, not written per seed

The life writer (1 LLM call) writes a **fixed event pool** once: the neutral life events, the betrayal, the matched
neutral corpo deal, reconciliation and interference events. The pool is committed as data. Each seed's cradle is
then assembled from it **in code**: which events, in what order, at what pain and salience. This does three
things: every manipulation is exact; arms differ only where planned; and a seed costs no LLM calls before the
probe, which makes 64b's large N affordable.

## Body state at probe start: equalized, and logged throughout

A cradle can leave arms in different drive states (a hungrier NPC trades differently whatever its history). So at
probe start every arm's **homeostatic and entropic drives are reset to the same values** (set points; entropic
drives at a fixed level below their deprivation thresholds), and drive drift is frozen during the probe. NAc and
EC state are **not** reset: they are part of the treatment. Logged on every turn in every arm: each drive's value,
pain received, NAc biases and percept aversions for the cue cluster, `recommend_action`'s score components, and the
recalled records. These are manipulation checks and covariates; they do not gate on their own.

## Arms (64a)

All arms share the persona, the body (`npcs/street_fixer`-derived, with opaque affordance names per L12), the
function, its envelope and its placement digest (Overdrive `inference_placement.md` §4.3, `single` policy), the seed, the probe order and the equalized drives.

| Arm | Episodes (Hippocampus) | NAc / EC state | Prompt | Purpose |
|---|---|---|---|---|
| A | life with the betrayal (text + pain 0.8) | A's own | persona | treatment |
| B | the same life; the betrayal swapped for the matched neutral deal | B's own | persona | matched control: "has corpo memories" alone |
| C | none | blank | persona | blank reference |
| D | A's | A's | persona; **recall off** | deletion probe: the effect must go through recall |
| E | none | blank | A's life as text, cut to the **same token budget** recall gets | the floor: a backstory prompt |
| F | none | **A's, transplanted** (hivemind bundle: NAc + EC, no episodes by construction) | persona | substrate alone |
| G | none | A's, transplanted | as E | prompt + substrate: does recall add anything beyond both? |

E, F and G split the mechanism: A − G is what episodic recall adds over a prompt plus learned state; F − C is what
the learned state does by itself. F and G use the existing `hivemind/bundle.py` export, so they need no new code.

## Probe

K = 12 scripted player encounters per seed in a fixed, counterbalanced order: 6 carry the corporate cue (credential,
clothing or employer named in the player's line) and 6 are matched lines with no cue. Each turn offers the same
affordances: `aff_01` (trade), `aff_02` (refuse), `aff_03` (stall/lie), `aff_04` (alert others), `aff_05`
(leave). The names are opaque in the body; the mapping is fixed in the harness. H5 adds 4 indirect-cue turns
(corporate signals sharing no word with the cradle text).

## Reads

- **R1 (primary, objective):** the affordance chosen on each turn, from the decision-provenance event.
- **R2:** the dialogue line, rated by a judge model **blind to arm** on a pre-registered distrust scale, plus a
  forced-choice task: "which of these two transcripts came from the betrayed NPC?" A human-rated subset of 20%
  checks the judge.
- **R3 (mechanism trace):** on each cue turn, whether a betrayal-cradle record surfaced, whether it was rendered
  into the prompt, and the turn's choice (the T1-2 chain, logged and not inferred).

## Gates (placeholders until review)

- **G0 apparatus:** every seed completes K turns; 0 LLM-outage fallbacks (the Exp 09 lesson); recall logs present.
- **G1 surfaced:** a betrayal record is rendered into the prompt on ≥ 4 of 6 cue turns in arm A, in ≥ 80% of seeds.
- **G2 conduct:** P(`aff_02` ∪ `aff_04` ∪ `aff_05` | cue) is higher in A than in B, one-sided Fisher exact over
  pooled turns, p < 0.05, **and** in the same direction in ≥ 70% of seeds.
- **G3 specificity:** A vs B on no-cue turns, absolute difference < 0.15.
- **G4 deletion:** D vs B on cue turns, absolute difference < 0.15.
- **G5 floor (reported; gates only the wider wording):** A vs E. "Beyond a backstory prompt" may be claimed only if
  A ≥ E on G2's measure **and** R2's forced-choice accuracy for A ≥ E's.
- **H5 (reported, expected to fail):** A vs B on indirect-cue turns.
- **H-sub (reported):** the same comparison in substrate-primary, actions only, to see whether NAc fear carries
  the effect without the LLM.

## 64b: the gradient (sketch; its own pre-registration)

The betrayal's **text stays fixed**; only its body-side parameters vary, sampled per seed from pre-registered
distributions rather than set at a few levels, and analysed with one pre-registered logistic model of
P(protective action | cue):

| Factor | Distribution | Mechanism prediction |
|---|---|---|
| Pain at the betrayal | uniform [0, 1], **including 0** (text with no pain) | LLM-primary: shallow slope (language priors dominate pain, the earlier pain-experiment finding); substrate-primary: steep slope |
| Betrayal count | 0, 1, 2, 4 events (0 = B's life) | rises, then saturates |
| Position in the life | early / middle / late (just before the game) | effect only through the recency tiebreak and consolidation, since the ranker reads no age beyond that |
| Interference | 0–60 neutral events after the betrayal | falls with interference |
| Salience | uniform [0.3, 1.0] | rises |

Both modes (LLM-primary and substrate-primary) run on the same seeds; the mode × pain interaction is the primary
term. Turns cost about one LLM call each, so N ≈ 150 seeds × 12 turns × 2 modes is roughly 3,600 calls: a few
hours on the rig, which a continuous-dose design needs. Pilot rows can set the ranges; pilot data never reaches a
gate.

## 64c: ordering (sketch)

The same events, two orders: betrayal → reconciliation vs reconciliation → betrayal, with the life's length held
fixed. If order matters, it can only come through recency, consolidation and NAc's update order (Rescorla-Wagner
updates do depend on order). Pre-register which of those the trace must show.

## Size and rig (64a)

N = 20 seeds × 7 arms × 16 turns (12 + 4 for H5) = 2,240 NPC turns at about one LLM call each, plus the pool
writer (1 call, committed, so every arm reads the same bytes). On mistral-7b on the usual rig that is a few hours
of LLM time. A second model is a separate experiment.

## Aborts

A typed abort, with no verdict, for any of: an LLM outage fallback; a seed whose cradle bytes differ between arms
except at the planned event; a recall log missing on any turn.

## Re-run on

Any change to the NPC-path prompt, the recall ranker, the seed-memory path, consolidation, or `recommend_action`.

## Open design questions for the review

1. Is a single swapped event enough of a manipulation, or does A need a pattern (2–3 events) to clear the ranker?
2. Should the cue words be planted (sharing tokens with the cradle) and the indirect cues kept as H5, as drafted?
   Planting tests the shipped ranker honestly, but it makes G2 partly a token-overlap test.
3. Is E's equal-token-budget rule the right fairness test, or should E get the whole story? The memory path's
   advantage should be scale: 100 events will not fit a prompt.
4. ~~Is pain part of the treatment?~~ Decided (owner, 2026-11-14): pain is part of the betrayal in 64a; 64b varies
   it, down to 0.
5. Which drive values do the arms reset to at probe start, and does freezing drift during the probe hide a real
   interaction between history and need?
6. 64b has five factors on about 150 seeds: are the main effects plus mode × pain the only terms, with the rest
   reported as exploratory?
