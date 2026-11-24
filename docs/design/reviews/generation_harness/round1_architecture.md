# Generation harness plan, round 1: Architecture (2026-11-22)

The reader's hand-back, condensed and saved by the author; statuses are unset until a reviewer sets them after the
fold. Reviewed `generation_harness_plan.md` at 620b7a0 (1,921 words), against:
- `pyproject.toml`'s import contracts;
- `boundaries.md` §2.1–§3;
- IG §1–§3, §5 and §8, and IP §2 and §4.1;
- `verify_harness.md` §2 and the roadmap's step 5a band-aid list;
- `imagination.py::place`, `bridge.py`, `src/maxim_overdrive/`, and the spike's code at 085c012.

**Summary:** the layer choice is defensible, but the claim that the existing contracts hold the harness is false
three ways (B1–B3). Its inference section uses the gateway's vocabulary, but its clients don't fit how the gateway is
built, so the harness would become a second host (B4). Several findings need decisions in other documents' owner
sections, which the plan doesn't name.

## BLOCKER

- **B1, §3: no import contract holds the harness.**
  - `skip-layer` applies only to `simcore.adapters` and `simcore.protocol`, so `maxim_overdrive` may import core
    internals. Adding the harness to it would forbid `imagination` and `scene`, so `place` itself.
  - The spike's files, moved "as is" (§6), import `grid.MaterialGrid`, `scene.Primitive` and `Box`, `reductions` and
    `world.World`.
  - *Fix (unverified):* state the import surface, and have H0 add a `generation-surface` contract. Either widen the
    surface deliberately, or give `imagination`, `scene` and `grid` public entry points. `boundaries.md` §2.2 owns this.
- **B2, U5 and U6: the battery can't import Maxim from the game layer.** `maxim-through-adapters` allows only
  `simcore.adapters.sem`. *Fix (unverified):* say where U5 and U6 run. Either membrane-side check functions owned by
  `boundaries.md` §8.1 and `npcs_and_sem.md`, or a test-only battery whose consumers read verdict files.
- **B3, U2 and U3 duplicate `simcore.verify`, which `verify-ships-nowhere` forbids the game to import.** Two owners of
  the resolution rule's comparison would drift apart. *Fix:* run U2 and U3 as tests over `simcore.verify`, or have
  `verify_harness.md` §2's owner decide.
- **B4, §4: there is no host-side client for a batch job.** IG's adapter is spawned, and spawning, dispatch, slots,
  retries, the kill and stamping all live in the engine host. Its contract is session-shaped: speakers' consent,
  thought budgets and `thought_failed` reasons. *Failure:* the harness writes its own channel client, a second
  implementation of IP §2.5–§2.7. *Fix (unverified):* IP and IG gain a "batch caller" contract (eligibility without
  speakers, the deadline source, a host-less dispatch API), and the plan links to it.

## SHOULD-FIX

- **S1, §4:** "a batch job declares its envelope" restates and alters IP §2.1, where envelopes are per function in
  the shipped `functions.yaml`. Fix: add batch functions there, so a job only names a function.
- **S2, §4:** a job can't set `max_in_flight`, since it only picks a placement. That field caps the client, not the
  server's slots. Fix: a job selects a placement id, and the server-slot proof goes in the engine proof.
- **S3, §4 and §6: the engine proof has no channel.** Only the gateway can read `/props`, and IG §3's `ready` frame
  carries no build, context, slots or measured digest. Fix: widen Q3 so that IG §3 and IP §2.2 gain the engine proof.
- **S4, §4:** making `exceed_context_size_error` an IG §5 row would change every NPC's agent-facing outcome. Fix
  (verified by reading both): leave IG §5 alone, and give the harness one versioned outcome-to-record mapping.
- **S5, §3 and §6:** the record, header, job and verdict formats have no owner; this is a plan, and B32 puts contracts
  in a design. Fix: H0 writes `docs/design/generation_harness.md`, owning them, with IP §4.1's provenance by
  reference.
- **S6, U1 and U9:** `place(grid, …)` is a listed step 5a band-aid. U1 through `place` and U9 through `imagine` would
  exercise different paths. Fix: U1 goes through `imagine` once 5a lands.
- **S7, Q1:** "a tools package would sit outside the import contracts" is false, since a third root joins `layers`.
  The cost of the recommendation is also unstated: the wheel ships all of `maxim_overdrive`, so players would get the
  bootstraps, labelling and the batch CLI.

## NIT

- **N1, U7:** Godot runs only at `ALLOWED_SPAWNS` sites in `tests/` and `scripts/`.
- **N2:** IG §2's log lives in a session directory that O26's purge deletes; name the batch log's home.
- **N3:** U2, U4, U10 and §6 link to unmerged documents (#51, torch-pilot); list them as H0's dependencies.
- **N4, Q2:** "wait for the gateway" means waiting for Phase 4's transports, which the roadmap puts after mid-2027.

## Checked, nothing found

- the layer choice: the game, not the core and not `scripts/`;
- not Maxim's experiment harness, and nothing on Maxim's ledger;
- only `place` writes;
- Q2's marked band-aid;
- Q3 sent to its owner;
- clean separation of runner, protocol, scoring and labelling;
- H4 names a real consumer;
- the spike stays frozen.
