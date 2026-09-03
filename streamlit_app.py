import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import requests, csv, os, threading, shutil, json, time, re, html
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path as _Path
from urllib.parse import quote

st.set_page_config(page_title="미국 증시 종합 위험지수", page_icon="🇺🇸", layout="wide")
st.markdown("""<style>
:root{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Apple SD Gothic Neo","Noto Sans KR","Segoe UI",sans-serif}
html,body,[class*="css"],.stApp,.stMarkdown,.stCaption,button,input,textarea,select{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Apple SD Gothic Neo","Noto Sans KR","Segoe UI",sans-serif!important}
.block-container{max-width:1180px;padding-top:2.2rem;padding-bottom:4rem}
.dev-credit{font-size:12px;color:#8b8f98;font-weight:600;letter-spacing:-.01em;margin-top:-.35rem;margin-bottom:.35rem}
.app-title-row{display:flex;align-items:center;margin-top:2px;margin-bottom:2px;padding:7px 0 4px;overflow:visible}.app-title-text{font-size:2.35rem;line-height:1.24;font-weight:850;letter-spacing:-.055em;color:#20232b;margin:0;overflow:visible}.overview-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:12px 0 8px}.overview-card{border:1px solid #e3e6eb;border-radius:22px;padding:18px 20px;background:rgba(255,255,255,.80);min-height:154px;box-sizing:border-box}.overview-head{display:flex;align-items:center;gap:9px;font-size:14px;font-weight:800;color:#555b65;margin-bottom:14px}.overview-head-icon{width:28px;height:28px;border:1px solid #e4e7eb;border-radius:9px;display:inline-flex;align-items:center;justify-content:center;background:#fff;flex:0 0 28px}.overview-head-icon svg{width:17px;height:17px}.overview-main{display:flex;align-items:baseline;gap:6px;min-height:52px}.overview-score{font-size:42px;line-height:1.04;font-weight:840;letter-spacing:-.045em;color:#2b2f37}.overview-unit{font-size:15px;font-weight:700;color:#444a54}.overview-status{display:flex;align-items:center;gap:9px;font-size:46px;font-weight:840;letter-spacing:-.045em;color:#282c34;min-height:52px;line-height:1.04}.overview-status .signal-status-dot{width:11px;height:11px;flex-basis:11px}.overview-sub{font-size:12px;color:#737983;margin-top:9px;line-height:1.45;min-height:18px}.overview-delta{font-size:11.5px;color:#717781;border-top:1px solid #eceef1;margin-top:12px;padding-top:9px}.overview-count{display:inline-flex;align-items:center;align-self:center;padding:2px 7px;border-radius:999px;background:#f2f3f5;color:#656b74;font-size:10.5px;line-height:1.3;font-weight:750;margin-left:5px;white-space:nowrap;letter-spacing:-.01em}
.hero{border:1px solid #e5e7eb;border-radius:28px;padding:30px 32px;margin:12px 0 22px;background:rgba(255,255,255,.72)}
.hero-score{font-size:64px;line-height:1;font-weight:850;letter-spacing:-.06em;color:#30323a}
.score-row{display:flex;align-items:baseline;gap:14px;margin-top:6px;flex-wrap:wrap}
.score-unit{font-size:20px;font-weight:650;letter-spacing:-.02em;color:#30323a}
.risk-guide{font-size:13px;font-weight:600;color:#6b7280;background:#f3f4f6;border-radius:999px;padding:7px 11px;white-space:nowrap}
.risk-label{font-size:18px;font-weight:750;margin-top:8px;color:#20232b}
.delta-up{color:#e5484d!important;font-weight:750!important}.delta-down{color:#2878d7!important;font-weight:750!important}.delta-flat{color:#8b8f98!important;font-weight:650!important}
.risk-state{display:flex;align-items:center;gap:6px;font-size:13px;color:#6b7280;margin-top:7px}.risk-dot{width:8px;height:8px;border-radius:50%;display:inline-block;flex:0 0 8px}.risk-dot.vlow{background:#22a06b}.risk-dot.low{background:#78b84a}.risk-dot.mid{background:#e5b82e}.risk-dot.high{background:#ef8b2c}.risk-dot.vhigh{background:#e5484d}.risk-dot.na{background:#a1a1aa}
.hero-state{display:flex;align-items:center;gap:8px;font-size:18px;font-weight:750;margin-top:8px;color:#20232b}.hero-state .risk-dot{width:10px;height:10px;flex-basis:10px}
.recession-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:8px}.recession-card{border:1px solid #e5e7eb;border-radius:16px;padding:11px 13px;background:rgba(255,255,255,.78);min-height:72px}.recession-name{font-size:12px;font-weight:700;color:#656b74;margin-bottom:6px}.recession-value{font-size:19px;font-weight:800;color:#282c34;line-height:1.15}
.signal-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin:12px 0 5px}.signal-card{border:1px solid #e5e7eb;border-radius:18px;padding:15px 16px;background:rgba(255,255,255,.78);min-height:96px}.signal-name{font-size:12px;font-weight:760;color:#737983;margin-bottom:9px;letter-spacing:-.01em}.signal-status{display:flex;align-items:center;gap:8px;min-height:25px}.signal-status-dot{width:10px;height:10px;border-radius:50%;display:inline-block;flex:0 0 10px}.signal-status-dot.normal{background:#22a06b}.signal-status-dot.watch{background:#e5b82e}.signal-status-dot.caution{background:#ef8b2c}.signal-status-dot.alert{background:#e5484d}.signal-value{font-size:21px;font-weight:850;color:#282c34;line-height:1.15;letter-spacing:-.025em}.signal-count{display:inline-flex;align-items:center;min-height:20px;padding:2px 7px;border-radius:999px;background:#f2f3f5;color:#656b74;font-size:10.5px;font-weight:750;white-space:nowrap}.signal-detail{font-size:11.5px;color:#737983;margin-top:8px;line-height:1.45;white-space:normal}
.small{font-size:13px;color:#6b7280}.hero-title{font-size:15px;font-weight:800;color:#555b65}.section{margin-top:30px;margin-bottom:10px}
div[data-testid="stMetric"]{border:1px solid #e5e7eb;border-radius:18px;padding:14px}
.data-status{font-size:12px;color:#6b7280;display:flex;align-items:center;gap:7px;margin:-2px 0 8px}.data-status span{width:7px;height:7px;border-radius:50%;background:#a1a1aa;animation:pulse 1.1s ease-in-out infinite}.data-status.done span{background:#22a06b;animation:none}
.loading-shell{border:1px solid #eceef1;border-radius:28px;padding:30px 32px;margin:20px 0;background:#fff}.loading-title,.loading-score,.loading-row span{background:linear-gradient(90deg,#f1f2f4 25%,#fafafa 50%,#f1f2f4 75%);background-size:200% 100%;animation:shimmer 1.2s infinite;border-radius:10px}.loading-title{height:18px;width:180px}.loading-score{height:58px;width:240px;margin-top:20px}.loading-row{display:flex;gap:12px;margin-top:24px}.loading-row span{display:block;height:70px;flex:1}.loading-text{font-size:13px;color:#8b8f98;margin-top:16px}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
.risk-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:10px}
.risk-card{position:relative;border:1px solid #e5e7eb;border-radius:18px;padding:16px 17px;background:rgba(255,255,255,.78);min-height:118px}
.risk-title{display:flex;align-items:center;gap:5px;font-size:15px;font-weight:750;color:#20232b;margin-bottom:13px}
.risk-score{font-size:27px;font-weight:850;line-height:1.05;letter-spacing:-.035em;color:#252831}
.risk-score span{font-size:13px;font-weight:650;color:#6b7280;letter-spacing:0}
.info-icon{appearance:none;-webkit-appearance:none;border:1.2px solid #7b818b;background:transparent;padding:0;margin:0;display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border-radius:50%;font-size:9px;line-height:1;font-weight:800;color:#626975;cursor:help;position:relative;outline:none;box-sizing:border-box}
.info-icon::before{content:'i';font-family:Arial,sans-serif}
.info-icon:hover,.info-icon:focus,.info-icon:focus-visible{background:#eef0f3;color:#32363f;border-color:#32363f}
.info-tip{visibility:hidden;opacity:0;pointer-events:none;position:absolute;z-index:999;left:50%;top:23px;transform:translateX(-50%) translateY(-2px);width:min(310px,76vw);padding:11px 12px;border:1px solid #dfe2e7;border-radius:12px;background:#fff;box-shadow:0 10px 30px rgba(0,0,0,.12);font-size:12.5px;font-weight:500;line-height:1.55;color:#3d424b;text-align:left;transition:opacity .12s ease,transform .12s ease}
.info-icon:hover .info-tip,.info-icon:focus .info-tip,.info-icon:focus-visible .info-tip{visibility:visible;opacity:1;transform:translateX(-50%) translateY(0)}
.market-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:10px}
.market-card{border:1px solid #e5e7eb;border-radius:17px;padding:14px 15px;background:rgba(255,255,255,.78);min-height:94px}
.market-name{display:flex;align-items:center;gap:5px;font-size:13px;font-weight:700;color:#555b65;margin-bottom:9px}
.market-value{font-size:22px;font-weight:820;letter-spacing:-.025em;color:#242832;line-height:1.1}
.market-delta{font-size:12px;margin-top:7px;color:#6b7280;white-space:nowrap}
@media(max-width:768px){
  .block-container{padding-top:calc(env(safe-area-inset-top,0px) + 2.65rem)!important;padding-left:14px!important;padding-right:14px!important;padding-bottom:3rem}
  h1{font-size:1.72rem!important;line-height:1.18!important;letter-spacing:-.045em!important;margin-top:0!important;margin-bottom:.55rem!important;font-weight:800!important}
  .dev-credit{font-size:11px;margin-top:-.2rem;margin-bottom:.45rem}
  p,li,div{letter-spacing:-.015em}
  .hero{border-radius:22px;padding:22px 20px;margin:8px 0 18px}
  .hero-score{font-size:50px}.score-unit{font-size:16px}.risk-guide{font-size:11px;padding:6px 9px}.risk-label{font-size:16px}
  .section{margin-top:24px;margin-bottom:8px}.section h3{font-size:1.15rem!important}
  div[data-testid="stAlert"]{padding:14px 15px!important;border-radius:16px!important}
  div[data-testid="stAlert"] p{font-size:.93rem!important;line-height:1.58!important}
  .risk-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
  .risk-card{min-height:104px;padding:13px 12px}
  .risk-title{font-size:13px;margin-bottom:10px;gap:4px}.risk-score{font-size:23px}.risk-state{font-size:12px;gap:5px}.risk-dot{width:7px;height:7px;flex-basis:7px}
  .info-icon{width:14px;height:14px;font-size:9px;border-width:1px;cursor:pointer}
  .info-tip{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%) scale(.98);width:min(330px,86vw);font-size:13px;padding:14px 15px;border-radius:15px;box-shadow:0 18px 55px rgba(0,0,0,.20)}
  .info-icon:hover .info-tip,.info-icon:focus .info-tip,.info-icon:focus-visible .info-tip{transform:translate(-50%,-50%) scale(1)}
  .market-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px}
  .market-card{min-height:84px;padding:12px 12px}.market-name{font-size:12px;margin-bottom:7px}.market-value{font-size:19px}.market-delta{font-size:11px;white-space:normal}
  div[data-testid="stMetric"]{padding:12px}
  .recession-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.recession-card{min-height:64px;padding:9px 8px;border-radius:14px}.recession-name{font-size:10.5px;margin-bottom:5px}.recession-value{font-size:16px}
  .signal-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:10px}.signal-card{min-height:92px;padding:13px 11px;border-radius:15px}.signal-name{font-size:10.5px;margin-bottom:8px}.signal-status{gap:6px;min-height:22px}.signal-status-dot{width:9px;height:9px;flex-basis:9px}.signal-value{font-size:18px}.signal-count{font-size:9.5px;min-height:18px;padding:1px 6px}.signal-detail{font-size:10.5px;margin-top:7px;line-height:1.4}
  .app-title-row{padding:6px 0 3px}.app-title-text{font-size:1.82rem;line-height:1.24}.overview-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:10px 0 7px}.overview-card{min-height:130px;padding:12px 9px;border-radius:15px}.overview-head{gap:5px;font-size:10.5px;margin-bottom:10px;line-height:1.25}.overview-head-icon{width:20px;height:20px;border-radius:7px;flex-basis:20px}.overview-head-icon svg{width:12px;height:12px}.overview-main{min-height:38px}.overview-score{font-size:28px;line-height:1.04}.overview-unit{font-size:10.5px}.overview-status{gap:5px;font-size:31px;min-height:38px;line-height:1.04}.overview-status .signal-status-dot{width:8px;height:8px;flex-basis:8px}.overview-sub{font-size:9.5px;margin-top:6px;line-height:1.35;min-height:25px}.overview-delta{font-size:9.5px;margin-top:7px;padding-top:6px}.overview-count{font-size:8.5px;padding:1px 5px;margin-left:1px}
}
</style>""", unsafe_allow_html=True)

