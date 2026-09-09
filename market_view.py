"""Market page rendering; pure engine results, HTML escaped at boundaries."""
import html
import pandas as pd
import streamlit as st
from market_engine import REGISTRY, evaluate, clean, percentile, pct
from presentation import Metric, number, fmt, tone, text

@st.cache_data(ttl=300,max_entries=8,show_spinner=False)
def cached_evaluate(data,asof):
    return evaluate(data,asof)

def render(st,data,asof=None):
    cutoff=str(pd.Timestamp(asof if asof is not None else pd.Timestamp.now(tz='UTC')).date())
    report=cached_evaluate(data,cutoff)
    esc=lambda x:html.escape(str(x))
    st.caption('시장 상태 v0.4 · 연구용 기준 · 개별 경보는 시장 전체 위험점수와 다른 개념입니다.')
    st.markdown('<div class="ms-summary">'+esc(report['summary'])+'</div>',unsafe_allow_html=True)
    overview=[]
    for group in ('주식','금리','신용','변동성','경기','물가'):
        rows=[r for r in report['results'].values() if r['group']==group and r['key'] not in ('VIXPOS','HYPOS')]
        valid=[r for r in rows if r['rank']>=0]; count=sum(r['rank']>=1 for r in valid)
        overview.append(f'<div class="ms-card"><b>{esc(group)}</b><div class="ms-value">{count}개 신호</div><div class="ms-detail">자료 확인 {len(valid)}/{len(rows)} · 영역 내 중복 신호 포함</div></div>')
    st.markdown('<div class="ms-grid6">'+''.join(overview)+'</div>',unsafe_allow_html=True)
    movers=[]
    day=pd.Timestamp(report['asof'])
    for k in ['SP500','NASDAQ','RUSSELL','VIX','US2Y','US10Y','US30Y','HY','BBB','DXY','USDKRW','USDJPY','WTI','GOLD','SILVER','COPPER']:
        if report['results'][k]['rank']<0:continue
        s=clean(data.get(k),day); is_bp=k in ('US2Y','US10Y','US30Y','HY','BBB'); n=5 if is_bp or k in ('DXY','USDKRW','USDJPY','WTI','GOLD','SILVER','COPPER') else 1
        q=percentile(s,n,'bp' if is_bp else 'pct')
        if pd.notna(q):
            v=(s.iloc[-1]-s.iloc[-1-n])*100 if is_bp else pct(s,n)
            movers.append((q,k,v,n,'bp' if is_bp else '%'))
    with st.expander('변화가 이례적인 지표 TOP 5',expanded=True):
        st.caption('서로 다른 관측기간의 이례성을 비교합니다. 위험도 순위가 아닙니다.')
        for q,k,v,n,unit in sorted(movers,reverse=True)[:5]:st.write(f"{REGISTRY[k]['title']} · {n}일 {v:+.2f}{unit} · {q:.1f}백분위")
        if not movers:st.write('분포 비교에 충분한 이력이 없습니다.')
    for group in ('주식','금리','신용','변동성','경기','물가','FX','원자재'):
        st.subheader(group)
        items=[r for r in report['results'].values() if r['group']==group]
        cards=[]
        for r in items:
            metric=Metric(r['title'],number(r['value']),r['unit'],r['state'],r['last_observation'],r['reason'])
            detail=r['reason']+' · '+r['persistence']
            cards.append(f'<article class="market-row"><div><strong>{text(metric.title)}</strong><small>관측 {text(metric.observed or "확인 불가")}</small></div><div class="market-value">{fmt(metric.value,2)} <small>{text(metric.unit)}</small></div><span class="state {tone(metric.state)}">{text(metric.state)}</span><div class="reason">{text(detail)}</div></article>')
        st.markdown('<div class="indicator-list">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    return report
