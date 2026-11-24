# Architecture review: phase1/vertical-slice (`origin/main...HEAD`, 9 commits, merge base 755f5a2)

## Summary

The lane keeps its hard rules. No file under `src/`, `data/` or `client/` changes. Every world write goes through `Applier.apply`. No module in the simulation path reads the clock, a random source or `hash()`. The voice is never imported by any simulation module. The wire binds 127.0.0.1 and requires the token, compared in constant time. I found two real crash paths and two layering and honesty problems that matter for the verdict.

**Counts: 0 BLOCKER, 6 SHOULD-FIX, 5 NIT.**

- **S1 is close to a BLOCKER.** I reproduced a server crash on the shipped path. I graded it SHOULD-FIX only because, by the charter's definition, its trigger is narrow.

**What I ran, all read-only.** Two Python probes in my scratchpad, with `PYTHONDONTWRITEBYTECODE=1` and the worktree's venv:
- a kindle-while-the-vendor-is-adjacent repro;
- a 4,000-tick crate-and-pallet burn.

Nothing in the repo was written, and I did not run the gate.

## Findings

### S1. SHOULD-FIX (reproduced): kindling a fuel while the vendor is within douse reach crashes the server
**Location:** `spikes/slice/slice_server/sim.py::Sim.step` / `Sim._vendor_step` / `Sim._apply`, `fire.py::Fire.kindle` / `Fire.douse`

**Defect.** The fire's state and the world's heat sources are two copies, and they are written at different points in a tick.
- `Fire.kindle` sets `burning=True` at once, during `_take`. The world's `fire:<region>` source only appears later, when `fire.step`'s decision is applied.
- `_vendor_step` runs between those two moments. It sees the new fire as small (power 0 ≤ 100 kW). If the vendor is within `douse_reach_m` (1.2 m), it calls `fire.douse` and then `Extinguish`.
- The applier correctly refuses that `Extinguish`, because nothing is burning yet, and `_apply` turns the refusal into `RuntimeError`.

**Reproduced:**
- Setup: `Sim(config.load())`, player at (5.4, 2.9) facing the crate, vendor at (5.4, 2.2), then `step([Kindle()])`.
- Result: `RuntimeError("the applier refused the fire's Decision(region='crate', power_w=0.0, out=True): nothing is burning on the crate")`.

**Failure scenario in play:**
1. The player lights the pallet.
2. The vendor walks toward it. The crate lies on the straight line from the stall (4.6, 3.0) to the pallet, so it passes within 1.2 m of the crate.
3. The player kindles the crate on that tick.
4. `Server.run` propagates the exception and the playtest session dies. `serve`'s `finally` then logs an "end" digest of a half-applied tick.

The stall sits 1.4 m from the crate against a 1.2 m reach, so one week-4 tuning change (raising `charges` or `douse_reach_m`) puts this on the idle path.

**Second trigger, unverified.** A fuel whose region the applier calls "gone" (struck away) would make `Ignite` fail the same way, because `_kindle` and `fire.step` target fuels by their authored bounds, not by the world's regions.

**Root cause.** The Fire module is a second source of truth for "is burning" with no single commit point. A guard at the call site would be a band-aid.

### S2. SHOULD-FIX (from reading urllib; not run): a voice failure outside `VoiceFailed` kills the authoritative server
**Location:** `spikes/slice/slice_server/voice.py::ollama.ask`, `Voice.ready`

**Defect.**
- `ask` catches `URLError`, `TimeoutError` and `JSONDecodeError`.
- `urllib.request.AbstractHTTPHandler.do_open` wraps only `h.request` errors in `URLError`. Errors from `h.getresponse()` and `response.read()` propagate unwrapped, for example `http.client.RemoteDisconnected`, `ConnectionResetError` and `http.client.IncompleteRead`.
- `_speak` only catches `VoiceFailed`, so such an exception is stored in the future. `Voice.ready()` then calls `f.result()` on the tick loop's thread and re-raises it inside `Server.run`.

**Failure scenario.** Ollama is restarted or OOM-killed mid-reply during a playtest, and the game server exits.

**Rules and claims broken:**
- the module docstring's "Any failure ... falls back to a canned line";
- the plan's premise that the voice stays out of the simulation's life (VS2, §3.5).

### S3. SHOULD-FIX: `Sim` mixes the simulation with the wire, display quantization and the voice's prose
**Location:** `spikes/slice/slice_server/sim.py::Sim.state`, `Sim._facts`, and the module's imports of `slice_server.wire.pack_cells` and `simcore.protocol.encoding.snapshot`

**Defect.** The module says "No clock and no IO here", but `Sim` has about ten jobs:
- world setup;
- intent dispatch;
- body stepping;
- vendor perception, decision application and dousing;
- strike and kindle targeting;
- body heat;
- the client message (`state()` packs zlib/base64 cell channels and builds the display-only `HEAT_LOW_C`/`HEAT_HIGH_C` quantization);
- the LLM's prompt text (`_facts`);
- the digest.

