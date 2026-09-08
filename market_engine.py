"""Market status v0.4. Research thresholds, not calibrated probabilities.
Observations must be point-in-time vintages for historical causal backtests.
"""
import numpy as np
import pandas as pd
import market_primitives as p

VERSION='0.4'
# All market-page indicators, including unavailable breadth, have explicit rules.
REGISTRY={}
def register(key,title,group,kind,rule,frequency='D',unit=''):
    REGISTRY[key]=dict(title=title,group=group,kind=kind,rule=rule,frequency=frequency,unit=unit)
for k,t in [('SP500','S&P500'),('NASDAQ','Nasdaq'),('RUSSELL','Russell 2000')]:
    register(k,t,'주식','equity','5일 하락 2.5/4/7%, 20일 5/8/12%, 252일 고점 낙폭 5/10/20%; 5일 하락 분포 90/97.5백분위. 최대 단계 적용; 중복 가산 없음.')
register('MA200','200일 이동평균 이격','주식','ma','하방 -3/-7/-12%, 상방 +12/+18%; 상방 과열과 하방 약화 분리.','D','%')
register('EW','동일가중 상대성과','주식','relative','RSP-SPY 20일 수익률 -2/-4/-7%p; 5일 상대성과로 지속·반전 확인.','D','%p')
register('CAPE','CAPE','주식','cape','월간 120개 이상: 과거 최대 20년 대비 80/90/97.5백분위. 12개월 변화 보조; 하락 시점 예측 금지.','M','배')
for k,t in [('ADV','상승 종목 비율'),('ABOVE200','200DMA 위 종목 비율'),('HILO','52주 신고가-신저가 비율')]:
    rule={'ADV':'동일 유니버스 상승/(상승+하락)×100의 5일평균 <45/35/25%; 20일평균으로 지속성 확인.', 'ABOVE200':'유효 200DMA 보유 구성종목 중 상회 비율 <50/40/25%; 20일 변화 -10/-20/-30%p도 평가.', 'HILO':'동일 유니버스 (신고가수-신저가수)/유효종목수×100의 5일평균 ≤-2/-5/-10%p; 20일평균 확인.'}[k]
    register(k,t,'주식','breadth',rule+' 공급원 미연결 시 확인 부족.','D','%')
register('EFFR','미국 기준금리','금리','policy','20관측 변화 25/50/100bp로 정책변화 표시; 인상·인하 분리, 물가·고용 교차확인. 절대수준 단독 위험 금지.','D','%')
for k,t in [('US3M','미국 3개월물'),('US2Y','미국 2년물'),('US10Y','미국 10년물'),('US30Y','미국 30년물'),('REAL10','미국 10년물 실질금리')]:
    register(k,t+' 국채수익률' if k!='REAL10' else t,'금리','rate','5일 절대변화 15/25/40bp, 20일 35/55/80bp, 변화 분포 90/97.5백분위; 상승·하락 분리.','D','%')
register('TERM','미국 10년물 기간프리미엄','금리','term','수준의 과거 504관측 90/97.5백분위, 20일 상승 20/40/70bp; 금리 변화와 교차확인.','D','%p')
for k,t in [('CURVE2','미국 10년물-2년물 금리차'),('CURVE3','미국 10년물-3개월물 금리차'),('CURVEFED','미국 10년물-기준금리 차')]:
    register(k,t,'금리','curve','0 미만 관찰, -1%p 이하 주의; 20일 절대변화 50/80bp; 역전 해소를 안전으로 단정하지 않음. 10Y-EFFR은 정책 상대위치 보조.','D','%p')
register('VIX','VIX','변동성','vix','수준 20/25/30, 5일 상승 20/35/60%, 20일 35/60/100%; 낮은 출발점·절대포인트 변화도 설명.')
register('VIXPOS','VIX 1년 위치','변동성','position','과거 252관측 내 위치만 표시; VIX 본지표와 중복 집계하지 않음.','D','백분위')
for k,t,rule in [('HY','하이일드 OAS','수준 4.5/6/8%p; 5일 확대 15/30/60bp, 20일 30/60/120bp'),('BBB','BBB OAS','수준 1.8/2.5/3.5%p; 5일 확대 8/15/30bp, 20일 18/35/70bp')]:
    register(k,t,'신용','credit',rule+'; 90/97.5백분위 보조; 축 수는 HY/BBB 합쳐 1개.','D','%p')
