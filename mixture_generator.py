import copy
from datetime import datetime

from input_writer import generate_composition, generate_physchem, assign_pd_svl

def maybe_make_degenerate(component_props, degeneracy_probability=0.1):
    import random

    if random.random() < degeneracy_probability:
        i, j = random.sample(range(len(component_props)), 2)

        component_props[j]['Tm'] = component_props[i]['Tm']
        component_props[j]['DH'] = component_props[i]['DH']
        component_props[j]['Xc'] = component_props[i]['Xc']
        component_props[j]['mode'] = component_props[i]['mode']

    return component_props


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

        # ---------------------------------------------------------
        # PD assignment based on max_addition_compounds (probabilistic)
        # ---------------------------------------------------------
        max_pd = params.get("max_addition_compounds", 0)
        pd_probability = 0.25  # or expose via GUI later

        # Start with all SVL
        modes = ["SVL"] * params["n_components"]

        if max_pd > 0:
            import random

            # PD cannot be assigned to the main component (index 0)
            candidate_indices = list(range(1, params["n_components"]))

            # Shuffle candidates for randomness
            random.shuffle(candidate_indices)

            pd_count = 0

            for idx in candidate_indices:
                if pd_count >= max_pd:
                    break

                # probabilistic PD assignment
                if random.random() < pd_probability:
                    modes[idx] = "PD"
                    pd_count += 1


        components = []
        for idx in range(params["n_components"]):
            components.append({
                "index": idx,
                "Xc": Xc[idx],
                "Tm": physchem[idx]["Tm"],
                "DH": physchem[idx]["DH"],
                "mode": modes[idx],
                #"is_addition_compound": idx in add_indices,
            })
        components = maybe_make_degenerate(components)
        
        m["components"] = components
        m["mixture_id"] = f"{prefix}_{i:03d}"
        mixtures.append(m)

    return mixtures
