"""
input_writer.py
----------------
Generates a single configuration JSON capturing the full state from
PagePhysChem. This JSON is later consumed by PageGenerateMatrix to
produce multiple mixtures.

Core responsibilities:
- Hold all user parameters (Params dataclass)
- Generate composition template rules
- Generate PhysChem template rules (Tm, DH)
- Apply stochastic variance
- Apply PD/SVL logic
- Apply addition-compound logic
- Assemble final JSON structure
- Write JSON to disk
"""

from dataclasses import dataclass, asdict
from datetime import datetime
import json
import numpy as np


# ============================================================
# 1. PARAMETER DATACLASS
# ============================================================

@dataclass
class Params:
    # Composition
    n_components: int
    main_component_index: int
    main_component_level: float
    stochastic_variance: float
    max_addition_compounds: int
    degeneracy_enabled: bool

    # PhysChem base values
    tm_base: float
    tm_sd_factor: float
    dh_sd_factor: float

    # PD/SVL rules
    max_pd_components: int
    pd_bias: str  # e.g. "lowest_Xc"

    # Slicing metadata (not used yet, but stored)
    max_solvent_volumes: int
    include_rmax_slice: bool

    # Optional: user notes, versioning, etc.
    notes: str = ""


# ============================================================
# 2. UTILITY: MIXTURE ID PREFIX
# ============================================================

def generate_config_id():
    """YYMMDD prefix for configuration."""
    return datetime.now().strftime("%y%m%d")


# ============================================================
# 3. COMPOSITION GENERATOR (template only)
# ============================================================

def generate_composition(params: Params):
    """
    Generates the composition vector Xc:
    - main component level fixed
    - remaining fraction distributed via inv.norm()
    - addition compounds inserted later
    """
    # Skeleton only — implementation later
    Xc = np.zeros(params.n_components)
    # ... fill main component
    # ... distribute impurities
    # ... apply addition compounds
    # ... normalise
    return Xc.tolist()


# ============================================================
# 4. PHYSCHEM GENERATOR (Tm, DH)
# ============================================================

def generate_physchem(params: Params, Xc):
    """
    Generates Tm and DH for each component using:
    - base Tm
    - stochastic variance as 1σ
    - DH derived from Tm via your correlation
    """
    physchem = []
    for i in range(params.n_components):
        # Skeleton only — implementation later
        Tm = 0.0
        DH = 0.0
        physchem.append({"Tm": Tm, "DH": DH})
    return physchem


# ============================================================
# 5. PD/SVL ASSIGNMENT
# ============================================================

def assign_pd_svl(params: Params, Xc):
    """
    Assigns PD/SVL modes:
    - PD = lowest Xc components
    - main component always SVL
    - addition compounds SVL
    """
    mode = ["SVL"] * params.n_components
    # Skeleton only — implementation later
    return mode


# ============================================================
# 6. ASSEMBLE FINAL JSON STRUCTURE
# ============================================================

def build_configuration_json(params: Params):
    """
    Builds the final JSON structure containing:
    - config_id
    - metadata
    - composition template
    - PhysChem template
    - PD/SVL template
    - slicing metadata
    """
    config_id = generate_config_id()

    # Generate core fields
    Xc = generate_composition(params)
    physchem = generate_physchem(params, Xc)
    mode = assign_pd_svl(params, Xc)

    # Assemble components
    components = []
    for i in range(params.n_components):
        components.append({
            "index": i,
            "Xc": Xc[i],
            "Tm": physchem[i]["Tm"],
            "DH": physchem[i]["DH"],
            "mode": mode[i],
            "is_addition_compound": False  # updated later
        })

    # Final JSON structure
    json_data = {
        "config_id": config_id,
        "metadata": {
            "n_components": params.n_components,
            "main_component_index": params.main_component_index,
            "main_component_level": params.main_component_level,
            "stochastic_variance": params.stochastic_variance,
            "max_addition_compounds": params.max_addition_compounds,
            "degeneracy_enabled": params.degeneracy_enabled,
            "notes": params.notes
        },
        "physchem_rules": {
            "tm_base": params.tm_base,
            "tm_sd_factor": params.tm_sd_factor,
            "dh_sd_factor": params.dh_sd_factor,
            "dh_correlation": "0.0714*(273+Tm)"
        },
        "slicing": {
            "max_solvent_volumes": params.max_solvent_volumes,
            "include_rmax_slice": params.include_rmax_slice
        },
        "components": components
    }

    return json_data


# ============================================================
# 7. WRITE JSON
# ============================================================

def write_json(path: str, json_data: dict):
    with open(path, "w") as f:
        json.dump(json_data, f, indent=2)