register('HYPOS','HY 1년 위치','신용','position','과거 252관측 내 위치만 표시; 신용 축에 중복 가산하지 않음.','D','백분위')
register('UNEMP','미국 실업률','경기','unemp','최근 3개월 상승 0.2/0.4/0.6%p와 Sahm 0.3/0.5/0.75%p 중 높은 단계.','M','%')
register('SAHM','Sahm Rule','경기','sahm','월간 3개월 평균-이전 12개월 3개월평균 저점; 0.30/0.50/0.75%p. 0.50만 공식 트리거, 나머지는 연구 기준.','M','%p')
register('CLAIMS','신규실업수당 4주평균','경기','claims','4주평균의 52주 저점 대비 +8/15/25%, 8주 변화 +5/10/20%; 최소 55주 관측.','W','건')
for k,t,l,m in [('CPI','CPI','3/3.5/5','3/4/6'),('CORECPI','근원 CPI','3/3.5/4.5','3/3.5/4.5'),('COREPCE','근원 PCE','2.5/3/4','2.5/3/4')]:
    register(k,t,'물가','inflation',f'YoY {l}%, 3개월 연율 {m}%; 연율이 YoY+0.5%p 이상이며 관찰기준 초과 시 재가속. YoY<0과 연율<-1 동반 시 하락압력 관찰.','M','% YoY')
# Minimum economically meaningful moves keep tiny changes from becoming alerts.
AUX_PROFILES={'GOLD':(1.5,3.0),'SILVER':(3.,6.),'COPPER':(2.,4.),'WTI':(3.,6.),'DXY':(.6,1.2),'USDKRW':(1.,2.),'USDJPY':(1.,2.)}
for k,t in [('DXY','달러지수'),('USDKRW','달러/원'),('USDJPY','달러/엔'),('WTI','WTI 원유 선물'),('GOLD','COMEX 금 선물'),('SILVER','COMEX 은 선물'),('COPPER','COMEX 구리 선물')]:
    a,b=AUX_PROFILES[k]
    register(k,t,'FX' if k in ('DXY','USDKRW','USDJPY') else '원자재','aux',f'5/20일 절대변화가 각각 {a}/{b}% 이상일 때만 과거 분포 90/97.5백분위로 관찰/주의. 5·20일 방향, 최근 5회 반복, 지표별 교차조건 병기. 단독 위험 승격 없음.')


def clean(s,asof,frequency='D'):
    if not isinstance(s,pd.Series) or not isinstance(s.index,pd.DatetimeIndex):return pd.Series(dtype=float)
    z=pd.to_numeric(s,errors='coerce').replace([np.inf,-np.inf],np.nan).dropna().copy()
    z.index=pd.to_datetime(z.index,utc=True).tz_convert(None).normalize()
    z=z.groupby(level=0).last().sort_index(); z=z.loc[z.index<=asof]
    if frequency=='M':z=z.groupby(z.index.to_period('M')).last().set_axis(z.groupby(z.index.to_period('M')).last().index.to_timestamp())
    if frequency=='W':z=z.groupby(pd.Grouper(freq='W-FRI')).last().dropna(); z=z[z.index<=asof]
    return z

def result(rank,reason,level='참고',change='참고',**meta):
    return p._ms_result_v346(p._ms_state_v346(rank),reason,level,change,meta)

def pct(s,n):
    return p._pct_ret_v02(s,n) if len(s)>n and s.iloc[-n-1]>0 else np.nan

def delta(s,n):return p._point_change_v02(s,n)

def sahm(s):
    ma=s.rolling(3).mean(); return (ma-ma.shift(1).rolling(12,min_periods=12).min()).dropna()

def percentile(s,n,kind='pct'):
    # 126 valid comparisons minimum, only earlier observations enter reference.
    mv=(s.pct_change(n,fill_method=None)*100 if kind=='pct' else s.diff(n)*100)
    h=mv.iloc[:-1].dropna().tail(504).abs()
    if len(h)<126 or not len(mv) or pd.isna(mv.iloc[-1]):return np.nan
    c=abs(mv.iloc[-1]); return float(((h<c).mean()+.5*(h==c).mean())*100)

