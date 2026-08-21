from __future__ import annotations

from typing import Any, Dict, List, Optional

import math

try:
    from multx_slicing_engine.slice_generator import generate_slices_for_mixture
except ImportError:  # pragma: no cover
    from slice_generator import generate_slices_for_mixture


def print_matrix_layer(layer: Dict[str, Any]) -> None:
    """Print the matrix-layer records to the terminal for comparison with the base block."""
    print("\n==============================================")
    print(" MATRIX LAYER SUMMARY")
    print("==============================================\n")

    print("[MIXTURE ANCHORS]")
    for anchor in layer.get("mixture_anchors", []):
        print(
            f"mixture_id={anchor['mixture_id']} | "
            f"components={anchor['component_count']} | "
            f"Rmax={anchor['Rmax']:.6f} | "
            f"RelSolVol(Rmax)={anchor['RelSolVol_Rmax']:.6f} | "
            f"slice_count={anchor['slice_count']}"
        )
        print(f"  Xc={anchor['Xc']}")

    print("\n[SEGMENT ROWS]")
    for segment in layer.get("segments", []):
        print(
            f"mixture_id={segment['mixture_id']} | seg={segment['segment_index']} | "
            f"R={segment['start_R']:.6f} → {segment['end_R']:.6f} | "
            f"solvent={segment['solvent_start']:.6f} → {segment['solvent_end']:.6f}"
        )
        print(f"  Xliq_start={segment['Xliq_start']}")
        print(f"  Xliq_end={segment['Xliq_end']}")

    print("\n[SLICE ROWS]")
    for scenario_name, rows in sorted(layer.get("slice_arrays", {}).items()):
        print(f"scenario={scenario_name}")
        for row in rows:
            print(
                f"  mixture_id={row['mixture_id']} | slice_index={row['slice_index']} | "
                f"R={row['R']:.6f} | RelSolVol={row['RelSolVol']:.6f}"
            )
            print(f"    Xc={row['Xc']}")
            print(f"    Xs={row['Xs']}")
            print(f"    Xliq={row['Xliq']}")
            print(f"    R_check={row['R_check']}")
            print(
                f"    correction_applied={row.get('correction_applied', False)} | "
                f"correction_flagged={row.get('correction_flagged', False)} | "
                f"delta_R={row.get('correction_delta_R', 0.0):.6f}"
            )


def _safe_list(values: Any) -> List[float]:
    if values is None:
        return []
    if isinstance(values, (list, tuple)):
        return [float(v) for v in values]
    return [float(values)]


def _compute_liquor_from_slice(Xc: List[float], Xs: List[float], R: float) -> List[float]:
    if abs(R - 1.0) < 1e-12:
        return [0.0 for _ in Xc]

    return [((R * xs) - xc) / (R - 1.0) for xc, xs in zip(Xc, Xs)]


def _clip_tiny_negative_values(values: List[float], threshold: float = 1e-12) -> List[float]:
    return [0.0 if abs(value) <= threshold and value < 0.0 else value for value in values]


def _adjust_slice_for_negative_liquor(
    Xc: List[float],
    Xs: List[float],
    R: float,
    tolerance: float = 0.005,
    min_value: float = 0.0,
    eps: float = 1e-12,
) -> tuple[float, List[float], bool, bool]:
    """Adjust R minimally so any negative liquor compositions become non-negative.

    The base relation is Xl = (R*Xs - Xc)/(R - 1). When one or more components
    become negative, this routine uses a small bracketed bisection search to find
    a nearby R that makes the minimum liquor composition cross zero. This is a
    stable 1-D root solve and avoids relying on a heavier optimizer dependency.
    """

    if abs(R - 1.0) < 1e-12:
        return R, [0.0 for _ in Xc], False, False

    xliq = _compute_liquor_from_slice(Xc, Xs, R)
    if all(value >= min_value - eps for value in xliq):
        return R, xliq, False, False

    def _f(candidate_R: float) -> float:
        candidate_xliq = _compute_liquor_from_slice(Xc, Xs, candidate_R)
        return min(value for value in candidate_xliq) - min_value

    def _bisect_root(lower: float, upper: float) -> float:
        lower_value = _f(lower)
        upper_value = _f(upper)
        if lower_value == 0.0:
            return lower
        if upper_value == 0.0:
            return upper

        for _ in range(80):
            midpoint = 0.5 * (lower + upper)
            midpoint_value = _f(midpoint)
            if abs(midpoint_value) <= eps:
                return midpoint
            if lower_value * midpoint_value <= 0.0:
                upper = midpoint
                upper_value = midpoint_value
            else:
                lower = midpoint
                lower_value = midpoint_value
        return 0.5 * (lower + upper)

    candidates: List[tuple[float, float]] = []
    if R < 1.0:
        left = max(1e-8, 0.0)
        right = max(1e-8, min(R, 1.0 - 1e-8))
        if left < right:
            left_value = _f(left)
            right_value = _f(right)
            if left_value * right_value <= 0.0:
                candidates.append((left, right))
        right = max(1e-8, min(1.0 - 1e-8, 1.0 - 1e-6))
        if right > R:
            right_value = _f(right)
            if _f(R) * right_value <= 0.0:
                candidates.append((R, right))
    else:
        left = max(1e-8, R)
        right = max(left + 1e-6, 1.0 + 1e-6)
        if left < right:
            left_value = _f(left)
            right_value = _f(right)
            if left_value * right_value <= 0.0:
                candidates.append((left, right))

    if not candidates:
        return R, xliq, False, False

    best_R = R
    best_xliq = xliq
    best_delta = float("inf")
    for lower, upper in candidates:
        adjusted_R = _bisect_root(lower, upper)
        adjusted_xliq = _compute_liquor_from_slice(Xc, Xs, adjusted_R)
        delta = abs(adjusted_R - R)
        if delta < best_delta:
            best_R = adjusted_R
            best_xliq = adjusted_xliq
            best_delta = delta

    correction_applied = abs(best_R - R) > eps
    correction_flagged = correction_applied and abs(best_R - R) > tolerance * max(abs(R), 1.0)
    return best_R, best_xliq, correction_applied, correction_flagged


