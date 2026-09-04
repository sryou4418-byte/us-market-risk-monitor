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

st.set_page_config(page_title="미국 증시 위험 모니터", page_icon="🇺🇸", layout="wide")

# v3.38.8 UI state must be initialized before any theme/navigation rendering.
_qp = st.query_params
_view = str(_qp.get("view", "dashboard"))
_theme = str(_qp.get("theme", "light"))
if _view not in ("dashboard", "heatmap"):
    _view = "dashboard"
if _theme not in ("light", "dark"):
    _theme = "light"

st.markdown("""<style>
:root{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Apple SD Gothic Neo","Noto Sans KR","Segoe UI",sans-serif}
html,body,[class*="css"],.stApp,.stMarkdown,.stCaption,button,input,textarea,select{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","SF Pro Text","Apple SD Gothic Neo","Noto Sans KR","Segoe UI",sans-serif!important}
.block-container{max-width:1180px;padding-top:2.2rem;padding-bottom:4rem}
.dev-credit{font-size:12px;color:#8b8f98;font-weight:600;letter-spacing:-.01em;margin-top:-.35rem;margin-bottom:.35rem}
.app-title-row{display:flex;align-items:center;margin-top:2px;margin-bottom:2px;padding:7px 0 4px;overflow:visible}.app-title-text{font-size:2.35rem;line-height:1.24;font-weight:850;letter-spacing:-.055em;color:#20232b;margin:0;overflow:visible}.overview-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:12px 0 8px}.overview-card{border:1px solid #e3e6eb;border-radius:22px;padding:18px 20px;background:rgba(255,255,255,.80);min-height:154px;box-sizing:border-box}.overview-head{display:flex;align-items:center;gap:9px;font-size:14px;font-weight:800;color:#555b65;margin-bottom:14px}.overview-head-icon{width:28px;height:28px;border:1px solid #e4e7eb;border-radius:9px;display:inline-flex;align-items:center;justify-content:center;background:#fff;flex:0 0 28px}.overview-head-icon svg{width:17px;height:17px}.overview-main{display:flex;align-items:baseline;gap:6px;min-height:52px}.overview-score{font-size:44px;line-height:1.04;font-weight:840;letter-spacing:-.045em;color:#2b2f37}.overview-unit{font-size:15px;font-weight:700;color:#444a54}.overview-status{display:flex;align-items:center;gap:9px;font-size:42px;font-weight:820;letter-spacing:-.04em;color:#282c34;min-height:52px;line-height:1.04}.overview-status .signal-status-dot{width:11px;height:11px;flex-basis:11px}.overview-sub{font-size:12px;color:#737983;margin-top:9px;line-height:1.45;min-height:18px}.overview-delta{font-size:11.5px;color:#717781;border-top:1px solid #eceef1;margin-top:12px;padding-top:9px}.overview-count{display:inline-flex;align-items:center;align-self:center;padding:2px 6px;border-radius:999px;background:#f2f3f5;color:#656b74;font-size:10px;line-height:1.3;font-weight:750;margin-left:4px;white-space:nowrap;letter-spacing:-.01em}
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
.market-card{border:1px solid #e5e7eb;border-radius:18px;padding:15px 16px;background:rgba(255,255,255,.82);min-height:118px;overflow:hidden}.market-card-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}.spark-wrap{height:34px;margin-top:10px;opacity:.88}.spark-wrap svg{display:block;width:100%;height:34px}.spark-line{fill:none;stroke:#8b93a1;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.spark-base{stroke:#eef0f3;stroke-width:1}.overview-horizon{font-size:10.5px;font-weight:700;color:#8b8f98;margin-top:2px}.overview-signal-line{display:flex;align-items:center;gap:6px;font-size:11px;color:#6f7580;margin-top:8px}.overview-signal-line .signal-status-dot{width:8px;height:8px;flex-basis:8px}
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
  .market-card{min-height:108px;padding:12px 12px}.spark-wrap{height:28px;margin-top:8px}.spark-wrap svg{height:28px}.market-name{font-size:12px;margin-bottom:7px}.market-value{font-size:19px}.market-delta{font-size:11px;white-space:normal}
  div[data-testid="stMetric"]{padding:12px}
  .recession-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:7px}.recession-card{min-height:64px;padding:9px 8px;border-radius:14px}.recession-name{font-size:10.5px;margin-bottom:5px}.recession-value{font-size:16px}
  .signal-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:10px}.signal-card{min-height:92px;padding:13px 11px;border-radius:15px}.signal-name{font-size:10.5px;margin-bottom:8px}.signal-status{gap:6px;min-height:22px}.signal-status-dot{width:9px;height:9px;flex-basis:9px}.signal-value{font-size:18px}.signal-count{font-size:9.5px;min-height:18px;padding:1px 6px}.signal-detail{font-size:10.5px;margin-top:7px;line-height:1.4}
  .app-title-row{padding:6px 0 3px}.app-title-text{font-size:1.82rem;line-height:1.24}.overview-grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:10px 0 7px}.overview-card{min-height:130px;padding:12px 9px;border-radius:15px}.overview-head{gap:5px;font-size:10.5px;margin-bottom:10px;line-height:1.25}.overview-head-icon{width:20px;height:20px;border-radius:7px;flex-basis:20px}.overview-head-icon svg{width:12px;height:12px}.overview-main{min-height:38px}.overview-score{font-size:30px;line-height:1.04}.overview-unit{font-size:10.5px}.overview-status{gap:5px;font-size:29px;font-weight:820;min-height:38px;line-height:1.04}.overview-status .signal-status-dot{width:8px;height:8px;flex-basis:8px}.overview-sub{font-size:9.5px;margin-top:6px;line-height:1.35;min-height:25px}.overview-delta{font-size:9.5px;margin-top:7px;padding-top:6px}.overview-count{font-size:8px;padding:1px 5px;margin-left:1px}
}

.r38-dark .stApp{background:#0f141c!important;color:#eef2f7!important}
.r38-dark .r38-panel,.r38-dark .r38-hero-card,.r38-dark .r38-action,.r38-dark .r38-market-table{background:#171e28!important;border-color:#2a3442!important;color:#edf2f7!important}
.r38-dark .r38-section-title,.r38-dark .r38-card-title,.r38-dark .r38-signal-main,.r38-dark .r38-risk-score,.r38-dark .r38-metric-value,.r38-dark .r38-recession-value{color:#f3f6fa!important}
.r38-dark .r38-subtitle,.r38-dark .r38-credit,.r38-dark .r38-horizon,.r38-dark .r38-risk-name,.r38-dark .r38-metric-name,.r38-dark .r38-note,.r38-dark .r38-risk-foot,.r38-dark .r38-side-copy{color:#aeb8c5!important}
.r38-dark .r38-col-head,.r38-dark .r38-recession-card{background:#121923!important;border-color:#2a3442!important;color:#dce4ee!important}
.r38-dark .r38-metric,.r38-dark .r38-market-col{border-color:#27313e!important}
.r38-dark .r38-interpret{background:#10263a!important;border-color:#204566!important;color:#cde7fb!important}
.r38-dark .r38-interpret-label{color:#79c1ff!important}
.r38-dark .r38-callout{background:#2a171a!important;border-color:#553036!important;color:#f2cdd1!important}
.r38-dark .r38-callout.warn{background:#2a2114!important;border-color:#554523!important;color:#f1dfb3!important}
.r38-dark [data-testid="stExpander"]{background:#171e28!important;border-color:#2a3442!important}

</style>""", unsafe_allow_html=True)

components.html(f"""<script>
(() => {{
  const dark = {str(_theme=="dark").lower()};
  const doc = window.parent.document;
  [doc.body, doc.querySelector('.stApp')].forEach(el => {{
    if (el) el.classList.toggle('r38-dark', dark);
  }});
}})();
</script>""", height=0)


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

