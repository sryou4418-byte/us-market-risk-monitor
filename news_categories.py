"""Informational categories only. No risk engine or sentiment scoring."""
import re
CATEGORIES=['주요 뉴스','연준·금리','경기·고용','물가','기업·실적','기술·AI·반도체','정책·무역','지정학·에너지','한국 관련']
RULES=[
 ('지정학·에너지',r'전쟁|중동|제재|원유|유가|천연가스|에너지|opec'),
 ('정책·무역',r'관세|무역|규제|재정정책|수출통제'),
 ('연준·금리',r'연준|fomc|기준금리|국채|금리'),
 ('물가',r'물가|인플레이션|\bcpi\b|\bpce\b'),
 ('경기·고용',r'\bgdp\b|고용|실업|소비|경기침체|소매판매'),
 ('기술·AI·반도체',r'반도체|인공지능|\bai\b|엔비디아|빅테크'),
 ('기업·실적',r'실적|가이던스|매출|순이익|인수합병|기업'),
 ('한국 관련',r'한국|코스피|코스닥|원화|원.?달러|삼성|sk하이닉스'),
]
QUERIES=[('주요 뉴스','뉴욕증시 OR 미국증시 OR S&P500 when:2d'),('연준·금리','연준 OR FOMC OR 미국국채 when:3d'),('경기·고용','미국 고용 OR 미국 GDP OR 미국 소비 when:3d'),('물가','미국 CPI OR 미국 PCE OR 미국 물가 when:3d'),('기업·실적','미국 기업실적 OR 미국 가이던스 when:3d'),('기술·AI·반도체','미국 AI OR 엔비디아 OR 반도체 when:3d'),('정책·무역','미국 관세 OR 미국 규제 when:3d'),('지정학·에너지','중동 OR 국제유가 OR 미국 에너지 when:3d'),('한국 관련','원달러 OR 한국 미국증시 when:3d')]

def classify(article):
    result=dict(article);title=str(result.get('title',''))
    matches=[cat for cat,pattern in RULES if re.search(pattern,title,re.I)]
    origin=result.get('category')
    result['category']=matches[0] if matches else origin if origin in CATEGORIES else '주요 뉴스'
    result['tags']=matches[1:]
    return result

def select(items,category):
    classified=[classify(x) for x in items]
    return classified if category=='전체' else [x for x in classified if category==x['category'] or category in x['tags']]
