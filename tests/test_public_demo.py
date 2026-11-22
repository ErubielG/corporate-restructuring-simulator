"""Tests that do not rely on the historical research Atlas."""
import copy
import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.make_synthetic_fixture import create_demo_database
from scripts.analyze_demo import aggregate
from v3sim.atlas import read_atlas_sales
from v3sim.dynamic_config import load_dynamic_config
from v3sim.dynamic_engine import DynamicRunner, run_dynamic
from v3sim.engine import sample_company
from v3sim.dynamic_config import generation_config

ROOT=Path(__file__).resolve().parents[1]

class SyntheticDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=load_dynamic_config(ROOT/'config_demo_synthetic.json')

    def test_fixture_contains_no_real_cases(self):
        with tempfile.TemporaryDirectory() as t:
            db=create_demo_database(Path(t)/'fixture.sqlite')
            atlas=read_atlas_sales(db)
            self.assertEqual(atlas.cases_total, 0)
            self.assertEqual(atlas.sale_observations, 0)
            self.assertEqual(atlas.operational_exact_pairs, 0)

    def test_config_validation(self):
        self.assertEqual(self.cfg['evidence_mode'], 'synthetic_only')
        self.assertGreater(self.cfg['population']['n'],0)

    def test_reproducible_results(self):
        cfg=copy.deepcopy(self.cfg)
        cfg['population']['n']=12
        a=run_dynamic(cfg,(),trace_limit=2)
        b=run_dynamic(cfg,(),trace_limit=2)
        self.assertEqual(a['results'],b['results'])
        self.assertEqual(a['summary'],b['summary'])

    def test_independent_sale_and_autonomy(self):
        cfg=copy.deepcopy(self.cfg)
        cfg['population']['n']=12
        for row in run_dynamic(cfg,(),trace_limit=0)['results']:
            self.assertGreaterEqual(row['operational_autonomy_month'],row['control_transfer_month'])
            self.assertFalse(row['legal_compliance_established'])

    def test_buyer_withdrawal_reopens_search(self):
        cfg=copy.deepcopy(self.cfg)
        cfg['population']['n']=1
        cfg['behavior']['appeal_probability']=0
        cfg['behavior']['delay_probability']=0
        cfg['operational_disruption']['probability']=0
        for k in ('legal_appeal','regulatory_suspension','buyer_withdrawal','remedy_revision','technical_failure'):
            cfg['dynamic_events'][k]['probability']=0
        company=sample_company(1,random.Random(42),generation_config(cfg),())
        baseline, trace0=DynamicRunner(company,cfg,seed=45,capture=True).execute()
        cfg['dynamic_events']['buyer_withdrawal']['probability']=1
        changed, trace1=DynamicRunner(company,cfg,seed=45,capture=True).execute()
        self.assertGreater(changed['control_transfer_month'],baseline['control_transfer_month'])
        self.assertTrue(any(x['event']=='BUYER_SEARCH_REOPENED' for x in trace1.events))
        self.assertEqual(sum(x['event']=='TASK_STARTED' and x['stage']=='tech_preparation' for x in trace1.events),1)

    def test_data_analysis_aggregation(self):
        sample=[{"category":"I","autonomy_by_maximum":"1","operational_autonomy_month":"4.0"},
                {"category":"I","autonomy_by_maximum":"0","operational_autonomy_month":"8.0"},
                {"category":"II","autonomy_by_maximum":"1","operational_autonomy_month":"12.0"}]
        out=aggregate(sample)
        self.assertEqual(out[0]["companies_synthetic"],2)
        self.assertEqual(out[0]["autonomy_by_maximum_simulated_rate"],0.5)
        self.assertEqual(out[0]["autonomy_median_months_simulated"],6.0)

    def test_no_historical_claims(self):
        cfg=copy.deepcopy(self.cfg)
        cfg['population']['n']=5
        result=run_dynamic(cfg,(),trace_limit=0)
        self.assertTrue(result['summary']['not_a_validated_forecast'])
        self.assertTrue(result['summary']['not_a_legal_compliance_rate'])

if __name__=='__main__':unittest.main()