# v3.38 데이터 공급자 추상화: 산식/UI는 공급자 심볼 대신 내부 표준 키를 사용한다.
# 완성본에서 실시간 API로 교체할 때 이 매핑/어댑터만 바꾸면 된다.
CANONICAL_DATA={
    "EFFR":{"internal":"기준금리","provider":"FRED","symbol":"EFFR"},
    "US2Y":{"internal":"2년물","provider":"FRED+TREASURY","symbol":"DGS2"},
    "US10Y":{"internal":"10년물","provider":"FRED+TREASURY","symbol":"DGS10"},
    "US30Y":{"internal":"30년물","provider":"FRED+TREASURY","symbol":"DGS30"},
    "SP500":{"internal":"S&P500","provider":"FRED","symbol":"SP500"},
    "VIX":{"internal":"VIX","provider":"FRED","symbol":"VIXCLS"},
    "HY_OAS":{"internal":"하이일드스프레드","provider":"FRED","symbol":"BAMLH0A0HYM2"},
    "UNEMP":{"internal":"실업률","provider":"FRED","symbol":"UNRATE"},
    "CPI":{"internal":"CPI","provider":"FRED","symbol":"CPIAUCSL"},
}

def canonical_series(data,key):
    meta=CANONICAL_DATA.get(key,{})
    return data.get(meta.get("internal",""),pd.Series(dtype=float))

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
    attempts=[
        ("query1.finance.yahoo.com","5d","1m"),
        ("query2.finance.yahoo.com","5d","5m"),
        ("query1.finance.yahoo.com","1mo","15m"),
        ("query2.finance.yahoo.com","1mo","1d"),
    ]
    last_error=None
    for host,rng,interval in attempts:
        try:
            url=f"https://{host}/v8/finance/chart/{enc}?range={rng}&interval={interval}&includePrePost=false"
            r=requests.get(url,headers=headers,timeout=(3,6)); r.raise_for_status()
            result=r.json().get("chart",{}).get("result") or []
            if not result: raise ValueError(f"{ticker}: Yahoo 데이터 없음")
            row=result[0]; meta=row.get("meta",{})
            closes=[float(x) for x in (row.get("indicators",{}).get("quote",[{}])[0].get("close") or []) if x is not None]
            cur=meta.get("regularMarketPrice")
            if cur is None and closes: cur=closes[-1]
            prev=meta.get("chartPreviousClose",meta.get("previousClose"))
            if prev is None and len(closes)>=2: prev=closes[-2]
            if cur is None: raise ValueError(f"{ticker}: 현재값 없음")
            return {"value":float(cur),"prev":float(prev) if prev is not None else np.nan,"time":time.time(),"spark":closes[-60:],"stale":False,"interval":interval}
        except Exception as e:
            last_error=e
    raise ValueError(f"{ticker}: Yahoo 요청 실패 ({last_error})")


def _refresh_fx():
    tickers={"원/달러":"USDKRW=X","엔/달러":"USDJPY=X","달러인덱스":"DX-Y.NYB","WTI 유가":"CL=F"}
    previous=_read_fx().get("items",{})
    snap={"updated":time.time(),"source":"Yahoo Finance","items":dict(previous)}
    errors=[]; successes=0
    with ThreadPoolExecutor(max_workers=4) as ex:
        futs={ex.submit(_fetch_yahoo_symbol,t):name for name,t in tickers.items()}
        for f,name in [(f,n) for f,n in futs.items()]:
            try:
                snap["items"][name]=f.result(); successes+=1
            except Exception as e:
                errors.append(f"{name}: {e}")
                if name in snap["items"]:
                    snap["items"][name]=dict(snap["items"][name]); snap["items"][name]["stale"]=True
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


# Handle one-shot manual refresh after refresh helpers are defined.
_manual_refresh = str(_qp.get("refresh", "0")) == "1"
if _manual_refresh:
    st.session_state.refresh_started = True
    st.session_state.refresh_applied = False
    st.session_state.refresh_baseline = _status_mtime()
    threading.Thread(target=_refresh_all_background, daemon=True).start()
    # Remove refresh=1 so browser reloads don't retrigger endlessly.
    st.query_params.clear()
    if _view != "dashboard":
        st.query_params["view"] = _view
    if _theme != "light":
        st.query_params["theme"] = _theme

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


def signal_floor(structure,rapid):
    sc=int((structure or {}).get("count",0) or 0); rc=int((rapid or {}).get("count",0) or 0)
    floor=0; reason=""
    if sc==1: floor,reason=40,"구조적 위험 신호 1개"
    elif sc>=2: floor,reason=50,"구조적 위험 신호 2개 이상"
    if rc==2 and 55>floor: floor,reason=55,"시장 급변 신호 2개"
    elif rc>=3 and 65>floor: floor,reason=65,"시장 급변 신호 3개 이상"
    if sc>=2 and rc>=3: floor,reason=70,"구조적 위험과 강한 급변 신호 동시 확인"
    elif sc>=2 and rc>=2 and 65>floor: floor,reason=65,"구조적 위험과 급변 신호 동시 확인"
    return floor,reason

def active_market_stress(sp,vix,credit_fast):
    z=sp.dropna(); vz=vix.dropna()
    if len(z)<21:return {"floor":0,"reason":"","drawdown":np.nan,"ret5":np.nan,"ret20":np.nan}
    peak=z.tail(252).max(); dd=(z.iloc[-1]/peak-1)*100 if peak>0 else np.nan
    r5=(z.iloc[-1]/z.iloc[-6]-1)*100 if len(z)>=6 and z.iloc[-6]>0 else np.nan
    r20=(z.iloc[-1]/z.iloc[-21]-1)*100 if z.iloc[-21]>0 else np.nan
    vv=latest(vz); cf=float(credit_fast) if pd.notna(credit_fast) else np.nan
    confirm55=(pd.notna(vv) and vv>=25) or (pd.notna(cf) and cf>=60)
    confirm65=(pd.notna(vv) and vv>=30) or (pd.notna(cf) and cf>=70)
    confirm75=(pd.notna(vv) and vv>=40) or (pd.notna(cf) and cf>=85)
    fast55=(pd.notna(r5) and r5<=-5) or (pd.notna(r20) and r20<=-8)
    fast65=(pd.notna(r5) and r5<=-7) or (pd.notna(r20) and r20<=-12)
    fast75=(pd.notna(r5) and r5<=-10) or (pd.notna(r20) and r20<=-15)
    floor=0; reason=""
    if pd.notna(dd) and dd<=-20 and fast75 and confirm75: floor,reason=75,"위기 수준의 진행 중 시장 스트레스"
    elif pd.notna(dd) and dd<=-15 and fast65 and confirm65: floor,reason=65,"강한 진행 중 시장 스트레스"
    elif pd.notna(dd) and dd<=-10 and fast55 and confirm55: floor,reason=55,"진행 중 시장 조정 스트레스"
    return {"floor":floor,"reason":reason,"drawdown":dd,"ret5":r5,"ret20":r20,"vix":vv,"credit_fast":cf}

def apply_risk_floors(base,structure,rapid,sp,vix,credit_fast):
    sf,sreason=signal_floor(structure,rapid); stress=active_market_stress(sp,vix,credit_fast)
    candidates=[(float(base) if pd.notna(base) else 0,"기본 종합위험"),(sf,sreason),(stress["floor"],stress["reason"])]
    final,reason=max(candidates,key=lambda x:x[0])
    return clamp(final),{"base":base,"signal_floor":sf,"stress_floor":stress["floor"],"reason":reason,"stress":stress}

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
base_overall=overall
overall,floor_diag=apply_risk_floors(base_overall,structure,rapid,sp,vix,current_fast.get("신용",np.nan))
if prev_snapshot is not None:
    prev_structure=structural_signals(prev_snapshot["details"],(prev_data["10년물"]-prev_data["2년물"]).dropna())
    prev_rapid=rapid_alert(prev_fast,{})
    prev_overall,_=apply_risk_floors(prev_snapshot["overall"],prev_structure,prev_rapid,prev_data["S&P500"],prev_data["VIX"],prev_fast.get("신용",np.nan))