# ============================================================
# 8. MAIN (optional for standalone testing)
# ============================================================

def main():
    # Example placeholder params
    params = Params(
        n_components=6,
        main_component_index=0,
        main_component_level=0.80,
        stochastic_variance=0.10,
        max_addition_compounds=1,
        degeneracy_enabled=False,
        tm_base=130,
        tm_sd_factor=1.0,
        dh_sd_factor=1.0,
        max_pd_components=2,
        pd_bias="lowest_Xc",
        max_solvent_volumes=3,
        include_rmax_slice=True,
        notes="Example configuration"
    )

    json_data = build_configuration_json(params)
    write_json("config.json", json_data)

import numpy as np

def generate_composition(params: Params):
    """
    Generates the composition vector Xc using:
    - fixed main component level
    - stochastic variance for impurities (inv.norm)
    - optional addition compounds
    - optional degeneracy
    - final normalisation to sum to 1.0
    """

    n = params.n_components
    main_idx = params.main_component_index
    var = params.stochastic_variance
    max_add = params.max_addition_compounds

    # ------------------------------------------------------------
    # 1. Allocate main component level
    # ------------------------------------------------------------
    Xc = np.zeros(n)
    Xc[main_idx] = params.main_component_level

    # Remaining fraction for impurities + addition compounds
    remaining = 1.0 - params.main_component_level

    # ------------------------------------------------------------
    # 2. Determine how many addition compounds we will insert
    # ------------------------------------------------------------
    # They occupy the *last* indices for simplicity (but not required)
    add_count = min(max_add, n - 1)
    add_indices = []

    if add_count > 0:
        # Choose random impurity positions for addition compounds
        impurity_positions = [i for i in range(n) if i != main_idx]
        add_indices = np.random.choice(impurity_positions, add_count, replace=False).tolist()

    # ------------------------------------------------------------
    # 3. Generate impurity fractions using inv.norm modulation
    # ------------------------------------------------------------
    impurity_indices = [i for i in range(n) if i not in [main_idx] + add_indices]
    n_imp = len(impurity_indices)

    if n_imp > 0:
        # Base equal distribution
        base = remaining / (n_imp + add_count)

        # Apply stochastic variance to each impurity
        imp_values = []
        for _ in impurity_indices:
            sigma = base * var
            val = np.random.normal(base, sigma)
            imp_values.append(max(val, 0.0))  # ensure non-negative

        # Insert into Xc
        for idx, val in zip(impurity_indices, imp_values):
            Xc[idx] = val

    # ------------------------------------------------------------
    # 4. Addition compounds get small fractions (also modulated)
    # ------------------------------------------------------------
    if add_count > 0:
        base_add = remaining / (n_imp + add_count)
        for idx in add_indices:
            sigma = base_add * var
            val = np.random.normal(base_add, sigma)
            Xc[idx] = max(val, 0.0)

    # ------------------------------------------------------------
    # 5. Optional degeneracy: force two impurities to match
    # ------------------------------------------------------------
    if params.degeneracy_enabled and n_imp >= 2:
        # Pick two impurity indices
        deg_pair = np.random.choice(impurity_indices, 2, replace=False)
        avg_val = (Xc[deg_pair[0]] + Xc[deg_pair[1]]) / 2
        Xc[deg_pair[0]] = avg_val
        Xc[deg_pair[1]] = avg_val

    # ------------------------------------------------------------
    # 6. Final normalisation (critical)
    # ------------------------------------------------------------
    total = np.sum(Xc)
    if total > 0:
        Xc = Xc / total
    else:
        # fallback: uniform distribution
        Xc = np.ones(n) / n

    return Xc.tolist(), add_indices


import numpy as np

