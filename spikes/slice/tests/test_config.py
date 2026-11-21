import copy

import pytest
import yaml
from slice_server import config


def _raw() -> dict:
    return yaml.safe_load((config.DATA / "body.yaml").read_text())


def test_the_shipped_body_file_loads() -> None:
    c = config.load()
    assert c.body.substeps == 8
    assert c.kindle.reach_m > 0


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda r: r.update(version="slice-1"), "version"),
        (lambda r: r.update(extra=1), "top-level"),
        (lambda r: r["body"].pop("mass_kg"), "missing"),
        (lambda r: r["body"].update(typo_kg=1.0), "unknown"),
        (lambda r: r["body"].update(mass_kg=float("nan")), "finite positive"),
        (lambda r: r["body"].update(mass_kg=-1.0), "finite positive"),
        (lambda r: r["body"].update(mass_kg=True), "finite positive"),
        (lambda r: r["body"].update(substeps=2.5), "whole number"),
        (lambda r: r.update(kindle=[]), "mapping"),
    ],
)
def test_a_bad_body_file_is_refused_by_name(change, message: str) -> None:
    raw = copy.deepcopy(_raw())
    change(raw)
    with pytest.raises(ValueError, match=message):
        config.parse(raw)


def test_a_body_file_must_be_a_mapping() -> None:
    with pytest.raises(ValueError, match="mapping"):
        config.parse([])
