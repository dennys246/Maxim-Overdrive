# Step 3b part (b), delta round 3: statuses and the author's fold

Diff: `d116508..7e04987` (7314103, delta round 2's fold, and 7e04987, a test-typing fix). One reader held all six
lenses, on Python 3.12 (Unicode 15.0) and 3.14 (Unicode 16.0) for the name probes. The reader can't write files, so
this is the author's condensed record. **Statuses are the reviewer's (O25); the Fold column is the author's claim.**

Two owner decisions came out of this round (2026-11-21), after three rounds in a row had found holes in the name rule
and the input lint kept meeting deliberate spellings:
- **Names: full Unicode, done properly.** The hand-written rules are replaced by IDNA2008 (the `idna` package, already
  locked) plus NFKC.
- **The input lint: fold R3-3 and R3-4, then stop.** It guards mistakes, not adversaries; further spellings go to
  backlog row B39 (trigger: untrusted code able to reach `src/`), and the review charter says so.

## Delta round 2 findings, status set by the reader

- **Fixed:** N4, SF-3/N5, D5, D-N1, N-1/N6, N-2, N-3, N-4/N9, N-5, N-6, N7, N8; SF-1 for the lesson's false claim.
- **Open:** SF-1's roadmap half and replacement wording (R3-5); N1, as `_REAL` was reachable through `vars()` (R3-3);
  N2/SF-2/D4, the name rule (R3-1, R3-2); N3, `__builtins__.getattr` (R3-4).

## New findings in 7314103..7e04987

| Id | Sev | Location | Scenario | Fold (author's claim) |
|---|---|---|---|---|
| R3-1 | SF | `schema.py::_visible_name` | Hindi, Tamil, Bengali, Khmer, Sinhala, vocalised Arabic and `O’Brien` refused: they need combining marks; the "any script" test was Latin only | each word must be a valid IDNA2008 label once lower-cased (marks after a base, joiners only where CONTEXTJ allows); `’` is a separator; the test holds eleven scripts' names |
| R3-2 | SF | `schema.py::_visible_name` | U+13441 (a blank letter) passed; the NFC clause guarded nothing a test saw; fullwidth and ligature forms passed | NFKC required (refuses compatibility forms, and decomposed Hangul jamo); a letter named BLANK or FILLER refused by its Unicode name; each in `Text.bad` |
| R3-3 | SF | `loaders.py::_REAL` | `vars(L)['_REAL'][h]` reached the real path past every check | any call of `vars`, `globals` or `locals` in `src/` is flagged; corpus rows |
| R3-4 | SF | `lint_inputs.py::_computed_getattr` | `g = __builtins__.getattr` passed | `getattr` as any value (a name, an attribute, a subscript) is flagged; corpus row |
| R3-5 | SF (Bio) | lesson 31 (numbered 25, then 29, before merges with main), roadmap OD-A16 | conflated two readers: the pain detector books an external failure, the replan path reads `error_kind`, which is `None` | both say so, cited at 043eab8 (`tools/base.py`, `executor.py:789`, `loop_state.py:248`, `plan_document.py:281`); "live" dropped, as unverified |
| R3-6 | NIT | `loaders.py::DataPath` | `DataPath()` and copies had no path entry and failed with a bare KeyError | only the gate constructs one (a private token); a copy is the same handle; test |
| R3-7 | NIT | the name rule | it follows each Python's Unicode database (3.12 and 3.14 differ by about 5,000 letters) | recorded in B38; every shipped name is ASCII |
| R3-8 | NIT | `lint_inputs.py` docstring | said `src/simcore/` only | every `src/` module |
| R3-9 | NIT | the starred clause | caught nothing the arity check missed | removed |
| R3-10 | NIT | `_text_of` | a NUL in a path raised a bare ValueError; a device was opened without `O_NOCTTY`; the FIFO test would hang, not fail, without `O_NONBLOCK` | coded `bad_name`; `O_NOCTTY`; the hang is not folded (no test timeout plugin is installed) |
