from __future__ import annotations

from typing import Iterable


def _segment_for_recovery(segments, R: float):
    candidates = []
    for seg in segments:
        if abs(seg.start_R - seg.end_R) <= 1e-12:
            continue
        # Direct recovery lookup only; no solvent plateau or degenerate_main_pair
        # adjustment is applied in the canonical slice logic.
        if seg.end_R - 1e-12 <= R <= seg.start_R + 1e-12:
            candidates.append(seg)

    if not candidates:
        return None

    return min(candidates, key=lambda seg: (abs(seg.start_R - R), abs(seg.end_R - R), seg.index))


def compute_slices(state, slice_R: Iterable[float]):
    """Return slice metadata for the requested recovery cuts."""
    slices = []
    for target in list(slice_R):
        selected = _segment_for_recovery(state.segments, float(target))
        if selected is None:
            slices.append({"R": float(target), "segment_index": None, "segment": None})
        else:
            slices.append({"R": float(target), "segment_index": selected.index, "segment": selected})
    return slices
