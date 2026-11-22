# Moves, steps 3d and 3e

Old locations are at `origin/main` 5c054f6, as in `moves.md` (which is near its word budget). No heading moved.
Abbreviations as in the plan's §2.

## Step 3d: packaging and gates

| Row | Contract | Owner section | Copies now links | Added to the owner |
|---|---|---|---|---|
| 39 | Phase 3 rows (OD ids) | `roadmap.md` Phase 3 | `boundaries.md` §9.3 (the table, now one sentence of ids); `npcs_and_sem.md` §8.1 (the "What" and "Path" columns; "Here" kept) | nothing; OD-A16's `wrong_target` stays the roadmap's, and the copies that lacked it are gone |
| 49 | Package layers | `boundaries.md` §2.2 | `tile_and_client.md` §7 (a lead line); `verify_harness.md` §2 ("under `maxim_overdrive` and above `simcore.protocol`"); `inference_gateway.md` §1 ("7a", "7b" removed; the column already cites §2.2); `sem_stimuli.md` §7.1 ("the layer order stays §2.2's") | ruling 49's five layers as `pyproject.toml`; which table rows are built, under which `simcore` package; which are not built; the table kept as O24's map of splits |
| 50 | Write-window owners | `boundaries.md` §4.1 | `boundaries.md` §10 ("`place` opens it too", now "the window's owners are §4.1's") | ruling 50's four owners; §10's "`place` opens it too (marked for 5a; `imagine` has no intent kind)", verbatim |
| 51 | `logging` in the core | `boundaries.md` §3 | `boundaries.md` §10 ("§3's ban covers `logging` too") | `logging` moved from allowed to banned, with `pyproject.toml`'s reason verbatim; the built list is the `sealed-core` contract, equal to `SEALED_CORE_BANNED` |
| 52 | Who imports `maxim` | `boundaries.md` §8.1 | `npcs_and_sem.md` §6.6 (the host's imports); `sem_stimuli.md` §7.3 (a citation on its `maxim-through-adapters` row) | as built, only `simcore.adapters.sem`; the worker module (SS §7.3) and `engine.adapters.inference` (IG §1) join when built; N §6.6's host sentence, verbatim; the pin 2.6 from `constraints/py3.12.txt` beside "verified on 2.15" |
| 53 | Where the gates are | `boundaries.md` §5.3 | `fire_solid.md` §5.1 ("the one input gate"); `architecture.md` "SEM for the environment" (the modulator no longer carries LLM output and client intents) | nothing; §5.3's client-frames row now cites §9.1 for the strict decoder, not §10 |
| 54 | Gate contract | `boundaries.md` §5.4 | `world_model.md` §8 (F14's lead line; material table v1's "versioned, closed keys, repeated keys refused"); `ip_and_licensing.md` §6 item 3 ("as every loader does") | nothing |
| 55 | Experiment harness | `npcs_and_sem.md` §10 | `boundaries.md` §2.1 (rule, package bullet, table row), §8.1 (table row), §8.4 | B §8.4's import bullet and ledger-pins bullet, verbatim apart from the subject ("it" for `maxim_experiments`) |
| 56 | Content and licence | `boundaries.md` §8.2 | `architecture.md` "Licensing"; `roadmap.md` standing rules | architecture's sentence, verbatim (the roadmap's is a subset) |

Also: `inference_placement.md` §4.3's ledger citation moves from B §8.4 to N §10, and B §2.1's "The engine's name is
open (Q1)" now reads `simcore` (O23, as built).

Skipped:
- **Row 57** (golden method): no live copy restates C §6's method. World_v2 §5 is a record; the roadmap's exit and
  the foundations plan's crate are row 59.
- **Row 58** (requirements by step): tile §11 restated checklist items and is now a link. Client §12 is kept: its
  step 2 and 8 items (bricks, picking, HUD, `net_client.gd`, a post-`imagine` frame) are not in `checklists.md`.
