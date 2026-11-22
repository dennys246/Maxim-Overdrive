"""Build the last fold table of npcs_and_sem.md, kept in reviews/npcs_v3/fold.md, from two rounds' lens files.

Covers `reviews/maxim_response_1/` (the review of Maxim's answers) and `reviews/npcs_v3/` (the review of v3). It
refuses, and writes nothing, when:
- a lens file has an id with no row here, or a row here has no id in any lens file;
- a row marked folded or partial names no place: it must cite a section (`§`) or the roadmap.
The ids are found by each file's heading patterns; a finding written outside them would be missed, so the per-file
counts are printed for a reader to check against each file's own severity totals.

Run from anywhere: `python3 docs/design/reviews/npcs_v3/foldtable.py`. It supersedes `maxim_response_1/foldtable.py`.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
R1 = ROOT / "docs/design/reviews/maxim_response_1"
R3 = ROOT / "docs/design/reviews/npcs_v3"
TARGET = ROOT / "docs/design/reviews/npcs_v3/fold.md"  # moved out of the design (B36)
MARKERS = ("\n## Fold table: Maxim's answers and their review", "\n## Fold table: the last two review rounds")


def ids_round1() -> list[tuple[str, str]]:
    ids = []
    bd = (R1 / "bio_determinism.md").read_text()
    ids += [("maxim_response_1/bio_determinism", m) for m in dict.fromkeys(re.findall(r"^\| (BD-\d+) \|", bd, re.M))]
    tb = (R1 / "trust_boundary.md").read_text()
    ids += [("maxim_response_1/trust_boundary", m) for m in dict.fromkeys(re.findall(r"^\| (TBR-\d+) \|", tb, re.M))]
    ar = (R1 / "architecture.md").read_text()
    ids += [("maxim_response_1/architecture", "Arch " + m) for m in dict.fromkeys(re.findall(r"\*\*[A-Z][^*(\n]*\((\d\.\d)\)", ar))]
    ids += [("maxim_response_1/architecture", "Arch §5")]
    ex = (R1 / "executor.md").read_text()
    for m in re.finditer(r"^\| (\d[a-z]|—) \| ([^|]+?) \|", ex, re.M):
        key = m.group(1) if m.group(1) != "—" else "— " + m.group(2).strip()[:40]
        ids.append(("maxim_response_1/executor", "Exec " + key))
    ids += [("maxim_response_1/executor", f"Exec N{n}") for n in re.findall(r"^(\d)\. \*\*", ex, re.M)]
    return ids


ROUND3 = [
    ("architecture.md", r"^### ((?:B|S)\d+)\. ", "Arch3 "),
    ("architecture.md", r"^- \*\*(N\d+) \(", "Arch3 "),
    ("bio_faithful.md", r"^### (BF3-\d+):", ""),
    ("bio_faithful.md", r"^- \*\*(BF3-\d+) ", ""),
    ("determinism.md", r"^### (DET-[BS]\d+):", ""),
    ("determinism.md", r"^- \*\*(DET-N\d+):", ""),
    ("executor.md", r"^\*\*([BS]\d+)\. ", "Exec3 "),
    ("executor.md", r"^- \*\*(N\d+)\. ", "Exec3 "),
    ("trust_boundary.md", r"^### (TB3-[BS]\d+)\. ", ""),
    ("trust_boundary.md", r"^- \*\*(TB3-N\d+)\.\*\*", ""),
]


def ids_round3() -> tuple[list[tuple[str, str]], dict[str, int]]:
    ids, per_file = [], {}
    for name, pattern, prefix in ROUND3:
        found = re.findall(pattern, (R3 / name).read_text(), re.M)
        per_file[name] = per_file.get(name, 0) + len(found)
        ids += [("npcs_v3/" + name.removesuffix(".md"), prefix + m) for m in dict.fromkeys(found)]
    return ids, per_file


F, P, N = "folded", "partial", "not folded"
MAP = {
    # -- round 1: Maxim's answers and their four-lens review (statuses re-checked against the npcs_v3 review) --------
    "BD-1": (P, "§5.1, roadmap OD-H5: its own plan, not `learned_hold_window`; the fixed-in-v1 yield deadline (learned only with a social cost) is left to the OD-H5 plan"),
    "BD-2": (F, "§5.1"), "BD-3": (F, "§4.4, §6.6 (the acoustics caveat)"),
    "BD-4": (F, "§0 (O11a), §4.4 (the lateness meter), §6.6 (the listener side and the Known gap; v3 had only the speaker side)"),
    "BD-5": (F, "§5.1, §12.1 item 5 (filler propensity)"),
    "BD-6": (F, "§5.1, §6.6 (the structural rule's test, written now; v3 lacked it)"),
    "BD-7": (F, "§0 (O11a), §4.4; its citation corrected after Maxim's second answer (Stivers & Robinson supports the order only)"),
    "BD-8": (F, "§5.1"), "BD-9": (F, "§5.1, §6.6"), "BD-10": (F, "§5.1, roadmap OD-H5"),
    "BD-11": (F, "§6.1 (the clock seam), roadmap OD-A2"),
    "BD-12": (F, "§6.1, §6.6 (the sentinel in the machinery clock, the offset-and-scale test), roadmap OD-A2, OD-A3"),
    "BD-13": (P, "§3.4, §6.6: isolation across NPCs and streams holds; within a Maxim stream draws stay sequential, so a cadence change shifts them, an accepted cost recorded in §3.4 (v3 marked this folded)"),
    "BD-14": (P, "roadmap OD-A2 (an advancing fake clock, a static ban on `time.*` and `datetime.now`, a long-horizon run), OD-A7 (`time_ns` ids); decay on load, `monotonic` stamps across saves, thread and set order, embedding floats and LLMs at T = 0 are in no design row, and `reply.md` §5 doesn't list the last two"),
    "BD-15": (F, "§12.2"), "BD-16": (F, "§4.8, §10 (d_z pre-registered, divergence tick per pair)"), "BD-17": (F, "§10"),
    "BD-18": (P, "roadmap OD-H6 (the wall interval on the machinery clock now; escalation later); the idle-DMN second trigger and a world-time refractory are not yet written"),
    "BD-19": (F, "§6.1, §6.4, §6.6 (the chooser stamp and yield-exclusion test; credit's real dependency), roadmap OD-A18, OD-A19"),
    "TBR-1": (F, "§6.1 (the leak closure), roadmap OD-A17"),
    "TBR-2": (F, "§6.1, `embeddable_agent_DRAFT.md` §3 (three tests plus a static ban, with named packages)"),
    "TBR-3": (F, "§6.1, roadmap OD-A17; the worker process contains what isn't closed yet (§6.3, §6.6)"),
    "TBR-4": (F, "§6.3, §6.6 (`spawn`; the host never latches itself, a start-up check; v3 missed the host side)"),
    "TBR-5": (F, "§6.6 (the channel as a gate, the test double behind it), `boundaries.md` §5.3 (v3 had neither)"),
    "TBR-6": (F, "§6.4, roadmap OD-A18, `embeddable_agent_DRAFT.md` OD-EA4 (the planted parallel-dispatch write)"),
    "TBR-7": (F, "§6.1, §6.6, roadmap OD-A17 (the static ban names `maxim.embodied_runtime`; no reply reaches the template)"),
    "TBR-8": (F, "§5.2, §6.6 (provenance with session id and host index)"),
    "TBR-9": (F, "§6.1: the request/reply cut makes the model path the host's"),
    "TBR-10": (F, "§6.1, roadmap OD-I3"),
    "TBR-11": (P, "§5.2, §6.6 (the guest-text gate, every Cf character restored); cloud egress refused with guests is a proposed sixth gate for the owner, §12.1 item 1"),
    "TBR-12": (F, "§6.6 (an environment allowlist, not a scrub; the host start-up check)"),
    "TBR-13": (F, "§12.1 items 1 and 7 (retention of guest speech agent-side)"),
    "TBR-14": (F, "§0 (O14), §12.1 item 1, roadmap Phase 4"),
    "Arch 1.1": (F, "§6.2, §11.3, §4.8"),
    "Arch 1.2": (P, "§6.1, §6.6: cognition tools inside `think` are proposed, not adopted, pending Maxim's C10 experiment"),
    "Arch 1.3": (F, "§4.7, §6.6, `embeddable_agent_DRAFT.md` OD-EA9"), "Arch 1.4": (F, "§4.2 (P1c), §4.5"),
    "Arch 2.1": (F, "§6.1"), "Arch 2.2": (F, "§6.1, §6.6 (the continuation split by owner), `embeddable_agent_DRAFT.md` §2"),
    "Arch 2.3": (F, "§6.1 (the basis), §6.6 (one staleness vocabulary and what resume does; v3 had only the basis)"),
    "Arch 2.4": (F, "§6.1, roadmap OD-A15"), "Arch 2.5": (F, "§6.1 (a model role)"),
    "Arch 2.6": (F, "§6.1, §5.2, §6.6 (per-chunk validation on decoded text)"),
    "Arch 3.1": (F, "§0 (O15a), roadmap OD-A15"), "Arch 3.2": (F, "§0 (O15, O15a; the stepped `think` after 1.4.0)"),
    "Arch 4.1": (F, "§6.1, §6.6 (one derivation)"), "Arch 4.2": (F, "roadmap OD-A11, OD-A18 (Maxim: no contradiction)"),
    "Arch 4.3": (P, "roadmap OD-A16, OD-A18 (D53, settle keys, side doors), OD-A12 (ConceptExtractor), §4.7 and §6.6 (chains, guest holds), roadmap OD-H6 (the submit trigger); the write window for agent stores is not written"),
    "Arch 4.4": (F, "§6.1, §6.6 (the host stamps priority and deadline from the kind; v3's agent-supplied deadline was a second source of time)"),
    "Arch 4.5": (F, "§4.8"), "Arch 4.6": (F, "§10"),
    "Arch §5": (F, "v3 and v3.1: §0 (O6a, O7a), §4.2, §4.4, §4.5, §4.7, §4.8, §5.2, §6.1, §6.2, §6.6; `boundaries.md` §7.1, §7.4; the embeddable draft; roadmap Phase 3; OA3's interim is §12.1 item 6"),
    "Exec 1a": (F, "§4.2 (`next_actions`)"), "Exec 1b": (F, "§6.1"), "Exec 1c": (F, "§4.2 (P1c), §6.1"),
    "Exec 1d": (F, "§6.1 (no inner tool loop)"), "Exec 2a": (F, "§6.1"), "Exec 2b": (F, "§12.2 (never share a router)"),
    "Exec 3a": (F, "§6.1 front gate"), "Exec 3b": (F, "§6.1 front gate"), "Exec 3c": (F, "§4.7 (`maxItems`)"),
    "Exec 3d": (F, "§6.3, §6.6"), "Exec 4a": (F, "§6.1 (`AgentHome`)"), "Exec 4b": (F, "§6.1 (`AgentHome`)"),
    "Exec 4c": (F, "§6.1 (`bio_stack.py:654`)"), "Exec 4d": (F, "§6.1, §6.6 (keyed substreams)"),
    "Exec 5a": (F, "§12.3"), "Exec 5b": (F, "§12.3"),
    "Exec 5c": (N, "the 3 legacy `np.random` calls change no design row; OD-A7's scope (randomness outside the fence) covers them"),
    "Exec 5d": (F, "§12.3"), "Exec 5e": (F, "§12.2"), "Exec 5f": (F, "§12.3"), "Exec 5g": (F, "roadmap Phase 3 (OD-I1, five sites)"),
    "Exec 6a": (F, "roadmap Phase 3 (OD-I3)"), "Exec 6b": (F, "§6.1, roadmap OD-I3"), "Exec 6c": (F, "roadmap Phase 3 (OD-I3)"),
    "Exec 6d": (F, "roadmap Phase 3 (OD-I3)"), "Exec 7a": (F, "§6.1 (roster row)"), "Exec 7b": (F, "roadmap OD-H6"),
    "Exec 7c": (F, "roadmap Phase 3 (OD-I4)"), "Exec 7d": (F, "roadmap Phase 3 (OD-I4)"),
    "Exec 7e": (F, "§6.1, §6.3 (no keys, the gateway in the host)"), "Exec 8a": (F, "§5.1, roadmap OD-H5"),
    "Exec 8b": (F, "§0 (O15a)"),
    "Exec — Citations for the resumable-think cut po": (F, "§6.1, `embeddable_agent_DRAFT.md` §1"),
    "Exec — Advisor POSIX-only": (F, "§6.6 (an OS sandbox per platform; Windows refused for guest sessions, proposed)"),
    "Exec N1": (F, "§4.2, §6.1"), "Exec N2": (F, "§6.1, roadmap OD-A17"), "Exec N3": (F, "§12.2"), "Exec N4": (F, "§6.3, §6.6"),
    "Exec N5": (F, "§3.4, §6.6 (one derivation; CLAUDE.md's numpy rule governs `World`; v3 left the conflict open)"),
    "Exec N6": (F, "§12.3"),
    "Exec N7": (F, "§1, §6.1, §6.4 (directories added; §1's time citation is `:1125-1127`; v3 had neither)"),
    # -- round 3: the five-lens review of v3 (npcs_v3) --------------------------------------------------------------
    "Arch3 B1": (F, "§6.6 (`apply` and `settle` the only writers, both host-called), `boundaries.md` §7.1"),
    "Arch3 B2": (F, "§6.6 (a host-owned header with the budgets, an opaque agent-owned body)"),
    "Arch3 S1": (F, "§6.6 (the lifecycle, end to end)"),
    "Arch3 S2": (F, "§6.6 (no backend in the worker; the doors fail closed), roadmap OD-A17, `embeddable_agent_DRAFT.md` §3"),
    "Arch3 S3": (F, "§6.1, §6.6 (cognition tools not adopted; C10)"),
    "Arch3 S4": (F, "§6.6 (stage 1 in the host; `PYTHONHASHSEED` pinned), `boundaries.md` §5.3, §5.4"),
    "Arch3 S5": (F, "§6.1, §6.6 (the host stamps priority and deadline)"),
    "Arch3 S6": (F, "§6.6 (`agent_failed`)"), "Arch3 S7": (F, "§6.6 (the test double behind the channel)"),
    "Arch3 S8": (F, "`embeddable_agent_DRAFT.md` §4 (PR 5 is the one submit-path design; PR 4a), roadmap OD-A15"),
    "Arch3 S9": (F, "§12.1 item 6 (reframed with dilate's numbers, co-op cost, abandon's real cost)"),
    "Arch3 S10": (F, "`world_model.md` §10 rows 9b and 10, §6.5"),
    "Arch3 N1": (F, "§6.6, `boundaries.md` §7.1 (inlining is a decision against O13)"),
    "Arch3 N2": (F, "`boundaries.md` §7.1 (the host service protocol of boundaries v2 and npcs v2)"),
    "Arch3 N3": (F, "§6.6 (one signature), `boundaries.md` §7.1"),
    "Arch3 N4": (F, "§6.6 (receipts have two projections)"),
    "Arch3 N5": (F, "roadmap Phase 3 note; the foundations fold rows annotated (§6.6), `boundaries.md` fold table"),
    "Arch3 N6": (F, "§6.6 (`truncated(prefix, reason=validation)`)"),
    "Arch3 N7": (F, "`boundaries.md` §5.3 (Agent homes: `MAXIM_DATA_HOME` the one allowed read until OD-A12)"),
    "BF3-1": (F, "§6.1, §6.6 (credit's real dependency), roadmap OD-A19, `correction_1.md`"),
    "BF3-2": (F, "§6.6 (the settle horizon is `[engineering]`; its route is the 300 s buffer)"),
    "BF3-3": (F, "§6.6 (the yield after ~1 s of unfilled silence; the account's onset a parameter)"),
    "BF3-4": (F, "§6.6 (the Known gap; the listener-side rule)"),
    "BF3-5": (F, "§6.6 (P1c in fatigue load and the speed trait)"),
    "BF3-6": (F, "§6.6, §8.2, roadmap OD-A15 (retrieval writes returned)"),
    "BF3-7": (F, "§6.6 (the offset-and-scale test)"),
    "BF3-8": (F, "§6.6 (planning in overlap, not the repertoire)"),
    "BF3-9": (F, "§6.6 (the O'Connell & Kowal caveat)"), "BF3-10": (F, "§6.6 (production vs perception)"),
    "BF3-11": (F, "§6.6, §12.1 item 5 (filler propensity)"), "BF3-12": (F, "§6.6 (Maxim's ANALOG label)"),
    "BF3-13": (F, "§6.6 (the BD-6 and BD-19 tests); this table re-marks BD-6 and BD-19"),
    "DET-B1": (F, "§4.4, §6.6 (resume at the landing tick; `reply_landed`)"),
    "DET-B2": (F, "§6.6 (the prefix is delivered speech in world time)"),
    "DET-B3": (F, "§6.1, §6.6, `embeddable_agent_DRAFT.md` OD-EA11"),
    "DET-S1": (F, "§6.6 (`floor_event` host records)"), "DET-S2": (F, "§6.6 (canonical repeat numbering)"),
    "DET-S3": (F, "§6.6 (the double in a spawned worker)"), "DET-S4": (F, "§6.6 (`agent_failed`, logged)"),
    "DET-S5": (F, "§6.6 (resume equivalence)"), "DET-S6": (F, "§6.6 (a coarse category, modelled part only)"),
    "DET-S7": (F, "§6.6 (fatigue counts modelled durations)"),
    "DET-S8": (F, "§3.4 (the accepted cost); this table re-marks BD-13 and BD-14"),
    "DET-N1": (F, "§6.6 (one signature)"), "DET-N2": (F, "§6.6 (host-stamped, outside the cache key)"),
    "DET-N3": (F, "§10 (d_z pre-registered, divergence tick per pair)"),
    "DET-N4": (F, "§6.6 (`npc_key`; state saved pickle-free)"), "DET-N5": (F, "§6.6 (the machinery clock's zero)"),
    "Exec3 B1": (F, "§6.6, `boundaries.md` §5.3 (the worker channel gate)"),
    "Exec3 S1": (F, "this fold table, after §12.3 (TBR-4, Exec N5 and N7 re-marked and folded)"),
    "Exec3 S2": (F, "roadmap Phase 4 (entry: OD-A1 to OD-A19, 1.4.0 and the slice), roadmap Phase 3 exit (OD-EA10 to OD-EA12)"),
    "Exec3 S3": (F, "§3.4, §6.6 (one derivation; the real hash names)"),
    "Exec3 S4": (F, "§6.3, §6.6 (the round-trip estimate, budget and levers)"),
    "Exec3 S5": (F, "§6.5; the foundations fold rows annotated in both files"),
    "Exec3 S6": (F, "§12.1 item 1, roadmap Phase 4 (the red gate and the five tests)"),
    "Exec3 N1": (F, "§1 (each count names its `main`)"), "Exec3 N2": (F, "§6.1, §6.4, `embeddable_agent_DRAFT.md` §3"),
    "Exec3 N3": (F, "§6.1 (ten families)"), "Exec3 N4": (F, "§6.1 (the roster row)"),
    "Exec3 N5": (F, "the header, §4.5, §6.1, `embeddable_agent_DRAFT.md` §1 (\"by default\"; the 0.11× row is a lower bound)"),
    "Exec3 N6": (F, "§8.1, §8.2, roadmap OD-H4 (folded into OD-H5)"),
    "Exec3 N7": (F, "§6.6 (one signature)"),
    "Exec3 N8": (P, "this generator, which writes the fold table after §12.3 (root-relative, per-file counts printed, refuses folded rows without a place); nothing in the gate reruns it yet, and the 40-character keys of two round-1 rows are kept so their ids stay stable"),
    "Exec3 N9": (F, "§0 (O14's dated note)"), "Exec3 N10": (F, "§6.1, §12.1 item 1 (which trigger uses the wake word)"),
    "TB3-B1": (F, "§6.6, `boundaries.md` §5.3"),
    "TB3-S1": (F, "§6.6, §12.2, `embeddable_agent_DRAFT.md` §2 (no reply reaches the template)"),
    "TB3-S2": (F, "§6.6 (provenance through derivation and relay; the purge's exit test)"),
    "TB3-S3": (F, "`boundaries.md` §5.3, §6.6 (every Cf character)"),
    "TB3-S4": (F, "§6.6 (decoded text, per chunk and whole)"), "TB3-S5": (F, "§6.6 (the host-delivered prefix)"),
    "TB3-S6": (F, "§6.6 (a container, not a sandbox; an OS sandbox proposed for guest sessions)"),
    "TB3-S7": (F, "§6.6 (the host never latches itself)"),
    "TB3-S8": (P, "§12.1 item 1: remote egress with guests is proposed as a sixth gate; the owner decides"),
    "TB3-S9": (F, "§6.6 (budgets per input and per NPC per world minute)"), "TB3-S10": (F, "§6.6 (`agent_failed`)"),
    "TB3-S11": (F, "§12.1 item 1, roadmap Phase 4 (the strict red gate on guest joins)"),
    "TB3-S12": (F, "this fold table, after §12.3 (TBR-5, 7, 8, 11, 12, 13 and 4 re-checked; TBR-11 stays partial)"),
    "TB3-N1": (F, "§12.2, `boundaries.md` §5.3 (OD-A18)"),
    "TB3-N2": (F, "`embeddable_agent_DRAFT.md` §3, roadmap OD-A17 (the ban's packages named)"),
    "TB3-N3": (F, "`embeddable_agent_DRAFT.md` §5 (OD-EA4's planted write)"),
    "TB3-N4": (F, "§6.6, `boundaries.md` §5.3 (one guest-text gate for every string)"),
}


def main() -> int:
    r1 = ids_round1()
    r3, per_file = ids_round3()
    ids = r1 + r3
    found = [i for _, i in ids]
    problems = [f"id with no row: {i}" for i in found if i not in MAP]
    problems += [f"row with no id: {k}" for k in MAP if k not in found]
    problems += [f"{k} is {st} but names no place (cite a § or the roadmap)" for k, (st, where) in MAP.items()
                 if st != N and "§" not in where and "roadmap" not in where]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    counts = {F: 0, P: 0, N: 0}
    lines = ["", "## Fold table: the last two review rounds (`reviews/maxim_response_1/`, `reviews/npcs_v3/`)", "",
             "Generated by `reviews/npcs_v3/foldtable.py` from the ids in both rounds' lens files. It refuses an id without",
             "a row, a row without an id, and a folded or partial row that names no section or roadmap row. The round-1",
             "statuses were re-checked against the npcs_v3 review, which found v3's table overstated (it claimed 87",
             "folded; the lenses put it at about 80): those rows say what v3 lacked.", "",
             "| Lens | Id | Status | Where, or why not |", "|---|---|---|---|"]
    for lens, i in ids:
        st, where = MAP[i]
        counts[st] += 1
        shown = re.sub(r"^(Exec3?|Arch3?) ", "", i)
        lines.append(f"| {lens} | {shown} | {st} | {where} |")
    lines += ["", f"**Counts:** {len(ids)} ids; {counts[F]} folded, {counts[P]} partial, {counts[N]} not folded.", ""]
    t = TARGET.read_text()
    cut = min((t.index(m) for m in MARKERS if m in t), default=len(t))
    TARGET.write_text(t[:cut].rstrip("\n") + "\n" + "\n".join(lines))
    print(f"{len(ids)} ids ({len(r1)} round 1, {len(r3)} round 3: {per_file}); {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
