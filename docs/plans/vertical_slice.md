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

**Relaxed:** one review round, not delta rounds; no diff-coverage, golden screenshots or cross-tier tests; gamey
constants, each commented where it is used.

**Kept:** CLAUDE.md's rules for the server, the applier, time and the wire hold here unchanged ("Rules that matter
here"; "Game engineering"). The slice adds:
- No file under `src/` changes; a core need it finds becomes a row in §8.
- It follows `main`'s API, merging `main` weekly. Its data stays in `spikes/slice/data/`, read with the repo's strict
  YAML reader.
- The LLM proposes words, never world state: the voice lives on the server, outside the simulation.
- On its raw socket, HTTP is refused at the first bytes: the slice's form of the `Origin` refusal.

**At the end**, every piece is either deleted or rebuilt through its real step. Nothing graduates by copy.

## 3. What the slice adds

### 3.1 The loop: a fixed timestep

The server runs a fixed simulation tick of 0.1 s, one `Simulation.step`, on a 0.2 m grid, paced to the wall clock. It
sends snapshots at 10 Hz. The client renders at its own frame rate and interpolates between snapshots.

- **Budget:** 100 ms per tick. The tile spec measures the heat substep at 0.59 ms at 0.2 m and 4.5 ms at 0.1 m
  (`tile_and_client.md` §1), so there is headroom.
- **Week 1 measures** tick CPU (min of N), snapshot bytes and encode time.
- **If a tick overruns,** the server slows the world (time dilation) rather than skipping ticks, and logs it.

### 3.2 The wire

- **Framing:** length-prefixed JSON frames over TCP.
- **Snapshots:** the existing `simcore.protocol.encoding.snapshot`, `zlib`-compressed. Raw, the 60 × 20 × 24 alley is
  about 29k cells, under 100 KB a frame.
- **Client to server:** `hello`, `move` (with Overdrive), `kindle`, `strike`, `say`.
- **Server to client:** `welcome`, `state`, `event`, `npc_line`, `error`.
- **Versioning:** none on purpose. The slice's format is `slice-0` and dies with it. Step 7 designs the real one.

### 3.3 Fire as a fuel budget (VS4)

Not fire's model, and nothing cites it as one: fire's truth is `fire_solid.md` and the ladder, and Phase 1's exit is
the torch-lit slab. `spikes/slice/data/fuel.yaml` holds, per material, `releasable_energy_j_kg` (wood 12.4 MJ/kg, the
tile spec's ΔH_c,eff), `ignition_c` and `burn_rate_kg_s_m2`, and per object a burnable share of its box.
`slice_server/fire.py` holds the laws:
1. **Fuel and power:** fuel is volume × density × share; power is burn rate × area × releasable energy, the area
   shrinking as (m/m₀)^(2/3); out at 5% of fuel.
2. **Growth:** power grows as (t / 90 s)² to that limit, a t-squared design fire. Without it no fire is ever small.
3. **Ignition by a skin:** a 2 mm surface node per object, heated by radiation and cooled by convection and
   re-radiation, lights at `ignition_c`. No cell mean is thresholded.
4. **Spread and the books:** a burning object radiates χ_r = 0.3 of its power as a point source,
   q = χ_r·P / (4πr²). The cells get the other 70% through the applier; the radiated share reaches skins and bodies
   or is exported. Conduction through air can't spread fire (0.34 m in 90 minutes, `tile_and_client.md` §1).
5. **Changes of state** (lit, doused, burnt out) happen only in the fire's step, beside the decision the world gets.

A pallet stack sits 0.4 m from the crate so spread can happen; `crate_far` stays out of reach.

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
      slowly, and fast in the puddle (rain under an awning gap).
  - **Tuned to a ladder:** Overdrive trips after about 168 s in still air, 31 s at 1 m from a full fire, never in
    the puddle (`tests/test_heat_debt.py`).
  - **Overheat:** above `T_warn` the HUD warns, and the NPC notices (smoke off your cyberware). Above `T_trip`,
    Overdrive cuts out and the body slows for 10 s.
- **What Overdrive buys:**
  - speed;
  - a harder `strike`: it cracks what it hits (120 kJ, 6 kJ of heat, recoil), but can't breach a wall. A walkable
    gap in 0.4 m drywall took 31 strikes of 250 kJ, so the glass and drywall were cut (owner, 2026-11-21).
- **Test (in `spikes/slice/tests/`):** with no Overdrive and no evaporation, `T` relaxes toward `T_air` as
  `exp(−hA·t/C)`. One closed-form check, so the tuning knobs mean what they say.
- **Tunables:** all of these live in `spikes/slice/data/body.yaml`.

### 3.5 The NPC: a behaviour tree with a voice

One NPC, a street vendor at a stall near the alley mouth.

**How it decides:** a behaviour tree, evaluated each tick, in priority order:
1. **flee** while the radiant flux on it passes 2.5 kW/m² (2 kW/m² is painful within 45 s; air warms too slowly);
2. **douse** a fire under 100 kW within 3 m of the stall, from 1.2 m, while it has a charge;
3. **warn** while a fire burns within 8 m;
4. **comment** when the player is overheating within 3 m;
5. **idle** otherwise.

**How it speaks:**
- Each change of the tree's state requests a line; the server words the prompt from the event's fields.
- The reply is capped at 25 words, asked of Ollama on 127.0.0.1 off the tick thread, with a 2.5 s timeout.
- Any failure falls back to a canned line and logs why.
- Measured (lesson 30): 0.23 s warm with the game alone on the Mac mini; 8 s with other work loading the machine.

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

Each session writes `spikes/slice/sessions/<n>.jsonl` (gitignored): intents by tick, tick stats every 50 ticks,
each vendor line with its source, latency and queue time, and a clean end's digest (or where it crashed).

The intent log plus the scene reruns a session bit for bit, which is the slice's replay test (§5). Heat, Overdrive
seconds, fires and the vendor's states are read out by replaying it, not stored twice.

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
  that no record reaches the engine.
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

- **Sessions:** three of 15 minutes, on the Mac mini (owner, 2026-11-21): the owner and two people new to the design.
  Each is logged (§3.7), the player thinking aloud.
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
