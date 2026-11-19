# npcs_and_sem.md v3 (3db82a8): Bio-faithful integration lens

**Reviewed:** commit 3db82a8 on `phase1/design-v2`: `docs/design/npcs_and_sem.md` v3 (§0 O11a/O12/O15a, §2.1, §2.3,
§4.2, §4.4–§4.6, §5.1, §6.1, §6.4, §8, §12, the `maxim_response_1` fold table), `docs/design/boundaries.md` §7.4,
`docs/maxim_upstream/embeddable_agent_DRAFT.md` v2 and roadmap Phase 3. Sources folded: `reviews/maxim_response_1/`
(`response.md`, `response_2.md`, `bio_determinism.md`, `synthesis.md`, `reply.md`, `foldtable.py`). Maxim code read
at `origin/main` 7084f561 with `git show`.

**Counts:** 1 BLOCKER, 7 SHOULD-FIX, 5 NIT.

**What holds:** the citation correction from Maxim's second answer is folded honestly (Stivers & Robinson for the
order only; Jefferson 1989 marked *to verify*). The speed trait is kept off the yield threshold (BD-5). The
admissibility rule (BD-17) is in §10. BD-1, BD-14 and BD-18 are marked partial, and they are partial. The clock seam
split (BD-12, BD-15) landed in §6.1, §12.2 and OD-A2/OD-A3. The PFC cycle count checks out: `max_cycles` counts cycle 1
(`agent_loop.py:533`, the `:3091-3094` default is 3 with a percept source, otherwise 2), so "up to 3·L before speech"
is right.

---

## BLOCKER

### BF3-1: settle's dependency is the wrong NAc mechanism. Eligibility traces decay per loop tick, not on the wall clock

**Where:** §6.1 "Credit at settle" row, §6.4 third bullet, roadmap OD-A18 ("After OD-A2"), embeddable draft PR 4,
`reply.md` §7. Fold table BD-19 says "folded".

**The claim:** "NAc's traces decay on the wall clock (`nac.py:1162`), so this depends strictly on the clock seam."

**What the code does:** `nac.py:1162` is `record_event`'s `now = time.time()` for the *pending-event / causal-link*
buffer (the 300 s `temporal_window_seconds`, `:439`, `:1327`). The eligibility traces that settle is meant to feed
decay in a different way. `decay_eligibility(factor=0.9)` (`nac.py:3707`) multiplies every trace by 0.9 **per call**,
and `_loop_bio_tick_maintenance` (`agent_loop.py:800-840`) calls it, plus five sibling per-tick decays (reward biases,
goal and cluster biases, percept valences, exploration visits), once per loop tick. So the fast trace's time constant
is "ticks of whoever drives the loop". The machinery clock never touches it.

**Failure scenario:** after OD-A2 and OD-A18 land as written, two NPCs dispatch the same act and get the same receipt
3 world seconds later. NPC A steps every tick at `tick_us` = 100 ms and NPC B at a rate divisor of 5, which §2.1
allows ("multi-rate is allowed"). A's trace is attenuated by 0.9^30 ≈ 0.04 and B's by 0.9^6 ≈ 0.53, a 13× difference
in credit for the same world history. Changing `tick_us` in sim-clock, or adding §9's k reflex substeps, moves every
NPC's learning the same way. This is the step-size dependence §2.1 forbids (the agent's resolution rule). The
bit-identical parity guard misses it, because it compares runs at one step size. Maxim accepted "6 after 3" on our
wrong reason (`response_2.md` §7), so the upstream sequencing would close the wrong gap.

**Fix:**
- Correct §6.1, §6.4, OD-A18 and the embeddable draft. Settle depends on (a) the clock seam for the causal-link
  window and the SCN temporal anchors, **and** (b) rewriting the six per-tick NAc decays as `exp(-dt/τ)` on the
  machinery clock.
- Place §8.2's "step-size invariance exit test in tier A" (still "not yet placed") as an OD-A row that OD-A18 depends
  on, with the NAc decays as its first plant.
- Send the correction to Maxim with the next message, since `reply.md` §7 carried the wrong citation.
- Mark BD-19 partial in the fold table.

---

## SHOULD-FIX

### BF3-2: Yagishita's 0.3–2 s window is cited to justify a settle horizon of seconds to minutes

**Where:** §6.1 "Credit at settle" ("dopamine's window after an action is 0.3–2 s"), §6.4 "Slow effects" and OD-A16's
settle horizon.

Yagishita et al. 2014 (*verified* in BD-19) shows dopamine enlarging spines only 0.3–2 s after glutamatergic input.
Beyond about 2 s it does nothing. BD-19 said longer delays need other machinery (tagging and capture, reverse replay,
BTSP; all *unverified*). v3 keeps the citation and drops that caveat, while §6.4 plans to credit slow effects, such as
ignite heating over many physics steps, through the same settle-into-NAc-traces path with a horizon. NAc's own
window is 300 s (`nac.py:439`), 150× the cited biology.

