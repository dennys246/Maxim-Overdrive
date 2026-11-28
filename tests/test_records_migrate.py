"""The converter on today's files (``docs/design/records_layout.md`` §8 stage 1; the cases §9 R2 names)."""

from __future__ import annotations

import pytest

from simcore.adapters.loaders import read_yaml
from tests._records import ROOT, build, decisions, index, migrate, records

TODAY = ROOT / "tests/fixtures/records/today"
HAND = ROOT / "tests/fixtures/records/hand.yaml"


@pytest.fixture(scope="module")
def result():
    files = {p.relative_to(TODAY).as_posix(): p.read_text(encoding="utf-8") for p in sorted(TODAY.rglob("*.md"))}
    return migrate.migrate(files, migrate.read_hand(read_yaml(HAND)))


def _one(result, family: str, ident: str, log: str | None = None):
    found = [r for r in result.records if r.family == family and r.id == ident and (log is None or r.log == log)]
    assert len(found) == 1, (family, ident, [r.path for r in found])
    return found[0]


def _status(result, ident: str, log: str) -> str:
    decisions_ = [r for r in result.records if r.family == "decisions"]
    derived: str = index.status(_one(result, "decisions", ident), log, index.Relations.of(decisions_))
    return derived


@pytest.mark.parametrize(
    ("ident", "log", "cell"),
    [
        ("O2", "boundaries", "superseded by O6"),
        ("O65", "boundaries", "live; amended by O70"),
        ("O67", "boundaries", "live; confirmed by O69"),
        ("O71", "boundaries", "live; corrected by O73"),
        ("O24", "boundaries", "live; amended by docs-contracts ruling 49"),
        ("D26", "world_model", "amended by D29; amended by docs-contracts ruling 59"),
    ],
)
def test_every_non_live_status_cell_derives_back_to_its_meaning(result, ident, log, cell):
    aliases = migrate.read_hand(read_yaml(HAND)).aliases
    assert decisions.meaning(_status(result, ident, log), aliases) == decisions.meaning(cell, aliases)


def test_the_relations_are_held_by_the_later_ruling(result):
    assert _one(result, "decisions", "O6").strings("supersedes") == ("O2",)
    assert _one(result, "decisions", "O69").strings("confirms") == ("O67", "O68")
    assert _one(result, "decisions", "O74").strings("confirms") == ("O73",)
    assert _one(result, "decisions", "O73").strings("corrects") == ("O71",)
    external = [dict(e) for e in _one(result, "decisions", "O24").maps("amended_by_external")]
    assert external == [{"path": "docs/design/reviews/docs_contracts/rulings.md", "ruling": "49"}]


def test_a_section_restating_row_restates_a_path_and_keeps_its_wording_in_legacy(result):
    record = _one(result, "decisions", "d26-to-d28")
    assert record.strings("restates") == ("docs/design/world_model.md §0",)
    (row,) = record.legacy["rows"]
    assert row["id_cell"] == "D26\u2013D28"
    assert row["status"] == "restates world_model §0; amended by docs-contracts ruling 59"


def test_a_cross_listed_decision_is_one_record_with_each_logs_cells(result):
    record = _one(result, "decisions", "T1")
    assert record.log == "client_rendering"
    assert record.strings("also_in") == ("tile_and_client",)
    rows = {row["log"]: row for row in record.legacy["rows"]}
    assert (
        rows["tile_and_client"]["status"] == "restates `client_rendering.md`; also in `decisions/client_rendering.md`"
    )
    d20 = _one(result, "decisions", "D20")
    assert d20.log == "client_rendering"
    assert d20.strings("restates") == ()
    assert {r["log"] for r in d20.legacy["rows"]} == {"client_rendering", "world_model"}


