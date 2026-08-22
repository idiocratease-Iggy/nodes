# engine/cascade.py
from solvers.halley import solve_eutectic_halley
from solvers.vba import solve_eutectic_walkdown

from engine.xeu import compute_xeu


def run_cascade(mixture, modes, solver="halley"):
    mix = mixture.copy()
    nodes_xeu = []
    nodes_mix = []
    lambdas = []
    node_recoveries = []
    cumulative_recovery = 1.0
    tk_nodes = []
    solvent_values = []
    solvent_total = 0.0

    while len(mix.active_components()) > 1:
        # 1. Solve eutectic
        # 1. Solve eutectic according to solver mode
        if solver == "vba":
            # Pure VBA walk-down
            Tk = solve_eutectic_walkdown(mix, modes)
            result = {"T_eutectic": Tk}

        elif solver == "hybrid":
            # Halley with fallback to VBA
            try:
                result = solve_eutectic_halley(mix, modes)
            except RuntimeError as e:
                # print(f"[HYBRID FALLBACK] case_id={mix.case_id}: {e}")
                Tk = solve_eutectic_walkdown(mix, modes)
                result = {"T_eutectic": Tk}

        elif solver == "halley":
        # Pure Halley (no fallback)
            result = solve_eutectic_halley(mix, modes)

        Tk_node = result["T_eutectic"]
        tk_nodes.append(Tk_node)

        # 2. Compute Xeu
        Xeu = compute_xeu(Tk_node, mix, modes)
        nodes_xeu.append(Xeu)

        # 3. Protocol Ratios: r_i = Xeu[i] / X[i]
        active = mix.active_components()
        ratios = {
            i: Xeu[i] / mix.X[i]
            for i in active
            if mix.X[i] > 0.0 and Xeu[i] > 0.0
        }

        if not ratios:
            break

        # 4. Dominant Selection and Lambda
        dominant_idx = max(ratios, key=ratios.get)
        lam = ratios[dominant_idx]

        # 5. Scale mixture
        scaled = [lam * mix.X[i] for i in range(mix.n_components)]
        S_scaled = sum(scaled)

        # 6. Subtract and Clamp
        new_X = [max(scaled[i] - Xeu[i], 0.0) for i in range(mix.n_components)]
        S_new = sum(new_X)

        if S_new <= 0.0:
            break

        # 7. Recovery Math
        Rk = S_new / S_scaled
        node_recoveries.append(Rk)
        cumulative_recovery *= Rk

        # 8. Relative solvent volume accumulates with each separation step.
        solvent_total += max(0.0, 1.0 - Rk)
        solvent_values.append(solvent_total)

        # 9. Renormalize
        mix.X = [x / S_new for x in new_X]
        nodes_mix.append(mix.X[:])
        lambdas.append(lam)

    # Final purity: the fraction of the remaining component in the final mix
    final_purity = 0.0
    if nodes_mix:
        active_indices = [i for i, x in enumerate(mix.X) if x > 1e-12]
        if active_indices:
            final_purity = mix.X[active_indices[0]]

    return (
        nodes_xeu,
        nodes_mix,
        lambdas,
        node_recoveries,
        cumulative_recovery,
        final_purity,
        tk_nodes,
        solvent_values,   # ← NEW
    )