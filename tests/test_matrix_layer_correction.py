import math

from multx_slicing_engine.matrix_layer import _adjust_slice_for_negative_liquor


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
