from __future__ import annotations


def build_experiment_rows(mixture, slices):
    """Build simple per-slice rows for the canonical debug harness."""
    rows = []
    for item in slices:
        seg = item.get("segment")
        row = {
            "R": item.get("R"),
            "segment_index": item.get("segment_index"),
            "start_R": getattr(seg, "start_R", None) if seg else None,
            "end_R": getattr(seg, "end_R", None) if seg else None,
            "Xliq_start": list(getattr(seg, "Xliq_start", [])) if seg else [],
            "Xliq_end": list(getattr(seg, "Xliq_end", [])) if seg else [],
            "solvent_start": getattr(seg, "solvent_start", None) if seg else None,
            "solvent_end": getattr(seg, "solvent_end", None) if seg else None,
        }
        rows.append(row)
    return rows
