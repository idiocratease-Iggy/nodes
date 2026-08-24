# MIT License
#
# Copyright (c) [2026] [Alan A. Smith]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.



from __future__ import annotations

import random
import math
from typing import Iterable, List, Dict, Any
from statistics import NormalDist


def _renormalize(vec: Dict[str, float]) -> Dict[str, float]:
    total = sum(vec.values())
    if total <= 0:
        return vec
    return {k: (v / total) for k, v in vec.items()}


def _gaussian(scale_percent: float) -> float:
    """Return a Gaussian perturbation using the inverse CDF of a normal distribution."""
    sd = min(scale_percent, 2.0) / 100.0  # cap at 2%
    dist = NormalDist(mu=0.0, sigma=sd)
    try:
        return dist.inv(random.random())
    except AttributeError:
        return dist.inv_cdf(random.random())


def apply_error(rows: Iterable[Dict[str, Any]], error_percent: float) -> List[Dict[str, Any]]:
    """
    Full experimental error model:
    1. Cross-contamination (one-way, homogeneous per phase)
    2. Analytical error (Gaussian ±, per-component)
    3. Renormalisation
    4. Updated R calculation
    5. Clamp R > 1 to 0.9999
    """

    mutated_rows = []

    for row in rows:
        new_row = dict(row)

        # -----------------------------
        # Extract composition groups
        # -----------------------------
        Xc = {k: float(new_row[k]) for k in new_row if k.startswith("Xc_")}
        Xs = {k: float(new_row[k]) for k in new_row if k.startswith("Xs_")}
        Xl = {k: float(new_row[k]) for k in new_row if k.startswith("Xliq_")}

        # -----------------------------
        # PART 1 — Cross-contamination
        # -----------------------------
        # One random seed per phase
        alpha_s = abs(_gaussian(error_percent))   # liquor → solid
        alpha_l = abs(_gaussian(error_percent))   # solid → liquor

        # Apply contamination
        Xs_cont = {k: Xs[k] + alpha_s * Xl[k.replace("Xs_", "Xliq_")] for k in Xs}
        Xl_cont = {k: Xl[k] + alpha_l * Xs[k.replace("Xliq_", "Xs_")] for k in Xl}

        # Renormalise
        Xs_cont = _renormalize(Xs_cont)
        Xl_cont = _renormalize(Xl_cont)

        # -----------------------------
        # PART 2 — Analytical error
        # -----------------------------
        # Unique random seed per component
        Xc_anal = {k: Xc[k] * (1.0 + _gaussian(error_percent)) for k in Xc}
        Xs_anal = {k: Xs_cont[k] * (1.0 + _gaussian(error_percent)) for k in Xs_cont}
        Xl_anal = {k: Xl_cont[k] * (1.0 + _gaussian(error_percent)) for k in Xl_cont}

        # Renormalise again
        Xc_final = _renormalize(Xc_anal)
        Xs_final = _renormalize(Xs_anal)
        Xl_final = _renormalize(Xl_anal)

        # -----------------------------
        # PART 3 — Updated R calculation (multi-component)
        # -----------------------------
        R_values = []

        for i in range(1, 10):  # support up to Xc_9 if needed
            kc = f"Xc_{i}"
            ks = f"Xs_{i}"
            kl = f"Xliq_{i}"

            if kc in Xc_final and ks in Xs_final and kl in Xl_final:
                xc = Xc_final[kc]
                xs = Xs_final[ks]
                xl = Xl_final[kl]

                denom = xs - xl
                if abs(denom) < 1e-12:
                    continue

                Ri = (xc - xl) / denom
                R_values.append(Ri)

        # Filter out obvious outliers
        if R_values:
            median_R = sorted(R_values)[len(R_values)//2]
            filtered = [r for r in R_values if abs(r - median_R) < 0.1]

            if not filtered:
                filtered = R_values

            R_new = sum(filtered) / len(filtered)

            # Clamp
            if R_new > 1.0:
                R_new = 0.9999
            if R_new < 0.0:
                R_new = 0.0

            new_row["R"] = R_new
            #print(
            #    f"[ERROR MODEL] mixture_id={new_row.get('mixture_id')} "
            #    f"slice={new_row.get('slice_number')} "
            #    f"R_original={row.get('R')} "
            #    f"R_mutated={R_new:.6f}"
            #)

        # -----------------------------
        # Write mutated compositions back
        # -----------------------------
        for k, v in Xc_final.items():
            new_row[k] = v
        for k, v in Xs_final.items():
            new_row[k] = v
        for k, v in Xl_final.items():
            new_row[k] = v

        mutated_rows.append(new_row)

    return mutated_rows