FRED_CSV="https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
FRED_RECENT="https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd={}"
SERIES={
    "기준금리":"EFFR","2년물":"DGS2","10년물":"DGS10","30년물":"DGS30",
    "10년물기간프리미엄":"THREEFYTP10",
    "하이일드스프레드":"BAMLH0A0HYM2","BBB스프레드":"BAMLC0A4CBBB",
    "CPI":"CPIAUCSL","근원CPI":"CPILFESL","근원PCE":"PCEPILFE",
    "실업률":"UNRATE","신규실업수당":"ICSA","S&P500":"SP500","VIX":"VIXCLS"
}
WEIGHTS={"시장·밸류에이션":.25,"변동성":.10,"금리":.25,"신용":.15,"경기":.17,"물가":.08}

ROOT_CACHE=_Path(os.environ.get("LOCALAPPDATA", str(_Path.home()))) / "RiskMonitor"
CACHE_DIR=ROOT_CACHE / "data"
CACHE_DIR.mkdir(parents=True,exist_ok=True)
RECENT_DAYS=90
REFRESH_STATUS=ROOT_CACHE / "refresh_status.json"
FX_CACHE=ROOT_CACHE / "fx_snapshot.json"
CAPE_CACHE=ROOT_CACHE / "cape.csv"
CAPE_URL="https://www.multpl.com/shiller-pe/table/by-month"


def _migrate_legacy_cache():
    if any(CACHE_DIR.glob("*.csv")): return
    base=_Path(os.environ.get("LOCALAPPDATA", str(_Path.home())))
    for old_name in ("RiskMonitor_3_25_0","RiskMonitor_3_24_0","RiskMonitor_3_23_0"):
        old=base / old_name / "data"
        if old.exists():
            for f in old.glob("*.csv"):
                try: shutil.copy2(f, CACHE_DIR / f.name)
                except Exception: pass
            break
_migrate_legacy_cache()


def _parse_fred(text,series):
    text=text.lstrip("\ufeff").strip(); lines=text.splitlines(); header=None; hi=None
    for i,line in enumerate(lines[:30]):
        row=next(csv.reader([line]))
        if "observation_date" in row and series in row:
            header=row; hi=i; break
    if header is None: raise ValueError(f"{series}: FRED CSV 헤더 없음")
    di,vi=header.index("observation_date"),header.index(series); rec=[]
    for row in csv.reader(lines[hi+1:]):
        if len(row)<=max(di,vi): continue
        d=pd.to_datetime(row[di],errors="coerce"); v=pd.to_numeric(row[vi],errors="coerce")
        if pd.notna(d) and pd.notna(v): rec.append((d,float(v)))
    if not rec: raise ValueError(f"{series}: 유효 데이터 없음")
    df=pd.DataFrame(rec,columns=["date",series]).drop_duplicates("date").sort_values("date")
    s=df.set_index("date")[series].astype(float); s.index=pd.DatetimeIndex(s.index)
    return s.dropna()


def _fetch(series,recent=False):
    if recent:
        since=(pd.Timestamp.now().normalize()-pd.Timedelta(days=RECENT_DAYS)).strftime("%Y-%m-%d")
        url=FRED_RECENT.format(series,since)
    else: url=FRED_CSV.format(series)
    r=requests.get(url,timeout=(3,10)); r.raise_for_status(); return _parse_fred(r.text,series)


def _cache_file(series): return CACHE_DIR / f"{series}.csv"

def _read_cache(series):
    f=_cache_file(series)
    if not f.exists(): return pd.Series(dtype=float)
    try:
        df=pd.read_csv(f,parse_dates=["date"])
        if "value" not in df: return pd.Series(dtype=float)
        return pd.Series(df["value"].astype(float).values,index=pd.DatetimeIndex(df["date"])).dropna().sort_index()
    except Exception: return pd.Series(dtype=float)


def _write_cache(series,s):
    if s is None or not len(s): return
    tmp=_cache_file(series).with_suffix(".tmp")
    pd.DataFrame({"date":s.index,"value":s.values}).to_csv(tmp,index=False); tmp.replace(_cache_file(series))


def _merge_and_write(series,new):
    old=_read_cache(series)
    merged=pd.concat([old,new]).groupby(level=0).last().sort_index() if len(old) else new.sort_index()
    _write_cache(series,merged); return merged


