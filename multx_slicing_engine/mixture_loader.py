# mixture_loader.py

class Mixture:
    def __init__(self, config):
        self.config_id = config["config_id"]
        self.n_components = config["metadata"]["n_components"]

        # Composition
        self.X = [comp["Xc"] for comp in config["components"]]

        # PhysChem
        self.T = [comp["Tm"] for comp in config["components"]]
        self.DH = [comp["DH"] for comp in config["components"]]
        self.modes = [comp["mode"] for comp in config["components"]]

        # Required by cascade
        self.case_id = config.get("mixture_id", "unknown")
        self.use_bracket = False  # halley option

    def active_components(self):
        return [i for i, x in enumerate(self.X) if x > 1e-12]

    def copy(self):
        new = Mixture({
            "config_id": self.config_id,
            "metadata": {"n_components": self.n_components},
            "components": [
                {"Xc": self.X[i], "Tm": self.T[i], "DH": self.DH[i], "mode": self.modes[i]}
                for i in range(self.n_components)
            ],
            "mixture_id": self.case_id,
        })
        return new

