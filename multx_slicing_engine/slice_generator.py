# multx_slicing_engine/slice_generator.py

from multx_slicing_engine.evaluate_recovery import evaluate_at_recovery

import random

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

    return results




def print_slices_to_terminal(mixture_id, slice_results):
    """
    Pretty-print slice results to terminal.
    """
    print("\n==============================================")
    print(f" SLICES FOR MIXTURE {mixture_id}")
    print("==============================================\n")

    for s in slice_results:
        xs = ", ".join(f"{v*100:.2f}%" for v in s.Xliq)
        print(f"Slice at R={s.R:.4f}")
        print(f"  Solvent: {s.solvent:.4f}")
        print(f"  Composition: [{xs}]")
        print("")


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
