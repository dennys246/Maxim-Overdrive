# The status check and its fold: `torch_pilot.md` (2026-11-22)

**The check.** Two readers set the status of round 2's findings from the tree at 94e85fe, the practice PR #27 used,
at the owner's request:
- `status_wire.md` covered Wire integrity;
- `status_five_lenses.md` covered Executor, Physics, Architecture, Determinism and Bio-faithful.

They raised no BLOCKER.

| Reader | fixed | deferred | rejected | open | new SHOULD-FIX | new NIT |
|---|---|---|---|---|---|---|
| Wire | 10 | 1 | 0 | 2 (W2-N2, W2-N6) | 1 (W3-S1) | 2 |
| Five lenses | 35 | 4 | 0 | 4 (P2-S6, A2-S1, A2-N2, D2-N2) | 4 (X3-1 to X3-4) | 1 (X3-5, four items) |

**The author's correction, first.** TP6, as recommended by the author and ruled by the owner, deletes `sources` at
6.1b. Today's `douse` (the record kind of `Extinguish`) removes a source, so that deletion takes `douse`'s subject too.
The recommendation didn't say so. The fold states it in §9.4: `douse` is applied and fruitless until 6.2's water sink
(D-N3), a Known gap. The owner confirmed TP6 with that consequence on 2026-11-22: "TP6 stands, go ahead".

**The fold (author's claims; no reviewer has read them):**

| Id | Change |
|---|---|
| W3-S1, X3-2 | §9.4: `source_exposure` goes too, as one recorded break with the pilots member. §10 routes sim_core §1, §3, §6, §9 and boundaries §5's writer rows to 6.1b, and names the heat-source tests' fate; checklist 6.1b carries it |
| X3-1 | tile §3.2: 5b's interim target rule restored (cell regions only), and §3's rule from 6.1b. fire_solid §2: the `kindle` exception takes effect from 6.1b and links `torch_pilot.md` §3 |
| X3-3 | §3: a cell region with no solid cell left is no candidate; craters are a Known gap (§7), fruitless in Phase 1 |
| X3-4 | tile §6.4's control row: the gate closes at 6.1b. Roadmap Phase 2: the crate's bar is restated by the 6.2 design |
| W2-N2, W3-N2 | tile §2.2: `centre_mm` is rounded half to even; a tick past 2³² − 1 is outside v0, with the refusal named by step 7 |
| W2-N6 | tile §2.2: one row per live pilot |
| P2-S6 | §9.2: a strict `<`, or both differences zero |
| A2-S1 | roadmap line 39: "pass the exit's gates" (`torch_pilot.md` §9.2) |
| A2-N2 | checklist 6.1b: the query's layer and a cross-act ranking case |
| D2-N2 | checklist step 9: saves at a cut and between end tick and removal |
| W2-S5 (test) | checklist 6.1b: a `leave` in the `kindle`'s own tick |
| W3-N1 | client_objects §1: the target rule's source is `torch_pilot.md` §3 |
| X3-5 | "under TP2"; "0.5 m-wide plank"; fire_solid §2's link. fold2's "back to 4" was true at 8a912ba; 94e85fe raised it to 6 |

**Not folded, reported to the owner:** fire_solid §5.4 says "empty tables add no bytes", which contradicts sim_core
§9's framing. It predates this branch, so it belongs to fire_solid's next revision.

**Word budgets against origin/main:**

| Document | Words |
|---|---|
| tile | 5,408 → 5,404 |
| fire_solid | 5,964 → 5,962 |
| fire_model | 5,449 → 5,427 |
| client_objects | 5,176 → 5,161 |
| sim_core | 3,770 → 3,770 |
| sem_stimuli | 5,898 → 5,898 |
