# Step 3b part (b), delta round 5: statuses and the author's fold

Diff: `3dab2b4..d263c1b` (delta round 4's fold). One reader held Executor, Trust boundary, Wire integrity and
Bio-faithful, under the owner's input-lint threat model (B31). Python 3.14 was not run for this round: Homebrew's 3.14
has no numpy, so `simcore` would not import. The reader can't write files, so this is the author's condensed record.
**Statuses are the reviewer's (O25); the Fold column is the author's claim.**

## Delta round 4 findings, status set by the reader

- **Fixed:** R4-2 (deleting the NFKC clause: 15 red), R4-4 (checked at 043eab8: `plan_document.py:280`,
  `loop_state.py:247`), R4-5 (300,000 fuzzed strings raised nothing but `IDNAError`), R4-6, R4-7 (`check_lock` PASS;
  pins identical), R4-9 (removing `O_NONBLOCK` fails the test in 12.4 s instead of hanging; this settles R3-10).
- **Fixed in part:** R4-1 (Cherokee in capitals and Arabic-Indic numbers kept; lower and title case refused, R5-1;
  the digit shortcut skips IDNA's mixing rule, R5-2), R4-3 (the trailing-joiner rule guarded by 30 tests; B30's list
  incomplete, R5-3).
- **Rejected:** R4-8, under the owner's threat model.

## New findings in d263c1b

| Id | Sev | Location | Scenario | Fold (author's claim) |
|---|---|---|---|---|
| R5-1 | SF | `schema.py::_visible_word` | Cherokee in lower case (`ꮳꮃꭹ`) or title case refused | a third candidate, upper-cased: enumerated over all of Unicode it admits exactly Cherokee's 86 small letters, each with its capital's `entity_key`, so no twin (`casefold` would admit U+1C80, a twin IDNA refuses); both cases in the kept-name test; dropping the candidate turns 2 tests red (measured) |
| R5-2 | SF | `_visible_word` | the digits-only shortcut skipped IDNA's CONTEXTO rule, so `room ١۲` (two digit systems) twinned `room ١٢` | one digit system per word (one zero point, `ord(ch) - unicodedata.digit(ch)`); `room ١۲` and `1٢` in `Text.bad`; dropping the rule turns 30 tests red (measured) |
| R5-3 | NIT | B30 | a joiner mid-word where it renders nothing (Tamil `க்` + ZWNJ + `க`) and whole numbers in two look-alike digit systems pass | both listed in B30, for TR39's skeleton |
| R5-4 | NIT | the comment above `_NAME_SEPARATORS` | said "once lower-cased" | matches `_visible_word` now |
