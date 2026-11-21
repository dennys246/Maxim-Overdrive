# A creator marketplace for licensed IP

Status: **note, not a reviewed design.** Written 2026-11-21 from the owner's stated goal: if the game gains traction,
artists and game developers sell or license their own IP (characters, worlds, stories, objects) to be embodied in
Maxim Overdrive. It extends `docs/design/ip_and_licensing.md`, whose §5 (the cost of running a marketplace) moved
here word for word as §3. Nothing in it is built before the marketplace decision (roadmap Phase 8). Before code it
gets a design review with Bio-faithful integration, Trust boundary, Wire integrity and Determinism and replay as
lenses, and the contract terms in §7 go to a lawyer. The legal points are a research pass, not advice.

## 1. Two marketplaces, not one

`ip_and_licensing.md` plans for creators selling **objects**: specs a player places, protected by content ids,
signatures and takedowns. The owner's goal is wider: creators licensing **IP to be embodied**, so a character
becomes a Maxim agent that lives, remembers and acts in Maxim Prime. The two differ in kind:

| | Object marketplace | IP marketplace |
|---|---|---|
| What is sold | A spec: geometry and materials | A character, world or story, plus the right to adapt it |
| Where it lives | The spec store and the world's cells | The spec store, and an agent's memory, which keeps changing |
| What the creator worries about | Copying | Copying, and what their character says and does |
| Who carries the risk | A host of user uploads (DMCA safe harbour) | Closer to a licensee or distributor: contracts carry the risk |
| Nearest precedent | Fab, Second Life | Roblox License Manager |

The IP marketplace needs everything the object one does, plus §4 to §7.

## 2. Decisions in brief

1. **The object marketplace's machinery is the base.** Content-addressed specs, provenance records and licence
   references (`ip_and_licensing.md` §6) carry an IP licence as well as an object licence. Nothing in §6 changes for
   this.
2. **A licence covers the agent, not only the spec.** A licensed character's memories, and memories derived from
   them, carry the licence reference wherever they go, including into Maxim (§6).
3. **Contracts are the main protection,** not the safe harbour: creators warrant ownership, indemnify the studio and
   grant embodiment rights explicitly (§7).
4. **First-party IP is settled first.** No third-party licence is signed until the studio owns Maxim Prime's IP
   (`ip_and_licensing.md` §7, "Who owns first-party IP") and the WashU OTM question (roadmap Phase 8) is answered.

## 3. What a marketplace would cost

Recorded so the decision is made with numbers. Nothing here is built before that decision.

- **Copyright takedowns (DMCA §512):**
  - a designated agent registered with the Copyright Office, renewed every three years;
  - expeditious takedown, and a counter-notice process;
  - a published repeat-infringer policy that is actually enforced.

  Taking a cut puts the safe harbour at risk: it is lost by a provider that receives a financial benefit directly
  attributable to infringement it has the right and ability to control.
- **EU DSA:** notice-and-action and statements of reasons. As a marketplace, Art. 30 seller verification: collect
  and verify identity and payment details, keep them six months after the relationship ends, and show the seller's
  name and address on listings. The small-enterprise exemption's scope is unverified.
- **Payouts:** identity checks, tax forms (1099s, DAC7), sanctions screening, chargeback reserves (Roblox holds 30
  days, Valve 90). Use a payouts provider or merchant of record (Stripe, Tebex, Xsolla, Paddle).
- **Steam:** in-game purchases go through Steam's microtransactions API. Crypto and NFTs have been banned since 2021.
  Cash-out or player trading of creator items is a delisting risk.
- **Curation and moderation:** the 2015 paid Skyrim mods were pulled in about a week (25% creator share, paywalled
  free mods, stolen content, no curation). Bethesda's vetted Verified Creators survived.
- **Unit economics:** Rec Room shut down in June 2026 with creator revenue up 70% a year. It kept about 30¢ per
  dollar after the store and the creator.

The precedents that fit best:
- **Roblox License Manager**, for a franchise licensing IP to creators: the rights holder sets the revenue share and
  scope, terms lock once used, and the platform detects use.
- **Second Life's** next-owner modify, copy and transfer flags, checked on the server.
- **Fab's** split of Personal and Professional tiers by the buyer's revenue, with old purchases grandfathered.
- **W3C ODRL 2.2** for machine-readable licence records.


## 4. What embodiment adds