def test_id_less_and_restating_rows_each_come_out_as_one_record(result):
    slugs = {r.id for r in result.records if r.family == "decisions" and records.id_key(r.id)[0] == 1}
    assert {"ruled-1", "the-split", "rt1-to-4", "d20-d25", "o23-o24-o31", "claude-md", "the-rounds-stop"} <= slugs
    assert (
        len([r for r in result.records if r.family == "decisions" and r.log == "npcs_and_sem" and r.id in slugs]) == 2
    )


def test_row_order_the_heading_tail_and_non_iso_dates_survive_in_legacy(result):
    o25 = _one(result, "decisions", "O25")
    assert o25.legacy["rows"][0]["position"] == 19  # after O42, out of id order
    assert _one(result, "lessons", "11").legacy["heading_tail"] == ", reworded 2026-11-20"
    odd = [r for r in result.records if r.family == "decisions" and r.meta["date"] == "unknown"]
    cells = {row.get("who_date") for r in odd for row in r.legacy["rows"]}
    assert "owner, 2026-11-17/18" in cells
    standing = _one(result, "decisions", "claude-md")  # "standing" renders from who alone, so it needs no legacy cell
    assert (standing.meta["who"], standing.meta["date"]) == ("standing", "unknown")
    assert "who_date" not in standing.legacy["rows"][0] or standing.legacy["rows"][0]["who_date"] is None


def test_the_backlogs_status_comes_only_from_its_prose(result):
    assert _one(result, "backlog", "B11").meta["status"] == "done"
    assert _one(result, "backlog", "B11").meta["done_in"] == "first green run at cf4020e, all four jobs"
    assert _one(result, "backlog", "B37").meta["status"] == "done in part"
    assert _one(result, "backlog", "B1").meta["status"] == "open"
    assert _one(result, "backlog", "B6").meta["status"] == "unknown"  # "done locally; pending": not invented
    b23 = _one(result, "backlog", "B23")
    assert b23.meta["lands_with"] == "unknown"
    assert b23.legacy["three_cells"] is True
    assert "unknown: docs/standards_backlog/B23-a-reviewer-sets-fold-status.md: lands_with" in result.listed


def test_gaps_without_a_bold_lead_gate_or_step_are_listed_never_invented(result):
    gaps = [r for r in result.records if r.family == "gaps"]
    assert len(gaps) == 18
    assert len([line for line in result.listed if line.startswith("hand title: gap")]) == 5
    assert all(r.meta["closes_at"] == "unknown" and r.meta["kind"] == "unknown" for r in gaps)
    gated = {r.slug: r.meta["gate"] for r in gaps if r.meta["gate"] != "unknown"}
    assert gated["fires-don-t-consume-fuel-once-nothing-solid-is-left-under-a"] == (
        "tests/test_cross_tier.py::test_a_fire_that_has_burned_its_fuel_stops_heating"
    )
    assert (
        len(gated) == 7
    )  # every bullet that names a red gate, "Red gate" or "red gate", counted apart from the converter
    assert gated["region-breached-picks-its-axis-from-cell-extents-so-the-axis"].startswith("tests/test_damage.py::")


def test_a_row_or_gap_with_no_bold_lead_and_no_hand_title_is_refused(result):
    files = {p.relative_to(TODAY).as_posix(): p.read_text(encoding="utf-8") for p in sorted(TODAY.rglob("*.md"))}
    empty = build.Hand({}, migrate.read_hand(read_yaml(HAND)).aliases, {}, {})
    with pytest.raises(decisions.MigrationError, match="no bold lead and no hand title"):
        migrate.migrate(files, empty)


def test_a_status_the_fields_cant_derive_fails_the_build():
    log = (
        "# Decisions\n\n| Id | Ruling | Who, date | Owner section | Status |\n|---|---|---|---|---|\n"
        "| O1 | **One.** | owner, 2026-11-16 | — | amended by O9 |\n"
    )
    with pytest.raises(decisions.MigrationError, match=r"status 'amended by O9' derives as 'live'"):
        build.build({"alpha": log}, build.Hand({}, {}, {}, {}))


