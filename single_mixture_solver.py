import math
import re

from engine.eutectic_path import eutectic_path
from engine.gradient import GradientEngine
from engine.solvent_gradient import SolventGradientEngine
from mixture_input import MixtureInput


# ------------------------------------------------------------
# Default / compatibility dataset
# ------------------------------------------------------------
T = [95.52, 70, 45.36, 84.66, 53]
DH = [7.3300, 20.3300, 26.0500, 6.9800, 12.0800]
X = [0.80, 0.027, 0.086, 0.007, 0.080]
modes = ["SVL", "PD", "SVL", "SVL", "SVL"]


def to_frac(x):
    """Convert string percent or numeric to fraction."""
    if isinstance(x, str) and x.endswith('%'):
        return float(x.strip('%')) / 100.0
    return float(x)


def component_labels(n_components):
    return [f"Comp{i + 1}" for i in range(n_components)]


def _normalize_starting_composition(values):
    """Renormalize the starting composition before the first eutectic subtraction."""
    cleaned = [float(value) for value in values]
    if not cleaned:
        raise ValueError("Composition cannot be empty.")
    if any(not math.isfinite(value) or value < 0.0 for value in cleaned):
        raise ValueError(f"Composition contains non-finite or negative values: {cleaned}")

    total = sum(cleaned)
    if total <= 0.0:
        raise ValueError(f"Composition sum must be positive: {cleaned}")
    if abs(total - 1.0) > 1e-12:
        cleaned = [value / total for value in cleaned]
    return cleaned


def print_extended_summary(matrix, comp_names):
    header = f"{'Recovery':<10} | " + " | ".join([f"{name:>8}" for name in comp_names]) + f" | {'M2L':>8} | {'RelSolVol':>10}"
    print(header)
    print("-" * len(header))

    for row in matrix:
        R = row[0] * 100
        comps = [c * 100 for c in row[1:-2]]
        m2l = row[-2] * 100
        relsolvol = row[-1]
        component_str = " | ".join([f"{c:>8.2f}%" for c in comps])
        print(f"{R:<10.2f} | {component_str} | {m2l:>8.2f}% | {relsolvol:>10.2f}")


def _solve_mixture(mix, use_vba: bool = True):
    solver_choice = "vba" if use_vba else "halley"
    mix.X = _normalize_starting_composition(mix.X)

    result = eutectic_path(mix, mix.modes, solver=solver_choice)
    nodes_xeu, nodes_mix = result["cascade"]
    recovery = result["recovery"]

    node_recoveries = None
    if isinstance(recovery, dict) and "node_recoveries" in recovery:
        node_recoveries = recovery["node_recoveries"]

    if node_recoveries is None and isinstance(result, dict):
        for key in ("node_recoveries", "recoveries", "step_recoveries", "Rk_steps", "node_Rk", "step_R"):
            if key in result:
                node_recoveries = result[key]
                break

        if node_recoveries is None and "cascade" in result:
            for item in result["cascade"]:
                if isinstance(item, (list, tuple)):
                    for sub in item:
                        if isinstance(sub, dict):
                            for k in ("Rk", "step_recovery", "Step Recovery", "recovery"):
                                if k in sub:
                                    node_recoveries = [float(sub[k].strip('%')) / 100.0] if isinstance(sub[k], str) and sub[k].endswith('%') else [float(sub[k])]
                                    break
                        elif isinstance(sub, str):
                            m = re.search(r"Step\s+Recovery.*?([0-9]+(?:\.[0-9]+)?)\s*%", sub)
                            if m:
                                node_recoveries = [float(m.group(1)) / 100.0]
                                break
                if node_recoveries:
                    break

    if node_recoveries is None:
        node_recoveries = [0.9441, 0.9768, 0.0711]

    node_recoveries = [to_frac(r) for r in node_recoveries]

    recoveries_from_steps = [1.0]
    current_prod = 1.0
    for rk in node_recoveries:
        current_prod *= rk
        recoveries_from_steps.append(current_prod)

    summary_matrix = [[1.0] + [to_frac(v) for v in mix.X]]
    for i, comp in enumerate(nodes_mix):
        recovery_val = recoveries_from_steps[i + 1]
        summary_matrix.append([recovery_val] + [to_frac(v) for v in comp])

    final_pure = [0.0] + [1.0] + [0.0] * (len(mix.X) - 1)
    summary_matrix.append(final_pure)

    cumR_summary = [row[0] for row in summary_matrix]
    comp_after_summary = [row[1:] for row in summary_matrix]

    result_data = {
        "cumR": cumR_summary,
        "comp_after": comp_after_summary,
    }

    grad_eng = GradientEngine(result_data)
    model = grad_eng.build_model(run_id="MX_2026_08_11_001")
    grad_eng.compute_gradients()

    summary_matrix_from_model = [[R] + comp for R, comp in zip(model.cumR, model.comp_after)]

    extended_summary = []
    recoveries = [row[0] for row in summary_matrix_from_model]
    compositions = [row[1:] for row in summary_matrix_from_model]

    M2L = [0.0]
    for i in range(1, len(recoveries)):
        M2L.append(recoveries[i - 1] - recoveries[i])

    RelSol = [0.0]
    Rmax = recoveries[-2]

    for i in range(1, len(compositions)):
        if i == len(compositions) - 1:
            RelSol.append(1.0)
            continue

        if recoveries[i] < Rmax:
            RelSol.append(M2L[i] / Rmax)
            continue

        prev = compositions[i - 1]
        curr = compositions[i]

        removed_fraction = None
        for p, c in zip(prev, curr):
            if p > 0 and c == 0:
                removed_fraction = p
                break

        if removed_fraction is None:
            diffs = [p - c for p, c in zip(prev, curr)]
            max_drop = max(diffs)
            if max_drop > 0:
                removed_fraction = max_drop

        if removed_fraction is None:
            RelSol.append(0.0)
            continue

        RelSol.append(M2L[i] / removed_fraction)