1. **Behaviour is part of the IP.** An LLM-driven character can say or do things that are off-brand or harmful
   under the licensor's name. This is the first question a rights holder asks. The licence carries **character
   bounds** the licensor sets (topics, actions, relationships it will not enter), checked before an NPC's intent
   reaches the world, like the IP gate (`ip_and_licensing.md` §3). The intent log already records why an NPC acted,
   so a licensor's complaint can be answered from the record. Whether bounds are enforced as hard refusals or as
   prompt guidance is a design question for the review; only hard refusals are a promise.
2. **Approval before release.** A licensor reviews the character's seed memories (the cradle) and a sample of play
   before the character goes live, and again after a large change. Roblox License Manager's terms lock once used;
   the same rule applies to a character's bounds.
3. **Revocation reaches memory.** `ip_and_licensing.md` §7 asks what a takedown does to replays. With an embodied
   character the harder case is memory: when a licence ends, what happens to that NPC's memories, and to other NPCs'
   memories of meeting it? Candidate rules, per licence tier: the character is retired and its memories deleted;
   other agents' memories of it are rewritten to an anonymous stand-in; or memories formed while the licence held
   survive, unnamed. The rule is chosen as a design, then written into the contract so it can be enforced.
4. **Adaptation is a separate right.** Book to world (`docs/book_to_world.md`) turns a book into a world, which is a
   derivative work. A third-party book needs adaptation rights, not only embodiment rights. The roadmap's order,
   a public-domain book first and then the owner's novel, needs no third-party rights.
5. **Likeness and voice.** If creators license *themselves* (face, voice, persona), right-of-publicity and
   voice-cloning laws apply as well as copyright, for example Tennessee's ELVIS Act (2024). That needs consent
   terms of its own, separate from a character licence.

## 5. The licence record

The licence reference in `ip_and_licensing.md` §6 holds one value today, `first-party/all-rights-reserved`, and the
reader refuses unknown values. An IP licence adds a grant record, signed by the store (`ip_and_licensing.md` §4,
"Signatures, not encryption"), with at least:

- the licensed work, its creator, and the spec ids and cradle it covers;
- scope: embodiment, adaptation, derivative play, and whether the character may appear in other creators' content;
- character bounds (§4 item 1) and the revocation rule (§4 item 3);
- term, territory and revenue share, set by the rights holder as in Roblox License Manager;
- whether memories derived from the work may leave the world (§6).

W3C ODRL 2.2 is the candidate format (`ip_and_licensing.md` §5's precedents, now §3 here). The grant record is
loaded like every other record: closed key sets, unknown values refused.

## 6. The Maxim side

NPC memory lives in Maxim, not in this repo, and Maxim can export, merge and share memory through its hivemind and
Oasis bundles. Maxim's signed bundle format v2 carries a signed SPDX `license` field; published Oasis bundles use
CDLA-Permissive-2.0, and a `--release` composition whose inputs carry a non-permissive licence only warns. There is
no licence-compatibility logic by design (`docs/plans/oasis_entry_index_v2.md` in Maxim, item (d)).

So a licensed character's memories could be merged into another agent, or into a permissive bundle anyone may reuse,
with only a warning. For a licensed character that is a breach the design allows. What Maxim needs, before any
licensed character exists:

- a licence class meaning "licensed: never leaves the world it was granted for", carried on memory rows derived from
  a licensed cradle, through consolidation;
- export and merge refuse that class rather than warn;
- a test that a licensed character's memory cannot reach a published bundle by any path.

This is Maxim work, to be filed there as an issue; it is recorded here because this game is its first consumer.

## 7. Creator contract terms (for the lawyer)

- **Warranties and indemnity:** the creator owns what they license, it infringes no one, and they indemnify the
  studio if it does.
- **The grant:** embodiment as an AI agent, memory formation, derivative play, adaptation where it applies, and
  the studio's right to change the character to fit the world.
- **Bounds and approval:** §4 items 1 and 2, and who decides a breach of bounds.
- **Revocation:** what ends a licence, and the memory rule of §4 item 3.
- **Likeness and voice consent,** where it applies (§4 item 5).
- **Moral rights:** EU creators may have rights that cannot be waived, such as integrity of the work, which an
  agent's behaviour could engage.
- **Structure:** whether the marketplace sits in its own company, so payout and takedown liability stays away from
  the game.

## 8. Open questions

- Hard-refusal character bounds: can they be enforced on an LLM-driven agent at a cost the game can carry?
- Revocation and replays together: is a replay bound to the licence in force when it was recorded
  (`ip_and_licensing.md` §7), and does the same answer cover memory?
- Does the DMCA safe harbour cover any part of a curated, revenue-shared IP marketplace, or none of it?
- Style licensing (`ip_and_licensing.md` §7) and character licensing may meet: a creator whose style seeds other
  characters.
