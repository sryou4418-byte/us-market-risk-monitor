import streamlit as st
import pandas as pd
import numpy as np
import requests, csv, os, threading, shutil, json, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path as _Path
from urllib.parse import quote

st.set_page_config(page_title="미국 증시 종합 위험지수", page_icon="🇺🇸", layout="wide")
st.markdown("""<style>
.block-container{max-width:1180px;padding-top:2rem;padding-bottom:4rem}
.hero{border:1px solid #e5e7eb;border-radius:28px;padding:30px 32px;margin:12px 0 22px;background:rgba(255,255,255,.72)}
.hero-score{font-size:64px;line-height:1;font-weight:850;letter-spacing:-.06em;color:#30323a}
.score-row{display:flex;align-items:baseline;gap:14px;margin-top:6px;flex-wrap:wrap}
.score-unit{font-size:20px;font-weight:650;letter-spacing:-.02em;color:#30323a}
.risk-guide{font-size:13px;font-weight:600;color:#6b7280;background:#f3f4f6;border-radius:999px;padding:7px 11px;white-space:nowrap}
.risk-label{font-size:18px;font-weight:750;margin-top:8px;color:#20232b}
.delta-up{color:#e5484d}.delta-down{color:#2878d7}.delta-flat{color:#8b8f98}
.small{font-size:13px;color:#6b7280}.section{margin-top:30px;margin-bottom:10px}
div[data-testid="stMetric"]{border:1px solid #e5e7eb;border-radius:18px;padding:14px}
.data-status{font-size:12px;color:#6b7280;display:flex;align-items:center;gap:7px;margin:-2px 0 8px}.data-status span{width:7px;height:7px;border-radius:50%;background:#a1a1aa;animation:pulse 1.1s ease-in-out infinite}.data-status.done span{background:#22a06b;animation:none}
.loading-shell{border:1px solid #eceef1;border-radius:28px;padding:30px 32px;margin:20px 0;background:#fff}.loading-title,.loading-score,.loading-row span{background:linear-gradient(90deg,#f1f2f4 25%,#fafafa 50%,#f1f2f4 75%);background-size:200% 100%;animation:shimmer 1.2s infinite;border-radius:10px}.loading-title{height:18px;width:180px}.loading-score{height:58px;width:240px;margin-top:20px}.loading-row{display:flex;gap:12px;margin-top:24px}.loading-row span{display:block;height:70px;flex:1}.loading-text{font-size:13px;color:#8b8f98;margin-top:16px}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
</style>""", unsafe_allow_html=True)

FRED_CSV="https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
FRED_RECENT="https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd={}"
SERIES={
    "기준금리":"EFFR","2년물":"DGS2","10년물":"DGS10","30년물":"DGS30",
    "하이일드스프레드":"BAMLH0A0HYM2","BBB스프레드":"BAMLC0A4CBBB",
    "CPI":"CPIAUCSL","근원CPI":"CPILFESL","근원PCE":"PCEPILFE",
    "실업률":"UNRATE","신규실업수당":"ICSA","S&P500":"SP500","VIX":"VIXCLS"
}
WEIGHTS={"시장추세":.25,"변동성":.15,"금리":.20,"신용":.15,"경기":.20,"물가":.05}

ROOT_CACHE=_Path(os.environ.get("LOCALAPPDATA", str(_Path.home()))) / "RiskMonitor"
CACHE_DIR=ROOT_CACHE / "data"
CACHE_DIR.mkdir(parents=True,exist_ok=True)
RECENT_DAYS=90
REFRESH_STATUS=ROOT_CACHE / "refresh_status.json"
FX_CACHE=ROOT_CACHE / "fx_snapshot.json"


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
    tickers={"원/달러":"USDKRW=X","엔/달러":"USDJPY=X","달러인덱스":"DX-Y.NYB"}
    snap={"updated":time.time(),"source":"Yahoo Finance","items":{}}
    errors=[]
    with ThreadPoolExecutor(max_workers=3) as ex:
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


def _write_refresh_status(ok,errors):
    ROOT_CACHE.mkdir(parents=True,exist_ok=True)
    payload={"finished":time.time(),"ok":bool(ok),"errors":errors[:10]}
    tmp=REFRESH_STATUS.with_suffix(".tmp"); tmp.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8"); tmp.replace(REFRESH_STATUS)


