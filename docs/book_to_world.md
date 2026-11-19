# Bringing a book to life (plan, 2026-11-14)

**Goal:** take a written story, from the novel that narrates Maxim Prime's characters or any other book, and turn
it into a world you can walk into on its last page: its places as scenes, its objects as imagined specs, and its
characters as Maxim agents who remember what they lived through in the book. Maxim Overdrive is the showcase for game
developers; the pipeline itself lives in **Maxim**, because nothing in it is specific to this game.

## The pipeline

```
book ──▶ extract ──▶ timeline ──▶ split by perspective ──▶ cradles (Maxim)  ──▶ NPCs at the last page
                 └──▶ places ──▶ scene specs ───────────────▶ world (this repo)
                 └──▶ objects ─▶ imagination specs ─────────▶ world (this repo)
```

1. **Extract** (LLM, structured, validated). Characters, places, objects and events. Every event records where it
   happened, who was present, what each person did and what it meant to them (valence, pain, reward), with a source
   span back into the text so every extraction can be checked against the page.
2. **Timeline.** Events in story order, mapped to experience time (`experience_us`), with flashbacks put back in
   order.
3. **Split by perspective: the core idea.** Each character's cradle holds **only what that character witnessed**,
   from their point of view. What they were only told comes in as *heard* episodes, stamped narrated rather than
   experienced (the provenance distinction on Maxim's grounding line, GL3). So characters disagree, misremember
   and keep secrets the way the book's characters do, and the dramatic irony survives into play.
4. **Cradles.** Each character's events are written into Maxim memory (Exp 64's prerequisites: the seed-memory
   path and the cradle writer), consolidated, and given a short live tail on the full loop.
5. **World.** Places become scene specs and objects become imagination specs. Both pass the world's rules (known
   materials, budgets), so the room where the fight happened has the scorch marks.
6. **Handoff.** The book's last page is the game's first turn.

## How we know it worked

The same discipline as Exp 64, applied to a book:
- **Knowledge boundaries:** ask a character about an event they did not witness. They should not know it, or should
  know only the version they heard.
- **Consistency:** a character's actions toward the player, given a cue from the book (an enemy's insignia), follow
  from what the book did to them, against a twin cradled on a version of the book without that chapter.
- **Fidelity:** extracted events checked against their source spans; a sample read by a person.

## Which books

- **The novel behind Maxim Prime:** the real target, written by Denny.
- **Public-domain books for the public showcase.** Anything else needs the rights holder's permission before it is
  shown publicly. Candidates that fit a machine-world RPG: E. M. Forster's *The Machine Stops* (1909), Karel Čapek's
  *R.U.R.* (1920, the play that gave us "robot"), Mary Shelley's *Frankenstein* (1818), Robert Louis Stevenson's
  *Strange Case of Dr Jekyll and Mr Hyde* (1886, self-modification, a natural fit for SEM), and Thea von Harbou's
  novel *Metropolis* (1925, in the US public domain since 2021). Check public-domain status in each country where
  it will be published.

## Where each part lives

| Part | Repo |
|---|---|
| Extraction, timeline, perspective split, cradle writer, seed-memory path | Maxim (new module; its own plan and review) |
| Scene and object specs from extracted places and objects, world rules, rendering | Maxim Overdrive |
| Knowledge-boundary and consistency experiments | Maxim (alongside Exp 64) |
