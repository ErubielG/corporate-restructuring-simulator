"""Synthetic sensitivity experiment across independently configured seeds.

This is a software-model robustness study, NOT a statistical confidence
interval for a population of real companies.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from v3sim.dynamic_analysis import scenario, evaluate
from v3sim.dynamic_config import load_dynamic_config


def run_experiment(config: dict, scales: list[float], seeds: list[int]):
    if not scales or not seeds:
        raise ValueError("At least one scale and seed are required")
    rows = []
    for scale in scales:
        if scale <= 0:
            raise ValueError("Operational scale must be positive")
        for seed in seeds:
            current = scenario(config, scale=scale, seed=seed)
            result = evaluate(current, ())
            rows.append({
                "operational_scale_hypothetical": scale,
                "seed": seed,
                "synthetic_companies": current["population"]["n"],
                "autonomy_by_maximum_simulated": result["rate"],
                "median_autonomy_to_sale_ratio_simulated": result["median_simulated_ratio"],
                "rate_category_I": result["by_category"].get("I", {}).get("autonomy_by_maximum"),
                "rate_category_II": result["by_category"].get("II", {}).get("autonomy_by_maximum"),
                "rate_category_III": result["by_category"].get("III", {}).get("autonomy_by_maximum"),
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config_demo_synthetic.json")
    parser.add_argument("--out", default="output/sensitivity/sensitivity.csv")
    parser.add_argument("--scales", type=float, nargs="+", default=[0.8, 1.0, 1.4, 1.8, 2.2])
    parser.add_argument("--seeds", type=int, nargs="+", default=[20261012, 20261013, 20261014, 20261015, 20261016])
    parser.add_argument("--n", type=int, default=None, help="Synthetic companies per replicate")
    args = parser.parse_args()
    config = load_dynamic_config(args.config)
    if config["evidence_mode"] != "synthetic_only":
        parser.error("This public experiment only supports synthetic_only")
    if args.n is not None:
        if args.n <= 0:
            parser.error("--n must be positive")
        config["population"]["n"] = args.n
    rows = run_experiment(config, args.scales, args.seeds)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"path": str(target), "replicates": len(rows),
                      "warning": "SIMULATED sensitivity; NOT empirically validated"}, indent=2))


if __name__ == "__main__":
    main()
