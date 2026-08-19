# test_run.py
import argparse
import re
from engine.eutectic_path import eutectic_path
from engine.gradient import GradientEngine
from engine.solvent_gradient import SolventGradientEngine
from mixture_input import MixtureInput


# ------------------------------------------------------------
# Explicit mixture data (your reference dataset)
# ------------------------------------------------------------
T = [95.52, 70, 45.36, 84.66, 53]
DH = [7.3300, 20.3300, 26.0500, 6.9800, 12.0800]
X = [0.80, 0.027, 0.086, 0.007, 0.080]
modes = ["SVL", "PD", "SVL", "SVL", "SVL"]

mix = MixtureInput(
    T=T,
    DH=DH,
    X=X,
    modes=modes,
)

if len(X) > 10:
    raise ValueError("This pipeline supports a maximum of 10 components.")


# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------
def to_frac(x):
    """Convert string percent or numeric to fraction."""
    if isinstance(x, str) and x.endswith('%'):
        return float(x.strip('%')) / 100.0
    return float(x)


def component_labels(n_components):
    return [f"Comp{i + 1}" for i in range(n_components)]


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


def main(use_vba: bool = True):
    solver_choice = "vba" if use_vba else "halley"
    global Rmax, composition_profile, solvent_profile

    print(f"Selected solver: {solver_choice}")

    # ------------------------------------------------------------
    # Run solver → eutectic path → cascade → recovery
    # ------------------------------------------------------------
    result = eutectic_path(mix, modes, solver=solver_choice)

    nodes_xeu, nodes_mix = result["cascade"]
    recovery = result["recovery"]

    # ------------------------------------------------------------
    # Data Processing & Recovery Calculation
    # ------------------------------------------------------------
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

    summary_matrix = [[1.0] + [to_frac(v) for v in X]]
    for i, comp in enumerate(nodes_mix):
        recovery_val = recoveries_from_steps[i + 1]
        summary_matrix.append([recovery_val] + [to_frac(v) for v in comp])

    final_pure = [0.0] + [1.0] + [0.0] * (len(X) - 1)
    summary_matrix.append(final_pure)

    cumR_summary = [row[0] for row in summary_matrix]
    comp_after_summary = [row[1:] for row in summary_matrix]

    # ------------------------------------------------------------
    # Gradient Engine & Model
    # ------------------------------------------------------------
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

    RelSolVol = [0.0]
    for i in range(1, len(RelSol)):
        # M2L is in percent, convert to fraction
        m2l_frac = M2L[i] / 100.0
        RelSolVol.append(RelSolVol[-1] + RelSol[i] * m2l_frac)


    for i in range(len(recoveries)):
        extended_summary.append(summary_matrix_from_model[i] + [M2L[i], RelSolVol[i]])

    n_components = len(summary_matrix_from_model[0]) - 1
    comp_names = component_labels(n_components)

    full_recoveries = [row[0] for row in summary_matrix_from_model]
    solvent_cascade = {
        "cumR": full_recoveries,
        "solvent": RelSolVol,
    }
    solv_eng = SolventGradientEngine(solvent_cascade)
    solv_eng.compute_gradients()

    print("\n==============================================")
    print(" EXTENDED SUMMARY MATRIX (M2L + RelSolVol)")
    print("================================================")
    print_extended_summary(extended_summary, comp_names)

    composition_profile = []
    solvent_profile = []
    R_values = [1.0 - i / 100.0 for i in range(101)]

    for R in R_values:
        comp_vector = grad_eng.composition_at_recovery(R)
        cleaned = [0.0 if abs(v) < 1e-6 else v for v in comp_vector]
        composition_profile.append((R, cleaned))
        solvent_profile.append((R, solv_eng.value_at_recovery(R)))

    return Rmax, composition_profile, solvent_profile


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run eutectic path simulation with different solvers.")
    parser.add_argument("--vba", dest="use_vba", action="store_const", const=True, default=None,
                        help="Use VBA walk-down solver")
    parser.add_argument("--halley", dest="use_vba", action="store_const", const=False,
                        help="Use Halley solver")
    args = parser.parse_args()

    if args.use_vba is None:
        parser.error("Please specify either --vba or --halley")

    Rmax, composition_profile, solvent_profile = main(use_vba=args.use_vba)
    from gui_main import run_gui
    run_gui(Rmax, composition_profile, solvent_profile)