def _treasury_latest():
    year=pd.Timestamp.now().year
    url=("https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
         f"daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv")
    headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
    r=requests.get(url,headers=headers,timeout=(3,6)); r.raise_for_status()
    rows=list(csv.DictReader(r.text.lstrip("\ufeff").splitlines())); parsed=[]
    for row in rows:
        d=pd.to_datetime(row.get("Date"),errors="coerce")
        if pd.isna(d): continue
        vals={}
        for col,key in (("2 Yr","DGS2"),("10 Yr","DGS10"),("30 Yr","DGS30")):
            v=pd.to_numeric(row.get(col),errors="coerce")
            if pd.notna(v): vals[key]=float(v)
        if vals: parsed.append((d,vals))
    if not parsed: raise ValueError("Treasury 최신 금리 데이터 없음")
    return max(parsed,key=lambda x:x[0])


def _read_all_cache():
    out={}
    for name,sid in SERIES.items():
        s=_read_cache(sid)
        if name=="기준금리" and not len(s):
            legacy=_read_cache("FEDFUNDS")
            if len(legacy): s=legacy
        out[name]=s
    return out


def _initial_fetch():
    out={}; errors=[]
    def one(item):
        name,sid=item
        try:
            s=_fetch(sid,recent=False); _write_cache(sid,s); return name,s,None
        except Exception as e: return name,pd.Series(dtype=float),f"{name} ({sid}): {e}"
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures=[ex.submit(one,x) for x in SERIES.items()]
        for f in as_completed(futures):
            name,s,err=f.result(); out[name]=s
            if err: errors.append(err)
    return out,errors


def _refresh_series(name,sid):
    try:
        cached=_read_cache(sid); new=_fetch(sid,recent=bool(len(cached)))
        return name,_merge_and_write(sid,new),None
    except Exception as e: return name,_read_cache(sid),f"{name}: {e}"


def _fetch_yahoo_symbol(ticker):
    enc=quote(ticker,safe="")
    headers={"User-Agent":"Mozilla/5.0"}
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?range=5d&interval=1m&includePrePost=false"
    r=requests.get(url,headers=headers,timeout=(3,6)); r.raise_for_status()
    result=r.json().get("chart",{}).get("result") or []
    if not result: raise ValueError(f"{ticker}: Yahoo 데이터 없음")
    meta=result[0].get("meta",{})
    cur=meta.get("regularMarketPrice")
    prev=meta.get("chartPreviousClose",meta.get("previousClose"))
    if cur is None: raise ValueError(f"{ticker}: 현재값 없음")
    if prev is None:
        url2=f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?range=10d&interval=1d"
        r2=requests.get(url2,headers=headers,timeout=(3,6)); r2.raise_for_status()
        rr=(r2.json().get("chart",{}).get("result") or [None])[0]
        closes=[] if rr is None else (rr.get("indicators",{}).get("quote",[{}])[0].get("close") or [])
        closes=[float(x) for x in closes if x is not None]
        prev=closes[-2] if len(closes)>=2 else (closes[-1] if closes else np.nan)
    return {"value":float(cur),"prev":float(prev) if prev is not None else np.nan,"time":time.time()}


def _refresh_fx():
    tickers={"원/달러":"USDKRW=X","엔/달러":"USDJPY=X","달러인덱스":"DX-Y.NYB","WTI 유가":"CL=F"}
    snap={"updated":time.time(),"source":"Yahoo Finance","items":{}}
    errors=[]
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(_fetch_yahoo_symbol,t):name for name,t in tickers.items()}
        for f,name in [(f,n) for f,n in futs.items()]:
            try: snap["items"][name]=f.result()
            except Exception as e: errors.append(f"{name}: {e}")
    if snap["items"]:
        ROOT_CACHE.mkdir(parents=True,exist_ok=True)
        tmp=FX_CACHE.with_suffix(".tmp"); tmp.write_text(json.dumps(snap,ensure_ascii=False),encoding="utf-8"); tmp.replace(FX_CACHE)
    return errors


def _read_fx():
    try: return json.loads(FX_CACHE.read_text(encoding="utf-8"))
    except Exception: return {"items":{}}


def _read_cape():
    if not CAPE_CACHE.exists(): return pd.Series(dtype=float)
    try:
        df=pd.read_csv(CAPE_CACHE,parse_dates=["date"])
        if "cape" not in df: return pd.Series(dtype=float)
        out=pd.Series(pd.to_numeric(df["cape"],errors="coerce").values,index=pd.DatetimeIndex(df["date"])).dropna()
        return out[~out.index.duplicated(keep="last")].sort_index()
    except Exception: return pd.Series(dtype=float)


def _refresh_cape():
    headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
    r=requests.get(CAPE_URL,headers=headers,timeout=(3,7)); r.raise_for_status()
    # Multpl의 월별 표를 외부 HTML 파서 의존성 없이 읽는다.
    rows=re.findall(r"<tr[^>]*>\s*<td[^>]*>(.*?)</td>\s*<td[^>]*>(.*?)</td>\s*</tr>",r.text,re.I|re.S)
    rec=[]
    for d_raw,v_raw in rows:
        d_txt=re.sub(r"<[^>]+>","",html.unescape(d_raw)).strip()
        v_txt=re.sub(r"<[^>]+>","",html.unescape(v_raw)).replace("\xa0","").strip()
        d=pd.to_datetime(d_txt,errors="coerce"); v=pd.to_numeric(v_txt.replace(",",""),errors="coerce")
        if pd.notna(d) and pd.notna(v): rec.append((d,float(v)))
    if len(rec)<100: raise ValueError("CAPE 월별 표 파싱 실패")
    df=pd.DataFrame(rec,columns=["date","cape"]).drop_duplicates("date",keep="last").sort_values("date")
    tmp=CAPE_CACHE.with_suffix(".tmp"); df.to_csv(tmp,index=False); tmp.replace(CAPE_CACHE)
    return True


def _write_refresh_status(ok,errors):
    ROOT_CACHE.mkdir(parents=True,exist_ok=True)
    payload={"finished":time.time(),"ok":bool(ok),"errors":errors[:10]}
    tmp=REFRESH_STATUS.with_suffix(".tmp"); tmp.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8"); tmp.replace(REFRESH_STATUS)


def _refresh_all_background():
    errors=[]
    priority=[("기준금리","EFFR"),("2년물","DGS2"),("10년물","DGS10"),("30년물","DGS30")]
    with ThreadPoolExecutor(max_workers=6) as ex:
        fs=[ex.submit(_refresh_series,*x) for x in priority]
        fx_future=ex.submit(_refresh_fx)
        cape_future=ex.submit(_refresh_cape)
        for f in fs:
            _,_,err=f.result()
            if err: errors.append(err)
        try: errors.extend(fx_future.result())
        except Exception as e: errors.append(f"환율: {e}")
        try: cape_future.result()
        except Exception as e: errors.append(f"CAPE: {e}")
    try:
        d,vals=_treasury_latest()
        for sid,v in vals.items(): _merge_and_write(sid,pd.Series([v],index=pd.DatetimeIndex([d]),dtype=float))
    except Exception as e: errors.append(f"미 재무부 최신 금리: {e}")
    rest=[x for x in SERIES.items() if x not in priority]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures=[ex.submit(_refresh_series,*x) for x in rest]
        for f in as_completed(futures):
            _,_,err=f.result()
            if err: errors.append(err)
    _write_refresh_status(True,errors)


def _status_mtime():
    try: return REFRESH_STATUS.stat().st_mtime
    except Exception: return 0.0


def _cache_ready(data):
    required=("기준금리","2년물","10년물","하이일드스프레드","CPI","실업률","S&P500","VIX")
    return all(len(data.get(k,pd.Series(dtype=float)).dropna()) for k in required)


data=_read_all_cache(); initial_errors=[]
if not _cache_ready(data):
    loading=st.empty(); loading.markdown("""
    <div class='loading-shell'><div class='loading-title'></div><div class='loading-score'></div>
    <div class='loading-row'><span></span><span></span><span></span></div><div class='loading-text'>최초 데이터 준비 중…</div></div>""",unsafe_allow_html=True)
    _,initial_errors=_initial_fetch(); data=_read_all_cache(); loading.empty()
if not _cache_ready(data):
    st.error("시장 데이터를 충분히 가져오지 못했습니다.")
    if initial_errors:
        with st.expander("오류 상세"):
            for e in initial_errors: st.write(e)
    st.stop()

if "refresh_started" not in st.session_state:
    st.session_state.refresh_started=True; st.session_state.refresh_applied=False; st.session_state.refresh_baseline=_status_mtime()
    threading.Thread(target=_refresh_all_background,daemon=True).start()

