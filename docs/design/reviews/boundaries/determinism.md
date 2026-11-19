# Determinism and replay lens: boundaries.md (draft, at 47add00)

Reader: Determinism and replay. Date: 2026-11-16. Counts: **4 BLOCKER, 9 SHOULD-FIX, 5 NIT.**

Inputs: CLAUDE.md, `docs/code_review.md` (the Determinism and replay lens, "Design reviews"), the design (B-3, B-8,
B-9, B-10 in depth; the enforcement table and migration), `world_model.md` §6 and §10. Checked against code in
`.worktrees/act-validation` at 2f200b5: `tests/test_determinism.py` (`run`, `digest`, the hash-seed subprocess test,
`findings`, `scanned_files`, `NOT_SIMULATION`, `PACKAGE`), `world/world.py` (`World.from_scene`, `_power_field`,
`advance`, `snapshot`), `world/grid.py` (`Region`, `MaterialGrid.paint`, `destroy`), `world/damage.py` (scipy
imports), `config.py` (`pathlib`, `yaml`, `MaterialTable.load`, `ActionLimits.load`), `sem_env/bridge.py`
(`RegionSensor`, `StructureModulator.execute/apply/_strike/_ignite`, `_is_this_region`), `imagination/spec.py`, and
the installed pymaxim 1.3.3 (`maxim/embodiment/sem.py`). Probes run in the main `.venv` (numpy 2.5.4, Python 3.14);
import-linter is not installed there, so the statements below about its semantics should be checked against the
version the gate will pin.

Summary: an import contract is a cheap, useful tripwire against the obvious mistake (`import time` in a physics
module), and it should land. But as written, B-3 seals the package that does not write the world, names one entry
import-linter cannot express, and treats imports as the leak when the measured hazards in this codebase are not
imports: a data file read from disk on every world construction, decisions made by object identity, live sensors
holding the whole `World`, and arrival-order float sums. B-9 promises one log without saying what goes in it, and
today's door cannot be logged. B-10's mechanism, as specified, is defeated by one line of user code, and its test
cannot fail on that line.

---

## BLOCKER

### D-B1. B-3 seals the wrong boundary: the code that writes cells is outside the core

`boundaries.md::B-3` (core = `maxim_world.world`), `sem_env/bridge.py::StructureModulator._strike`,
`::StructureModulator._ignite`, `imagination/spec.py::place`

The core is defined as `maxim_world.world` "today". The writes that change the world on the shipped path today are
`damage.strike(...)` called from `bridge.StructureModulator._strike`, `self._world.sources[...] = source` in
`_ignite`, `sources.pop` in `apply`, and `imagination.spec.place`. All of them live outside the core, and
`sem_env` imports `maxim`, whose own `maxim/embodiment/sem.py:1560` does `self.last_fired = time.time()` (a
failure-mode trigger on an Entity). B-8 puts `sem_env` above `world.world`, so every contract stays green while
`sem_env` mutates the world.

Failure scenario: during sim-clock, someone adds "a fire set less than 2 s ago can't be re-lit" to `_ignite` using
`time.monotonic()`, or evaluates Maxim failure modes on environment Entities from the sim lane. The B-3 contract is
green, because `sem_env` isn't the core. The B-8 layers contract is green, because sem_env may import world. Only the
AST scan catches the first case, and only while its scope stays wider than "the core" (see S6). The second case
(`time.time()` inside Maxim, reached through sem_env) is caught by nothing static. Replays diverge with the wall
clock.

Fix: define the core by what runs on the simulation lane, as an explicit module list, not as a package name.
That list is the grid, the laws, the turn loop and simulation, and **the intent applier**. Split
`StructureModulator` now, not at sim-clock: the gate half (`parse_action`, target checks) stays in `sem_env`, and
the write half (`apply`, `_strike`, `_ignite`, extinguish) moves into the core as the applier of typed intents. Do
the same for `place`. Add a non-vacuity test: every function that assigns into a grid array, `regions` or
`sources` is defined in a module on the core list. Otherwise the contract guards an empty room.

### D-B2. The core reads an unrecorded input from disk: the material table and action limits

`world/world.py::World.from_scene` (`materials = materials or MaterialTable.load()`), `config.py::MaterialTable.load`,
`config.py::ActionLimits.load`, `boundaries.md::B-3`

"The intent log plus the scene and rig reproduce any session" (CLAUDE.md) is false today and B-3 doesn't fix it.
`World.from_scene` loads `data/materials/core.yaml` through `pathlib` and `yaml` when no table is passed, and every
test and caller relies on that default. The limits file decides which intents are refused, and a refusal is part of
what a replay must reproduce. Neither file is named by "scene and rig", and none of `pathlib`, `io`, `yaml`, `open`
is on B-3's list.

