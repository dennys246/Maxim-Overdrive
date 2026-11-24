"""O75's strict red gates: Maxim defects fixed upstream (#1773) but in no release the lock installs yet.

Each gate runs against the installed pymaxim and fails today. When the lock moves to a release that contains the fix
(1.3.5, O78), the gate passes, strict xfail turns that into a failure, and the session that moves the lock removes it
and closes its roadmap row. Each gate's check is one helper; beside each gate, a passing test runs the same helper
against a monkeypatched stand-in for the fix, so a gate that could never flip would show here as a red proof.
"""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

import numpy as np
import pytest
from packaging.requirements import Requirement

cost_tracker = pytest.importorskip("maxim.models.language.cost_tracker")
semantic = pytest.importorskip("maxim.similarity.semantic")


def _assert_a_world_time_of_zero_is_a_time(state: Path) -> None:
    """OD-I1: ``now or time.time()`` turns 0.0 into the wall clock (``CostTracker.get_totals`` is one of five sites).

    A cost recorded at t = 1 s is inside the hourly window at t = 0 s. Read at the wall clock instead, the window's
    cutoff is decades later and prunes it, so the hourly total comes back 0.0. The test reads no clock itself.
    """
    tracker = cost_tracker.CostTracker(
        {"m": cost_tracker.ModelPricing(input_price=1.0, output_price=0.0)},
        cost_tracker.CostTrackerConfig(state_path=str(state)),
    )
    cost = tracker.record(provider="p", model="m", input_tokens=1_000_000, output_tokens=0, timestamp=1.0)
    assert cost == 1.0
    assert tracker.get_totals(now=0.0)["hourly"] == cost


def _assert_a_pickled_embedding_file_is_refused(path: Path) -> None:
    """OD-I3: ``EmbeddingStore.load`` reads with ``allow_pickle=True``, so an object array in the file is unpickled.

    The file is version 1, the format 1.3.4's ``save`` writes, with object arrays, which numpy stores pickled. A
    loader with pickle off refuses it and loads nothing (#1773 returns 0 and logs the refusal).
    """
    np.savez(
        path,
        memory_ids=np.array(["mem-1"], dtype=object),
        embeddings=np.zeros((1, 4), dtype=np.float32),
        hashes_json=np.array(['{"mem-1": [1, 2]}'], dtype=object),
        version=np.array([1]),
    )
    store = semantic.EmbeddingStore(embedder=None)  # load never embeds; a real NeuralSemanticLSH may load a model
    assert store.load(str(path)) == 0
    assert len(store) == 0


def _assert_rich_14_is_admitted(requires: list[str]) -> None:
    """OD-I6: pymaxim's ``rich<14`` cap keeps every embedder off import-linter 2.7+, which needs ``rich>=14.2``."""
    rich = next(Requirement(r) for r in requires if Requirement(r).name == "rich")
    assert rich.specifier.contains("14.2.0")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="OD-I1 (Maxim #1684): a world time of 0.0 becomes the wall clock at five sites; fixed by #1773, in no "
    "release before 1.3.5 (O75, O78)",
)
def test_a_world_time_of_zero_is_a_time(tmp_path: Path) -> None:
    _assert_a_world_time_of_zero_is_a_time(tmp_path / "cost_state.json")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="OD-I3 (Maxim #1685): EmbeddingStore.load unpickles its file; fixed by #1773, in no release before 1.3.5 "
    "(O75, O78)",
)
def test_the_embedding_store_refuses_a_pickled_file(tmp_path: Path) -> None:
    _assert_a_pickled_embedding_file_is_refused(tmp_path / "embeddings.npz")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="OD-I6 (Maxim #1768): pymaxim requires rich<14; widened by #1773, in no release before 1.3.5 (O75, O78)",
)
def test_pymaxim_admits_rich_14() -> None:
    _assert_rich_14_is_admitted(metadata.requires("pymaxim") or [])


def test_the_zero_time_gate_passes_once_zero_is_honoured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand-in for the fix: a clock that reads 0.0, so ``0.0 or time.time()`` and ``0.0`` agree."""

    class _Clock:
        @staticmethod
        def time() -> float:
            return 0.0

    monkeypatch.setattr(cost_tracker, "time", _Clock)
    _assert_a_world_time_of_zero_is_a_time(tmp_path / "cost_state.json")


def test_the_pickle_gate_passes_once_pickle_is_off(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stand-in for the fix: numpy's loader with pickle off, as #1773 calls it."""
    load = np.load

    def without_pickle(file: str, allow_pickle: bool = False) -> object:
        return load(file, allow_pickle=False)

    monkeypatch.setattr(semantic.np, "load", without_pickle)
    _assert_a_pickled_embedding_file_is_refused(tmp_path / "embeddings.npz")


def test_the_rich_gate_passes_once_the_cap_is_widened() -> None:
    """Stand-in for the fix: #1773's requirement, ``rich>=13.0.0,<16.0``."""
    _assert_rich_14_is_admitted(["idna>=3.4,<4.0", "rich>=13.0.0,<16.0"])
