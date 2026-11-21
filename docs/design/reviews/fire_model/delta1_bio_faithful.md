# Fire model v2, delta round 1: Bio-faithful integration

Reader: Bio-faithful integration lens (`docs/code_review.md`). Design: `docs/design/fire_model.md` v2 on disk in the
`fire-design` worktree (staged, uncommitted; v1 = 08310d1). Lesson 24 on disk. Maxim read only through git at
origin/main 437ec7b1. Membrane read in the `gates` worktree (`src/simcore/adapters/sem/bridge.py`).

**Corrections to my own round-1 findings come first.** Two of round 1's fixes, now folded into v2, rested on false
claims of mine:
- **Round-1 S1** said "`drive:health` is already NOCICEPTIVE and in the fear set, so health loss does condition fear".
  That holds only on a flat body with a root `health` drive (`minecraft_player.yaml`). On the humanoid bodies S1 was
  about, there is no `drive:health` at all (NB2 below).
- **Round-1 S2(a)** said local burn fear "needs only a variant config". Maxim's canonical agent builder has no knob for
  that config, and a recorded invariant forbids it (NB1 below).
- **Round-1 N1** tagged the stand-ins "ANALOG or OPEN". Under Maxim's own definitions they are EARN (NS2 below).

v2 copied all three faithfully, so the errors in v2 are mine.

## Status of round-1 findings (Bio-faithful table)

| Finding | Status | Reading of the tree |
|---|---|---|
| B1 MP-2 against GL1 N4 and TR18, unnamed | **fixed** | §11 item 10 splits MP-2. MP-2a is "a question to GL2b(ii)'s calibration", which matches `autonomic_layer.md:712` and `:1136`. MP-2b names GL1 N4 with the exact quoted phrase (`thalamic_relay.md:881-882`) and TR18 (`:941`, record-only sinks), and it brings evidence. The learner it should feed is still unnamed (NS4). |
| S1 `health` can't be written on humanoids; not a stopgap | **fixed** | §5.1 "Body shape" states that health is derived, cites C5, and makes OD-C10 a prerequisite or names the flat-body divergence. The reworded sentence is there. The fix inherited my false fear claim (NB2), and it misses an existing Maxim damage path (NS1). |
| S2 MP-1 scope and precedent | **open** | (a) The split is in §11 item 10, and (b) the Exp 60 precedent is cited. (c) is not folded: the evidence criterion "health loss inside the drive's comfort band" and the fact that the scenario needs GL2b plus bodies appear nowhere in v2. More importantly, (a)'s premise was wrong, and NB1 supersedes it. |
| S3 sight has no channel; fractions have nowhere to go | **fixed** | §5.1's Sight row reads "whatever is in view … a lamp excites it too", tagged as a stand-in until OD-C8. The fractions stay lab instruments and never go through a region instrument. Lesson 24 still exports the v1 wording (NS5). |
| S4 leak test 2 misfiles tissue | **fixed** | §5.1 test 2 is now "is it transduction". It states tissue properties as world physics and gives core temperature one owner. Lesson 24 carries the correction. |
| S5 lab and NPC not separated; `strike` | **fixed** | §5.4 has two builders. The NPC builder excludes `ignite`, `extinguish`, `strike(energy_j)` and `RegionInstrument`, a golden test covers its surface, and `strike` becomes a body act. `parse_action` refusal goes through `execute`. What happens to the shipped `to_maxim_entity` is unstated (NS3). |
| S6 credit for `apply` OPEN; timing | **fixed** | §5.1 marks `kindle`'s delayed-ignition credit OPEN until OD-A16. §5.4 moves NPC acts to Phase 4 with item entities and bodies. |
| S7 duplicate ids; world_v2 §7 timing | **open** | Fixed: the world_v2 §7 row is in §10.1, and MP-5 → P4/OD-C10 and MP-4 → P3/OD-A16 are mapped. Not fixed: MP-1 and MP-2 still duplicate `research/signals/maxim_senses.md` §5 **P-B** (the Wire-4 allowlist review) and **P-C** (GL2b `NociceptorSpec`). They also duplicate world_v2 §7's own bullets for those two items, and L6's P-F1/P-F2. MP-5 is also P-A. MP-4 omits sem.md P3 and OD-C5, which `tile_and_client.md:240,467` pairs with OD-A16 for `kindle` credit. Five live ids for two asks is the exact case lesson 13 exists to prevent. Fix: one id per ask, with the aliases listed once. |
| S8 NPC lesson claim; LLM prior | **fixed** | §7 "Not claimed" names the LLM prior, Exp 38's counter-prior (checked: `docs/experiments/38_counter_prior_substrate.md`) and L6 §5. §0 item 6 agrees. |
| N1 EARN/ANALOG/OPEN | **fixed** | §5.1 tags every divergence. The tags themselves are wrong (NS2). |
| N2 asks table | **fixed** | §11 item 10's table. |
| N3 phantom-credit attribution; deltas vs absolute | **open** | The author's note says "not folded: belongs to L6". The tree records no reason a reviewer can accept and no trigger. MP-3 will be drafted from L6, so the misattribution and the unstated delta-to-absolute change would travel into a Maxim draft. To close: one clause on §11's MP-3 row ("its draft corrects L6 §4's attribution and states the delta → absolute change"), which would make this `deferred` with MP-3's draft as the trigger. |
| N4 client-only flourish | **fixed** | §12, as a named asymmetry. |
| N5 sem.md N3 verbs | **fixed** | §10.1, the T18 row. |

