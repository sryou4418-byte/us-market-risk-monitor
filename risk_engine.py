"""Pure composite-risk calculation. Extracted unchanged from main; no UI or I/O."""
import numpy as np
import pandas as pd
WEIGHTS={"시장·밸류에이션":.25,"변동성":.10,"금리":.25,"신용":.15,"경기":.17,"물가":.08}

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


def historical_risk_fast_338(data, cape, asof):
    months = pd.date_range(pd.Timestamp(asof).normalize() - pd.DateOffset(months=12), pd.Timestamp(asof).normalize(), freq='MS')
    rows = []
    prior_fast = {}
    for dt in months:
        sub = {k: v.loc[:dt].dropna() for k, v in data.items()}
        if len(sub.get('S&P500', pd.Series(dtype=float))) < 220 or len(sub.get('VIX', pd.Series(dtype=float))) < 30 or len(sub.get('10년물', pd.Series(dtype=float))) < 30:
            continue
        sub_cape = cape.loc[:dt].dropna() if len(cape) else cape
        snap = compute_snapshot(sub, sub_cape, with_alerts=False)
        fast = fast_signal_scores(snap['details'])
        rap = rapid_alert(fast, prior_fast)
        struct = structural_signals(snap['details'], (sub['10년물'] - sub['2년물']).dropna())
        final, _ = apply_risk_floors(snap['overall'], struct, rap, sub['S&P500'], sub['VIX'], fast.get('신용', np.nan))
        rows.append((dt, snap['overall'], final))
        prior_fast = fast
    return pd.DataFrame(rows, columns=['date', 'base', 'risk']).set_index('date') if rows else pd.DataFrame(columns=['base', 'risk'])
