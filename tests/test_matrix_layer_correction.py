import math
from types import SimpleNamespace

from multx_slicing_engine.matrix_layer import _adjust_slice_for_negative_liquor, build_matrix_layer


def test_adjusts_r_to_remove_negative_liquor_values_and_flags_large_shift():
    Xc = [0.10, 0.80]
    Xs = [0.60, 0.20]
    original_R = 0.80

    adjusted_R, adjusted_xliq, correction_applied, correction_flagged = _adjust_slice_for_negative_liquor(
        Xc,
        Xs,
        original_R,
        tolerance=0.005,
    )

    assert correction_applied is True
    assert correction_flagged is True
    assert math.isclose(adjusted_R, 0.16666666666666666, rel_tol=1e-9)
    assert all(value >= -1e-12 for value in adjusted_xliq)


def test_build_matrix_layer_preserves_original_slice_recovery_when_correcting_liquor():
    summary = {
        "mixture": SimpleNamespace(mixture_id="mix_1", X=[0.10, 0.80]),
        "state": SimpleNamespace(segments=[]),
        "num_slices": 1,
        "slices": [SimpleNamespace(R=0.80, solvent=0.50, Xsol=[0.60, 0.20])],
    }

    layer = build_matrix_layer([summary])
    row = layer["slice_arrays"]["slice_count_1"][0]

    assert row["correction_applied"] is True
    assert row["R"] != 0.80
    assert row["correction_delta_R"] > 0.0