def _refresh_all_background():
    errors=[]
    priority=[("기준금리","EFFR"),("2년물","DGS2"),("10년물","DGS10"),("30년물","DGS30")]
    with ThreadPoolExecutor(max_workers=5) as ex:
        fs=[ex.submit(_refresh_series,*x) for x in priority]
        fx_future=ex.submit(_refresh_fx)
        for f in fs:
            _,_,err=f.result()
            if err: errors.append(err)
        try: errors.extend(fx_future.result())
        except Exception as e: errors.append(f"환율: {e}")
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
            info=json.loads(REFRESH_STATUS.read_text(encoding="utf-8")); ts=datetime.fromtimestamp(info.get("finished",time.time())).strftime("%H:%M")
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
    cutoff=pd.Timestamp.now().normalize()-pd.DateOffset(years=lookback_years); s=s.loc[s.index>=cutoff]
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
    # 시장 붕괴가 아니라 '과열'을 측정한다. 200일선 아래에서는 과열 위험이 낮아지고,
    # +5% 이후부터 점진적으로, +10% 이후에는 더 빠르게 상승한다.
    return interp_score(dev,[-15,-5,0,5,10,15,20],[0,5,15,40,70,90,100])


def market_overheat_score(sp):
    if len(sp)<220:return np.nan,np.nan
    ma=sp.rolling(200).mean(); dev=(latest(sp)/latest(ma)-1)*100
    return market_overheat_from_dev(dev),dev


def vix_surge_score(vix):
    z=vix.dropna()
    if len(z)<6 or z.iloc[-6]<=0:return np.nan
    chg=(z.iloc[-1]/z.iloc[-6]-1)*100
    return interp_score(chg,[-20,0,10,25,50,80],[0,5,25,55,85,100])


def volatility_score(vix):
    return weighted_custom({"level":percentile_score(vix,latest(vix),True),"surge":vix_surge_score(vix)},{"level":.75,"surge":.25})


def sahm_series(u):
    m=u.resample("MS").mean(); ma3=m.rolling(3).mean(); low=ma3.rolling(12,min_periods=12).min(); return (ma3-low).dropna()

def sahm_score(u):
    s=sahm_series(u); return clamp(latest(s)*100) if len(s) else np.nan


def spread_change_score(s,obs=20):
    z=s.dropna()
    if len(z)<=obs:return np.nan
    delta=float(z.iloc[-1]-z.iloc[-1-obs])
    return interp_score(delta,[-1,0,.25,.5,1,2],[0,5,25,45,70,100])


def credit_score(hy,bbb):
    # FRED의 ICE OAS 장기 히스토리가 3년으로 제한되어 단순 백분위 대신 절대 스트레스 구간을 중심으로 평가.
    hy_abs=interp_score(latest(hy),[1.5,2.5,3.5,5,7,10,15],[5,12,25,50,70,90,100])
    bbb_abs=interp_score(latest(bbb),[.4,.8,1.0,1.5,2.5,4,6],[5,12,20,40,65,85,100]) if len(bbb.dropna()) else np.nan
    widening=weighted_custom({"hy":spread_change_score(hy),"bbb":spread_change_score(bbb)},{"hy":.7,"bbb":.3})
    return weighted_custom({"hy":hy_abs,"bbb":bbb_abs,"widening":widening},{"hy":.55,"bbb":.25,"widening":.20})


def claims_score(icsa):
    z=icsa.dropna()
    if len(z)<60:return np.nan
    ma4=z.rolling(4).mean().dropna()
    if len(ma4)<53:return np.nan
    yoy=(ma4.iloc[-1]/ma4.iloc[-53]-1)*100
    return interp_score(yoy,[-20,0,10,20,40,60],[5,12,30,50,75,100])


def economy_score(unemp,icsa):
    return weighted_custom({"unemp":percentile_score(unemp,latest(unemp),True),"sahm":sahm_score(unemp),"claims":claims_score(icsa)},
                           {"unemp":.40,"sahm":.40,"claims":.20})


def inflation_score(cpi,core_cpi,core_pce):
    items={"headline":percentile_score(cpi.pct_change(12),latest(cpi.pct_change(12)),True)}
    if len(core_cpi.dropna()): items["core_cpi"]=percentile_score(core_cpi.pct_change(12),latest(core_cpi.pct_change(12)),True)
    if len(core_pce.dropna()): items["core_pce"]=percentile_score(core_pce.pct_change(12),latest(core_pce.pct_change(12)),True)
    return weighted_custom(items,{"headline":.40,"core_cpi":.35,"core_pce":.25})


