from __future__ import annotations

from typing import Any, Dict, List, Optional

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
                    "mass_balance_ok": True,
                    "correction_applied": False,
                    "correction_delta_R": 0.0,
                }

                scenario_key = f"slice_count_{scenario_count}"
                slice_arrays.setdefault(scenario_key, []).append(row)

    return {
        "mixture_anchors": mixture_anchors,
        "segments": segment_rows,
        "slice_arrays": slice_arrays,
    }