@pytest.mark.parametrize("cell", ["live; retired by O2", "restated", "amended by O2 and O3"])
def test_a_status_the_converter_cant_read_is_refused(cell):
    with pytest.raises(decisions.MigrationError, match="can't read"):
        decisions.meaning(cell, {})


def test_a_restated_name_without_an_alias_is_refused():
    log = (
        "# D\n\n| Id | Ruling | Who, date | Owner section | Status |\n|---|---|---|---|---|\n"
        "| D1, D2 | **Both.** | owner, 2026-11-16 | — | restates nowhere §9 |\n"
    )
    with pytest.raises(decisions.MigrationError, match="names no path the hand aliases give"):
        build.build({"alpha": log}, build.Hand({}, {}, {}, {}))


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("# D\n\nno table\n", "no table"),
        ("# D\n\n| Id | Ruling | Who, date | Owner section | Status |\n|--|\n", "separator"),
        (
            "# D\n\n| Id | Ruling | Who, date | Owner section | Status |\n|---|---|---|---|---|\n| O1 | a | b |\n",
            "five cells",
        ),
    ],
)
def test_a_log_that_isnt_todays_form_is_refused(text, match):
    with pytest.raises(decisions.MigrationError, match=match):
        decisions.split_log("alpha", text)


def test_two_rows_of_one_id_in_one_log_are_refused():
    rows = [decisions.Row("alpha", n, "O1", "**x**", "owner, 2026-11-16", "—", "live") for n in (1, 2)]
    with pytest.raises(decisions.MigrationError, match="two rows in one log"):
        decisions.group_rows(rows)


def test_a_hand_file_naming_a_key_twice_is_refused():
    with pytest.raises(decisions.MigrationError, match="names a key twice"):
        migrate.read_hand({"version": 1, "titles": [{"key": "a", "value": "x"}, {"key": "a", "value": "y"}]})


def test_a_lesson_heading_without_its_date_is_refused():
    with pytest.raises(decisions.MigrationError, match="without its date"):
        migrate.lessons("# L\n\n## Time\n\n### 1. One\n\nText.\n")


def test_a_backlog_row_that_isnt_three_or_four_cells_is_refused():
    head = "# B\n\n| ID | Rule it enforces | The check | Lands with |\n|---|---|---|---|\n"
    with pytest.raises(decisions.MigrationError, match="three or four cells"):
        migrate.backlog(head + "| B1 | a |\n")
    with pytest.raises(decisions.MigrationError, match="no table"):
        migrate.backlog("# B\n")


def test_a_gaps_list_line_that_is_neither_a_bullet_nor_a_group_is_refused():
    with pytest.raises(decisions.MigrationError, match="not a bullet or a group"):
        migrate.gaps("# G\n\n**Gaps:**\n- **A.** x\nstray\n", build.Hand({}, {}, {}, {}))


def test_a_slug_id_row_that_names_a_relation_is_refused():
    log = (
        "# D\n\n| Id | Ruling | Who, date | Owner section | Status |\n|---|---|---|---|---|\n"
        "| ruled 1 | **One.** | owner, 2026-11-16 | — | superseded by O2 |\n"
    )
    with pytest.raises(decisions.MigrationError, match="a slug-id row is 'superseded by O2'"):
        build.build({"alpha": log}, build.Hand({}, {}, {}, {}))


def test_a_decision_row_with_no_bold_lead_needs_a_hand_title():
    log = (
        "# D\n\n| Id | Ruling | Who, date | Owner section | Status |\n|---|---|---|---|---|\n"
        "| O1 | No lead here. | owner, 2026-11-16 | — | live |\n"
    )
    with pytest.raises(decisions.MigrationError, match="decision row alpha:O1 has no bold lead and no hand title"):
        build.build({"alpha": log}, build.Hand({}, {}, {}, {}))
    _, recs, listed = build.build({"alpha": log}, build.Hand({"alpha:O1": "One"}, {}, {}, {}))
    assert recs[0].title == "One"
    assert listed == ["hand title: decision alpha:O1: One"]
