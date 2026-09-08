import pandas as pd
import numpy as np
_MS_RANK={"안정":0,"정상":0,"참고":0,"관찰":1,"주의":2,"위험":3,"확인 부족":-1}
_MS_STATE={0:"정상",1:"관찰",2:"주의",3:"위험"}

def _pct_ret_v02(s,n):
    z=s.dropna()
    if len(z)<=n:return np.nan
    return (float(z.iloc[-1])/float(z.iloc[-1-n])-1.0)*100.0

def _point_change_v02(s,n):
    z=s.dropna()
    if len(z)<=n:return np.nan
    return float(z.iloc[-1]-z.iloc[-1-n])

def _pctile_v345(s,window=252):
    z=s.dropna().tail(window)
    if len(z)<10:return np.nan
    cur=float(z.iloc[-1]); return float((z<=cur).mean()*100)

def _ms_rank_v346(state):
    return _MS_RANK.get(state,-1)

def _ms_state_v346(rank):
    return _MS_STATE.get(max(0,min(3,int(rank))),"정상")

def _ms_result_v346(state,reason="",level="—",change="—",meta=None):
    return {"state":state,"rank":_ms_rank_v346(state),"reason":reason,"level":level,"change":change,"meta":meta or {}}

def _ms_missing_v346(reason="데이터 부족"):
    return _ms_result_v346("확인 부족",reason,"확인 부족","확인 부족")

def _ms_worse_v346(*states):
    good=[x for x in states if x in _MS_RANK and _MS_RANK[x]>=0]
    if not good:return "확인 부족"
    return max(good,key=lambda x:_MS_RANK[x])

def _ms_raise_v346(state,minimum):
    if state=="확인 부족": return minimum
    return _ms_state_v346(max(_ms_rank_v346(state),_ms_rank_v346(minimum)))

def _move_percentile_v346(s,n,kind="pct",mode="abs",window=504):
    z=s.dropna().astype(float)
    if len(z)<=max(n+30,40): return np.nan
    mv=(z.pct_change(n)*100.0) if kind=="pct" else (z.diff(n)*100.0)
    cur=float(mv.iloc[-1]) if pd.notna(mv.iloc[-1]) else np.nan
    hist=mv.iloc[:-1].dropna().tail(window)
    if pd.isna(cur) or len(hist)<30:return np.nan
    if mode=="abs":
        cur_cmp=abs(cur); comp=hist.abs()
    elif mode=="up":
        cur_cmp=cur; comp=hist
    elif mode=="down":
        cur_cmp=-cur; comp=-hist
    else:
        cur_cmp=cur; comp=hist
    return float((((comp<cur_cmp).mean()) + 0.5*((comp==cur_cmp).mean()))*100.0)

def _move_pct_text_v346(p):
    if pd.isna(p): return "역사 비교 부족"
    tail=max(0.1,100.0-float(p))
    return f"최근 분포 상위 {tail:.1f}% 변동" if p>=50 else f"최근 분포 {p:.0f}백분위"

def _rank_fixed_v346(v,observe,caution,danger):
    if pd.isna(v): return -1
    a=abs(float(v))
    if a>=danger:return 3
    if a>=caution:return 2
    if a>=observe:return 1
    return 0

def _eval_equity_v346(s):
    z=s.dropna().astype(float)
    if len(z)<25:return _ms_missing_v346()
    r5=_pct_ret_v02(z,5); r20=_pct_ret_v02(z,20)
    dd=(float(z.iloc[-1]/z.tail(min(252,len(z))).max()-1.0)*100.0) if len(z) else np.nan
    level_rank=3 if dd<=-20 else (2 if dd<=-10 else (1 if dd<=-5 else 0))
    change_rank=0
    if pd.notna(r5): change_rank=max(change_rank,3 if r5<=-7 else (2 if r5<=-4 else (1 if r5<=-2.5 else 0)))
    if pd.notna(r20): change_rank=max(change_rank,3 if r20<=-12 else (2 if r20<=-8 else (1 if r20<=-5 else 0)))
    p5=_move_percentile_v346(z,5,"pct","abs")
    if pd.notna(r5) and r5<0 and pd.notna(p5):
        if p5>=97.5: change_rank=max(change_rank,2)
        elif p5>=90: change_rank=max(change_rank,1)
    rank=max(level_rank,change_rank)
    reason=f"5일 {r5:+.1f}% · 20일 {r20:+.1f}% · 고점 대비 {dd:.1f}%" if pd.notna(r5) and pd.notna(r20) and pd.notna(dd) else "주가 하락속도와 고점 대비 낙폭을 함께 확인"
    return _ms_result_v346(_ms_state_v346(rank),reason,_ms_state_v346(level_rank),_ms_state_v346(change_rank),{"r5":r5,"r20":r20,"dd":dd,"p5":p5})

