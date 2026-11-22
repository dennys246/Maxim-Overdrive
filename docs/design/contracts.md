# Contracts: the registry B36's lint checks

Each row names a contract, the one section that owns it, and its kind. The owner section marks its defining block with
`<!-- contract: <name>: <members> -->`, and `scripts/lint_contracts.py` fails when another block in a design, plan,
the roadmap or `architecture.md` holds three or more of those members, or the signature, or when a design holds a
fold or decision table (CLAUDE.md, "One owner per contract"). "Restates at" is how many members one block must hold to count as a copy: three, or one more than the largest
reference outside the owner, whichever is greater (owner, 2026-11-21, round 1 ruling 1). The references that set each
count above three were judged one by one and are listed below, so a reviewer can re-judge them. A copy below a row's
count passes unseen, and so does a contract this table doesn't list: both stay with review (B36). Marker lines don't
count toward a design's word budget (round 1 ruling 2).

| Contract | Owner | Kind | Restates at |
|---|---|---|---|
| `thought_failed.reasons` | `design/inference_placement.md` §2.6 | vocabulary | 3 |
| `truncated.reasons` | `design/inference_placement.md` §2.6 | vocabulary | 3 |
| `receipt.kinds` | `design/sem_stimuli.md` §6.2 | vocabulary | 3 |
| `intent_result.outcomes` | `design/tile_and_client.md` §3.3 | vocabulary | 3 |
| `intent.kinds` | `design/tile_and_client.md` §3.2 | vocabulary | 5 |
| `refusal.codes` | `design/tile_and_client.md` §3.4 | vocabulary | 6 |
| `record.kinds` | `design/boundaries.md` §6.1 | vocabulary | 5 |
| `intent_record.fields` | `design/boundaries.md` §6.2 | vocabulary | 5 |
| `ordering.key` | `design/boundaries.md` §6.2 | signature | 1 |
| `codec.kinds` | `design/npcs_and_sem.md` §6.6 | vocabulary | 4 |
| `server.messages` | `design/client_rendering.md` §4.1 | vocabulary | 5 |
| `client.messages` | `design/tile_and_client.md` §3.3 | vocabulary | 4 |

Not registered yet, and why:
- `agent_failed`'s reasons (`npcs_and_sem.md` §6.6) are written inside one code span, so the lint can't see them
  separately.
- The snapshot channels (`client_rendering.md` §4.2) wait on #31's ruling.
- The log header and the tiers are prose and table text, not code-span vocabularies.

The references that set the counts above three (2026-11-21):
- `intent.kinds` (4): `boundaries.md` §6.2's `kind_rank` ranks the kinds; tile §2.3, §3.1 and §3.3 name the kinds a
  rule or a message carries; `checklists.md` step 5's body motion; `vertical_slice.md` §3's throwaway messages.
- `refusal.codes` (5): tile §6.3's exit script asserts five stage-2 refusals; tile §3.2's `kindle` names the codes it
  produces.
- `record.kinds` (4): `sem_stimuli.md` §4.5's lifecycle table; `boundaries.md` §5.3's gate table and §6.2's log-record
  bullets name the kinds they gate or log.
- `intent_record.fields` (4): `boundaries.md` §5.3's client-frames row and §7.3's cognition rule name the timing fields
  they refuse or strip; tile §3.1's pipeline.
- `codec.kinds` (3): `npcs_and_sem.md` §6.3's lane names the calls it serialises.
- `server.messages` (4): tile §3.3's client table names its replies; tile §3.4's Reply column; `checklists.md`
  step 7's fixtures.
- `client.messages` (3): tile §3.1–§3.2 and `checklists.md` step 5 name the move and kindle messages;
  `vertical_slice.md` §3.