# v3.38.8 adaptive dashboard refinement — Streamlit engine + custom HTML/CSS skin.
st.markdown("""<style>
html,body,.stApp{background:#f5f7fb!important;color:#171b23}
header[data-testid="stHeader"]{background:transparent!important}
.block-container{max-width:none!important;padding:26px 28px 54px 188px!important}
[data-testid="stSidebar"]{display:none!important}[data-testid="stToolbar"]{right:10px!important}#MainMenu{visibility:hidden}
.r38-sidebar{position:fixed;z-index:50;left:0;top:0;bottom:0;width:158px;background:linear-gradient(180deg,#101b2d,#0d1726);color:#fff;padding:22px 13px 18px;box-sizing:border-box}.r38-brand{display:flex;align-items:center;gap:9px;padding:0 9px 20px;font-size:14px;font-weight:800;line-height:1.25}.r38-brand-mark{width:27px;height:32px}.r38-brand-mark svg{width:27px;height:32px}.r38-nav{display:flex;flex-direction:column;gap:6px}.r38-nav-item{display:flex;align-items:center;gap:11px;height:42px;border-radius:7px;padding:0 11px;color:#aeb9c9;font-size:13.5px;font-weight:650;text-decoration:none!important}.r38-nav-item.active{background:linear-gradient(90deg,#365dce,#506be6);color:#fff;box-shadow:0 5px 16px rgba(45,78,190,.28)}.r38-nav-icon{width:17px;text-align:center;font-size:15px}.r38-side-bottom{position:absolute;left:20px;right:20px;bottom:20px;border-top:1px solid rgba(255,255,255,.08);padding-top:16px;color:#9eabba;font-size:11px;line-height:1.55}.r38-side-title{color:#dbe3ef;font-weight:700}.r38-toggle{display:flex;align-items:center;justify-content:space-between;margin-top:16px;color:#9eabba!important;text-decoration:none!important}.r38-toggle-pill{width:34px;height:18px;border-radius:999px;background:#566274;position:relative}.r38-toggle-pill:after{content:'';position:absolute;width:14px;height:14px;border-radius:50%;background:#d9dee6;left:2px;top:2px;transition:.15s}.r38-toggle-pill.on{background:#4469d8}.r38-toggle-pill.on:after{left:18px;background:#fff}
.r38-mobilebar{display:none}.r38-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;margin-bottom:16px}.r38-title{font-size:30px;font-weight:850;letter-spacing:-.045em;line-height:1.18}.r38-subtitle{font-size:15px;color:#69717d;margin-top:6px}.r38-credit{font-size:12px;color:#939aa5;margin-top:3px}.r38-head-actions{display:flex;gap:10px}.r38-action{height:44px;border:1px solid #dfe4eb;border-radius:8px;background:#fff;padding:0 15px;display:flex;align-items:center;font-size:14px;font-weight:650;color:#3c4654;text-decoration:none!important}
.r38-panel{background:#fff;border:1px solid #dde3eb;border-radius:12px;padding:19px;margin-bottom:15px;box-shadow:0 1px 2px rgba(25,38,58,.025)}.r38-section-title{display:flex;align-items:center;gap:7px;font-size:18px;font-weight:820;color:#202631;margin-bottom:15px}
.r38-info{position:relative;display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border:1px solid #9da5af;border-radius:50%;font-size:9px;color:#7d8590;font-weight:800;cursor:help;outline:none;flex:0 0 15px}.r38-info:hover,.r38-info:focus{background:#eef2f7;color:#37404b;border-color:#66717e}.r38-info-tip{visibility:hidden;opacity:0;pointer-events:none;position:absolute;z-index:9999;left:50%;top:23px;transform:translateX(-50%) translateY(-3px);width:min(330px,78vw);padding:12px 13px;border:1px solid #dfe4ea;border-radius:11px;background:#fff;box-shadow:0 12px 32px rgba(13,24,40,.15);font-size:12.5px;font-weight:550;line-height:1.55;color:#414955;text-align:left;white-space:normal;transition:opacity .12s ease,transform .12s ease}.r38-info:hover .r38-info-tip,.r38-info:focus .r38-info-tip{visibility:visible;opacity:1;transform:translateX(-50%) translateY(0)}
.r38-hero-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;align-items:stretch}.r38-hero-card{position:relative;min-height:306px;height:100%;border:1px solid #e3e7ed;border-radius:11px;padding:19px 19px 17px;box-sizing:border-box;background:#fff;overflow:visible;display:flex;flex-direction:column}.r38-hero-card.danger{border-color:#f0dddd}.r38-hero-card.warn{border-color:#f0e4cf}.r38-card-title{font-size:16.5px;font-weight:800;color:#3a4049;display:flex;align-items:center;gap:6px}.r38-horizon{font-size:12.5px;color:#8b929d;margin-top:4px}.r38-hero-main{display:grid;grid-template-columns:minmax(0,1fr) minmax(145px,38%);align-items:center;gap:18px;margin-top:18px;min-height:126px;flex:1}.r38-hero-left{min-width:0}.r38-hero-side{min-width:0;display:flex;align-items:center;justify-content:flex-start;text-align:left}.r38-big{font-size:45px;font-weight:850;line-height:1;white-space:nowrap;letter-spacing:-.05em}.r38-big.red{color:#d92f3b}.r38-big.orange{color:#d77b00}.r38-unit{font-size:14px;font-weight:650;white-space:nowrap;color:#555d68;margin-left:4px}.r38-badge{display:inline-flex;border-radius:999px;padding:6px 10px;font-size:12px;font-weight:800;margin-top:9px}.r38-badge.red{color:#fff;background:#e83d49}.r38-badge.orange{color:#fff;background:#f09a18}.r38-badge.green{color:#fff;background:#2ca675}.r38-badge.gray{color:#5e6672;background:#eef1f5}.r38-delta-label{font-size:12px;color:#737b87}.r38-delta{font-size:14px;margin-top:4px;font-weight:800}.r38-up{color:#e03b45}.r38-down{color:#2f70c9}.r38-flat{color:#7b8490}.r38-side-copy{font-size:13.5px;line-height:1.5;color:#616a76;font-weight:700;max-width:185px}.r38-side-copy strong{display:block;font-size:14.5px;color:#343b45;margin-bottom:4px}.r38-signal-main{font-size:38px;font-weight:850;white-space:nowrap;line-height:1.05;letter-spacing:-.035em;color:#252b34}.r38-signal-meta{font-size:13px;color:#707985;margin-top:8px;font-weight:700}.r38-callout{position:static;margin-top:12px;height:72px;min-height:72px;box-sizing:border-box;border-radius:8px;padding:12px 13px;font-size:12.5px;line-height:1.5;background:#fff6f6;border:1px solid #f5dede;color:#5c3b3e;display:flex;flex-direction:column;justify-content:center}.r38-callout.warn{background:#fff9ef;border-color:#f3e4c9;color:#69523a}.r38-summary-lines{display:flex;flex-direction:column;gap:3px}.r38-summary-lines b{font-weight:820}.r38-chips{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}.r38-chip{display:inline-flex;align-items:center;min-height:25px;box-sizing:border-box;padding:4px 8px;border-radius:999px;background:#fff0f0;border:1px solid #f3d3d3;color:#c33b42;font-size:11.5px;font-weight:750;line-height:1.2;white-space:nowrap}.r38-chip.warn{background:#fff5e7;border-color:#f0ddbd;color:#a76600}.r38-interpret{margin-top:12px;padding:14px 16px;border-radius:9px;background:#eef7ff;border:1px solid #d6e9f9;font-size:13.5px;line-height:1.6;color:#294862;font-weight:620}.r38-interpret-label{font-weight:850;color:#1f6598;margin-right:9px;white-space:nowrap}
.r38-risk-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:9px}.r38-risk-card{border:1px solid #e2e7ed;border-radius:9px;padding:15px 12px 13px;min-height:158px}.r38-risk-top{display:flex;align-items:center;gap:8px}.r38-risk-icon{width:28px;height:28px;border-radius:7px;background:#f2f6ff;border:1px solid #dfe7fa;display:flex;align-items:center;justify-content:center;color:#345ec8;font-size:14px;font-weight:800}.r38-risk-icon svg{width:17px;height:17px}.r38-risk-name{font-size:clamp(10.5px,.78vw,13px);font-weight:760;color:#3d4550;display:flex;align-items:center;gap:5px;white-space:nowrap;min-width:0}.r38-risk-numrow{display:flex;align-items:center;justify-content:space-between;margin-top:15px}.r38-risk-score{font-size:clamp(23px,1.7vw,28px);font-weight:850;white-space:nowrap}.r38-mini-state{font-size:clamp(8.5px,.66vw,11px);font-weight:800;border-radius:999px;padding:4px 7px;background:#fff1f1;color:#d63e46;white-space:nowrap}.r38-mini-state.mid{background:#fff7df;color:#c98300}.r38-mini-state.low{background:#edf8f3;color:#24855e}.r38-segments{display:flex;gap:3px;margin-top:13px}.r38-seg{height:4px;flex:1;border-radius:99px;background:#e8ebef}.r38-seg.on-red{background:#ea3944}.r38-seg.on-orange{background:#f0a018}.r38-seg.on-green{background:#3da77a}.r38-risk-foot,.r38-note{font-size:clamp(9.5px,.7vw,11.5px);color:#8c949f;margin-top:10px}.r38-risk-foot{white-space:nowrap}
.r38-market-table{border:1px solid #e1e6ed;border-radius:9px;overflow:hidden;display:grid;grid-template-columns:repeat(5,minmax(0,1fr));background:#fff}.r38-market-col{min-width:0;border-right:1px solid #e7ebf0}.r38-market-col:last-child{border-right:0}.r38-col-head{height:42px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:800;background:#fafbfc;border-bottom:1px solid #e7ebf0}.r38-metric{min-height:90px;padding:11px 12px 9px;border-bottom:1px solid #edf0f3}.r38-metric:last-child{border-bottom:0}.r38-metric-name{font-size:11.5px;color:#555e69;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.r38-metric-row{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;margin-top:4px}.r38-metric-value{font-size:18px;font-weight:820;white-space:nowrap}.r38-metric-delta{font-size:11px;margin-top:3px;font-weight:700;white-space:nowrap}.r38-spark{width:74px;height:30px;flex:0 0 74px}.r38-spark svg{width:100%;height:30px}.r38-recession{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}.r38-recession-card{background:#f8fafc;border:1px solid #e7ebf0;border-radius:8px;padding:10px 11px}.r38-recession-name{font-size:11.5px;color:#808895}.r38-recession-value{font-size:19px;font-weight:820;margin-top:3px}
div[data-testid="stButton"] button{border:1px solid #dfe4eb!important;background:#fff!important;color:#3e4651!important;border-radius:7px!important;font-size:12px!important;font-weight:700!important;min-height:36px!important;box-shadow:none!important}[data-testid="stExpander"]{border:1px solid #dde3eb!important;border-radius:10px!important;background:#fff!important}.r38-footer{font-size:10.5px;color:#9299a3;text-align:right;margin-top:12px}
@media(max-width:1180px) and (min-width:781px){.r38-hero-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.r38-hero-card:first-child{grid-column:1/-1}.r38-hero-card{min-height:300px}.r38-hero-main{grid-template-columns:minmax(0,1fr) minmax(150px,36%)}.r38-big{white-space:nowrap}.r38-unit{white-space:nowrap}.r38-signal-main{white-space:nowrap}}
@media(max-width:1050px){.block-container{padding-left:176px!important;padding-right:18px!important}.r38-risk-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.r38-market-table{grid-template-columns:repeat(3,minmax(0,1fr))}.r38-market-col:nth-child(3){border-right:0}.r38-market-col:nth-child(n+4){border-top:1px solid #e7ebf0}}

@media (orientation:portrait) and (min-width:781px){
  .r38-hero-grid{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:8px}
  .r38-hero-card:first-child{grid-column:auto!important}
  .r38-hero-card{min-height:300px;padding:16px 13px 14px}
  .r38-card-title{font-size:clamp(13px,1.25vw,16px);white-space:nowrap}
  .r38-horizon{font-size:clamp(10px,1vw,12px);white-space:nowrap}
  .r38-hero-main{grid-template-columns:minmax(0,1fr) minmax(95px,34%);gap:10px;min-height:120px}
  .r38-big{font-size:clamp(34px,3.6vw,43px)}
  .r38-unit{font-size:clamp(11px,1.15vw,13px)}
  .r38-signal-main{font-size:clamp(31px,3.7vw,38px)}
  .r38-badge{font-size:clamp(9.5px,1vw,11.5px);padding:5px 8px}
  .r38-side-copy{font-size:clamp(10px,1.05vw,12.5px);line-height:1.42;max-width:150px}
  .r38-side-copy strong{font-size:clamp(10.5px,1.1vw,13px)}
  .r38-callout{min-height:68px;padding:10px 11px;font-size:clamp(10px,1vw,12px)}
  .r38-chip{font-size:clamp(9px,.95vw,11px);padding:4px 7px}
  .r38-risk-grid{grid-template-columns:repeat(6,minmax(0,1fr))!important;gap:7px}
  .r38-risk-card{padding:12px 8px 11px;min-height:148px;min-width:0}
  .r38-risk-top{gap:5px}
  .r38-risk-icon{width:25px;height:25px;flex:0 0 25px;font-size:12px}
  .r38-risk-name{font-size:clamp(9px,1.15vw,11.5px)}
  .r38-mini-state{font-size:clamp(7.8px,.9vw,9.8px);padding:3px 5px}
  .r38-risk-score{font-size:clamp(20px,2.45vw,25px)}
  .r38-risk-foot{font-size:clamp(8px,.9vw,10px)}
  .r38-segments{gap:2px}
}
@media(max-width:780px){.r38-sidebar{display:none}.block-container{padding:calc(env(safe-area-inset-top,0px) + 44px) 12px 40px!important}.r38-mobilebar{display:flex;align-items:center;justify-content:space-between;background:#101b2d;color:#fff;margin:-18px -12px 15px;padding:12px 14px}.r38-mobile-brand{font-size:13px;font-weight:800}.r38-mobile-menu{font-size:19px}.r38-title{font-size:23px}.r38-subtitle{font-size:11.5px}.r38-head-actions{display:none}.r38-panel{padding:12px 11px}.r38-section-title{font-size:15px}.r38-hero-grid{grid-template-columns:1fr}.r38-hero-card{min-height:255px}.r38-hero-main{grid-template-columns:1fr;gap:10px;min-height:auto}.r38-hero-side{justify-content:flex-start;text-align:left}.r38-side-copy{max-width:none}.r38-callout{margin-top:14px;height:auto;min-height:auto}.r38-card-title{font-size:14px}.r38-big{font-size:37px;white-space:nowrap}.r38-signal-main{font-size:31px;white-space:nowrap}.r38-risk-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}.r38-market-table{grid-template-columns:repeat(2,minmax(0,1fr))}.r38-market-col,.r38-market-col:nth-child(3){border-right:1px solid #e7ebf0}.r38-market-col:nth-child(even){border-right:0}.r38-market-col:nth-child(n+3){border-top:1px solid #e7ebf0}.r38-recession{gap:5px}.r38-metric{min-height:80px;padding:9px}.r38-spark{width:58px;flex-basis:58px}.r38-info-tip{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%) scale(.98);width:min(340px,86vw);font-size:13px;padding:14px 15px;border-radius:14px;box-shadow:0 18px 55px rgba(0,0,0,.20)}.r38-info:hover .r38-info-tip,.r38-info:focus .r38-info-tip{transform:translate(-50%,-50%) scale(1)}.r38-footer{text-align:left}}
</style>""", unsafe_allow_html=True)
# ---------- v3.38.8 redesigned frontend ----------
import math

