"""Extra methodological and reproducibility tests, no historical data required."""
import copy
import csv
import tempfile
import unittest
from pathlib import Path

from v3sim.dynamic_analysis import scenario, evaluate
from v3sim.dynamic_config import load_dynamic_config
from v3sim.dynamic_engine import run_dynamic
from v3sim.dynamic_cli import export
from v3sim.atlas import read_atlas_sales
from scripts.make_synthetic_fixture import create_demo_database

ROOT = Path(__file__).resolve().parents[1]


class AdditionalPublicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_dynamic_config(ROOT / "config_demo_synthetic.json")

    def test_sensitivity_keeps_other_scaling_parameters(self):
        base = copy.deepcopy(self.cfg)
        base["transitional_services_scale"] = 1.7
        base["sector_multiplier_scale"] = 1.25
        changed = scenario(base, scale=1.4, seed=17)
        self.assertEqual(changed["transitional_services_scale"], 1.7)
        self.assertEqual(changed["sector_multiplier_scale"], 1.25)
        self.assertEqual(changed["operational_scale"], 1.4)
        self.assertEqual(changed["population"]["seed"], 17)
        self.assertEqual(base["operational_scale"], 1.0)

    def test_different_duration_scaling_changes_modeled_outcome(self):
        base = copy.deepcopy(self.cfg)
        base["population"]["n"] = 40
        shorter = run_dynamic(scenario(base, scale=0.6, seed=130), (), 0)
        longer = run_dynamic(scenario(base, scale=2.4, seed=130), (), 0)
        a = [x["operational_autonomy_month"] for x in shorter["results"]]
        b = [x["operational_autonomy_month"] for x in longer["results"]]
        self.assertTrue(any(x != y for x, y in zip(a, b)))
        for record in longer["results"]:
            self.assertFalse(record["legal_compliance_established"])
            self.assertFalse(record["sanction_or_wrongdoing_established"])

    def test_synthetic_outputs_preserve_provenance(self):
        with tempfile.TemporaryDirectory() as t:
            db = create_demo_database(Path(t) / "zero_cases.sqlite")
            atlas = read_atlas_sales(db)
            cfg = copy.deepcopy(self.cfg)
            cfg["population"]["n"] = 8
            result = run_dynamic(cfg, (), 1)
            export(Path(t) / "output", cfg, atlas, db, result)
            with (Path(t) / "output" / "empresas_resultados.csv").open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 8)
            self.assertTrue(all(row["company_id"].startswith("SYNT-") for row in rows))

    def test_repeated_seeds_give_same_sensitivity_metric(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["population"]["n"] = 25
        a = evaluate(scenario(cfg, scale=1.4, seed=90), ())
        b = evaluate(scenario(cfg, scale=1.4, seed=90), ())
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