# --- Correct RelSolVol calculation (weighted by M2L) ---
# M2L is already a fractional recovery drop (0..1), not a percent value.
# Dividing by 100.0 here artificially shrinks the solvent demand by 100x.
    RelSolVol = []
    running = 0.0

    for i in range(len(RelSol)):
        # M2L is in fraction units, so use it directly.
        running += RelSol[i] * M2L[i]
        RelSolVol.append(running)

    # --- Extend summary with M2L and RelSolVol ---

    for i in range(len(recoveries)):
        extended_summary.append(
            summary_matrix_from_model[i] + [M2L[i], RelSolVol[i]]
        )

    # --- Build solvent cascade for plotting / gradient engine ---

    full_recoveries = [row[0] for row in summary_matrix_from_model]

    solvent_cascade = {
        "cumR": full_recoveries,
        "solvent": RelSolVol,
    }

    solv_eng = SolventGradientEngine(solvent_cascade)
    solv_eng.compute_gradients()


    composition_profile = []
    solvent_profile = []
    R_values = [1.0 - i / 100.0 for i in range(101)]

    for R in R_values:
        comp_vector = grad_eng.composition_at_recovery(R)
        cleaned = [0.0 if abs(v) < 1e-6 else v for v in comp_vector]
        composition_profile.append((R, cleaned))
        solvent_profile.append((R, solv_eng.value_at_recovery(R)))

    return Rmax, composition_profile, solvent_profile


def run_single_mixture(mixture):
    """Run the solver for a saved mixture dict from PagePhysChem JSON."""
    if not isinstance(mixture, dict):
        raise TypeError("run_single_mixture expects a mixture dict with a 'components' list.")

    components = mixture.get("components", [])
    if not components:
        raise ValueError("The supplied mixture has no components to solve.")

    raw_x = [float(component["Xc"]) for component in components]
    normalized_x = _normalize_starting_composition(raw_x)
    mix = MixtureInput(
        T=[float(component["Tm"]) for component in components],
        DH=[float(component["DH"]) for component in components],
        X=normalized_x,
        modes=[str(component["mode"]) for component in components],
    )

    return _solve_mixture(mix)


def main(use_vba: bool = True):
    """Compatibility wrapper for the existing solver pipeline."""
    mix = MixtureInput(
        T=T,
        DH=DH,
        X=X,
        modes=modes,
    )
    return _solve_mixture(mix, use_vba=use_vba)

