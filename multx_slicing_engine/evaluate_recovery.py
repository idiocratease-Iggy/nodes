# evaluate_recovery.py

from dataclasses import dataclass
from typing import List

try:
    from multx_slicing_engine.canonical_types import EutecticPathState
    from multx_slicing_engine.canonical_gradients import SegmentGradients
except ImportError:
    from canonical_types import EutecticPathState
    from canonical_gradients import SegmentGradients


@dataclass
class SliceResult:
    R: float
    Xliq: List[float]
    Xsol: List[float]
    Ks: float
    kl: float
    solvent: float


def _segment_for_recovery(segments, R: float):
    """Pick the unique active segment for a recovery value, even when boundaries collapse."""
    candidates = []
    for seg in segments:
        if abs(seg.start_R - seg.end_R) <= 1e-12:
            continue
        if seg.end_R - 1e-12 <= R <= seg.start_R + 1e-12:
            candidates.append(seg)

    if not candidates:
        return segments[-1]

    return min(
        candidates,
        key=lambda seg: (abs(seg.start_R - R), abs(seg.end_R - R), seg.index),
    )


def evaluate_at_recovery(state: EutecticPathState,
                         segment_grads: List[SegmentGradients],
                         R: float) -> SliceResult:
    """
    Evaluate liquor composition, solid composition, solvent volume,
    and mass balance at arbitrary recovery R.
    """

    # ------------------------------------------------------------
    # 1. Clamp R to cascade domain
    # ------------------------------------------------------------
    if not state.segments:
        raise ValueError("state.segments is empty")

    last_seg = state.segments[-1]
    if R < last_seg.end_R:
        R = last_seg.end_R

    # ------------------------------------------------------------
    # 2. Find correct segment
    # ------------------------------------------------------------
    seg = _segment_for_recovery(state.segments, R)
    seg_index = seg.index
    sg = segment_grads[seg_index]

    # ------------------------------------------------------------
    # 3. Liquor composition (linear interpolation)
    # ------------------------------------------------------------
    start_R = seg.start_R
    end_R = seg.end_R
    if abs(start_R - end_R) <= 1e-12:
        Xliq = list(seg.Xliq_start)
    else:
        Xliq = []
        for x0, x1 in zip(seg.Xliq_start, seg.Xliq_end):
            if abs(x0) <= 1e-12:
                Xliq.append(0.0)
                continue
            frac = (R - start_R) / (end_R - start_R)
            Xliq.append(x0 + (x1 - x0) * frac)

    # ------------------------------------------------------------
    # 4. Solid composition
    # ------------------------------------------------------------
    node_idx = seg_index + 1
    if node_idx < len(state.nodes):
        Xsol = state.nodes[node_idx].Xeu
    else:
        Xsol = state.nodes[-1].Xeu

    # ------------------------------------------------------------
    # 5. Mass balance
    # ------------------------------------------------------------
    Ks_values = []
    for i in range(len(Xliq)):
        denom = (Xsol[i] - Xliq[i])
        if abs(denom) < 1e-12:
            continue
        Ks_values.append((state.initial_mixture.X[i] - Xliq[i]) / denom)

    Ks = sum(Ks_values) / len(Ks_values) if Ks_values else 0.0
    kl = 1 - Ks

    # ------------------------------------------------------------
    # 6. Solvent volume
    # ------------------------------------------------------------
    solvent = sg.solvol_grad * R + sg.solvol_int

    return SliceResult(
        R=R,
        Xliq=Xliq,
        Xsol=Xsol,
        Ks=Ks,
        kl=kl,
        solvent=solvent,
    )
