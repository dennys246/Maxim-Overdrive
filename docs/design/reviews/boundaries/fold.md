<!-- Moved verbatim from `docs/design/boundaries.md` at 5c054f6 by phase1/docs-contracts (CLAUDE.md, "One owner per
contract": fold tables live in reviews/). A record: never edited. -->

## Fold table: the v1 review (`reviews/boundaries/`)

Every v1 BLOCKER and SHOULD-FIX, as folded in v2. **Three v2 folds were revised in v3** after the foundations review
found them not achieved or overtaken: D-B4 (v2's flag-toggling window failed; v3's ownership window, §4.1), D-S8 (v2
left lanes §4.2's arrival order standing; v3 states one key, §6.2), and Arch B1 / BF-1 (v2's mode (a); superseded by O6,
§7.2).

| Finding | Severity | Status |
|---|---|---|
| Arch B1 execute's result contract | BLOCKER | folded: §7.2 (owner decision O2; detail in part 2) |
| Arch B2 the gate lint can't see the door | BLOCKER | folded: §5.2 |
| Arch S1 rendering tier reaches physics | SHOULD-FIX | folded: §2.2, §10 |
| Arch S2 layers allow skipping | SHOULD-FIX | folded: §2.2 skip-layer rule, §10 |
| Arch S3 the intent gate has no home | SHOULD-FIX | folded: §2.2 `engine.intents` |
| Arch S4 sealed set too narrow; two lists | SHOULD-FIX | folded: §3 |
| Arch S5 no geometry layer | SHOULD-FIX | folded: §2.2 |
| Arch S6 read-only views wrong once there are lanes | SHOULD-FIX | folded: §4.2 |
| Arch S7 schema vs registry | SHOULD-FIX | folded: §9.1 |
| Arch S8 split trigger; client not cut | SHOULD-FIX | folded: §2.1 |
| Arch S9 engine reaches game data by default paths | SHOULD-FIX | folded: §3, §8.2 |
| Arch S10 harness has no package | SHOULD-FIX | folded: §2.1, §8.4 (imports engine only, per BF-9, not engine and game) |
| Arch S11 other doors; unmarked band-aid | SHOULD-FIX | folded: §6.4 |
| Arch S12 order disagrees with world_model §10 | SHOULD-FIX | folded: §11.1, world_model §10 and roadmap updated |
| BF-1 queued intents blind Maxim's credit | BLOCKER | folded: §7.2 mode (a) now, (b) later; §9.3 |
| BF-2 where the substrate runs | BLOCKER | folded: §3, §7.1 (owner decision O3) |
| BF-3 only `sem_env` can't hold | BLOCKER | folded: §8.1 |
| BF-4 percepts are samples, not views | SHOULD-FIX | folded: §4.2 |
| BF-5 the push path | SHOULD-FIX | folded: §4.3 |
| BF-6 no actor on execute | SHOULD-FIX | folded: §7.2 per-actor binding; §9.3 |
| BF-7 the membrane is omniscient | SHOULD-FIX | folded: §4.4 (B-13) |
| BF-8 stale: credit or context | SHOULD-FIX | folded: §7.2 (lesson 9 wins; lanes §4.3 to be corrected) |
| BF-9 harness must depend on the engine only | SHOULD-FIX | folded: §8.4 |
| BF-10 drift check covers shape only | SHOULD-FIX | folded: §8.1 |
| BF-11 two clocks into one agent | SHOULD-FIX | folded: §7.3 |
| D-B1 the writers are outside the core | BLOCKER | folded: §3 |
| D-B2 unrecorded input from disk | BLOCKER | folded: §3, §6.3 |
| D-B3 the log has no record | BLOCKER | folded: §6.2 |
| D-B4 read-only views defeated | BLOCKER | folded: §4.1 |
| D-S1 the tripwire can't see the cited case | SHOULD-FIX | folded: §3 |
| D-S2 the forbidden list vs import-linter | SHOULD-FIX | folded: §3, §10 |
| D-S3 non-import leaks | SHOULD-FIX | folded: §3 |
| D-S4 environment header | SHOULD-FIX | folded: §6.3 |
| D-S5 observation reads live state | SHOULD-FIX | folded: §4.2 |
| D-S6 the AST scan can go vacuous | SHOULD-FIX | folded: §11.2 |
| D-S7 one log for every input | SHOULD-FIX | folded: §6.1, §6.2 |
| D-S8 canonical same-tick order | SHOULD-FIX | folded: §6.2 |
| D-S9 log the typed canonical intent | SHOULD-FIX | folded: §6.2 |
| X-1 lint-imports reads the main checkout | BLOCKER | folded: §10 |
| X-2 `execute` is the gate | BLOCKER | folded: §5.2, §5.3 |
| X-3 B-10 guards copies | BLOCKER | folded: §4.1, §4.2 |
| X S-1 `os.urandom`; scan misses | SHOULD-FIX | folded: §3 |
| X S-2 the layers fail on today's code | SHOULD-FIX | folded: §2.2 |
| X S-3 three gates don't refuse | SHOULD-FIX | folded: §5.4 (gates-to-be, hardened in 2c) |
| X S-4 the lint rule's false positives and misses | SHOULD-FIX | folded: §5.2 (rule dropped) |
| X S-5 migration drops the game package | SHOULD-FIX | folded: §11.2 |
| X S-6 import-linter pin; cache | SHOULD-FIX | folded: §10 |
| X S-7 B-9's check misses `sources`; mechanism | SHOULD-FIX | folded: §4.1, §6.4 |
| X S-8 the core does file IO; `sem_env` runs in the turn | SHOULD-FIX | folded: §3 (the writers move in; the gate half is outside, with no clock or IO) |
| X S-9 packaging and the B-5 split | SHOULD-FIX | folded: §8.2 |
| TB-B1 the lint can't detect a new door | BLOCKER | folded: §5.2 |
| TB-B2 typed frozen is false | BLOCKER | folded: §5.1 |
| TB-B3 no authority or identity | BLOCKER | folded: §6.1 |
| TB-S1 the gate list is incomplete | SHOULD-FIX | folded: §5.3 |
| TB-S2 gates not equally strong | SHOULD-FIX | folded: §5.4 |
| TB-S3 no cost or size budgets | SHOULD-FIX | folded: §5.4 |
| TB-S4 the schema is shape only | SHOULD-FIX | folded: §9.1 |
| TB-S5 the target check is by identity | SHOULD-FIX | folded: §5.3, §6.2 |
| TB-S6 imagination is a second door | SHOULD-FIX | folded: §5.3, §6.4 |
| TB-S7 the B-9 test sees only exercised paths | SHOULD-FIX | folded: §4.1 |
| TB-S8 the wheel's licence; material key sets | SHOULD-FIX | folded: §8.2 |
| W1 rebases land in the game package | BLOCKER | folded: §2.1, §11.3 |
| W2 scope references go engine-only | BLOCKER | folded: §11.2 |
| W3 lint-imports reads the main checkout | BLOCKER | folded: §10 |
| W4 the empty package has no caller | SHOULD-FIX | folded: §2.1 |
| W5 the `_data` mapping is never exercised | SHOULD-FIX | folded: §11.2 |
| W6 the tier variable split across files | SHOULD-FIX | folded: §11.2 |
| W7 docs sed unsafe and incomplete | SHOULD-FIX | folded: §11.2 |
| W8 contracts partly unexpressible; the guard step | SHOULD-FIX | folded: §3, §10 |
| W9 merge order | SHOULD-FIX | folded: §11.3 |

v1 coverage: 18 of 18 BLOCKERs and 52 of 52 SHOULD-FIXes folded in v2, three of them revised in v3 (above), and the
gate-registry fold (Arch B2, TB-B1, X-2) made mechanical in v3 (foundations Arch S15). NITs folded where they touched a
section: Arch N1–N8; BF-12 to BF-15; D-N1 to D-N3, D-N5; X N-1 to N-3; TB-N1 to N-4; W10 to W14. D-N4 (drive
determinism tests from the golden log, by kind) is deferred to sim-clock, where the golden log is born.
