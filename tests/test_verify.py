"""The verification harness against observables whose answers are known exactly (verify_harness §4).

Each study uses a synthetic observable, value = exact + C * h**p, so the harness's answer can be checked in closed form.
"""

import math

import pytest

from simcore.verify import Band, Run, Work, band_gate, converges, same_class_under_refinement

W = Work(substeps=1, cell_substeps=1)


def _power_law(p, c=1.0, exact=10.0, by="dx_m"):
    """value = exact + c * h**p, with h the run's spacing or step: an observable of known order p."""

    def observable(run):
        return exact + c * getattr(run, by) ** p, Work(run.steps, run.steps * 7)

    return observable


def _space(*dxs):
    return [Run(dx, 1.0, 10) for dx in dxs]


def _time(*steps):
    return [Run(0.1, 100.0 / n, n) for n in steps]


# --- converges, against a closed form ---


def test_a_second_order_observable_shows_order_two_against_its_closed_form():
    study = converges(_power_law(2), _space(0.2, 0.1, 0.05), exact=10.0)
    assert study.orders == pytest.approx((2.0, 2.0))
    assert study.errors == pytest.approx((0.04, 0.01, 0.0025))
    assert study.reference_converged is True
    assert study.work == (Work(10, 70),) * 3


def test_a_time_study_refines_the_step_at_a_fixed_spacing():
    study = converges(_power_law(1, by="dt_s"), _time(10, 20, 40), exact=10.0)
    assert study.orders == pytest.approx((1.0, 1.0))
    assert [w.substeps for w in study.work] == [10, 20, 40]


def test_an_exact_fine_answer_has_infinite_order_and_two_exact_answers_have_none():
    exact_at_fine = converges(lambda r: (10.0 if r.dx_m < 0.15 else 10.5, W), _space(0.2, 0.1), exact=10.0)
    assert exact_at_fine.orders == (math.inf,)
    both_exact = converges(lambda r: (10.0, W), _space(0.2, 0.1), exact=10.0)
    assert math.isnan(both_exact.orders[0])
    coarse_exact = converges(lambda r: (10.0 if r.dx_m > 0.15 else 10.5, W), _space(0.2, 0.1), exact=10.0)
    assert coarse_exact.orders == (-math.inf,)


# --- converges, against the finest run (Richardson) ---


def test_richardson_recovers_the_order_without_a_closed_form():
    study = converges(_power_law(2), _space(0.4, 0.2, 0.1, 0.05), order_tol=1e-6)
    assert study.orders == pytest.approx((2.0, 2.0))
    assert study.reference_converged is True
    assert study.errors[-1] == 0.0


def test_a_reference_whose_order_is_still_moving_is_reported_unconverged():
    # value = 10 + h**2 + h: the order drifts from 1 toward 2 as h shrinks, so the last two orders disagree.
    study = converges(lambda r: (10 + r.dx_m**2 + r.dx_m, W), _space(1.6, 0.8, 0.4, 0.2), order_tol=0.05)
    assert study.reference_converged is False


def test_three_runs_give_one_order_and_never_claim_a_converged_reference():
    study = converges(_power_law(2), _space(0.2, 0.1, 0.05), order_tol=1.0)
    assert len(study.orders) == 1
    assert study.reference_converged is False


@pytest.mark.parametrize("order_tol", [None, 0.0, -1.0, math.inf, math.nan])
def test_a_reference_study_refuses_a_missing_or_meaningless_order_tolerance(order_tol):
    with pytest.raises(ValueError, match="order_tol"):
        converges(_power_law(2), _space(0.4, 0.2, 0.1), order_tol=order_tol)


def test_a_reference_study_refuses_two_runs():
    with pytest.raises(ValueError, match="three runs"):
        converges(_power_law(2), _space(0.2, 0.1), order_tol=0.1)


def test_a_reference_study_refuses_a_changing_refinement_ratio():
    with pytest.raises(ValueError, match="one refinement ratio"):
        converges(_power_law(2), _space(0.4, 0.2, 0.05), order_tol=0.1)


# --- what makes one study ---


def test_a_study_refuses_a_single_run():
    with pytest.raises(ValueError, match="at least two runs"):
        converges(_power_law(2), _space(0.2), exact=10.0)


def test_a_study_that_refines_space_and_time_together_is_refused():
    # E2: mixing them lets their errors cancel.
    with pytest.raises(ValueError, match="not both or neither"):
        converges(_power_law(2), [Run(0.2, 10.0, 10), Run(0.1, 5.0, 20)], exact=10.0)