Failure scenario: material table v1 retunes `degrade_rate` for wood. Every committed replay and golden intent log
now diverges, because the crate loses cells a turn earlier. Nothing in the log says which table it was recorded
under, so the divergence reads as a physics regression and someone regenerates the goldens. Same failure if
`max_power_w` changes: an ignite that was accepted is now refused on replay, and the world forks at that tick.

Fix: the core does no file IO. Loaders are gates (B-4) above the core. The core receives frozen, loaded tables as
required keyword-only parameters, with no `MaterialTable.load()` default. Forbid `pathlib`, `io`, `yaml` and
`importlib` in the core contract, and `open(` in the AST scan. The log header (B-9) records a content digest of the
scene, the rig, the material table and the action limits, and a replay refuses a header it can't match, loudly
(the versioned-format rule).

### D-B3. B-9's log has no defined record, and today's door can't be logged

`boundaries.md::B-9`, `sem_env/bridge.py::StructureModulator._is_this_region`, `::StructureModulator.execute`

B-9 says "the same intent log records both" but never says what an intent record is, what goes in the log and what
doesn't. Today's door takes live objects. Maxim's orchestrator passes `target=<Entity>`, and `_is_this_region`
decides by object identity (`target.modulators.get("structure") is self`). A log of the params can't serialize an
Entity. A replay has no Entity to compare by `is`, so the accept-or-refuse decision can't be replayed. `execute` is
also synchronous: Maxim expects a `ModulatorResult` carrying `destroyed_volume_m3` now, but an intent applied at the
next tick can't return that.

Failure scenario: sim-clock logs `(affordance, params)` as `execute` receives them. The `target` key holds an
Entity, which is pickled, `repr`'d with a memory address, or dropped. On replay a namesake refusal ("another thing
called crate") either can't be evaluated or evaluates differently. The replayed world strikes the crate where the
live world refused, and every later tick differs.

Fix (in this design, before sim-clock builds the log), define:
- **The intent record:** frozen; schema version; actor id; sequence number per actor; the tick it was applied;
  the tick of the observation it was based on (S5); affordance; **typed, canonical params** (after `parse_action`);
  and the target as a **stable id** (a region name or a persisted entity id). Entity-to-id resolution, and the
  namesake and identity checks, happen at the door **before** logging. Nothing identity-based crosses into the log.
- **Input vs derived:** the log holds inputs only. That is every intent, refused ones included, since a refusal at
  apply time depends on world state, plus host commands (D-S7). An NPC's thought (prompt, LLM output, tool-call
  text) is never a log input: the only thing a thought contributes to the world is the intent it produced, and that
  is logged. Results (`ModulatorResult`, refusal reasons, destroyed volume) are derived. Replay recomputes them and
  compares them against a per-tick digest stored as a check, never as an input.
- **Replay never calls anything live:** no model, no Maxim, no clock. That follows from the above, and should be
  stated as a rule with a test (a replay run with `maxim` blocked from import).
