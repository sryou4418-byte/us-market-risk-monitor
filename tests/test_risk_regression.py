"""Frozen outputs from pre-refactor main, plus exact AST checks on extracted rules."""
import ast,hashlib,json,unittest
from pathlib import Path
import numpy as np
import pandas as pd
import risk_engine
from test_contracts import inputs


def normalize(obj):
    if isinstance(obj,dict):return {k:normalize(v) for k,v in obj.items()}
    if isinstance(obj,(tuple,list)):return [normalize(v) for v in obj]
    if isinstance(obj,(int,float,np.number)):return float(obj) if np.isfinite(obj) else None
    if isinstance(obj,pd.Timestamp):return str(obj)
    return obj


class RiskRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.golden=json.loads(Path(__file__).with_name('golden_risk.json').read_text(encoding='utf-8'))

    def test_all_extracted_financial_functions_unchanged(self):
        tree=ast.parse(Path(risk_engine.__file__).read_text(encoding='utf-8'))
        hashes={n.name:hashlib.sha256(ast.dump(n).encode()).hexdigest() for n in tree.body if isinstance(n,ast.FunctionDef)}
        for name,expected in self.golden['function_ast_sha256'].items():
            self.assertEqual(hashes[name],expected,name)

    def test_scores_signals_details_match_previous_main(self):
        for case,expected in self.golden['cases'].items():
            with self.subTest(case=case):
                data,cape=inputs(case)
                self.assertEqual(normalize(risk_engine.compute_snapshot(data,cape)),expected)