The simulation module imports the wire module, so the dependency runs upward. The "words never become acts" boundary is held only by `test_no_simulation_code_imports_the_voice`, an import-name scan. Meanwhile `Sim` itself authors what the voice is told.

**Consequences:**
- any change to the client message or a prompt edits the deterministic core module;
- step 7 or 5b cannot lift the sim without the wire;
- a later "facts" change that reads voice state would not trip the import scan.

The lane relaxes rigor, not separation of concerns. The plan says pieces are "rebuilt through its real step", and that is harder from this shape.

### S4. SHOULD-FIX: the plan describes a slice that was not built
**Location:** `docs/plans/vertical_slice.md` §2, §3.2–§3.5, §5

The week-1 fold updated the plan; weeks 2–3 changed the design and did not. Differences between the plan and the code:

| Plan | Code |
|---|---|
| §3.3 ignition: "hottest exposed cell passes `ignition_c` ... thresholds a cell mean" | a slice-local 2 mm skin node (`fire.py::Fire._skin_rate`) |
| §3.3 spread: radiation is "heat deposited through the applier" | nothing is deposited; the skin's energy is booked outside the world |
| §3.3: no growth phase | a t-squared growth phase (`growth_s` 90 s) |
| §3.5 flee: "air near it passes 60 °C" | flux over 2.5 kW/m² |
| §3.5 douse: "within 2 m of its fire extinguisher" | `douse_range_m` 3.0 m from the stall and `douse_reach_m` 1.2 m |
| §3.4 puddle: "evaporation is unlimited" | only the refill rate changes (`heat_debt.step`) |
| §3.2: a `look` intent | dropped (`intents.py` docstring) |
| §2: "refuses an `Origin` header" | HTTP verbs refused at the first bytes (`wire.py`) |
| §3.4: strike "can break the glass panel and the drywall" | glass and drywall cut (commit cfb1fff) |

**Consequence.** §7's verdict and §8's "each core need becomes a row against its step" will be written against this plan. A reader of the plan would conclude the slice thresholds cell means and deposits spread heat through the applier, and it does neither.

**One-owner rule (merged to main today).** §2 restates CLAUDE.md's rules (authoritative server, applier-only writes, 127.0.0.1 + token + `Origin`) instead of linking them. The Origin line has already drifted from the code, which is the failure that rule exists to prevent.

### S5. SHOULD-FIX: fire radiation is created energy, but the comments call it exported
**Location:** `spikes/slice/slice_server/fire.py` module docstring ("the same 'exported, unreceived' accounting the tile spec gives flame radiation"), `Fire.flux_at`, `sim.py::Sim._heat_body`

**Defect.**
- The world receives 100% of each fire's power. `test_the_cells_gain_exactly_the_energy_the_fire_releases` asserts this to 1e-6.
- On top of that, `χ_r·P` is delivered to neighbour skins, to the player's heat node (`radiant_w_m2 * radiant_area_m2`) and to the vendor's flee decision.
- In the tile spec (§1.2, §5.4), the exported line is debited from the flame. Here nothing is debited, so radiation adds energy to the slice's books.

**Rule broken.** The lane permits gamey constants only where "each place where it does says so in a comment". This place says the opposite. §5's "fuel budget conserves energy" test checks only the cell side, so it cannot see the extra energy.

### S6. SHOULD-FIX: lesson 29 presents a contaminated latency as the game's measured L
**Location:** `docs/lessons_maxim_in_games.md` §29

**Defect.** "At the measured 8 s the bound is 1/8 of real time, not 1/3" applies `npcs_and_sem.md` §4.5's `D / L` (D = 1 s) to the 8 s warm latency. That latency was measured at load average 125–142, caused by other agent sessions sharing the dev machine, not by the game. The same lesson's own Mac mini numbers, with the game's own server and client running, give 0.23 s warm (p95 0.27 s), well under §4.5's L = 3 s.

**Consequence.** The lessons file is the stated evidence base for pushbacks to Maxim. As written, it hands §4.5 a number that the lesson's own evidence shows is not the game's load. Part (a) of the lesson, keep a model-free decision path, is well supported. The 1/8 sentence overstates.

### N1. NIT: the known-gap number disagrees with its source and points at a directory planned for deletion
**Location:** `docs/architecture.md` Known gaps ("lost 42.2 of 84.0 MJ to 14 destroyed cells")

- Commit 6e8f037 says the cells gained 41.7 of 83.96 MJ, which is 42.3 MJ lost, not 42.2.
- The measurement is not in a test or a committed probe.
- It cites `spikes/slice/`, which plan §8 deletes.

My own 4,000-tick probe (player at the spawn, vendor with no charges) gave a different burn: the pallet lit at tick 1342, not 69 s; peak 385 °C; the crate released 38.2 MJ and the pallet 42.5 MJ, still burning at tick 4000. It is not comparable, which is the point: the line cannot be reproduced from the tree. The probe also showed the air-runaway gap (`World._power_field` falling back to air) did not trigger in this burn.

