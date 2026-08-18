# canonical_gradients.py

from dataclasses import dataclass
from typing import List
from canonical_eutectic import EutecticPathState, Segment


@dataclass
class SegmentGradients:
    index: int
    gradients: List[float]      # m_i for each component
    intercepts: List[float]     # b_i for each component
    solvol_grad: float          # gradient for RelSolVol
    solvol_int: float           # intercept for RelSolVol


def compute_segment_gradients(state: EutecticPathState) -> List[SegmentGradients]:
    """
    Compute gradients/intercepts for each segment in the canonical state.
    Composition and solvent volume are both linear between nodes.
    """
    segment_grads = []

    for seg in state.segments:
        R0 = seg.start_R
        R1 = seg.end_R

        X0 = seg.Xliq_start
        X1 = seg.Xliq_end

        # Composition gradients
        gradients = []
        intercepts = []

        for i in range(len(X0)):
            if abs(R1 - R0) < 1e-12:
                m = 0.0
            else:
                m = (X1[i] - X0[i]) / (R1 - R0)
            b = X0[i] - m * R0
            gradients.append(m)
            intercepts.append(b)

        # Solvent volume gradients (RelSolVol)
        # We will add solvent values to segments later
        if hasattr(seg, "solvent_start") and hasattr(seg, "solvent_end"):
            if abs(R1 - R0) < 1e-12:
                sol_m = 0.0
            else:
                sol_m = (seg.solvent_end - seg.solvent_start) / (R1 - R0)
            sol_b = seg.solvent_start - sol_m * R0
        else:
            sol_m = 0.0
            sol_b = 0.0

        sg = SegmentGradients(
            index=seg.index,
            gradients=gradients,
            intercepts=intercepts,
            solvol_grad=sol_m,
            solvol_int=sol_b,
        )
        segment_grads.append(sg)

    return segment_grads