def label(x):
    if pd.isna(x):return "데이터 부족"
    if x<=20:return "매우 낮음"
    if x<=40:return "낮음"
    if x<=60:return "보통"
    if x<=80:return "높음"
    return "매우 높음"


def delta_value(a,b):
    if pd.isna(a) or pd.isna(b): return None,"비교 불가","flat"
    d=float(a-b)
    if d>0:return d,f"▲ {abs(d):.1f}","up"
    if d<0:return d,f"▼ {abs(d):.1f}","down"
    return d,"— 0.0","flat"


fed,y2,y10,y30=data["기준금리"],data["2년물"],data["10년물"],data["30년물"]
hy,bbb=data["하이일드스프레드"],data["BBB스프레드"]
cpi,core_cpi,core_pce=data["CPI"],data["근원CPI"],data["근원PCE"]
unemp,icsa,sp,vix=data["실업률"],data["신규실업수당"],data["S&P500"],data["VIX"]
spread210=y10-y2; spread10fed=y10-fed
market,dev=market_overheat_score(sp); sahm=sahm_series(unemp); sahm_now=latest(sahm)

scores={
 "시장추세":market,
 "변동성":volatility_score(vix),
 "금리":weighted_custom({
   "curve":percentile_score(spread210,latest(spread210),False),
   "policy":percentile_score(spread10fed,latest(spread10fed),True),
   "level":percentile_score(y10,latest(y10),True)}, {"curve":.40,"policy":.35,"level":.25}),
 "신용":credit_score(hy,bbb),
 "경기":economy_score(unemp,icsa),
 "물가":inflation_score(cpi,core_cpi,core_pce)
}
overall=weighted(scores)

# 비교용 직전 관측값 기반 점수. 발표주기가 다른 지표는 각자 직전 관측값을 사용한다.
zsp=sp.dropna(); prev_market=market_overheat_score(zsp.iloc[:-1])[0] if len(zsp)>220 else np.nan
zv=vix.dropna(); prev_vol=volatility_score(zv.iloc[:-1]) if len(zv)>30 else np.nan
prev_rate=weighted_custom({
    "curve":percentile_score(spread210,second(spread210),False),
    "policy":percentile_score(spread10fed,second(spread10fed),True),
    "level":percentile_score(y10,second(y10),True)}, {"curve":.40,"policy":.35,"level":.25})
prev_credit=credit_score(hy.dropna().iloc[:-1],bbb.dropna().iloc[:-1]) if len(hy.dropna())>21 else np.nan
prev_econ=economy_score(unemp.dropna().iloc[:-1],icsa.dropna().iloc[:-1]) if len(unemp.dropna())>15 else np.nan
prev_infl=inflation_score(cpi.dropna().iloc[:-1],core_cpi.dropna().iloc[:-1],core_pce.dropna().iloc[:-1]) if len(cpi.dropna())>30 else np.nan
prev={"시장추세":prev_market,"변동성":prev_vol,"금리":prev_rate,"신용":prev_credit,"경기":prev_econ,"물가":prev_infl}
prev_overall=weighted(prev)

st.title("미국 증시 종합 위험지수")
st.caption("시장·금리·신용·경기·물가를 현재 공개 데이터 기준으로 자동 분석")
refresh_indicator(); _,delta_text,delta_class=delta_value(overall,prev_overall)

st.markdown(f"""<div class="hero"><div class="small">위험지수</div><div class="score-row">
<div class="hero-score">{overall:.1f}<span class="score-unit"> /100</span></div><div class="risk-guide">100에 가까울수록 위험</div>
</div><div class="risk-label">{label(overall)}</div></div>""",unsafe_allow_html=True)
cc1,cc2=st.columns([1,2])
with cc1: st.markdown(f"**전일 비교** <span class='delta-{delta_class}'>{delta_text}</span>",unsafe_allow_html=True)
with cc2: st.caption("▲ 위험 증가 · ▼ 위험 감소")

comments=[]
if pd.notna(dev):
    if dev>=15: comments.append("S&P500이 200일 이동평균을 크게 웃돌아 시장 과열 부담이 매우 높습니다.")
    elif dev>=10: comments.append("S&P500이 200일 이동평균을 크게 웃돌아 과열 부담이 높아지고 있습니다.")
    elif dev<=0: comments.append("S&P500의 200일선 기준 과열 부담은 낮은 상태입니다.")
