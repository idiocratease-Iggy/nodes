import math
from types import SimpleNamespace

from multx_slicing_engine.matrix_layer import _diagnose_slice_liquor, build_matrix_layer


def test_diagnoses_negative_liquor_without_changing_slice_recovery():
    Xc = [0.10, 0.80]
    Xs = [0.60, 0.20]
    original_R = 0.80

    adjusted_R, adjusted_xliq, negative_count, correction_flagged = _diagnose_slice_liquor(
        Xc,
        Xs,
        original_R,
    )

    assert negative_count == 1
    assert correction_flagged is True
    assert math.isclose(adjusted_R, 1.0 / 6.0, rel_tol=1e-9)
    assert adjusted_xliq[0] == 0.0
    assert math.isclose(adjusted_xliq[1], 3.2, rel_tol=1e-9)


def test_build_matrix_layer_reports_negative_liquor_count_and_adjusted_recovery():
    summary = {
        "mixture": SimpleNamespace(mixture_id="mix_1", X=[0.10, 0.80]),
        "state": SimpleNamespace(segments=[]),
        "num_slices": 1,
        "slices": [SimpleNamespace(R=0.80, solvent=0.50, Xliq=[0.60, 0.20])],
    }

    layer = build_matrix_layer([summary])
    row = layer["slice_arrays"]["slice_count_1"][0]

    assert row["negative_liquor_count"] == 1
    assert math.isclose(row["adjusted_R"], 1.0 / 6.0, rel_tol=1e-9)
    assert row["R"] == 0.80
    assert row["correction_delta_R"] > 0.0


def test_build_matrix_layer_uses_slice_composition_as_xs_input():
    summary = {
        "mixture": SimpleNamespace(mixture_id="mix_1", X=[0.10, 0.80]),
        "state": SimpleNamespace(segments=[]),
        "num_slices": 1,
        "slices": [SimpleNamespace(R=0.80, solvent=0.50, Xsol=[0.60, 0.20], Xliq=[0.20, 0.40])],
    }

    layer = build_matrix_layer([summary])
    row = layer["slice_arrays"]["slice_count_1"][0]

    assert row["Xs"] == [0.20, 0.40]
