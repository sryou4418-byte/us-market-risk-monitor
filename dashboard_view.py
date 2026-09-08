"""Home presentation only: consume engine results without recalculating risk."""
from html import escape
from math import isfinite


def _text(value):
    return escape(str(value))


def overview_html(score, risk_label, delta, structure, rapid, observed):
    """Keep signal states and counts distinct from the composite 0–100 score."""
    available = score is not None and isfinite(float(score))
    value = f'{score:.1f}' if available else '—'
    state = risk_label if available else '데이터 부족'
    tone = {'매우 낮음': 'calm', '낮음': 'calm', '보통': 'watch',
            '높음': 'alert', '매우 높음': 'alert'}.get(state, 'unknown')
    cards = [f'<article class="home-axis home-score"><h3>위험지수</h3>'
             '<p class="home-role">현재 시장의 전반적인 위험 수준</p>'
             f'<div class="home-value">{value}<span> / 100</span></div>'
             f'<span class="home-state {tone}">{_text(state)}</span>'
             f'<p class="home-foot">전일 대비 {_text(delta) if available else "—"}</p></article>']
    for title, role, horizon, result in (
        ('구조적 위험', '시장 내부에 누적되는 위험 요인', '수개월~1년 · 지속 취약성', structure),
        ('시장 급변신호', '단기 충격과 빠른 시장 변화 감지', '수일~수주 · 단기 스트레스', rapid),
    ):
        level = result.get('level', '데이터 부족')
        count = result.get('count')
        status_tone = {'정상': 'calm', '관찰': 'watch', '주의': 'watch',
                       '경계': 'alert', '급변 경보': 'alert', '강한 스트레스': 'alert'}.get(level, 'unknown')
        count_text = f'감지된 신호 {count}개' if count is not None else '신호 수 확인 불가'
        cards.append(f'<article class="home-axis"><h3>{title}</h3>'
                     f'<p class="home-role">{role}</p><div class="home-signal">{_text(level)}</div>'
                     f'<span class="home-state {status_tone}">{_text(count_text)}</span>'
                     f'<p class="home-foot">{horizon}</p></article>')
    summary = f'위험지수 {state} · 구조적 위험 {structure.get("level", "데이터 부족")} · 급변신호 {rapid.get("level", "데이터 부족")}'
    return ('<section class="home-overview" aria-label="세 영역으로 보는 시장 위험">'
            '<div class="home-intro"><p class="home-eyebrow">MARKET OVERVIEW</p>'
            '<h2>한눈에 보는 시장 위험</h2>'
            f'<p class="home-summary">{_text(summary)}</p>'
            f'<p class="home-foot">S&amp;P500 관측일 {_text(observed)} · 지표별 자료 시점은 다를 수 있어요.</p></div>'
            f'<div class="home-axes">{"".join(cards)}</div></section>')


def render(st, *, score, risk_label, delta, structure, rapid, observed, navigate):
    st.markdown(overview_html(score, risk_label, delta, structure, rapid, observed),
                unsafe_allow_html=True)
    with st.container(key='home_details'):
        st.button('위험지수 산출 근거 보기', key='home_risk_details',
                  on_click=navigate, args=('risk',), use_container_width=True)
        with st.expander('구조적 위험 · 감지된 요인'):
            st.caption('수개월 이상 지속될 수 있는 시장의 취약성을 확인해요.')
            items = structure.get('items', [])
            for item in items:
                st.write('• ' + str(item[0]))
            if not items:
                st.write('확보된 자료에서 감지된 구조적 위험신호가 없어요.')
        with st.expander('시장 급변신호 · 감지된 요인'):
            st.caption('빠른 지표의 동시 악화와 지속 여부를 함께 확인해요.')
            items = rapid.get('active', [])
            for item in items:
                st.write('• ' + str(item))
            if not items:
                st.write('확보된 자료에서 감지된 시장 급변신호가 없어요.')
            st.caption('신호가 없다는 표시는 모든 지표의 데이터가 확보됐다는 뜻은 아니에요.')
