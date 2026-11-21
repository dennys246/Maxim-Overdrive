"""Readers for the fetched files: CSV columns as numpy arrays, and Markdown tables from READMEs.

The files are untrusted data. A header that isn't the expected one, a unit that isn't the expected unit, a cell
that isn't a number or blank/NaN, or a time column that doesn't increase is refused with the file and line, never
guessed at.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import pins

Array = npt.NDArray[np.float64]

# Column-name stems and accepted units, case-insensitive. Units sit in a second row ("[g]") or in the name ("(g)").
CONE_COLUMNS = (("time", ("s",)), ("mass", ("g",)), ("hrr|heat release", ("kw/m2", "kw m-2")))


@dataclass(frozen=True)
class Table:
    """A CSV's header names and its numeric columns (NaN where a cell is blank or NaN)."""

    names: tuple[str, ...]
    units: tuple[str, ...]
    columns: tuple[Array, ...]


def _cell(text: str, where: str) -> float:
    s = text.strip()
    if s == "" or s.lower() == "nan":
        return math.nan
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"{where}: {s!r} is not a number") from None


def _split_unit(name: str) -> tuple[str, str]:
    """'Mass (g)' -> ('Mass', 'g'); 'Mass' -> ('Mass', '')."""
    n = name.strip()
    if n.endswith(")") and "(" in n:
        head, _, unit = n[:-1].rpartition("(")
        return head.strip(), unit.strip()
    return n, ""


def _is_unit_row(row: list[str]) -> bool:
    """A second header row of units: "[s],[g],..." or "s,g,..." (its first cell isn't a number)."""
    first = row[0].strip()
    if first.startswith("["):
        return True
    try:
        float(first)
    except ValueError:
        return first != "" and first.lower() != "nan"
    return False


def read_csv(path: Path) -> Table:
    """A numeric CSV: a header row, an optional "[unit]" row, then numbers. Rows that are entirely empty are skipped."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    names_units = [_split_unit(c) for c in rows[0]]
    names = tuple(n for n, _ in names_units)
    units = [u for _, u in names_units]
    body = rows[1:]
    if body and body[0] and _is_unit_row(body[0]):
        units = [c.strip().strip("[]") for c in body[0]] + [""] * (len(names) - len(body[0]))
        body = body[1:]
    data: list[list[float]] = []
    for lineno, row in enumerate(body, start=len(rows) - len(body) + 1):
        if not any(c.strip() for c in row):
            continue
        if len(row) > len(names):
            raise ValueError(f"{path}:{lineno}: {len(row)} cells under {len(names)} names")
        cells = [_cell(c, f"{path}:{lineno}") for c in row] + [math.nan] * (len(names) - len(row))
        data.append(cells)
    cols = tuple(np.array([r[j] for r in data], dtype=np.float64) for j in range(len(names)))
    t = cols[0]
    if not (np.all(np.isfinite(t)) and np.all(np.diff(t) > 0)):
        raise ValueError(f"{path}: the time column is not finite and strictly increasing")
    return Table(names=names, units=tuple(units[: len(names)]), columns=cols)


def cone_columns(path: Path) -> tuple[Array, Array, Array]:
    """Time (s), mass (g) and Q'' (kW/m²) of a cone file, after checking the first three columns' names and units."""
    table = read_csv(path)
    for j, (stems, units) in enumerate(CONE_COLUMNS):
        name = table.names[j].lower()
        unit = table.units[j].lower() if j < len(table.units) else ""
        erratum = pins.UNIT_ERRATA.get((path.stem, j))
        if erratum is not None and unit == erratum[1]:
            unit = erratum[0]
        if not any(name.startswith(s) or s in name for s in stems.split("|")):
            raise ValueError(f"{path}: column {j} is {table.names[j]!r}, expected {stems}")
        if unit not in units:
            raise ValueError(f"{path}: column {j} unit is {unit!r}, expected one of {units}")
    return table.columns[0], table.columns[1], table.columns[2]


def markdown_tables(text: str) -> list[list[list[str]]]:
    """Every pipe table in a Markdown text, as rows of stripped cells (the |---| rule row dropped)."""
    tables: list[list[list[str]]] = []
    current: list[list[str]] = []
    for line in [*text.splitlines(), ""]:
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if not all(set(c) <= set("-: ") for c in cells):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    return tables


def flameout_times(text: str) -> dict[str, float]:
    """{test name without extension: t_flameout (s)} from every README table with a t_flameout column."""
    out: dict[str, float] = {}
    for table in markdown_tables(text):
        header = [c.lower() for c in table[0]]
        cols = [j for j, c in enumerate(header) if c.startswith("t_flameout")]
        if not cols:
            continue
        j = cols[0]
        for row in table[1:]:
            name = row[0].removesuffix(".csv").removesuffix(".CSV")
            if j < len(row) and row[j]:
                out[name] = _cell(row[j], f"README row {name}")
    return out
