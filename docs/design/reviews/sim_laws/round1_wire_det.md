# Step 5a PR 2 (phase1/sim-laws @ 3b4c493): Wire integrity and Determinism review

Reviewer: independent, read-only. Diff: `git diff origin/main...3b4c493` (30 files). Read: `docs/code_review.md`,
`docs/design/sim_core.md` §5 to §13, `docs/plans/checklists.md` (step 5a), `docs/roadmap.md`, `boundaries.md` §6.4.

**Counts: 0 BLOCKER, 3 SHOULD-FIX, 6 NIT.**

## What I ran

- `pytest -p no:cacheprovider` on test_fields, test_laws, test_heat, test_ownership, test_simulation, test_determinism,
  test_damage, test_tooling_config: 284 passed, 1 skipped (the 0.05 m tier), 1 xfailed.
- `scripts/lint_standards.py`: PASS (21 rules held by a check, 27 by review only). `scripts/check_plan.py`: PASS.
  `lint-imports`: 10 kept, 0 broken, `laws-independent` among them.
- Break probes, in a throwaway interpreter with nothing in the tree edited:
  - dropping a field from `fields.FIELDS` makes `test_the_committed_artifact_is_the_registry_byte_for_byte` fail;
  - swapping heat and thermal damage (`run_physics.__kwdefaults__["laws"]`) makes
    `test_the_law_tuple_is_bit_identical_to_heat_with_damage_as_its_callback` fail at 0.2 m;
  - a strike that destroys nothing moves `topology_version` by 0 (this probe is the evidence for S1);
  - the artifact has no CRLF and ends in LF.

## Checks

| Check | Result |
|---|---|
| `docs/generated/fields.md` regenerated and compared byte for byte | Yes: `read_bytes() == render().encode()`, and drift fails it (verified). The regeneration command is in a test comment. LF isn't pinned (N5) |
| Registry agrees with the tuple and the laws | Yes: `LAW_NAMES` is held to `DEFAULT_LAWS`, every `law.writes` is declared, writers are listed laws first, one resolver per input |
| sim_core §5, §5.1, §6, §7 against the code | Two contract divergences (S1, S2). The other departures are named in the commit but not recorded anywhere durable (S3) |
| CLAUDE.md layout and the `World.advance` wording | Accurate about the modules. The PR that retires float time is stated three different ways (N2), and three lines overrun the wrap (N4) |
| Checklist (step 5a) | Its §5.1 item "`topology_version` rises once per strike record" contradicts the code (S1). Its §6 "LF endings" item is unguarded (N5) |
| boundaries.md §6.4 | Still has "the laws in `advance`" and no Topology row. The checklist's §13 gives that to 5a without naming a PR, so it isn't a finding against PR 2. The roadmap is stale (S3) |
| B36 restatement | CLAUDE.md links to §5.1 and doesn't restate it. `topology.py`'s docstring restates §5.1's batch definition (N6) |
| Topology request order | Deterministic: batch order is emission order, and every requester emits from a sequence that comes from its input. The docstring's "no two could race" claim is false (S2) |
| `hash()` | None added |
| Set iteration | Sets appear only in duplicate checks (`check_laws`, test_fields). None feeds an order |
| Insertion order | `fields`, `_RUN`, `_group` and `DEFAULT_LAWS` are tuples. `_WRITERS_OF` is only looked up. `World._power_field` still iterates sources in insertion order, which predates this PR and is scheduled (sim_core §7, checklist §7) |
| Float time | `grid.time_s += seconds` as before, under the existing interim. The substep loop still counts steps rather than summing floats |
| Bit identity of the new path | `test_laws` keeps a frozen copy of the pre-tuple loop and callback, compares every byte each turn, and asserts that thermal destruction happens, so the refresh path runs. Swapping the laws turns it red (verified). The arithmetic it shares with the shipped path (`heat.substep`, `_power_field`, `destroy`, `stable_dt`) is unchanged by this diff |
| PR 1's bit-identity tests | Unchanged and green. They compare `Simulation` with direct `World` calls, which now both run the tuple, so they never held pre-change identity. That rests on `test_laws` plus the by-hand comparison against f72817a in the commit. There is no golden digest, which is consistent with §12 (the first replay golden lands in PR 4) |
| Window rollback restores `topology_version` | Yes (`test_a_window_that_rolls_back_restores_the_topology_version`) |

## SHOULD-FIX

**S1. `src/simcore/core/writers.py::WriterGate._close_batch`: `topology_version` bumps once per *changing* batch, but
the contract says once per batch, and the docstring quotes a sentence that doesn't exist.**
sim_core §5.1 says "bumps `topology_version` once per batch", and §7 says it "increments once per topology batch".
The checklist's §5.1 test reads "`topology_version` rises once per strike record". The code bumps only when a batch
painted, named or destroyed something, so a strike that breaks nothing leaves the version where it was (verified: delta
0). `writers.py`'s module docstring cites §5.1 as saying "bumped once per changing batch". Grep finds that phrase only in
`writers.py`, so the quote is invented.
Failure scenario: `topology_version` is a member of §9's per-tick digest, and from PR 4 it keys the conductance and
`stable_dt` caches. Suppose PR 4's author writes the checklist test, or a second implementation (a save loader, a
replay checker), from sim_core's wording: it counts one bump per strike record, and the tick digests diverge on every
strike that destroys nothing. The code's rule is arguably the better one, since caches shouldn't miss when nothing
changed, but it is a contract change.
Fix (unverified): the owner rules. Then state the rule once, in sim_core §7, fix §5.1, the checklist item and the
docstring's quote, and add a test pinning the zero-change case on the strike path, not only on `topology.apply`.

