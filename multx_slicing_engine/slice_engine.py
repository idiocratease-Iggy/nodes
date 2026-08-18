from __future__ import annotations

from typing import Iterable


def compute_slices(state, slice_R: Iterable[float]):
    """Return slice metadata for the requested recovery cuts."""
    slices = []
    for target in list(slice_R):
        selected = None
        for seg in state.segments:
            if seg.end_R <= target <= seg.start_R:
                selected = seg
                break
        if selected is None:
            slices.append({"R": float(target), "segment_index": None, "segment": None})
        else:
            slices.append({"R": float(target), "segment_index": selected.index, "segment": selected})
    return slices
