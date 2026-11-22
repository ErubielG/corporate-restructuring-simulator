"""Pure synthetic sensitivity smoke tests; no historical Atlas required."""
import copy
import unittest
from pathlib import Path

from scripts.run_sensitivity import run_experiment
from v3sim.dynamic_config import load_dynamic_config

ROOT = Path(__file__).resolve().parents[1]


class PortfolioAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_dynamic_config(ROOT / "config_demo_synthetic.json")

    def test_sensitivity_row_count_and_labels(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["population"]["n"] = 12
        rows = run_experiment(cfg, [0.8, 1.0], [100, 101])
        self.assertEqual(len(rows), 4)
        self.assertEqual({r["operational_scale_hypothetical"] for r in rows}, {0.8, 1.0})
        self.assertTrue(all(0 <= r["autonomy_by_maximum_simulated"] <= 1 for r in rows))

    def test_sensitivity_repeatable(self):
        cfg = copy.deepcopy(self.cfg)
        cfg["population"]["n"] = 9
        one = run_experiment(cfg, [1.0], [11])
        two = run_experiment(cfg, [1.0], [11])
        self.assertEqual(one, two)

    def test_invalid_operational_scale_rejected(self):
        with self.assertRaises(ValueError):
            run_experiment(self.cfg, [0], [1])

    def test_empty_seeds_rejected(self):
        with self.assertRaises(ValueError):
            run_experiment(self.cfg, [1], [])

if __name__ == "__main__":
    unittest.main()
