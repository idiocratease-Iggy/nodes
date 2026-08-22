# multi_component_harness.py

import json
import sys
import os

from numpy import matrix

ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, "data")
sys.path.append(ROOT)


try:
    from multx_slicing_engine.mixture_loader import mixture_from_json
    from multx_slicing_engine.canonical_eutectic import build_canonical_state
    from multx_slicing_engine.canonical_gradients import compute_segment_gradients
    from multx_slicing_engine.matrix_layer import build_matrix_layer, print_matrix_layer
except ImportError:
    from mixture_loader import mixture_from_json
    from canonical_eutectic import build_canonical_state
    from canonical_gradients import compute_segment_gradients
    from matrix_layer import build_matrix_layer, print_matrix_layer


def resolve_matrix_path(matrix_json_path):
    """Resolve a matrix JSON path relative to working dir, repo root, or data folder."""
    if not matrix_json_path:
        matrix_json_path = "physchem_matrix.json"

    candidate = os.path.abspath(matrix_json_path)
    if os.path.exists(candidate):
        return candidate

    project_root_candidate = os.path.join(ROOT, matrix_json_path)
    if os.path.exists(project_root_candidate):
        return project_root_candidate

    data_candidate = os.path.join(DATA_DIR, os.path.basename(matrix_json_path))
    if os.path.exists(data_candidate):
        return data_candidate

    # Last fallback: if caller passed a filename without directory, assume data folder.
    if os.path.dirname(matrix_json_path) == "":
        return os.path.join(DATA_DIR, matrix_json_path)

    return candidate


def run_single_mixture(mix_dict):
    """Runs canonical pipeline for one mixture dict from matrix JSON."""
    mixture = mixture_from_json(mix_dict)
    modes = mixture.modes

    state = build_canonical_state(mixture, modes, solver="vba")
    segment_grads = compute_segment_gradients(state)

    return {
        "mixture": mixture,
        "state": state,
        "segment_grads": segment_grads,
        "Rmax": state.Rmax,
        "RelSolVol_Rmax": state.solvent_at_Rmax,
    }


def print_canonical_summary(summary):
    """Prints node and gradient info for one mixture."""
    state = summary["state"]

    # print("\n==============================================")
    # print(" CANONICAL NODES & GRADIENTS")
    # print("==============================================")

    for seg in state.segments:
        if seg.end_R == seg.start_R:
            continue

        m_sol = (seg.solvent_end - seg.solvent_start) / (seg.end_R - seg.start_R)

        xs = ", ".join(f"{v:.6f}" for v in seg.Xliq_start)
        xe = ", ".join(f"{v:.6f}" for v in seg.Xliq_end)

        # print(f"\nSEGMENT {seg.index}")
        # print(f"Rec: {seg.start_R:.6f} → {seg.end_R:.6f}")
        # print(f"Solvent: {seg.solvent_start:.6f} → {seg.solvent_end:.6f}")
        # print(f"m_sol: {m_sol:.12f}")
        # print(f"Xc_start: [{xs}]")
        # print(f"Xc_end:   [{xe}]")

    # print("\n----------------------------------------------")
    # print(f"Rmax: {state.Rmax:.6f}")
    # print(f"RelSolVol(Rmax): {state.solvent_at_Rmax:.6f}")
    # print("----------------------------------------------\n")


def _extract_num_unique_mixtures(matrix):
    """Return the configured unique-mixture count when present, else the list length."""
    if not isinstance(matrix, list) or not matrix:
        return 0

    first = matrix[0]
    if isinstance(first, dict):
        return int(first.get("num_unique_mixtures", len(matrix)))
    return len(matrix)


def _extract_max_solvent_volumes(mix_dict):
    """Return slicing.max_solvent_volumes for a mixture dict if present, else None."""
    if not isinstance(mix_dict, dict):
        return None

    slicing_cfg = mix_dict.get("slicing") if isinstance(mix_dict.get("slicing"), dict) else {}
    if not slicing_cfg and isinstance(mix_dict.get("metadata"), dict):
        slicing_cfg = mix_dict["metadata"].get("slicing") if isinstance(mix_dict["metadata"].get("slicing"), dict) else {}

    if not isinstance(slicing_cfg, dict):
        return None

    value = slicing_cfg.get("max_solvent_volumes")
    if value is None:
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _run_multi_mixture_harness(matrix, max_mixtures=None):
    """Shared canonical run loop used by JSON/GUI entry points."""
    if not isinstance(matrix, list):
        raise ValueError("Matrix JSON must be a list of mixture dictionaries.")

    if not matrix:
        return []

    if max_mixtures is None:
        limit = len(matrix)
    else:
        try:
            limit = int(max_mixtures)
        except (TypeError, ValueError):
            limit = len(matrix)
        if limit <= 0:
            limit = len(matrix)

    num_mix = _extract_num_unique_mixtures(matrix)
    if num_mix > 0:
        limit = min(limit, len(matrix), num_mix)
    else:
        limit = min(limit, len(matrix))

    results = []

    for idx, mix_dict in enumerate(matrix[:limit]):
        # print(f"\n----------------------------------------------")
        # print(f" MIXTURE {idx+1} / {limit}")
        # print(f" mixture_id: {mix_dict.get('mixture_id', 'N/A')}")
        # print(f"----------------------------------------------")

        summary = run_single_mixture(mix_dict)
        results.append(summary)

        print_canonical_summary(summary)

    return results


