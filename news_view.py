"""News selection and presentation, isolated from financial calculations."""
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlparse
import streamlit as st
from news_categories import CATEGORIES,select
from ui_shell import news_filters
from presentation import text


def render(st,items):
    category=str(st.query_params.get('news_category','전체'))
    if category not in ['전체']+CATEGORIES:category='전체'
    news_filters(items,category,CATEGORIES,select)
    def save_search():st.session_state['_news_search_saved']=st.session_state['news_search']
    query=st.text_input('뉴스 제목 검색',key='news_search',value=st.session_state.get('_news_search_saved',''),placeholder='찾고 싶은 키워드를 입력하세요',on_change=save_search)
    chosen=[q for q in select(items,category) if query.casefold() in q.get('title','').casefold()]
    st.caption(f'{category} · {len(chosen)}개 기사 · 제목 기반 분류')
    cards=[]
    for q in chosen:
        link=q.get('link','')
        if urlparse(link).scheme not in ('http','https'):link=''
        timestamp=q.get('published',0)
        date=datetime.fromtimestamp(timestamp,ZoneInfo('Asia/Seoul')).strftime('%m.%d %H:%M') if timestamp else '시각 미확인'
        title=text(q.get('title','제목 없음'))
        headline=f'<a class="news-title" href="{text(link)}" target="_blank" rel="noopener noreferrer">{title}</a>' if link else f'<div class="news-title">{title}</div>'
        cards.append(f'<article class="news-card"><div class="news-meta"><span class="news-category">{text(q.get("category",""))}</span><span>{text(q.get("source",""))}</span><span>{date}</span></div>{headline}<div class="news-go">원문 읽기 ↗</div></article>')
    if cards:st.markdown('<div class="news-list">'+''.join(cards)+'</div>',unsafe_allow_html=True)
    else:st.info('선택한 조건에 맞는 기사가 없습니다.')
