"""Streamlit entry point: route, session state, loading status and view composition."""
import json
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from data_service import MarketStore
from loading_service import start as start_job, status as job_status
from market_loader import load as load_aux
from ui_shell import render_shell, footer, navigate, PAGES
from risk_service import report as risk_report

st.set_page_config(page_title='미국 증시 위험 모니터',page_icon='📊',layout='wide')
view=str(st.query_params.get('view','dashboard'))
if view not in PAGES:view='dashboard'
theme='dark' if st.query_params.get('theme')=='dark' else 'light'
render_shell(view,theme)
store=MarketStore()

if view in ('news','heatmap'):
    from news_view import render as render_news
    from heatmap_view import render as render_map
    is_news=view=='news'
    path=store.NEWS_CACHE if is_news else store.HEATMAP_CACHE
    reader=store._read_news_cache if is_news else store._read_heatmap_cache
    fresh=store._news_cache_fresh if is_news else store._heatmap_cache_fresh
    def load_light():
        value=store._fetch_news_snapshot(force=True) if is_news else store._fetch_slickcharts_top200(force=True)
        if value.get('stale') or not value.get('items'):raise ValueError('수집 실패')
    manual=not is_news and st.button('시장맵 업데이트',key='light_refresh349',icon=':material/refresh:')
    if manual or not fresh():start_job(path,load_light,cooldown=0 if manual else 30)
    st.query_params.pop('refresh',None)
    # Periodic fragment also retries a failed/empty first load, without a full-page reload.
    @st.fragment(run_every='30s')
    def light_content():
        if not fresh():start_job(path,load_light,cooldown=30)
        snapshot=reader();state=job_status(path)
        if snapshot.get('items'):
            if is_news:render_news(st,snapshot['items'])
            else:render_map(st,snapshot,theme)
            updated=snapshot.get('updated',0)
            stamp=datetime.fromtimestamp(updated,ZoneInfo('Asia/Seoul')).strftime('%m.%d %H:%M KST')
            st.caption('마지막 수집 '+stamp+(' · 갱신 확인 중' if state.get('running') else ''))
        elif state.get('running'):st.info('데이터를 처음 준비하고 있어요. 완료 후 자동으로 표시합니다.')
        else:st.warning('자료를 가져오지 못했습니다. 잠시 후 자동으로 다시 확인합니다.')
        if state.get('error'):st.caption('새 자료 수집 실패 · 저장된 자료를 유지합니다.')
    light_content()
    footer()
    st.stop()

key=store.ROOT_CACHE/'core_refresh'
manual=str(st.query_params.get('refresh','0'))=='1'
if manual:
    st.query_params.pop('refresh',None)
    start_job(key,lambda:store._refresh_all_background(force=True),cooldown=5)

def get_data():
    stamp=(str(store.ROOT_CACHE),store._status_mtime())
    if st.session_state.get('_market_data_stamp')!=stamp or job_status(key).get('running'):
        st.session_state['_market_data_mem']=store._read_all_cache()
        st.session_state['_market_data_stamp']=stamp
    return st.session_state['_market_data_mem']

data=get_data()
if not store._cache_ready(data):
    def bootstrap():
        _,errors=store._initial_fetch()
        store._write_refresh_status(not errors,errors)
    if not job_status(key) or st.button('데이터 다시 받기',key='bootstrap_retry348'):
        start_job(key,bootstrap,cooldown=5)
    st.button('뉴스 먼저 보기',key='bootstrap_news',on_click=navigate,args=('news',))
    st.button('시장맵 먼저 보기',key='bootstrap_heatmap',on_click=navigate,args=('heatmap',))
    @st.fragment(run_every='2s')
    def progress():
        current=store._read_all_cache()
        ready=sum(bool(len(s)) for s in current.values())
        st.info(f'처음 실행할 데이터를 준비하고 있어요. {ready}/{len(store.SERIES)}개 준비')
        if store._cache_ready(current):
            st.session_state.pop('_market_data_stamp',None)
            st.rerun()
        if not job_status(key).get('running'):st.warning('필수 자료가 부족합니다. 데이터 다시 받기를 눌러 주세요.')
    progress();footer();st.stop()

if store._auto_refresh_due():start_job(key,lambda:store._refresh_all_background(force=False),cooldown=30)
baseline=store._status_mtime()
polling=job_status(key).get('running',False)
@st.fragment(run_every='2s' if polling else None)
def refresh_status():
    if polling and (store._status_mtime()>baseline or not job_status(key).get('running')):
        st.session_state.pop('_market_data_stamp',None);st.rerun()
    if job_status(key).get('running'):st.caption('저장된 자료 표시 중 · 새 자료 확인 중…')
    else:
        try:
            status=json.loads(store.REFRESH_STATUS.read_text(encoding='utf-8'))
            stamp=datetime.fromtimestamp(status['finished'],ZoneInfo('Asia/Seoul')).strftime('%m.%d %H:%M KST')
            st.caption(('마지막 수집 확인 ' if status.get('ok',False) else '일부 자료 수집 미확인 · 마지막 시도 ')+stamp)
        except (OSError,ValueError,KeyError):st.caption('저장된 자료 표시 · 수집 완료 시각 확인 불가')
refresh_status()
cape=store._read_cape()
asof=str(pd.Timestamp.now(tz='UTC').date())
if view=='market':
    from market_view import render
    aux,state,_=load_aux(store.ROOT_CACHE/'market_aux_v348.json')
    if state.get('running'):
        @st.fragment(run_every='2s')
        def aux_progress():
            if not job_status(store.ROOT_CACHE/'market_aux_v348.json').get('running'):st.rerun()
            st.caption('보조지표를 갱신하고 있어요.')
        aux_progress()
    mapping={'SP500':'S&P500','US3M':'3개월물','US2Y':'2년물','US10Y':'10년물','US30Y':'30년물','EFFR':'기준금리','REAL10':'10년물실질금리','TERM':'10년물기간프리미엄','HY':'하이일드스프레드','BBB':'BBB스프레드','VIX':'VIX','UNEMP':'실업률','CLAIMS':'신규실업수당','CPI':'CPI','CORECPI':'근원CPI','COREPCE':'근원PCE'}
    market_data=dict(aux)
    market_data.update({k:data[v] for k,v in mapping.items()});market_data['CAPE']=cape
    render(st,market_data,asof)
else:
    report=risk_report(data,cape,asof)
    if view=='dashboard':
        from dashboard_view import render
        render(st,report=report,data=data,navigate=navigate)
    else:
        from risk_view import render
        render(st,report,data,cape,navigate)
footer()
