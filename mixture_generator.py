import copy
from datetime import datetime

from input_writer import generate_composition, generate_physchem, assign_pd_svl


def generate_mixture_set(config: dict, num_systems: int):
    """Generate fresh per-mixture component data from a clean config JSON."""
    mixtures = []
    prefix = datetime.now().strftime("%y%m%d")

    clean_config = copy.deepcopy(config)
    params = clean_config.get("metadata", {})
    physchem_rules = clean_config.get("physchem_rules", {})

    for i in range(1, num_systems + 1):
        m = copy.deepcopy(clean_config)

        Xc, add_indices = generate_composition(
            params["n_components"],
            params["main_component_level"],
            params["max_addition_compounds"],
            params["stochastic_variance"],
        )

        physchem = generate_physchem(
            params,
            Xc,
            add_indices,
            physchem_rules.get("tm_base", params.get("tm_base", 0.0)),
            physchem_rules.get("tm_sd_factor", params.get("tm_sd_factor", 1.0)),
            physchem_rules.get("dh_sd_factor", params.get("dh_sd_factor", 1.0)),
        )

        modes = assign_pd_svl({**params}, Xc, add_indices, pd_probability=0.25)

        components = []
        for idx in range(params["n_components"]):
            components.append({
                "index": idx,
                "Xc": Xc[idx],
                "Tm": physchem[idx]["Tm"],
                "DH": physchem[idx]["DH"],
                "mode": modes[idx],
                "is_addition_compound": idx in add_indices,
            })

        m["components"] = components
        m["mixture_id"] = f"{prefix}_{i:03d}"
        mixtures.append(m)

    return mixtures