- **Row 50, the roadmap's band-aid list** already cites B §4.1 and names the marked files the lint needs; left.
  B §11.1's 2c bullet is a migration record; left.
- **Row 52, `inference_gateway.md` §1's** "`maxim-through-adapters` gains `engine.adapters.inference`": left, as IG
  has no slack and the line places its own module.
- **Row 54, `fire_solid.md` §1.3 and §5.1** state limits and catalogue rules of their own, not the gate contract.
- **Row 55, `boundaries.md` §10's B-7 row** still names `maxim_experiments`; it is enforcement, left for the owner.
- **O8** is not copied: "Only the applier and the physics laws hold the write handle" and "a shipped build doesn't
  copy frames at exit" contradict the built window (four owners; `CellStore.writing` copies in every build).

Word counts (5c054f6 → now): `boundaries.md` 13,982 → 10,598; `npcs_and_sem.md` 23,492 → 16,002;
`tile_and_client.md` 5,909 → 5,356; `verify_harness.md` 1,252 → 1,243; `inference_gateway.md` 2,509 → 2,507;
`inference_placement.md` 4,886 → 4,607; `sem_stimuli.md` 5,996 → 5,862; `fire_solid.md` 5,972 → 5,949;
`architecture.md` 2,792 → 2,742; `roadmap.md` 6,976 → 6,825; `world_model.md` 4,666 → 3,480;
`ip_and_licensing.md` 1,874 → 1,872.

## Step 3e: world and physics

