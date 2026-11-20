# Second delta round, step 3b(a): Executor and Wire integrity

Range: `git diff 8c1de1e a3d7b07`. I ran it on a `git archive a3d7b07` copy with the worktree's venv and
`PYTHONPATH=<copy>/src`. The targeted modules pass on the copy: ownership, frames, constructors, sem_bridge,
act_validation, imagination, snapshot, validation and extremes (670 tests), plus `test_lint_gates.py` (97). The
mutation harness is `_durable/3b_review/delta2_mutate.py`, and every mutation below ran against those modules plus
`test_determinism.py`.

## Status of my delta findings (set from the tree)

| id | status | evidence (mutation → result) |
|---|---|---|
| S-a: two independent window locks | **fixed** | `CellStore.holding()` and `writing()` share `_refuse_a_second_owner`. Each of these turns a test red: `holding` ignoring an open grid window (`test_one_window_at_a_time_and_none_at_rest`); `writing` ignoring `holding` (`test_the_grid_window_and_the_sources_window_share_one_owner`); a sources-only window that takes no lock (same test). An ignite inside a raising grid window is now refused with `WindowClosed`, and nothing commits. |
| S-b: stale "every application publishes" claims | **fixed** (by restoring the claim rather than the texts) | A sources-only window publishes again, on the same immutable owners. Removing that `_publish()` turns `test_a_window_that_changes_only_the_sources_..._still_publishes_a_frame` red. The five texts are true again; boundaries §10 now says "copies none but still publishes". One trace remains: the frames.py module docstring still opens "published when they change", which a sources-only republish is not (NIT below). |
| S-c: applier `isinstance` untested | **fixed** | Dropping the guard turns `test_the_applier_refuses_a_region_that_is_not_a_name[region0]` red. |
| N-a: `vars()` evades the peek scan | **fixed** | Removing the `vars` branch turns `test_the_peek_scan_catches[...vars...]` red. `.__dict__` is in `PEEKS`, with a catch case. |
| N-b: `_take_cells` speedup unguarded | **fixed** | The `elif True:` (always copy) mutation turns `test_a_paint_far_from_every_region_copies_no_region_mask` red. |
| N-c: numpy scalars echoed as type names | **fixed** | Removing the `np.floating` branch turns `test_an_object_echoes_as_its_type_never_its_address` red. The integer and bool branches are covered by the new scalar test. |

## Did every test the fold added fail when its guard was removed?

Each mutation below turned the named test red:

- the five tests in the status table above (`test_the_grid_window_and_the_sources_window_share_one_owner`,
  `test_a_window_that_changes_only_the_sources_..._still_publishes_a_frame`,
  `test_the_applier_refuses_a_region_that_is_not_a_name`, `test_the_peek_scan_catches`,
  `test_a_paint_far_from_every_region_copies_no_region_mask`);
- `test_a_numpy_scalar_echoes_its_value_and_a_huge_set_echoes_its_size_without_sorting`: removing
  `_SET_SORT_LIMIT` turns it red;
- the `Frame._region` `ValueError` change: reverting to `KeyError` turns
  `test_a_reading_refuses_an_unknown_quantity_or_region` red;
- `test_size_and_mass_refusals_read_as_plain_numbers`: this one I re-proved by reading, not by mutation. It matches
  the `.2f` text, so `.3g` (`2e+03`) would fail it.

The lint tests (`CHAINED_UNSAFE`, `CHAINED_INPUT` and the tuple-assignment modulator) pass, and each asserts that a
finding exists. I did not mutate `lint_inputs._inner` (Trust's lens).

The one exception is `test_a_cylinder_scene_is_bit_identical_on_a_rerun`, which follows.

## New findings

Counts: **0 BLOCKER, 0 SHOULD-FIX, 2 NIT.**

### N-d. NIT: `tests/test_determinism.py::test_a_cylinder_scene_is_bit_identical_on_a_rerun` cannot see the change that motivated it

The comment says the box-only digests "say nothing about cylinders, whose mask now squares as `r*r`, not `r**2`".
The test compares the scene's digest with itself in one process. So it fails only if the cylinder path is
non-deterministic in-process. It cannot fail on any change to the cylinder geometry.

I mutated `Cylinder.mask` to `(self.radius_m * 1.001) ** 2`, a 0.1% larger radius, and the test stayed **green**
(2 passed). The before-and-after comparison that answers D4 lives only in the hand-off, as fold.md says. That is
honest, but it is not a check.

I also measured the risk:

- `r*r != r**2` for 1,389 of 10⁶ random radii (0.14%, matching fold.md);
- over 3,000 random radii and centres at 0.2 m and 0.1 m, **zero** cells changed side;
- the shipped scenes and data carry no cylinders.

So nothing ships wrong.

If the cylinder path should be pinned, commit the scene's digest (the value fold.md says matches fa27d5f) as a
golden beside the box digests. That turns the hand comparison into a test that a geometry change makes red. Otherwise
rename the test so it claims only in-process repeatability.

`Cylinder.volume_m3` also changed to `math.pi * r * r * h`, so `place`'s returned mass can differ from 3a0d482's in
the last bit. No consumer compares it exactly.

### N-e. NIT: `src/simcore/core/frames.py` module docstring: "published when they change"

Since S-b's fold, a frame is also published after a sources-only window, holding the same cells. The rest of the
sentence ("after each write window closes, which is after each intent application and each advance") is now exact.
Drop "when they change", or say "when they change or an intent applies".

## Wire integrity: contracts in this diff

| Contract | Before → after | Consumers | What they get |
|---|---|---|---|
| Frame cadence for a sources-only window | none → one republished frame, same owners | instruments (Maxim's post-execute read), tests | Sequence +1 per ignite or extinguish; same arrays (asserted by `is`). Matches lesson 23 and §4.2 again. |
| `CellStore.holding()` (new) and shared ownership | two locks → one owner | `World.writing(cells=False)`; nested callers now raise `WindowClosed` | No shipped path nests: `advance`, `_strike`, `_ignite`, `_extinguish`, `place` and `Scene.build` each open one window. |
| `World.writing` drops its own lock (`_sources_open`) | world lock → grid's | applier, `advance`, tests | Nested world windows are still refused (`test_the_world_window_has_one_owner_at_a_time_too` passes). |
| `Frame.reading` / `is_solid` on an unknown region: `KeyError` → `ValueError` | frames | `RegionInstrument` (validates the region at construction), `StructureModulator` (checks `region_names` first), tests | No `except KeyError` in src, scripts or tests (grep). |
| `shown` echo text | `<a float64>` → the value; a set over 1,000 → `<a set of N>` | every refusal message | Plain values unchanged. |
| `place` refusal text | `.3g` → `.2f` m, `.0f` kg | `place` callers (tests updated) | "too large: 10.00 m across"; "too heavy: 1234 kg". |
| `lint_gates._members` reads tuple assignments | — | the registry | `test_the_repository_registers_every_entry_point` still passes, so no new unregistered entries. |