@st.fragment(run_every="1s")
def refresh_indicator():
    baseline=st.session_state.get("refresh_baseline",0.0); now=_status_mtime()
    if st.session_state.get("refresh_started") and not st.session_state.get("refresh_applied") and now>baseline:
        st.session_state.refresh_applied=True; st.rerun()
    if st.session_state.get("refresh_applied"):
        try:
            info=json.loads(REFRESH_STATUS.read_text(encoding="utf-8")); ts=datetime.fromtimestamp(info.get("finished",time.time()), tz=ZoneInfo("Asia/Seoul")).strftime("%H:%M KST")
            st.markdown(f"<div class='data-status done'><span></span>최신 데이터 · {ts}</div>",unsafe_allow_html=True)
        except Exception: st.markdown("<div class='data-status done'><span></span>최신 데이터</div>",unsafe_allow_html=True)
    else: st.markdown("<div class='data-status'><span></span>최신 데이터 확인 중…</div>",unsafe_allow_html=True)


def latest(s):
    s=s.dropna(); return float(s.iloc[-1]) if len(s) else np.nan

def second(s):
    z=s.dropna(); return float(z.iloc[-2]) if len(z)>=2 else np.nan

def clamp(x): return float(np.clip(x,0,100)) if pd.notna(x) else np.nan

def interp_score(x,xp,fp):
    if pd.isna(x): return np.nan
    return clamp(float(np.interp(float(x),xp,fp)))


def percentile_score(series,value,high_is_risk=True,lookback_years=20):
    s=series.dropna().copy()
    if len(s)<30 or pd.isna(value): return np.nan
    idx=pd.to_datetime(s.index,errors="coerce"); s=s[~idx.isna()].copy(); s.index=idx[~idx.isna()]
    if not len(s): return np.nan
    cutoff=s.index.max()-pd.DateOffset(years=lookback_years); s=s.loc[s.index>=cutoff]
    if len(s)<30:return np.nan
    p=float((s<=float(value)).mean()*100); return clamp(p if high_is_risk else 100-p)


def weighted(scores):
    n=d=0
    for k,w in WEIGHTS.items():
        v=scores.get(k,np.nan)
        if pd.notna(v): n+=float(v)*w; d+=w
    return clamp(n/d) if d else np.nan


def weighted_custom(scores,weights):
    n=d=0
    for k,w in weights.items():
        v=scores.get(k,np.nan)
        if pd.notna(v): n+=float(v)*w; d+=w
    return clamp(n/d) if d else np.nan


def market_overheat_from_dev(dev):
    # 가격이 붕괴한 뒤의 스트레스가 아니라, 폭락 전 가격 과열 취약성을 측정한다.
    return interp_score(dev,[-15,-5,0,5,10,15,20],[0,5,15,40,70,90,100])


def cape_score(cape_value):
    return interp_score(cape_value,[10,15,20,25,30,35,40,45],[5,10,25,45,65,80,92,100])


def market_momentum_score(sp,dev):
    z=sp.dropna()
    if len(z)<21 or z.iloc[-21]<=0:return np.nan
    ret20=(z.iloc[-1]/z.iloc[-21]-1)*100
    raw=interp_score(ret20,[-12,-6,0,3,6,10,15],[0,5,10,30,55,80,100])
    # 폭락 뒤의 기술적 반등을 과열로 오인하지 않도록 200일선 위치에 따라 모멘텀 영향 제한.
    if pd.isna(dev): gate=.5
    elif dev<=0: gate=.25
    elif dev<5: gate=.25+.35*(dev/5)
    elif dev<10: gate=.60+.30*((dev-5)/5)
    else: gate=1.0
    return clamp(raw*gate),ret20


def market_risk_score(sp,cape):
    if len(sp.dropna())<220:return np.nan,{"dev":np.nan,"cape":np.nan,"mom20":np.nan}
    z=sp.dropna(); ma=z.rolling(200).mean(); dev=(latest(z)/latest(ma)-1)*100
    over=market_overheat_from_dev(dev)
    cv=latest(cape) if len(cape.dropna()) else np.nan
    val=cape_score(cv) if pd.notna(cv) else np.nan
    mom,mom20=market_momentum_score(z,dev)
    score=weighted_custom({"over":over,"value":val,"momentum":mom},{"over":.45,"value":.35,"momentum":.20})
    return score,{"dev":dev,"cape":cv,"over":over,"valuation":val,"momentum":mom,"mom20":mom20}


def vix_surge_detail(vix):
    z=vix.dropna()
    if len(z)<6 or z.iloc[-6]<=0:return {"score":np.nan,"pct":np.nan,"points":np.nan}
    pct=(z.iloc[-1]/z.iloc[-6]-1)*100; pts=float(z.iloc[-1]-z.iloc[-6])
    pct_s=interp_score(pct,[-25,0,10,25,50,80,150],[0,5,20,45,70,90,100])
    pts_s=interp_score(pts,[-8,0,2,5,10,20,40],[0,5,20,45,70,90,100])
    return {"score":weighted_custom({"pct":pct_s,"pts":pts_s},{"pct":.60,"pts":.40}),"pct":pct,"points":pts}


def volatility_score(vix):
    level=interp_score(latest(vix),[10,12,15,20,25,30,40,60],[5,10,20,40,60,75,90,100])
    surge=vix_surge_detail(vix)
    return weighted_custom({"level":level,"surge":surge["score"]},{"level":.55,"surge":.45}),{"level":level,**surge}


def sahm_series(u):
    m=u.resample("MS").mean(); ma3=m.rolling(3).mean(); low=ma3.rolling(12,min_periods=12).min(); return (ma3-low).dropna()


def sahm_score(u):
    s=sahm_series(u); v=latest(s) if len(s) else np.nan
    return interp_score(v,[0,.1,.2,.35,.5,.75,1.5],[5,15,30,50,70,90,100]),v


def rate_rise_score(y10,obs=20):
    z=y10.dropna()
    if len(z)<=obs:return np.nan,np.nan
    delta=float(z.iloc[-1]-z.iloc[-1-obs])
    return interp_score(delta,[-1,-.5,0,.15,.35,.60,1.0,1.5],[0,5,10,25,50,75,90,100]),delta


def rate_score(y2,y10,fed,term_premium):
    curve=(y10-y2).dropna(); policy=(y10-fed).dropna()
    curve_v=latest(curve); policy_v=latest(policy); tp=latest(term_premium) if len(term_premium.dropna()) else np.nan
    level=interp_score(latest(y10),[0,1.5,2.5,3.5,4.25,5,6,8],[5,10,20,35,55,75,90,100])
    rise,rise_delta=rate_rise_score(y10,20)
    # 음의 스프레드는 단기금리가 장기금리보다 높은 긴축/역전 상태로 평가.
    curve_s=interp_score(curve_v,[-2,-1,-.5,0,.5,1,2],[100,90,75,60,35,20,5])
    policy_s=interp_score(policy_v,[-3,-2,-1,0,1,2],[100,90,70,45,20,5])
    tp_s=interp_score(tp,[-1,-.5,0,.5,1,1.5,2.5],[5,10,20,45,65,80,100]) if pd.notna(tp) else np.nan
    score=weighted_custom({"level":level,"rise":rise,"curve":curve_s,"policy":policy_s,"tp":tp_s},
                          {"level":.35,"rise":.25,"curve":.15,"policy":.15,"tp":.10})
    return score,{"level":level,"rise":rise,"rise_delta":rise_delta,"curve":curve_s,"curve_value":curve_v,
                  "policy":policy_s,"policy_value":policy_v,"tp":tp_s,"tp_value":tp}


def spread_change_score(s,obs=20):
    z=s.dropna()
    if len(z)<=obs:return np.nan
    delta=float(z.iloc[-1]-z.iloc[-1-obs])
    if obs<=5:
        return interp_score(delta,[-.5,0,.15,.30,.60,1.20,2.0],[0,5,25,45,70,90,100])
    return interp_score(delta,[-1,0,.25,.50,1.0,2.0,4.0],[0,5,25,45,70,90,100])


def credit_score(hy,bbb):
    hy_abs=interp_score(latest(hy),[1.5,2.5,3.5,5,7,10,15],[5,12,25,50,70,90,100])
    bbb_abs=interp_score(latest(bbb),[.4,.8,1.0,1.5,2.5,4,6],[5,12,20,40,65,85,100]) if len(bbb.dropna()) else np.nan
    hy5,bbb5=spread_change_score(hy,5),spread_change_score(bbb,5)
    hy20,bbb20=spread_change_score(hy,20),spread_change_score(bbb,20)
    fast5=weighted_custom({"hy":hy5,"bbb":bbb5},{"hy":.70,"bbb":.30})
    trend20=weighted_custom({"hy":hy20,"bbb":bbb20},{"hy":.70,"bbb":.30})
    score=weighted_custom({"hy":hy_abs,"bbb":bbb_abs,"fast5":fast5,"trend20":trend20},
                          {"hy":.45,"bbb":.20,"fast5":.15,"trend20":.20})
    return score,{"hy_abs":hy_abs,"bbb_abs":bbb_abs,"fast5":fast5,"trend20":trend20}


