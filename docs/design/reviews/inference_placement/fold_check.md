# Fold table, short delta check (ed55c2f → the next commit)

This table records the author's claims. The findings come from `check_wire_integrity.md` and `check_other_lenses.md`.
Their statuses for earlier findings stand as written. A reviewer sets the statuses of the claims below (O25).

| Finding | Claim |
|---|---|
| B2/D7 (open): copy includes in-flight replies | IP §4.2: the copy is the cache as it stood at the save's header snapshot, and the occurrence counters are saved |
| N-B1 taint's second leg covers only hearing | IG §6: perceived by any channel; an NPC-authored world string carries its author's taint |
| N-S1 gateway crash never cools | IP §2.6: a crash during an attempt is a placement fault |
| N-S2 start timeouts under load mark a placement down | IG §4: a start timeout never counts; only an exit before `ready` does |
| N-N1, C-S3: `single`, wait or end | IP §2.4: one rule for every policy (wait if a candidate is only cooling, else `unavailable`) |
| N-N2 phantom interruptions | IP §6.2: OPEN |
| N-N3, C-S4: speaker identity across sessions | **open: needs the owner's ruling** |
| D-S1 (open): clearing rests on agent provenance | IG §6: OPEN |
| D-6 (open): transport timeout relation | IG §4: (1 + unswitchable retries) × `transport_timeout_s` ≤ `call_ceiling_s`, checked at load |
| D-8 (open): numbers not in this tree | IP §6.3: states the numbers, citing each source |
| S-3 (open): real parallelism | checklist, deferred to Phase 4 |
| S-5 (open): prompt layout | roadmap OD-A14: the ask to B1 |
| N-3 (open): per-NPC placement-change meter | B5 row |
| C-S1 stop reasons not closed | IG §5: a closing row (`ok`) |
| C-S2 rerun read point | IP §4.2: keyed to the log's terminal record |
| N-b validation at delivery | IP §2.6: `truncated(prefix, reason=validation)` |
| N-c, N-d ownership of `failed(empty)` and `endpoints.yaml` | IP §2.6 cites §2.7; IP owns two files, IG owns `endpoints.yaml` |
| N-e "never `LLMRouter`" | boundaries §8.1: "never calling" |
| N-f guest-string list | IG §6 points to npcs §6.6 |
| N-g `open` field sources | IG §3: placement `id`, `transport_timeout_s` from `health` |
| N-h branch occurrence indices | as B2 |
| D12 (open) registry row | boundaries §5.3: an "inference gates" row |
| N4 (round 1, open) outcome and receipt words | IP §2.6: two vocabularies, stated |
| N-i dangling until merge | #29 has merged (B36 resolves). The citation of #25's lesson stands until #25 merges, and IP §6.3 now carries the numbers. |
| N-j decision table inside a design doc; checklist growth; OD-A14 `thinking` | OD-A14 and the draft now include `thinking`. The decision-table placement is a question for the owner and for `phase1/docs-contracts`, whose restructure covers every design document's §0. The checklist is a plan, so the design no-grow rule doesn't apply to it. |