def base(key,s):
    cfg=REGISTRY[key]; kind=cfg['kind']
    minlen={'equity':252,'ma':200,'relative':21,'cape':120,'breadth':21,'policy':21,'rate':25,'term':147,'curve':22,'vix':22,'position':127,'credit':22,'unemp':15,'sahm':1,'claims':55,'inflation':1,'aux':147}[kind]
    if len(s)<minlen:return p._ms_missing_v346(f'이력 부족: {len(s)}/{minlen}관측')
    if kind in ('equity','ma','cape','vix','claims','inflation','aux') and (s.tail(525 if kind=='aux' else 252 if kind in ('equity','ma') else 16 if kind=='inflation' else 55 if kind=='claims' else 240 if kind=='cape' else 22)<=0).any():return p._ms_missing_v346('0 이하 가격/지수: 비율 계산 보류')
    if kind=='equity':r=p._eval_equity_v346(s)
    elif kind=='ma':r=p._eval_ma200_v346(s)
    elif kind=='relative':r=p._eval_relative_v346(s.iloc[-1]); r['reason']+=f' · 5일 상대성과 {s.attrs.get("relative5",np.nan):+.2f}%p'
    elif kind=='rate':r=p._eval_rate_move_v346(s)
    elif kind=='curve':r=p._eval_curve_v346(s)
    elif kind=='credit':r=p._eval_credit_v346(s,key)
    elif kind=='vix':
        r=p._eval_vix_v346(s); r['reason']+=f' · 5일 {delta(s,5):+.1f}포인트'
    elif kind=='sahm':r=p._eval_sahm_v346(s.iloc[-1])
    elif kind=='claims':r=p._eval_claims_v346(s)
    elif kind=='unemp':
        gap=p.latest(sahm(s)); ch=delta(s,3)
        rank=max(3 if gap>=.75 else 2 if gap>=.5 else 1 if gap>=.3 else 0,3 if ch>=.6 else 2 if ch>=.4 else 1 if ch>=.2 else 0)
        r=result(rank,f'3개월 {ch:+.2f}%p · Sahm {gap:.2f}%p',change=p._ms_state_v346(rank))
    elif kind=='inflation':
        r=p._eval_inflation_v346(s,{'CPI':'CPI','CORECPI':'Core CPI','COREPCE':'Core PCE'}[key])
        if r['meta'].get('yoy',1)<0 and r['meta'].get('ann3',1)<-1:
            r=result(max(1,r['rank']),r['reason']+' · 물가 하락압력 동반',r['level'],r['change'],**r['meta'])
    elif kind=='policy':
        bp=delta(s,20)*100; rank=p._rank_fixed_v346(bp,25,50,100)
        r=result(rank,f'20관측 {bp:+.0f}bp · '+('인상' if bp>0 else '인하' if bp<0 else '유지')+' · EFFR 변화는 목표범위 결정 자체와 구분',change=p._ms_state_v346(rank))
    elif kind in ('position','cape','term'):
        window=240 if kind=='cape' else 504 if kind=='term' else 252
        h=s.iloc[:-1].tail(window); v=s.iloc[-1]; q=float(((h<v).mean()+.5*(h==v).mean())*100)
        rank=0 if kind=='position' else 3 if kind=='cape' and q>=97.5 else 2 if q>=97.5 or (kind=='cape' and q>=90) else 1 if q>=(80 if kind=='cape' else 90) else 0
        if kind=='term': rank=max(rank,3 if delta(s,20)>=.7 else 2 if delta(s,20)>=.4 else 1 if delta(s,20)>=.2 else 0)
        r=result(rank,f'과거 {len(h)}관측 대비 {q:.1f}백분위',p._ms_state_v346(rank),pctl=q)
        if kind=='cape':r['reason']+=f' · 12개월 {pct(s,12):+.1f}% · 장기 밸류에이션 부담'
        if kind=='term':r['reason']+=f' · 20일 {delta(s,20)*100:+.0f}bp'
        if kind=='position':r['state']='참고'
    elif kind=='breadth':
        if key in ('ADV','ABOVE200') and ((s<0)|(s>100)).any():return p._ms_missing_v346('비율 단위 오류: 0~100 필요')
        v=float(s.tail(5).mean()) if key!='ABOVE200' else float(s.iloc[-1])
        th={'ADV':(45,35,25),'ABOVE200':(50,40,25),'HILO':(-2,-5,-10)}[key]
        rank=sum(v<t for t in th) if key!='HILO' else sum(v<=t for t in th)
        if key=='ABOVE200': rank=max(rank,sum(delta(s,20)<=t for t in (-10,-20,-30)))
        r=result(rank,f'현재 판정값 {v:.1f}% · 20일평균 {s.tail(20).mean():.1f}%',p._ms_state_v346(rank))
    else:
        ranks=[]; moves=[]
        for n,floor in zip((5,20),AUX_PROFILES[key]):
            v=pct(s,n); q=percentile(s,n); moves.append((v,q))
            ranks.append((2 if q>=97.5 else 1 if q>=90 else 0) if abs(v)>=floor else 0)
        if any(pd.isna(q) for _,q in moves):return p._ms_missing_v346('분포 비교 이력 부족')
        rank=max(ranks); r=result(rank,f'5일 {moves[0][0]:+.2f}% · 20일 {moves[1][0]:+.2f}% · 변동성 기준 {moves[0][1]:.1f}/{moves[1][1]:.1f}백분위',change=p._ms_state_v346(rank))
    return r


