"""Create reproducible figures from a *synthetic* M1 simulation.

Requires optional data-science dependencies from requirements-analysis.txt.
Never label these charts as empirical observations or validated forecasts.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def plot_distribution(rows: pd.DataFrame, destination: Path) -> None:
    required = {"company_id", "category", "operational_autonomy_month", "control_transfer_month"}
    missing = required - set(rows.columns)
    if missing:
        raise ValueError(f"Missing required simulation columns: {sorted(missing)}")
    if not rows["company_id"].astype(str).str.startswith("SYNT-").all():
        raise ValueError("Only demonstrably synthetic company IDs are allowed in this demo")
    if rows.empty:
        raise ValueError("No synthetic rows supplied")
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for category, group in sorted(rows.groupby("category"), key=lambda x: x[0]):
        ax.hist(group["operational_autonomy_month"].dropna(), bins=18, alpha=0.55,
                label=f"Category {category} (n={len(group)})")
    ax.set_title("Simulated operational autonomy times")
    ax.set_xlabel("Months since modeled process start")
    ax.set_ylabel("Synthetic companies")
    ax.legend()
    ax.grid(axis="y", alpha=0.20)
    fig.text(0.5, 0.01, "SYNTHETIC SCENARIO — not observed durations or validated predictions",
             ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_sensitivity(rows: pd.DataFrame, destination: Path) -> None:
    required = {"scale_hypothetical", "seed", "autonomy_by_maximum"}
    if required - set(rows.columns):
        raise ValueError("Missing sensitivity columns")
    grouped = rows.groupby("scale_hypothetical")["autonomy_by_maximum"]
    lo, hi, med = grouped.min(), grouped.max(), grouped.median()
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    ax.fill_between(med.index.to_numpy(dtype=float), lo.to_numpy(dtype=float),
                    hi.to_numpy(dtype=float), alpha=0.2,
                    label="Min–max over synthetic seeds (NOT a confidence interval)")
    ax.plot(med.index.to_numpy(dtype=float), med.to_numpy(dtype=float), marker="o",
            label="Median simulated outcome across seeds")
    ax.set_ylim(0, 1)
    ax.set_xlabel("Hypothetical operational-duration multiplier")
    ax.set_ylabel("Simulated autonomy by hypothetical maximum")
    ax.set_title("Sensitivity to assumed operational duration")
    ax.grid(alpha=0.20)
    ax.legend(loc="best")
    fig.text(0.5, 0.01, "SYNTHETIC SCENARIO — seed variation is not empirical uncertainty",
             ha="center", fontsize=8)
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description="Plot synthetic M1 simulation, NOT empirical evidence")
    ap.add_argument("--companies", default="output/demo/empresas_resultados.csv")
    ap.add_argument("--sensitivity", default="output/sensitivity/barrido_v32.csv")
    ap.add_argument("--out", default="figures")
    ns = ap.parse_args()
    out = Path(ns.out)
    plot_distribution(pd.read_csv(ns.companies), out / "synthetic_duration_distribution.png")
    plot_sensitivity(pd.read_csv(ns.sensitivity), out / "synthetic_sensitivity.png")
    print(f"Saved synthetic diagnostic figures to {out}")


if __name__ == "__main__":
    main()
