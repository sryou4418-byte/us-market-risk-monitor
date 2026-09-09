import unittest
import pandas as pd
from presentation import Metric,number,fmt,signal_names
from risk_service import report
from risk_engine import historical_risk_fast_338
from data_contract import normalize_series
from test_market import fixture

MAPPING={'기준금리':'EFFR','3개월물':'US3M','2년물':'US2Y','10년물':'US10Y','30년물':'US30Y','10년물실질금리':'REAL10','10년물기간프리미엄':'TERM','하이일드스프레드':'HY','BBB스프레드':'BBB','실업률':'UNEMP','신규실업수당':'CLAIMS','CPI':'CPI','근원CPI':'CORECPI','근원PCE':'COREPCE','S&P500':'SP500','VIX':'VIX'}


def inputs(case='normal'):
    source=fixture()
    data={k:source[v].copy() for k,v in MAPPING.items()}
    cape=source['CAPE'].copy()
    if case=='stress':
        data['S&P500'].iloc[-20:]*=.75
        data['VIX'].iloc[-5:]=50
        data['하이일드스프레드'].iloc[-20:]=8
    if case=='missing_inflation':
        for k in ['CPI','근원CPI','근원PCE']:data[k]=pd.Series(dtype=float,index=pd.DatetimeIndex([]))
    if case=='missing_cape':cape=pd.Series(dtype=float)
    if case=='short_history':data={k:v.iloc[-2:] for k,v in data.items()}
    return data,cape


class Contracts(unittest.TestCase):
    def test_normalization_rejects_undated_and_preserves_calendar_gaps(self):
        with self.assertRaises(ValueError):normalize_series(pd.Series([1,2]))
        self.assertIsInstance(normalize_series(pd.Series(dtype=float)).index,pd.DatetimeIndex)
        source=pd.Series([1,2,float('inf'),4],index=pd.to_datetime(['2026-03-01','2026-01-01','2026-02-01','2026-01-01']))
        normalized=normalize_series(source)
        self.assertEqual(normalized.tolist(),[4,1])
        self.assertEqual(len(normalized),2)
    def test_missing_is_not_zero(self):
        for value in [None,float('nan'),float('inf'),'invalid']:
            self.assertIsNone(number(value));self.assertEqual(fmt(value),'—')
        self.assertEqual(fmt(0),'0.0')
        m=Metric.from_series('CPI',pd.Series(dtype=float),'%')
        self.assertEqual(m.state,'자료 없음');self.assertIsNone(m.observed)
        self.assertIsNone(m.release_time)

    def test_signal_description_hides_internal_scores(self):
        self.assertEqual(signal_names({'items':[('고용 악화 확인',75.0)]}),['고용 악화 확인'])

    def test_missing_component_kept_missing_in_report(self):
        data,cape=inputs('missing_inflation');r=report(data,cape,'2026-09-05')
        self.assertIsNone(number(r['scores']['물가']))
        self.assertEqual(r['coverage']['risk'],(5,6))

    def test_cutoff_prevents_future_observations(self):
        data,cape=inputs();a=report(data,cape,'2026-09-05')
        for s in data.values():s.loc[pd.Timestamp('2026-10-01')]=999999
        b=report(data,cape,'2026-09-05')
        self.assertEqual(a['final'],b['final']);self.assertEqual(a['scores'],b['scores'])

    def test_history_is_explicit_and_repeatable(self):
        data,cape=inputs()
        a=historical_risk_fast_338(data,cape,'2026-09-05')
        b=historical_risk_fast_338(data,cape,'2026-09-05')
        pd.testing.assert_frame_equal(a,b)
        self.assertEqual(list(a.columns),['base','risk'])