def test_a_study_that_refines_nothing_is_refused():
    with pytest.raises(ValueError, match="not both or neither"):
        converges(_power_law(2), [Run(0.2, 10.0, 10), Run(0.2, 10.0, 10)], exact=10.0)


def test_a_study_whose_runs_cover_different_times_is_refused():
    with pytest.raises(ValueError, match="same simulated time"):
        converges(_power_law(2), [Run(0.2, 1.0, 10), Run(0.1, 1.0, 20)], exact=10.0)


def test_a_study_that_goes_fine_to_coarse_is_refused():
    with pytest.raises(ValueError, match="coarse to fine"):
        converges(_power_law(2), _space(0.1, 0.2), exact=10.0)


# --- band_gate ---


def _threshold_at(edge_by_dx):
    return lambda run, x: x >= edge_by_dx[run.dx_m]


def test_the_band_spans_each_grids_flip_point():
    xs = [float(x) for x in range(11)]
    band = band_gate(_threshold_at({0.2: 6.0, 0.1: 4.0, 0.05: 5.0}), xs, _space(0.2, 0.1, 0.05))
    assert band == Band(edges=(6.0, 4.0, 5.0), low=4.0, high=6.0)


def test_the_flip_point_is_found_at_either_end_of_the_range():
    band = band_gate(_threshold_at({0.2: 1.0, 0.1: 10.0}), [float(x) for x in range(11)], _space(0.2, 0.1))
    assert band.edges == (1.0, 10.0)


@pytest.mark.parametrize("edge", [0.0, 99.0])  # true already at the first value; never true
def test_an_outcome_the_range_doesnt_bracket_is_refused(edge):
    with pytest.raises(ValueError, match="isn't bracketed"):
        band_gate(_threshold_at({0.2: edge}), [0.0, 1.0, 2.0], _space(0.2))


@pytest.mark.parametrize("xs", [[1.0], [0.0, 2.0, 1.0], [0.0, 0.0, 1.0]])
def test_band_gate_refuses_control_values_that_dont_ascend(xs):
    with pytest.raises(ValueError, match="strictly ascending"):
        band_gate(_threshold_at({0.2: 1.0}), xs, _space(0.2))


def test_band_gate_refuses_no_runs():
    with pytest.raises(ValueError, match="at least one run"):
        band_gate(_threshold_at({}), [0.0, 1.0], [])


# --- same_class_under_refinement ---


def test_an_outcome_that_holds_at_every_refinement_is_the_same_class():
    assert same_class_under_refinement(lambda run: run.seconds > 50, Run(0.2, 10.0, 10)) is True


def test_an_outcome_that_flips_when_time_is_refined_is_caught():
    # The splitting failure the physics spike found at 0.2 m: the class depends on the step count.
    assert same_class_under_refinement(lambda run: run.steps > 50, Run(0.2, 10.0, 10)) is False


def test_refinement_keeps_the_simulated_time():
    seen = []

    def record(run):
        seen.append(run)
        return True

    same_class_under_refinement(record, Run(0.2, 10.0, 10), factors=(1, 4))
    assert seen == [Run(0.2, 10.0, 10), Run(0.2, 2.5, 40)]
    assert {run.seconds for run in seen} == {100.0}


@pytest.mark.parametrize("factors", [(), (0, 10), (1, 2.5), (True, 10)])
def test_refinement_refuses_factors_that_arent_whole_and_positive(factors):
    with pytest.raises(ValueError, match="factors"):
        same_class_under_refinement(lambda run: True, Run(0.2, 10.0, 10), factors=factors)


# --- Run ---


@pytest.mark.parametrize(
    ("dx_m", "dt_s", "steps", "field"),
    [
        (0.0, 1.0, 1, "dx_m"),
        (math.nan, 1.0, 1, "dx_m"),
        (0.1, -1.0, 1, "dt_s"),
        (0.1, math.inf, 1, "dt_s"),
        (0.1, 1.0, 0, "steps"),
        (0.1, 1.0, 1.5, "steps"),
        (0.1, 1.0, True, "steps"),
    ],
)
def test_a_run_refuses_a_meaningless_discretisation(dx_m, dt_s, steps, field):
    with pytest.raises(ValueError, match=field):
        Run(dx_m, dt_s, steps)


def test_the_harness_is_deterministic():
    first = converges(_power_law(2), _space(0.4, 0.2, 0.1, 0.05), order_tol=1e-6)
    assert converges(_power_law(2), _space(0.4, 0.2, 0.1, 0.05), order_tol=1e-6) == first
