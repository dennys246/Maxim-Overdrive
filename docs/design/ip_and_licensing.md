# IP protection, content identity and a possible creator marketplace

Status: **note, not a reviewed design.** It records a research pass from 2026-11-17 and the owner's agreement with its
direction. Before code, it gets a design review like any other architecture change, with Bio-faithful integration,
Trust boundary, Wire integrity and Determinism and replay as lenses.

## 1. Decisions in brief

1. **An IP gate in front of `imagination.spec.place`** ships in the same phase as the LLM caller that feeds it
   (Phase 6). It does not wait for a marketplace.
2. **Content identity is proposed for protocol v0, intent log v0 and save v0.** Every placed object refers to a
   content-addressed spec, with a provenance record and a licence reference beside it. That is cheap before those
   formats freeze and a migration of every save after. It is a proposal for the real-time design's next delta
   round, not settled scope (section 6).
3. **The marketplace is a business decision, not an infrastructure task.** No marketplace code is written until
   players exist and the owner decides to run one. Section 5 lists what it would cost.
4. **No DRM.** Creators are protected by where their content lives, by licences and by takedowns, not by encrypting
   content on the player's machine (section 4).

## 2. Why the gate is ours to build

- **The operator is liable for output.** In *Getty v. Stability* (UK High Court, 4 Nov 2025), Stability, not its
  users, was held responsible for outputs carrying Getty's watermark. A game that turns LLM output into world
  objects is the operator.
- **Provider indemnities don't cover us.** Anthropic's commercial indemnity excludes modified outputs, outputs
  combined with other content, and outputs from customer prompts, and trademark claims are largely outside these
  programmes. A validated, placed spec is both modified and combined.
- **Name blocking fails.** He et al., "Fantastic Copyrighted Beasts" (ICLR 2025), reproduce Mario from "videogame,
  plumber" and bypass DALL·E 3's name block with descriptions.
- **Similar is not safe by default.** Copyright protects expression, not ideas. An energy sword is an idea and stock
  genre material; a specific hilt, colour code and name are expression. *DC Comics v. Towle* (9th Cir. 2015) held
  that the Batmobile is a protected character. A renamed near-copy is the classic way to infringe.

## 3. The gate

It runs on the spec, before `place`, where all imagined content already passes. A rendered-output gate (logo and
character detection) is added only when the game generates images.

1. **A lexicon pass** over name and description, with normalised and fuzzy matching. Sources: Wikidata (CC0)
   fictional characters, franchises and objects with their aliases (P1080, P1441, P8345), plus a curated list of
   famous marks. A hit means "send to the judge", never "block": most marks are ordinary words.
2. **An LLM judge** over the whole spec (name, description, geometry, materials): "is this recognisably an existing
   protected work or brand?" It catches indirect anchoring that a lexicon misses.
3. **Rewrite from the idea, then judge again.** The rewrite starts from the abstract idea ("a plasma blade") and
   builds fresh. It never edits the original's distinctive elements away one by one.
4. **Every verdict goes in the intent log** (refused, rewritten, passed, with the reason), so a replay shows why.
   Judge calls are thought results like any other LLM call: logged, never re-run on replay.
5. **Ground generation in Maxim Prime's own catalogue.** NPC prompts that know the city's brands, corporations and
   gear reach for those first.

What is out of reach: full trademark clearance from USPTO or EUIPO data (too broad, too noisy), and any guarantee
of non-infringement. A lawyer reviews the pipeline before commercial release.

## 4. Protecting creators without DRM

The world server runs on the host player's machine (`docs/design/realtime_lanes_coop.md` §5: loopback bind, host
and guest tokens). So the "server-authoritative" guarantee protects the world from the client; it does not hide
anything from the player who owns the machine. Any licensed content the host's server simulates is on the host's
disk, and encryption only moves the key next to it. Second Life's CopyBot (2006) shows the end state.

There is a second, deeper reason. A spec is geometry plus materials, and the snapshot that every client must receive
to draw the world *is* that geometry, sampled at the rig's resolution. Anything a player can see, they can copy at
that resolution. That is the analogue hole, and no transport encryption closes it.

