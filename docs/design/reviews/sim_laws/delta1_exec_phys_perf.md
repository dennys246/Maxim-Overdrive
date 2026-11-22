# Step 5a PR 2, delta round 1: Executor, Physics and Performance

Reviewer: independent, read-only. Tree: the staged fold on 3b4c493 (`git checkout-index` into
`_durable/sim_laws_review/delta1_epp/fold`); f72817a extracted to `delta1_epp/base`; 3b4c493 from round 1's
`exec_work/head` and `perf/head`. Plants went into `delta1_epp/plant`, a copy of the fold. Scripts are in
`delta1_epp/scripts/`. The worktree's own suite passes: 2744 passed, 22 skipped, 6 xfailed.

**Counts: 0 BLOCKER, 2 SHOULD-FIX, 3 NIT.**

## Status of my lenses' round-1 findings

| Finding | Status | Evidence |
|---|---|---|
| Exec SF1, self-asserted identity | **open (partly fixed)** | G3, G4, a string writer, a token made by hand, a second `claim`, nesting and construction after a run are all refused at runtime (`probes2.py`). But `physics.run_law` turns `law.name` back into a token for any caller: see D1 |
| Exec SF2, handles outlive the block; views unlockable | **open (partly fixed)** | Revocation works: a handle kept from heat's block and written in thermal's block and after both lands nowhere (P4). `flags.writeable = True` is refused (P5). `view.base.obj` still unlocks `material`: see D2 |
| Exec NIT 3, `_edited` leaks | fixed | `CellStore.as_writer` resets it at block entry and in `finally` |
| Exec NIT 4, contract test collapses two laws | fixed | `damage/loads.py` and `damage/thermal.py`; the test asserts one module per law |
| Exec NIT 5, replan trigger and batch boundary | **open (half)** | The §5 sentence is fixed. The per-record batch-boundary deferral to PR 4 exists only in `fold.md`: no checklist row and no marker (grep of `docs/plans`, `roadmap.md`, `standards_backlog.md`, `src`). A deferral needs a tracked trigger |
| Exec NIT 6, the reference shares code | fixed | `tests/test_laws.py` docstring, line 5 |
| Perf P1, every mask held at once | **fixed, verified** | tracemalloc, 1.536×10⁶ cells: 400 unnamed boxes, base 61.6 / 3b4c493 647.6 / fold 61.6 MB; 400 named, 1233.8 / 1819.9 / 1233.8 MB; 32-primitive `imagine`, 48.4 / 93.8 / 46.9 MB |
| Perf P2, per-load passes | fixed (the allocation); the rest rejected | `slated` is made only from the second load on. The kept `gone.sum()` now carries Arch N1's cross-check against Topology's count, which is reason enough. The `solid` recompute is one pass per load: NIT-sized |
| Perf P3, gate overhead | deferred to B5 (trigger: 5a's bar 7 or B5's regression gate) | Measured below. Acceptable now. The fold table describes its scaling wrongly: see D3 |
| Perf P4, `check_laws` on every call | fixed | `check_laws(DEFAULT_LAWS)` runs at import, and `_group` skips the default tuple |

## Writer identity as tokens (question 2)

Refused at runtime (`probes2.py`): a string or hand-made token, a second `claim`, thermal writing `material`,
calling `topology.apply` (nesting) or `destroy`, construction after a run, an undeclared read, `time_s` in a block.
Two holes remain.

### SHOULD-FIX D1: `src/simcore/core/physics.py::run_law`: the token comes from `law.name`, so any code can write as any law

`run_law` narrows to `_TOKENS.get(law.name)`. Neither `check_laws` nor any scan ties the law object to the
registered one. Plant P2 put this in `simulation.py`, which is not a law:

```python
class _Imposter:
    name = "damage.thermal"; reads = (); writes = ()
    def step(self, grid, dt_s, inputs):
        grid.integrity[...] = 0.5
        return Changes()
...
physics.run_law(grid, _Imposter(), 0.0, LawInputs())
```

Every B43 guard module (`test_ownership`, `test_laws`, `test_fields`, `test_determinism`, `test_tooling_config`)
stays green; at runtime the impostor's integrity write committed (`probes.py` P2).

A fake law with `reads=None` also gets Topology's "read anything", and a fake tuple through `run_physics(laws=...)`
works too (`check_laws` checks names and writes, not identity). `OWNED_CALLS` doesn't list `run_law`. This is round
1's SF1 respelled: identity is a string again for any `src/` caller (only `applier.py`'s own scan would see it).

**Failure scenario.** A PR 3 or PR 4 fix in `simulation.py` or `world.py` needs to write integrity or temperature,
and calls `run_law` with a small adapter named after the law. It lands green, and the flow rule and B43 stop meaning
anything there.

**Fix (unverified):**
- make it `_run_law`, and add it (and `run_physics` and `resolve_loads` called with `laws=`) to `OWNED_CALLS`, owned
  by `physics.py`, so a test helper is the only other caller;
- or grant a token only when `law is` the registered instance (a name-to-law map built from `DEFAULT_LAWS`), so a
  test law gets `None`;
- either way, refuse `reads=None` from a law.

### SHOULD-FIX D2: `src/simcore/core/grid.py::CellStore._channel`: a read-only view unlocks through `.base.obj`

