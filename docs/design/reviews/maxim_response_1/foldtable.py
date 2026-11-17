"""Build the v3 fold table from the ids present in the four lens files; refuse any id without a row, or a row without an id."""
import re, sys
from pathlib import Path
R = Path("docs/design/reviews/maxim_response_1")
ids = []
bd = R.joinpath("bio_determinism.md").read_text()
ids += [("bio_determinism", m) for m in dict.fromkeys(re.findall(r"^\| (BD-\d+) \|", bd, re.M))]
tb = R.joinpath("trust_boundary.md").read_text()
ids += [("trust_boundary", m) for m in dict.fromkeys(re.findall(r"^\| (TBR-\d+) \|", tb, re.M))]
ar = R.joinpath("architecture.md").read_text()
ids += [("architecture", "Arch " + m) for m in dict.fromkeys(re.findall(r"\*\*[A-Z][^*(\n]*\((\d\.\d)\)", ar))]
ids += [("architecture", "Arch §5")]
ex = R.joinpath("executor.md").read_text()
for m in re.finditer(r"^\| (\d[a-z]|—) \| ([^|]+?) \|", ex, re.M):
    ids.append(("executor", "Exec " + (m.group(1) if m.group(1) != "—" else "— " + m.group(2).strip()[:40])))
ids += [("executor", f"Exec N{n}") for n in re.findall(r"^(\d)\. \*\*", ex, re.M)]