if pd.notna(latest(vix)) and latest(vix)>=25: comments.append("VIX가 높은 수준으로 올라 시장 변동성 부담이 커졌습니다.")
if pd.notna(sahm_now):
    if sahm_now>=.5: comments.append("Sahm Rule 기준으로 경기침체 경보 수준에 도달했습니다.")
    elif sahm_now>=.3: comments.append("실업률 상승폭이 커지면서 고용시장 위험 신호가 나타나고 있습니다.")
if pd.notna(latest(hy)) and latest(hy)>=5: comments.append("하이일드 신용스프레드가 확대돼 신용시장 위험에 주의가 필요합니다.")
if not comments: comments.append("현재 주요 지표에서는 뚜렷한 극단적 위험 신호가 나타나지 않고 있습니다.")
st.info("**현재 시장 해석**\n\n"+" ".join(comments))

st.markdown('<div class="section"><h3>구성요소 위험도</h3></div>',unsafe_allow_html=True)
labels={"시장추세":"시장 위험","변동성":"변동성 위험","금리":"금리 위험","신용":"신용시장 위험","경기":"경기 위험","물가":"물가 위험"}
infos={
    "시장추세":"시장 붕괴 여부가 아니라 S&P500의 과열 정도를 봅니다. 200일 이동평균 대비 이격도가 커질수록 과열 위험을 높게 평가합니다. 200일선 아래에서는 과열 위험이 낮아집니다.",
    "변동성":"VIX의 장기 상대 수준과 최근 5거래일 급등 정도를 함께 반영합니다. VIX가 높거나 짧은 기간에 급등하면 위험도가 올라갑니다.",
    "금리":"기존 방식 그대로 10년물-2년물 금리차, 10년물-EFFR 차이, 10년물 국채수익률을 40%·35%·25%로 반영합니다.",
    "신용":"하이일드 OAS와 BBB OAS의 절대 수준, 최근 약 20거래일 스프레드 확대 속도를 반영합니다. FRED의 ICE OAS 장기자료 제한 때문에 단순 3년 백분위만 사용하지 않습니다.",
    "경기":"실업률의 장기 상대 수준, Sahm Rule, 신규 실업수당 청구건수 4주 평균의 전년 대비 변화를 함께 반영합니다.",
    "물가":"헤드라인 CPI, 근원 CPI, 근원 PCE의 전년 대비 상승률을 각각 장기 상대 수준으로 환산해 종합합니다."
}
cols=st.columns(3)
for i,k in enumerate(scores):
    with cols[i%3]:
        tcol,icol=st.columns([6,1],vertical_alignment="center")
        with tcol: st.markdown(f"**{labels[k]}**")
        with icol:
            with st.popover("ⓘ",help=f"{labels[k]} 계산 설명"):
                st.markdown(f"**{labels[k]}는 무엇을 반영하나?**")
                st.write(infos[k])
        st.markdown(f"<div style='font-size:26px;font-weight:800;line-height:1.15'>{scores[k]:.1f} <span style='font-size:14px;font-weight:600;color:#6b7280'>/100</span></div>",unsafe_allow_html=True)
        st.caption(label(scores[k]))
st.caption("모든 위험점수는 0~100이며, 100에 가까울수록 위험합니다. 각 카테고리 내부에 여러 세부지표를 사용하더라도 최종 종합지수에서는 카테고리 가중치만 적용합니다.")

st.markdown('<div class="section"><h3>핵심 시장 상태</h3></div>',unsafe_allow_html=True)
a,b,c,d=st.columns(4)
a.metric("S&P 500",f"{latest(sp):,.2f}",f"{dev:+.1f}% vs 200일선" if pd.notna(dev) else None)
b.metric("VIX",f"{latest(vix):.2f}",label(scores["변동성"]))
c.metric("10년물 국채수익률",f"{latest(y10):.2f}%",f"10Y-EFFR {latest(spread10fed):+.2f}%p")
d.metric("하이일드 스프레드",f"{latest(hy):.2f}%p",label(scores["신용"]))

fx=_read_fx().get("items",{})
e,f,g=st.columns(3)
def fx_metric(col,name,decimals=2):
    item=fx.get(name,{})
    v=item.get("value",np.nan); p=item.get("prev",np.nan)
    if pd.isna(v): col.metric(name,"갱신 중…"); return
    delta=None
    if pd.notna(p) and p!=0:
        ch=float(v-p); pct=ch/p*100; delta=f"{ch:+,.{decimals}f} ({pct:+.2f}%)"
    col.metric(name,f"{v:,.{decimals}f}",delta)