def evaluate(data,asof=None):
    asof=pd.Timestamp(asof if asof is not None else pd.Timestamp.now(tz='UTC')).tz_localize(None).normalize()
    z={k:clean(data.get(k),asof,c['frequency']) for k,c in REGISTRY.items()}
    z['MA200']=z['SP500'].copy(); z['SAHM']=sahm(z['UNEMP'])
    for key,b in [('CURVE2','US2Y'),('CURVE3','US3M'),('CURVEFED','EFFR')]: z[key]=(z['US10Y']-z[b]).dropna()
    z['VIXPOS']=z['VIX'].copy(); z['HYPOS']=z['HY'].copy()
    rsp=clean(data.get('RSP'),asof); spy=clean(data.get('SPY'),asof)
    aligned=pd.concat([rsp,spy],axis=1,join='inner').dropna()
    if len(aligned)>20:
        z['EW']=(aligned.iloc[:,0].pct_change(20,fill_method=None)-aligned.iloc[:,1].pct_change(20,fill_method=None)).mul(100).dropna()
        z['EW'].attrs['relative5']=pct(aligned.iloc[:,0],5)-pct(aligned.iloc[:,1],5)
    results={}
    # Drop stale inputs before cross-confirmation: absence never becomes stability.
    for key,cfg in REGISTRY.items():
        s=z[key]; max_age={'D':7,'W':21,'M':75}[cfg['frequency']]
        stale=bool(len(s) and (asof-s.index[-1]).days>max_age)
        if cfg['frequency']=='M' and cfg['kind']!='inflation' and len(s)>=16 and len(s.tail(16).index.to_period('M').unique()) != (s.index[-1].to_period('M')-s.index[-16].to_period('M')).n+1:
            r=p._ms_missing_v346('월간 관측 누락: 달력 기간 계산 보류'); z[key]=s.iloc[:0]
        elif stale:r=p._ms_missing_v346(f'자료 지연: 마지막 관측 {s.index[-1]:%Y-%m-%d}'); z[key]=s.iloc[:0]
        elif cfg['kind']=='inflation' and not len(s):r=p._ms_missing_v346('FRED 수집 실패 또는 저장 자료 없음')
        else:r=base(key,s)
        r.update(key=key,title=cfg['title'],group=cfg['group'],rule=cfg['rule'],asof=str(asof.date()),last_observation=str(s.index[-1].date()) if len(s) else None)
        r['value']=float(s.iloc[-1]) if len(s) else np.nan
        if cfg['kind']=='inflation':r['value']=r.get('meta',{}).get('yoy',np.nan)
        if cfg['kind']=='inflation' and len(s) and (asof.to_period('M')-s.index[-1].to_period('M')).n>=2:
            r['reason']+=' · 최신 발표 대기 또는 수집 지연'
        if key=='CLAIMS':r['value']=r.get('meta',{}).get('avg4',np.nan)
        if key=='MA200':r['value']=r.get('meta',{}).get('dev',np.nan)
        if cfg['kind']=='position':r['value']=r.get('meta',{}).get('pctl',np.nan)
        r['unit']=cfg['unit']; r['evidence']=[]; r['counterevidence']=[]; r['missing']=[]
        hits=0; valid=0
        for offset in range(min(5,len(s))):
            past=s.iloc[:len(s)-offset] if offset else s
            br=base(key,past)
            if br['rank']>=0:valid+=1; hits+=int(br['rank']>=1)
        r['persistence']=f'최근 {valid}회 중 {hits}회 신호' if valid else '반복 확인 부족'
        results[key]=r
    def ok(k):return results[k]['rank']>=0
    def ret(k,n=20):return pct(z[k],n) if ok(k) else np.nan
    def ch(k,n=20):return delta(z[k],n) if ok(k) else np.nan
    axis_keys={'주식':['SP500','NASDAQ','RUSSELL','EW','ADV','ABOVE200','HILO'], '변동성':['VIX'],'신용':['HY','BBB'],'금리':['US2Y','US10Y','US30Y','REAL10','TERM'],'경기':['UNEMP','SAHM','CLAIMS'],'물가':['CPI','CORECPI','COREPCE']}
    axes={}
    for name,keys in axis_keys.items():
        valid=[k for k in keys if ok(k)]
        flagged=[k for k in valid if results[k]['rank']>=1 and (name!='금리' or ch(k)>0)]
        axes[name]=dict(available=bool(valid),active=bool(flagged),keys=flagged,valid=len(valid),expected=len(keys))
    stress=[a for a in ('주식','변동성','신용') if axes[a]['active']]
    for k,r in results.items():
        if not ok(k):r['interpretation']='현재 상태를 판단할 자료가 부족합니다.'; r['confidence']='확인 부족';continue
        group=r['group']; support=[a for a,v in axes.items() if v['active'] and a!=group]; counter=[a for a in ('주식','변동성','신용') if axes[a]['available'] and not axes[a]['active'] and a!=group]
        r['evidence']=[f'{a} 영역에도 신호' for a in support]
        r['counterevidence']=[f'{a} 영역의 동반 신호 부족' for a in counter]
        r['missing']=[f'{a} 자료 부족' for a,v in axes.items() if not v['available']]
        if k in AUX_PROFILES:
            move=ret(k); up=move>0; down=move<0
            r['evidence']=[]; r['counterevidence']=[]
            candidates=[]
            if k=='GOLD':
                if up and len(stress)>=2:candidates.append('금 상승과 여러 시장의 불안 신호가 겹쳐 안전자산 선호와 부합합니다.');r['evidence']+=stress
                if up and ch('REAL10')<=-.15 and ret('DXY')<=-1:candidates.append('실질금리 하락·달러 약세가 함께 나타나 금 보유 여건 개선과 부합합니다.');r['evidence']+=['실질금리','달러']
                if down and ch('REAL10')>=.15 and ret('DXY')>=1:candidates.append('실질금리 상승·달러 강세와 금 하락이 함께 나타납니다.');r['evidence']+=['실질금리','달러']
                if up and counter:r['counterevidence']=[f'{a} 동반 불안 없음' for a in counter]
                r['missing']+=['중앙은행 매입·ETF 수급 미연결']
            elif k in ('COPPER','WTI','SILVER'):
                if down and axes['경기']['active'] and axes['주식']['active']:candidates.append('가격 하락에 고용·주식 약화가 겹쳐 수요 둔화 가능성을 관찰합니다.');r['evidence']+=['경기','주식']
                if down and ret('DXY')>=1:candidates.append('달러 강세와 가격 하락이 동반됩니다. 수요 감소로 단정할 수 없습니다.');r['evidence']+=['달러']
                if up and ret('SP500')>=2 and (ret('COPPER')>=4 if k!='COPPER' else ret('RUSSELL')>=2):candidates.append('주식·산업 관련 가격의 상승이 동반됩니다. 수요 회복 여부는 추가 확인이 필요합니다.');r['evidence']+=['주식','산업가격']
                if k=='WTI' and up and axes['물가']['active']:candidates.append('유가 상승과 물가 부담이 겹칩니다. 유가만으로 물가 재가속 원인을 확정하지 않습니다.');r['evidence']+=['물가']
                if k=='SILVER' and up and ret('GOLD')>=3:candidates.append('금과 은이 함께 상승합니다. 귀금속 공통 흐름을 확인합니다.');r['evidence']+=['금']
                r['missing']+=['재고·생산·실물 수급 미연결: 공급 차질 원인 판정 보류']
                r['counterevidence']=[f'{a} 동반 악화 없음' for a in counter] if down else []
            elif k=='DXY':
                if up and len(stress)>=2:candidates.append('달러 강세와 시장 불안이 동반됩니다. 달러 선호 가능성을 관찰합니다.');r['evidence']+=stress
                if up and ch('US2Y')>=.15:candidates.append('미국 단기금리 상승과 달러 강세가 함께 나타납니다.');r['evidence']+=['미국 금리']
                if down and ch('US2Y')<=-.15:candidates.append('미국 단기금리 하락과 달러 약세가 함께 나타납니다.');r['evidence']+=['미국 금리']
                r['missing']+=['주요국 금리차·자금 흐름 미연결']
            else:
                dollar=ret('DXY'); same=(up and dollar>=1) or (down and dollar<=-1)
                if same:candidates.append('달러지수와 같은 방향입니다. 달러 공통 요인과 부합합니다.');r['evidence']+=['달러']
                if pd.notna(dollar) and not same:r['counterevidence']+=['달러지수의 뚜렷한 동행 없음']
                if k=='USDJPY' and down and len(stress)>=2:candidates.append('엔화 강세와 시장 불안이 동반됩니다. 캐리 청산 자체는 확인되지 않았습니다.');r['evidence']+=stress
                r['missing']+=['한국·일본 금리차/수급·정책 자료 미연결']
            if not candidates:candidates=['가격 움직임은 확인되지만 원인을 구분할 교차 근거가 충분하지 않습니다.']
            r['interpretation']=' '.join(candidates)
            if np.sign(ret(k,5))!=np.sign(move):r['counterevidence'].append('5일과 20일 방향이 달라 추세 지속성 약함')
        elif REGISTRY[k]['kind']=='position':r['interpretation']='최근 분포에서의 위치입니다. 별도 위험 신호로 중복 집계하지 않습니다.'
        elif k=='CAPE':r['interpretation']='장기 밸류에이션 부담을 봅니다. 단기 하락 시점을 알려주는 신호는 아닙니다.'
        elif k=='MA200' and r.get('meta',{}).get('dev',0)>0:r['interpretation']='이동평균 위 이격입니다. 상방 과열과 시장 하락 스트레스는 구분합니다.'
        elif group=='금리':
            d=ch(k)
            r['interpretation']=('금리 상승에 따른 부담' if d>0 else '금리 하락 또는 상대관계 변화')+'을 관찰합니다. 물가·고용·신용의 동반 움직임으로 의미를 구분합니다.'
            if k.startswith('CURVE'):r['interpretation']='역전과 기울기 변화를 관찰합니다. 역전 해소만으로 안전이나 침체를 확정하지 않습니다.'
        elif group=='경기':r['interpretation']='고용 약화 신호를 관찰합니다. 실업률과 Sahm은 같은 원자료여서 독립 증거로 중복 계산하지 않습니다.'
        elif group=='물가':r['interpretation']='연간 물가와 최근 속도를 함께 봅니다. CPI·근원 CPI·근원 PCE는 물가 한 영역으로 묶습니다.'
        else:r['interpretation']='지표 고유의 상태와 다른 시장 영역의 동반 신호를 구분해 확인합니다.'
        # This is evidence coverage, never a probability or causal certainty.
        r['confidence']='보통' if len(set(r['evidence']))>=2 and not r['counterevidence'] else '낮음'
    available=sum(axes[a]['available'] for a in ('주식','변동성','신용'))
    if available<3:sentence=f'핵심 3개 영역 중 {available}개 확인. 시장 전반 판단에는 자료가 부족합니다.'
    elif len(stress)>=2:sentence=' · '.join(stress)+'에서 동반 신호가 나타납니다. 각 지표의 현재 수준과 반복 여부를 함께 확인하세요.'
    elif len(stress)==1:sentence=stress[0]+' 영역에 신호가 있으나 다른 핵심 영역으로 확산되는지는 추가 확인이 필요합니다.'
    else:sentence='주식·변동성·신용의 동반 불안 신호는 제한적입니다. 금리·경기·물가의 부담은 별도로 확인하세요.'
    return dict(version=VERSION,results=results,axes=axes,summary=sentence,asof=str(asof.date()))