def _compute_r_check(Xc: List[float], Xs: List[float], Xl: List[float]) -> List[float]:
    results: List[float] = []
    for xc, xs, xl in zip(Xc, Xs, Xl):
        denom = xs - xl
        if abs(denom) < 1e-12:
            results.append(float("nan"))
        else:
            results.append((xc - xl) / denom)
    return results


def build_matrix_layer(canonical_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a structured matrix-layer view from canonical harness results.

    The base pipeline remains unchanged. This layer consumes the existing summary
    records and exposes them in a simpler shape for later matrix construction.
    """

    mixture_anchors: List[Dict[str, Any]] = []
    segment_rows: List[Dict[str, Any]] = []
    slice_arrays: Dict[str, List[Dict[str, Any]]] = {}

    for summary in canonical_results:
        mixture = summary.get("mixture")
        if mixture is None:
            continue

        state = summary.get("state")
        slices = summary.get("slices") or []
        num_slices = int(summary.get("num_slices", len(slices) or 3))
        configured_slices = list(slices)

        Xc = _safe_list(getattr(mixture, "X", []))

        anchor = {
            "mixture_id": getattr(mixture, "mixture_id", ""),
            "component_count": len(Xc),
            "Xc": Xc,
            "Rmax": float(summary.get("Rmax", 0.0)),
            "RelSolVol_Rmax": float(summary.get("RelSolVol_Rmax", 0.0)),
            "slice_count": num_slices,
            "segment_count": len(getattr(state, "segments", []) or []),
        }
        mixture_anchors.append(anchor)

        for seg in getattr(state, "segments", []) or []:
            if getattr(seg, "end_R", 0.0) == getattr(seg, "start_R", 0.0):
                continue

            segment_rows.append({
                "mixture_id": getattr(mixture, "mixture_id", ""),
                "segment_index": getattr(seg, "index", 0),
                "start_R": float(getattr(seg, "start_R", 0.0)),
                "end_R": float(getattr(seg, "end_R", 0.0)),
                "solvent_start": float(getattr(seg, "solvent_start", 0.0)),
                "solvent_end": float(getattr(seg, "solvent_end", 0.0)),
                "Xliq_start": _safe_list(getattr(seg, "Xliq_start", [])),
                "Xliq_end": _safe_list(getattr(seg, "Xliq_end", [])),
            })

        for scenario_count in range(1, num_slices + 1):
            if scenario_count == num_slices and configured_slices:
                scenario_slices = configured_slices
            else:
                scenario_slices = generate_slices_for_mixture(summary, scenario_count)

            for slice_index, slice_result in enumerate(scenario_slices, start=1):
                Xs = _safe_list(getattr(slice_result, "Xsol", []))
                R = float(getattr(slice_result, "R", 0.0))
                relsolvol = float(getattr(slice_result, "solvent", 0.0))
                derived_xliq = _compute_liquor_from_slice(Xc, Xs, R)
                original_R = R
                adjusted_R, adjusted_xliq, correction_applied, correction_flagged = _adjust_slice_for_negative_liquor(
                    Xc,
                    Xs,
                    R,
                    tolerance=0.005,
                )
                if correction_applied:
                    derived_xliq = adjusted_xliq
                    R = adjusted_R
                derived_xliq = _clip_tiny_negative_values(derived_xliq)
                r_check = _compute_r_check(Xc, Xs, derived_xliq)

                row = {
                    "mixture_id": getattr(mixture, "mixture_id", ""),
                    "slice_count": scenario_count,
                    "slice_index": slice_index,
                    "R": R,
                    "RelSolVol": relsolvol,
                    "Xc": Xc,
                    "Xs": Xs,
                    "Xliq": derived_xliq,
                    "R_check": r_check,
                    "mass_balance_ok": not correction_flagged,
                    "correction_applied": correction_applied,
                    "correction_delta_R": abs(original_R - adjusted_R) if correction_applied else 0.0,
                    "correction_flagged": correction_flagged,
                }

                scenario_key = f"slice_count_{scenario_count}"
                slice_arrays.setdefault(scenario_key, []).append(row)

    return {
        "mixture_anchors": mixture_anchors,
        "segments": segment_rows,
        "slice_arrays": slice_arrays,
    }
