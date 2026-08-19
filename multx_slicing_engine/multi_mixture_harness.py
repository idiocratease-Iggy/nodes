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
except ImportError:
    from mixture_loader import mixture_from_json
    from canonical_eutectic import build_canonical_state
    from canonical_gradients import compute_segment_gradients


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

    print("\n==============================================")
    print(" CANONICAL NODES & GRADIENTS")
    print("==============================================")

    for seg in state.segments:
        if seg.end_R == seg.start_R:
            continue

        m_sol = (seg.solvent_end - seg.solvent_start) / (seg.end_R - seg.start_R)

        xs = ", ".join(f"{v:.6f}" for v in seg.Xliq_start)
        xe = ", ".join(f"{v:.6f}" for v in seg.Xliq_end)

        print(f"\nSEGMENT {seg.index}")
        print(f"Rec: {seg.start_R:.6f} → {seg.end_R:.6f}")
        print(f"Solvent: {seg.solvent_start:.6f} → {seg.solvent_end:.6f}")
        print(f"m_sol: {m_sol:.12f}")
        print(f"Xc_start: [{xs}]")
        print(f"Xc_end:   [{xe}]")

    print("\n----------------------------------------------")
    print(f"Rmax: {state.Rmax:.6f}")
    print(f"RelSolVol(Rmax): {state.solvent_at_Rmax:.6f}")
    print("----------------------------------------------\n")


def run_multi_mixture_harness(matrix_json_path, max_mixtures=5):
    """Reads matrix JSON and runs canonical pipeline for up to max_mixtures mixtures."""
    print("\n==============================================")
    print(" MULTI-MIXTURE CANONICAL HARNESS")
    print("==============================================\n")

    resolved_path = resolve_matrix_path(matrix_json_path)
    print(f"Loading matrix JSON from: {resolved_path}")

    with open(resolved_path, "r") as f:
        matrix = json.load(f)

    if not isinstance(matrix, list):
        raise ValueError("Matrix JSON must be a list of mixture dictionaries.")

    if not matrix:
        return []

    # Extract number of mixtures from JSON if present
    num_mix = matrix[0].get("num_unique_mixtures", len(matrix)) if isinstance(matrix[0], dict) else len(matrix)
    limit = min(len(matrix), max_mixtures, num_mix)
    results = []

    for idx, mix_dict in enumerate(matrix[:limit]):
        print(f"\n----------------------------------------------")
        print(f" MIXTURE {idx+1} / {limit}")
        print(f" mixture_id: {mix_dict.get('mixture_id', 'N/A')}")
        print(f"----------------------------------------------")

        summary = run_single_mixture(mix_dict)
        results.append(summary)

        print_canonical_summary(summary)

    return results

from multx_slicing_engine.slice_generator import (
    generate_slices_all_mixtures,
    print_slices_to_terminal
)

if __name__ == "__main__":
    matrix_json_path = os.path.join(DATA_DIR, "physchem_matrix.json")
    canonical_results = run_multi_mixture_harness(matrix_json_path, max_mixtures=5)

    # Generate slices using the JSON-defined slice count when present.
    all_slices = generate_slices_all_mixtures(canonical_results)

    # Print slices to terminal
    for entry in all_slices:
        print_slices_to_terminal(entry["mixture_id"], entry["slices"])

