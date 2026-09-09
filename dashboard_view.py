"""Overview: one prominent score, two signal summaries, concise evidence."""
from presentation import text,fmt,number,tone,signal_names,Metric
from risk_engine import label


def overview_html(score,risk_label,delta,structure,rapid,observed):
    available = number(score) is not None
    state = risk_label if available else '데이터 부족'
    signals=[]
    for title,role,result in [('구조적 위험','누적된 시장의 취약성',structure),('시장 급변신호','빠른 악화와 단기 충격',rapid)]:
        level = result.get('level','데이터 부족')
        count = result.get('count')
        count_text = f'감지된 신호 {count}개' if count is not None else '신호 수 확인 불가'
        signals.append(f'<article class="signal-summary"><div class="signal-heading"><h3>{title}</h3><span class="state {tone(level)}">{text(level)}</span></div><p>{role}</p><strong>{text(count_text)}</strong></article>')
    return ('<section class="overview-layout" aria-label="세 영역으로 보는 시장 위험">'
            '<article class="score-hero"><p class="eyebrow">COMPOSITE RISK</p><h2>위험지수</h2>'
            f'<div class="score-value">{fmt(score)}<span> / 100</span></div><span class="state {tone(state)}">{text(state)}</span>'
            f'<p>전일 대비 <b>{text(delta) if available else "—"}</b></p>'
            '<div class="risk-scale" aria-hidden="true"><i></i><i></i><i></i><i></i><i></i></div>'
            '<div class="scale-labels"><span>낮은 위험</span><span>높은 위험</span></div>'
            f'<p class="observation">S&amp;P500 관측일 {text(observed)}</p></article>'
            f'<div class="signal-stack">{"".join(signals)}<p class="muted">세 축은 서로 다른 관점입니다. 구조·급변 신호는 최종 위험지수의 하한에 반영됩니다.</p></div></section>')


def sparkline(series):
    values=[number(v) for v in series.dropna().tail(60)]
    if len(values)<2 or any(v is None for v in values):return ''
    low,high=min(values),max(values)
    points=' '.join(f'{i*116/(len(values)-1)+2:.1f},{34-(v-low)/(high-low or 1)*28:.1f}' for i,v in enumerate(values))
    return f'<svg class="sparkline" viewBox="0 0 120 40" role="img" aria-label="최근 관측값 추이"><polyline points="{points}"/></svg>'


def render(st,*,report,data,navigate):
    observed = str(data['S&P500'].dropna().index[-1].date()) if len(data['S&P500'].dropna()) else '확인 불가'
    st.markdown(overview_html(report['final'],label(report['final']),report['delta'],report['structure'],report['rapid'],observed),unsafe_allow_html=True)
    counts=report['coverage']
    st.caption('계산 가능한 항목 · 위험지수 %s/6 영역 · 구조적 위험 %s/4 요인 · 급변신호 %s/4 축. 자료 완전성이나 신뢰도 비율은 아닙니다.' % (counts['risk'][0],counts['structure'][0],counts['rapid'][0]))
    st.button('위험지수 산출 근거 보기',key='home_risk_details',type='primary',on_click=navigate,args=('risk',),icon=':material/arrow_forward:')
    st.markdown('<div class="section-heading"><h2>주요 시장 지표</h2><span>현재값 · 최근 흐름</span></div>',unsafe_allow_html=True)
    rows=[]
    for name,unit in [('S&P500',''),('VIX',''),('10년물','%'),('하이일드스프레드','%p'),('실업률','%')]:
        s=data[name];m=Metric.from_series(name,s,unit)
        rows.append(f'<article class="indicator-row"><div><strong>{text(m.title)}</strong><small>관측 {m.observed or "확인 불가"}</small></div>{sparkline(s)}<div class="indicator-value">{fmt(m.value,2)} <small>{unit}</small></div></article>')
    st.markdown('<div class="indicator-list">'+''.join(rows)+'</div>',unsafe_allow_html=True)
    st.button('시장 상태에서 모든 지표 보기',key='home_market_details',on_click=navigate,args=('market',))
    with st.expander('감지된 위험 요인'):
        for title,result in [('구조적 위험',report['structure']),('시장 급변신호',report['rapid'])]:
            st.write('**'+title+'**')
            for item in signal_names(result):st.write('• '+item)
            if not signal_names(result):st.write('확보된 자료에서 감지된 신호가 없습니다.')
        st.caption('신호 없음은 모든 자료가 확보됐다는 뜻이 아닙니다.')