F, P, N = "folded", "partial", "not folded"
MAP = {
 "BD-1": (P, "§5.1, OD-H5: its own plan, not `learned_hold_window`; the fixed-in-v1 yield deadline (learned only with a social cost) is left to the OD-H5 plan"),
 "BD-2": (F, "§5.1"), "BD-3": (F, "§4.4"), "BD-4": (F, "O11a, §4.4 (the lateness meter)"), "BD-5": (F, "§5.1"),
 "BD-6": (F, "§5.1"), "BD-7": (F, "O11a, §4.4; its citation corrected after Maxim's second answer (Stivers & Robinson supports the order only)"),
 "BD-8": (F, "§5.1"), "BD-9": (F, "§5.1"), "BD-10": (F, "§5.1, OD-H5"), "BD-11": (F, "§6.1 (the clock seam), OD-A2"),
 "BD-12": (F, "§6.1, OD-A2, OD-A3; the guard is the planted-render test plus a lint, per Maxim"),
 "BD-13": (F, "§6.1, OD-A7: keyed `random.Random` substreams (Maxim: Philox isn't needed), `seed_all` banned"),
 "BD-14": (P, "OD-A2 (an advancing fake clock), OD-A7 (`time_ns` ids); the rest (decay on load, monotonic stamps across saves, thread and set order, embedding floats, LLMs at T = 0, file-system order) is in `reply.md` §5 for Maxim's candidates doc, not yet in a design row"),
 "BD-15": (F, "§12.2"), "BD-16": (F, "§4.8"), "BD-17": (F, "§10"),
 "BD-18": (P, "OD-H6 (the wall interval on the machinery clock now; escalation later); the idle-DMN second trigger and a world-time refractory are not yet written"),
 "BD-19": (F, "§6.1 (credit at settle), §6.4, OD-A18"),
 "TBR-1": (F, "§6.1 (the leak closure), OD-A17"), "TBR-2": (F, "§6.1, `embeddable_agent_DRAFT.md` §3 (three tests plus a static ban)"),
 "TBR-3": (F, "§6.1, OD-A17; the worker process contains what isn't closed yet (O13)"), "TBR-4": (F, "O13, §6.3 (`spawn`, the latch after the pipe)"),
 "TBR-5": (F, "O13, §6.3"), "TBR-6": (F, "§6.4, OD-A18 (side doors folded into dispatch)"), "TBR-7": (F, "§6.1, OD-A17, §12.1 item 1"),
 "TBR-8": (F, "§5.2, O14"), "TBR-9": (F, "§6.1: the request/reply cut makes the model path the host's"), "TBR-10": (F, "§6.1, OD-I3"),
 "TBR-11": (F, "§5.2, O14, OD-I5; the worker holds no keys (O13)"), "TBR-12": (F, "O13 (a scrubbed environment)"),
 "TBR-13": (F, "§12.1 item 1, OD-A12"), "TBR-14": (F, "O14, §12.1 item 1"),
 "Arch 1.1": (F, "§6.2, §11.3, §4.8"),
 "Arch 1.2": (P, "§6.1 (world vs cognition tools, proposed): Maxim's answers didn't cover it"),
 "Arch 1.3": (F, "§4.7, `embeddable_agent_DRAFT.md` OD-EA9"), "Arch 1.4": (F, "§4.2 (P1c), §4.5"),
 "Arch 2.1": (F, "§6.1"), "Arch 2.2": (F, "§6.1 (the continuation), `embeddable_agent_DRAFT.md` §2 (a census of think-path writes first)"),
 "Arch 2.3": (F, "§6.1 (the basis)"), "Arch 2.4": (F, "§6.1, OD-A15"), "Arch 2.5": (F, "§6.1 (a model role)"),
 "Arch 2.6": (F, "§6.1, §5.2 (per-chunk validation)"), "Arch 3.1": (F, "O15a, OD-A15"), "Arch 3.2": (F, "O15, O15a (accepted, with the stepped `think` after 1.4.0)"),
 "Arch 4.1": (F, "§6.1 (injectable keyed substreams)"), "Arch 4.2": (F, "OD-A11, OD-A18 (Maxim: no contradiction)"),
 "Arch 4.3": (P, "OD-A16/OD-A18 (D53, settle keys), OD-A18 (side doors), OD-A12 (ConceptExtractor), §4.7 (chains, guest holds), OD-H6 (the submit trigger); the write window for agent stores is not written"),
 "Arch 4.4": (F, "§6.1 (priority and deadline fields)"), "Arch 4.5": (F, "§4.8"), "Arch 4.6": (F, "§10"),
 "Arch §5": (F, "this revision: O6a, O7a, §4.2, §4.4, §4.5, §4.7, §4.8, §5.2, §6.1, §6.2; `boundaries.md` §7.1, §7.4; the embeddable draft; roadmap Phase 3; OA3's interim is §12.1 item 6"),
 "Exec 1a": (F, "§4.2 (`next_actions`)"), "Exec 1b": (F, "§6.1"), "Exec 1c": (F, "§4.2 (P1c), §6.1"), "Exec 1d": (F, "§6.1 (no inner tool loop)"),
 "Exec 2a": (F, "§6.1"), "Exec 2b": (F, "§12.2 (never share a router)"), "Exec 3a": (F, "§6.1 front gate"), "Exec 3b": (F, "§6.1 front gate"),
 "Exec 3c": (F, "§4.7 (`maxItems`)"), "Exec 3d": (F, "O13"), "Exec 4a": (F, "§6.1 (`AgentHome`)"), "Exec 4b": (F, "§6.1 (`AgentHome`)"),
 "Exec 4c": (F, "§6.1 (`bio_stack.py:654`)"), "Exec 4d": (F, "§6.1 (keyed substreams)"), "Exec 5a": (F, "§12.3"), "Exec 5b": (F, "§12.3"),
 "Exec 5c": (N, "the 3 legacy `np.random` calls change no design row; OD-A7's scope (randomness outside the fence) covers them"),
 "Exec 5d": (F, "§12.3"), "Exec 5e": (F, "§12.2"), "Exec 5f": (F, "§12.3"), "Exec 5g": (F, "OD-I1"),
 "Exec 6a": (F, "OD-I3"), "Exec 6b": (F, "§6.1, OD-I3"), "Exec 6c": (F, "OD-I3"), "Exec 6d": (F, "OD-I3"),
 "Exec 7a": (F, "§6.1 (roster row)"), "Exec 7b": (F, "OD-H6"), "Exec 7c": (F, "OD-I4"), "Exec 7d": (F, "OD-I4"),
 "Exec 7e": (F, "§6.1, O13 (no keys, the gateway in the host)"), "Exec 8a": (F, "§5.1, OD-H5"), "Exec 8b": (F, "O15a"),
 "Exec — Citations for the resumable-think cut po": (F, "§6.1, `embeddable_agent_DRAFT.md` §1"),
 "Exec — Advisor POSIX-only": (F, "O13 (Windows needs an OS sandbox)"),
 "Exec N1": (F, "§4.2, §6.1"), "Exec N2": (F, "§6.1, OD-A17"), "Exec N3": (F, "§12.2"), "Exec N4": (F, "O13"),
 "Exec N5": (F, "§6.1 (keyed substreams, `seed_all` banned)"), "Exec N6": (F, "§12.3"), "Exec N7": (F, "§6.1 uses the corrected citations"),
}
found = [i for _, i in ids]
missing = [i for i in found if i not in MAP]
extra = [k for k in MAP if k not in found]
if missing or extra:
    sys.exit(f"missing rows: {missing}\nrows with no id: {extra}")
counts = {F: 0, P: 0, N: 0}
lines = ["", "## Fold table: Maxim's answers and their review (`reviews/maxim_response_1/`)", "",
         "Generated by a script from the ids present in the four lens files (`executor.md`, `architecture.md`,",
         "`bio_determinism.md`, `trust_boundary.md`); the script refuses an id without a row and a row without an id.", "",
         "| Lens | Id | Status | Where, or why not |", "|---|---|---|---|"]
for lens, i in ids:
    st, where = MAP[i]
    counts[st] += 1
    lines.append(f"| {lens} | {i.replace('Exec ', '').replace('Arch ', '')} | {st} | {where} |")
lines += ["", f"**Counts:** {len(ids)} ids; {counts[F]} folded, {counts[P]} partial, {counts[N]} not folded.", ""]
p = Path("docs/design/npcs_and_sem.md"); t = p.read_text()
marker = "\n## Fold table: Maxim's answers and their review"
if marker in t:
    t = t[: t.index(marker)]
p.write_text(t.rstrip("\n") + "\n" + "\n".join(lines))
print(len(ids), counts)
