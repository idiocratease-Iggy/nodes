# canonical_solvent.py
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


from typing import List


def compute_relsolvol_from_cascade(
    cumR: List[float],
    nodes_mix: List[List[float]],
    X_feed: List[float],
) -> List[float]:
    """
    Canonical implementation of M2L / RelSol / RelSolVol, mirroring test_run.py.

    Inputs
    ------
    cumR       : cumulative recoveries, length = 1 + n_nodes
                 (cumR[0] = 1.0 feed, cumR[k] = product of Rk up to node k)
    nodes_mix  : liquor compositions at each node, length = n_nodes
    X_feed     : initial feed composition vector

    Returns
    -------
    solvent_per_node : list of RelSolVol values at each node (length = n_nodes),
                       in the same order as nodes_mix.
    """

    n_components = len(X_feed)

    # ------------------------------------------------------------
    # Build summary_matrix: feed row + node rows + final pure row
    # ------------------------------------------------------------
    summary_matrix: List[List[float]] = []

    # Feed row (100% recovery, initial composition)
    summary_matrix.append([1.0] + list(X_feed))

    # Node rows: use cumR[1:], aligned with nodes_mix
    for i, comp in enumerate(nodes_mix):
        recovery_val = cumR[i + 1]
        summary_matrix.append([recovery_val] + list(comp))

    # Final pure row: recovery = 0, one component at 100%, others 0
    # (same convention as test_run.py)
    final_pure = [0.0] + [1.0] + [0.0] * (n_components - 1)
    summary_matrix.append(final_pure)

    # ------------------------------------------------------------
    # Extract recoveries and compositions
    # ------------------------------------------------------------
    recoveries = [row[0] for row in summary_matrix]
    compositions = [row[1:] for row in summary_matrix]

    # ------------------------------------------------------------
    # M2L: mass removed to mother liquors per step
    # ------------------------------------------------------------
    M2L: List[float] = [0.0]
    for i in range(1, len(recoveries)):
        M2L.append(recoveries[i - 1] - recoveries[i])

    # ------------------------------------------------------------
    # RelSol: relative solubility per step
    # ------------------------------------------------------------
    RelSol: List[float] = [0.0]
    # Rmax is the recovery at the penultimate row (before final pure)
    Rmax = recoveries[-2]

    for i in range(1, len(compositions)):
        # Last row (final pure): RelSol = 1.0 by definition
        if i == len(compositions) - 1:
            RelSol.append(1.0)
            continue

        # If recovery below Rmax, use M2L / Rmax
        if recoveries[i] < Rmax:
            RelSol.append(M2L[i] / Rmax)
            continue

        prev = compositions[i - 1]
        curr = compositions[i]

        removed_fraction = None
        removed_components = []

        # Detect a degenerate multi-removal event: multiple components that were
        # present in the previous state are now zero in the current state.
        for p, c in zip(prev, curr):
            if p > 0.0 and c == 0.0:
                removed_components.append(p)

        if removed_components:
            removed_fraction = sum(removed_components)
        else:
            # Fallback: largest drop in composition
            diffs = [p - c for p, c in zip(prev, curr)]
            max_drop = max(diffs)
            if max_drop > 0.0:
                removed_fraction = max_drop

        # If still unknown, RelSol = 0.0
        if removed_fraction is None or removed_fraction == 0.0:
            RelSol.append(0.0)
            continue

        RelSol.append(M2L[i] / removed_fraction)

    # ------------------------------------------------------------
    # RelSolVol: cumulative solvent requirement
    # NOTE: M2L is already a fraction (0..1), not a percent. Use the
    # corrected fractional mass-transfer term directly; do not divide by 100.
    # ------------------------------------------------------------
    RelSolVol: List[float] = [0.0]
    for i in range(1, len(RelSol)):
        RelSolVol.append(RelSolVol[-1] + RelSol[i] * M2L[i])

    # ------------------------------------------------------------
    # Return node-level RelSolVol (exclude feed and final pure)
    # ------------------------------------------------------------
    n_nodes = len(nodes_mix)
    # summary_matrix rows: 0 = feed, 1..n_nodes = nodes, n_nodes+1 = final pure
    # RelSolVol aligned with these rows, so take indices 1..n_nodes
    solvent_per_node = [RelSolVol[i] for i in range(1, 1 + n_nodes)]

    return solvent_per_node
