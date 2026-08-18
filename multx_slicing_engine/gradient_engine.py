from dataclasses import dataclass
from typing import List

try:
    from multx_slicing_engine.canonical_types import EutecticPathState, Segment
except ImportError:
    from canonical_types import EutecticPathState, Segment


@dataclass
class SegmentGradients:
    index: int
    gradients: List[float]
    intercepts: List[float]
    solvol_grad: float
    solvol_int: float
    start_R: float
    end_R: float


class GradientEngine:
    """Build piecewise-linear segment gradients for canonical state data."""

    def __init__(self, state: EutecticPathState):
        self.state = state
        self.segments: List[SegmentGradients] = []
        self._build_gradients()

    def _build_gradients(self) -> None:
        self.segments.clear()

        for seg in self.state.segments:
            R0 = seg.start_R
            R1 = seg.end_R
            X0 = seg.Xliq_start
            X1 = seg.Xliq_end
            S0 = seg.solvent_start
            S1 = seg.solvent_end

            dR = R1 - R0
            if abs(dR) < 1e-12:
                gradients = [0.0 for _ in X0]
                intercepts = list(X0)
                solvol_grad = 0.0
                solvol_int = S0
            else:
                gradients = [(x1 - x0) / dR for x0, x1 in zip(X0, X1)]
                intercepts = [x0 - m * R0 for x0, m in zip(X0, gradients)]
                solvol_grad = (S1 - S0) / dR
                solvol_int = S0 - solvol_grad * R0

            sg = SegmentGradients(
                index=seg.index,
                gradients=gradients,
                intercepts=intercepts,
                solvol_grad=solvol_grad,
                solvol_int=solvol_int,
                start_R=R0,
                end_R=R1,
            )
            self.segments.append(sg)

    def get_segment_gradients(self) -> List[SegmentGradients]:
        return self.segments
