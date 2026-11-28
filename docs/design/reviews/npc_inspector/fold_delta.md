# NPC inspector, delta-round fold (v2 to v3): the author's claims

These are the author's claims, not statuses (O25). The delta round found no new BLOCKER in any lens. Under the
charter's stop rule (CLAUDE.md, "Review finds; it doesn't design"), the author proposes that the paper rounds end at
v3. The owner's acceptance would be the recorded overrule. Mechanism findings go to the build steps: the Determinism
delta already deferred D2-S6, D2-N1 and D2-N2 itself.

**Round-1 statuses the delta reviewers set:** 70 fixed, 1 deferred (Bio S9, with step 4's merge as its trigger) and
4 open (Architecture A3; Wire F5 and F9; Trust TB-S6 in part, and TB-N2). v3 addresses the four open ones as
follows:
- A3: §6 and §8 name `boundaries.md` §7.1's contents list.
- F5: §7 states the join honestly and §8 lists the key disagreement.
- F9: §8 adds the bug-report exporter, the receipt key, the stage-1 receipt hole and B5.
- TB-S6 and TB-N2: §5 now has §10 item 4 as a question, and §6 says evidence is single-player or consented.

**Two corrections to round 1's fold table.** The Wire delta found two of the author's claims overstated:
- F3: v2 didn't carry `(actor, seq)`.
- TB-N4: v2's `stimulus` row stored receptor and site.

v3 now says the reader resolves receptor and site from the bindings digest, and the receipt key is listed in §8.

| Finding | v3 section | Author's claim |
|---|---|---|
| Bio D1 | §6 "Where it is aimed", §9 | Aimed at OD-EA's `StepOutput` and `api.on()`; the EVENT seam is cited as the reason, not the target; pushback 1 dropped, and the wall-time facts become evidence for the world-clock plan |
| Bio D2 | §2 table and "Four channels" | `thought_state` is host bookkeeping; `stimulus` values are input and its receipts host verdict |
| Bio D3 | §6 "Values compute on wall time" | Salience fed a wall `now`, energy recharge, retention, valence stamp, each cited. Verified: read `salience_map.py:222-227` |
| Bio F1 note | §6 "Consumers" | Quoted whole; direct only once `readout` carries credit values |
| Arch D1 | §4, §9 | Replay comparison is a test under `tests/`; replay never reads the record |
| Arch D2 | §2 `write_ref`, §8 | Host-derivable key (segment, settle tick, canonical index); the audit record keyed the same; join test |
| Arch D3 | §2, §8 | Per-segment on/off only, as never-refused metadata; gap reason `off` removed |
| Arch N1 | §2 `stimulus` | The whole BoundFrame, by link |
| Arch N2 | §4 | Truncation lives in the writer's module |
| Arch N3 | §7 "Which UI" | The gate's output is a declared `Format` owned here, its fields set at the viewer's build step |
| Arch N4 | §10 item 8 | Cites the owner's 2026-11-26 choice for #81, marked not yet recorded |
| Arch N5 | §2 opening, `write_ref` | Count dropped; `stimulus` named as a check copy |
| Wire N1 | §2 "On replay", §8, §9 | Per-tick values against the bound lane; stage-1 receipts get a consistency check; the bound-lane hole goes to §8 |
| Wire N2 | §4 | As Arch D1 |
| Wire N3 | §2, §8 | As Arch D2 |
| Wire N4 | §3 "The lane" | Superseded lanes citation removed. Verified: read `realtime_lanes_coop.md:3` |
| Wire N5 | §7 | As Arch N3; browser views out of contract |
| Wire N6 | §2 `stimulus` | Whole BoundFrame, `events` and `registry_digest` included |
| Wire N7 | §8, §2 | Exporter, B5, receipt key and header class listed; `purged` gap reason |
| Wire N8 | §1, §2, §3, §6, §7 | Codec rule scoped; `mind_record.gaps` registered; "header snapshot"; "thought segment"; tools field in §8; tier wording |
| Trust D-S1 | §2, §8, §9 | Receipts in §6.2's form; stale prefix sentences in §8; schema test for string fields |
| Trust D-S2 | §7 | Godot child-process view in contract; browser views out until their own design |
| Trust D-S3 | §5, §10 item 4 | The invented rule removed; save handover is the owner's question |
| Trust D-S4 | §7, §8 | `write_ref` "not readable" until OD-A15 has a gated reader |
| Trust D-N1 | §3 "Size" | Bytes per segment |
| Trust D-N2 | §2, §8 | O26's list quoted; agent-store ruling put to OD-A15's owner |
| Trust D-N3 | §3 | Stop is per agent |
| Trust D-N4 | §3 | Building can't raise; validation on the record's thread |
| Det D2-S1 | as Wire N1 | |
| Det D2-S2 | §1 tier 3, §3, §8 | Own thread; no barrier-time promise; B5 row with world-log write time on and off |
| Det D2-S3 | §3 "Saves", §8 | Asynchronous close with a complete-to tick in the save header |
| Det D2-S4 | §3, §9 | One batch per tick; drops counted on the simulation lane; reproducibility only with a queue that can't overflow |
| Det D2-S5 | §1, §2 | Stamp is the tick of the change; landing ticks are fields |
| Det D2-S6 | §9 | Reviewer-deferred; v3 also adds the two-order release leg |
| Det D2-N1 | §9 | Structural never-draining test |
| Det D2-N2 | §9 | Plant differs from truth; gated writes folded |
| Det D2-N3 | §3 | `tick_end` last; actor id dropped; canonical order cited |
| Det D2-N4 | §2 | As Arch D3 |
| Exec DE-S1 | §2 stamp column | A stamp per kind |
| Exec DE-S2 | §9 | As D2-N1; timing bar to `phase1/lanes` |
| Exec DE-S3 | as Arch D2 | |
| Exec DE-N1 | as D2-N3 | |
| Exec DE-N2 | as Arch D3 | |
| Exec DE-N3 | as Wire N1 and D2-S4 | |
| Exec DE-N4 | §6 | Sink argument scoped to multi-agent processes |
| Exec DE-N5 | §1, §2 | Both hippocampus sites cited. Verified: read `hippocampus_retrieval.py:216-222`; follow-ups marked proposed |

v3 is 4,499 words, under the 6,000-word limit for a new design. `lint_standards.py` passes.
