# slice_engine.py

from typing import List
from evaluate_recovery import evaluate_at_recovery, SliceResult
from canonical_gradients import compute_segment_gradients
from canonical_eutectic import EutecticPathState


def compute_slices(state: EutecticPathState,
                   slice_recoveries: List[float]) -> List[SliceResult]:

    segment_grads = compute_segment_gradients(state)
    results = []

    for R in slice_recoveries:
        res = evaluate_at_recovery(state, segment_grads, R)
        results.append(res)

    return results