### N2. NIT: no deadline for the hello frame
**Location:** `spikes/slice/slice_server/server.py::Server._accept` / `_handle`

A local process that connects and stays silent holds the single client slot indefinitely, and the real client is closed on accept. It is local only, so the impact is small. A hello deadline would close it (unverified).

### N3. NIT: the digest misses state that changes later ticks
**Location:** `spikes/slice/slice_server/sim.py::Sim.digest`

It omits `Fuel.burning_s`, which drives `power_w` through the growth term, and `vendor_state`. A divergence in either shows only ticks later, through `fuel_kg` or events, so a mismatch is reported late and harder to localise.

### N4. NIT: `main.gd` is a god script
**Location:** `spikes/slice/godot/scripts/main.gd`

432 lines in one script covering:
- connection bootstrap;
- scene construction;
- HUD and vitals text;
- input and edge detection;
- the camera;
- flames;
- the puddle;
- the vendor and its label;
- the `--demo` script and the capture.

It is throwaway, but the demo and capture and the HUD are separable concerns. The 37.0 °C in the core bar is a magic number that duplicates `body.yaml`'s start temperature.

### N5. NIT: the slice config uses `yaml.safe_load` instead of the strict loader
**Location:** `spikes/slice/slice_server/config.py::load`

`yaml.safe_load` silently keeps the last of duplicate keys. The repo's gate, `simcore.adapters.loaders.read_yaml`, refuses duplicates, and the slice could call it without a `src/` change. A duplicated tunable during week-4 tuning would be silently overridden. The check does validate unknown and missing keys.

## Checked and clean

- **No `src/`, `data/` or `client/` change** in the diff. The slice's data lives in `spikes/slice/data/`, and `core.yaml` is untouched.
- **Applier-only writes.** Every world mutation goes through `Applier.apply` (`Ignite`, `Extinguish`, `Strike`). `Ignite(power 0)` is within limits (min 0.0), and `_check_fire_fits_the_limits` checks peak power and radius at start-up. The body and the vendor's body only read `frame.solid`.
- **Determinism.** No `time`, `random` or builtin `hash` in `sim`, `fire`, `npc`, `body`, `heat_debt`, `reach`, `alley` or `intents`. Fuel and region iteration is sorted. Time comes only from `world.advance(tick_s)`, and the wall clock appears only in `server.py` (pacing, `thread_time` meters) and `voice.py`. A stop lands between ticks. `test_words_change_no_act` replays with and without `Say`.
- **The voice stays out of the simulation**, apart from S2's crash path and S3's prose:
  - `Say` is a no-op in `Sim._take`;
  - lines are sent and logged but never read back;
  - no simulation module imports `voice`;
  - Ollama is restricted to `http://127.0.0.1:`.
- **Wire security:**
  - binds `127.0.0.1` with port 0 in tests;
  - the token is compared with `hmac.compare_digest`, and the first frame must be a `slice-0` hello;
  - nothing is sent before authentication (tested);
  - frames are capped at 1 MiB, and an HTTP prefix is refused (any ASCII first four bytes also exceed the cap);
  - NaN and Infinity are refused in both directions;
  - every intent key is checked, numbers must be finite with effort in [0, 1], and `say` is capped at 200 characters;
  - outbox is capped at 8 MiB, and a second client is refused;
  - the run file is 0600, inside the worktree and gitignored.
- **Lane rules on physics:**
  - `air_mean_c` uses centre-inside weighting but is commented as a lane exception and decides no outcome; it is a read, not a deposit;
  - energy is deposited only through `World`'s volume-overlap `_power_field`;
  - the body's heat reads a 1 m reduction, not one cell;
  - the vendor's oracle sensing is flagged as off-precedent (lesson 24).
- **Body physics.** Semi-implicit Euler, the tunnelling check is enforced at construction, and the substep count is consistent with plan §3.4.
- **Client.** It only sends intents and draws snapshots. Crack changes size as well as shade, glow changes emission, and the HUD states use words before colour. Engine choices carry a one-line why (MultiMesh, CPUParticles3D, StreamPeerTCP).
- **No dependencies outside the lock.** Imports are stdlib plus numpy and pyyaml (pyyaml 6.0.3 is in `constraints/py3.12.txt`).
- **Doc edits.** D28, `foundations_plan` step 10 and the roadmap's Phase 2 bullet agree with VS5. Each is a pointer, not a second statement of a contract.
- **Main has moved.** `origin/main` is past the merge base (verify harness, one-owner rule, CLAUDE.md edits). The plan's weekly main merge is due, and the `architecture.md` Known-gaps hunk is near lines main also edited.

Probe scripts, if wanted:
- <scratchpad>/douse.py (the S1 repro)
- <scratchpad>/burn.py (the N1 burn)
