# test_harness_single.py
import json
import sys
import os

from PyQt6.QtWidgets import QApplication, QFileDialog




# Add project root to Python path
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT)


try:
    from multx_slicing_engine.mixture_loader import Mixture, mixture_from_json
    from multx_slicing_engine.canonical_eutectic import build_canonical_state
    from multx_slicing_engine.canonical_gradients import compute_segment_gradients
    from multx_slicing_engine.slice_engine import compute_slices
    from multx_slicing_engine.experiment_builder import build_experiment_rows
    from multx_slicing_engine.evaluate_recovery import evaluate_at_recovery as evaluate_recovery
except ImportError:
    from mixture_loader import Mixture, mixture_from_json
    from canonical_eutectic import build_canonical_state
    from canonical_gradients import compute_segment_gradients
    from slice_engine import compute_slices
    from experiment_builder import build_experiment_rows
    from evaluate_recovery import evaluate_at_recovery as evaluate_recovery

def run_test(json_data):
    mixture = mixture_from_json(json_data)
    modes = mixture.modes

    if not mixture.active_components():
        raise ValueError("Invalid JSON: mixture.active_components() is empty after parsing.")

    state = build_canonical_state(mixture, modes, solver="vba")
    segment_grads = compute_segment_gradients(state)

    # Example slice recoveries
    slice_R = [0.9, 0.5, 0.1]

    slices = compute_slices(state, slice_R)
    rows = build_experiment_rows(mixture, slices)

    state = build_canonical_state(mixture, modes, solver="vba")
    segment_grads = compute_segment_gradients(state)

    #print("\n==============================================")
    #print(" CANONICAL SEGMENTS")
    #print("==============================================\n")

    #for seg in state.segments:
    #    # Skip degenerate segments
    #    if seg.end_R == seg.start_R:
    #        continue

    #    m_sol = (seg.solvent_end - seg.solvent_start) / (seg.end_R - seg.start_R)
    #    b_sol = seg.solvent_start - m_sol * seg.start_R

    #    xs = ", ".join(f"{v:.6f}" for v in seg.Xliq_start)
    #    xe = ", ".join(f"{v:.6f}" for v in seg.Xliq_end)

    #    print(f"SEGMENT {seg.index}")
    #    print(f"Rec: {seg.start_R:.6f} → {seg.end_R:.6f}")
    #    print(f"Solvent: {seg.solvent_start:.6f} → {seg.solvent_end:.6f}")
    #    print(f"m_sol: {m_sol:.12f}")
    #    print(f"Xc_start: [{xs}]")
    #    print(f"Xc_end:   [{xe}]\n")

    print("\n==============================================")
    print(" CANONICAL SLICE COMPOSITIONS")
    print("==============================================\n")

    slice_points = [0.90, 0.50, 0.10]

    for R in slice_points:
        result = evaluate_recovery(state, segment_grads, R)

        xs = ", ".join(f"{v * 100:.2f}%" for v in result.Xliq)
        print(f"Slice at R={R:.2f}")
        print(f"  Evaluated R: {result.R:.2f}")
        print(f"  Solvent: {result.solvent:.2f}")
        print(f"  Composition: [{xs}]")
        #print(f"  Ks: {result.Ks:.6f}, kl: {result.kl:.6f}\n")




def pick_json_file():
    app = QApplication(sys.argv)

    path, _ = QFileDialog.getOpenFileName(
        None,
        "Select MultXeu JSON File",
        "",
        "JSON Files (*.json)"
    )

    if not path:
        print("No file selected.")
        sys.exit(0)

    return path


if __name__ == "__main__":
    json_path = pick_json_file()

    with open(json_path, "r") as f:
        data = json.load(f)

    print(f"\nLoaded: {json_path}\n")
    run_test(data)