def _esc(x): return html.escape(str(x))

def _info38(text):
    return f'<span class="r38-info" tabindex="0">i<span class="r38-info-tip">{_esc(text)}</span></span>'

def _gauge_svg(score, tone="#e53b46"):
    sc=0.0 if pd.isna(score) else float(np.clip(score,0,100))
    angle=180-(sc*1.8); rad=math.radians(angle); cx,cy=50,53
    nx=cx+26*math.cos(rad); ny=cy-26*math.sin(rad)
    return f'''<div class="r38-gauge"><svg viewBox="0 0 100 66" aria-hidden="true"><path d="M12 53 A38 38 0 0 1 88 53" pathLength="100" fill="none" stroke="#edf0f4" stroke-width="8" stroke-linecap="round"/><path d="M12 53 A38 38 0 0 1 88 53" pathLength="100" fill="none" stroke="{tone}" stroke-width="8" stroke-linecap="round" stroke-dasharray="{sc:.1f} 100"/><line x1="50" y1="53" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#aab1bb" stroke-width="1.2"/><circle cx="50" cy="53" r="2.2" fill="#fff" stroke="#aab1bb" stroke-width="1"/><text x="10" y="64" class="r38-gauge-label">0</text><text x="84" y="64" class="r38-gauge-label">100</text></svg></div>'''

