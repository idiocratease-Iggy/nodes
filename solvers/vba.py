import math

def solve_eutectic_walkdown(mixture, modes,
                            criteria=1e-4,
                            initial_step=5,
                            max_iter=2000):

    # Start from a safe high temperature:
    # lowest melting point + margin
    HighTemp = max(mixture.T[i] for i in mixture.active_components())


    Change = initial_step
    Convergence = False

    for _ in range(max_iter):
        SumOfXs = 0.0

        for i in mixture.active_components():
            Ti = mixture.T[i]
            DH = mixture.DH[i]
            R = 0.008314  #kJ/mol/K

            if modes[i] == "PD":
                # PG quadratic model
                c = -math.exp(2 * DH / R * (1/(Ti+273) - 1/(HighTemp+273)))
                if c < -1.0:
                    c = -1.0
                Xeu_i = (-4.0 + math.sqrt(16.0 + 16.0*c)) / -8.0
            else:
                # SVL model
                Xeu_i = math.exp(DH / R * (1/(Ti+273) - 1/(HighTemp+273)))

            SumOfXs += Xeu_i

        diff = SumOfXs - 1.0

        if diff > criteria:
            # too eutectic-rich → step down
            HighTemp -= Change
            Convergence = False

        elif diff < 0.0:
            # too lean → step up and shrink step
            HighTemp += Change
            Change /= 2.0
            Convergence = False

        else:
            Convergence = True

        if Convergence:
            break

    return HighTemp