- **`execute`'s synchronous contract** is a Maxim decision this design runs into. Under the push-back rule it is a
  Phase 3 item (Maxim's modulator returns an acceptance now and delivers the outcome later), not a local
  workaround.

### D-B4. B-10's read-only views are defeated by one line, and the proposed test can't fail on it

`boundaries.md::B-10`, `sem_env/bridge.py::RegionSensor.__init__` (`self._world = world`), `world/grid.py::Region`,
`world/world.py::snapshot`

Measured (numpy 2.5.4): for `v = a.view(); v.flags.writeable = False`:
- `v[0] = 1` raises, so the test B-10 proposes ("writing to a view raises") passes;
- `v.flags.writeable = True; v[1] = 7` succeeds and writes `a`;
- `v.base[0] = 5` succeeds.

Only a read-only **owner** blocks re-enabling the flag ("cannot set WRITEABLE flag to True of this array" for a view
of a read-only owner). `np.asarray` returns the same read-only object, which is fine; `np.array` copies, which is
harmless.

Two further holes:
- **The arrays are not the surface.** `RegionSensor` holds the whole `World`, so a sensor can call
  `self._world.advance()`, assign to `self._world.sources`, or write `grid.regions[r].cells[...]`. `Region` is a frozen
  dataclass, but its `cells` mask is a mutable array, and `paint` writes into it with
  `np.logical_and(..., out=other.cells)`.
- **The design targets the snapshot,** which already copies: `material.copy()`, and `astype` for the rest. So the
  part B-10 names as the work is already safe, and the parts that aren't safe go unnamed.

Failure scenario: a sensor "normalises" a reading with `t = view; t.flags.writeable = True; t -= offset`, or a Maxim
cradle helper calls `sensor._world.advance()` to "peek ahead". The B-10 test is green. The world moved outside
`World.advance`, unlogged, and the replay diverges.

Fix:
- Make the grid's arrays read-only **at the owner**, and give the simulation lane a write context (`with
  grid.writing():`) that is entered only inside `advance` and the intent applier. This gives B-9 its guard for free:
  "every cell write happens under advance or intent application" becomes "a write anywhere else raises", tested by
  running the full golden scenario.
- Store `regions` and `sources` behind `MappingProxyType`, with region masks read-only.
- Type sensors against an `Observation` protocol with no `advance`, `sources` or `grid` attribute, so mypy refuses the
  peek (the "push invariants into types" rule).
- The test must enumerate the outward surfaces and try each of: write, re-enable the flag, write through `.base`,
  `out=` into a ufunc, and attribute assignment.

ctypes and `np.ndarray(buffer=...)` tricks stay possible: this guards mistakes, not adversaries, and the design
should say so.

---

## SHOULD-FIX

### D-S1. The `sys.setprofile` tripwire can't see the case B-3 cites

`boundaries.md::B-3` ("such as an unseeded `random.Random` built inside Maxim"), `world_model.md` §6

`sys.setprofile` delivers a `c_call` event with the C function object, **not its arguments**. `random.Random()` with
no seed goes through Python `Random.seed(a=None)` into the C `_random.Random.seed`, which reads OS entropy inside C
with no Python-visible `os.urandom` call. The hook therefore sees a `seed` call it can't tell apart from
`seed(1234)`, unless it inspects the calling frame's `a` local in `random.Random.seed`. It also only fires on paths a
test exercises, and only on the thread it's installed on (Python 3.10, which CI runs, has no
`threading.setprofile_all_threads`). Comparing the global numpy and stdlib RNG states before and after doesn't catch
a private `Generator` or a private `Random`.

Failure scenario: a tripwire built from the prose flags every `seed` (false alarms, so it's narrowed), or flags
none (silent). An unseeded `random.Random()` inside a Maxim helper on the sim lane picks different tie-breaks per
run, and the tripwire is green.

Fix: name the tripwire as a check, with an explicit denylist covering `time.time`, `time_ns`, `monotonic`,
`perf_counter`, `process_time`, `datetime.now`, `utcnow`, `today`, `date.today`, `os.urandom`, `os.getrandom`,
`uuid1`, `uuid4`, `secrets.*`, `SystemRandom`, `os.getpid`, `os.environ` access, `threading.get_ident`,
`Random.seed` with `a is None` (via the frame), and `SeedSequence` with no entropy. Prove it with one planted call
per entry. Run it over the golden replay corpus, so its reach grows with the corpus.

### D-S2. The forbidden list doesn't map onto import-linter as written

`boundaries.md::B-3` (the list), the enforcement table row for B-3

- `os.urandom` is a function, not a module. `from os import urandom` is an import of `os`. Either forbid `os`
  outright (the core needs none of it), or drop the entry and leave `os.urandom` to the AST scan. As written, an
  implementer will either quietly drop it or invent a workaround.
- Stdlib and third-party targets need `include_external_packages`, and external packages are squashed: their
  internals aren't traced. That's fine for `numpy` importing `threading`, but it means the contract can't see what
  `maxim` or `pathlib` reach. Check, against the pinned version, whether external forbidden modules may be
  subpackages at all.
- The host, transport and thinking lane don't exist yet. A forbidden contract over a module that doesn't exist is
  either a config error or vacuously green, depending on version. Either way, each entry needs its own
  planted-import proof when its module is born.
- `importlib.import_module("time")`, `__import__` and `exec` bypass both import-linter and the import half of the AST
  scan.
- Missing from the list: `sys`, `pathlib`, `io`, `yaml`, `importlib`, `gc`, `weakref` (finalizer timing),
  `signal`, `multiprocessing`, `concurrent`, `subprocess`, `platform`, `locale`.
- Say explicitly that `hashlib`, `math`, `dataclasses` and `logging` (output-only) are allowed, so nobody bans the
  stable hash.

### D-S3. The leaks that aren't imports have no guard named

`boundaries.md::B-3` ("the AST scan stays for calls and names imports can't show")

The scan today catches the RNG, the clock and `hash()`. Not caught:
- **`id()`:** `_target_label` avoids memory addresses by attention.
- **Iteration over a `set` or `frozenset` of strings:** the hash-seed subprocess test catches this only on the
  exercised path.
- **Unstable sorts:** `sorted`, `np.sort` and `np.argsort` with ties under the default `kind`. numpy 2 dispatches
  SIMD sort kernels by CPU, so tie order is not promised across machines or versions. `world_model.md` §6's "sorted
  order" needs `kind="stable"` and integer keys.
- **BLAS reductions:** `@`, `np.dot`, `linalg`, `einsum(optimize=...)`. Threaded OpenBLAS and Accelerate split
  reductions by thread count, so results move with `OPENBLAS_NUM_THREADS`. None exist today; a sparse heat solver
  would bring them.
- **Global floating-point state:** `np.seterr` and `errstate` set by a library change whether a step raises.
- **`os.environ` and `getenv` reads.**

Failure scenario: zones add a `set()` of gap ids iterated to assemble face counts in float. The hash-seed test
doesn't exercise zones yet. Replays across processes differ.

Fix: extend the AST scan for the core (`id(`, unstable `sort`/`argsort`, BLAS calls, `seterr`, `getenv`, `open(`,
`importlib`, `__import__`, `exec`, `eval`). Either forbid BLAS in the core or pin its threads to 1 on the sim lane
(threadpoolctl), and say which.

### D-S4. The replay promise needs an environment header, or a numpy bump breaks the goldens silently

`boundaries.md::B-9`, `world_model.md` §6 (the save's derived-state check)

Same machine, bit-identical is the promise. A numpy, scipy or Python upgrade on the same machine changes pairwise
summation blocking, SIMD transcendental kernels (`scipy.special.ndtr` in `damage.py`) and sort dispatch.
`NPY_DISABLE_CPU_FEATURES` changes them on the same binary.

Failure scenario: the dependency bot bumps numpy from 2.5 to 2.6. Every committed golden replay turns red with no
code change. The path of least resistance is regenerating the goldens, which destroys the regression value of the
whole corpus.

Fix: the log and save header record Python, numpy and scipy versions, `platform.machine()`, the numpy CPU dispatch
features and the BLAS thread count. A replay with a matching header must be bit-identical. A replay with a
different header is checked for outcome class, like the rig rule. Write down the policy for regenerating goldens.

### D-S5. Observation reads live state: NPC perception depends on scheduling

`sem_env/bridge.py::RegionSensor.value`, `boundaries.md::B-10`

When the thinking lane reads sensors while the sim lane is inside `heat.step`, it sees a half-advanced
temperature field. Replay stays exact, because the resulting intent is logged. But a cradle rerun with a
deterministic (mocked or cached) model is not reproducible, and nobody can reconstruct what the NPC saw from the
log.

Two further requirements:
- Observation must never draw from the World's `Generator`. A noisy sensor that consumes the sim stream makes the
  physics depend on how often an NPC looked.
- Sensor noise, when it comes, uses a counter-based stream keyed by (seed, tick, sensor id).

Fix: observation reads a per-tick published immutable frame, and every intent records `observed_tick`. This belongs
in B-10, and is the concurrency half of D-B4.

### D-S6. The AST scan can go vacuous in the rename, or shrink to "the core"

`tests/test_determinism.py::PACKAGE` (`ROOT / "src" / "maxim_overdrive"`), `::NOT_SIMULATION`, `boundaries.md`
Migration

The rename is "mechanical" on imports, but `PACKAGE` is a path string. If it survives, the scan reads the new,
empty `maxim_overdrive` game package and passes with zero findings over zero engine files. B-3's wording ("the AST
scan stays for calls and names imports can't show"), next to a narrower "core", invites shrinking the scan to the
core, which drops `sem_env` (D-B1).

Fix:
- The scan covers both packages minus an explicit non-simulation allowlist (host and transport), as
  `NOT_SIMULATION` does today.
- Assert non-vacuity: the file defining `World.advance` and the intent applier are among the scanned files, and the
  count is at least a floor.

### D-S7. "One log for every actor" must be one log for every input

`boundaries.md::B-9`

Players and NPCs aren't the only inputs. Others are: `World.advance(seconds)` with a free float argument, the time
dial, pause, rig selection, save and load, imagination's `place`, and the admin or editor `set_material` from §10.
Any of them that the host derives from wall-clock latency has to be logged.

Failure scenario: the host advances by `seconds=elapsed_wall` when it falls behind. The log holds intents only, and
the replay advances fixed turns. It diverges at the first stall.

Fix: the log records every input to the Simulation, host commands included. The integer clock (sim-clock) makes
`advance` take ticks, never seconds from outside.

### D-S8. Same-tick ordering of many actors must be canonical, or arrival order is the outcome

`world/world.py::World._power_field` (sums `self.sources.values()` in insertion order), `boundaries.md::B-9`

Two NPCs ignite two regions in the same tick. In the live run, NPC B's thought lands first, so `sources` is
`{B, A}`, and the float power sum differs in the last bit from a run where A's thought landed first. Replay from the
log is exact, but "the same scene, rig and intents give bit-identical state, whatever the thread scheduling" (the
charter's question) is false.

Fix: B-9 states the application order: sort same-tick intents by (tick, actor id, per-actor seq), never by arrival.
Order-dependent float accumulations over named collections iterate in sorted-key order.

### D-S9. Log the typed canonical intent, not the raw payload, and say so

`boundaries.md::B-9`, `sem_env/bridge.py::parse_action`

If the log holds the raw LLM or client payload, a replay re-runs `parse_action`. Any later tightening of the gate
(PR 1 tightened it six times) then changes old replays: an intent accepted then is refused now. If it holds the
typed intent, replay skips the gate, which is correct: the gate already ran.

Fix:
- Log the canonical typed intent, versioned, and keep the raw payload only as an optional audit field.
- Golden fixtures for the record format (the round-trip-plus-goldens rule).

---

## NIT

### D-N1. The survey omits what the core actually depends on

`boundaries.md` "Why now"

"No module under `src/` imports `time`, `random`, `datetime`, `uuid` or `os`" is true. But the core reaches
`pathlib` and `yaml` (`config.py`, file IO) and `scipy` (`damage.py`: `ndimage`, `special.ndtr`). Those are the
dependencies that bear on determinism, and the survey should list them.

### D-N2. Ordering keys "in metres" should be integers

`world_model.md` §6 (S-4: "an ordering key in metres")

A float key admits NaN (which breaks `sorted`'s total order, so the result depends on input order), and `-0.0`
compares equal to `0.0`. Use quantized integers (millimetres, or cell indices at the finest rig).

### D-N3. The tripwire is a test, not a runtime seal

`boundaries.md::B-3`

A setprofile hook costs several times the runtime, so it can't run on the shipped path. Say that it guards only
what the replay corpus exercises, so that "sealed" isn't read as a runtime property.

### D-N4. Determinism tests should be driven by the golden log, by kind

`tests/test_determinism.py::run`

`run()` covers ignite, strike and degradation. As intent kinds and laws arrive, drive the bit-identity, hash-seed
and tripwire tests from the golden intent log, with an assertion that every intent kind and every host command
appears in it. Otherwise new paths are born unguarded.

### D-N5. B-8 is import direction, not write permission

`boundaries.md::B-8`

The layers contract lets layer 6 (`sem_env`) import and mutate layer 5. Say in B-8 that write permission is enforced
by D-B4's owner-level read-only arrays, not by the layers, so nobody cites B-8 as B-9's guard.

---

## Tests that prove each guard can fail (plant, watch red, remove)

| Guard | Plant |
|---|---|
| B-3 contract, per entry | `import time`, `import os`, `import pathlib`, `import yaml`, `import maxim`, `import threading` in one core module each (and a transitive one: a core module imports a helper that imports `time`) |
| B-3 contract non-vacuity | move the intent applier out of the core list: the "every writer is on the core list" test goes red |
| AST scan | `id(x)`, `sorted(s)` over a set, `np.argsort(a)` (no `kind`), `importlib.import_module("time")`, `open(p)`, `os.getenv("X")`, `a @ b` in a core file; the scan's non-vacuity floor, by pointing `PACKAGE` at the empty game package |
| Tripwire | each denylist entry called from inside `advance` on the sim thread, including `random.Random()` (unseeded) vs `random.Random(1)` (must stay green) |
| D-B2 hidden input | change one `degrade_*` value in a temporary material table: the replay refuses on header mismatch, not on a digest diff at turn 17 |
| B-9 record | a logged intent whose target came from an Entity round-trips through the log, and the replay reproduces the namesake refusal with `maxim` blocked from import |
| B-9 ordering | the same two ignites submitted in both arrival orders give bit-identical digests |
| B-9 one door | a sensor that writes `grid.temperature[0, 0, 0] += 1` during a scenario raises (owner read-only, outside `grid.writing()`) |
| B-10 | for every outward surface: direct write, `flags.writeable = True` then write, write through `.base`, ufunc `out=`, attribute assignment on the observation; each must raise |
| D-S4 header | the same log replayed with a patched numpy version string is checked for outcome class only, and says so |
| D-S5 | a sensor read from a second thread mid-step returns the published frame for `tick - 1`, never a mix |