Counts: fixed 11, open 3 (S2, S7, N3), deferred 0, rejected 0.

---

## New findings on v2

Counts: 2 BLOCKER, 5 SHOULD-FIX, 4 NIT.

### BLOCKER

#### NB1. MP-1(i) "by config, no default change" is neither config-only nor clear of a recorded invariant

**Location:** `fire_model.md::§11` item 10 (MP-1(i) row) and `::§10.1` (world_v2 §7 row, "MP-1(i) is asked
earlier"); `origin/main:docs/plans/autonomic_layer.md:233-234`; `origin/main:src/maxim/runtime/bio_stack.py:200-235,358`;
`origin/main:src/maxim/runtime/agent_factory.py:1227`.

There are two problems, both of which I introduced in round-1 S2(a).

1. **No host can reach the field.** `NACConfig.cluster_fear_failure_modes` is a dataclass field, but
   `build_bio_stack` ("the canonical bio-pipeline construction site … every production agent entry point calls this
   builder") builds `NACConfig(substrate_explore_bonus_weight=…, drive_gate_enabled=…, persistence_path=…)`. It takes
   no NAc config parameter, and `config_loader` has no setting for the field. `agent_factory.py:1227` builds
   `NACConfig(persistence_path=…)`. A "variant config" therefore needs a `src/` change in Maxim: a builder parameter or
   a resolved setting, with three-lens review. The other route is for Overdrive to hand-roll NAc outside the canonical
   builder, which is exactly the kind of workaround CLAUDE.md forbids.
2. **The recorded invariant is unnamed.** `autonomic_layer.md` §1.4 lists among the invariants the plan "must not
   break": "Wire-4 allowlist `DEFAULT_CLUSTER_FEAR_FAILURE_MODES` … No stage edits it; a burn is **not** added to the
   fear set." L6b's MP-1 cited this ("*Touches:* `autonomic_layer.md` §1 invariant"). v2's row dropped it and kept
   only the Exp 60 precedent. Even if (i) avoids the default, "a burn is not added to the fear set" is the decision
   being argued against. CLAUDE.md ("Push back on Maxim") requires that decision to be named.

**Failure scenario.** The owner rules item 10 "as written". MP-1(i) is filed as a config question that needs no
Maxim change. Maxim's review finds that no host can set the field and that it contradicts §1.4, so the ask bounces.
Meanwhile Phase 4 builds its own `NAc(NACConfig(cluster_fear_failure_modes=…))` beside `build_bio_stack` to "use the
config": a silent fork of Maxim's construction site, which is a standing-rule break.

**Fix.** Restate MP-1(i) as "a `build_bio_stack` parameter (or setting) for the fear allowlist, a src change with
three-lens review". Name §1.4's invariant as the decision argued against, and keep Exp 60 as the precedent. The same
§1.4 bullet already governs MP-1(ii).

#### NB2. "`drive:health` … is in the fear set" is false on every humanoid body, so the body-shape choice decides whether a burn conditions fear at all

**Location:** `fire_model.md::§5.1` (Tissue damage row, "drive:health pain, which already conditions fear"; Body
shape, "Until GL2b, an NPC learns fire only from injury"); `origin/main:src/maxim/_data/components/bodies/base_humanoid.yaml:57,198`;
`origin/main:src/maxim/_data/components/bodies/minecraft_player.yaml:26-36`;
`origin/main:src/maxim/embodiment/body.py:511,614`; `origin/main:src/maxim/proprioception/pain.py:134`.

`drive:<name>` pain comes only from a sensor with a `drive:` block (`body.py:511`). Of Maxim's shipped bodies, only
`minecraft_player.yaml` declares a root `health` with a drive. `base_humanoid` (and `infant_humanoid`, which extends
it) has `health: derived` and no health drive. Its health loss surfaces through failure modes, and among them is
`injury` (`health < 0.2`, pain 0.7). Those publish `failure_mode: failure.name` (`body.py:614`), and `injury` is not
in `{"drive:health", "drive:oxygen"}`.

So on the humanoid route that §5.1 recommends (integrity via OD-C10), a burn conditions **no situation fear, not even
from injury**. NAc's tool-level learning still hears the injury, but Wire-4 does not. The sentence "Until GL2b, an
NPC learns fire only from injury, never from the pain that comes first" is wrong in both directions:
- **On a humanoid,** it doesn't learn situation fear from injury either.
- **On an infant body,** DRIVE pain from `arms.thermal` does precede damage and does book NAc aversion. That is what
  Exp 38's false hearth measures. It is only small (R-1's 0.04) and outside the fear set.

I wrote both of v2's sentences in round 1.

**Failure scenario.** Phase 4 picks the humanoid body with OD-C10, on the strength of §5.1's assurance that burn
damage "already conditions fear". NPCs get burned repeatedly and never form fear of the alley fire's situation
cluster. With the LLM prior masking it (§7), this goes unnoticed. MP-1 is also argued to Maxim on a premise its
reviewers will refute.

**Fix.** Correct both §5.1 sentences per body shape:
- **Flat body:** `drive:health`, in the fear set, so fear forms from injury.
- **Humanoid:** `injury` / `concussion` / `crippled` failure modes, not in the fear set, so no situation fear until
  MP-1. Tool-level aversion forms from DRIVE thermal pain where a thermal drive exists.

Make MP-1's ask cover whichever failure mode the chosen body emits, and record the body choice as a Phase 4 decision
that MP-1 depends on.

### SHOULD-FIX

#### NS1. Body shape omits Maxim's existing per-part damage path

**Location:** `fire_model.md::§5.1` (Body shape), `::§11` (MP-5 "a prerequisite of per-part burns");
`origin/main:src/maxim/embodiment/spec.py:1025` (`apply_damage(amount, damage_type)`);
`origin/main:src/maxim/_data/components/bodies/base_humanoid.yaml:118` (`torso.damage_affinities.fire`);
`origin/main:src/maxim/simulation/tools.py` (`damage_component`, the #873 comment: "Damage lands on a part or not at
all").

Maxim already routes typed damage to a part: `ModulatorSpec.apply_damage` distributes damage by
`damage_affinities[damage_type]`, and base_humanoid's torso declares `fire: {core_integrity: 0.8}`. The design lists
only two routes, OD-C10 and a flat body, so "Search Maxim before proposing" isn't met for MP-5's motivation.

This route may well be unsuitable, and the design needs to say why. It has no world-owner refusal like
`world_set_axis`. `fire` affinity exists only on the torso. The sim tool publishes its own pain, which would be a
second pain path beside `evaluate_failures`.

**Failure scenario.** Maxim's review of MP-5 answers that "per-part fire damage exists (`apply_damage`, #873)" and
asks why it isn't used. The ask stalls, or Phase 4 calls `apply_damage` directly without the analysis above and adds
an unowned body write.

**Fix.** Cite it, then use it or reject it with reasons, and keep MP-5's evidence to what `apply_damage` can't do.

#### NS2. The divergence tags invert Maxim's meaning

**Location:** `fire_model.md::§5.1` (Divergences); `origin/main:docs/plans/bio_faithful_roadmap.md:12-15`.

Maxim's definitions are:
- **EARN:** we intend to implement it; a trigger and target are listed.
- **ANALOG:** a deliberate engineering analog; "implementing the biology is NOT a goal".
- **OPEN:** undecided.

v2 tags "generic in-view luminance" as ANALOG while also calling it "a stand-in for vision until OD-C8", and it tags
the root-sensor skin stopgap ANALOG although MP-5/OD-C10 is planned to remove it. Both are EARN, with triggers OD-C8
and OD-C10. Credit as OPEN until OD-A16 is arguably EARN too, since OD-A16 gates Phase 4 (O30). (My round-1 N1
suggested these tags.)

**Failure scenario.** An upstream draft quotes the ANALOG tags. Maxim reads them as "Overdrive does not intend to
build vision or per-part skin", and OD-C8 and OD-C10 lose their stated need.

#### NS3. Which builder `to_maxim_entity` becomes is unstated, and the NPC builder has no caller in Phase 1

**Location:** `fire_model.md::§5.4` (two builders); `gates:src/simcore/adapters/sem/bridge.py::to_maxim_entity`,
`::region_parts`.

Today's shipped `src/` builder is the lab surface: every `RegionInstrument` plus `structure` with
`strike`/`ignite`/`extinguish`. v2 says "the lab builder lives in tests only" and the NPC builder "exposes no …
`RegionInstrument`". Read together, the shipped region Entity in Phase 1 has no sensors (fractions wait for OD-C8)
and no modulators. That is an empty surface with no caller until Phase 4, which is capability without a caller
(CLAUDE.md, "A fix ships with a caller"). The golden test would also pin a surface no NPC uses yet.

**Failure scenario.** Step 6 keeps `to_maxim_entity` in `src/` unchanged, as "the lab builder", because nothing says
otherwise. Phase 4 then picks up the only `src/` builder, and with it `ignite` and the omniscient instruments that
§5.5 forbids.

**Fix.** State it explicitly:
- In Phase 1, `to_maxim_entity`'s lab surface moves under `tests/`, and `ignite`/`extinguish` are deleted from
  `StructureModulator`.
- The NPC builder and its N7 golden fixture land with Phase 4's first NPC body, which is their caller.

#### NS4. MP-2b names neither its learner nor the cheaper alternative inside GL2b

**Location:** `fire_model.md::§11` item 10 (MP-2b); `origin/main:docs/plans/autonomic_layer.md:658`, §3.2 ("a second
receptor on the same sensor", `modality` used "for track routing"); `thalamic_relay.md:941`.

MP-2b asks that the 41–46 °C band feed "a learner" but doesn't say which one:
- the PainBus learners via `affective_slow`, which reverses TR18 wholesale;
- a new subscriber;
- GL4's join.

It also doesn't weigh the alternative GL2b's design nearly allows already: a second, lower-threshold `NociceptorSpec`
whose events route to `nociceptive_fast`. That puts the warning band on PainBus with no TR18 change. Its cost is a
named FUNCTIONAL divergence (C-fibre-range heat on the Aδ track). §3.2's YAML shows one `nociceptor:` per sensor, so
even this needs a small schema question.

**Failure scenario.** Maxim's reviewers ask which learner, and whether the second spec on the fast track suffices.
The pushback has no answer, and TR18, a decision its own review reached, is challenged for more than the evidence
needs.

**Fix.** Name the learner. State the two options and argue for one, with the closed-form 41–46 °C dwell times as the
deciding evidence.

#### NS5. Lesson 24 still exports v1's leaking sight sensor

**Location:** `lessons_maxim_in_games.md::24` ("luminous flame in view").

v2 §5.1 fixed S3: generic luminance, so "a lamp excites it too". The lesson, which is the document meant for other
engines, still lists "luminous flame in view" as a world-computed stimulus. That is the oracle shape leak test 1
rejects. Its "state reaches an NPC only as continuous fractions through a percept" also omits v2's caveat that no
such channel exists until OD-C8.

**Failure scenario.** A reader applies lesson 24 and builds a flame-detector "sight" sensor that fires only for fire:
an NPC that fears fire through walls and never fears a lamp's heat. That is exactly the case the lesson's own test
forbids.

**Fix.** Say "luminance, size and flicker of whatever is in view, after line of sight", and add "until a percept
channel exists, fractions stay lab instruments".

### NIT

- **NN1. Ask timing is half stated.** `fire_model.md::§10.1` says only MP-2a and MP-1(i) are "asked earlier".
  MP-2b's and MP-1(ii)'s timing is unstated, and L6b §5's order table ("MP-2, then MP-1 … ask now", whole) isn't
  reconciled with the split. Add a "when" column to §11's table.
- **NN2. Undefined referents.** `fire_model.md::§5.1`: "the root-sensor skin stopgap" is defined only in L6b §5 (a
  `TEMPORARY(phase3)` root `world` sensor). The Sight row computes line of sight world-side, while world_v2 §7 (P-E)
  still lists "percepts gated by line of sight" as a Maxim ask. Say whether P-E stands or is withdrawn.
- **NN3. Band edges overlap.** MP-2b's slow band is 41–46 °C, against L6b's 41–45 with the fast receptor at ~46. Pick
  one edge, so the dwell-time evidence measures a defined interval.
- **NN4. The Tissue damage row is unconditional.** It says "a Henriques integral into the part's `integrity`", but
  the same section's Body shape paragraph says that route needs OD-C10 or doesn't exist on a flat body. Write "into
  the part's `integrity` (OD-C10) or root `health` (a flat body)".