def claims_score(icsa):
    z=icsa.dropna()
    if len(z)<20:return np.nan,{"level":np.nan,"trend":np.nan,"trend_pct":np.nan}
    ma4=z.rolling(4).mean().dropna()
    if len(ma4)<12:return np.nan,{"level":np.nan,"trend":np.nan,"trend_pct":np.nan}
    # 인구/노동시장 규모 변화 때문에 절대 건수 대신 과거 10년 내 상대 수준을 보되, 미래 데이터는 사용하지 않는다.
    level=percentile_score(ma4,latest(ma4),True,lookback_years=10)
    if len(ma4)>=9 and ma4.iloc[-9]>0:
        pct=(ma4.iloc[-1]/ma4.iloc[-9]-1)*100
        trend=interp_score(pct,[-20,-5,0,5,10,20,40],[0,5,15,30,50,75,100])
    else: pct=trend=np.nan
    return weighted_custom({"level":level,"trend":trend},{"level":.60,"trend":.40}),{"level":level,"trend":trend,"trend_pct":pct}


def economy_score(unemp,icsa):
    unemp_level=interp_score(latest(unemp),[3,3.5,4,4.5,5,6,8,10],[10,15,25,40,55,70,90,100])
    sahm_s,sahm_v=sahm_score(unemp); claims,cd=claims_score(icsa)
    # Sahm 단독 신호의 오경보를 줄이기 위해 신규 실업수당의 최근 8주 상승 추세가 확인될 때만 강한 신호로 인정한다.
    claims_confirm=pd.notna(cd.get("trend",np.nan)) and cd.get("trend",0)>=50
    sahm_adj=sahm_s
    if pd.notna(sahm_v) and sahm_v>=.5 and not claims_confirm: sahm_adj=min(sahm_s,55)
    score=weighted_custom({"unemp":unemp_level,"sahm":sahm_adj,"claims":claims},{"unemp":.30,"sahm":.35,"claims":.35})
    return score,{"unemp":unemp_level,"sahm":sahm_adj,"sahm_raw":sahm_s,"sahm_value":sahm_v,"claims":claims,"claims_confirm":claims_confirm,**{f"claims_{k}":v for k,v in cd.items()}}


def _annualized_3m(s):
    m=s.dropna().resample("MS").last().dropna()
    if len(m)<4 or m.iloc[-4]<=0:return np.nan
    return ((m.iloc[-1]/m.iloc[-4])**4-1)*100


def inflation_level_score(v):
    return interp_score(v,[0,1,2,2.5,3,4,6,8,10],[5,10,20,35,50,70,90,98,100])


def inflation_momentum_score(v):
    return interp_score(v,[-2,0,1,2,2.5,3,4,6,8,10],[0,5,10,20,35,50,70,90,98,100])


def _inflation_metric(s,yoy_weight,m3_weight):
    yoy=latest(s.pct_change(12)*100); m3=_annualized_3m(s)
    ys=inflation_level_score(yoy); ms=inflation_momentum_score(m3)
    return weighted_custom({"yoy":ys,"m3":ms},{"yoy":yoy_weight,"m3":m3_weight}),{"yoy":yoy,"m3":m3,"yoy_score":ys,"m3_score":ms}


def inflation_score(cpi,core_cpi,core_pce):
    h,hd=_inflation_metric(cpi,.55,.45)
    c,cd=_inflation_metric(core_cpi,.45,.55) if len(core_cpi.dropna()) else (np.nan,{})
    p,pd_=_inflation_metric(core_pce,.45,.55) if len(core_pce.dropna()) else (np.nan,{})
    score=weighted_custom({"headline":h,"core_cpi":c,"core_pce":p},{"headline":.25,"core_cpi":.35,"core_pce":.40})
    recent=weighted_custom({"headline":hd.get("m3_score",np.nan),"core_cpi":cd.get("m3_score",np.nan),"core_pce":pd_.get("m3_score",np.nan)},
                           {"headline":.25,"core_cpi":.35,"core_pce":.40})
    yoy_comp=weighted_custom({"headline":hd.get("yoy_score",np.nan),"core_cpi":cd.get("yoy_score",np.nan),"core_pce":pd_.get("yoy_score",np.nan)},
                             {"headline":.25,"core_cpi":.35,"core_pce":.40})
    return score,{"headline":hd,"core_cpi":cd,"core_pce":pd_,"recent":recent,"yoy":yoy_comp}


def inversion_memory(spread210,months=18,full_months=6):
    z=spread210.dropna().sort_index()
    if not len(z):return 0.0,None
    inv=z[z<0]
    if not len(inv):return 0.0,None
    last_inv=inv.index[-1]; end=z.index[-1]
    age=max(0.0,(end-last_inv).days/30.44)
    if age<=full_months:sev=100.0
    elif age>=months:sev=0.0
    else:sev=100*(months-age)/(months-full_months)
    return clamp(sev),last_inv


def structural_signals(details,spread210):
    items=[]; mem,last_inv=inversion_memory(spread210)
    if mem>=25:
        items.append(("장단기 금리 역전 이력",mem))
    val=details.get("market",{}).get("valuation",np.nan)
    if pd.notna(val) and val>=85: items.append(("시장 고평가",val))
    recent=details.get("inflation",{}).get("recent",np.nan); yoy=details.get("inflation",{}).get("yoy",np.nan)
    if pd.notna(recent) and recent>=70 and (pd.isna(yoy) or recent>=yoy): items.append(("물가 재가속",recent))
    ed=details.get("economy",{})
    if pd.notna(ed.get("sahm_value",np.nan)) and ed.get("sahm_value",0)>=.5 and ed.get("claims_confirm",False):
        items.append(("고용 악화 확인",max(ed.get("sahm",0),ed.get("claims_trend",0))))
    if len(items)>=3:level="경계"
    elif len(items)>=2:level="주의"
    elif len(items)==1:level="관찰"
    else:level="정상"
    return {"level":level,"count":len(items),"items":items,"inversion_memory":mem,"last_inversion":last_inv}


def fast_signal_scores(details):
    credit_vals=[details.get("credit",{}).get("fast5",np.nan),details.get("credit",{}).get("trend20",np.nan)]
    credit_vals=[float(v) for v in credit_vals if pd.notna(v)]
    return {
        "VIX":details.get("volatility",{}).get("score",np.nan),
        "신용":max(credit_vals) if credit_vals else np.nan,
        "10년물":details.get("rates",{}).get("rise",np.nan),
        "고용":details.get("economy",{}).get("claims_trend",np.nan),
    }


def rapid_alert(current_fast,previous_fast=None):
    previous_fast=previous_fast or {}
    flags={k:(pd.notna(v) and v>=70) for k,v in current_fast.items()}
    prev_flags={k:(pd.notna(previous_fast.get(k,np.nan)) and previous_fast.get(k,np.nan)>=70) for k in current_fast}
    count=sum(flags.values()); prev_count=sum(prev_flags.values())
    extreme_vix=pd.notna(current_fast.get("VIX",np.nan)) and current_fast.get("VIX",0)>=85
    extreme_credit=pd.notna(current_fast.get("신용",np.nan)) and current_fast.get("신용",0)>=80
    if count>=3 and (prev_count>=2 or sum(pd.notna(v) and v>=85 for v in current_fast.values())>=2):
        level="강한 스트레스"
    elif count>=2 and (prev_count>=2 or (extreme_vix and extreme_credit)):
        level="급변 경보"
    elif count>=1:
        level="관찰"
    else:
        level="정상"
    active=[k for k,v in flags.items() if v]
    return {"level":level,"count":count,"active":active,"scores":current_fast}


def _truncate_one(s):
    z=s.dropna(); return z.iloc[:-1] if len(z)>1 else z


def compute_snapshot(data,cape,with_alerts=True):
    fed,y2,y10=data["기준금리"],data["2년물"],data["10년물"]
    tp=data.get("10년물기간프리미엄",pd.Series(dtype=float))
    hy,bbb=data["하이일드스프레드"],data["BBB스프레드"]
    cpi,core_cpi,core_pce=data["CPI"],data["근원CPI"],data["근원PCE"]
    unemp,icsa,sp,vix=data["실업률"],data["신규실업수당"],data["S&P500"],data["VIX"]
    market,md=market_risk_score(sp,cape); vol,vd=volatility_score(vix); rates,rd=rate_score(y2,y10,fed,tp)
    credit,cd=credit_score(hy,bbb); econ,ed=economy_score(unemp,icsa); infl,id_=inflation_score(cpi,core_cpi,core_pce)
    scores={"시장·밸류에이션":market,"변동성":vol,"금리":rates,"신용":credit,"경기":econ,"물가":infl}
    details={"market":md,"volatility":vd,"rates":rd,"credit":cd,"economy":ed,"inflation":id_}
    overall=weighted(scores)
    structure=structural_signals(details,(y10-y2).dropna()) if with_alerts else None
    return {"scores":scores,"details":details,"overall":overall,"structure":structure}

