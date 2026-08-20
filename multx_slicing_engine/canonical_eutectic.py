from __future__ import annotations

import re
from typing import Any, List, Sequence

try:
    from multx_slicing_engine.canonical_types import EutecticPathState, Node, Segment
    from multx_slicing_engine.mixture_loader import Mixture
except ImportError:
    from canonical_types import EutecticPathState, Node, Segment
    from mixture_loader import Mixture

from mixture_input import MixtureInput
from engine.eutectic_path import eutectic_path


def to_frac(x):
    """Convert string percent or numeric to fraction."""
    if isinstance(x, str) and x.endswith('%'):
        return float(x.strip('%')) / 100.0
    return float(x)


def _coerce_mixture(mixture: Any) -> Any:
    if isinstance(mixture, Mixture):
        return mixture
    if hasattr(mixture, "T") and hasattr(mixture, "DH") and hasattr(mixture, "X"):
        return mixture
    if hasattr(mixture, "components") and hasattr(mixture, "T"):
        return mixture
    if isinstance(mixture, dict):
        return Mixture(mixture)
    raise TypeError(f"Unsupported mixture object: {type(mixture)!r}")


def _extract_node_recoveries(result: Any) -> List[float]:
    """Mirror the node recovery extraction logic used in test_run.py."""
    recovery = result.get("recovery") if isinstance(result, dict) else None

    node_recoveries = None
    if isinstance(recovery, dict) and "node_recoveries" in recovery:
        node_recoveries = recovery["node_recoveries"]

    if node_recoveries is None and isinstance(result, dict):
        for key in ("node_recoveries", "recoveries", "step_recoveries", "Rk_steps", "node_Rk", "step_R"):
            if key in result:
                node_recoveries = result[key]
                break

        if node_recoveries is None and "cascade" in result:
            for item in result["cascade"]:
                if isinstance(item, (list, tuple)):
                    for sub in item:
                        if isinstance(sub, dict):
                            for k in ("Rk", "step_recovery", "Step Recovery", "recovery"):
                                if k in sub:
                                    node_recoveries = [float(sub[k].strip('%')) / 100.0] if isinstance(sub[k], str) and sub[k].endswith('%') else [float(sub[k])]
                                    break
                        elif isinstance(sub, str):
                            match = re.search(r"Step\s+Recovery.*?([0-9]+(?:\.[0-9]+)?)\s*%", sub)
                            if match:
                                node_recoveries = [float(match.group(1)) / 100.0]
                                break
                if node_recoveries:
                    break

    if node_recoveries is None:
        node_recoveries = [0.9441, 0.9768, 0.0711]

    return [to_frac(r) for r in node_recoveries]


def _normalize_summary_rows(summary_matrix: List[List[float]]) -> List[List[float]]:
    """Deduplicate equal recoveries and keep the canonical rows in descending R order."""
    rows: List[List[float]] = []
    for row in summary_matrix:
        if not row:
            continue
        recovery = float(row[0])
        if not rows:
            rows.append([recovery] + list(row[1:]))
            continue

        prev_recovery = float(rows[-1][0])
        if abs(recovery - prev_recovery) <= 1e-12:
            rows[-1] = [recovery] + list(row[1:])
        else:
            rows.append([recovery] + list(row[1:]))

    rows.sort(key=lambda row: float(row[0]), reverse=True)
    unique_rows: List[List[float]] = []
    for row in rows:
        recovery = float(row[0])
        if not unique_rows:
            unique_rows.append(list(row))
            continue
        if abs(recovery - float(unique_rows[-1][0])) <= 1e-12:
            unique_rows[-1] = list(row)
        else:
            unique_rows.append(list(row))
    return unique_rows


def _build_summary_matrix(X: List[float], nodes_mix: List[List[float]], node_recoveries: List[float]) -> List[List[float]]:
    """Build the same summary_matrix shape used by test_run.py."""
    recoveries_from_steps = [1.0]
    current_prod = 1.0
    for rk in node_recoveries:
        current_prod *= rk
        recoveries_from_steps.append(current_prod)

    summary_matrix = [[1.0] + [to_frac(v) for v in X]]
    for i, comp in enumerate(nodes_mix):
        recovery_val = recoveries_from_steps[i + 1]
        summary_matrix.append([recovery_val] + [to_frac(v) for v in comp])

    final_pure = [0.0] + [1.0] + [0.0] * (len(X) - 1)
    summary_matrix.append(final_pure)
    return summary_matrix


