# Future flexibility: external dependencies (2026-11-18)

One of three independent flexibility reviews. Scope: Maxim, Godot, Python/numpy/scipy/BLAS, and pyproject, lockfile
and CI. Read on `phase1/tile-spec` (f6afd66 plus the working tree) and Maxim `origin/main` 6fee7377 (2026-11-17).
Evidence is *measured* (a command ran here), *cited* (a file or page), or *from memory, to verify*.

**No BLOCKER.** The biggest risk is schedule, not a defect: Phase 4 rests on a Maxim release with no date, whose gate
is far from met. The cheapest insulation is mostly paper (O29, done for real) and one lockfile.

## Ranked table

| # | Risk | Cost if it happens | Likelihood | Action now | Owning step | Action cost |
|---|---|---|---|---|---|---|
| 1 | Maxim's stepped `think` (candidates B1) slips a year or more | Phase 4 has no NPCs. The game's pillar waits, and the agent line's tests age against a double | **High** (§1.1) | Carry out O29: write the minimal tier-A subset. Fix roadmap Phase 4, which still requires "OD-A1 to OD-A21" against O29, and record B1's real line (1.5 hybrid src phase). Ask for the date range O29 asks for | roadmap edit, merge line (step 1) | ~1 h |
| 2 | No lockfile, and ruff, mypy and hypothesis are floor-only, so the gate goes red with no local change, and worktrees drift apart | Unrelated PRs fail. Two worktrees' `prepush: PASS` mean different things | **High** over months (§4) | A committed constraints file per Python version, used by CI and step 0a. A weekly unpinned CI job surfaces drift as its own PR | step 1 (standards) or 3a | ~1–2 h |
| 3 | Golden replays (B2) recorded on one numpy, checked on another | The bit-identical corpus quietly downgrades to outcome class in CI forever, or someone regenerates goldens to make CI green | **High** without a lock; low with one (§3) | Lock (row 2). Key the replay goldens by an environment digest. Make world_model §8's header list match boundaries' list | step 5 (intent log), step 9 (save) | ~1 h of spec, then small code |
| 4 | The 3.10 CI cell tests a different numpy/scipy line from 3.14 | Two numerical stacks gated. Pins forced by 3.10 (import-linter 2.15 already). The cell tests numpy 2.2, which is out of support | **Certain** (measured, §4) | Raise `requires-python` to ≥ 3.12. Run the matrix on 3.12 and 3.14 | step 1 or 3a | ~30 min, plus CLAUDE.md text |
| 5 | Our `AgentPort` and reply shape differ from what Maxim ships for B1 | The adapter, the double and the log's reply records need a migration | **Medium–high** (§1.2) | One rule in the agent-line checklist: only host-owned types are frozen into logs and saves. Maxim-shaped values exist only in the adapter. The logged reply record is versioned, and the adapter translates into it | agent line (O19), its checklist | ~15 min |
| 6 | pymaxim changes a frozen SEM type | The mirror plus the bridge's `affordances` builder change. Cheap, because the drift test catches it | **Low–medium** (§1.3) | Keep the drift test. With row 2, move the "latest pymaxim" run into the scheduled job. **Conflicts with CLAUDE.md** ("update the mirror rather than pinning it away"), so the owner decides | step 1 | ~30 min |
| 7 | A Godot upgrade overwrites goldens under the same path | Goldens from two engines mixed under one key. The diff images lose their meaning | **High** that an upgrade comes within 12 months; low cost | Add the Godot version to the golden path key (`compat-llvmpipe-mesa<v>-godot<v>`) | step 2 | minutes |
| 8 | GDScript later proves too slow (greedy meshing; client_rendering §5) | A move to C++ GDExtension or C# for one module | Medium for one module; low for a full switch | None now. B3's language-neutral wire fixtures already make a rewrite checkable. Don't add a language-abstraction layer | — | 0 |
| 9 | BLAS enters the sim | Results depend on thread count and the BLAS vendor | Low (banned in the core, boundaries §4) | None beyond the existing AST ban and the threadpoolctl policy | 3a | 0 |

## 1. Maxim

### 1.1 The slip is likely, and the docs understate it

- **What Phase 4 waits on.** The stepped `think` is candidates **B1**. It "lands after the 1.4.0 cut", and its
  **Line is "the 1.5 hybrid line's src phase"** (Maxim `docs/plans/overdrive_refactor_candidates.md` §B1). Our
  roadmap says only "after Maxim's 1.4.0 cut with the agent-loop decomposition slice" (roadmap Phase 4; npcs O15a).
  That leaves out a whole release line.