def _status_tone(score):
    if pd.isna(score): return ('gray','#89919b')
    if score>=61: return ('red','#e53b46')
    if score>=41: return ('orange','#efa019')
    return ('green','#2fa374')

def _risk_badge(score):
    c,_=_status_tone(score); return f'<span class="r38-badge {c}">{_esc(label(score))}</span>'

def _seg_html(score):
    n=0 if pd.isna(score) else int(np.clip(math.ceil(float(score)/20),0,5))
    c,_=_status_tone(score); on={'red':'on-red','orange':'on-orange','green':'on-green','gray':''}[c]
    return '<div class="r38-segments">'+''.join(f'<span class="r38-seg {on if i<n else ""}"></span>' for i in range(5))+'</div>'

def _spark_svg_38(values, cls='flat'):
    vals=[float(x) for x in values if pd.notna(x)]
    if len(vals)<2:return '<div class="r38-spark"></div>'
    vals=vals[-60:]; lo=min(vals); hi=max(vals); span=(hi-lo) or 1.0; pts=[]
    for i,v in enumerate(vals):
        x=2+62*i/(len(vals)-1); y=25-22*(v-lo)/span; pts.append(f'{x:.1f},{y:.1f}')
    color='#e53b46' if cls=='up' else ('#2f70c9' if cls=='down' else '#8b93a1')
    pts_str=' '.join(pts)
    return f'<div class="r38-spark"><svg viewBox="0 0 66 28" preserveAspectRatio="none"><polyline points="{pts_str}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></div>'

def _fmt_series_metric(s, unit='%', decimals=2):
    cur=latest(s); prv=second(s)
    if pd.isna(cur): return 'N/A','', 'flat'
    val=f'{cur:,.{decimals}f}{unit}'
    if pd.isna(prv): return val,'직전값 없음','flat'
    ch=float(cur-prv)
    if ch>0:return val,f'▲ {abs(ch):.{decimals}f}{unit}','up'
    if ch<0:return val,f'▼ {abs(ch):.{decimals}f}{unit}','down'
    return val,f'— {0:.{decimals}f}{unit}','flat'

def _fmt_fx_metric(name,decimals=2):
    item=fx.get(name,{})
    v=item.get('value',np.nan); p=item.get('prev',np.nan); stale=bool(item.get('stale',False))
    if pd.isna(v): return 'N/A','', 'flat'
    val=f'{v:,.{decimals}f}'
    if pd.isna(p) or p==0:return val,('직전값 없음 · 지연' if stale else '직전값 없음'),'flat'
    ch=float(v-p); pct=ch/p*100
    suffix=' · 지연' if stale else ''
    if ch>0:return val,f'▲ {abs(ch):,.{decimals}f} (+{abs(pct):.2f}%){suffix}','up'
    if ch<0:return val,f'▼ {abs(ch):,.{decimals}f} (-{abs(pct):.2f}%){suffix}','down'
    return val,f'— 0.{"0"*decimals} (0.00%){suffix}','flat'

def _cpi_metric(s):
    yoy=s.pct_change(12)*100; cur=latest(yoy); prv=second(yoy)
    if pd.isna(cur):return 'N/A','', 'flat'
    val=f'{cur:.2f}%'
    if pd.isna(prv):return val,'직전 발표 없음','flat'
    ch=float(cur-prv)
    if ch>0:return val,f'▲ {abs(ch):.2f}%p','up'
    if ch<0:return val,f'▼ {abs(ch):.2f}%p','down'
    return val,'— 0.00%p','flat'

def _metric_html(name,value,delta,cls,spark):
    return f'''<div class="r38-metric"><div class="r38-metric-name">{_esc(name)}</div><div class="r38-metric-row"><div><div class="r38-metric-value">{_esc(value)}</div><div class="r38-metric-delta r38-{cls}">{_esc(delta)}</div></div>{_spark_svg_38(spark,cls)}</div></div>'''

fed,y2,y10,y30=data['기준금리'],data['2년물'],data['10년물'],data['30년물']
term_premium=data.get('10년물기간프리미엄',pd.Series(dtype=float)); hy,bbb=data['하이일드스프레드'],data['BBB스프레드']
cpi,core_cpi,core_pce=data['CPI'],data['근원CPI'],data['근원PCE']; unemp,icsa,sp,vix=data['실업률'],data['신규실업수당'],data['S&P500'],data['VIX']
cape=_read_cape(); spread210=(y10-y2).dropna(); spread10fed=(y10-fed).dropna()
snapshot=compute_snapshot(data,cape); scores=snapshot['scores']; details=snapshot['details']; structure=snapshot['structure']
base_overall=snapshot['overall']; dev=details['market'].get('dev',np.nan); sahm_now=details['economy'].get('sahm_value',np.nan)
zsp=sp.dropna(); prev_date=zsp.index[-2] if len(zsp)>=2 else None
if prev_date is not None:
    prev_data={k:v.loc[:prev_date].dropna() for k,v in data.items()}; prev_cape=cape.loc[:prev_date].dropna() if len(cape) else cape
    prev_snapshot=compute_snapshot(prev_data,prev_cape,with_alerts=False); prev_fast=fast_signal_scores(prev_snapshot['details'])
else:
    prev_data={}; prev_snapshot=None; prev_fast={}
current_fast=fast_signal_scores(details); rapid=rapid_alert(current_fast,prev_fast)
overall,floor_diag=apply_risk_floors(base_overall,structure,rapid,sp,vix,current_fast.get('신용',np.nan))
if prev_snapshot is not None:
    prev_structure=structural_signals(prev_snapshot['details'],(prev_data['10년물']-prev_data['2년물']).dropna()); prev_rapid=rapid_alert(prev_fast,{})
    prev_overall,_=apply_risk_floors(prev_snapshot['overall'],prev_structure,prev_rapid,prev_data['S&P500'],prev_data['VIX'],prev_fast.get('신용',np.nan))
else: prev_overall=np.nan
_,delta_text,delta_class=delta_value(overall,prev_overall)

now_kst=datetime.now(ZoneInfo('Asia/Seoul'))
_theme_q='dark' if _theme=='dark' else 'light'
_dashboard_active=' active' if _view=='dashboard' else ''
_heatmap_active=' active' if _view=='heatmap' else ''
_theme_next='light' if _theme=='dark' else 'dark'
sidebar='''<aside class="r38-sidebar"><div class="r38-brand"><span class="r38-brand-mark"><svg viewBox="0 0 32 38" fill="none"><path d="M16 2.5 27 7v8.4c0 8.1-4.4 14.4-11 18.1C9.4 29.8 5 23.5 5 15.4V7L16 2.5Z" stroke="#E7EDF7" stroke-width="1.5"/><path d="m11 18 3 3 7-8" stroke="#E7EDF7" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg></span><span>Market Risk<br>Monitor</span></div><nav class="r38-nav"><a class="r38-nav-item'''+_dashboard_active+'''" href="?view=dashboard&theme='''+_theme_q+'''"><span class="r38-nav-icon">⌂</span>대시보드</a><a class="r38-nav-item'''+_heatmap_active+'''" href="?view=heatmap&theme='''+_theme_q+'''"><span class="r38-nav-icon">▦</span>S&P500 히트맵</a><div class="r38-nav-item"><span class="r38-nav-icon">◉</span>위험지수</div><div class="r38-nav-item"><span class="r38-nav-icon">≋</span>시장 상태</div><div class="r38-nav-item"><span class="r38-nav-icon">▣</span>데이터</div><div class="r38-nav-item"><span class="r38-nav-icon">♢</span>알림</div><div class="r38-nav-item"><span class="r38-nav-icon">▤</span>리포트</div><div class="r38-nav-item"><span class="r38-nav-icon">⚙</span>설정</div><div class="r38-nav-item"><span class="r38-nav-icon">?</span>도움말</div></nav><div class="r38-side-bottom"><div class="r38-side-title">최종 업데이트</div><div>'''+now_kst.strftime('%Y.%m.%d %H:%M')+'''</div><div>(한국시간 기준)</div><a class="r38-toggle" href="?view='''+_view+'''&theme='''+_theme_next+'''">다크 모드 <span class="r38-toggle-pill'''+(' on' if _theme=='dark' else '')+'''"></span></a></div></aside><div class="r38-mobilebar"><div class="r38-mobile-brand">Market Risk Monitor</div><div class="r38-mobile-menu">☰</div></div>'''
st.markdown(sidebar,unsafe_allow_html=True)
st.markdown(f'''<div class="r38-head"><div><div class="r38-title">미국 증시 위험 모니터</div><div class="r38-subtitle">현재 시장 상황과 주요 위험 신호를 한눈에 확인하세요.</div><div class="r38-credit">Developed by 유유상 · v3.38.8</div></div><div class="r38-head-actions"><div class="r38-action">{now_kst.strftime('%Y.%m.%d')}　▣</div><a class="r38-action" href="?view={_view}&theme={_theme_q}&refresh=1">↻　데이터 업데이트</a></div></div>''',unsafe_allow_html=True)

