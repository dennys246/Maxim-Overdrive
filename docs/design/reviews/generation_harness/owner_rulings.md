# Generation harness design: the owner's rulings (2026-11-22)

A record of the owner's answers to `docs/design/generation_harness.md` §11 at e55c079. The design takes them in its
delta fold. This record isn't edited after that; a later ruling is a new section.

1. **The 0.05 m reference comparison runs on every spec,** once H0 has measured its cost. A stratified sample is the
   fallback only if that cost is prohibitive, and only by a new ruling.
2. **`owner_lan` is accepted as a declared known gap.** A batch job's local-only rule (`egress ∈ {loopback, owner_lan}`)
   admits any machine on the owner's tailnet, including a cloud VM joined to it, and the harness can't tell those
   apart. The owner's trigger: resolve it when the peer-mesh interaction between Maxim and Overdrive is refined (Maxim's
   leader and peer lanes, `docs/plans/deferred/vllm_self_hosted_servers.md` and Overdrive's inference placement). It is
   recorded in `docs/known_gaps.md` with that trigger in the delta fold.