- **The 1.4.0 gate is mechanical, and far from met.** `scripts/release_gates.json` fails CI for any version ≥ 1.4.0
  until each gated function is at most 200 lines. Measured on `origin/main` with `ast`:
  - `orchestrator.py::start_simulation_mode` is **1,905 lines** (pinned at 3,003 at slice 0);
  - `tool_dispatch.py::execute_and_learn` is **357**;
  - `agent_loop.py::run_agentic_loop` is 120, which passes.
  
  `docs/plans/roadmap_1_4.md` adds that T0 was "33 items, 32 open (as of 2026-10-18)".
- **Cadence.** Six releases from 1.2.0 (2026-09-08) to 1.3.3 (2026-10-23), and none since. #1361's S3–S6 are slated
  for 1.3.6, which isn't out (Maxim tags; PyPI lists 1.3.3 as the latest).
- **Scenario.** 1.4.0 ships in spring 2027, and the 1.5 hybrid src phase lands B1 after it with its own reviews.
  First real NPCs then come late 2027 or later. A one-year slip is the base case, not the tail.
- **The cheapest insulation is O29, actually done.** The owner decided it on 2026-11-17, and no document holds its
  output: `grep "minimal tier-A"` finds only the decision and the skeptic's finding. Roadmap Phase 4 still requires
  all of OD-A1 to OD-A21.
  - Write the subset from the Phase 4 exit test: three cradled NPCs on the first tile, single-player.
  - Likely in it: B1 (stepped `think`), A3 A-pre (no host time in prompts), A2 (keyed substreams, #1305, already a
    1.4.0 gate item), A4 (leak closure), A5/OD-I3 (pickle-free load) and B2 (dispatch/settle).
  - Likely outside it: OD-A20 and OD-A21 (anchor similarity, τ_elig), A1's full global-path closure beyond the stores
    one NPC touches, and the guest gates (O28 moved co-op to Phase 5).
  
  This is a doc edit, but it turns "wait for Phase 3" into a list Maxim can schedule against.
- **What doesn't help:** a non-Maxim NPC brain (see Over-insulation).

### 1.2 The port shape will move

Maxim's B1 is `think(continuation, input) → request | reply` (candidates §B1). Ours is `think(handle, reply | None)`,
with a host-owned header and an opaque agent body (npcs §6.1, §6.6). Maxim's text says B1 is "one design with hybrid
§A.1b", so its final shape isn't ours to fix. What already insulates:
- `maxim` is banned from the core by import contract (boundaries §4);
- the continuation is an opaque, versioned blob;
- the double implements our port, not Maxim's.

The remaining exposure is the **intent log**. O26 says replay "replays the recorded model replies", so replies are a
logged format. If §6.2 freezes `Reply`'s variants (`cancelled(prefix)`, `truncated(prefix, reason)`) as Maxim-shaped
values, a different Maxim reply type forces a log migration.
- **Action:** the logged reply record is a host type, versioned, and the adapter maps Maxim's values into it.
- **YAGNI:** no speculative shim for API variants Maxim hasn't proposed.

### 1.3 SEM types and the drift test

- `maxim/embodiment/sem.py` was last changed 2026-10-14. The three dataclasses are `frozen=True, slots=True` and
  "SHAPE-FROZEN at 1.0 (CC3)", with `ENTITY_FORMAT_VERSION = "1.1"`.
- The most likely change is **ours**: O5 makes SEM refinement a priority, and `docs/maxim_upstream/` carries a
  breaking-change plan draft. Under CC3 a trailing defaulted field is additive.
  `tests/test_sem_compat.py::_shape` compares fields, defaults and flags, so it fails on such a field until
  `_compat.py` is updated. That is cheap and intended.
- **The gap is when it fires.** With `pymaxim>=1.3` unpinned, a pymaxim release turns every open branch red at once.
  Today all three worktree venvs hold pymaxim 1.3.3 (*measured*) only because they were installed close together.
- **Recommendation:** lock pymaxim with everything else (row 2), and run the drift test plus mypy against the newest
  pymaxim in a scheduled CI job that opens or fails one tracking run. The drift check keeps firing; it stops landing
  on unrelated PRs. This **conflicts with CLAUDE.md's Commands paragraph**, which treats an unrelated red gate as
  "the drift check working". The owner decides; if the answer is no, keep it as is and accept the noise.
