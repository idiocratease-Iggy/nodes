"""Experimental error mutation hook.

This module is intentionally a stub. The production error logic has not been
finalized yet, so the current behavior is a no-op multiplier for the composition
fields in order to keep the export pipeline functional while preserving the
canonical row ordering.
"""

from __future__ import annotations

from typing import Iterable, List, Dict, Any


def apply_error(rows: Iterable[Dict[str, Any]], error_percent: int) -> List[Dict[str, Any]]:
    """Return a derived copy of the rows with a placeholder error mutation.

    For now, the implementation is intentionally conservative: all composition-like
    values are multiplied by 1.0, which preserves the current dataset while keeping
    the error export path connected and testable.
    """
    mutated_rows = []
    for row in rows:
        new_row = dict(row)
        for key, value in list(new_row.items()):
            if key.startswith(("Xc_", "Xs_", "Xliq_")) and value not in (None, ""):
                try:
                    new_row[key] = float(value) * 1.0
                except (TypeError, ValueError):
                    pass
            elif key in {"R", "RelSolVol", "Rmax", "RelSolVol(Rmax)"} and value not in (None, ""):
                try:
                    new_row[key] = float(value) * 1.0
                except (TypeError, ValueError):
                    pass
        mutated_rows.append(new_row)
    return mutated_rows
