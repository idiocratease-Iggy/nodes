# engine/xeu.py

import math

def compute_xeu(Tk, mixture, modes):
    """
    Compute eutectic mole fractions Xeu_i for each ACTIVE component.
    Removed components get Xeu = 0.
    Active components are renormalised so sum(Xeu) = 1.
    """

    T = mixture.T
    DH = mixture.DH
    n = mixture.n_components
    R = 0.008314  # kJ/mol/K

    # Active components (those with X > 0)
    active = mixture.active_components()

    TiK = [Ti + 273.15 for Ti in T]
    Ci  = [DH[i] / R for i in range(n)]
    Bi  = [Ci[i] / TiK[i] for i in range(n)]
    PD_twoCi = [2 * Ci[i] for i in range(n)]

    Tg = Tk + 273.15

    # Compute raw Xeu only for active components
    raw = []
    for i in active:

        if modes[i] == "PD":
            # === EXACT VBA LOGIC ===
            A = PD_twoCi[i] * (1.0 / TiK[i] - 1.0 / Tg)

            # c = -exp(A)
            c = -math.exp(A)

            # clamp c >= -1
            if c < -1.0:
                c = -1.0

            # Xeu = (-4 + sqrt(16 + 16*c)) / -8
            root = math.sqrt(16.0 + 16.0 * c)
            Xeu_i = (-4.0 + root) / -8.0

        else:
            # SVL mode (exact VBA)
            Xeu_i = math.exp(Ci[i] * (1.0 / TiK[i] - 1.0 / Tg))

        raw.append(Xeu_i)

    # Renormalise so sum(Xeu) = 1
    s = sum(raw)
    Xeu = [0.0] * n
    if s > 0:
        for idx, i in enumerate(active):
            Xeu[i] = raw[idx] / s

    return Xeu