def label(x):
    if pd.isna(x):return "데이터 부족"
    if x<=20:return "매우 낮음"
    if x<=40:return "낮음"
    if x<=60:return "보통"
    if x<=80:return "높음"
    return "매우 높음"

def risk_class(x):
    if pd.isna(x): return "na"
    if x<=20: return "vlow"
    if x<=40: return "low"
    if x<=60: return "mid"
    if x<=80: return "high"
    return "vhigh"



def delta_value(a,b):
    if pd.isna(a) or pd.isna(b): return None,"비교 불가","flat"
    d=float(a-b)
    if d>0:return d,f"▲ {abs(d):.1f}","up"
    if d<0:return d,f"▼ {abs(d):.1f}","down"
    return d,"— 0.0","flat"


fed,y2,y10,y30=data["기준금리"],data["2년물"],data["10년물"],data["30년물"]
term_premium=data.get("10년물기간프리미엄",pd.Series(dtype=float))
hy,bbb=data["하이일드스프레드"],data["BBB스프레드"]
cpi,core_cpi,core_pce=data["CPI"],data["근원CPI"],data["근원PCE"]
unemp,icsa,sp,vix=data["실업률"],data["신규실업수당"],data["S&P500"],data["VIX"]
cape=_read_cape()
spread210=(y10-y2).dropna(); spread10fed=(y10-fed).dropna()

snapshot=compute_snapshot(data,cape)
scores=snapshot["scores"]; details=snapshot["details"]; overall=snapshot["overall"]; structure=snapshot["structure"]
dev=details["market"].get("dev",np.nan); sahm_now=details["economy"].get("sahm_value",np.nan)

# 전일 비교는 직전 S&P500 거래일 기준으로 모든 시계열을 그 날짜까지 잘라 재계산한다.
zsp=sp.dropna(); prev_date=zsp.index[-2] if len(zsp)>=2 else None
if prev_date is not None:
    prev_data={k:v.loc[:prev_date].dropna() for k,v in data.items()}
    prev_cape=cape.loc[:prev_date].dropna() if len(cape) else cape
    prev_snapshot=compute_snapshot(prev_data,prev_cape,with_alerts=False)
    prev_overall=prev_snapshot["overall"]
    prev_fast=fast_signal_scores(prev_snapshot["details"])
else:
    prev_snapshot=None; prev_overall=np.nan; prev_fast={}
current_fast=fast_signal_scores(details)
rapid=rapid_alert(current_fast,prev_fast)

st.markdown('''<div class="app-title-row"><div class="app-title-text">미국 증시 종합 위험지수</div></div>''', unsafe_allow_html=True)
st.markdown('<div class="dev-credit">Developed by 유유상</div>', unsafe_allow_html=True)
st.caption("시장·밸류에이션·금리·신용·경기·물가를 현재 공개 데이터 기준으로 자동 분석")
refresh_indicator(); _,delta_text,delta_class=delta_value(overall,prev_overall)

_structure_detail=", ".join(x[0] for x in structure.get("items",[])) if structure.get("items") else "뚜렷한 구조적 위험 신호 없음"
_structure_raw=structure.get("level","정상")
_structure_state={"정상":("정상","normal"),"관찰":("관찰","watch"),"주의":("주의","caution"),"경계":("경고","alert")}.get(_structure_raw,(str(_structure_raw),"watch"))
_structure_count=int(structure.get("count",0) or 0)
_structure_count_html=f'<span class="overview-count">{_structure_count}개</span>' if _structure_count else ""
_rapid_detail=", ".join(rapid.get("active",[])) if rapid.get("active") else "동시 급변 신호 없음"
_rapid_raw=rapid.get("level","정상")
_rapid_state={"정상":("정상","normal"),"관찰":("관찰","watch"),"급변 경보":("주의","caution"),"강한 스트레스":("경고","alert")}.get(_rapid_raw,(str(_rapid_raw),"watch"))
_rapid_count=int(rapid.get("count",0) or 0)
_rapid_count_html=f'<span class="overview-count">{_rapid_count}개</span>' if _rapid_count else ""
_structure_detail_html=html.escape(_structure_detail)
_rapid_detail_html=html.escape(_rapid_detail)

_shield='''<svg viewBox="0 0 24 24" fill="none" stroke="#4a5568" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2.8 19 5.6v5.2c0 4.6-2.7 8.2-7 10.4-4.3-2.2-7-5.8-7-10.4V5.6L12 2.8Z"/><path d="m8.2 13.2 2.2-2.2 1.8 1.7 3.6-4"/></svg>'''
_warn='''<svg viewBox="0 0 24 24" fill="none" stroke="#c98b00" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 4.2 2.8 17.3a2 2 0 0 0 1.7 3h15a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></svg>'''
_bell='''<svg viewBox="0 0 24 24" fill="none" stroke="#2f7d5a" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></svg>'''
st.markdown(
    f'<div class="overview-grid">'
    f'<div class="overview-card"><div class="overview-head"><span class="overview-head-icon">{_shield}</span>위험지수</div><div class="overview-main"><span class="overview-score">{overall:.1f}</span><span class="overview-unit">/100</span></div><div class="overview-sub"><span class="risk-dot {risk_class(overall)}"></span>&nbsp; <b>{label(overall)}</b></div><div class="overview-delta">전일 대비 <span class="delta-{delta_class}">{delta_text}</span></div></div>'
    f'<div class="overview-card"><div class="overview-head"><span class="overview-head-icon">{_warn}</span>구조적 위험 신호</div><div class="overview-status"><span class="signal-status-dot {_structure_state[1]}"></span>{_structure_state[0]}{_structure_count_html}</div><div class="overview-sub">{_structure_detail_html}</div></div>'
    f'<div class="overview-card"><div class="overview-head"><span class="overview-head-icon">{_bell}</span>시장 급변 신호</div><div class="overview-status"><span class="signal-status-dot {_rapid_state[1]}"></span>{_rapid_state[0]}{_rapid_count_html}</div><div class="overview-sub">{_rapid_detail_html}</div></div>'
    f'</div>', unsafe_allow_html=True)

comments=[]
if pd.notna(dev):
    if dev>=15: comments.append("S&P500의 200일선 대비 과열 수준이 매우 높습니다.")
    elif dev>=10: comments.append("S&P500의 200일선 대비 과열 부담이 높은 편입니다.")
    elif dev<=0: comments.append("S&P500의 200일선 기준 가격 과열 부담은 낮은 상태입니다.")
_cape_now=details.get("market",{}).get("cape",np.nan)
if pd.notna(_cape_now) and details.get("market",{}).get("valuation",0)>=80: comments.append(f"CAPE가 {_cape_now:.1f}배로 역사적 고평가 구간에 있습니다.")
if rapid.get("level") in ("급변 경보","강한 스트레스"): comments.append("서로 다른 빠른 지표가 동시에 악화돼 단기 시장 스트레스가 확인됩니다.")
elif rapid.get("level")=="관찰": comments.append("한 개 이상의 빠른 지표가 급변해 추가 확인이 필요한 상태입니다.")
if structure.get("count",0)>=2: comments.append("여러 구조적 취약성이 동시에 나타나 중기 하락 위험을 주의해서 볼 필요가 있습니다.")
if not comments: comments.append("현재 구조적 취약성과 급변 신호가 동시에 강하게 나타나지는 않고 있습니다.")
st.info("**현재 시장 해석**\n\n"+" ".join(comments))