**Failure scenario:** OD-A16 adds a 60 s settle horizon for ignite. The design's only biological citation says that
path stops working after 2 s, and the bio-mapping reader takes "credit at settle" as EARN-grade on Yagishita.

**Fix:** tag the dispatch/settle *shape* as ANALOG (Yagishita), and the horizon beyond about 2 s as `[engineering]`.
Alternatively, name a long-delay route (replay at outcome, tagging and capture) as *to verify* and an OPEN divergence
in §12.2.

### BF3-3: the yield at about 1 s comes about 300 ms after the account, and Jefferson's metric is about silence

**Where:** O11a, §4.4 floor-holding bullet, §5.1, OD-H5.

Jefferson's 1989 "standard maximum" is about **silence**. Under O11a the NPC is never silent: a filler, then at
600–700 ms an account ("let me think"). An account projects a forthcoming answer, and Stivers & Robinson's
progressivity argument is exactly that a non-answer response *satisfies* the turn. Maxim's own first answer put the
account **at** about 1 s, before yielding ("after about 1 s, people usually give an account before they give up the
floor"). v3 moved the account earlier and kept the yield at 1 s, so the account holds the floor for about 300 ms.
None of the cited sources supports yielding 300 ms after "let me think". BD-7 mentions a word-search display (gaze
aversion, the "thinking face"; Goodwin & Goodwin 1986) as the way people hold the floor through a long search, but
v3 doesn't use it to extend the hold.

**Failure scenario:** a player asks "what's the door code?" The NPC says "uh…" at 200 ms and "let me think" at 650 ms,
gives up the floor at 1000 ms, then 2 s later says "about what you asked…". It reads as erratic, not as thinking.

**Fix:** measure the yield threshold from the last *floor-holding act*, not from the turn end. Or state that an
account plus a word-search display licenses a longer, separately parameterised hold. Either way, cite Jefferson only
for unfilled silence and tag the post-account hold `[engineering]`.

### BF3-4: at the design's own latency, every live reply is a yield. The listener side of BD-4 did not land

**Where:** O11a, §4.4, §4.5's table (D = 1 s, L = 3 s), §5.1's listener hesitation feature (BD-6), §12.2. Fold table:
BD-4 "folded".

With L = 3 s from §4.5 and a yield at 1 s, essentially **every** live-play reply goes filler, then account, then yield,
then a late return. Floor-holding becomes the normal form of an NPC answer, not a fallback. §5.1 also adopted BD-6's
listener rule (store "that the speaker hesitated" as a percept feature), so a slow GPU now writes hesitation features
into every listening NPC's **persisted** memory. Listeners learn that speakers are reluctant, and that carries over
into later sessions on other machines. That is the O12 violation BD-4 named ("variation belongs to the person, not
the machine"). The O11 guards protect only the speaker.

BD-4's CHANGE-OURS had four bullets. Only the meter and the first-filler split landed. Missing: a named Known gap (not
in §12.2, nor in `architecture.md`); "NPC listeners can't tell lateness from hesitation; pretending they can would be
an oracle"; and "the honest fix is latency, not a flag".

**Failure scenario:** a co-op session on a laptop GPU, 40 conversations. Every NPC listener stores about 40
hesitation features against the player and the other NPCs. On the owner's rig the next day, those NPCs treat the
same speakers as reluctant.

**Fix:** add the §12.2 Known gap with BD-4's meter definition (the share of transitions over 700 ms caused by
lateness, per machine) and the two missing sentences. State the expected yield rate at the §4.5 reference latency.
Mark BD-4 partial until they land.

### BF3-5: the costliest phase, P1c deliberation, is left out of mental-fatigue load and the speed trait

**Where:** §2.3 ("Load is world time spent in P1 and Pn"), §4.6 ("load (world time in P1 and Pn × the kind's
weight)"), O12 ("scales the modelled onset"), §4.2's P1c row.