def _eval_ma200_v346(s):
    z=s.dropna().astype(float)
    if len(z)<200:return _ms_missing_v346("200거래일 데이터 부족")
    ma=z.rolling(200).mean(); dev=float((z.iloc[-1]/ma.iloc[-1]-1.0)*100.0)
    if dev<=-12:rank=3
    elif dev<=-7:rank=2
    elif dev<=-3:rank=1
    elif dev>=18:rank=2
    elif dev>=12:rank=1
    else:rank=0
    side="하방 이탈" if dev<0 else ("상방 과열" if dev>=12 else "정상 범위")
    return _ms_result_v346(_ms_state_v346(rank),f"200DMA 대비 {dev:+.1f}% · {side}",_ms_state_v346(rank),"참고",{"dev":dev})

def _eval_relative_v346(v):
    if pd.isna(v):return _ms_missing_v346()
    rank=3 if v<=-7 else (2 if v<=-4 else (1 if v<=-2 else 0))
    return _ms_result_v346(_ms_state_v346(rank),f"RSP가 SPY 대비 20일 {v:+.1f}%p",_ms_state_v346(rank),"참고",{"relative":v})

def _eval_rate_move_v346(s,label="금리"):
    z=s.dropna().astype(float)
    if len(z)<25:return _ms_missing_v346()
    c5=_point_change_v02(z,5); c20=_point_change_v02(z,20)
    bp5=c5*100 if pd.notna(c5) else np.nan; bp20=c20*100 if pd.notna(c20) else np.nan
    rank=max(_rank_fixed_v346(bp5,15,25,40),_rank_fixed_v346(bp20,35,55,80),0)
    p5=_move_percentile_v346(z,5,"bp","abs"); p20=_move_percentile_v346(z,20,"bp","abs")
    p=max([x for x in (p5,p20) if pd.notna(x)],default=np.nan)
    if pd.notna(p):
        if p>=97.5:rank=max(rank,2)
        elif p>=90:rank=max(rank,1)
    direction="급등" if (pd.notna(bp5) and bp5>0) else ("급락" if pd.notna(bp5) and bp5<0 else "변화")
    reason=f"5일 {bp5:+.0f}bp · 20일 {bp20:+.0f}bp · {direction}" if pd.notna(bp5) and pd.notna(bp20) else f"{label} 변화속도 확인"
    return _ms_result_v346(_ms_state_v346(rank),reason,"참고",_ms_state_v346(rank),{"bp5":bp5,"bp20":bp20,"pctl":p})

def _eval_curve_v346(s,label="수익률곡선"):
    z=s.dropna().astype(float)
    if len(z)<22:return _ms_missing_v346()
    cur=float(z.iloc[-1]); ch20=float((z.iloc[-1]-z.iloc[-21])*100.0)
    level_rank=2 if cur<=-1.0 else (1 if cur<0 else 0)
    change_rank=2 if abs(ch20)>=80 else (1 if abs(ch20)>=50 else 0)
    if cur>=0 and float(z.iloc[-21])<0 and ch20>=25: change_rank=max(change_rank,1)
    rank=min(2,max(level_rank,change_rank))
    phase="역전" if cur<0 else ("정상 기울기" if cur>=0 else "")
    reason=f"현재 {cur:+.2f}%p · 20일 {ch20:+.0f}bp · {phase}"
    return _ms_result_v346(_ms_state_v346(rank),reason,_ms_state_v346(level_rank),_ms_state_v346(change_rank),{"spread":cur,"bp20":ch20})

def _eval_vix_v346(s):
    z=s.dropna().astype(float)
    if len(z)<22:return _ms_missing_v346()
    cur=latest(z); r5=_pct_ret_v02(z,5); r20=_pct_ret_v02(z,20)
    level_rank=0 if cur<20 else (1 if cur<25 else (2 if cur<30 else 3))
    stable=cur<15
    change_rank=0
    if pd.notna(r5): change_rank=max(change_rank,3 if r5>=60 else (2 if r5>=35 else (1 if r5>=20 else 0)))
    if pd.notna(r20): change_rank=max(change_rank,3 if r20>=100 else (2 if r20>=60 else (1 if r20>=35 else 0)))
    p5=_move_percentile_v346(z,5,"pct","up")
    if pd.notna(p5):
        if p5>=97.5 and pd.notna(r5) and r5>0:change_rank=max(change_rank,2)
        elif p5>=90 and pd.notna(r5) and r5>0:change_rank=max(change_rank,1)
    rank=max(level_rank,change_rank)
    state="안정" if rank==0 and stable else _ms_state_v346(rank)
    reason=f"VIX {cur:.1f} · 5일 {r5:+.1f}% · 20일 {r20:+.1f}%" if pd.notna(r5) and pd.notna(r20) else f"VIX {cur:.1f}"
    return _ms_result_v346(state,reason,("안정" if stable else _ms_state_v346(level_rank)),_ms_state_v346(change_rank),{"value":cur,"r5":r5,"r20":r20,"p5":p5})