**S2. `src/simcore/core/topology.py` module docstring and `apply`: a request's key is not defined in the contract, and
the reason given for emission order is false.**
sim_core §5.1 says Topology applies requests "in key order", but only keyed-table rows have keys. The code uses
emission order, and the commit names that as a departure. That much is deterministic: loads keep the record's order,
primitives keep the spec's or scene's order, and destroys commute.
The docstring's reason is wrong, though: "no requester in step 5a emits two that could race". `Scene.build` allows
an air primitive to overlap solids, since `_check_no_solid_overlaps` refuses only solid overlaps. `_voxelize` allows
an object's own primitives to overlap ("overlap among the object's own primitives is allowed"), with different
materials. In both cases the last `Paint` wins, so the order of the requests is the outcome.
Failure scenario: a later change makes request order canonical, for instance sorting by mask or material for
caching or batching, trusting "nothing races". Carved doorways and mixed-material imagined objects then change
silently, and a PR 4 replay of an `imagine` record diverges from the live run if the log's primitive list is ever
normalised.
Fix (unverified): in sim_core §5.1, say that an unkeyed request's key is its emission index, and that requesters emit
in their input's order. Correct the docstring, and add a test where two overlapping paints in opposite orders give
different cells, so the order is shown to be load-bearing.

**S3. Durable records: PR 2's departures exist only in the commit message, and the roadmap now contradicts the code.**
The commit lists these departures: damage is one module rather than a package; `_power_field` stays on World;
request keys are emission order; laws narrow at runtime with `as_writer` rather than through typed handles; `time_s`
isn't a registry field; `World.advance` stays. To these I'd add §5's `bound_reads`/`prepare` and the header recording
the tuple, both absent.
`src/simcore/core/simulation.py`'s docstring keeps the list "Interim departures from sim_core.md, each named with the
PR that ends it", and none of these were added to it. `docs/roadmap.md` line 51 still says "step 5a's PR 2 moves the
laws' window into the step", while `world.py`'s marker now says PR 4. The marker lint checks files, not PR numbers,
so it can't catch this.
Failure scenario: the PR 3 or PR 4 author works from the list and the roadmap, never adds the typed handles (the
checklist's "a planted law touching an undeclared field raises" is met only for writes, at runtime) or the header
tuple, and step 5a closes with the departures still in place.
Fix (unverified): add each departure, with the PR that ends it, to the simulation.py list, or to the checklist's §5
and §6 items, and correct the roadmap's PR number.

## NIT

**N1. Stale names in the docs.** `docs/code_review.md:61` gives `damage.strike` as the example of a Call contract,
and that function is gone. `docs/architecture.md:152` says "`damage.strike` refuse[s] non-finite", which is now
`law.Load.__post_init__` (reached through `physics.strike`). `docs/design/fire_solid.md:158–159` lists `damage.strike`
and `thermal_degrade`, and says "`grid.destroy` bumps `topology_version`", but the bump is per Topology batch now (see
S1).

**N2. Three answers to which PR retires float time.** CLAUDE.md's write-window rule says "until step 5a's PRs 3 and 4".
CLAUDE.md's Determinism rule says "until step 5a's PR 4". `simulation.py` says `time_s` goes in "PR 3". Pick one, or
link to the departures list.

**N3. `writers.py::WriterGate.as_writer`: `_edited` is window-wide, and a block that raises doesn't reset it.** A
law's `as_writer` block closes, and bumps for, edits made before it in the same window. A raising block leaves
`_edited` True for the next block. Neither is reachable today: grep finds no exception caught inside a window, and
imagination now validates before it opens one. Both become reachable in PR 4: sim_core §5.1 has one window serve the
apply phase, so a refused record's partial batch (paints and then a refusal) leaks a bump into the next record's
batch. Trigger: PR 4. Fix (unverified): save and restore `_edited` per `as_writer` block, and decide what a raising
batch's cell writes mean inside a window that commits.

**N4. CLAUDE.md wrapping.** Three lines overrun the file's 120-column wrap: the `topology.py` layout line, "Every write
happens inside the write window, as a writer…", and the Determinism line's Guard. This is cosmetic.

**N5. The artifact's LF endings are unguarded.** The checklist's §6 asks for LF endings. No `.gitattributes` pins
`docs/generated/fields.md`, so a `core.autocrlf=true` checkout fails the byte comparison. That fails red, which is the
safe direction, but it's spurious. Adding `docs/generated/* text eol=lf` would fix it (unverified).

**N6. `topology.py`'s docstring restates §5.1's batch definition** ("one record's apply (its stage 2 and its loads),
one law's one substep, or construction"). B36's lint covers documents only, but this is the kind of copy that went
stale in S1. Link to §5.1 instead. Related, for PR 4: `physics.resolve_loads` closes one batch per per-record *law*,
while §5.1 makes a record's stage 2 and its loads one batch. The two agree only while stage 2 emits no requests, and
`imagine` as stage 2 will.

## Not findings (checked)

- `LoadsLaw.step`'s `slated` mask: for a record with one load (every record today) it is bit-identical to the old
  `strike`. With several loads, later loads still see the slated cells as solid. `test_two_loads…` pins that, and
  it is deterministic.
- `_channel` returns a read-only view to undeclared writers, so the values are identical and only writability
  changes. Heat's `stable_dt` is still the tuple's bound, because the damage laws return infinity.
- `heat.step` reads power once and never refreshes, matching the old behaviour with no callback.
- The ownership scans, the applier's outcome scan and the world-edit scan are non-vacuous, and each has planted cases.
