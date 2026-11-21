# Vertical slice plan: one alley, played, in four weeks

A thin cut through every layer (input, simulation, wire, rendering, one mind) to answer one question by playing:
**is Overdrive-as-heat-debt in a burning alley fun for ten minutes, and why or why not?** The answer decides how far
the fire ladder (step 6) and the NPC line need to go before anything else is built. Budget: this plan ≤ 2,500 words;
the verdict note ≤ 1,000. No other documents.

## 1. Decisions

| Id | Decision | Who, when |
|---|---|---|
| VS1 | A prototype lane: the slice lives in `spikes/slice/`, imports `simcore` read-only, and is throwaway | owner, 2026-11-21 |
| VS2 | One NPC: a scripted behaviour tree decides; a local LLM (qwen2.5:3b) only writes its lines | owner, 2026-11-21 |
| VS3 | Time-box: four weeks, 2026-11-23 to 2026-12-18; overruns cut scope (§6), never extend | owner, 2026-11-21 |
| VS4 | Fire: a per-material fuel budget (§3.3) | owner, 2026-11-21 |
| VS5 | Step 10 (D28) moves here; the verdict lands before Phase 2's crate and rungs 6.2–6.4 are scheduled or rerun 2 is unbanked. 6.1, the slab exit (fire fallback, owner 2026-11-20, `solid_spike/results_rerun1.md` §7), is untouched | owner, 2026-11-21 |

## 2. The lane's rules

**What is relaxed:**
- One review round at the end (Executor and Architecture) instead of delta rounds.
- No diff-coverage, no golden screenshots, no cross-tier tests.
- The slice may threshold cell means and use gamey constants. Each place where it does says so in a comment.

**What still holds, because breaking it would teach the wrong lesson:**
- **The server is authoritative.** The Godot project draws and sends intents, nothing else.
- **Every world change goes through `simcore.core.applier`.** The slice never writes cells or sources directly.
- **The LLM proposes words, never world state.**
- **The wire binds 127.0.0.1,** requires the per-launch token, and refuses an `Origin` header.
- **Simulation time comes only from `World.advance`.** The wall clock paces the loop and times LLM waits, and never
  enters the sim.
- **No dependencies outside the lock.** The wire is stdlib `socket`, `zlib` and `json`; Godot's `StreamPeerTCP`.
- **ruff, typed GDScript and the isolation rules apply.** Session logs go inside the worktree.
- **No file under `src/` changes on this branch.** A core need the slice finds becomes a row in §8, for the real steps.
- **The slice follows `main`'s API.** It merges `main` weekly and adapts when 3b(b) lands (scene v1 with `spawns`,
  coded `Refused`). Its data stays in `spikes/slice/data/`, outside `data/`, read by the slice itself.

**At the end**, every piece is either deleted or rebuilt through its real step. Nothing graduates by copy.

## 3. What the slice adds

### 3.1 The loop: a fixed timestep

The server runs a fixed simulation tick of 0.1 s, `world.advance(0.1)` on a 0.2 m grid, paced to the wall clock. It
sends snapshots at 10 Hz. The client renders at its own frame rate and interpolates between snapshots.

- **Budget:** 100 ms per tick. The tile spec measures the heat substep at 0.59 ms at 0.2 m and 4.5 ms at 0.1 m
  (`tile_and_client.md` §1), so there is headroom.
- **Week 1 measures** tick CPU (min of N), snapshot bytes and encode time.
- **If a tick overruns,** the server slows the world (time dilation) rather than skipping ticks, and logs it.

### 3.2 The wire

- **Framing:** length-prefixed JSON frames over TCP.
- **Snapshots:** the existing `simcore.protocol.encoding.snapshot`, `zlib`-compressed. Raw, the 60 × 20 × 24 alley is
  about 29k cells, under 100 KB a frame.
- **Client to server:** `move` (with Overdrive), `look`, `kindle`, `strike`, `say`.
- **Server to client:** `snapshot`, `body`, `npc_line`, `event`.
- **Versioning:** none on purpose. The slice's format is `slice-0` and dies with it. Step 7 designs the real one.

### 3.3 Fire as a fuel budget (VS4)

The owner remembered "releasable energy per material alongside a flammable tag". It exists only on paper:
- T18 specified flammable labels, and `fire_model.md` §5.3 records that none reached `src/`.
- Its successor is the 6.0a data files: `chemistry.yaml` with ΔH_c,eff, and the crate as a porous bed with 32.4 kg
  of wood and 5.4 m² of surface (`tile_and_client.md` §1). Not built.
- Today `data/materials/core.yaml` has no fuel field, and `Applier.ignite` adds a heat source of fixed power that
  never runs out (the burnout gap).