def _append_slice_results(canonical_results):
    """Generate and print slice output for each summary in the canonical results."""
    slice_results = []
    for summary in canonical_results:
        mixture = summary["mixture"]
        raw = getattr(mixture, "raw", {}) or {}
        slicing_cfg = raw.get("slicing") or raw.get("metadata", {}).get("slicing") or {}
        num_slices = int(slicing_cfg.get("max_solvent_volumes", 3)) if slicing_cfg.get("max_solvent_volumes") is not None else 3
        if num_slices <= 0:
            num_slices = 3

        summary["num_slices"] = num_slices
        summary["slices"] = generate_slices_for_mixture(summary, num_slices)
        slice_results.append({
            "mixture_id": mixture.mixture_id,
            "slices": summary["slices"],
        })

    # print("\n==============================================")
    # print(" SLICES FOR ALL MIXTURES")
    # print("==============================================\n")
    for entry in slice_results:
        print_slices_to_terminal(entry["mixture_id"], entry["slices"])

    return canonical_results


def _emit_matrix_layer_summary(canonical_results):
    """Build and print the matrix-layer view after the base-block results are ready."""
    layer = build_matrix_layer(canonical_results)
    print_matrix_layer(layer)
    return layer


def run_multi_mixture_harness_from_json(json_path, max_mixtures=None):
    """Load a matrix JSON file and run the canonical harness for the configured subset."""
    # print("DEBUG: Harness JSON mode called, path =", json_path)
    resolved_path = resolve_matrix_path(json_path)
    # print("\n==============================================")
    # print(" MULTI-MIXTURE CANONICAL HARNESS")
    # print("==============================================\n")
    # print(f"Loading matrix JSON from: {resolved_path}")

    with open(resolved_path, "r") as f:
        matrix = json.load(f)

    results = _run_multi_mixture_harness(matrix, max_mixtures=max_mixtures)
    _append_slice_results(results)
    _emit_matrix_layer_summary(results)
    # print("DEBUG: Harness JSON mode returning", len(results) if isinstance(results, list) else results)
    return results


def run_multi_mixture_harness_from_gui(matrix_dict_list, max_mixtures=None):
    """Run the canonical harness from the already-built GUI matrix list."""
    # print("DEBUG: Harness GUI mode called, mixtures =", len(matrix_dict_list) if isinstance(matrix_dict_list, list) else 0)
    # print("\n==============================================")
    # print(" MULTI-MIXTURE CANONICAL HARNESS")
    # print("==============================================\n")
    # print(f"Loading matrix from GUI list with {len(matrix_dict_list) if isinstance(matrix_dict_list, list) else 0} entries")

    canonical_results = _run_multi_mixture_harness(matrix_dict_list, max_mixtures=max_mixtures)
    # print("DEBUG: Harness GUI mode returning", len(canonical_results) if isinstance(canonical_results, list) else canonical_results)
    _append_slice_results(canonical_results)
    _emit_matrix_layer_summary(canonical_results)
    return canonical_results


def run_multi_mixture_harness(matrix_json_path, max_mixtures=None):
    """Reads matrix JSON and runs canonical pipeline for the requested number of mixtures."""
    return run_multi_mixture_harness_from_json(matrix_json_path, max_mixtures=max_mixtures)

from multx_slicing_engine.slice_generator import (
    generate_slices_all_mixtures,
    generate_slices_for_mixture,
    print_slices_to_terminal,
)

if __name__ == "__main__":
    matrix_json_path = os.path.join(DATA_DIR, "physchem_matrix.json")
    canonical_results = run_multi_mixture_harness(matrix_json_path, max_mixtures=None)

    # Generate slices using the JSON-defined slice count when present.
    all_slices = generate_slices_all_mixtures(canonical_results)

    # Print slices to terminal
    for entry in all_slices:
        print_slices_to_terminal(entry["mixture_id"], entry["slices"])

