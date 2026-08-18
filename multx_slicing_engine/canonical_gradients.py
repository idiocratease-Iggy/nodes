# canonical_gradients.py

from typing import List

try:
    from multx_slicing_engine.gradient_engine import GradientEngine, SegmentGradients
except ImportError:
    from gradient_engine import GradientEngine, SegmentGradients


def compute_segment_gradients(state) -> List[SegmentGradients]:
    """Build a list of SegmentGradients for the given canonical state."""
    engine = GradientEngine(state)
    return engine.get_segment_gradients()
