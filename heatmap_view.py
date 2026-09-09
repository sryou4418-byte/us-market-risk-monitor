import html, math, time
import numpy as np
HEATMAP_TARGET_COUNT = 200
from datetime import datetime
from zoneinfo import ZoneInfo
SECTOR_KO = {'Information Technology': '정보기술', 'Communication Services': '커뮤니케이션', 'Consumer Discretionary': '경기소비재', 'Financials': '금융', 'Health Care': '헬스케어', 'Industrials': '산업재', 'Consumer Staples': '필수소비재', 'Energy': '에너지', 'Utilities': '유틸리티', 'Real Estate': '부동산', 'Materials': '소재'}
def _esc(x): return html.escape(str(x))
def _heat_color(change,dark=False):
    if not np.isfinite(change):
        return "#313844" if dark else "#e7ebf0"
    mag=min(abs(float(change)),5.0)/5.0
    if change>0:
        lo=(86,35,40) if dark else (255,238,239)
        hi=(210,47,58) if dark else (229,59,70)
    elif change<0:
        lo=(27,48,77) if dark else (235,243,255)
        hi=(43,104,190) if dark else (47,112,201)
    else:
        return "#313844" if dark else "#eef1f4"
    rgb=tuple(round(lo[i]+(hi[i]-lo[i])*mag) for i in range(3))
    return "#%02x%02x%02x"%rgb


def _heat_text_color(change,dark=False):
    if dark:
        return "#f7f9fc"
    if np.isfinite(change) and abs(float(change))>=2.2:
        return "#ffffff"
    return "#17202b"


def _split_rect(items,x,y,w,h):
    if not items:
        return []
    if len(items)==1:
        return [(items[0],x,y,w,h)]
    total=sum(max(float(i[2]),0.0001) for i in items)
    target=total/2.0
    acc=0.0
    cut=1
    for idx,it in enumerate(items[:-1],1):
        acc+=max(float(it[2]),0.0001)
        if acc>=target:
            cut=idx
            break
    a,b=items[:cut],items[cut:]
    wa=sum(max(float(i[2]),0.0001) for i in a)
    ratio=wa/total if total else 0.5
    out=[]
    if w>=h:
        w1=w*ratio
        out.extend(_split_rect(a,x,y,w1,h))
        out.extend(_split_rect(b,x+w1,y,w-w1,h))
    else:
        h1=h*ratio
        out.extend(_split_rect(a,x,y,w,h1))
        out.extend(_split_rect(b,x,y+h1,w,h-h1))
    return out


