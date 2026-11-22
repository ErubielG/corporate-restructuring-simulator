"""Generate two reproducible figures from synthetic model CSV outputs.

Requires optional analysis dependencies: pip install -e '.[analysis]'
"""
from __future__ import annotations

import argparse
from pathlib import Path


def create_figures(company_csv: str, sensitivity_csv: str, out_dir: str):
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    companies = pd.read_csv(company_csv)
    sensitivity = pd.read_csv(sensitivity_csv)
    folder = Path(out_dir)
    folder.mkdir(parents=True, exist_ok=True)

    durations = pd.to_numeric(companies["operational_autonomy_month"], errors="coerce").dropna()
    if durations.empty:
        raise ValueError("No finite autonomy durations available")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.hist(durations, bins=22, edgecolor="white")
    ax.axvline(durations.median(), linestyle="--", linewidth=1.5, label="Median")
    ax.set(xlabel="Simulated operational autonomy (months)", ylabel="Synthetic companies",
           title="Distribution of simulated durations")
    ax.legend()
    fig.tight_layout()
    fig.savefig(folder / "duration_distribution.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    grouped = sensitivity.groupby("operational_scale_hypothetical")
    x = sorted(grouped.groups)
    mins = [grouped.get_group(val)["autonomy_by_maximum_simulated"].min() for val in x]
    maxs = [grouped.get_group(val)["autonomy_by_maximum_simulated"].max() for val in x]
    medians = [grouped.get_group(val)["autonomy_by_maximum_simulated"].median() for val in x]
    ax.fill_between(x, mins, maxs, alpha=0.2, label="Observed range across configured seeds")
    ax.plot(x, medians, marker="o", label="Median across configured seeds")
    ax.set(xlabel="Hypothetical operational-duration multiplier",
           ylabel="Share within assumed maximum (synthetic)",
           title="Sensitivity across seeds (not a confidence interval)", ylim=(0, 1.02))
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(folder / "sensitivity_across_seeds.png", dpi=160)
    plt.close(fig)
    return folder


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--companies", default="output/demo/empresas_resultados.csv")
    p.add_argument("--sensitivity", default="output/sensitivity/sensitivity.csv")
    p.add_argument("--out", default="figures")
    args = p.parse_args()
    print(create_figures(args.companies, args.sensitivity, args.out))


if __name__ == "__main__":
    main()
