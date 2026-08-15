import os
import json
import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox

# Hide the main tkinter window
root = tk.Tk()
root.withdraw()


# ============================================================
# Configuration (matches your CRYSS VBA physics)
# ============================================================

N_CASES = 100        # number of mixtures to generate
N_COMPONENTS = 7       # number of components per mixture

BASE_T = 50.0           # °C
MPT_RANGE = 180.0       # °C spread → Tm ∈ [50, 200]
HOF_RANGE = 1.0         # ±50% variation around baseline ΔH

OUTPUT_FILE = "input_batch.json"

# ============================================================
# Composition pattern probabilities
# ============================================================

DOM_95 = 0.30   # 95% dominant component
DOM_80 = 0.30   # 80% dominant component
DOM_70 = 0.30   # 70% dominant component
RAND   = 0.10   # fully random Dirichlet
DEGENERACY = 1           # 1 for yes, 0 for no

# Optional: sanity check
assert abs((DOM_95 + DOM_80 + DOM_70 + RAND) - 1.0) < 1e-9, \
    "Composition probabilities must sum to 1.0"



# ============================================================
# Composition generator (Dirichlet → sums to 1)
# ============================================================

def generate_composition(n, degenerate_indices=None):
    """
    Generate n-component composition vector with controlled patterns:
    - DOM_95: one dominant component at ~95%
    - DOM_80: one dominant component at ~80%
    - DOM_70: one dominant component at ~70%
    - RAND: fully random Dirichlet composition
    """
 
    r = np.random.random()
 
    # Fully random case
    if r < RAND:
        raw = np.random.dirichlet(np.ones(n))
        return raw.tolist(), np.argmax(raw)
 
    # Choose dominant component index
    dominant_idx = np.random.randint(0, n)
    
    if degenerate_indices is not None:
        while dominant_idx in degenerate_indices:
            dominant_idx = np.random.randint(0, n)
 
    # Determine dominant fraction based on probability ranges
    if r < RAND + DOM_95:
        dominant_fraction = 0.95
    elif r < RAND + DOM_95 + DOM_80:
        dominant_fraction = 0.80
    else:
        dominant_fraction = 0.70
 
    # Remaining fraction distributed randomly
    remaining = 1.0 - dominant_fraction
    rest = np.random.dirichlet(np.ones(n - 1)) * remaining
 
    # Build final composition vector
    Xc = np.zeros(n)
    Xc[dominant_idx] = dominant_fraction
 
    j = 0
    for i in range(n):
        if i != dominant_idx:
            Xc[i] = rest[j]
            j += 1
            
    if degenerate_indices is not None:
        i1, i2 = sorted(degenerate_indices)
        Xc[i1] = Xc[i2] = (Xc[i1] + Xc[i2]) / 2
 
    return Xc.tolist(), dominant_idx





# ============================================================
# Melting point generator (your CRYSS VBA logic)
# ============================================================

def generate_tm(n):
    """Generate melting points using CRYSS-style physics."""
    return [
        BASE_T + np.random.random() * MPT_RANGE
        for _ in range(n)
    ]


# ============================================================
# Enthalpy generator (your CRYSS VBA logic)
# ΔH ∝ (273 + Tm) * random multiplier
# ============================================================

def generate_dh(Tm):
    """Generate ΔH values correlated with melting point."""
    return [
        0.07 * (273.0 + T) * (0.5 + HOF_RANGE * np.random.random())
        for T in Tm
    ]


# ============================================================
# PD/SVL assignment logic (your corrected rules)
# - PD_count = randint(0, floor(n/2))
# - PD assigned to lowest-composition components
# - No reordering of components
# ============================================================

def assign_pd_svl(Xc, degenerate_indices=None):
    """Assign PD/SVL modes based on composition."""
    n = len(Xc)
    max_pd = n // 2
    pd_count = np.random.randint(0, max_pd + 1)

    # indices sorted by ascending composition
    sorted_indices = np.argsort(Xc)

    PD_indices = set(sorted_indices[:pd_count])

    mode = ["PD" if i in PD_indices else "SVL" for i in range(n)]
    if degenerate_indices:
        for idx in degenerate_indices:
            mode[idx] = "SVL"
    return mode


# ============================================================
# Generate one complete case
# ============================================================

def generate_case(case_id, n_components):
    Tm = generate_tm(n_components)
    DH = generate_dh(Tm)
    Xc, dominant_idx = generate_composition(n_components)
    
    degenerate_indices = None
    if DEGENERACY:
        # Pick 2 indices from those that are not the dominant one
        potential_indices = [i for i in range(n_components) if i != dominant_idx]
        # Pick 2 from them
        degenerate_indices = np.random.choice(potential_indices, 2, replace=False).tolist()
        
        # Set properties
        Tm[degenerate_indices[0]] = Tm[degenerate_indices[1]]
        DH[degenerate_indices[0]] = DH[degenerate_indices[1]]
        
        # Re-generate Xc to ensure it has the correct degenerate compositions
        Xc, dominant_idx = generate_composition(n_components, degenerate_indices=degenerate_indices)

    mode = assign_pd_svl(Xc, degenerate_indices=degenerate_indices)
    
    return {
        "case_id": case_id,
        "Tm": Tm,
        "DH": DH,
        "Xc": Xc,
        "mode": mode
    }



# ============================================================
# Generate full batch
# ============================================================

def generate_batch(n_cases, n_components):
    return [generate_case(i + 1, n_components) for i in range(n_cases)]


# ============================================================
# Write JSON output
# ============================================================

def write_json(filename, batch):
    path = os.path.abspath(filename)
    with open(path, "w") as f:
        json.dump(batch, f, indent=2)
    # print(f"Wrote {len(batch)} cases to {path}")



# ============================================================
# Print summary for sanity checking
# ============================================================

def print_summary(batch):
    pd_counts = [case["mode"].count("PD") for case in batch]
    print(f"Generated {len(batch)} cases")
    print(f"PD count distribution: min={min(pd_counts)}, "
          f"max={max(pd_counts)}, mean={np.mean(pd_counts):.2f}")

    # Optional: print first case for inspection
    print("\nExample case:")
    print(json.dumps(batch[0], indent=2))


# ============================================================
# Main entry point
# ============================================================

def main():
    batch = generate_batch(N_CASES, N_COMPONENTS)
    
    # Open save dialog
    file_path = filedialog.asksaveasfilename(
        initialfile="input_batch.json",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
    )
    
    if file_path:
        write_json(file_path, batch)
    else:
        print("Save operation cancelled by user.")
    #print_summary(batch)



if __name__ == "__main__":
    main()
