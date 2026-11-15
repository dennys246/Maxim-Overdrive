# Standards backlog: rules waiting for a check

Every rule in CLAUDE.md's "Engineering standards" names its guard. A rule that nothing checks yet points here, so
the gap stays visible. Mechanizing a row beats adding a rule. When a row's check lands, cite the check in CLAUDE.md
and mark the row **done** with the commit, rather than deleting it.

| ID | Rule it enforces | The check | Lands with |
|---|---|---|---|
| B1 | Pre-push review | The hand-off note and PR description carry a round summary (lenses, severity counts, deferrals), and no `src/` commit after the last round goes unreviewed. Process today; a check could compare the reviewed commit with the pushed head. | open |
| B2 | Determinism and replay | The server records every accepted intent with its turn. A replay test feeds a recorded log back in and gets bit-identical state. | Phase 1 step 2 |
| B3 | Versioned formats | Golden wire fixtures under `tests/fixtures/wire/`, decoded by the Python tests and by the GDScript client tests, so both sides prove they read the same bytes. Unknown protocol versions are refused at the handshake. | Phase 1 steps 2 and 4 |
| B4 | Versioned formats | Save format v0: a round-trip test plus a committed golden save that every later version must still load or refuse loudly. | Phase 1 (save v0) |
| B5 | Performance budgets | A benchmark per profile on the first tile: turn time, snapshot encode time and bytes. A regression of more than 20% against the committed baseline fails pre-push. The budgets are set from the first measurements, not guessed. | Phase 1 step 3 |
| B6 | Client standards | `scripts/prepush.sh` runs Godot headless: a project import, a parse check of every script with typed-GDScript warnings as errors, and the client test suite. | Phase 1 step 4 |
| B7 | Client standards; exit tests | Golden screenshots: a scripted scene at a fixed camera and turn, rendered at each profile and compared with a perceptual tolerance. This is how "looks the same apart from detail" becomes a test. | Phase 1 step 5 |
| B8 | Assets and data | `assets/MANIFEST.yaml` lists every non-code asset with source, author and licence. A check fails on unlisted files and on licences that `ASSETS_LICENSE.md` doesn't allow. | the first non-procedural asset |
| B9 | Physics invariants | Hypothesis property tests over random scenes: energy is conserved in an insulated box with no sources; integrity never rises without a repair action; temperatures stay finite and within physical bounds. | Phase 1 hardening, before step 3 |
| B10 | Testing: prove a guard by deletion | Periodic mutation testing (for example `mutmut`) over `world/`, `server/` and `imagination/`. Surviving mutants become tests or written reasons. | open |
| B11 | Everything in pre-push | `.github/workflows/test.yml` runs `scripts/prepush.sh` on every push and PR. It has not yet run on GitHub; the first push verifies it, and a red first run is fixed in the workflow, not by loosening the gate. | first push of `phase1/standards` |
| B12 | Assets and data | Every file under `data/` loads and validates in a test (materials, rigs, scenes), so a malformed data file fails pre-push rather than at launch. | Phase 1 step 3 |
| B13 | No silent swallows | Ruff's BLE and S110 catch `except Exception` and `except: pass`. They don't catch a narrow `except` that returns a fallback without reporting it; that is a reviewer's job until a lint exists. | open |
| B14 | The client is untrusted input | Server tests that refuse: a handshake with any `Origin` header, a missing or wrong token, an unknown protocol version, malformed and oversized messages (an error reply, state unchanged). A test that the listener is bound to loopback only. | Phase 1 step 2 |