- **Out of reach of the shape test.** It can't see behaviour: `Entity` construction, and `ModulatorAffordanceTool`
  semantics beyond the types mypy checks. That is acceptable until tier A; at tier A the strict red gate against
  real pymaxim (§6.2) covers it.

## 2. Godot

- **Support policy (cited).** Only the latest patch of a minor series is supported. The previous minor gets security
  and platform fixes only, and older minors reach end of life ([release policy][gp]). Pinning 4.7.2 is right for
  goldens. Expect one forced upgrade a year, typically for an Apple platform change on the owner's Mac. CLAUDE.md
  already makes an upgrade its own branch.
- **Golden keying.** client_rendering §6.5 keys goldens by Mesa version (`compat-llvmpipe-mesa<version>/`), not by
  Godot version. A 4.8 upgrade changes shader compilation and glow under the same key, so the upgrade branch
  overwrites the 4.7 goldens in place. Add `-godot<version>` to the key, and have `update_goldens.sh` refuse a
  Godot/key mismatch. Step 2, minutes.
- **Compatibility renderer (T8, owner).** It suits an unshaded raymarch and llvmpipe CI. The golden key already
  carries `compat-`, so Forward+ in Phase 2 gets a separate golden set rather than a rewrite.
  - The depth formula sits behind `#if CURRENT_RENDERER == RENDERER_COMPATIBILITY` (client_rendering §5, [ran]), so
    a renderer switch is a known, local edit.
  - The Mac is already advisory, which is right. No action.
- **GDScript vs C# (§7.2: no .NET toolchain).** It is reversible because the client is thin and its contract (B3
  wire fixtures, goldens) is language-neutral. The realistic reversal is one hot module (greedy meshing) moving to a
  GDExtension, not the whole client to C#. Don't pre-build a seam for it.

## 3. numpy, scipy, BLAS and replay determinism