refresh_indicator()

if _view=="heatmap":
    st.markdown(
        '<section class="r38-panel"><div class="r38-section-title">S&amp;P500 히트맵</div>'
        '<div class="r38-note">TradingView 공식 Stock Heatmap 위젯 · 사이드바에서 선택할 때만 불러옵니다.</div></section>',
        unsafe_allow_html=True
    )
    heatmap_html = '''<div class="tradingview-widget-container" style="height:760px;width:100%">
      <div class="tradingview-widget-container__widget" style="height:calc(100% - 32px);width:100%"></div>
      <div class="tradingview-widget-copyright"><a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank">S&P 500 heatmap by TradingView</a></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js" async>
      {
        "exchanges": [],
        "dataSource": "SPX500",
        "grouping": "sector",
        "blockSize": "market_cap_basic",
        "blockColor": "change",
        "locale": "kr",
        "symbolUrl": "",
        "colorTheme": "__THEME__",
        "hasTopBar": true,
        "isDataSetEnabled": true,
        "isZoomEnabled": true,
        "hasSymbolTooltip": true,
        "isMonoSize": false,
        "width": "100%",
        "height": "100%"
      }
      </script>
    </div>'''.replace("__THEME__", "dark" if _theme=="dark" else "light")
    components.html(heatmap_html,height=790,scrolling=False)
    st.stop()

_structure_count=int(structure.get('count',0) or 0); _structure_raw=structure.get('level','정상')
_rapid_count=int(rapid.get('count',0) or 0); _rapid_raw=rapid.get('level','정상')
struct_score=50 if _structure_count>=2 else (40 if _structure_count==1 else 0); rapid_score=65 if _rapid_count>=3 else (55 if _rapid_count==2 else 0)
struct_tone='#e53b46' if _structure_count>=3 else ('#ef9d17' if _structure_count else '#2fa374'); rapid_tone='#e53b46' if _rapid_count>=2 else ('#ef9d17' if _rapid_count else '#2fa374')
struct_label={'정상':'정상','관찰':'관찰','주의':'주의','경계':'경고'}.get(_structure_raw,_structure_raw); rapid_label={'정상':'정상','관찰':'관찰','급변 경보':'경고','강한 스트레스':'경고'}.get(_rapid_raw,_rapid_raw)
struct_chips=''.join(f'<span class="r38-chip warn">{_esc(x[0])}</span>' for x in structure.get('items',[])) or '<span class="r38-chip warn">활성 신호 없음</span>'
rapid_chips=''.join(f'<span class="r38-chip">{_esc(x)}</span>' for x in rapid.get('active',[])) or '<span class="r38-chip">급변 없음</span>'
_struct_names=[x[0] for x in structure.get('items',[]) if x]
if rapid.get('level') in ('급변 경보','강한 스트레스'):
    market_summary='단기 시장 스트레스가 빠르게 높아지고 있어 변동성 확대에 주의가 필요합니다.'
elif _structure_count>=2:
    market_summary='시장 급변은 제한적이지만 여러 구조적 부담이 겹쳐 중기 위험을 주의해서 볼 구간입니다.'
elif _structure_count==1:
    _reason=_struct_names[0] if _struct_names else '구조적 위험 요인'
    market_summary=f'시장 전반은 비교적 안정적이지만, {_reason}로 구조적 부담은 남아 있습니다.'
elif overall>=61:
    market_summary='여러 위험 요인이 높아져 시장 취약성이 높은 상태입니다.'
elif overall>=41:
    market_summary='시장 위험은 보통 수준이며 일부 지표의 변화는 계속 확인할 필요가 있습니다.'
else:
    market_summary='시장 전반은 안정적이며 뚜렷한 급변 신호는 없습니다.'
hero_tone='#e53b46' if overall>=61 else ('#ef9d17' if overall>=41 else '#2fa374')
level1=f'''<section class="r38-panel"><div class="r38-section-title">한눈에 보는 시장 위험 {_info38("종합 위험지수는 중기적인 시장 취약성을 0~100으로 요약합니다. 구조적 위험은 수개월~1년 지속될 수 있는 취약성을, 시장 급변 신호는 수일~수주 단위의 빠른 스트레스를 별도로 보여줍니다.")}</div><div class="r38-hero-grid">
<div class="r38-hero-card danger"><div class="r38-card-title">위험지수 {_info38("시장·밸류에이션, 변동성, 금리, 신용, 경기, 물가를 가중 합산한 기본 위험도에 구조·급변·진행 중 시장 스트레스 하한을 적용한 최종 위험지수입니다.")}</div><div class="r38-horizon">중기 · 누적 시장 취약성</div><div class="r38-hero-main"><div class="r38-hero-left"><div><span class="r38-big {'red' if overall>=61 else ('orange' if overall>=41 else '')}">{overall:.1f}</span><span class="r38-unit">/ 100</span></div>{_risk_badge(overall)}</div><div class="r38-hero-side"><div class="r38-side-copy"><strong>전일 대비</strong><div class="r38-delta r38-{delta_class}">{_esc(delta_text)}</div></div></div></div><div class="r38-callout"><div class="r38-summary-lines"><div>현재 위험도 <b>{_esc(label(overall))}</b></div><div class="r38-chips"><span class="r38-chip warn">구조적 신호 {_structure_count}개</span><span class="r38-chip">급변 신호 {_rapid_count}개</span></div></div></div></div>
<div class="r38-hero-card warn"><div class="r38-card-title">구조적 위험 {_info38("장단기금리 역전 기억, 높은 CAPE, 물가 재가속, 고용 악화처럼 수개월 이상 지속될 수 있는 구조적 취약성을 감지합니다.")}</div><div class="r38-horizon">수개월~1년 · 지속 취약성</div><div class="r38-hero-main"><div class="r38-hero-left"><div class="r38-signal-main">{_esc(struct_label)}</div><span class="r38-badge {'orange' if _structure_count else 'green'}">신호 {_structure_count}개</span></div><div class="r38-hero-side"><div class="r38-side-copy"><strong>{'활성 신호 확인' if _structure_count else '구조 신호 없음'}</strong>{'현재 구조적 취약성이 감지되었습니다.' if _structure_count else '현재 뚜렷한 구조적 취약성은 없습니다.'}</div></div></div><div class="r38-callout warn"><b>감지된 신호 ({_structure_count}개)</b><div class="r38-chips">{struct_chips}</div></div></div>
<div class="r38-hero-card danger"><div class="r38-card-title">시장 급변 신호 {_info38("VIX, 신용 스프레드, 10년물 금리 상승, 신규 실업수당 추세 등 서로 다른 빠른 지표가 동시에 악화되는지를 봅니다. 1개 축은 관찰만 하며, 2개 이상 동시 확인되면 단기 시장 스트레스가 강화된 것으로 해석합니다.")}</div><div class="r38-horizon">수일~수주 · 단기 시장 스트레스</div><div class="r38-hero-main"><div class="r38-hero-left"><div class="r38-signal-main">{_esc(rapid_label)}</div><span class="r38-badge {'red' if _rapid_count>=2 else ('orange' if _rapid_count else 'green')}">급변 {_rapid_count}개</span></div><div class="r38-hero-side"><div class="r38-side-copy"><strong>{'단기 스트레스 확인' if _rapid_count>=2 else ('단일 축 관찰' if _rapid_count else '급변 없음')}</strong>{'여러 시장 축의 급격한 악화가 동시에 확인됩니다.' if _rapid_count>=2 else ('일부 급변 축을 관찰 중입니다.' if _rapid_count else '현재 뚜렷한 단기 급변 신호는 없습니다.')}</div></div></div><div class="r38-callout"><b>감지된 신호 ({_rapid_count}개)</b><div class="r38-chips">{rapid_chips}</div></div></div>
</div><div class="r38-interpret"><span class="r38-interpret-label">현재 시장 해석</span>{_esc(market_summary)}</div></section>'''
st.markdown(level1,unsafe_allow_html=True)


