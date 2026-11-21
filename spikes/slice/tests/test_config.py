import copy

import pytest
import yaml
from slice_server import config


def _raw(name: str) -> dict:
    return yaml.safe_load((config.DATA / name).read_text())


def test_the_shipped_files_load() -> None:
    c = config.load()
    assert c.body.substeps == 8
    assert c.kindle.reach_m > 0
    assert c.heat.warn_c < c.heat.trip_c
    assert set(c.fuel.objects) == {"crate", "crate_far", "pallet"}
    assert c.fuel.fire.ambient_c == 20.0


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
        (lambda r: r["heat"].update(warn_c=90.0), "warn_c must be below trip_c"),
        (lambda r: r["heat"].pop("latent_j_kg"), "missing"),
    ],
)
def test_a_bad_body_file_is_refused_by_name(change, message: str) -> None:
    raw = copy.deepcopy(_raw("body.yaml"))
    change(raw)
    with pytest.raises(ValueError, match=message):
        config.parse_body(raw)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda r: r.update(version=0), "version"),
        (lambda r: r.pop("fire"), "top-level"),
        (lambda r: r["materials"]["wood"].pop("ignition_c"), "missing"),
        (lambda r: r["materials"]["wood"].update(ignition_c=-5.0), "finite positive"),
        (lambda r: r["objects"].update(crate=1.5), "at most 1"),
        (lambda r: r["objects"].update(crate="lots"), "finite positive"),
        (lambda r: r["fire"].update(ambient_c=20.0), "unknown"),
        (lambda r: r.update(objects=[]), "mapping"),
    ],
)
def test_a_bad_fuel_file_is_refused_by_name(change, message: str) -> None:
    raw = copy.deepcopy(_raw("fuel.yaml"))
    change(raw)
    with pytest.raises(ValueError, match=message):
        config.parse_fuel(raw, ambient_c=20.0)


def test_a_file_must_be_a_mapping() -> None:
    with pytest.raises(ValueError, match="mapping"):
        config.parse_body([])
    with pytest.raises(ValueError, match="mapping"):
        config.parse_fuel("fuel", ambient_c=20.0)
