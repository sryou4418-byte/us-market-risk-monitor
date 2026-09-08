import ast
import sys
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from concurrent.futures import ThreadPoolExecutor
import csv
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import pandas as pd
from streamlit.testing.v1 import AppTest
from loading_service import start,status,parallel_map,atomic_json
from market_loader import load,TICKERS
from news_categories import classify,select,CATEGORIES
from market_view import cached_evaluate
APP=Path(__file__).resolve().parents[1]/'streamlit_app.py'

class LoadingTests(unittest.TestCase):
    def test_dedup_and_retry(self):
        done=threading.Event();key='test-'+str(time.monotonic())
        self.assertTrue(start(key,lambda:done.wait(2),0))
        self.assertFalse(start(key,lambda:None,0));done.set()
        deadline=time.monotonic()+2
        while status(key).get('running') and time.monotonic()<deadline:time.sleep(.005)
        self.assertFalse(status(key)['running'])
        self.assertFalse(start(key,lambda:None,30))
    def test_parallel_bound_and_success_on_failure(self):
        lock=threading.Lock();active=0;peak=0;seen={}
        def fetch(x):
            nonlocal active,peak
            with lock:active+=1;peak=max(peak,active)
            time.sleep(.02)
            with lock:active-=1
            if x==5:raise ValueError('offline')
            return x
        errors=parallel_map(dict(enumerate(range(11))),fetch,lambda k,v:seen.update({k:v}),4)
        self.assertLessEqual(peak,4);self.assertGreater(peak,1);self.assertEqual(len(seen),10);self.assertIn(5,errors)
    def test_stale_returns_immediately_and_failure_preserves(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'aux.json';old={'items':{'GOLD':{'updated':1,'dates':['2026-09-01'],'values':[100]}}};atomic_json(path,old)
            release=threading.Event()
            def delayed(symbol):release.wait(2);raise ValueError('network unavailable')
            before=time.perf_counter();data,state,_=load(path,fetch=delayed)
            self.assertLess(time.perf_counter()-before,.2);self.assertTrue(state['running']);self.assertEqual(data['GOLD'].iloc[0],100)
            release.set();deadline=time.monotonic()+3
            while status(path).get('running') and time.monotonic()<deadline:time.sleep(.01)
            self.assertEqual(json.loads(path.read_text()),old)
    def test_cache_key_changes_with_values(self):
        cached_evaluate.clear()
        a={'GOLD':pd.Series(100.,index=pd.bdate_range(end='2026-09-04',periods=550))}
        x=cached_evaluate(a,'2026-09-05');a['GOLD'].iloc[-1]=150
        y=cached_evaluate(a,'2026-09-05')
        self.assertNotEqual(x['results']['GOLD']['rank'],y['results']['GOLD']['rank'])
    def test_classification_no_risk(self):
        a=classify({'title':'중동 전쟁 유가 상승에 물가 우려','category':'주요 뉴스'})
        self.assertEqual(a['category'],'지정학·에너지');self.assertIn('물가',a['tags']);self.assertNotIn('score',a)
        self.assertEqual(len(select([a],'물가')),1)
        self.assertEqual(classify({'title':'미국 기업 가이던스 발표'})['category'],'기업·실적')
    def test_news_page_without_core_or_network(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'LOCALAPPDATA':d}):
            root=Path(d)/'RiskMonitor';root.mkdir()
            atomic_json(root/'korean_econ_news.json',{'updated':time.time(),'items':[{'title':'연준 금리 동결','category':'연준·금리','source':'Test','published':time.time(),'link':'https://example.com/news'}]})
            with patch('requests.get',side_effect=AssertionError('unexpected network')) as request:
                app=AppTest.from_file(str(APP));app.query_params['view']='news';app.run(timeout=15)
                self.assertEqual(len(app.exception),0,[x.message for x in app.exception]);self.assertEqual(len(app.selectbox),0)
                rendered='\n'.join(x.value for x in app.markdown)
                self.assertIn('news-filter-grid',rendered);self.assertIn('기사 1개',rendered)
                self.assertFalse(any(x.label=='새로고침' for x in app.button))
                app.query_params['news_category']='물가';app.run(timeout=15)
                self.assertEqual(len(app.exception),0);request.assert_not_called()
    def test_parser_invalid_and_duplicates(self):
        node=next(x for x in ast.parse(APP.read_text(encoding='utf-8')).body if isinstance(x,ast.FunctionDef) and x.name=='_parse_fred')
        ns={'pd':pd,'csv':csv};exec(compile(ast.Module(body=[node],type_ignores=[]),'parser','exec'),ns)
        z=ns['_parse_fred']('\ufeffpreamble\nobservation_date,X\n2026-01-02,2\n2026-01-01,.\n2026-01-02,4\nbad,5\n2026-01-03,3','X')
        self.assertEqual(z.tolist(),[2.,3.])
    def test_news_no_engine_dependency(self):
        s=(APP.parent/'news_categories.py').read_text(encoding='utf-8');self.assertNotIn('market_engine',s)

    def test_recent_inflation_gap_detection(self):
        tree=ast.parse(APP.read_text(encoding='utf-8'))
        node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='_recent_month_gaps')
        ns={'pd':pd};exec(compile(ast.Module(body=[node],type_ignores=[]),'gap','exec'),ns)
        s=pd.Series(range(16),index=pd.date_range('2025-01-01',periods=16,freq='MS'),dtype=float)
        self.assertEqual(ns['_recent_month_gaps'](s),[])
        missing=s.drop(pd.Timestamp('2025-11-01'))
        self.assertEqual(ns['_recent_month_gaps'](missing),['2025-11'])

    def test_full_routes_with_cached_data(self):
        from test_market import fixture
        data=fixture()
        mapping={'기준금리':'EFFR','3개월물':'US3M','2년물':'US2Y','10년물':'US10Y','30년물':'US30Y','10년물실질금리':'REAL10','10년물기간프리미엄':'TERM','하이일드스프레드':'HY','BBB스프레드':'BBB','실업률':'UNEMP','신규실업수당':'CLAIMS','CPI':'CPI','근원CPI':'CORECPI','근원PCE':'COREPCE','S&P500':'SP500','VIX':'VIX'}
        tree=ast.parse(APP.read_text(encoding='utf-8'));series=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SERIES' for t in n.targets))
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'LOCALAPPDATA':d}):
            root=Path(d)/'RiskMonitor';(root/'data').mkdir(parents=True)
            for name,sid in series.items():data[mapping[name]].rename('value').to_csv(root/'data'/f'{sid}.csv',index_label='date')
            data['CAPE'].rename('cape').to_csv(root/'cape.csv',index_label='date')
            atomic_json(root/'refresh_status.json',{'updated':time.time(),'finished':time.time()})
            atomic_json(root/'fx_snapshot.json',{'items':{}})
            auxiliary={'items':{k:{'updated':time.time(),'dates':[x.isoformat() for x in data[k].index],'values':data[k].tolist()} for k in TICKERS}}
            atomic_json(root/'market_aux_v348.json',auxiliary)
            atomic_json(root/'sp500_market_map_200.json',{'updated':time.time(),'items':[{'symbol':'AAPL','name':'Apple','sector':'Technology','weight':6,'change':1,'price':100}]})
            with patch('requests.get',side_effect=AssertionError('unexpected network')) as request:
                for view in ('dashboard','risk','market','heatmap'):
                    with self.subTest(view=view):
                        app=AppTest.from_file(str(APP));app.query_params['view']=view;app.run(timeout=20)
                        self.assertEqual(len(app.exception),0,[x.message for x in app.exception])
                request.assert_not_called()

    def test_cold_bootstrap_shows_shell_without_waiting(self):
        with tempfile.TemporaryDirectory() as d,patch.dict(os.environ,{'LOCALAPPDATA':d}),patch('loading_service.status',return_value={'running':True}),patch('requests.get',side_effect=AssertionError('UI must not fetch')) as request:
            app=AppTest.from_file(str(APP));app.run(timeout=10)
            self.assertEqual(len(app.exception),0)
            self.assertTrue(any('준비' in x.value for x in app.info))
            request.assert_not_called()

