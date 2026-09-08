import ast
import html
import json
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import market_engine as e
from market_view import render

ASOF=pd.Timestamp('2026-09-05')
def series(value=100,n=550,freq='B'):
    return pd.Series(float(value),index=pd.date_range(end='2026-09-04',periods=n,freq=freq))
def moving(v=100,change=0):
    s=series(v); s.iloc[-20:]=np.linspace(v,v*(1+change/100),20); return s

def fixture():
    data={k:series(100) for k in e.REGISTRY}
    for k in ['EFFR','US3M','US2Y','US10Y','US30Y']:data[k]=series(4)
    data.update(REAL10=series(2),TERM=series(.3),VIX=series(15),HY=series(3),BBB=series(1),UNEMP=series(4,180,'MS'),CLAIMS=series(220000,100,'W-FRI'),CAPE=series(25,180,'MS'),RSP=series(100),SPY=series(100))
    for k in ['CPI','CORECPI','COREPCE']:
        s=series(100,180,'MS');s.iloc[:]=100*(1.02**(np.arange(len(s))/12));data[k]=s
    data.update(ADV=series(55),ABOVE200=series(65),HILO=series(1))
    return data

class TestMarket(unittest.TestCase):
    def run_engine(self,data):return e.evaluate(data,ASOF)
    def test_all_registered(self):
        r=self.run_engine({}); self.assertEqual(len(r['results']),37)
        self.assertTrue(all(v['rank']==-1 for v in r['results'].values()))
        self.assertIn('자료가 부족',r['summary'])
    def test_complete_fixture(self):
        r=self.run_engine(fixture()); self.assertTrue(all(v['rank']>=0 for v in r['results'].values()))
    def test_no_small_gold_alarm(self):
        r=self.run_engine({'GOLD':moving(100,.2)})['results']['GOLD'];self.assertEqual(r['rank'],0)
    def test_aux_large_move_capped(self):
        for k in e.AUX_PROFILES:
            with self.subTest(key=k):self.assertEqual(self.run_engine({k:moving(100,100)})['results'][k]['rank'],2)
    def test_gold_safe_haven_requires_axes(self):
        d=fixture();d.update(GOLD=moving(100,10),SP500=moving(100,-15),VIX=moving(15,150),HY=moving(3,100))
        r=self.run_engine(d)['results']['GOLD'];self.assertIn('안전자산',r['interpretation'])
        d=fixture();d['GOLD']=moving(100,10);r=self.run_engine(d)['results']['GOLD'];self.assertNotIn('안전자산',r['interpretation'])
    def test_gold_opportunity_cost(self):
        d=fixture();d.update(GOLD=moving(100,10),REAL10=moving(2,-20),DXY=moving(100,-5))
        self.assertIn('보유 여건',self.run_engine(d)['results']['GOLD']['interpretation'])
    def test_copper_does_not_invent_supply(self):
        d=fixture();d['COPPER']=moving(100,15)
        r=self.run_engine(d)['results']['COPPER'];self.assertTrue(any('공급 차질 원인 판정 보류' in x for x in r['missing']))
    def test_stale_not_cross_evidence(self):
        d=fixture();d['REAL10']=moving(2,-20);d['REAL10'].index-=pd.Timedelta(days=60);d.update(GOLD=moving(100,10),DXY=moving(100,-5))
        r=self.run_engine(d);self.assertEqual(r['results']['REAL10']['rank'],-1);self.assertNotIn('보유 여건',r['results']['GOLD']['interpretation'])
    def test_flat_history_midpoint(self):self.assertEqual(e.percentile(series(),5),50)
    def test_history_minimum(self):self.assertTrue(np.isnan(e.percentile(series(n=100),5)))
    def test_equity_not_double_counted(self):
        r=self.run_engine({'SP500':moving(100,-6)})['results']['SP500'];self.assertEqual(r['rank'],2)
    def test_no_positive_ma_stress(self):
        d=fixture();d['SP500']=moving(100,30);r=self.run_engine(d)
        self.assertGreater(r['results']['MA200']['rank'],0);self.assertFalse(r['axes']['주식']['active'])
    def test_credit_single_axis(self):
        d=fixture();d.update(HY=moving(3,100),BBB=moving(1,200));r=self.run_engine(d)
        self.assertEqual([k for k in r['axes'] if k=='신용'],['신용'])
    def test_sahm_previous_window(self):
        s=series(4,15,'MS');s.iloc[-1]=5.5
        self.assertAlmostEqual(e.sahm(s).iloc[-1],.5)
    def test_monthly_repeated_days(self):
        s=series(100,24,'MS');daily=s.resample('D').ffill()
        self.assertLessEqual(len(e.clean(daily,ASOF,'M')),24)
    def test_negative_oil(self):
        s=series();s.iloc[-3]=-10
        self.assertEqual(self.run_engine({'WTI':s})['results']['WTI']['rank'],-1)
    def test_nonfinite_filtered(self):
        s=series();s.iloc[-2]=np.inf
        self.assertEqual(self.run_engine({'GOLD':s})['results']['GOLD']['rank'],0)
    def test_breadth_invalid_unit(self):
        self.assertEqual(self.run_engine({'ADV':series(150)})['results']['ADV']['rank'],-1)
    def test_named_series_relative_alignment(self):
        d=fixture();d['RSP'].name='value';d['SPY'].name='value'
        self.assertGreaterEqual(self.run_engine(d)['results']['EW']['rank'],0)
    def test_monthly_missing_period(self):
        d=fixture();d['COREPCE']=d['COREPCE'].drop(d['COREPCE'].index[-4])
        r=self.run_engine(d)['results']['COREPCE']
        self.assertGreaterEqual(r['rank'],0)
        self.assertTrue(np.isnan(r['meta']['ann3']))
        self.assertTrue(pd.notna(r['meta']['yoy']))
        self.assertIn('특정 월 누락',r['reason'])
    def test_inflation_uses_exact_calendar_month(self):
        d=fixture();s=d['CPI'];d['CPI']=s.drop(s.index[-13])
        r=self.run_engine(d)['results']['CPI']
        self.assertGreaterEqual(r['rank'],0)
        self.assertTrue(np.isnan(r['meta']['yoy']))
        self.assertTrue(pd.notna(r['meta']['ann3']))
        self.assertIn('전년비 기준월',r['reason'])
    def test_inflation_missing_both_is_unavailable(self):
        d=fixture();s=d['CORECPI'];d['CORECPI']=s.drop([s.index[-4],s.index[-13]])
        r=self.run_engine(d)['results']['CORECPI']
        self.assertEqual(r['rank'],-1)
        self.assertIn('특정 월 누락',r['reason'])
    def test_future_is_ignored(self):
        s=series();a=self.run_engine({'GOLD':s})['results']['GOLD']
        s.loc[pd.Timestamp('2026-09-10')]=1000;b=self.run_engine({'GOLD':s})['results']['GOLD']
        self.assertEqual(a,b)
    def test_reversal_counter(self):
        d=fixture();s=moving(100,20);s.iloc[-5:]=np.linspace(119,110,5);d['GOLD']=s
        self.assertTrue(any('방향' in x for x in self.run_engine(d)['results']['GOLD']['counterevidence']))
    def test_deflation_flag(self):
        d=fixture();d['CPI']=series(100,180,'MS');d['CPI'].iloc[-4:]=[100,99,98,97]
        self.assertIn('하락압력',self.run_engine(d)['results']['CPI']['reason'])
    def test_renders_every_indicator_and_escapes(self):
        class Surface:
            def __init__(self):self.text=[]
            def __getattr__(self,name):
                def call(*a,**kw):self.text.extend(str(x) for x in a);return self
                return call
            def __enter__(self):return self
            def __exit__(self,*a):return False
        st=Surface();r=render(st,fixture(),ASOF)
        self.assertEqual(len(r['results']),37)
        for c in e.REGISTRY.values():self.assertIn(html.escape(c['title']),' '.join(st.text))
        self.assertNotIn('해석과 판정 기준',' '.join(st.text))

if __name__=='__main__':unittest.main()

