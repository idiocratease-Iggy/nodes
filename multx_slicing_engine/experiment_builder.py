# experiment_builder.py

def build_experiment_rows(mixture, slices):
    rows = []

    for s in slices:
        row = {
            "R": s.R,
            "Xliq": s.Xliq,
            "Xsol": s.Xsol,
            "Ks": s.Ks,
            "kl": s.kl,
            "solvent": s.solvent,
        }
        rows.append(row)

    return rows
