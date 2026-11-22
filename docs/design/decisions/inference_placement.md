# Decisions of `inference_placement.md`

<!-- Moved verbatim from `inference_placement.md` §0 at 5c054f6 by phase1/docs-contracts (CLAUDE.md, "One owner
per contract"). A record: rulings are never edited; a new ruling is a new row. Who, date and Owner section come
from the source table where it had those columns; otherwise the date is the ruling's own or its heading's, and
"cites" lists the sections the ruling's text names, which are not necessarily its owner.
Status comes from supersessions and amendments the rulings state, and from the docs-contracts rulings (`reviews/docs_contracts/rulings.md`). -->

| Id | Ruling | Who, date | Owner section | Status |
|---|---|---|---|---|
| O46 | **The host's thinking lane owns placement.** It decides which model serves each request, by function, consent, health, capacity and budget. Maxim's `LLMRouter` is not built on the NPC path, and Maxim's backends are the transports. This argues against Maxim's rule that placement "rides on `LLMRouter`" (§1.2); the pushback is OD-A24. | owner, 2026-11-21 | §1, §2 | live |
| O47 | **The calls run in host-owned inference gateway processes, not in the world server.** O13's "the LLM gateway stays in the host" reads as host-side. | owner, 2026-11-21 | IG §2 | live |
| O48 | **Each function is pinned to its first eligible placement by default; `spill` is an opt-in per function. Load never moves a pinned function (§2.7).** | owner, 2026-11-21 | §2.4, §2.7 | live |
| O49 | **A model on another of the player's machines counts as remote under O18.** | owner, 2026-11-21 | IG §6 | live |
| O50 | **No streaming until Maxim's backends can stream to their caller.** The gateway calls with `stream=False`, and the first word arrives with the whole reply (§6.3). | owner, 2026-11-21 | IG §3, §6.3 | live |
| O51 | **Consent is per speaker and outlives the session.** Taint covers every guest-supplied string, by any channel. | owner, 2026-11-21 | IG §6 | live |
| O52 | **O46 goes to Maxim as a pushback** (OD-A24). | owner, 2026-11-21 | §9 | live |
| O53 | **One gateway process per placement.** | owner, 2026-11-21 | IG §2 | live |
| O54 | **Either the speaker or the save's owner may purge a speaker's words; only the speaker may release them to a remote class.** | owner, 2026-11-21 | IG §6 | live |
| O55 | **A speaker is the guest's persistent identity, not a session:** a key the guest's client keeps, proven at the handshake, so consent, purge and release follow the person across sessions. | owner, 2026-11-21 | IG §6 | live |
| O58 | **Local models first; a hosted model is the player's opt-in (owner, 2026-11-22).** Every model-backed feature, NPCs and imagination alike, is designed for and accepted on local models. A player whose hardware can't run them may opt into a hosted model (Claude or an OpenAI model) through the `third_party` class's existing opt-in and spending cap (IG §6); this ruling adds no mechanism. Open: the minimum hardware that counts as able to run them, a measured budget (backlog B5), and who pays for the hosted opt-in. | owner, 2026-11-22 | IG §6 | live |
| — | Kept by the owner: an `owner_lan` endpoint must have a private, link-local or CGNAT address, and `http://` to one needs `cleartext: true` (IG §7). Load failures wait on the same placement (§2.7). Cache pairing covers only the shared prefix (§4.2). | owner, 2026-11-21 |  | live |
