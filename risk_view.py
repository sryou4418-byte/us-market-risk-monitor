"""Risk detail consumes one engine report; no duplicate financial thresholds."""
from presentation import text,fmt,number,signal_names,tone
from risk_engine import label,WEIGHTS,historical_risk_fast_338
import pandas as pd
import streamlit as st


@st.cache_data(ttl=3600,max_entries=8,show_spinner=False)
def history(data,cape,asof):
    return historical_risk_fast_338(data,cape,asof)


def render(st,report,data,cape,navigate):
    st.button('홈으로 돌아가기',key='risk_back',on_click=navigate,args=('dashboard',),icon=':material/arrow_back:')
    state=label(report['final'])
    st.markdown(f'<section class="detail-summary"><div><p class="eyebrow">현재 위험지수</p><strong>{fmt(report["final"])}<small> / 100</small></strong></div><div><span class="state {tone(state)}">{text(state)}</span><p>전일 대비 {text(report["delta"])}</p></div></section>',unsafe_allow_html=True)
    st.subheader('점수가 만들어지는 과정')
    st.caption('기본 점수와 두 하한 중 가장 높은 값이 최종 위험지수입니다. 세 축을 다시 더하거나 평균 내지 않습니다.')
    steps=[('기본 종합위험',report['overall']),('구조·급변 신호 하한',report['floors']['signal_floor']),('시장 스트레스 하한',report['floors']['stress_floor'])]
    st.markdown('<div class="formation">'+''.join(f'<div><span>{name}</span><strong>{fmt(value)}</strong></div>' for name,value in steps)+'</div>',unsafe_allow_html=True)
    st.subheader('위험지수 구성요소')
    rows=[]
    for name,value in report['scores'].items():
        width=max(0,min(100,number(value))) if number(value) is not None else 0
        state=label(value)
        rows.append(f'<article class="component-row"><div><strong>{text(name)}</strong><small>기본 가중치 {WEIGHTS[name]:.0%}</small></div><div class="component-track"><span style="width:{width}%"></span></div><b>{fmt(value)}</b><span class="state {tone(state)}">{text(state)}</span></article>')
    st.markdown('<div class="indicator-list">'+''.join(rows)+'</div>',unsafe_allow_html=True)
    st.caption('자료가 없는 구성요소는 —로 표시합니다. 기존 엔진은 확보된 점수의 가중치를 재정규화합니다.')
    for title,key in [('구조적 위험','structure'),('시장 급변신호','rapid')]:
        result=report[key]
        with st.expander(title+' · '+result['level'],expanded=True):
            st.caption('계산 가능한 항목 %s/%s · 감지 %s개' % (*report['coverage'][key],result['count']))
            for name in signal_names(result):st.write('• '+name)
            if not signal_names(result):st.write('확보된 자료에서 감지된 신호가 없습니다.')
    with st.expander('최근 1년 위험지수 추이'):
        st.caption('현시점 확보 자료로 재계산한 월별 스냅샷입니다. 당시 발표 자료를 복원한 백테스트가 아닙니다.')
        if st.button('추이 계산',key='history338'):st.session_state['show_history_338']=True
        if st.session_state.get('show_history_338'):
            hist=history(data,cape,report['asof'])
            if len(hist):
                frame=hist[['risk','base']].rename(columns={'risk':'최종 위험지수','base':'기본 위험지수'})
                st.line_chart(frame,color=['#d43d57','#245bd6'])
            else:st.info('과거 추이를 계산할 자료가 부족합니다.')
    with st.expander('계산 기준과 자료 시점'):
        st.write('기본 가중치: '+ ' · '.join(f'{k} {v:.0%}' for k,v in WEIGHTS.items()))
        st.write('구조적 위험과 시장 급변신호는 엔진의 상태와 감지 개수로 표시하며 별도 점수를 만들지 않습니다.')
        st.write('관측 대상 월과 실제 발표일은 다를 수 있습니다. 발표시점 정합성 및 장기 금융 검증은 후속 연구 항목입니다.')
