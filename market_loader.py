"""Persistent per-symbol stale-while-revalidate daily history cache."""
import json
import time
from pathlib import Path
from urllib.parse import quote
import pandas as pd
import requests
from loading_service import start,status,atomic_json,parallel_map
TICKERS={'NASDAQ':'^IXIC','RUSSELL':'^RUT','RSP':'RSP','SPY':'SPY','GOLD':'GC=F','SILVER':'SI=F','COPPER':'HG=F','WTI':'CL=F','DXY':'DX-Y.NYB','USDKRW':'USDKRW=X','USDJPY':'USDJPY=X'}

def read(path):
    try:
        value=json.loads(Path(path).read_text(encoding='utf-8'))
        return value if isinstance(value.get('items'),dict) else {'items':{}}
    except (OSError,ValueError,AttributeError):return {'items':{}}

def fetch_symbol(symbol):
    last=None
    for host in ('query1.finance.yahoo.com','query2.finance.yahoo.com'):
        try:
            response=requests.get(f'https://{host}/v8/finance/chart/{quote(symbol,safe="")}?range=2y&interval=1d&includePrePost=false',headers={'User-Agent':'Mozilla/5.0'},timeout=(3,7))
            response.raise_for_status();row=response.json()['chart']['result'][0]
            dates=pd.to_datetime(row['timestamp'],unit='s',utc=True).tz_convert(None).normalize()
            s=pd.Series(row['indicators']['quote'][0]['close'],index=dates,dtype=float).dropna().sort_index()
            if s.empty:raise ValueError('empty history')
            return {'updated':time.time(),'dates':[x.isoformat() for x in s.index],'values':s.tolist()}
        except Exception as exc:last=exc
    raise ValueError(f'{symbol}: {last}')

def load(path,force=False,fetch=fetch_symbol):
    path=Path(path);cached=read(path)
    due={k:v for k,v in TICKERS.items() if force or time.time()-cached['items'].get(k,{}).get('updated',0)>=600}
    if due:
        def refresh():
            snap=read(path)
            def accept(key,value):
                snap['items'][key]=value;atomic_json(path,snap)
            errors=parallel_map(due,fetch,accept,4)
            if errors:raise RuntimeError('; '.join(errors))
        start(path,refresh,cooldown=0 if force else 30)
    data={}
    for k,v in cached['items'].items():
        try:data[k]=pd.Series(v['values'],index=pd.to_datetime(v['dates']),dtype=float)
        except (ValueError,KeyError,TypeError):continue
    return data,status(path),cached