st.markdown('<div class="section"><h3>구성요소 위험도</h3></div>',unsafe_allow_html=True)
labels={"시장·밸류에이션":"시장·밸류에이션 위험","변동성":"변동성 위험","금리":"금리 위험","신용":"신용시장 위험","경기":"경기 위험","물가":"물가 위험"}
infos={
    "시장·밸류에이션":"S&P500의 200일 이동평균 대비 과열 45%, CAPE 밸류에이션 35%, 최근 20거래일 상승 모멘텀 20%를 반영합니다. 폭락 이후 가격 하락 자체를 위험점수로 추가하지 않습니다.",
    "변동성":"현재 VIX 절대 수준 55% + 최근 5거래일 급등 45%입니다. 급등은 상승률과 포인트 상승폭을 함께 봅니다.",
    "금리":"10년물 수준 35% + 최근 20거래일 상승속도 25% + 10Y-2Y 15% + 10Y-EFFR 15% + 10년물 기간프리미엄 10%입니다.",
    "신용":"하이일드 OAS 수준 45% + BBB OAS 수준 20% + 최근 5거래일 확대 15% + 최근 20거래일 확대 20%입니다.",
    "경기":"실업률 수준 30% + Sahm Rule 35% + 신규 실업수당 35%입니다. Sahm Rule은 신규 실업수당의 최근 8주 상승 추세가 확인되지 않으면 강도를 제한합니다.",
    "물가":"CPI 25% + 근원 CPI 35% + 근원 PCE 40%이며, 각 지표에서 전년동월비와 최근 3개월 연율화 흐름을 함께 반영합니다. 최근 흐름의 비중을 더 높였습니다."
}
risk_cards=[]
for k in scores:
    score_txt=f"{scores[k]:.1f}" if pd.notna(scores[k]) else "N/A"
    tip=infos[k].replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    risk_cards.append(f'<div class="risk-card"><div class="risk-title">{labels[k]}<button class="info-icon" aria-label="{labels[k]} 설명" type="button"><span class="info-tip">{tip}</span></button></div><div class="risk-score">{score_txt} <span>/100</span></div><div class="risk-state"><span class="risk-dot {risk_class(scores[k])}"></span>{label(scores[k])}</div></div>')
st.markdown('<div class="risk-grid">'+''.join(risk_cards)+'</div>',unsafe_allow_html=True)

st.markdown('<div class="section"><h3>핵심 시장 상태</h3></div>',unsafe_allow_html=True)
fx=_read_fx().get("items",{})

def _fmt_fx(name,decimals=2):
    item=fx.get(name,{})
    v=item.get("value",np.nan); p=item.get("prev",np.nan)
    if pd.isna(v): return "갱신 중…","최신 데이터 확인 중","flat"
    delta=""; cls="flat"
    if pd.notna(p) and p!=0:
        ch=float(v-p); pct=ch/p*100
        if ch>0:
            cls="up"; delta=f"▲ {abs(ch):,.{decimals}f} (+{abs(pct):.2f}%)"
        elif ch<0:
            cls="down"; delta=f"▼ {abs(ch):,.{decimals}f} (-{abs(pct):.2f}%)"
        else:
            delta=f"— 0.{('0'*decimals)} (0.00%)"
    return f"{v:,.{decimals}f}",delta,cls

def _series_delta(s,unit="%",decimals=2):
    cur=latest(s); prevv=second(s)
    if pd.isna(cur): return "N/A","", "flat"
    value=f"{cur:,.{decimals}f}{unit}"
    if pd.isna(prevv): return value,"직전값 비교 불가","flat"
    ch=float(cur-prevv)
    if ch>0: return value,f"▲ {abs(ch):.{decimals}f}{unit}","up"
    if ch<0: return value,f"▼ {abs(ch):.{decimals}f}{unit}","down"
    return value,f"— {0:.{decimals}f}{unit}","flat"

def _cpi_yoy_display(s):
    yoy=s.pct_change(12)*100
    cur=latest(yoy); prevv=second(yoy)
    if pd.isna(cur): return "N/A","", "flat"
    value=f"{cur:.2f}%"
    if pd.isna(prevv): return value,"직전 발표 비교 불가","flat"
    ch=float(cur-prevv)
    if ch>0:return value,f"▲ {abs(ch):.2f}%p","up"
    if ch<0:return value,f"▼ {abs(ch):.2f}%p","down"
    return value,"— 0.00%p","flat"

market_info={
    "미국 기준금리":"미국의 실효 연방기금금리(EFFR)입니다. 연준의 통화정책과 단기 금융환경을 보여주는 대표 금리입니다.",
    "미국 2년물 국채수익률":"미국 2년 만기 국채의 시장 수익률입니다. 향후 기준금리 기대에 민감하게 반응합니다.",
    "미국 10년물 국채수익률":"미국 10년 만기 국채의 시장 수익률입니다. 장기금리와 금융환경을 판단하는 대표 지표입니다.",
    "미국 30년물 국채수익률":"미국 30년 만기 국채의 시장 수익률입니다. 장기 성장·물가 기대와 장기 자금조달 여건을 반영합니다.",
    "실업률":"미국 노동시장에서 실업자가 차지하는 비율입니다. 경기 둔화와 고용시장 변화를 판단하는 핵심 지표입니다.",
    "원/달러":"미국 달러 1달러당 원화 가격입니다. 원화 가치와 달러 강세 정도를 참고하기 위한 지표입니다.",
    "엔/달러":"미국 달러 1달러당 일본 엔화 가격입니다. 엔화 가치와 글로벌 달러 흐름을 참고하는 지표입니다.",
    "달러인덱스":"주요 통화 대비 미국 달러의 상대적 강도를 나타내는 달러인덱스(DXY)입니다.",
    "하이일드 스프레드":"미국 투기등급 회사채가 국채보다 추가로 요구하는 금리입니다. 커질수록 신용시장 스트레스가 높다는 의미입니다.",
    "CPI":"미국 소비자물가지수의 전년 대비 상승률입니다. 소비자가 체감하는 전반적인 물가 압력을 보여줍니다.",
    "WTI 유가":"서부텍사스산원유(WTI) 선물의 현재 가격입니다. 에너지 비용과 물가 압력, 경기 기대를 참고하는 시장 지표이며 종합위험지수 산식에는 포함하지 않습니다."
}

market_items=[]
for name,series,unit,dec in [
    ("미국 기준금리",fed,"%",2),
    ("미국 2년물 국채수익률",y2,"%",2),
    ("미국 10년물 국채수익률",y10,"%",2),
    ("미국 30년물 국채수익률",y30,"%",2),
    ("실업률",unemp,"%",1),
]:
    v,dlt,cls=_series_delta(series,unit,dec)
    market_items.append((name,v,dlt,cls))

for name in ("원/달러","엔/달러","달러인덱스"):
    v,dlt,cls=_fmt_fx(name,2)
    market_items.append((name,v,dlt,cls))

v,dlt,cls=_fmt_fx("WTI 유가",2)
if v not in ("갱신 중…","N/A"):
    v=f"${v}"
market_items.append(("WTI 유가",v,dlt,cls))

v,dlt,cls=_series_delta(hy,"%p",2)
market_items.append(("하이일드 스프레드",v,dlt,cls))
v,dlt,cls=_cpi_yoy_display(cpi)
market_items.append(("CPI",v,dlt,cls))

market_cards=[]
for n,v,dlt,cls in market_items:
    tip=market_info.get(n,"현재값과 직전값을 비교해 시장 상태를 참고하는 지표입니다.").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    market_cards.append(
        f'<div class="market-card"><div class="market-name">{n}'
        f'<button class="info-icon" aria-label="{n} 설명" type="button"><span class="info-tip">{tip}</span></button>'
        f'</div><div class="market-value">{v}</div><div class="market-delta delta-{cls}">{dlt}</div></div>'
    )
st.markdown('<div class="market-grid">'+''.join(market_cards)+'</div>',unsafe_allow_html=True)
st.caption("ⓘ 데스크톱에서는 마우스를 올리고, 모바일에서는 터치하면 지표 설명을 볼 수 있습니다. 환율·달러인덱스·WTI 유가는 참고자료이며 위험지수 산식에는 포함하지 않습니다.")

@st.cache_data(ttl=3600,show_spinner=False)
def historical_risk_fast(data,cape):
    months=pd.date_range(pd.Timestamp.now().normalize()-pd.DateOffset(months=12),pd.Timestamp.now().normalize(),freq="MS")
    rows=[]
    for dt in months:
        sub={k:v.loc[:dt].dropna() for k,v in data.items()}
        if len(sub.get("S&P500",pd.Series(dtype=float)))<220 or len(sub.get("VIX",pd.Series(dtype=float)))<30 or len(sub.get("10년물",pd.Series(dtype=float)))<30: continue
        sub_cape=cape.loc[:dt].dropna() if len(cape) else cape
        snap=compute_snapshot(sub,sub_cape,with_alerts=False)
        rows.append((dt,snap["overall"]))
    return pd.DataFrame(rows,columns=["date","risk"]).set_index("date") if rows else pd.DataFrame(columns=["risk"])