| Row | Contract | Owner section | Copies now links | Added to the owner |
|---|---|---|---|---|
| 59 | Phase 1 exit | `roadmap.md` Phase 1 "Exit" | `tile_and_client.md` §6 and `fire_model.md` §7 (one lead line each; their crate text stays, as Phase 2's); `foundations_plan.md` §2's "set a crate on fire" sentence; `checklists.md` step 8's exit-script bullet (the heading is unchanged) | nothing |
| 60 | Band gate | `world_model.md` §3 | tile §6.3 item 7 (the rule; the script's 2× stays as its own margin); `verify_harness.md` §4; `sem_stimuli.md` §2.3; `npcs_and_sem.md` §2.1; `checklists.md` (plume item) | ruling 60's second rule (the operating point clears the band by a margin); "This replaces v2's outcome-margin rule" dropped |
| 61 | Convergence predicate | `verify_harness.md` §4 (rule `world_model.md` §1.1) | tile §6.3 item 8 (the tol/4 allowance dropped; its tolerances stay) | nothing |
| 62 | Material files and split | `fire_solid.md` §5.1 | `fire_model.md` §9.1 (the table, "v0 fixtures migrate", the landing order; the refusal list stays, as §5.1 cites it); `world_model.md` §8; tile §5.1 | FM §9.1's "u8 ids stable", "each reacting component with a formula or elemental mass fractions", "transitions", "void fraction, bulk density" |
| 63 | Ledger lines | `fire_solid.md` §5.4 where it speaks | FM §9.2: `Δ(skins)` now stays, linking FS §5.4 | nothing; tile §5.4's `unreceived` marked for the flames design |
| 64 | Object–grid coupling | `fire_solid.md` §1.1, §3.1 | FM §2.1's coupling row; FM §2.2's heat bullet | nothing |
| 65 | Pyrolysis rate law | `fire_solid.md` §4.2 | FM §3.1 (the bullet and the paragraph); tile §5.2's 6c; WM §3's pyrolysis row | nothing |
| 66 | Extinction | FS §4.4 for the cone; FM §4.3 otherwise | none deleted; WM §3's O₂ paragraph marked for the flames design | nothing |
| 67 | R0, R1 grading | `fire_solid.md` §4.5–§4.6 | FM §6.2's R0 and R1 rows (graded and pass columns) | nothing |
| 68 | Radiation | FM §4.4 (emission), SS §2.3 (body side) | tile §2.1's point source and face-to-body exchange | nothing |
| 69 | Body, core temperature, tags | `sem_stimuli.md` §3.1, §2.2 (and §3.3) | tile §8's "no metabolism"; FM §5.1's core-temperature line and two ANALOG tags | nothing |
| 70, 76 | Push path, `world_set_axis` | `sem_stimuli.md` §4.4 | `boundaries.md` §4.3; `npcs_and_sem.md` §7.2; FM §5.1 (OD-C10) | B §4.3's root-only and OD-C10 line, verbatim |
| 71 | Region ownership | FS §1.3 for objects; otherwise marked | FM §2.2's "cells ∪ objects"; `architecture.md`'s two "removes it/both" gaps marked for the flames design | nothing |
| 72 | Thin-feature rule | `world_model.md` §1.1 | `architecture.md` (two lines); tile §1.1's slats line | the rule (CLAUDE.md's and architecture's words) and FM §10.1's exemption, verbatim, citing FS §1.3 |
| 73 | Field registry | `boundaries.md` §9.1 | SS §3.1's citation (was `world_v2.md` §2.5) | nothing |
| 74 | B-13, lab-only sensors | `boundaries.md` §4.4 | N §7.1, §7.3; tile §8, §10; FM §5.1, §5.4; FS §2; SS §6.1 | N §7.1's "(a probe, a lag)" and §7.3's "(an instrument may carry it)" |
| 75 | Stimulus split | `sem_stimuli.md` §1 | FM §5.1 (intro and leak tests) | nothing |
| 77 | Tick, physics step | tile §6.1 (T3) | SS §2.2 | nothing |
| 78 | Reconstruct, decide, integrate | `world_model.md` §3 | `roadmap.md` Phase 1 (the fuel bullet's citation); `architecture.md` | nothing |

X22: the roadmap's clinic line now reads "the alley", with the clinic's timing D27's. Left: "a cell's burn rate must
estimate the integral" (against FM §0.3), D26's "fuel recession and pyrolysis" moved to Phase 2 (against FM §10.1)
and the 6 s turn-length question (against T3); no ruling covers them.

Skipped or left:
- **Row 77, `npcs_and_sem.md` §9's table** keeps its values: its lead line already links T3, and the values are world
  config's own fields (ruling: N §9 owns world config). `foundations_plan.md`'s T3 row is a plan list.
- **Row 59, `long_term_features.md`** line 25's "light a built fire" contradicts line 26; its fire row is hands off.
- **Row 62, FM §9.1's variants row** ("the only knobs an imagined object may set") is not copied: FS §5.2's spec v1
  also sets geometry.
- **Row 63, SS §3.1's "unreceived share"** and tile §2.1's derived flux numbers stay.
- **Row 65, WM §3's ignition and ablation rows** are FS §4.4 and §4.3's in substance, but not row 65's contract.
- **Row 70, the pinned frame** in N §7.3 and B §4.2 stays; SS §6.1 supersedes it by name.

Word counts (5c054f6 → now): `roadmap.md` 6,976 → 6,822; `architecture.md` 2,792 → 2,743; `tile_and_client.md`
5,909 → 5,334; `fire_model.md` 5,991 → 5,392; `fire_solid.md` 5,972 → 5,967; `world_model.md` 4,666 → 3,542;
`verify_harness.md` 1,252 → 1,241; `sem_stimuli.md` 5,996 → 5,874; `npcs_and_sem.md` 23,492 → 15,908;
`boundaries.md` 13,982 → 10,563; `foundations_plan.md` 2,500 → 2,471; `checklists.md` 7,354 → 7,227.

Fixed on review of step 3e: `fire_model.md` §3.1 keeps the DP-S1 (18 ulp) and FDS `REFERENCE_TEMPERATURE` sentences.
They are the rationale for the cutoff, not a copy of the law. Open: boundaries §4.3 and npcs §7.2 said a push "needs no
log record" because it was "a pure function of the agent's pinned frame". `sem_stimuli.md` §6.1 supersedes the pinned
frame, and §4.4 doesn't say whether a `BoundFrame` push needs a log record. The claim was dropped with the pinned frame
and not restated.

## Round 1 fold

| Finding | What moved or changed | From | To |
|---|---|---|---|
| S2, A6 | "v2 §2.1 stands" became world_model's own sentence; v2 is provenance | `world_model.md` §2 | `world_model.md` §2 |
| S2, A6 | "A `Region` keeps its authored footprint …" bullet, verbatim | `world_v2.md` §2.4 | `world_model.md` §5 |
| S2, A6 | "Topology has one choke point. Every material change goes through `set_material`, which bumps a `topology_version`." verbatim | `world_v2.md` §2.2 | `world_model.md` §7 |
| S2, A6 | "v2 §8 stands" became world_model's own sentence (the grammar is `client_rendering.md` §4.1's) | `world_model.md` §8 | `world_model.md` §8 |
| S2 | Actor-id allocation bullet and `TimeAuthority` bullet, verbatim; the §5.3 table cells point "below" | `realtime_lanes_coop.md` §4.2, §5 | `boundaries.md` §5.3 |
| S2, A6 | Handshake citation repointed | `ip_and_licensing.md` §4 | `boundaries.md` §5.3 |
| S2, A6 | Superseded banner added (the only edit) | — | `world_v2.md` header |
| S1 | "`seq` is an integer in `[0, 2^31)` and must increase within a session (W-F5)", verbatim, as a bullet after the intent record (inside the record's item it broke the `intent_record.fields` marker) | `realtime_lanes_coop.md` §7 | `boundaries.md` §6.2 |
| S4 | `boundaries.md` §9.3's CC3 paragraph, verbatim less its last sentence (the owner bullet already says it); both design copies became a link | `boundaries.md` §9.3, `npcs_and_sem.md` §8.1 | roadmap Phase 3 ("Ids") |
| S5 | Tier-A table cells restating OD-A2, OD-A3, OD-A7, OD-A17, OD-A18 replaced by the ids; Overdrive-side text kept | `npcs_and_sem.md` §6.1 | roadmap Phase 3 rows |
| A7 | Status amended: boundaries O24 (ruling 49), O8 (50); npcs O11a (41), O14 (45); world_model D26 (59); tile "O23, O24, O31" (49), "D26–D28" (59); fire_model "ruled 2" (61). Each header's status sentence now names the docs-contracts rulings | `rulings.md` | `decisions/*.md` |

**Skipped, and why.**
- `world_v2.md` §2.1's table and bullets: they place solids in "rig cells" at "the rig's cell", and argue from "when
  the rig changes" and "splits the rigs", which D20 and `world_model.md` §1 retired ("The rig profiles stop deciding
  physics"); "An air cell's temperature becomes its zone's" conflicts with world_model §8 ("Air cells' `temperature_c`
  stays cell temperature"). No ruling covers either. Not copied; for the owner.
- `world_v2.md` §2.2's third sentence ("Zone volumes, gaps and the volume profile update incrementally, in the same
  substep as the change") conflicts with world_model §6 ("Topology work is batched once per physics step, not per
  substep"). Not copied.
- `world_v2.md` §8, still live and unowned: the save bullet ("tied to one rig's cell size", the same D20 conflict;
  derived fields checked against a stored digest; the "heavy mode" test); the six golden fixtures (unknown optional
  and required channels), whose owner, `client_rendering.md` §4.2, has no word slack; "the intent log header hashes
  the registry", absent from `boundaries.md` §6.3. Not copied; for the owner.
- Provenance, left: `boundaries.md` §7.1 and `npcs_and_sem.md` §6.3 (supersession notes on lanes §4.1), `npcs_and_sem.md`
  §9's world config ("from"), §11.2's supersession table, `tile_and_client.md` §6.2 (lanes §8 only names the stepped
  host mode as a PR item; there is no text to copy), `checklists.md` items on realtime §7 (to-do items).
- Excluded: `sem_stimuli.md` §7.1's "`world_v2.md` §2.6" (another session's PR). Not handled: `verify_harness.md` and
  `checklists.md` cite "`world_v2.md` row 2" for the exact work counters.

## Delta 1 fold (author's claims; the delta reports set the statuses)

Correction to "Round 1 fold" above: its "Not copied; for the owner" about `world_v2.md` §8 is out of date. The author
homed all three items in 7cfea02: the registry hash in `boundaries.md` §6.3, the save's grammar and digest in
`world_model.md` §8 F5 (less the D20-retired rig cell size), and the heavy-mode test and the six fixtures in
`checklists.md` steps 9 and 7.

| Finding | Change |
|---|---|
| Wire D-S1 | `realtime_lanes_coop.md` §5's joins-and-leaves bullet copied verbatim into `boundaries.md` §5.3 |
| Wire D-S2 | the `seq` range moves to `tile_and_client.md` §3.3, as every client message's; `boundaries.md` §6.2 links |
| Wire D-S3 | this correction |
| Arch NEW-1 | ruling 3 is `sem_stimuli.md` §11.2's Q8; ruling 5 is the first item of `checklists.md` step 5a |
| Wire D-N1 | F5's sentences reordered so "refused too" follows "refused" |
| Wire D-N3, Arch NEW-8 | the banner drops its citation of `world_model.md`'s status line |
| Arch NEW-2 | the registry's intro states the marker's `not:` and the row's count |
| Arch NEW-3 | numbered lists of rulings are caught |
| Arch NEW-4 | a design without sections is exempt only by a banner in its lead paragraphs |
| Arch NEW-5 | a stale exclusion, a span both named and excluded, and any keyword but `not:` fail |
| Arch NEW-6 | tests for the table header row and for the registry being out of scope; the dead guard is gone |
| Arch NEW-7 | the docstring says a list owner is its first item |
| Wire N1 | `fire_model.md` §10.1's row links `world_model.md` §1.1's exemption |
| Wire N2 | the plan's base reads 5c054f6 |
| Wire N5 | npcs' bare §6.6 reads "this document's §6.6" |
| Wire N6 | `boundaries.md` §7.1's `dt_ticks` links `npcs_and_sem.md` §2.1 |

Left, with reasons:
- Wire S2's `sem_stimuli.md` §7.1 citation of `world_v2.md` §2.6, the ledger exchange, which no live owner holds:
  `phase1/sim-clock` (#36) edits that phrase. Trigger: the first main merge after #36, then the ledger rule moves to a
  live owner.
- `world_v2.md` §2.1's rig-cell text and its air-cell temperature, and §2.2's per-substep topology update, are history.
  D20 and `world_model.md` §6 and §8 replace them, so nothing is copied.
- `verify_harness.md` and `checklists.md` step 5a cite "`world_v2.md` row 2" for the exact work counters. That row is a
  plan step in a superseded design, so a citation of it is provenance; 5a builds the counters.
- Wire S3's remainder and Arch A7's remainder are the owner's: CLAUDE.md's "Reconstruct" paragraph restates
  `world_model.md` §3; the decision records repeat a ruling that several designs restated, as moved; an Owner cell is
  `—` where the source table had no column for it; CLAUDE.md says such tables live in "reviews/ and indexes", and
  `decisions/` is an index.
- Executor N5 (the step 4 commit said 42 tests where 43 were collected) is history in a commit message. Executor N6
  (a signature matches only with its exact spacing) is the lint's stated limit.
- Wire N3 (headers that say "uncommitted") and N4 (tile §3.2's heading names `kindle`) are left as they are.
- Wire D-N2 (fire_model §12's "in 6.4" against #34's "6.1") is main's text, inherited.
