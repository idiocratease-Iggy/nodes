def compute_recovery(cascade_nodes, lambdas):
    # print("\n==============================")
    # print(" RECOVERY DEBUG (simple)")
    # print("==============================\n")

    node_recovery = []
    cumulative = 1.0

    for i, (Xeu, lam) in enumerate(zip(cascade_nodes, lambdas), start=1):
        total_scaled = lam * sum(Xeu)
        sum_after = 1.0 - total_scaled

        if total_scaled > 0 and sum_after >= 0:
            R = sum_after / total_scaled
        else:
            R = 1.0

        # print(f"--- Node {i} ---")
        # print(f"λ = {lam:.6f}")
        # print(f"Sum(Xeu) = {sum(Xeu):.6f}")
        # print(f"TotalScaled = {total_scaled:.6f}")
        # print(f"SumAfter = {sum_after:.6f}")
        # print(f"Node Recovery = {R*100:.2f}%\n")

        node_recovery.append(R)
        cumulative *= R

    cumulative_recovery = cumulative

    # print("==============================")
    # print(" FINAL RECOVERY (simple)")
    # print("==============================")
    # print(f"Cumulative Recovery = {cumulative_recovery*100:.2f}%\n")

    return {
        "node_recovery": node_recovery,
        "cumulative_recovery": cumulative_recovery,
    }
