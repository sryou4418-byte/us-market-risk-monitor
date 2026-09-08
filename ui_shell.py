"""Session-preserving navigation and shared responsive visual rules."""
from pathlib import Path
import streamlit as st

VERSION = '3.50.0'
PAGES = {'dashboard': '대시보드', 'heatmap': 'S&P500 시장 맵',
         'risk': '위험지수', 'market': '시장 상태', 'news': '뉴스'}


def navigate(view):
    if view not in PAGES:
        return
    st.query_params['view'] = view
    st.query_params.pop('refresh', None)
    if view == 'news' and st.session_state.get('_news_category_saved'):
        st.query_params['news_category'] = st.session_state['_news_category_saved']


def toggle_theme():
    st.query_params['theme'] = 'light' if st.query_params.get('theme') == 'dark' else 'dark'
    st.query_params.pop('refresh', None)


def request_refresh():
    st.query_params['refresh'] = '1'


def choose_category(category):
    st.session_state['_news_category_saved'] = category
    st.query_params['news_category'] = category


def news_filters(items, active, categories, select):
    with st.container(key='news_filters'):
        for index, category in enumerate(['전체'] + categories):
            count = len(items) if category == '전체' else len(select(items, category))
            st.button(f'{category} · 기사 {count}개', key=f'news_filter_{index}',
                      type='primary' if category == active else 'secondary',
                      use_container_width=True, on_click=choose_category, args=(category,))


@st.cache_data(show_spinner=False)
def _stylesheet(stamp):
    return Path(__file__).with_name('ui_theme.css').read_text(encoding='utf-8')


def render_shell(view, theme):
    colors = ('#101722', '#182231', '#233247', '#eaf0f8', '#b8c5d6', '#384961') if theme == 'dark' else (
        '#f5f7fb', '#ffffff', '#edf2f8', '#202c3d', '#526277', '#dbe3ed')
    names = ('canvas', 'surface', 'soft', 'text', 'muted', 'border')
    palette = ';'.join(f'--ui-{name}:{color}' for name, color in zip(names, colors))
    sheet = Path(__file__).with_name('ui_theme.css')
    st.markdown('<style>:root{' + palette + ';color-scheme:' + theme + '}' +
                _stylesheet(sheet.stat().st_mtime_ns) + '</style>', unsafe_allow_html=True)
    with st.sidebar:
        st.markdown('### Market Risk Monitor')
        st.caption('미국 증시 위험 모니터')
        for key, label in PAGES.items():
            st.button(label, key='nav_' + key, on_click=navigate, args=(key,),
                      type='primary' if key == view else 'secondary', use_container_width=True)
        st.divider()
        st.button('라이트 모드로 전환' if theme == 'dark' else '다크 모드로 전환',
                  key='theme_toggle', on_click=toggle_theme, use_container_width=True)
        st.caption('v' + VERSION)
    # Native sidebar owns its mobile toggle; do not cover it with a fixed header.
    st.markdown(f'<div class="r38-head"><div><div class="r38-title">{PAGES[view]}</div>'
                f'<div class="r38-credit">미국 증시 위험 모니터 · v{VERSION}</div></div></div>',
                unsafe_allow_html=True)
    if view not in ('news', 'heatmap'):
        st.button('데이터 업데이트', key='data_refresh', on_click=request_refresh)
