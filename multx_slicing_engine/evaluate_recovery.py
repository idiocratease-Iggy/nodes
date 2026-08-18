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
    last_seg = state.segments[-1]
    if R < last_seg.end_R:
        R = last_seg.end_R

    # ------------------------------------------------------------
    # 2. Find correct segment
    # ------------------------------------------------------------
    seg_index = None
    for idx, seg in enumerate(state.segments):
        if seg.end_R <= R <= seg.start_R:
            seg_index = idx
            break

    if seg_index is None:
        seg_index = len(state.segments) - 1

    sg = segment_grads[seg_index]

    # ------------------------------------------------------------
    # 3. Liquor composition (linear interpolation)
    # ------------------------------------------------------------
    Xliq = [sg.gradients[i] * R + sg.intercepts[i]
            for i in range(len(sg.gradients))]

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