def generate_physchem(params: Params, Xc, add_indices):
    """
    Generates PhysChem values (Tm, DH) for each component using:
    - Tm' = inv.norm(Tm_base, Tm_base * variance)
    - DH_base = 0.0714 * (273 + Tm')
    - DH' = inv.norm(DH_base, DH_base * variance)
    - PD/SVL modulation (small directional shifts)
    - Addition-compound modulation (optional)
    """

    n = params.n_components
    var = params.stochastic_variance

    physchem = []

    # ------------------------------------------------------------
    # PD/SVL bias parameters (small shifts)
    # ------------------------------------------------------------
    pd_shift = 0.03      # PD slightly lower Tm/DH
    svl_shift = 0.03     # SVL slightly higher Tm/DH
    add_shift = 0.05     # addition compounds slightly higher Tm/DH

    # ------------------------------------------------------------
    # First pass: generate raw Tm and DH
    # ------------------------------------------------------------
    for i in range(n):

        # Base Tm for this component
        Tm_base = params.tm_base

        # 1σ = Tm_base * variance
        sigma_T = Tm_base * var

        # Generate modulated Tm
        Tm_mod = np.random.normal(Tm_base, sigma_T)
        Tm_mod = max(Tm_mod, 1.0)  # ensure positive

        # DH correlation
        DH_base = 0.0714 * (273.0 + Tm_mod)

        # 1σ = DH_base * variance
        sigma_H = DH_base * var

        # Generate modulated DH
        DH_mod = np.random.normal(DH_base, sigma_H)
        DH_mod = max(DH_mod, 0.1)

        physchem.append({"Tm": Tm_mod, "DH": DH_mod})

    # ------------------------------------------------------------
    # Second pass: apply PD/SVL shifts
    # ------------------------------------------------------------
    # PD/SVL assignment happens outside this function
    # but we apply shifts here once mode is known
    # ------------------------------------------------------------
    # We expect assign_pd_svl() to be called AFTER this function,
    # so we only prepare the structure here.
    # The caller will apply shifts based on mode.
    # ------------------------------------------------------------

    return physchem

 

def assign_pd_svl(params: Params, Xc, add_indices):
    """
    Assign PD/SVL modes using Alan's rules:
    - PD assigned to lowest-Xc components
    - PD_count ≤ max_pd_components
    - main component ALWAYS SVL
    - addition compounds ALWAYS SVL
    """

    n = params.n_components
    main_idx = params.main_component_index
    max_pd = params.max_pd_components

    # Start with all SVL
    mode = ["SVL"] * n

    # PD candidates = all components except main + addition compounds
    pd_candidates = [
        i for i in range(n)
        if i != main_idx and i not in add_indices
    ]

    if len(pd_candidates) == 0:
        return mode

    # Sort by ascending composition
    sorted_candidates = sorted(pd_candidates, key=lambda i: Xc[i])

    # PD count limited by user
    pd_count = min(max_pd, len(sorted_candidates))

    # Assign PD to lowest-Xc components
    for idx in sorted_candidates[:pd_count]:
        mode[idx] = "PD"

    # Main component and addition compounds forced SVL
    mode[main_idx] = "SVL"
    for idx in add_indices:
        mode[idx] = "SVL"

    return mode




def build_configuration_json(params: Params):
    """
    Builds the final JSON structure containing:
    - config_id (YYMMDD)
    - metadata (PagePhysChem state)
    - composition template (Xc)
    - PhysChem template (Tm, DH)
    - PD/SVL mode assignment
    - addition-compound flags
    - slicing metadata
    """

    # ------------------------------------------------------------
    # 1. Generate configuration ID (YYMMDD)
    # ------------------------------------------------------------
    config_id = generate_config_id()

    # ------------------------------------------------------------
    # 2. Generate composition
    # ------------------------------------------------------------
    Xc, add_indices = generate_composition(params)

    # ------------------------------------------------------------
    # 3. Generate PhysChem (Tm, DH)
    # ------------------------------------------------------------
    physchem = generate_physchem(params, Xc, add_indices)

    # ------------------------------------------------------------
    # 4. Assign PD/SVL modes
    # ------------------------------------------------------------
    mode = assign_pd_svl(params, Xc, add_indices)

    # ------------------------------------------------------------
    # 5. Assemble component entries
    # ------------------------------------------------------------
    components = []
    for i in range(params.n_components):
        components.append({
            "index": i,
            "Xc": Xc[i],
            "Tm": physchem[i]["Tm"],
            "DH": physchem[i]["DH"],
            "mode": mode[i],
            "is_addition_compound": (i in add_indices)
        })

    # ------------------------------------------------------------
    # 6. Assemble final JSON structure
    # ------------------------------------------------------------
    json_data = {
        "config_id": config_id,

        "metadata": {
            "n_components": params.n_components,
            "main_component_index": params.main_component_index,
            "main_component_level": params.main_component_level,
            "stochastic_variance": params.stochastic_variance,
            "max_addition_compounds": params.max_addition_compounds,
            "degeneracy_enabled": params.degeneracy_enabled,
            "notes": params.notes
        },

        "physchem_rules": {
            "tm_base": params.tm_base,
            "tm_sd_factor": params.tm_sd_factor,
            "dh_sd_factor": params.dh_sd_factor,
            "dh_correlation": "0.0714*(273+Tm)"
        },

        "slicing": {
            "max_solvent_volumes": params.max_solvent_volumes,
            "include_rmax_slice": params.include_rmax_slice
        },

        "components": components
    }

    return json_data



if __name__ == "__main__":
    main()
