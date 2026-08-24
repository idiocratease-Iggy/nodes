# engine/eutectic_path.py

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

  
import math
from solvers.halley import solve_eutectic_halley
from solvers.vba import solve_eutectic_walkdown
from engine.cascade import run_cascade
from engine.xeu import compute_xeu

def eutectic_path(mixture, modes, solver="halley"):

    # 1. Solve eutectic for node 1
    
    active_ts = [mixture.T[i] for i in mixture.active_components()]
    #min_t = min(active_ts)
    #max_t = max(active_ts)
    
    if solver == "halley":
        if mixture.use_bracket:
            # print(f"DEBUG: Using solver 'halley' with bracket [{min_t}, {max_t}]")
            result = solve_eutectic_halley(mixture, modes)
        
    
    elif solver == "vba":
        # print(f"DEBUG: Using solver '{solver}'")
        Tk = solve_eutectic_walkdown(mixture, modes)
        result = {"T_eutectic": Tk}
    
    else:
        raise NotImplementedError(f"Solver '{solver}' is not wired at present.")
    
    Tk = result["T_eutectic"]
    # print(f"DEBUG: Tk type: {type(Tk)}, value: {Tk}")
    
    # 2. Compute Xeu for node 1
    Xeu = compute_xeu(Tk, mixture, modes)
    
    # 3. Run cascade → returns nodes and lambdas
    raw_result = run_cascade(mixture.copy(), modes, solver=solver)
    # print(f"DEBUG: run_cascade returned {len(raw_result)} values")
    nodes_xeu, nodes_mix, lambdas, node_recoveries, Rmax, final_purity, tk_nodes, solvent_values = raw_result


    
    # 4. Package recovery results
    recovery = {
        "node_recoveries": node_recoveries,   # [0.9814, 0.8094, 0.8553, 0.0011]
        "Rmax": Rmax,                         # 0.0007 → 0.07%
        "final_purity": final_purity          # 0.9613 → 96.13%
    }
    
    # 5. Return everything
    return {
        "solver": solver,
        "Tk": Tk,
        "Xeu": Xeu,
        "cascade": (nodes_xeu, nodes_mix),
        "recovery": recovery,
        "tk_nodes": tk_nodes,
        "solvent": solvent_values,
    }