fx_metric(e,"원/달러",2); fx_metric(f,"엔/달러",2); fx_metric(g,"달러인덱스",2)
st.caption("환율·달러인덱스는 참고용이며 위험지수 산식에는 포함하지 않습니다. 무료·API키 없는 Yahoo Finance 시장 데이터를 백그라운드에서 갱신합니다.")

@st.cache_data(ttl=3600,show_spinner=False)
def historical_risk_fast(data):
    months=pd.date_range(pd.Timestamp.now().normalize()-pd.DateOffset(months=12),pd.Timestamp.now().normalize(),freq="MS")
    rows=[]
    for dt in months:
        sub={k:v.loc[:dt].dropna() for k,v in data.items()}
        if len(sub["S&P500"])<220 or len(sub["VIX"])<30 or len(sub["10년물"])<30: continue
        mm,_=market_overheat_score(sub["S&P500"]); vv=volatility_score(sub["VIX"])
        s210=(sub["10년물"]-sub["2년물"]).dropna(); sf=(sub["10년물"]-sub["기준금리"]).dropna()
        rr=weighted_custom({"curve":percentile_score(s210,latest(s210),False),"policy":percentile_score(sf,latest(sf),True),"level":percentile_score(sub["10년물"],latest(sub["10년물"]),True)}, {"curve":.40,"policy":.35,"level":.25})
        cr=credit_score(sub["하이일드스프레드"],sub["BBB스프레드"])
        ec=economy_score(sub["실업률"],sub["신규실업수당"])
        inf=inflation_score(sub["CPI"],sub["근원CPI"],sub["근원PCE"])
        rows.append((dt,weighted({"시장추세":mm,"변동성":vv,"금리":rr,"신용":cr,"경기":ec,"물가":inf})))
    return pd.DataFrame(rows,columns=["date","risk"]).set_index("date") if rows else pd.DataFrame(columns=["risk"])

st.markdown('<div class="section"><h3>종합위험지수 추이</h3></div>',unsafe_allow_html=True)
if st.button("최근 1년 추이 불러오기",type="secondary"):
    with st.spinner("추이 계산 중…"): hist=historical_risk_fast(data)
    if len(hist): st.line_chart(hist,height=320); st.caption("최근 1년 월별 스냅샷 · 버튼을 눌렀을 때만 계산")
    else: st.warning("과거 위험지수를 계산할 데이터가 부족합니다.")
else: st.caption("초기 로딩 속도를 위해 과거 추이 계산은 필요할 때만 실행합니다.")

st.markdown('<div class="section"><h3>경기침체 신호</h3></div>',unsafe_allow_html=True)
a,b,c=st.columns(3)
a.metric("실업률",f"{latest(unemp):.1f}%")
b.metric("Sahm Rule",f"{sahm_now:.2f}%p" if pd.notna(sahm_now) else "N/A")
c.metric("침체 경보","발생" if pd.notna(sahm_now) and sahm_now>=.5 else "정상")

with st.expander("세부 데이터 및 계산 기준"):
    st.write("시장: S&P500의 200일 이동평균 대비 이격도를 이용한 과열 위험. 하락 스트레스는 이 점수에 직접 포함하지 않습니다.")
    st.write("변동성: VIX 장기 상대수준 75% + 최근 5거래일 급등 25%.")
    st.write("금리: 10Y-2Y 40% + 10Y-EFFR 35% + 10년물 국채수익률 25%. 기존 구조 유지.")
    st.write("신용: HY OAS 절대수준 55% + BBB OAS 절대수준 25% + 최근 스프레드 확대속도 20%.")
    st.write("경기: 실업률 40% + Sahm Rule 40% + 신규 실업수당 청구건수 20%.")
    st.write("물가: CPI 40% + 근원 CPI 35% + 근원 PCE 25%.")
    st.write("현재 2·10·30년물은 가능한 경우 미 재무부 공식 일일 수익률곡선의 더 최신 값을 우선 반영하며 기준금리는 일간 EFFR을 사용합니다.")
    st.write("환율: 원/달러, 엔/달러, 달러인덱스는 참고표시 전용이며 종합위험지수에는 포함하지 않습니다.")

st.caption(f"Risk Monitor 3.26.0 Web Test · 화면 갱신 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} · 캐시 즉시 표시 · 백그라운드 최신화")