def _eval_credit_v346(s,kind="HY"):
    z=s.dropna().astype(float)
    if len(z)<22:return _ms_missing_v346()
    cur=latest(z); c5=_point_change_v02(z,5); c20=_point_change_v02(z,20)
    bp5=c5*100 if pd.notna(c5) else np.nan; bp20=c20*100 if pd.notna(c20) else np.nan
    if kind=="HY":
        if cur<3.5: level_rank=0; stable=True
        elif cur<4.5: level_rank=0; stable=False
        elif cur<6.0: level_rank=1; stable=False
        elif cur<8.0: level_rank=2; stable=False
        else: level_rank=3; stable=False
        cr5=(15,30,60); cr20=(30,60,120)
    else:
        if cur<1.3: level_rank=0; stable=True
        elif cur<1.8: level_rank=0; stable=False
        elif cur<2.5: level_rank=1; stable=False
        elif cur<3.5: level_rank=2; stable=False
        else: level_rank=3; stable=False
        cr5=(8,15,30); cr20=(18,35,70)
    change_rank=0
    if pd.notna(bp5) and bp5>0: change_rank=max(change_rank,3 if bp5>=cr5[2] else (2 if bp5>=cr5[1] else (1 if bp5>=cr5[0] else 0)))
    if pd.notna(bp20) and bp20>0: change_rank=max(change_rank,3 if bp20>=cr20[2] else (2 if bp20>=cr20[1] else (1 if bp20>=cr20[0] else 0)))
    p5=_move_percentile_v346(z,5,"bp","up")
    if pd.notna(p5) and pd.notna(bp5) and bp5>0:
        if p5>=97.5:change_rank=max(change_rank,2)
        elif p5>=90:change_rank=max(change_rank,1)
    rank=max(level_rank,change_rank)
    state="안정" if rank==0 and stable else _ms_state_v346(rank)
    reason=f"{kind} {cur:.2f}%p · 5일 {bp5:+.0f}bp · 20일 {bp20:+.0f}bp" if pd.notna(bp5) and pd.notna(bp20) else f"{kind} {cur:.2f}%p"
    return _ms_result_v346(state,reason,("안정" if stable else _ms_state_v346(level_rank)),_ms_state_v346(change_rank),{"value":cur,"bp5":bp5,"bp20":bp20,"p5":p5})

def _eval_claims_v346(s):
    z=s.dropna().astype(float)
    if len(z)<20:return _ms_missing_v346()
    avg4=z.rolling(4).mean().dropna()
    if len(avg4)<10:return _ms_missing_v346()
    cur=latest(avg4); ch8=_pct_ret_v02(avg4,8); p=_pctile_v345(avg4,52)
    low52=float(avg4.tail(52).min()) if len(avg4.tail(52)) else np.nan
    rise52=((cur/low52)-1.0)*100.0 if pd.notna(low52) and low52>0 else np.nan
    # Claims are not abnormal merely because they make a small new 1-year high.
    # Level alert requires a meaningful rise from the 52-week low; percentile is supporting context.
    level_rank=3 if pd.notna(rise52) and rise52>=25 else (2 if pd.notna(rise52) and rise52>=15 else (1 if pd.notna(rise52) and rise52>=8 else 0))
    if pd.notna(p) and p<80: level_rank=min(level_rank,1)
    change_rank=3 if pd.notna(ch8) and ch8>=20 else (2 if pd.notna(ch8) and ch8>=10 else (1 if pd.notna(ch8) and ch8>=5 else 0))
    rank=max(level_rank,change_rank)
    reason=f"4주평균 {cur/1000:.0f}K · 52주 저점 대비 {rise52:+.1f}% · 약 8주 {ch8:+.1f}% · 1년 {p:.0f}백분위" if pd.notna(ch8) and pd.notna(p) and pd.notna(rise52) else f"4주평균 {cur/1000:.0f}K"
    return _ms_result_v346(_ms_state_v346(rank),reason,_ms_state_v346(level_rank),_ms_state_v346(change_rank),{"avg4":cur,"ch8":ch8,"pctl":p,"rise52":rise52})

