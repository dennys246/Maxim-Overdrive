# NPC inspector: the owner's rulings (2026-11-27)

The author put v3's §10 questions to the owner, plus the proposal in `fold_delta.md` to end the paper rounds, each
with a recommendation where the author had one. The owner answered each through a multiple-choice prompt on
2026-11-27. Every ruling took the author's recommendation except NI6, which had none.

| # | Question | Ruling | What it changes |
|---|---|---|---|
| NI1 | End the paper rounds at v3 | Yes, under B33. This acceptance is the recorded overrule `code_review.md` ("When the rounds stop") requires. Mechanism findings move to the build steps §9 names | `npc_inspector.md` header |
| NI2 | This branch and step 4 | Merge before step 4, as the owner chose for PR #81 on 2026-11-26 | the merge order |
| NI3 | Scope | §1–§4 and §9's tests enter `phase1/agents`' checklist; the viewer waits | `npc_inspector.md` §1 tags; `plans/checklists.md` at that step |
| NI4 | A record failure | A gap for that agent while the world goes on; never stop the run | `npc_inspector.md` §3, "Failure never stops the world" |
| NI5 | The information rules | The deep view is earned in the fiction: a diegetic tool with costs. Outside it, players see behaviour only | `npc_inspector.md` §5 |
| NI6 | Handing a save to another person | Another speaker's words are stripped from a save handed to someone else, unless that speaker consented. A single-player save is shared as it is | `npc_inspector.md` §5, §8; filed as an `O` decision after step 4 |
| NI7 | Audiences | Both, developer first: a developer and science view now, a player view later under NI5 | §7's views, at the viewer's build step |
| NI8 | The ethics framing | Witnessing a life, not dissecting one | §7's views, at the viewer's build step |
| NI9 | The viewer | Godot first, under this contract; a browser view only after its own transport design | none: v3's §7 already holds this |

**Still open, for a reviewer.** No reviewer has read v3, so the claims in `fold_delta.md` carry no reviewer status
(O25). With the rounds ended, `phase1/agents`' first review round sets them. These rulings decide nothing about
whether a fold is right.

**Not yet in the decision logs.** NI2 to NI9 change contracts that other documents own (NI6 binds the world log's
speech and the audit record's guest text). The decision files stay frozen until step 4
(`plans/next_steps/4_records_build.md`), so each ruling is filed as an `O` decision after step 4 merges, and this table is the record until then.
