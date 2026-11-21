# Step 3b part (b), delta round 4: statuses and the author's fold

Diff: `7e04987..3dab2b4` (delta round 3's fold). One reader held Executor, Trust boundary, Wire integrity,
Architecture and Bio-faithful, on Python 3.12 and 3.14, under the owner's input-lint threat model (B38). The reader
can't write files, so this is the author's condensed record. **Statuses are the reviewer's (O25); the Fold column is
the author's claim.**

## Delta round 3 findings, status set by the reader

- **Fixed:** R3-1, R3-3, R3-4, R3-5 (the conflation; a new false clause is R4-4), R3-6, R3-8, R3-9; R3-10's NUL case.
- **Fixed in part:** R3-2 (the blank-letter rule; the NFKC clause had no failing test, R4-2).
- **Deferred with its trigger:** R3-7 (B37).
- **Open:** R3-10's hang, deferred with no row (R4-9). `O_NOCTTY` accepted untested.

## New findings in 3dab2b4

| Id | Sev | Location | Scenario | Fold (author's claim) |
|---|---|---|---|---|
| R4-1 | SF | `schema.py::_visible_name` | `.lower()` refused all of Cherokee (written in capitals IDNA allows, lower-cased to letters it doesn't); IDNA's per-label bidi rule refused "room ٢" with an Arabic-Indic digit | a word is kept if it is a valid label as written or lower-cased; a digits-only word is judged as digits; both in the kept-name test. A digit fused to an RTL word (`2חדר`) stays refused by RFC 5893 rule 1, a deliberate choice |
| R4-2 | SF | `_visible_name`, `Text.bad` | deleting the NFKC clause left 821 tests green; it alone refuses a Kelvin-sign twin of "Krate" | `Krate` in `Text.bad`; deleting the clause now turns 15 tests red (measured) |
| R4-3 | SF | B37, `_visible_name` | a joiner ending a word (`க்` + ZWJ) passed, a twin of `க்`; B37 said only cross-script look-alikes remained, though mark runs and `O'Brien` / `O’Brien` remain | a trailing ZWJ or ZWNJ is refused, two `Text.bad` rows; B37 lists what remains, the apostrophe pair included (folding `’` is Maxim's `entity_key`) |
| R4-4 | SF (Bio) | lesson 29 (numbered 25 before the merge with main) | "neither reads the text" is false: the replan prompt carries it as "Failure reason:" (`plan_document.py:280`) | "neither classifies by the text, though the replan prompt carries it verbatim" |
| R4-5 | NIT | `_visible_name` | `except (IDNAError, ValueError)` wider than needed | `idna.IDNAError` only |
| R4-6 | NIT | `Text.convert` | the refusal message named no IDNA rule | it names NFKC and IDNA2008 |
| R4-7 | NIT | lockfiles | idna's `# via` lines didn't list this package | added in both; `check_lock` passes |
| R4-8 | NIT | `_computed_getattr` | `vars(args)` on an argparse namespace is flagged | accepted under the owner's threat model; attribute access is the allowed spelling |
| R4-9 | NIT | the FIFO test | without `O_NONBLOCK` it hung the gate rather than failing | the read runs on a 10 s deadline; removing `O_NONBLOCK` now fails the test (measured) |
