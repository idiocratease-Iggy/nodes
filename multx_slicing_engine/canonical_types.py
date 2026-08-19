from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class Node:
    index: int
    Tk: float
    Xeu: List[float]
    Xliq_after: List[float]
    recovery: float
    removed_components: List[int]
    multi_removal: bool
    solvent: float


@dataclass
class Segment:
    index: int
    start_R: float
    end_R: float
    Xliq_start: List[float]
    Xliq_end: List[float]
    solvent_start: float
    solvent_end: float
    metadata: Dict[str, Any] = None


@dataclass
class EutecticPathState:
    solver: str
    initial_mixture: Any
    nodes: List[Node]
    segments: List[Segment]
    Rmax: float
    final_purity: float
    tk_nodes: List[float]
    degenerate_cascade: bool
    solvent_at_Rmax: float = 0.0
