


print("Loaded solvent_gradient.py from:", __file__)


class PurificationModel:
    def __init__(self, run_id, cumR, comp_after, gradients, intercepts, metadata=None):
        self.run_id = run_id
        self.cumR = cumR
        self.comp_after = comp_after
        self.gradients = gradients
        self.intercepts = intercepts
        self.metadata = metadata or {}

    def __repr__(self):
        return f"<PurificationModel run_id={self.run_id}>"


class SolventGradientEngine:
    def __init__(self, cascade_results):
        """
        cascade_results must contain:
        - cumR: list of cumulative recoveries after each node (descending from 1 to 0)
        - solvent: list of scalar solvent values at each node (RelSolVol)
        """
        self.cascade = cascade_results
        self.cumR = cascade_results.get("cumR", [])
        self.solvent = cascade_results.get("solvent", [])
        self.gradients = None
        self.intercepts = None

    def find_interval(self, R):
        """
        Given a recovery R (0–1), find the cascade interval [k, k+1]
        such that cumR[k+1] <= R <= cumR[k].
        """
        for k in range(len(self.cumR) - 1):
            if self.cumR[k+1] <= R <= self.cumR[k]:
                return k

        return len(self.cumR) - 2

    def compute_gradients(self):
        """
        Compute gradient (m) and intercept (b) for each segment
        between each cascade node.
        """
        cumR = self.cumR
        solvent = self.solvent

        gradients = []
        intercepts = []

        num_intervals = len(cumR) - 1

        if len(solvent) < num_intervals + 1:
            last_value = solvent[-1]
            while len(solvent) < num_intervals + 1:
                solvent.append(last_value)

        for k in range(num_intervals):
            Ck = cumR[k]
            Ck1 = cumR[k+1]

            solvent_k = solvent[k]
            solvent_k1 = solvent[k+1]

            if Ck1 == Ck:
                m = 0.0
            else:
                m = (solvent_k1 - solvent_k) / (Ck1 - Ck)

            b = solvent_k - m * Ck

            gradients.append(m)
            intercepts.append(b)

        self.gradients = gradients
        self.intercepts = intercepts

    def value_at_recovery(self, R):
        """Compute scalar value at arbitrary recovery R (0–1)."""
        if self.gradients is None or self.intercepts is None:
            raise ValueError("Gradients not computed. Call compute_gradients() first.")

        k = self.find_interval(R)

        m = self.gradients[k]
        b = self.intercepts[k]

        return m * R + b

    def generate_profile(self, R_values):
        """
        Generate solvent profile over a list of recovery values.
        Returns a list of tuples: (R, scalar_value)
        """
        profile = []

        for R in R_values:
            value = self.value_at_recovery(R)
            profile.append((R, value))

        return profile