def render_history_chart(hist):
    # 기본 차트 대신 가벼운 SVG를 사용해 한국식 표기와 모바일 터치 종료 시 툴팁 숨김을 보장합니다.
    rows=[]
    for dt,val in hist["risk"].dropna().items():
        dt=pd.Timestamp(dt)
        rows.append({"date":f"{dt.year}년 {dt.month}월 {dt.day}일","year":int(dt.year),"month":int(dt.month),"risk":round(float(val),1)})
    payload=json.dumps(rows,ensure_ascii=False)
    chart_html='''<div id="riskChartWrap" style="width:100%;height:320px;position:relative;font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR','Segoe UI',sans-serif;touch-action:pan-y;">
<svg id="riskChart" width="100%" height="320" style="overflow:visible"></svg>
<div id="riskTip" style="display:none;position:absolute;pointer-events:none;background:#fff;border:1px solid #dfe2e7;border-radius:10px;padding:8px 10px;box-shadow:0 8px 24px rgba(0,0,0,.13);font-size:12px;line-height:1.55;color:#30343b;white-space:nowrap;z-index:5"></div></div>
<script>(()=>{
const data=__PAYLOAD__,svg=document.getElementById('riskChart'),wrap=document.getElementById('riskChartWrap'),tip=document.getElementById('riskTip');if(!data.length)return;
const NS='http://www.w3.org/2000/svg',W=Math.max(320,wrap.clientWidth),H=320,L=52,R=14,T=18,B=46,PW=W-L-R,PH=H-T-B;svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
const vals=data.map(d=>d.risk),rawMin=Math.min(...vals),rawMax=Math.max(...vals),ymin=Math.max(0,Math.floor((rawMin-5)/10)*10),ymax=Math.min(100,Math.ceil((rawMax+5)/10)*10||ymin+10);
const x=i=>L+(data.length===1?PW/2:i*PW/(data.length-1)),y=v=>T+(ymax-v)*PH/(ymax-ymin||1),el=(n,a={})=>{const q=document.createElementNS(NS,n);Object.entries(a).forEach(([k,v])=>q.setAttribute(k,v));return q};
for(let j=0;j<=4;j++){const v=ymin+(ymax-ymin)*j/4,yy=y(v);svg.appendChild(el('line',{x1:L,y1:yy,x2:W-R,y2:yy,stroke:'#eceef1','stroke-width':'1'}));const t=el('text',{x:L-10,y:yy+4,'text-anchor':'end',fill:'#7a8089','font-size':'12'});t.textContent=v.toFixed(1);svg.appendChild(t)}
const yt=el('text',{x:13,y:T+PH/2,'text-anchor':'middle',fill:'#7a8089','font-size':'11',transform:`rotate(-90 13 ${T+PH/2})`});yt.textContent='위험지수';svg.appendChild(yt);
const ticks=[],step=W<500?3:2;data.forEach((d,i)=>{if(i===0||i===data.length-1||d.month===1||i%step===0)ticks.push(i)});[...new Set(ticks)].forEach(i=>{const d=data[i],t=el('text',{x:x(i),y:H-14,'text-anchor':'middle',fill:'#7a8089','font-size':W<500?'11':'12'});t.textContent=(i===0)?`${String(d.year).slice(-2)}년 ${d.month}월`:(d.month===1?`${String(d.year).slice(-2)}년`:`${d.month}월`);svg.appendChild(t)});
svg.appendChild(el('polyline',{points:data.map((d,i)=>`${x(i)},${y(d.risk)}`).join(' '),fill:'none',stroke:'#5a67d8','stroke-width':'2.5','stroke-linejoin':'round','stroke-linecap':'round','vector-effect':'non-scaling-stroke'}));data.forEach((d,i)=>svg.appendChild(el('circle',{cx:x(i),cy:y(d.risk),r:'3.2',fill:'#fff',stroke:'#5a67d8','stroke-width':'2','vector-effect':'non-scaling-stroke'})));
const show=clientX=>{const rect=wrap.getBoundingClientRect(),px=Math.max(0,Math.min(rect.width,clientX-rect.left)),idx=Math.max(0,Math.min(data.length-1,Math.round(px/rect.width*(data.length-1)))),d=data[idx];tip.innerHTML=`<b>날짜</b> ${d.date}<br><b>위험지수</b> ${d.risk.toFixed(1)}`;tip.style.display='block';requestAnimationFrame(()=>{let left=px+12;if(left+tip.offsetWidth>rect.width)left=px-tip.offsetWidth-12;tip.style.left=Math.max(4,left)+'px';tip.style.top=Math.max(6,(y(d.risk)/H*rect.height)-tip.offsetHeight-10)+'px'})},hide=()=>tip.style.display='none';
wrap.addEventListener('mousemove',e=>show(e.clientX));wrap.addEventListener('mouseleave',hide);wrap.addEventListener('touchstart',e=>{if(e.touches[0])show(e.touches[0].clientX)},{passive:true});wrap.addEventListener('touchmove',e=>{if(e.touches[0])show(e.touches[0].clientX)},{passive:true});wrap.addEventListener('touchend',hide,{passive:true});wrap.addEventListener('touchcancel',hide,{passive:true});document.addEventListener('touchstart',e=>{if(!wrap.contains(e.target))hide()},{passive:true});
})();</script>'''
    chart_html=chart_html.replace("__PAYLOAD__",payload)
    components.html(chart_html,height=330,scrolling=False)

st.markdown('<div class="section"><h3>종합위험지수 추이</h3></div>',unsafe_allow_html=True)
if "show_history" not in st.session_state: st.session_state.show_history=False
if st.button("최근 1년 추이 불러오기",type="secondary"):
    st.session_state.show_history=True
if st.session_state.show_history:
    with st.spinner("추이 계산 중…"): hist=historical_risk_fast(data,cape)
    if len(hist):
        render_history_chart(hist)
        st.caption("최근 1년 월별 스냅샷 · 최초 계산 후 서버 공용 캐시를 최대 1시간 재사용")
    else: st.warning("과거 위험지수를 계산할 데이터가 부족합니다.")
else: st.caption("초기 로딩 속도를 위해 과거 추이 계산은 필요할 때만 실행합니다.")

st.markdown('<div class="section"><h3>경기침체 신호</h3></div>',unsafe_allow_html=True)
_claims_confirm=bool(details.get("economy",{}).get("claims_confirm",False))
if pd.notna(sahm_now) and sahm_now>=.5 and _claims_confirm: _recession_status="확인"
elif pd.notna(sahm_now) and sahm_now>=.5: _recession_status="관찰"
else: _recession_status="정상"
# 명확한 3개 카드 구성
_sahm_text=f"{sahm_now:.2f}%p" if pd.notna(sahm_now) else "N/A"
_recession_html=(f'<div class="recession-grid">'
                 f'<div class="recession-card"><div class="recession-name">실업률</div><div class="recession-value">{latest(unemp):.1f}%</div></div>'
                 f'<div class="recession-card"><div class="recession-name">Sahm Rule</div><div class="recession-value">{_sahm_text}</div></div>'
                 f'<div class="recession-card"><div class="recession-name">침체 신호</div><div class="recession-value">{_recession_status}</div></div>'
                 '</div>')
st.markdown(_recession_html,unsafe_allow_html=True)

with st.expander("세부 데이터 및 계산 기준"):
    st.write("종합위험지수: 시장·밸류에이션 25% + 금리 25% + 신용 15% + 경기 17% + 변동성 10% + 물가 8%.")
    st.write("시장·밸류에이션: 200일선 과열 45% + CAPE 35% + 최근 20거래일 상승 모멘텀 20%. 폭락 자체는 추가 위험으로 가산하지 않습니다.")
    st.write("변동성: 현재 VIX 절대수준 55% + 최근 5거래일 급등 45%.")
    st.write("금리: 10년물 수준 35% + 최근 20거래일 상승속도 25% + 10Y-2Y 15% + 10Y-EFFR 15% + 10년물 기간프리미엄 10%.")
    st.write("신용: HY OAS 45% + BBB OAS 20% + 최근 5거래일 확대 15% + 최근 20거래일 확대 20%.")
    st.write("경기: 실업률 30% + Sahm Rule 35% + 신규 실업수당 35%. Sahm 단독 신호는 신규 실업수당의 최근 8주 상승 추세가 확인되지 않으면 강도를 제한합니다.")
    st.write("물가: CPI 25% + 근원 CPI 35% + 근원 PCE 40%. 각 지표에서 전년동월비와 최근 3개월 연율화를 함께 반영합니다.")
    st.write("구조적 위험 신호와 시장 급변 신호는 종합위험점수에 단순 가산하지 않고 별도 레이어로 표시합니다.")
    st.write("CAPE는 Shiller PE 월별 공개 표를 보조 데이터로 사용하며, 수집 실패 시 해당 세부 비중은 자동으로 제외·재정규화합니다.")
    st.write("현재 2·10·30년물은 가능한 경우 미 재무부 공식 일일 수익률곡선의 더 최신 값을 우선 반영하며 기준금리는 일간 EFFR을 사용합니다.")
    st.write("참고지표: 원/달러, 엔/달러, 달러인덱스, WTI 유가는 표시 전용이며 종합위험지수에는 포함하지 않습니다.")

st.caption(f"Risk Monitor 3.35.0 Readability Balance · 화면 갱신 {datetime.now(ZoneInfo("Asia/Seoul")).strftime('%Y-%m-%d %H:%M:%S KST')} · 캐시 즉시 표시 · 백그라운드 최신화")
