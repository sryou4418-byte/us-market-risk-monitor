"""Shared navigation, theme and session selection; no market calculations."""
from pathlib import Path
import streamlit as st
from app_version import VERSION

PAGES = {'dashboard':'홈', 'risk':'위험지수', 'market':'시장 상태', 'heatmap':'시장맵', 'news':'뉴스'}
ICONS = {'dashboard':':material/home:', 'risk':':material/query_stats:', 'market':':material/monitoring:', 'heatmap':':material/grid_view:', 'news':':material/article:'}
DESCRIPTIONS = {'dashboard':'오늘의 시장을 세 가지 관점으로 살펴보세요.', 'risk':'점수에서 출발해, 위험을 만든 근거까지.', 'market':'지표의 수준과 변화, 함께 나타나는 신호.', 'heatmap':'종목 비중과 등락으로 보는 시장의 흐름.', 'news':'시장 이해를 돕는 경제 뉴스. 위험점수에는 반영하지 않아요.'}


def navigate(view):
    if view not in PAGES:return
    st.query_params['view'] = view
    st.query_params.pop('refresh',None)
    if view == 'news' and st.session_state.get('_news_category_saved'):
        st.query_params['news_category'] = st.session_state['_news_category_saved']


def toggle_theme():
    st.query_params['theme'] = 'light' if st.query_params.get('theme') == 'dark' else 'dark'
    st.query_params.pop('refresh',None)


def request_refresh():
    st.query_params['refresh'] = '1'


def choose_category(category):
    st.session_state['_news_category_saved'] = category
    st.query_params['news_category'] = category


def news_filters(items, active, categories, select):
    with st.container(key='news_filters'):
        for index, category in enumerate(['전체']+categories):
            count = len(items) if category == '전체' else len(select(items,category))
            st.button(f'{category} · 기사 {count}개',key=f'news_filter_{index}',type='primary' if category == active else 'secondary',on_click=choose_category,args=(category,),use_container_width=True)


def render_shell(view,theme):
    names = ('canvas','surface','soft','text','muted','border','accent')
    colors = ('#101722','#192331','#223147','#eef4ff','#b1bfd2','#35455b','#92b6ff') if theme == 'dark' else ('#f4f7fc','#ffffff','#eaf1fc','#172b4d','#52647c','#d9e3f0','#245bd6')
    palette = ';'.join(f'--ui-{n}:{c}' for n,c in zip(names,colors))
    sheet = Path(__file__).with_name('ui_theme.css').read_text(encoding='utf-8')
    st.markdown('<style>:root{'+palette+';color-scheme:'+theme+'}'+sheet+'</style>',unsafe_allow_html=True)
    with st.container(key='brandbar'):
        st.markdown('<div class="brand"><span class="brand-mark">M</span><div>Market Monitor'+f'<small>미국 증시 위험 모니터 · v{VERSION}</small></div></div>',unsafe_allow_html=True)
        st.button('라이트 모드' if theme == 'dark' else '다크 모드',key='theme_toggle',icon=':material/light_mode:' if theme == 'dark' else ':material/dark_mode:',on_click=toggle_theme)
    with st.container(key='primary_nav'):
        for key,label in PAGES.items():
            st.button(label,key='nav_'+key,icon=ICONS[key],on_click=navigate,args=(key,),type='primary' if key == view else 'secondary',use_container_width=True)
    title = '시장 한눈에' if view == 'dashboard' else PAGES[view]
    with st.container(key='page_intro'):
        st.markdown(f'<header class="page-heading"><p class="eyebrow">US MARKET / {view.upper()}</p><h1>{title}</h1><p>{DESCRIPTIONS[view]}</p></header>',unsafe_allow_html=True)
        if view not in ('news','heatmap'):
            st.button('데이터 업데이트',key='data_refresh',icon=':material/refresh:',on_click=request_refresh)


def footer():
    st.caption(f'Market Monitor · v{VERSION} · 지표별 관측일과 발표시점은 다를 수 있습니다.')
    view = st.query_params.get('view','dashboard')
    if view not in PAGES:view='dashboard'
    if st.session_state.get('_last_rendered_view') != view:
        st.session_state['_last_rendered_view'] = view
        # Static first-party script. No parent frame, external code or user input.
        # Route changes start at the heading; filters/theme retain their position.
        st.html('''<script>
        if (!document.documentElement.dataset.marketNavigationListener) {
          document.documentElement.dataset.marketNavigationListener='1';
          document.addEventListener('click', event => {
            const button=event.target.closest('button');
            if (button && button.closest('.st-key-primary_nav, .st-key-home_risk_details, .st-key-risk_back, .st-key-home_market_details')) {
              document.documentElement.dataset.marketNavigationStart=String(performance.now());
            }
          },true);
        }
        requestAnimationFrame(() => requestAnimationFrame(() => {
          const main = document.querySelector('[data-testid="stMain"]');
          const title = document.querySelector('.page-heading h1');
          if (main) main.scrollTo({top:0,behavior:'instant'});
          if (title) {
            title.tabIndex=-1; title.focus({preventScroll:true});
            const started=Number(document.documentElement.dataset.marketNavigationStart);
            if (started) title.dataset.navigationReadyMs=(performance.now()-started).toFixed(1);
            delete document.documentElement.dataset.marketNavigationStart;
          }
        }));
        </script>''' + '<!-- '+view+' -->',unsafe_allow_javascript=True)
