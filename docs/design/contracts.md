# Contracts: the registry B36's lint checks

Each row names a contract, the one section that owns it, and its kind. The owner section marks its defining block with
`<!-- contract: <name>: <members> -->`, and `scripts/lint_contracts.py` fails when another block in a design, plan,
the roadmap or `architecture.md` holds three or more of those members, or the signature, or when a design holds a
fold or decision table (CLAUDE.md, "One owner per contract"). "Restates at" is how many members one block must hold
to count as a copy: three by default, more for a vocabulary whose members prose names in passing (the intent kinds,
the refusal codes, the messages). A marker lists the members that identify its vocabulary and leaves out words that
other vocabularies share (`imagine`, `speak`, the tick fields). An owner block may name another contract's members.
The counts were set after the lint's first run on the tree, just above the blocks it flagged that were references,
so a partial copy below a row's count passes unseen. A contract another module depends on and this table doesn't list
is still held to the rule, by review (B36).

| Contract | Owner | Kind | Restates at |
|---|---|---|---|
| `thought_failed.reasons` | `design/inference_placement.md` §2.6 | vocabulary | 3 |
| `truncated.reasons` | `design/inference_placement.md` §2.6 | vocabulary | 3 |
| `receipt.kinds` | `design/sem_stimuli.md` §6.2 | vocabulary | 3 |
| `intent_result.outcomes` | `design/tile_and_client.md` §3.3 | vocabulary | 3 |
| `intent.kinds` | `design/tile_and_client.md` §3.2 | vocabulary | 5 |
| `refusal.codes` | `design/tile_and_client.md` §3.4 | vocabulary | 8 |
| `record.kinds` | `design/boundaries.md` §6.1 | vocabulary | 3 |
| `intent_record.fields` | `design/boundaries.md` §6.2 | vocabulary | 3 |
| `ordering.key` | `design/boundaries.md` §6.2 | signature | 1 |
| `codec.kinds` | `design/npcs_and_sem.md` §6.6 | vocabulary | 3 |
| `server.messages` | `design/client_rendering.md` §4.1 | vocabulary | 4 |
| `client.messages` | `design/tile_and_client.md` §3.3 | vocabulary | 4 |

Not registered yet, and why:
- `agent_failed`'s reasons (`npcs_and_sem.md` §6.6) are written inside one code span, so the lint can't see them
  separately.
- The snapshot channels (`client_rendering.md` §4.2) wait on #31's ruling.
- The log header and the tiers are prose and table text, not code-span vocabularies.
