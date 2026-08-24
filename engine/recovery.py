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