What does protect creators:

| Mechanism | What it protects | Cost |
|---|---|---|
| Content-addressed spec ids plus provenance | Attribution; proving who made what first; spotting re-uploads by hash and by similarity | Low, and it starts now (section 6) |
| **Signatures, not encryption** | A creator signs their spec; the store signs licence grants. The server refuses a licensed spec without a valid grant. A forged or stripped spec fails loudly. | Low to medium |
| Licences plus takedown | The legal remedy, which is what actually deters commercial copying | The marketplace's operational cost (section 5) |
| Store-hosted behaviour | If creators ever supply *code* (scripted behaviour), not just specs, it runs on a studio-run service and never reaches the player | High: a hosted service plus sandboxing untrusted code. Avoid unless it is the product. |

Encryption still has its ordinary job: TLS for every connection that leaves the machine, and encryption at rest for
whatever creator account data we hold. Payment and identity data should be held by a merchant of record or payouts
provider, not by us, which keeps us out of PCI scope.

## 5. What a marketplace would cost

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

## 6. What changes now

These belong in protocol v0, intent log v0 and save v0 (`realtime_lanes_coop.md` §7, roadmap Phase 1), and are
proposed as findings for the next delta round of that design rather than edited into it here.

1. **Specs are content-addressed, by content alone.** A `SpecId` is a hash of the canonical encoding of the
   object's content: its primitives, materials and description (sorted keys, fixed number format, no `hash()`). The
   same object made twice has the same id, which is what lets a re-upload be spotted by hash (section 4). `place`
   stores the spec in a spec store keyed by id, and the region keeps a reference to its id. Today `place` keeps only
   a name and a mask and drops the spec (`imagination/spec.py:95-96`).
2. **Provenance and licence are a separate record per placement, not part of the id.**
   - Provenance: origin (`authored`, `imagined`, later `licensed`), creator actor, tick, and parent spec ids (the
     derivation chain). Two people who make the same object get one `SpecId` and two provenance records, and
     "who made it first" is the earliest tick.
   - Licence reference: one value today, `first-party/all-rights-reserved`. The reader refuses unknown values.
3. **The spec reader refuses unknown keys.** Today `_read` ignores them, so a misspelt key vanishes silently. That
   is a present trust-boundary defect, not part of this proposal. It is marked in `imagination/spec.py` and
   scheduled under Phase 1 in the roadmap, with the act-validation branch that is reworking `_read`.
4. **Region identity crosses the wire.** The `welcome` region list carries each region's spec id. The intent log
   header hashes the *initial* spec store, as the v0 header design (`realtime_lanes_coop.md` §7) hashes the scene,
   rig, material table, world config and roster. Specs imagined mid-session arrive later as logged thought
   results, so their content is in the records, not the header.
5. **Material ids are not a creator namespace.** `data/materials/core.yaml` ids are permanent `uint8` values (at most
   255). Third-party materials, if they come, get string ids mapped to per-world compact indices at load, recorded
   in the save. Nothing changes now; the constraint is written down so nobody spends the `uint8` space on content.

## 7. Open questions

- **Takedowns and replays.** Replays are bit-identical and the log refuses changed content. Removing an object
  changes every later state through heat, damage and fire, and can flip later placements between accepted and
  refused. A placeholder that keeps the physics footprint keeps the geometry, and for a physical spec the geometry is
  the expression. Likely answer: a replay is a private record bound to the licence in force when it was recorded,
  not redistributable after revocation. This is a legal question first.
- **Who owns first-party IP** (Denny or RMDig LLC, `docs/roadmap.md` open questions) has to be settled before any
  third-party licensing.
- **Style licensing.** No game platform pays a source creator when their style seeds a generation; the live schemes
  are in music (LANDR, Suno with WMG, Udio with Kobalt). Novel, and it needs an attribution method first.
- **Unverified facts from the research pass:** the Core platform's status, Minecraft's and Bethesda's official
  splits, the DSA small-enterprise exemption, the current 1099-K threshold, and the WIPO Global Brand Database's
  API. No merits ruling yet in *Disney v. Midjourney* or *NYT v. OpenAI*.