def _eval_sahm_v346(v):
    if pd.isna(v):return _ms_missing_v346()
    rank=3 if v>=0.75 else (2 if v>=0.50 else (1 if v>=0.30 else 0))
    reason=f"3개월 평균이 이전 12개월 저점 대비 {v:.2f}%p 상승"
    return _ms_result_v346(_ms_state_v346(rank),reason,_ms_state_v346(rank),"월간",{"value":v})

def _eval_inflation_v346(s,kind="CPI"):
    z=s.dropna().astype(float)
    if not len(z):return _ms_missing_v346("FRED 저장 자료 없음")
    z=z.groupby(z.index.to_period("M")).last()
    anchor=z.index[-1]
    def calendar_value(months):
        target=anchor-months
        return float(z.loc[target]) if target in z.index else np.nan
    cur=float(z.iloc[-1]); y0=calendar_value(12); a0=calendar_value(3)
    y=(cur/y0-1.0)*100.0 if pd.notna(y0) and y0>0 else np.nan
    a=((cur/a0)**4-1.0)*100.0 if pd.notna(a0) and a0>0 else np.nan
    missing=[]
    if pd.isna(y):missing.append(f"전년비 기준월 {anchor-12} 누락")
    if pd.isna(a):missing.append(f"3개월 연율 기준월 {anchor-3} 누락")
    if pd.isna(y) and pd.isna(a):
        reason="특정 월 누락: "+" · ".join(missing) if len(z)>=4 else f"필요 이력 부족: {len(z)}개월"
        return _ms_missing_v346(reason)
    if kind=="Core PCE":
        l=(2.5,3.0,4.0); m=(2.5,3.0,4.0)
    elif kind=="Core CPI":
        l=(3.0,3.5,4.5); m=(3.0,3.5,4.5)
    else:
        l=(3.0,3.5,5.0); m=(3.0,4.0,6.0)
    level_rank=(3 if y>=l[2] else (2 if y>=l[1] else (1 if y>=l[0] else 0))) if pd.notna(y) else -1
    change_rank=(3 if a>=m[2] else (2 if a>=m[1] else (1 if a>=m[0] else 0))) if pd.notna(a) else -1
    if pd.notna(y) and pd.notna(a) and a>=y+0.5 and a>=m[0]:change_rank=max(change_rank,2)
    rank=max(level_rank,change_rank)
    parts=[f"YoY {y:.1f}%" if pd.notna(y) else "YoY 확인 부족",f"3개월 연율 {a:.1f}%" if pd.notna(a) else "3개월 연율 확인 부족"]
    if pd.notna(y) and pd.notna(a) and a>=y+0.5 and a>=m[0]:parts.append("최근 재가속")
    if missing:parts.append("특정 월 누락: "+", ".join(missing))
    return _ms_result_v346(_ms_state_v346(rank)," · ".join(parts),_ms_state_v346(level_rank) if level_rank>=0 else "확인 부족",_ms_state_v346(change_rank) if change_rank>=0 else "확인 부족",{"yoy":y,"ann3":a,"missing_metrics":missing})

def _eval_move_only_v346(s,n5=5,n20=20,kind="pct",cap="주의"):
    z=s.dropna().astype(float)
    if len(z)<40:return _ms_missing_v346()
    v5=_pct_ret_v02(z,n5) if kind=="pct" else (_point_change_v02(z,n5)*100)
    v20=_pct_ret_v02(z,n20) if kind=="pct" else (_point_change_v02(z,n20)*100)
    p5=_move_percentile_v346(z,n5,kind,"abs"); p20=_move_percentile_v346(z,n20,kind,"abs")
    p=max([x for x in (p5,p20) if pd.notna(x)],default=np.nan)
    rank=0
    if pd.notna(p):
        if p>=97.5:rank=2
        elif p>=90:rank=1
    rank=min(rank,_ms_rank_v346(cap))
    reason=(f"5일 {v5:+.1f}% · 20일 {v20:+.1f}% · {_move_pct_text_v346(p)}" if kind=="pct" and pd.notna(v5) and pd.notna(v20)
            else f"최근 변화 · {_move_pct_text_v346(p)}")
    return _ms_result_v346(_ms_state_v346(rank),reason,"참고",_ms_state_v346(rank),{"v5":v5,"v20":v20,"pctl":p})

def latest(s):
    s=s.dropna(); return float(s.iloc[-1]) if len(s) else np.nan