`np.asarray(memoryview(arr).toreadonly())` has a `memoryview` as its `.base`. `memoryview.obj` is the window's own
writable array. Plant P1 put `grid.material.base.obj[0, 0, 0] = 0` in `heat.substep`: it committed, `topology_version` didn't
move, and no guard went red (only physics tests, as side effects). The fold's claims "a read-only view's memory
is a read-only buffer, so it can't be unlocked" (`fold.md`) and "a view that can't be made writable" (the
`CellStore` docstring) are false as written.

No honest mistake reaches `.base.obj`, but the fold claims the route closed, and it bypasses Topology's version.

**Fix (unverified):** either say plainly in `writers.py`, the docstring and the B43 row that the gate catches mistakes,
not deliberate `.base` walks, or add `.obj` and `.base` on grid arrays to the core scan. Hiding the exporter needs a
copy, `readonly.frozen`'s O(cells), and that would need a profile first.

### NIT D4: private reach has a free check the fold doesn't use

The fold names "code that reaches into private names" as the residual. Three examples:
- `grid._channels["material"][...] = 0` from a law writes `material` with no version bump (P3);
- `writers._claimed["topology"]` hands any code Topology's token (P6);
- `topology._TOPOLOGY`.

Ruff's `SLF001` flags all three (verified on the plant copy). `ruff check --select SLF001 src scripts` passes on the
fold today with zero findings, so selecting it for `src/` and `scripts/` (tests exempt) costs nothing and closes most
of the residual. Unverified across the whole gate.

## Bit-identity against f72817a (question 3)

**It holds.** One script ran against each tree's own `src/`, with `simcore.__file__` asserted. Every digest is
byte-identical between f72817a and the fold:

- the determinism scenario at 0.2 and 0.1 m (`f7429cba…`, `e9e57122…`);
- a 120-turn fire-only burn at 0.2 m, with the hash of every turn's substep count;
- four strikes in a row at 0.2 and 0.1 m, with the volumes and `absorbed_j` equal to the last bit;
- `place` then 10 turns of fire at 0.2 and 0.1 m (`8904f715…`, `e5927ebe…`).

The tightening replan with power (k = 3, 7, 10: 456, 1156 and 1685 substeps) matches base `heat.step` with its callback
byte for byte (`replan_base.txt` = `replan_fold.txt`). The fold's `heat.step` removal therefore changed nothing.

## The overhead (question 4)

Min-of-N at load 5–6 (an earlier pass at load 12–35 showed a spurious 2.5×; discarded).

| Measure | 3b4c493 | fold |
|---|---|---|
| Enter a heat block, read `material` and `temperature`, exit (27 / 27k / 512k cells) | 1.4 / 1.5 / 2.0 µs | 3.5 / 7.4 / 61.7 µs |
| Heat substep inside its block (27 / 27k / 512k) | 33.1–33.6 / 533–539 / 9332–9432 µs | 35.1–37.2 / 540–546 / 9418–9494 µs |
| Revocation copy alone, paired in-process (heat block / whole tuple substep), 512k cells | — | +21 µs / +170 µs (0.2% / 0.8%) |
| The same, 4.1×10⁶ cells | — | +1.5 ms / +3.7 ms (1.9% / 2.0%) |
| `World.advance`, determinism scenario, 0.2 m (min of 3 processes) | 1.021 ms (base 0.980) | 1.014 ms |
| `World.advance`, 0.1 m | 9.767 ms (base 9.683) | 9.620 ms |

Real but small: ~2 µs fixed per block, plus one copy per written field per block (~2.3 ns/cell, float64): heat's
`temperature` every substep, thermal's `integrity` when something is hot. At turn level the fold, 3b4c493 and base are
within 4% and within noise. Acceptable for PR 2.

### NIT D3: `docs/design/reviews/sim_laws/fold.md` (Perf P3 row): the cost is O(cells), not fixed µs

Not reproduced: the row's 14–30 vs 5–18 µs per law and 1.24 → 1.38 ms turns (I get +2–4 µs per block, no turn
change). More importantly, revocation is a full-field copy per writing block per substep. Round 1 recorded "nothing new is O(cells) per
substep", and that is no longer true. At the max profile it is about 2% of a substep, which counts against bar 7
("no worse than today's `advance(6.0)`").

**Fix:** restate the row as "~2 µs per block plus one copy of each written field per block (~2% at 4×10⁶ cells)", and
name per-block lease reuse (or skipping revocation for the orchestrator's own laws) as the B5 lever.

## Lazy construction (question 5)

The memory claims are **true**, measured independently; the table above has the numbers. The construction and
`imagine` peaks are back at base, and the named floor is the region table's own masks, as the fold says.

The in-window refusal works: a 32-primitive object whose last primitive hits an unnamed solid is refused
`space_taken` at a 27.9 MB peak (= base), with `material`, regions and `topology_version` unchanged after rollback.

## New findings, summary

| ID | Severity | Site | Fix verified? |
|---|---|---|---|
| D1 | SHOULD-FIX | `physics.py::run_law` (token by `law.name`) | unverified |
| D2 | SHOULD-FIX | `grid.py::CellStore._channel` (`.base.obj` unlock; false claim) | unverified |
| D3 | NIT | `fold.md` Perf P3 row (O(cells) copy, numbers not reproduced) | n/a |
| D4 | NIT | `pyproject.toml` ruff select (SLF001 free, catches P3, P6, `_TOPOLOGY`) | check fires: verified; gate: unverified |
| NIT 5 remainder | NIT | `docs/plans/checklists.md` (PR 4 batch-boundary row missing) | n/a |