v3 adds P1c as a modelled phase, but the load term still sums only P1 and Pn. So the phase that *is* effortful
control (repeated recurrence through enrichment, Maxim's "PFC" cycles) costs no fatigue. O12 doesn't say whether the
trait scales P1c's per-cycle cost either.

**Failure scenario:** an NPC that deliberates 3 cycles on every choice tires exactly as fast as one that answers at
once. OD-X2 then tests state-dependent timing on a fatigue drive blind to deliberation.

**Fix:** add P1c to the load term in §2.3 and §4.6, with its own weight (`[engineering]`). State whether the trait
scales P1c, and add it to §12.1 item 5's domains.

### BF3-6: "read-only" think and cognition tools drop Maxim's retrieval strengthening

**Where:** §6.1 "World tools vs cognition tools" ("read-only cognition tools (memory recall, narrative) resolve inside
`think`"); embeddable draft §2 ("The agent is read-only on the think path"); OD-EA4.

In Maxim, recall is not read-only. The strength model re-anchors a retrieved trace to now and raises S, which is
Bjork's testing effect (`memory/types.py` record-update docstring: "A retrieval re-anchors to now"; `strategies.py:46`,
`:596`, on the experience clock). PFC enrichment between cycles (`agent_loop.py:584`) recalls memories. A read-only
`think` either loses retrieval strengthening, a caricature of the hippocampus, or keeps it as a side door that breaks
OD-EA4.

**Failure scenario:** an NPC rehearses a fact in deliberation 20 times over a week and forgets it as fast as one that
never recalled it. Or, with the side effect kept, OD-EA4's "no store changes until apply/settle" goes red on the
first recall.

**Fix:** retrieval updates leave `think` as returned writes, stamped with the modelled time of the cycle that
recalled them (not apply time), and are applied by `apply`. Add this to Arch 2.2's census of think-path writes, and
push it upstream with OD-A15.

### BF3-7: the planted-render guard covers instants, not durations or order derived from the machinery clock

**Where:** §6.1 clock-seam row, OD-A2/OD-A3, OD-EA11.

§1 says perceived time includes "durations, order and time of day". The guard plants a sentinel *instant* (raw,
clock and date forms), and the lint bans `datetime.now`, `strftime` and `localtime`. A prompt builder that renders
`f"{(now - stamp)/60:.1f} min ago"` from machinery floats passes both, and hands cognition exact world durations. That
is the same O4 breach BD-12 found, one subtraction later.

**Fix:** add a planted-*interval* test (two events a sentinel interval apart, such as 7 h 13 min 29 s, checked in
seconds, minutes and hours), and ban arithmetic on machinery-clock values in prompt-reaching modules. Durations come
only from the perceived-time port.

### BF3-8: §5.1 attaches the planning neuroscience to the floor-holding repertoire

**Where:** §5.1 OD-H5 bullet ("It enters as `[engineering]` with its evidence cited: response planning starts in the
middle of the other speaker's turn (Bögels 2015) … Castellucci 2022, so 'not a neural mechanism' is too strong").

BD-9 drew the line carefully: the *repertoire* (fillers, accounts, yields) is behavioural conversation analysis, and
the neural evidence is for **when planning starts** (OD-H4) and the speech-planning network. v3 compresses this into
neural evidence for floor-holding, and Maxim's second answer accepted "neural evidence" for the plan. A behavioural
repertoire is now presented as having a mechanism.

**Failure scenario:** the OD-H5 plan's bio-mapping column reads ANALOG (Bögels, Castellucci) for filler selection and
the yield, and a null on gap distribution is read against neural claims no one made.

**Fix:** in §5.1 and OD-H5, write that the repertoire is behavioural `[engineering]` (CA sources), that the Bögels and
Castellucci evidence is ANALOG for OD-H4's early planning, and that the FOK predictor's neural basis is uncited
(*to verify*, as BD-9 said).

---

## NIT

- **BF3-9 (§4.4):** Clark & Fox Tree 2002 is cited *verified* for "*uh* minor, *um* major", but BD-3's caveat (contested
  on acoustics, O'Connell & Kowal 2005) is missing. That signalling function is exactly what picks the first filler.
- **BF3-10 (O11a):** "gaps past about 700 ms read as dispreferred (Kendrick & Torreira 2015)": K&T is a production
  statistic (dispreferred responses outnumber preferred ones past about 700 ms). The perception claim is Roberts et
  al. 2006 (and Kohtz & Niebuhr 2017, secondary). Attribute each to what it shows.
- **BF3-11 (§5.1, §6.1):** Bögels 2015, Castellucci 2022 and Yagishita 2014 appear without the document's
  *verified* / *to verify* tag (BD-9 and BD-19 verified them). Bortfeld 2001 is downgraded to *to verify*, though BD-5
  verified the abstract. The filler-propensity trait isn't in §12.1 item 5, as BD-5 asked.
- **BF3-12 (§4.2 P1c):** "PFC deliberation" is Maxim's label. Say it is Maxim's ANALOG naming, so the phase isn't read
  as a prefrontal claim of ours.
- **BF3-13 (fold table):** BD-6's test (a filler-only turn adds zero utterance records and zero credit events; the
  listener's percept carries the hesitation feature) and BD-19's chooser stamp and named yield-exclusion test on the
  settle path aren't written. "Folded" for BD-6 and BD-19 overstates it (BD-19 is already partial by BF3-1).

## Push back on Maxim (CLAUDE.md)

Owed and not yet in roadmap Phase 3:
- the per-tick NAc decays (BF3-1), and correcting `reply.md` §7's citation;
- retrieval writes on a host-called `think` (BF3-6);
- the step-size invariance exit test, which BF3-1 makes load-bearing.

Each argues against a recorded Maxim choice: the per-tick decay contract in `_loop_bio_tick_maintenance`, and the
"read-only think" in our own draft as Maxim accepted it.
