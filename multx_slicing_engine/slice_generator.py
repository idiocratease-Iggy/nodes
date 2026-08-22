# multx_slicing_engine/slice_generator.py

from multx_slicing_engine.evaluate_recovery import evaluate_at_recovery

import random

try:
    from multx_slicing_engine.evaluate_recovery import _segment_for_recovery
except ImportError:
    from evaluate_recovery import _segment_for_recovery


def debug_slicing_state(state, slice_results):
    """Print the canonical node/segment summary and the resulting slice values."""
    # print("\n=== DEBUG: canonical nodes ===")
    for node in getattr(state, "nodes", []):
        pass

    # print("\n=== DEBUG: canonical segments ===")
    for seg in getattr(state, "segments", []):
        pass

    segments = list(getattr(state, "segments", []))

    # print("\n=== DEBUG: slice values ===")
    for slice_result in slice_results:
        if isinstance(slice_result, dict):
            R = float(slice_result.get("R", 0.0))
            slice_xsol = list(slice_result.get("Xsol", []))
            slice_xliq = list(slice_result.get("Xliq", []))
        else:
            R = float(getattr(slice_result, "R", 0.0))
            slice_xsol = list(getattr(slice_result, "Xsol", []))
            slice_xliq = list(getattr(slice_result, "Xliq", []))

        seg = _segment_for_recovery(segments, R)
        seg_xsol = list(getattr(seg, "Xsol", []))
        pass

    # print("\n=== DEBUG: slice summary complete ===")


def generate_slices_for_mixture(summary, num_slices, jitter=0.2):
    """
    Generate slice points between R=1.0 and Rmax for a single mixture.

    The anchor positions are distributed evenly and symmetrically across the
    full recovery interval, excluding the exact endpoints. Each point is then
    perturbed by a small jitter proportional to the local spacing between
    adjacent anchors.
    """
    import random

    state = summary["state"]
    grads = summary["segment_grads"]
    Rmax = summary["Rmax"]

    if num_slices <= 0:
        return []

    interval = max(1e-9, 1.0 - Rmax)
    step = interval / (num_slices + 1)

    # Interior anchors that are evenly spread between 1.0 and Rmax, with the
    # midpoint centered in the interval.
    anchor_points = [1.0 - step * (k + 1) for k in range(num_slices)]

    # Jitter relative to local spacing so points remain near their intended
    # symmetric arrangement without collapsing toward either endpoint.
    jitter_fraction = max(0.0, min(0.5, jitter))
    jitter_range = step * jitter_fraction

    jittered_points = []
    for R in anchor_points:
        eps = random.uniform(-jitter_range, jitter_range)
        Rj = R + eps
        # Keep the points strictly inside the valid interval, but not equal to
        # the exact endpoints.
        Rj = max(Rmax + 1e-9, min(1.0 - 1e-9, Rj))
        jittered_points.append(Rj)

    jittered_points = sorted(jittered_points, reverse=True)
    results = []
    for Rj in jittered_points:
        res = evaluate_at_recovery(state, grads, Rj)
        results.append(res)

    # Wire the standalone forensic debug helper into the normal slice-generation flow.
    debug_slicing_state(state, results)
    return results




def print_slices_to_terminal(mixture_id, slice_results, state=None):
    """
    Pretty-print slice results to terminal.
    """
    # print("\n==============================================")
    # print(f" SLICES FOR MIXTURE {mixture_id}")
    # print("==============================================\n")

    if state is not None:
        debug_slicing_state(state, slice_results)

    for s in slice_results:
        xs = ", ".join(f"{v*100:.2f}%" for v in s.Xliq)
        xsol = ", ".join(f"{v:.6f}" for v in s.Xsol)
        # print(f"Slice at R={s.R:.4f}")
        # print(f"  seg.index={s.seg_index}  seg.start_R={s.seg_start_R:.6f}  seg.end_R={s.seg_end_R:.6f}")
        # print(f"  seg.Xsol=[{xsol}]")
        # print(f"  Xliq=[{xs}]")
        # print(f"  sum(Xliq)={sum(s.Xliq):.6f}  min={min(s.Xliq):.6f}  max={max(s.Xliq):.6f}")
        # print(f"  Solvent(RelSolVol@slice): {s.solvent:.4f}")
        # print("")


def resolve_slice_count(summary, fallback_num_slices=3):
    """Resolve the requested slice count from the loaded mixture JSON, with a safe fallback."""
    mixture = summary.get("mixture") if isinstance(summary, dict) else None
    if mixture is None:
        return int(fallback_num_slices)

    raw = getattr(mixture, "raw", mixture) or {}
    if not isinstance(raw, dict):
        return int(fallback_num_slices)

    raw_slicing = raw.get("slicing") if isinstance(raw.get("slicing"), dict) else {}
    metadata = raw.get("metadata", {}) if isinstance(raw.get("metadata", {}), dict) else {}
    metadata_slicing = metadata.get("slicing") if isinstance(metadata.get("slicing"), dict) else {}
    slicing_cfg = raw_slicing or metadata_slicing or {}

    configured_slices = slicing_cfg.get("max_solvent_volumes")
    if configured_slices is not None:
        try:
            count = int(configured_slices)
            if count > 0:
                return count
        except (TypeError, ValueError):
            pass

    return int(fallback_num_slices)


def generate_slices_all_mixtures(canonical_results, num_slices=3):
    """
    Generate slices for all mixtures in canonical_results.
    Returns a list of dicts:
        {
            "mixture_id": ...,
            "slices": [slice_result, ...]
        }
    """
    all_slices = []

    for summary in canonical_results:
        mixture = summary["mixture"]
        mixture_id = mixture.mixture_id

        slice_count = resolve_slice_count(summary, fallback_num_slices=num_slices)
        slice_results = generate_slices_for_mixture(summary, slice_count)

        all_slices.append({
            "mixture_id": mixture_id,
            "slices": slice_results
        })

    return all_slices
