"""Retrospective signal-frequency audit; NOT a point-in-time investment backtest.
Usage: python backtest_market.py --asof 2026-09-05 --output audit
"""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
from io import StringIO
import json
from pathlib import Path
from urllib.parse import quote
import time
import numpy as np
import pandas as pd
import requests
from market_engine import evaluate, REGISTRY
FRED={'SP500':'SP500','US3M':'DGS3MO','US2Y':'DGS2','US10Y':'DGS10','US30Y':'DGS30','REAL10':'DFII10','EFFR':'EFFR','TERM':'THREEFYTP10','HY':'BAMLH0A0HYM2','BBB':'BAMLC0A4CBBB','VIX':'VIXCLS','UNEMP':'UNRATE','CLAIMS':'ICSA','CPI':'CPIAUCSL','CORECPI':'CPILFESL','COREPCE':'PCEPILFE'}
YAHOO={'NASDAQ':'^IXIC','RUSSELL':'^RUT','RSP':'RSP','SPY':'SPY','GOLD':'GC=F','SILVER':'SI=F','COPPER':'HG=F','WTI':'CL=F','DXY':'DX-Y.NYB','USDKRW':'USDKRW=X','USDJPY':'USDJPY=X'}

def fetch(item,asof):
    key,provider,symbol=item
    if provider=='fred':
        url=f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={symbol}'
        r=requests.get(url,timeout=(5,25));r.raise_for_status()
        df=pd.read_csv(StringIO(r.text));s=pd.Series(pd.to_numeric(df.iloc[:,1],errors='coerce').values,index=pd.to_datetime(df.iloc[:,0]),name=key).dropna()
    else:
        # Three years includes a one-year audit plus two-year rolling context.
        start=int((asof-pd.Timedelta(days=1200)).timestamp());end=int((asof+pd.Timedelta(days=1)).timestamp())
        url=f'https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol,safe="")}?period1={start}&period2={end}&interval=1d'
        r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=(5,25));r.raise_for_status()
        d=r.json()['chart']['result'][0]
        s=pd.Series(d['indicators']['quote'][0]['close'],index=pd.to_datetime(d['timestamp'],unit='s',utc=True).tz_convert(None).normalize(),name=key).dropna()
    s=s.loc[(s.index<=asof)&(s.index>=asof-pd.DateOffset(years=16 if REGISTRY.get(key,{}).get('frequency')=='M' else 5))]
    return key,s

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--asof',required=True);parser.add_argument('--output',default='audit');parser.add_argument('--offline-data');args=parser.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True);(out/'data').mkdir(exist_ok=True)
    asof=pd.Timestamp(args.asof);data={};errors={}
    if args.offline_data:
        for file in Path(args.offline_data).glob('*.csv'):
            df=pd.read_csv(file,index_col=0,parse_dates=True)
            data[file.stem]=df.iloc[:,0]
        errors={k:'not_available_in_offline_input' for k in list(FRED)+list(YAHOO) if k not in data}
    else:
        jobs=[(k,'fred',v) for k,v in FRED.items()]+[(k,'yahoo',v) for k,v in YAHOO.items()]
        with ThreadPoolExecutor(max_workers=6) as pool:
            fs={pool.submit(fetch,j,asof):j[0] for j in jobs}
            for f in as_completed(fs):
                key=fs[f]
                try:
                    key,s=f.result();data[key]=s;s.rename('value').to_csv(out/'data'/f'{key}.csv',index_label='date');print(key,len(s),flush=True)
                except Exception as ex:errors[key]=type(ex).__name__;print(key,'unavailable',type(ex).__name__,flush=True)
    calendar_key=next((k for k in ('SP500','SPY','RSP') if k in data),None)
    if not calendar_key:raise RuntimeError('Audit trading calendar unavailable')
    # SPY/RSP fallback supplies dates ONLY; never substitute them as S&P500 data.
    dates=data[calendar_key].loc[asof-pd.DateOffset(years=1):asof].index[-250:]
    rows=[];summary=[];started=time.monotonic()
    for i,day in enumerate(dates):
        r=evaluate(data,day)
        for k,v in r['results'].items():rows.append({'date':str(day.date()),'key':k,'title':v['title'],'state':v['state'],'rank':v['rank'],'reason':v['reason'],'interpretation':v['interpretation'],'confidence':v['confidence']})
        summary.append({'date':str(day.date()),'summary':r['summary']})
        if (i+1)%25==0:print('audit',i+1,'/',len(dates),round(time.monotonic()-started,1),'s',flush=True)
    df=pd.DataFrame(rows);df.to_csv(out/'daily_signals.csv',index=False)
    counts=pd.crosstab([df.key,df.title],df.state).reindex(columns=['안정','정상','참고','관찰','주의','위험','확인 부족'],fill_value=0)
    counts.to_csv(out/'signal_counts.csv')
    meta={'calendar_source':calendar_key,'partial_coverage':bool(errors),'type':'retrospective_revised_observations','asof':args.asof,'start':str(dates.min().date()),'end':str(dates.max().date()),'days':len(dates),'available_sources':sorted(data),'source_errors':errors,'not_connected':['CAPE','ADV','ABOVE200','HILO'],'point_in_time':False,'trading_returns_tested':False,'thresholds_calibrated':False}
    (out/'audit_metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2));pd.DataFrame(summary).to_csv(out/'daily_summary.csv',index=False)
    print(json.dumps(meta,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
