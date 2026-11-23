# Generation harness design, delta 1: Architecture, Trust boundary and Executor (2026-11-22)

The reader's hand-back, condensed and saved by the author. The reader set every status, read from the tree at e55c079
against:
- `pyproject.toml` and the gates: `test_determinism.py`, `tests/_imports.py` and `lint_inputs.py`;
- `imagination.place`, `simulation.py` and `encoding.py`;
- `boundaries.md` §2.2, §4.4 and §9.1, IG §8, IP §2.2, `sem_stimuli.md` D10, `fire_model.md` and the roadmap.

## Statuses

**Architecture:**
- **Fixed:**
  - B2, as a proposal;
  - B3: `overdrive_tools` may import `simcore.verify`;
  - S1 and S3: proposed IP and IG edits;
  - S2, S4, S5 and S6;
  - S7: a third root out of the wheel;
  - N1;
  - N3, with one inconsistency (NN1).
- **Open:**
  - B1: the import surface is stated but can't carry the checks (NB1);
  - N2: the batch log's home doesn't exist (NB3).
- **Deferred:** B4, because IG and IP can't carry the protocol. Trigger: Phase 4. The removal moment isn't really
  scheduled (NS3).
- **Rejected as moot, accepted:** N4.

**Executor:**
- **Fixed:**
  - B1, as named but partly wrong (NS1, NN3);
  - B2: L5 is inverted, and a planted failure mode turns it red;
  - B3, mostly (NN4);
  - S1, S2, S5, S6, S7, S8 and S9;
  - N1, N3 in intent, and N4.
- **Deferred:** S3. `digest.py`'s owner decides; trigger: U8's build at H3.
- **Open:**
  - S4: fold1 claims "L5 records only clock-free fields", but neither the design nor the checklist says so;
  - N2: PR #50 is still cited without a commit.

**Trust boundary:**
- **Fixed:**
  - T1: no fallback, and the base URL is checked before the first request;
  - T3, T4, T5, T6, T8 and T9;
  - T7, mostly (NS6);
  - N1 (also in the spike at 397e8db) and N2;
  - N3, in rule.
- **Open:** T2. The log home doesn't exist (NB3), and the mask omits the API key (NS5).

## New findings

**Contract blockers (B33):**
- **NB1, §4: the stated import surface omits modules the design requires.**
  - The missing modules: `schema` (the job file is a `Format`), `refusals` (§6's `spec_fault`), `materials` (U4 and
    the engine-property bounds), and frames or reductions (U2, U3, the ledger and U8).
  - The only read path listed is `encoding`, whose `temperature_c` is float16 (about 0.5 °C near 1,000 °C and 2–4 °C
    above 2,048 °C). That puts display quantization inside a verification bar.
  - *Fix (unverified):* list those modules, and say that verdicts read published frames, never `encoding`.
- **NB2, §3 against §5.3:** "byte-identical records" across runs can't hold while every record has `wall_s` and
  timed-out records are written. *Fix (unverified):* classify record fields as `must_match` or informational, and
  define identity as the byte equality of the projection onto identity fields, with timed-out and transport records
  removed.
- **NB3, §2 and §4: the egress check's address has no legitimate home.**
  - The "per-user directory" §2 names doesn't exist (`data.py` resolves only shipped data).
  - IP §2.2's placement has no address field, and IG §8's `endpoints.yaml` is read only by the gateway.
  - H1 would write a second reader of IG's gated files, or invent an ungated file holding the address and key: T2's
    leak path again.
  - *Fix (unverified):* a versioned per-user `generation_endpoints` file as the harness's own registered gate, with
    its directory proposed to `boundaries.md`, or an IG §8 exception by name.

**SHOULD-FIX:**
- **NS1:** one `NOT_SIMULATION` entry exempts the whole package, battery and scorer included. Exempt only the client
  and runner module. A mechanism, for the H1 checklist.
- **NS2:** the lab builder's "new home" is named nowhere. `fire_model.md:243` puts it in tests only, and a `src/`
  import from `tests/` isn't covered by `tests-out`.
- **NS3:** `TEMPORARY(phase4/inference)`'s removal depends on Phase 3 asks (F6, OD-I12) and on batch eligibility,
  which no Phase 4 row carries. Fix: add the row, or mark the band-aid against the Phase 3 items.
- **NS4:** the measured weights digest is a declaration for `owner_lan`, and the temporary client's engine proof
  source (`/props`) is unstated.
- **NS5:** the mask omits the API key. Fix: the key never enters a run directory, masked too, with a planted test.
- **NS6:** §9.1's strict decoder isn't built, and it bounds size, not depth. List its build as an H1 precondition and
  propose the depth bound to §9.1.
- **NS7:** §5.5 excludes `within_margin` specs from every consumer, which steers stage 2's data, the very argument §6
  makes against excluding `engine_gap`. Fix: decide exclusion per consumer, or say why the margin is different.

**NIT:**
- NN1: §10's H0 omits PR #52.
- NN2: the package's source path is unnamed.
- NN3: the `ALLOWED` list names `subprocess` with no consumer, and spawn sites outside `tests/` and `scripts/`
  aren't covered.
- NN4: U3s and U10 name no band source.
- NN5: U11's "Until" names no step.

**Verdict:** most round-1 findings are fixed in the tree. Exec S4, Trust T2, Arch N2 and Arch B1 remain open against
fold1's claims. Three new contract BLOCKERs (NB1–NB3) mean that under B33 the rounds stop: they fold or the owner
overrules them. The mechanism findings (NS1, NS4, NS5, NS6, the NITs) move to the H0/H1/H3 checklist; NS2, NS3 and NS7
need the author's decision.