def _risk_icon_svg(kind):
    icons={
        '시장·밸류에이션':'<svg viewBox="0 0 24 24" fill="none"><path d="M4 17 9 12l4 3 7-8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 7h3v3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
        '변동성':'<svg viewBox="0 0 24 24" fill="none"><path d="M3 13c3-7 5 7 8 0s5-7 10 0" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
        '금리':'<span style="font-size:15px;font-weight:850">%</span>',
        '신용':'<svg viewBox="0 0 24 24" fill="none"><rect x="4" y="6" width="16" height="12" rx="2" stroke="currentColor" stroke-width="1.7"/><path d="M7 10h10M7 14h6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/></svg>',
        '경기':'<svg viewBox="0 0 24 24" fill="none"><path d="M5 18V11M10 18V7M15 18v-4M20 18V9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>',
        '물가':'<span style="font-size:16px;font-weight:850">$</span>'
    }
    return icons.get(kind,'')

label_map={'시장·밸류에이션':'시장 과열도','변동성':'변동성','금리':'금리','신용':'신용 시장','경기':'경기','물가':'물가'}
risk_info_map={
'시장·밸류에이션':'S&P500의 200일선 대비 과열, CAPE 고평가, 최근 상승 모멘텀을 종합한 시장 과열도입니다.',
'변동성':'현재 VIX 절대수준과 최근 5거래일 급등 속도를 종합합니다.',
'금리':'미국 10년물 수준과 상승 속도, 10Y-2Y, 10Y-EFFR, 기간프리미엄을 종합합니다.',
'신용':'하이일드·BBB 스프레드 수준과 최근 5일·20일 악화 속도를 종합합니다.',
'경기':'실업률, Sahm Rule, 신규 실업수당의 상대 수준과 추세를 종합합니다.',
'물가':'CPI, 근원 CPI, 근원 PCE의 전년비와 최근 3개월 연율화 흐름을 종합합니다.'
}
risk_cards=[]
for k in ['시장·밸류에이션','변동성','금리','신용','경기','물가']:
    sc=scores.get(k,np.nan); state_class='low' if pd.notna(sc) and sc<41 else ('mid' if pd.notna(sc) and sc<61 else '')
    score_txt=f'{sc:.1f}' if pd.notna(sc) else 'N/A'
    risk_cards.append(f'''<div class="r38-risk-card"><div class="r38-risk-top"><div class="r38-risk-icon">{_risk_icon_svg(k)}</div><div class="r38-risk-name">{label_map[k]} {_info38(risk_info_map[k])}</div></div><div class="r38-risk-numrow"><div class="r38-risk-score">{score_txt}</div><span class="r38-mini-state {state_class}">{_esc(label(sc))}</span></div>{_seg_html(sc)}<div class="r38-risk-foot">0~100 · 높을수록 위험</div></div>''')
st.markdown(f'''<section class="r38-panel"><div class="r38-section-title">6대 위험 카테고리 현황 {_info38("종합 위험지수를 구성하는 여섯 영역의 현재 점수입니다. 각 점수는 0~100이며 높을수록 해당 영역의 위험이 큽니다.")}</div><div class="r38-risk-grid">{''.join(risk_cards)}</div><div class="r38-note">* 각 카테고리는 0~100 점수로 평가되며, 높을수록 위험이 큽니다.</div></section>''',unsafe_allow_html=True)

fx=_read_fx().get('items',{})
spv,spd,spc=_fmt_series_metric(sp,'',2); effv,effd,effc=_fmt_series_metric(fed,'%',2); y2v,y2d,y2c=_fmt_series_metric(y2,'%',2); y10v,y10d,y10c=_fmt_series_metric(y10,'%',2); y30v,y30d,y30c=_fmt_series_metric(y30,'%',2)
hyv,hyd,hyc=_fmt_series_metric(hy,'%p',2); cpiv,cpid,cpic=_cpi_metric(cpi); unv,und,unc=_fmt_series_metric(unemp,'%',1)
dxyv,dxyd,dxyc=_fmt_fx_metric('달러인덱스',2); krwv,krwd,krwc=_fmt_fx_metric('원/달러',2); jpyv,jpyd,jpyc=_fmt_fx_metric('엔/달러',2); wtiv,wtid,wtic=_fmt_fx_metric('WTI 유가',2); wtiv='$'+wtiv if wtiv!='N/A' else wtiv
cols=[('주식 / 정책',[('S&P 500',spv,spd,spc,list(sp.dropna().tail(60).values)),('미국 기준금리',effv,effd,effc,list(fed.dropna().tail(36).values))]),('국채 금리',[('미국 2Y',y2v,y2d,y2c,list(y2.dropna().tail(60).values)),('미국 10Y',y10v,y10d,y10c,list(y10.dropna().tail(60).values)),('미국 30Y',y30v,y30d,y30c,list(y30.dropna().tail(60).values))]),('신용 / 물가',[('하이일드 스프레드',hyv,hyd,hyc,list(hy.dropna().tail(60).values)),('CPI',cpiv,cpid,cpic,list((cpi.pct_change(12)*100).dropna().tail(18).values))]),('경기 / 달러',[('실업률',unv,und,unc,list(unemp.dropna().tail(18).values)),('달러 인덱스',dxyv,dxyd,dxyc,fx.get('달러인덱스',{}).get('spark',[]))]),('환율 / 원자재',[('원/달러',krwv,krwd,krwc,fx.get('원/달러',{}).get('spark',[])),('엔/달러',jpyv,jpyd,jpyc,fx.get('엔/달러',{}).get('spark',[])),('WTI 유가',wtiv,wtid,wtic,fx.get('WTI 유가',{}).get('spark',[]))])]
market_html=[]
for head,items in cols: market_html.append('<div class="r38-market-col"><div class="r38-col-head">'+_esc(head)+'</div>'+''.join(_metric_html(*x) for x in items)+'</div>')
_claims_confirm=bool(details.get('economy',{}).get('claims_confirm',False))
if pd.notna(sahm_now) and sahm_now>=.5 and _claims_confirm: rec_status='확인'
elif pd.notna(sahm_now) and sahm_now>=.5: rec_status='관찰'
else: rec_status='정상'
sahm_text=f'{sahm_now:.2f}%p' if pd.notna(sahm_now) else 'N/A'; unemp_text=f'{latest(unemp):.1f}%' if pd.notna(latest(unemp)) else 'N/A'
rec_html=f'''<div class="r38-recession"><div class="r38-recession-card"><div class="r38-recession-name">실업률</div><div class="r38-recession-value">{unemp_text}</div></div><div class="r38-recession-card"><div class="r38-recession-name">Sahm Rule</div><div class="r38-recession-value">{sahm_text}</div></div><div class="r38-recession-card"><div class="r38-recession-name">경기침체 신호</div><div class="r38-recession-value">{rec_status}</div></div></div>'''
st.markdown(f'''<section class="r38-panel"><div class="r38-section-title">핵심 시장 상태 {_info38("위험지수 계산과 시장 해석에 쓰는 주요 지표의 현재값, 직전 변화, 최근 추세를 함께 보여줍니다. 환율·DXY·WTI 일부 항목은 참고용이며 산식에는 포함되지 않습니다.")}</div><div class="r38-market-table">{''.join(market_html)}</div>{rec_html}<div class="r38-note">환율·달러인덱스·WTI 유가는 참고자료이며 종합위험지수 산식에는 포함하지 않습니다.</div></section>''',unsafe_allow_html=True)

