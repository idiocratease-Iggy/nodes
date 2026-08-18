# test_harness_single.py
import sys
import os

# Add project root to Python path
ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.append(ROOT)

import json
from mixture_loader import Mixture
from canonical_eutectic import build_canonical_state
from slice_engine import compute_slices
from experiment_builder import build_experiment_rows

def run_test(json_data):
    mixture = Mixture(json_data)
    modes = mixture.modes

    state = build_canonical_state(mixture, modes, solver="vba")

    # Example slice recoveries
    slice_R = [0.9, 0.5, 0.1]

    slices = compute_slices(state, slice_R)
    rows = build_experiment_rows(mixture, slices)

    print("\n=== CANONICAL TEST OUTPUT ===\n")
    for r in rows:
        print(r)

if __name__ == "__main__":
    import json

    # Paste your JSON here
    json_data = {
        "config_id": "260818",
        "metadata": {
            "n_components": 4,
            "main_component_index": 0,
            "main_component_level": 0.8,
            "stochastic_variance": 0.2,
            "max_addition_compounds": 0
        },
        "physchem_rules": {
            "tm_base": 130.0,
            "tm_sd_factor": 1.0,
            "dh_sd_factor": 1.0,
            "dh_correlation": "0.0714*(273+Tm)"
        },
        "slicing": {
            "max_solvent_volumes": 3
        },
        "components": [
            {
                "index": 0,
                "Xc": 0.8253504254982652,
                "Tm": 104.13337198178527,
                "DH": 24.942560743352143,
                "mode": "SVL"
            },
            {
                "index": 1,
                "Xc": 0.07338284187758957,
                "Tm": 103.31801482508642,
                "DH": 30.458135567508755,
                "mode": "SVL"
            },
            {
                "index": 2,
                "Xc": 0.04111882448835009,
                "Tm": 128.26765969589815,
                "DH": 32.06024213536574,
                "mode": "SVL"
            },
            {
                "index": 3,
                "Xc": 0.06014790813579518,
                "Tm": 180.92615084065432,
                "DH": 31.553079650364555,
                "mode": "SVL"
            }
        ],
        "mixture_id": "260818_001"
    }

    run_test(json_data)

