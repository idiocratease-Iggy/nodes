# canonical_eutectic.py

from dataclasses import dataclass
from typing import List, Dict, Any

from engine.cascade import run_cascade
from engine.xeu import compute_xeu


@dataclass
class Node:
    index: int
    Tk: float                  # eutectic temperature at node
    Xeu: List[float]           # solid composition at node
    Xliq_after: List[float]    # liquor composition after node
    recovery: float            # node recovery R_k
    removed_components: List[int]  # indices of components removed at this node
    multi_removal: bool        # True if >1 component removed
    solvent: float             # solvent volume at node


@dataclass
class Segment:
    index: int
    start_R: float
    end_R: float
    Xliq_start: List[float]
    Xliq_end: List[float]
    solvent_start: float      # ← NEW
    solvent_end: float        # ← NEW
    metadata: Dict[str, Any] = None



@dataclass
class EutecticPathState:
    solver: str
    initial_mixture: Any       # mixture object (as used in MultXeu)
    nodes: List[Node]
    segments: List[Segment]
    Rmax: float
    final_purity: float
    tk_nodes: List[float]
    degenerate_cascade: bool   # True if fewer nodes than n_components - 1


def build_canonical_state(mixture, modes, solver: str = "vba") -> EutecticPathState:
    """
    Build a canonical representation of the eutectic path for a given mixture.

    Uses the existing cascade physics (run_cascade + compute_xeu),
    but wraps the results into structured Node and Segment objects.
    """
    # 1. Run the cascade using existing physics
    nodes_xeu, nodes_mix, lambdas, node_recoveries, cumulative_recovery, final_purity, tk_nodes, solvent_values = \
        run_cascade(mixture.copy(), modes, solver=solver)

    n_components = mixture.n_components
    expected_nodes = max(n_components - 1, 0)
    actual_nodes = len(nodes_xeu)
    degenerate_cascade = actual_nodes < expected_nodes

    nodes: List[Node] = []

    # 2. Build Node objects
    for idx, (Xeu, Xliq_after, Rk, Tk, Sol) in enumerate(
        zip(nodes_xeu, nodes_mix, node_recoveries, tk_nodes, solvent_values), start=1
    ):

        # removed components: those with Xeu > 0
        removed = [i for i, x in enumerate(Xeu) if x > 1e-12]
        multi_removal = len(removed) > 1

        node = Node(
            index=idx,
            Tk=Tk,
            Xeu=Xeu,
            Xliq_after=Xliq_after,
            recovery=Rk,
            removed_components=removed,
            multi_removal=multi_removal,
            solvent=Sol,
        )
        nodes.append(node)

    segments: List[Segment] = []

    # 3. Build Segment objects (between successive nodes)
    # cumR is descending from 1 → cumulative_recovery
    # we reconstruct cumR from node_recoveries
    cumR: List[float] = [1.0]
    for Rk in node_recoveries:
        cumR.append(cumR[-1] * Rk)

    # segments: [k] → between node k and node k+1
    for k in range(len(nodes) - 1):
        seg = Segment(
            index=k + 1,
            start_R=cumR[k],
            end_R=cumR[k + 1],
            Xliq_start=nodes[k].Xliq_after,
            Xliq_end=nodes[k + 1].Xliq_after,
            solvent_start=nodes[k].solvent,
            solvent_end=nodes[k + 1].solvent,
            metadata={},
    )

        segments.append(seg)

    state = EutecticPathState(
        solver=solver,
        initial_mixture=mixture,
        nodes=nodes,
        segments=segments,
        Rmax=cumulative_recovery,
        final_purity=final_purity,
        tk_nodes=tk_nodes,
        degenerate_cascade=degenerate_cascade,
    )

    return state