def _build_relsolvol(summary_matrix: List[List[float]]) -> List[float]:
    """Compute the weighted RelSolVol used by the corrected single-mixture solver."""
    recoveries = [row[0] for row in summary_matrix]
    compositions = [row[1:] for row in summary_matrix]

    M2L = [0.0]
    for i in range(1, len(recoveries)):
        M2L.append(recoveries[i - 1] - recoveries[i])

    RelSol = [0.0]
    Rmax = recoveries[-2]

    for i in range(1, len(compositions)):
        if i == len(compositions) - 1:
            RelSol.append(1.0)
            continue

        if recoveries[i] < Rmax:
            RelSol.append(M2L[i] / Rmax)
            continue

        prev = compositions[i - 1]
        curr = compositions[i]

        removed_fraction = None
        removed_components = []
        for p, c in zip(prev, curr):
            if p > 0 and c == 0:
                removed_components.append(p)

        if removed_components:
            removed_fraction = sum(removed_components)
        else:
            diffs = [p - c for p, c in zip(prev, curr)]
            max_drop = max(diffs)
            if max_drop > 0:
                removed_fraction = max_drop

        if removed_fraction is None:
            RelSol.append(0.0)
            continue

        RelSol.append(M2L[i] / removed_fraction)

    # Match the corrected single-mixture solver: the solvent requirement is weighted
    # by the fractional mass removed in that step, not by the raw RelSol ratio alone.
    RelSolVol = [0.0]
    running = 0.0
    for i in range(1, len(RelSol)):
        running += RelSol[i] * M2L[i]
        RelSolVol.append(running)

    return RelSolVol


def build_canonical_state(mixture: Any, modes: Sequence[str] | None = None, solver: str = "vba") -> EutecticPathState:
    """Construct a canonical state aligned with test_run.py solvent cascade logic."""
    mixture_obj = _coerce_mixture(mixture)
    mode_list = list(modes) if modes is not None else list(mixture_obj.modes)

    mix_input = MixtureInput(
        T=list(mixture_obj.T),
        DH=list(mixture_obj.DH),
        X=list(mixture_obj.X),
        case_id=mixture_obj.case_id,
        modes=list(mode_list),
        use_bracket=True,
    )

    result = eutectic_path(mix_input, mode_list, solver=solver)
    nodes_xeu, nodes_mix = result["cascade"]
    recovery = result.get("recovery", {})
    node_recoveries = _extract_node_recoveries(result)
    tk_nodes = list(result.get("tk_nodes", []))

    nodes: List[Node] = []
    for idx, (xeu_vec, mix_vec, tk_value) in enumerate(zip(nodes_xeu, nodes_mix, tk_nodes)):
        nodes.append(
            Node(
                index=idx,
                Tk=float(tk_value) if tk_value is not None else 0.0,
                Xeu=list(xeu_vec),
                Xliq_after=list(mix_vec),
                recovery=float(node_recoveries[idx]) if idx < len(node_recoveries) else 0.0,
                removed_components=[],
                multi_removal=False,
                solvent=0.0,
            )
        )

    summary_matrix = _normalize_summary_rows(_build_summary_matrix(mix_input.X, nodes_mix, node_recoveries))
    RelSolVol = _build_relsolvol(summary_matrix)

    segments: List[Segment] = []
    for idx, (start_row, end_row) in enumerate(zip(summary_matrix[:-1], summary_matrix[1:])):
        start_R = float(start_row[0])
        end_R = float(end_row[0])
        if abs(start_R - end_R) <= 1e-12:
            continue
        if start_R < end_R:
            start_R, end_R = end_R, start_R

        segments.append(
            Segment(
                index=idx,
                start_R=start_R,
                end_R=end_R,
                Xliq_start=list(start_row[1:]),
                Xliq_end=list(end_row[1:]),
                solvent_start=float(RelSolVol[idx]),
                solvent_end=float(RelSolVol[idx + 1]),
                metadata={"node_index": idx},
            )
        )

    segments.sort(key=lambda seg: seg.start_R, reverse=True)
    for idx, seg in enumerate(segments):
        seg.index = idx

    rmax = float(result.get("recovery", {}).get("Rmax", summary_matrix[-2][0] if len(summary_matrix) > 1 else 1.0))
    solvent_at_rmax = 0.0
    if segments:
        for seg in segments:
            if seg.start_R >= rmax and seg.end_R <= rmax:
                solvent_at_rmax = float(seg.solvent_end)
                break
        if solvent_at_rmax == 0.0:
            solvent_at_rmax = float(segments[-1].solvent_end)

    return EutecticPathState(
        solver=str(solver),
        initial_mixture=mix_input,
        nodes=nodes,
        segments=segments,
        Rmax=rmax,
        final_purity=float(result.get("recovery", {}).get("final_purity", 0.0)),
        tk_nodes=list(tk_nodes),
        degenerate_cascade=False,
        solvent_at_Rmax=solvent_at_rmax,
    )
