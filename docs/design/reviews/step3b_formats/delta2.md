# Step 3b part (b), delta round 2: statuses and the author's fold

Diff: `f2c180c..d116508` (290bff6, the owner's two decisions, and d116508, delta round 1's fold). Two readers:
Executor with Trust boundary; Wire integrity with Architecture, Determinism and Bio-faithful. The gate printed
`prepush: PASS d1165086b38d` for the reviewed commit. Readers can't write files, so this is the author's condensed
record. **Statuses are the reviewers' (O25); the Fold column is the author's claim, for delta round 3 to set.**

Verified, no change: the simulation bit-identical to `origin/main` at 0.2 and 0.1 m on three scenarios; no design
document grew across the branch (tile 5,985 to 5,967 words, fire_solid 5,992 to 5,972); every sibling worktree's
consumer of the changed contracts still holds (client-shader's v0 scene is round 1's Wire S1, deferred).

## Delta round 1 findings, status set by the delta-2 readers

- **Fixed:** D1 (Trust) and T1-S3 for `real_path` and `touch`; D2/D-S3; D3 (Trust) for the static case; D-S1; D-S4;
  D6 and D9 (Trust); D1, D2, D3, D4, D5, D6, D7 (Det); D-S2; D8; S5 (Wire); D-N3; D-N4.
- **Rejected, reviewer accepts:** D-N5 / D7 (Trust), the `read_yaml` handler's scope, documented.
- **Open:** D4 (Trust), the invisible-character class (N2 below); D5 (Trust) and D-N1, right but untested; Bio N4,
  whose recorded evidence was wrong (SF-1 below).

## New findings in d116508

| Id | Sev | Location | Scenario | Fold (author's claim) |
|---|---|---|---|---|
| SF-1 (Bio) | SF | lesson 25, roadmap OD-A16 | cited `classify_failure_type` misreading `out_of_range (energy_j)`; its only caller is the planner Maxim's docstring calls dormant (`plan_manager.py`, 043eab8) | corrected: the live replan path reads `error_kind` (`loop_state.py:248`); the dormant classifier is no evidence |
| N1 (Trust) | SF | `loaders.py::DataPath` | `(data_dir() / 'x.yaml')._path.open()` read a data file past the gate: an underscore is not a capability | a handle holds no path; the gate keeps each in a `WeakKeyDictionary` no caller can import; handles compare by identity; test asserts no `_path`; corpus row marks the route as guarded by the type |
| N2 (Trust) / SF-2 | SF | `schema.py::Text` | U+034F, U+E0100-E01EF, a trailing U+2800 and NFD `café` passed beside `crate`, `café` | the hand list is replaced by an allowlist by Unicode category: letters, digits, space and `_ - . '`, in NFC, minus the four Hangul fillers; each case is in `Text.bad` and a test keeps real names from any script |
| N3 (Trust) | SF | `lint_inputs.py::_computed_getattr` | `getattr(*(g, '__globals__'))`, `g2 = getattr`, and computed names in the game package passed | any `getattr` but a plain call with a literal name is flagged, in every `src/` module; corpus rows both ways |
| N4 (Trust) | SF | `loaders.py::_text_of` | a symlink swapped for a FIFO between `is_file()` and `open()` hung the read | opened once, `O_NONBLOCK`, judged by `fstat` on the descriptor before anything reads; an unreadable file is a coded refusal (test) |
| SF-3 / N5 | SF / NIT | `grid.py::name_region` | deleting its region-name check left every test green | its own parametrized test |
| D5, D-N1 (open) | NIT | `Text`, `bridge.py` | right but untested | a `str` subclass in `Text.bad`; a numpy affordance test |
| N-1 / N6 | NIT | `MAX_DIFFUSIVITY_M2_S` comment | "above 0.04 s" was false (0.0375 uniform, about 0.019 worst); lead is not the lowest specific heat | measured figures; thorium |
| N-2 | NIT | `digest.py` | "below 600 digits", 600 accepted | "at most" |
| N-3 | NIT | `test_sem_compat.py` | `tool_bridge`'s inline aliases unchecked | read from its source, compared as a set |
| N-4 / N9 | NIT | `Text.reserved` | `Text(reserved=("Self",))` matched nothing | normalised under `entity_key`; test |
| N-5 | NIT | lesson 25, `agent_text` | "a schema field" contradicts `wrong_target (target)` | "a name we wrote"; over-long lines rewrapped |
| N-6 | NIT | corpus | three rows imported the removed `real_path` | rewritten as methods on a value |
| N7 | NIT | `_text_of` | the bounded read was untested | a test spies on the read's size |
| N8 | NIT | `existing_directory` | an absolute candidate replaced the base | a TypeError (candidates are written in code); test |
