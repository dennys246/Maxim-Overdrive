# NPC inspector, round 1 fold: the author's claims

The author folded round 1 into `npc_inspector.md` v2. This table is the author's claim per finding, not a status:
a delta reviewer sets each one's status from the tree (O25). "Verified" names what the author ran or read; every
other fix is a text change for the delta round to check.

**Shared root.** v1 copied facts the world log and the agent-home audit record already own. Five findings, across
four lenses, trace to that: A1, F2, E-S7, F7 and TB-B1. v2's §2 removes the copies, so the record holds no free text.
That one change carries most of the guest-text and bug-report folds (TB-B1, TB-B2, F10, A5).

| Finding | v2 section | Author's claim |
|---|---|---|
| Det B1 | §1 "by tier", §9 | Invariant split by tier; tier 3 held to a copy budget with a stalled-writer test |
| Det B2 | §9 | Echo double that folds every input into its home; its home digest owned here |
| Det B3 | §3 "The lane", "Failure" | Frozen entries, bounded queue, record lane; failure leaves a gap and a status; stopping the run is in §10 item 4 |
| Det S1 | §2 `gap` | Closed gap reasons |
| Det S2 | §3 "One record per segment" | Per segment, with a parent link; a save truncates; links `inference_placement.md` §4.2 |
| Det S3 | §3 "Crashes" | Whole ticks with tick ends; torn final tick trimmed; read to the last tick complete in both |
| Det S4 | §2 `gap` (`rewound`) | Restart gap names the home's snapshot tick; refused frames excluded |
| Det S5 | §2 table "On replay", §9 | Re-derived or recorded per kind; replay never writes a record and compares deliveries |
| Det S6 | §1 "Its clock" | Stamp is the world-time event, never arrival; test asserts it |
| Det N1 | §3 "The lane", §9 | Record's own order key; hash-seed reproducibility test |
| Det N2 | §3 "Size" | Rotation unit is the segment; reader budgets are contract |
| Det N3 | §2 | No text in the record, so no redaction rewrite in it |
| A1 | §2 | Record holds no memory writes; `write_ref` points at OD-A15's audit record |
| A2 | §2 `stimulus` | Delivered frame content, by link; body frame excluded; clamp noted |
| A3 | §6 "On Overdrive's side" | Names the step-output format change and its owners; own barrier-budget line |
| A4 | §4 | Writer and reader in `simcore.host`; import rule restated to fit |
| A5 | §2 | Moot: no guest text in the record; question 4 removed from §10 |
| A6 | §8 | Save v1 and the gate table listed as proposed owner edits; no bug-report rule of its own |
| A7 | §10 item 7 | Exit-test consequence and #80's terms stated |
| A8 | §9, header | One future owner (a `docs/maxim_upstream/` draft); PR #81 cited as unmerged |
| A9 | §9 | `OD-` id and Phase 3 row after step 4 |
| A10 | §4 | Writing scan replaces the ownership-scan line |
| A11 | §3 | Per segment; on/off in the log header (§8) |
| A12 | §2 table, §1 | Replay split corrected; meters arrive with `phase1/lanes` |
| F1 | §2 `stimulus` | Delivered frame (`sem_stimuli.md` §4.2), not §7.3's pull; noise and transduction stated |
| F2 | §2 | As A1 |
| F3 | §2 | Receipt is `(pid or (actor, seq), kind)` as delivered; valence dropped; stage-2 truth excluded |
| F4 | §3 "The format" | Intent log's pattern; c14n-1, held by others, migrations; tick-rule amendment in §8. Verified: read `sim_core.md` §14 |
| F5 | §7 | Join on `(actor_id, seq)` |
| F6 | §3 | As Det S2 |
| F7 | §2 | Log facts are read from the log, not copied; closed world-time stamp rule |
| F8 | §6, §8 | As A3 |
| F9 | §8 | "What this changes elsewhere" |
| F10 | §2 | As TB-B1 |
| F11 | §4 | One Python gate; every view reads its output |
| F12 | §2 | "Sleep calls" removed |
| F13 | §2, §7, header | Receipts re-derived; writing scan; Origin cited to §5.3; unmerged sources marked; kind names distinct from `record.kinds` |
| TB-B1 | §2 | No free text in the record; text stays in the log and audit record, which O26 already reaches |
| TB-B2 | §2, §5 | Nothing new for a bug report to drop; the log's and the audit record's own rules apply |
| TB-S1 | §2 `refusal`, "Excluded" | Post-gate values only; refusals hold code and length; held reply excluded by name |
| TB-S2 | §7 | Plain-text rule for every view, terminal escapes, planted-markup tests |
| TB-S3 | §3 "Size", §4 | Unconditional gate; budgets are contract |
| TB-S4 | §3 | Bounds equal the codec's; an internal refusal becomes a `stopped` gap |
| TB-S5 | §2 "Excluded" | Closed schema; failures by closed reasons only |
| TB-S6 | §5 | Tiers bind display; confidentiality rule; O54 and O55 |
| TB-S7 | §7 "Transport" | File picker, no listener; any listener uses §5.3's handshake |
| TB-N1 | §2, §9 | Replay compares deliveries; other log joins read the log itself |
| TB-N2 | §2 | No guest text, so no release question |
| TB-N3 | §7 | Purge-can't-recall noted |
| TB-N4 | §2 | Receptor and site come from the binding table; no labels in the record |
| TB-N5 | §1 | No clock for file names |
| BF B1 | §6 | Recast as a question to the EVENT seam (decisions 4 to 6); existing emitters cited. Verified: read `reachy_app_maxim_seams.md:173-175` and `tool_dispatch.py:197` at `b90800e` |
| BF S1 | §1, §6 | The three couplings named. Verified: read `prompt_builder.py:83-90, 217-222` and `hippocampus.py:2549-2554` |
| BF S2 | §6 | Guard depends on OD-EA's digest, covering the touch fields |
| BF S3 | §6 | Clock-free in value; world-clock dependency; rerun of `readout` not meaningful until then |
| BF S4 | §2 "Three channels" | Input, host verdict, recording, and report; provenance is ground truth |
| BF S5 | §2 "When a report has read the recording" | Tool-informed marking, once the host can see it |
| BF S6 | §7 | Michael et al. 2013 is the meta-analysis; Weisberg's qualifiers added |
| BF S7 | §7 "Names and tiers" | Maxim's names with EARN, ANALOG or OPEN tier; in-fiction names for players |
| BF S8 | §1 | Never run Maxim over an agent home |
| BF S9 | §9 | Three pushbacks and a lesson, after step 4 |
| BF N1, N2 | §2 | Comparisons and scopes stated; hedges dropped |
| E-B1 | §2 | As F1 and F3 |
| E-S1 | §3 | As F4 |
| E-S2 | §2 table | As Det S5 |
| E-S3 | §6 | `bio_telemetry.py` and NAc cited |
| E-S4 | §4, §9 | Import rule names the reader; the on/off test runs through a save, load and continue |
| E-S5 | §5 | §5.4's rule joined; the client-premise and line-of-sight claims corrected |
| E-S6 | §3 | As Det S2 |
| E-S7 | §2 | As A1 |
| E-N1 | §5 | `ts` cited to `console/server.py:1872` |
| E-N2 | §2, §9 | Channel per kind in the table; tests named |
| E-N3 | §9 "Stamps" | Stamp assertion |
| E-N4 | §3 "Size" | Rate set by deliveries; budgets at the build step |
| E-N5 | §7 | As BF S6 |
| E-N6 | §10 item 7 | Says it edits `contracts.md` |

**Not folded:** none. The over-budget reports (Trust boundary 3,181 words, Wire 3,424) are kept verbatim.