def _heatmap_html(snapshot,dark=False):
    items=[q for q in snapshot.get("items",[])[:HEATMAP_TARGET_COUNT] if float(q.get("weight",0) or 0)>0]
    if not items:
        return ""

    sector_totals={}
    for q in items:
        sec=q.get("sector") or "기타"
        sector_totals[sec]=sector_totals.get(sec,0.0)+float(q.get("weight",0) or 0)

    sector_items=[(sec,sec,w) for sec,w in sorted(sector_totals.items(),key=lambda kv:kv[1],reverse=True)]
    sector_rects=_split_rect(sector_items,0,0,100,100)
    rect_map={sec:(x,y,w,h) for (sec,_,_),x,y,w,h in sector_rects}

    blocks=[]
    valid_changes=[]
    for sector,_ in sorted(sector_totals.items(),key=lambda kv:kv[1],reverse=True):
        sx,sy,sw,sh=rect_map[sector]
        rows=[q for q in items if (q.get("sector") or "기타")==sector]
        row_by_symbol={q["symbol"]:q for q in rows}
        inner=[(q["symbol"],q["name"],float(q["weight"])) for q in sorted(rows,key=lambda q:float(q.get("weight",0) or 0),reverse=True)]
        rects=_split_rect(inner,sx,sy,sw,sh)
        sec_changes=[]
        for (sym,name,weight),x,y,w,h in rects:
            q=row_by_symbol.get(sym,{})
            ch=float(q.get("change",np.nan))
            if np.isfinite(ch):
                valid_changes.append(ch)
                sec_changes.append(ch)
            price=float(q.get("price",np.nan))
            bg=_heat_color(ch,dark)
            fg=_heat_text_color(ch,dark)
            change_txt=f"{ch:+.2f}%" if np.isfinite(ch) else "N/A"
            weight_txt=f"{weight:.3f}%"
            price_txt=f"${price:,.2f}" if np.isfinite(price) else "N/A"
            area=w*h
            cls=" lg" if area>=190 else (" md" if area>=70 else (" sm" if area>=24 else " xs"))
            stale_txt=" · 지연" if q.get("stale") or snapshot.get("stale") else ""
            blocks.append(
                f'<div class="tm-tile{cls}" tabindex="0" role="button" '
                f'data-symbol="{_esc(sym)}" data-name="{_esc(name)}" data-change="{_esc(change_txt)}" '
                f'data-weight="{_esc(weight_txt)}" data-price="{_esc(price_txt)}" '
                f'style="left:{x:.4f}%;top:{y:.4f}%;width:{w:.4f}%;height:{h:.4f}%;background:{bg};color:{fg}" '
                f'title="{_esc(sym)} · {_esc(name)} · {change_txt} · 비중 {weight_txt}">'
                f'<div class="tm-symbol">{_esc(sym)}</div>'
                f'<div class="tm-change">{_esc(change_txt)}</div>'
                f'<div class="tm-name">{_esc(name)}{stale_txt}</div>'
                f'</div>'
            )

        blocks.append(
            f'<div class="tm-sector-outline" '
            f'style="left:{sx:.4f}%;top:{sy:.4f}%;width:{sw:.4f}%;height:{sh:.4f}%"></div>'
        )
        if sw*sh>=120:
            avg=float(np.mean(sec_changes)) if sec_changes else np.nan
            avg_txt=f"{avg:+.2f}%" if np.isfinite(avg) else ""
            blocks.append(
                f'<div class="tm-sector-label" style="left:{sx:.4f}%;top:{sy:.4f}%">'
                f'{_esc(sector)} <span>{_esc(avg_txt)}</span></div>'
            )

    up=sum(1 for x in valid_changes if x>0)
    down=sum(1 for x in valid_changes if x<0)
    flat=len(valid_changes)-up-down
    source_note="저장된 종목 비중"
    return (
        '<div class="hm-summary">'
        f'<div><strong>S&amp;P500 시장 맵 · {len(items)}종목</strong>'
        f'<span>타일 면적 = {source_note} · 색상 = 일간 등락률</span></div>'
        f'<div class="hm-breadth">상승 {up} · 하락 {down} · 보합 {flat}</div>'
        '</div>'
        '<div class="tm-help">작은 타일은 텍스트를 생략합니다. 타일을 누르면 종목 상세가 표시됩니다. '
        '모바일에서는 전체 맵을 화면 폭에 맞춰 한눈에 보이도록 축소합니다. 작은 종목은 텍스트를 생략하고 큰 타일 위주로 표시합니다.</div>'
        f'<div class="tm-viewport"><div class="tm-wrap">{"".join(blocks)}</div></div>'
    )



def render(st,snapshot,theme):
    from pathlib import Path
    from presentation import fmt,text
    sheet=Path(__file__).with_name('heatmap.css').read_text(encoding='utf-8')
    st.markdown('<style>'+sheet+'</style>',unsafe_allow_html=True)
    st.markdown(_heatmap_html(snapshot,dark=theme=='dark'),unsafe_allow_html=True)
    st.subheader('종목 찾아보기')
    def save_search():st.session_state['_map_search_saved']=st.session_state['map_search']
    query=st.text_input('종목명 또는 심볼 검색',key='map_search',value=st.session_state.get('_map_search_saved',''),placeholder='예: AAPL, Apple',on_change=save_search)
    rows=[]
    for q in snapshot.get('items',[]):
        if query.casefold() not in (q.get('symbol','')+' '+q.get('name','')).casefold():continue
        rows.append(f'<article class="market-row"><div><strong>{text(q.get("symbol",""))}</strong><small>{text(q.get("name",""))}</small></div><div class="market-value">{fmt(q.get("price"),2)} USD</div><span>{fmt(q.get("change"),2)}%</span><small class="reason">{text(q.get("sector",""))} · 비중 {fmt(q.get("weight"),3)}%</small></article>')
    if rows:st.markdown('<div class="indicator-list">'+''.join(rows)+'</div>',unsafe_allow_html=True)
    else:st.info('검색 결과가 없습니다.')