@st.cache_data(ttl=3600,show_spinner=False)
def historical_risk_fast_338(data,cape):
    months=pd.date_range(pd.Timestamp.now().normalize()-pd.DateOffset(months=12),pd.Timestamp.now().normalize(),freq='MS'); rows=[]; prior_fast={}
    for dt in months:
        sub={k:v.loc[:dt].dropna() for k,v in data.items()}
        if len(sub.get('S&P500',pd.Series(dtype=float)))<220 or len(sub.get('VIX',pd.Series(dtype=float)))<30 or len(sub.get('10년물',pd.Series(dtype=float)))<30: continue
        sub_cape=cape.loc[:dt].dropna() if len(cape) else cape; snap=compute_snapshot(sub,sub_cape,with_alerts=False); fast=fast_signal_scores(snap['details']); rap=rapid_alert(fast,prior_fast)
        struct=structural_signals(snap['details'],(sub['10년물']-sub['2년물']).dropna()); final,_=apply_risk_floors(snap['overall'],struct,rap,sub['S&P500'],sub['VIX'],fast.get('신용',np.nan)); rows.append((dt,snap['overall'],final)); prior_fast=fast
    return pd.DataFrame(rows,columns=['date','base','risk']).set_index('date') if rows else pd.DataFrame(columns=['base','risk'])

def render_history_chart_338(hist):
    rows=[]
    for dt,row in hist.dropna(how='all').iterrows():
        dt=pd.Timestamp(dt); rows.append({'date':f'{dt.year}년 {dt.month}월 {dt.day}일','year':int(dt.year),'month':int(dt.month),'risk':round(float(row['risk']),1),'base':round(float(row['base']),1)})
    payload=json.dumps(rows,ensure_ascii=False)
    chart_html='''<div id="r38ChartWrap" style="width:100%;height:300px;position:relative;font-family:-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR','Segoe UI',sans-serif;touch-action:pan-y;background:#fff"><svg id="r38Chart" width="100%" height="300"></svg><div id="r38Tip" style="display:none;position:absolute;pointer-events:none;background:#101827;color:#fff;border-radius:7px;padding:8px 10px;font-size:11px;line-height:1.55;white-space:nowrap;z-index:5"></div></div><script>(()=>{const data=__PAYLOAD__,svg=document.getElementById('r38Chart'),wrap=document.getElementById('r38ChartWrap'),tip=document.getElementById('r38Tip');if(!data.length)return;const NS='http://www.w3.org/2000/svg',W=Math.max(320,wrap.clientWidth),H=300,L=38,R=12,T=24,B=35,PW=W-L-R,PH=H-T-B;svg.setAttribute('viewBox',`0 0 ${W} ${H}`);const x=i=>L+(data.length===1?PW/2:i*PW/(data.length-1)),y=v=>T+(100-v)*PH/100,el=(n,a={})=>{const q=document.createElementNS(NS,n);Object.entries(a).forEach(([k,v])=>q.setAttribute(k,v));return q};[[70,100,'#fff1f1'],[40,70,'#fff8e8'],[0,40,'#f1f8f4']].forEach(([a,b,c])=>svg.appendChild(el('rect',{x:L,y:y(b),width:PW,height:y(a)-y(b),fill:c})));[0,25,50,75,100].forEach(v=>{const yy=y(v);svg.appendChild(el('line',{x1:L,y1:yy,x2:W-R,y2:yy,stroke:'#e7ebef','stroke-width':'1'}));const t=el('text',{x:L-7,y:yy+4,'text-anchor':'end',fill:'#818995','font-size':'10'});t.textContent=v;svg.appendChild(t)});data.forEach((d,i)=>{if(i===0||i===data.length-1||i%2===0){const t=el('text',{x:x(i),y:H-11,'text-anchor':'middle',fill:'#818995','font-size':'10'});t.textContent=i===0?`${String(d.year).slice(-2)}년 ${d.month}월`:(d.month===1?`${String(d.year).slice(-2)}년`:`${d.month}월`);svg.appendChild(t)}});svg.appendChild(el('polyline',{points:data.map((d,i)=>`${x(i)},${y(d.base)}`).join(' '),fill:'none',stroke:'#4169c7','stroke-width':'1.6','stroke-dasharray':'5 4'}));svg.appendChild(el('polyline',{points:data.map((d,i)=>`${x(i)},${y(d.risk)}`).join(' '),fill:'none',stroke:'#e23a43','stroke-width':'2.1','stroke-linejoin':'round','stroke-linecap':'round'}));const leg1=el('text',{x:L,y:12,fill:'#e23a43','font-size':'10'});leg1.textContent='━ 최종 위험지수';svg.appendChild(leg1);const leg2=el('text',{x:L+92,y:12,fill:'#4169c7','font-size':'10'});leg2.textContent='┄ 기본 위험지수';svg.appendChild(leg2);const show=clientX=>{const rect=wrap.getBoundingClientRect(),px=Math.max(0,Math.min(rect.width,clientX-rect.left)),idx=Math.max(0,Math.min(data.length-1,Math.round(px/rect.width*(data.length-1)))),d=data[idx];tip.innerHTML=`<b>${d.date}</b><br><span style="color:#ff5961">●</span> 최종 위험지수　<b>${d.risk.toFixed(1)}</b><br><span style="color:#6790e8">●</span> 기본 위험지수　${d.base.toFixed(1)}`;tip.style.display='block';tip.style.left=Math.max(4,Math.min(px+10,rect.width-175))+'px';tip.style.top='45px'},hide=()=>tip.style.display='none';wrap.addEventListener('mousemove',e=>show(e.clientX));wrap.addEventListener('mouseleave',hide);wrap.addEventListener('touchstart',e=>{if(e.touches[0])show(e.touches[0].clientX)},{passive:true});wrap.addEventListener('touchend',hide,{passive:true});})();</script>'''.replace('__PAYLOAD__',payload)
    components.html(chart_html,height=305,scrolling=False)

st.markdown(f'''<section class="r38-panel"><div class="r38-section-title">위험지수 추이 {_info38("빨간선은 신호 하한을 반영한 최종 위험지수, 파란 점선은 하한 적용 전 기본 위험지수입니다. 과거 계산은 초기 로딩 속도를 위해 필요할 때만 실행합니다.")}</div>''',unsafe_allow_html=True)
if 'show_history_338' not in st.session_state: st.session_state.show_history_338=False
if st.button('최근 1년 추이 불러오기',type='secondary',key='history338'): st.session_state.show_history_338=True
if st.session_state.show_history_338:
    with st.spinner('추이 계산 중…'): hist=historical_risk_fast_338(data,cape)
    if len(hist): render_history_chart_338(hist); st.caption('최근 1년 월별 스냅샷 · 빨강=최종 위험지수, 파랑 점선=신호 하한 적용 전 기본 위험지수')
    else: st.warning('과거 위험지수를 계산할 데이터가 부족합니다.')
else: st.caption('초기 로딩 속도를 위해 과거 추이 계산은 필요할 때만 실행합니다.')
st.markdown('</section>',unsafe_allow_html=True)
with st.expander('세부 데이터 및 계산 기준'):
    st.write('종합위험지수: 시장·밸류에이션 25% + 금리 25% + 신용 15% + 경기 17% + 변동성 10% + 물가 8%.')
    st.write('최종 위험지수는 기본 위험도, 구조·급변 신호 하한, 진행 중 시장 스트레스 하한 중 가장 높은 값을 사용합니다.')
    st.write('시장·밸류에이션: 200일선 과열 45% + CAPE 35% + 최근 20거래일 상승 모멘텀 20%. 폭락 자체는 추가 위험으로 가산하지 않습니다.')
    st.write('변동성: 현재 VIX 절대수준 55% + 최근 5거래일 급등 45%.')
    st.write('금리: 10년물 수준 35% + 최근 20거래일 상승속도 25% + 10Y-2Y 15% + 10Y-EFFR 15% + 10년물 기간프리미엄 10%.')
    st.write('신용: HY OAS 45% + BBB OAS 20% + 최근 5거래일 확대 15% + 최근 20거래일 확대 20%.')
    st.write('경기: 실업률 30% + Sahm Rule 35% + 신규 실업수당 35%.')
    st.write('물가: CPI 25% + 근원 CPI 35% + 근원 PCE 40%.')
    st.write('데이터 공급자는 내부 표준 키와 분리되어 향후 실시간 API로 교체하기 쉽도록 유지합니다.')
st.markdown(f'<div class="r38-footer">Risk Monitor 3.38.8 · 화면 갱신 {datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST")} · 캐시 즉시 표시 · 백그라운드 최신화</div>',unsafe_allow_html=True)
