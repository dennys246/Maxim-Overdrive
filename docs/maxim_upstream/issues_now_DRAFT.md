# DRAFT for Maxim: two issues that can be filed now

Both are discrete defects, actionable now, with a definite done state (Maxim `CONTRIBUTING.md`'s test for an
issue). Both are outside the decomposition fence. Read against `origin/main` `7084f561`. Their statuses are the
roadmap's Issues now rows (O76): OD-I1 was filed by Maxim, and OD-I2 was downgraded to a docstring nit.

## OD-I1. `salience_map` turns a time of exactly 0.0 into the wall clock

- **Where:** `attention/salience_map.py` (`:227` on `7084f561`): `now = current_time or time.time()`.
- **The defect:** `0.0` is falsy, so a caller that passes a real time of `0.0` gets the wall clock instead. Any
  caller on a clock that starts at zero (a test clock, a stepped world, a replay) is silently mixed with wall time on
  its first tick.
- **Done when:** the line reads `current_time if current_time is not None else time.time()`, and a test passes
  `current_time=0.0` and asserts the result is computed at 0.0 (red before the fix).
- **Size:** a few lines. No behaviour change for any caller that passes `None` or a nonzero time.
- **Same pattern elsewhere:** the PR should grep for `_time or time.time()` and `timestamp or time.time()` and list
  any other site, fixed or not.

## OD-I2. `ModulatorResult` has no CC3 declaration

- **Where:** `embodiment/sem.py::ModulatorResult`. It is a frozen dataclass that crosses the tool boundary, and its
  docstring is one line ("Outcome of a modulator action").
- **The defect:** Maxim's `CLAUDE.md` CC3 rule says every frozen dataclass that persists or crosses a wire MUST
  declare one of two paths (`docs/agents/persistence-config.md` §3):
  - (a) defaults on all fields plus an `extra` escape hatch;
  - (b) a `SHAPE-FROZEN at 1.0 (CC3)` marker with its rejection rationale.

  `ModulatorResult` declares neither. It does not meet path (a) as it stands: five fields are required, and its free
  dict is named `metadata` with no `hash=False, compare=False`.
- **The proposed fix:** path (b). Add the marker, with `metadata` documented as the extension channel. Say which keys
  Maxim reads from it today (the bridge promotes `outcome_valence` and `measured_drive_transitions` into
  `side_effects`), and that keys a modulator invents are invisible to learning unless promoted.
- **Done when:** the docstring carries the marker and rationale, and the CC3 lint (if it covers `sem.py`) accepts it.
- **Why Overdrive cares:** the SEM refinement plan (OD-C items) adds trailing defaulted fields here. CC3 path (b) is
  what makes those additive.