**The slice's version** is a slice-local `spikes/slice/data/fuel.yaml`. It does not touch `core.yaml` or pre-empt
6.0a's format. Per material it holds:
- `flammable` (bool),
- `releasable_energy_j_kg` (wood: 12.4 MJ/kg, the tile spec's ΔH_c,eff),
- `ignition_c` (gamey: wood 300 °C),
- `burn_rate_kg_s_m2` (gamey, tuned so the crate burns for about 3 minutes).

Each named object keeps a fuel mass, its volume × density × fuel fraction. Per tick:
1. **Ignite:** a flammable object whose hottest exposed cell passes `ignition_c` is ignited through the applier.
   *Gamey: this thresholds a cell mean.*
2. **Burn:** the source's power is `burn_rate × exposed area × releasable energy`, and fuel drops by
   `burn_rate × area × dt`. When fuel reaches zero the source is extinguished through the applier.
3. **Spread by radiation.** Conduction through air cannot spread fire: the tile spec puts the diffusion length at
   0.34 m in 90 minutes. So a burning object radiates as a point source, `q = χ_r·P / (4πr²)` with χ_r ≈ 0.3. This
   is the standard point-source model from fire engineering. Each other flammable object receives it on its nearest
   face, as heat deposited through the applier.

The scene adds one fuel object near the crate (a pallet stack 1.0 m away) so that spread can happen at all.
`crate_far` stays out of reach.

This is not fire's model, and nothing cites it as one. Fire's truth stays `fire_solid.md` and the ladder. The
slice's burning crate is a gamey stand-in for play, not Phase 1's exit, which is the torch-lit slab.

### 3.4 The body and Overdrive as heat debt

- **Movement: dynamic motion, kinematic collision.** A capsule (radius 0.3 m, height 1.8 m, mass 80 kg) with a
  velocity.
  - `move` carries a desired direction and effort, never a step, so either body model reads the same intent.
  - Drive force and friction are integrated by semi-implicit Euler: velocity first, then position. Top speed is
    1.5 m/s, or 3 m/s in Overdrive.
  - Eight substeps per tick: at 6 m/s none crosses half a 0.2 m cell, so nothing tunnels.
  - Collision uses the tile spec's slide rule, and the blocked axis's velocity drops to zero.
  - An Overdrive strike or a blast near a body applies an impulse (knockback). Drive work, ½mv², is logged against
    Phase 5's action energy.
- **Heat:** each body is one lumped thermal node for its cyberware: core temperature `T` and capacity `C`.
  - Heat in: `P_od` while Overdrive is held, plus radiation from fires by §3.3's point-source law.
  - Heat out:
    - Convection: `hA·(T − T_air)`, where `T_air` is the mean air temperature over a 1 m sphere around the body,
      read from the frame (a consumer reads at its own scale, never one cell).
    - Evaporation: while coolant remains, it boils off at `L = 2.26 MJ/kg`, capped per second. Coolant refills
      slowly. In the puddle zone (rain under an awning gap), evaporation is unlimited and coolant refills fast.
  - **Overheat:** above `T_warn` the HUD warns, and the NPC notices (smoke off your cyberware). Above `T_trip`,
    Overdrive cuts out and the body slows for 10 s.
- **What Overdrive buys:**
  - speed;
  - `strike` at Overdrive power, which can break the glass panel and the drywall partition the slice adds.
    Concrete stays out of reach.
- **Test (in `spikes/slice/tests/`):** with no Overdrive and no evaporation, `T` relaxes toward `T_air` as
  `exp(−hA·t/C)`. One closed-form check, so the tuning knobs mean what they say.
- **Tunables:** all of these live in `spikes/slice/data/body.yaml`.

### 3.5 The NPC: a behaviour tree with a voice

One NPC, a street vendor at a stall near the alley mouth.

**How it decides:** a behaviour tree, evaluated each tick, in priority order:
1. **flee** when the air near it passes 60 °C;
2. **put the fire out** when a fire is small and within 2 m of its fire extinguisher, through the applier;
3. **warn** when a fire burns farther away;
4. **comment** when the player is overheating near it;
5. **idle** otherwise.

**How it speaks:**
- Each decision that changes the tree's state may request a line.
- The prompt carries the new state and a few perceived facts. The reply is capped at 25 words, sent to Ollama on
  127.0.0.1 off the tick thread, with a 2.5 s timeout.
- On a timeout or a refusal it falls back to a canned line.
- Measured on this machine (`spikes/llm/results/`): about 0.3 s to the first token and 1–2 s for a short reply.

**Talking to it:** the player's `say` text goes into the next prompt as words. It can change what the NPC says, never
what it does.

**It senses by oracle, on purpose.** It reads heat and glow within 4 m and the player's core temperature straight
from the frame, exactly what lesson 24 rules out for real NPCs. They stay in `spikes/` and set no precedent for SEM sensors.

**Not here:** Maxim. This NPC is the comparison baseline. If the verdict says "the vendor felt alive enough", that is
a number the NPC line has to beat.

### 3.6 The client: a separate Godot project

- **Where:** `spikes/slice/godot/`, a separate 4.7.2 project, the same pattern as `tools/godot_probes/`. Throwaway
  code stays out of `client/`'s gate and goldens.
- **Drawing the alley:** solid cells are drawn as one `MultiMeshInstance3D` of cubes. A MultiMesh draws thousands of
  instances in one draw call, which suits grey-box voxels.
- **Per-cell state:** material sets each cube's base shade; glow raises emission and brightness; crack shrinks the
  cube and darkens it. State is never shown by colour alone.
- **Reuse:** once `phase1/client-shader` lands, crack and glow copy its `render/*.gdshaderinc`.
- **Black background:** 4.7.2 Compatibility maps a non-black clear colour differently with glow on, glow off and at
  render scale 0.5 (measured on `phase1/client-shader`).
- **Flames:** a `CPUParticles3D` per burning object, purely visual.
- **The rest:** a third-person camera, a HUD with core temperature, coolant and an Overdrive meter, and NPC lines as
  a speech label.

### 3.7 Telemetry

Each session writes `spikes/slice/sessions/<n>.jsonl` (gitignored):
- intents, by tick;
- body temperature, coolant and Overdrive seconds, once a second;
- ignitions, spreads, burnouts and NPC states;
- LLM latencies.

The intent log plus the scene reruns a session, which is the slice's replay test (§5).

## 4. Schedule

| Week | Builds | Done when |
|---|---|---|
| 1 (11-23) | the fixed-tick server, the wire, the Godot project drawing the alley live, the body walking | you walk around a crate lit by `kindle` (glow needs rung 6b); tick CPU and snapshot bytes logged |
| 2 (11-30) | §3.3 fire (ignite, burn, burnout, radiative spread), §3.4 heat debt and the HUD | a lit crate spreads to the pallet and both burn out; Overdrive near the fire trips you, the puddle saves you |
| 3 (12-07) | §3.5 the NPC and its voice, `strike` in Overdrive, the glass and drywall | the vendor warns, flees or puts the fire out unscripted by the player; `say` changes its lines and never its acts |
| 4 (12-14) | tuning, three playtests, the verdict note | §7's note is written and the owner reads it |

## 5. Tests the lane keeps

These are few, and each guards something the verdict depends on:
- **The closed form for body cooling** (§3.4).
- **A fuel budget conserves energy:** the heat released equals fuel burned × releasable energy, within 1%.
- **Replay:** the same intent log gives the same final state digest.
- **The NPC cannot write the world:** a test feeds the voice a line asking to "set the crate on fire" and checks
  that no applier call happens.
- **Wire refusals:** a missing token, an `Origin` header and an oversized frame are each refused.

## 6. Cut list

When a week slips, cut in this order and record each cut in the verdict note:
1. the LLM voice (canned lines instead);
2. `strike`, glass and drywall;
3. radiative spread (one object burning alone);
4. the puddle zone (coolant refill only).

The fixed tick, the body, fuel burnout, heat debt and the HUD are the slice itself. If those don't run by the end of
week 3, the verdict is about why not.

## 7. The playtest and the verdict

- **Sessions:** three, about 15 minutes each: the owner, and two people who have not read the design. Each session
  is logged (§3.7), with the player thinking aloud.
- **Questions:**
  - Did you change where you went or fought because of heat?
  - Did you use fire on purpose?
  - Did you read the alley's state (glow, cracks, the gauge) without being told?
  - What did the vendor add?
  - When did you stop having fun?
- **Numbers:**
  - Overdrive seconds per minute;
  - deaths or trips by overheat;
  - fires lit on purpose against fires lit by accident;
  - time spent in the puddle zone;
  - LLM fallback rate and p95 latency.
- **The verdict note** (`docs/plans/vertical_slice_verdict.md`, ≤ 1,000 words) answers, with evidence:
  1. Is heat debt the core loop, or does it need a different pressure?
  2. Which fire behaviours did the player notice and use? This sets the fire ladder's stopping rung: build only the
     rungs that change something a player noticed.
  3. Did the scripted vendor feel alive? What would a Maxim NPC have to do that it couldn't?
  4. Did the tick, wire and snapshot budgets hold?

## 8. What feeds back

- **The roadmap:** step 10's row moved here after `phase1/solid-spike` merged (`foundations_plan.md`, D28, Phase
  2's crate bullet). The owner scopes Phase 2's fire from §7's answer 2.
- **Step 5b's body model:** whether players used momentum and knockback decides kinematic against dynamic before
  5b's code (`tile_and_client.md` §2.3 is kinematic today).
- **`docs/lessons_maxim_in_games.md`:** one entry from §7's answer 3, with its numbers.
- **The real steps:** each core need the slice found becomes a row against its step (bodies in 5b, the wire in 7,
  fuel in 6.0a).
- **Then** `spikes/slice/` is deleted, or kept as a reference spike if the owner wants it.

## 9. Risks

- **The prototype that ships.** Slice code drifts into `src/`. *Answer:* §2's "no file under `src/` changes", and
  §8's rebuild through real steps.
- **Gamey fire teaches false lessons** about what real fire allows. *Answer:* §7 judges noticed behaviours, not
  numbers. The fire ladder still owns truth.
- **The slice becomes a design project.** *Answer:* one plan, one verdict note, one review round, the cut list.
- **The LLM voice dominates the impression.** *Answer:* the cut list makes it the first to go, and one playtest runs
  with canned lines.