- **What the sim exposes today** (`grep` over `src/`, *measured*):
  - float reductions `.sum()`: heat energy, damage absorbed energy and mean integrity, and the source weights in
    `world.py`, which feed state;
  - `scipy.special.ndtr` (damage's Gaussian CDF);
  - `scipy.ndimage.label`, which is integer and exact;
  - elementwise `+ − × ÷`, `where` and `clip`, which IEEE makes exact.
  
  No BLAS, and boundaries §4 bans it.
- **numpy promises no bit-identity across releases or CPUs.** Maintainers call bit-identical results across systems
  and future releases "impractical", and SIMD rewrites of sin/cos changed results on some CPUs
  ([numpy-discussion][nd1], [nd2]). Float `add.reduce` has SIMD-dispatched loops, so its result can depend on the
  build's dispatch targets (*from memory, to verify*). The `ndtr` implementation has moved within scipy's special
  module across releases (*from memory, to verify*).
- **What breaks on an upgrade.** Saves don't: they store state, and nothing is recomputed on load. Replays do. A
  committed intent log replayed on a newer numpy can differ in the last bit by tick N, and the digest fails. The design
  already answers this correctly: an environment mismatch downgrades to an outcome-class check, and says so
  (boundaries §8). With no lock, though, CI's numpy is whatever PyPI served that day. CI's environment then never
  matches the recording machine, so the bit-identical corpus is never checked bit-identically in CI.
  `test_two_runs_are_bit_identical` and the hash-seed test stay valid on any version, and they are the real guard.
- **Actions:**
  1. Lock (row 2), so a numpy change is a deliberate commit. It regenerates goldens "on a recorded environment
     change", which boundaries already requires.
  2. Key the replay goldens by an environment digest, as the Godot goldens are keyed by Mesa.
  3. Make world_model §8's header list (numpy, scipy, BLAS, platform, dirty flag) match boundaries' list (adds Python,
     `platform.machine()`, numpy's CPU dispatch features, BLAS thread count). Two lists will drift.
- **YAGNI:** no hand-rolled compensated summation, fixed-point fields or a vendored numpy. The promise is one
  machine, bit-identical. Across machines it is outcome class, and the tier rule already enforces that.

## 4. pyproject, lockfile and the CI matrix

- **No lockfile** (*measured*: no `uv.lock`, `requirements*` or constraints file). Every dependency is a floor or a
  range: `numpy>=1.26,<3.0`, `scipy>=1.11,<2.0`, `ruff>=0.15`, `mypy>=1.15`, `hypothesis>=6.100`, `pymaxim>=1.3`.
  `.github/workflows/test.yml` runs `pip install -e '.[dev,maxim]'` fresh on each run.
- **What gate drift looks like.**
  - **ruff:** a minor release stabilises new rules inside selected families (`RUF`, `PL`, `UP`, `B`), and the gate
    fails on code nobody touched (ruff's versioning policy, *from memory, to verify*). The floor is 0.15; the venvs
    hold 0.17.5.
  - **mypy:** strict mode gains checks across majors (venvs: 2.4.1, floor 1.15).
  - **warnings:** `filterwarnings = ["error"]` makes any new `DeprecationWarning` from numpy, scipy or pytest a
    failure.
  - **worktrees:** today the venvs of design-v2, standards and tile-spec agree exactly (numpy 2.5.5, scipy 1.18.1,
    ruff 0.17.5, mypy 2.4.1, hypothesis 6.170.15, pymaxim 1.3.3; *measured*), by timing alone. A venv rebuilt next
    month differs, and step 0a's "record `pip show pymaxim`" records the drift without preventing it.
- **The 3.10 cell is a different stack** (PyPI metadata, *measured*):
  - numpy 2.3 requires ≥ 3.11 and 2.5 ≥ 3.12; scipy 1.16 requires ≥ 3.11 and 1.18 ≥ 3.12;
  - so CI on 3.10 resolves numpy 2.2.6 and scipy 1.15.3, and 3.14 gets numpy 2.5.x and scipy 1.18.x.
  
  Python 3.10 reached end of life in 2026-10 (PEP 619, *from memory, to verify*), and numpy 2.2 is past SPEC 0's
  window ([endoflife.date][eol]). The cell spends gate time on a stack no player will run, and it already forced the
  import-linter pin (boundaries §12). Nothing in the §0 tables decides 3.10; it is CLAUDE.md text. Recommend ≥ 3.12,
  a matrix of 3.12 and 3.14, and ruff and mypy targets moved to match. pymaxim's `>=3.10` doesn't constrain this.
- **The lock.**
  - **Mechanism:** `uv pip compile` (or `pip-compile`) to `constraints/py312.txt` and `py314.txt`, with hashes. CI and
    step 0a install with `-c`.
  - **Drift:** a weekly scheduled job installs unconstrained and opens the bump as its own commit, which regenerates
    goldens "on a recorded environment change".
  - **Cost:** about an hour, plus a minute per bump.
  - **Not** a switch to Poetry or uv project management. A constraints file is enough.

## Over-insulation to avoid

- A shippable non-Maxim NPC brain (conflicts with O6 and §6.2; revisit only on the owner's call if the slip passes a
  year).
- Vendoring or forking pymaxim, or a version-adapter layer for SEM types beyond `_compat.py`.
- Deterministic summation or fixed-point physics to get bit-identity across machines (the promise is per machine).
- A Godot abstraction layer, or C# readiness.
- Exact Docker pinning beyond client_rendering §6.5's digest, Mesa and SHA-256, which is already sufficient.

## Sources

- Maxim `origin/main` 6fee7377: `docs/plans/overdrive_refactor_candidates.md` (§B1, §Order),
  `scripts/release_gates.json`, `docs/plans/roadmap_1_4.md`, `src/maxim/embodiment/sem.py`, and the tags v1.2.0–v1.3.3.
- Here: `pyproject.toml`, `.github/workflows/test.yml`, `tests/test_sem_compat.py`, `docs/roadmap.md` (Phase 3,
  Phase 4), `docs/design/npcs_and_sem.md` §0 and §6, `docs/design/boundaries.md` §4 and §8,
  `docs/design/world_model.md` §8, `docs/design/client_rendering.md` §6.5 and §7.
- PyPI JSON API for numpy, scipy and pymaxim `requires_python` (fetched 2026-11-18).
- [gp]: https://docs.godotengine.org/en/stable/about/release_policy.html
- [nd1]: https://mail.python.org/archives/list/numpy-discussion@python.org/thread/56BRFMN7LDV2VPRUVZGE7C2AIAGCGVBV
- [nd2]: https://mail.python.org/archives/list/numpy-discussion@python.org/thread/C6EYZZSR4EWGVKHAZXLE7IBILRMNVK7L
- [eol]: https://endoflife.date/numpy
