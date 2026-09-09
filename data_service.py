"""Provider adapters and disk cache, bound to one explicit store instance.
No UI dependencies. A background job retains its originating store and paths.
"""
import pandas as pd
import numpy as np
import requests, csv, os, shutil, json, time, re, html
from pathlib import Path as _Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from urllib.parse import quote
from news_categories import QUERIES

class MarketStore:

    def __init__(self):
        self.FRED_CSV = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id={}'
        self.FRED_RECENT = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id={}&cosd={}'
        self.SERIES = {'기준금리': 'EFFR', '3개월물': 'DGS3MO', '2년물': 'DGS2', '10년물': 'DGS10', '30년물': 'DGS30', '10년물기간프리미엄': 'THREEFYTP10', '10년물실질금리': 'DFII10', '하이일드스프레드': 'BAMLH0A0HYM2', 'BBB스프레드': 'BAMLC0A4CBBB', 'CPI': 'CPIAUCSL', '근원CPI': 'CPILFESL', '근원PCE': 'PCEPILFE', '실업률': 'UNRATE', '신규실업수당': 'ICSA', 'S&P500': 'SP500', 'VIX': 'VIXCLS'}
        self.CANONICAL_DATA = {'EFFR': {'internal': '기준금리', 'provider': 'FRED', 'symbol': 'EFFR'}, 'US3M': {'internal': '3개월물', 'provider': 'FRED+TREASURY', 'symbol': 'DGS3MO'}, 'US2Y': {'internal': '2년물', 'provider': 'FRED+TREASURY', 'symbol': 'DGS2'}, 'US10Y': {'internal': '10년물', 'provider': 'FRED+TREASURY', 'symbol': 'DGS10'}, 'US30Y': {'internal': '30년물', 'provider': 'FRED+TREASURY', 'symbol': 'DGS30'}, 'SP500': {'internal': 'S&P500', 'provider': 'FRED', 'symbol': 'SP500'}, 'VIX': {'internal': 'VIX', 'provider': 'FRED', 'symbol': 'VIXCLS'}, 'HY_OAS': {'internal': '하이일드스프레드', 'provider': 'FRED', 'symbol': 'BAMLH0A0HYM2'}, 'UNEMP': {'internal': '실업률', 'provider': 'FRED', 'symbol': 'UNRATE'}, 'CPI': {'internal': 'CPI', 'provider': 'FRED', 'symbol': 'CPIAUCSL'}}
        self.ROOT_CACHE = _Path(os.environ.get('LOCALAPPDATA', str(_Path.home()))) / 'RiskMonitor'
        self.CACHE_DIR = self.ROOT_CACHE / 'data'
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.RECENT_DAYS = 1000
        self.REFRESH_STATUS = self.ROOT_CACHE / 'refresh_status.json'
        self.FX_CACHE = self.ROOT_CACHE / 'fx_snapshot.json'
        self.CAPE_CACHE = self.ROOT_CACHE / 'cape.csv'
        self.HEATMAP_CACHE = self.ROOT_CACHE / 'sp500_market_map_200.json'
        self.HEATMAP_SECTOR_CACHE = self.ROOT_CACHE / 'sp500_sector_map.json'
        self.HEATMAP_TTL_SECONDS = 600
        self.HEATMAP_SECTOR_TTL_SECONDS = 86400
        self.HEATMAP_TARGET_COUNT = 200
        self.SLICKCHARTS_SP500_URL = 'https://www.slickcharts.com/sp500'
        self.WIKI_SP500_URL = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        self.SECTOR_KO = {'Information Technology': '정보기술', 'Communication Services': '커뮤니케이션', 'Consumer Discretionary': '경기소비재', 'Financials': '금융', 'Health Care': '헬스케어', 'Industrials': '산업재', 'Consumer Staples': '필수소비재', 'Energy': '에너지', 'Utilities': '유틸리티', 'Real Estate': '부동산', 'Materials': '소재'}
        self.FALLBACK_SECTOR = {'NVDA': '정보기술', 'AAPL': '정보기술', 'MSFT': '정보기술', 'AVGO': '정보기술', 'ORCL': '정보기술', 'AMD': '정보기술', 'CSCO': '정보기술', 'IBM': '정보기술', 'CRM': '정보기술', 'QCOM': '정보기술', 'AMAT': '정보기술', 'TXN': '정보기술', 'ADI': '정보기술', 'MU': '정보기술', 'NOW': '정보기술', 'PLTR': '정보기술', 'LRCX': '정보기술', 'KLAC': '정보기술', 'GOOGL': '커뮤니케이션', 'GOOG': '커뮤니케이션', 'META': '커뮤니케이션', 'NFLX': '커뮤니케이션', 'TMUS': '커뮤니케이션', 'DIS': '커뮤니케이션', 'T': '커뮤니케이션', 'VZ': '커뮤니케이션', 'CMCSA': '커뮤니케이션', 'AMZN': '경기소비재', 'TSLA': '경기소비재', 'HD': '경기소비재', 'MCD': '경기소비재', 'BKNG': '경기소비재', 'TJX': '경기소비재', 'LOW': '경기소비재', 'SBUX': '경기소비재', 'NKE': '경기소비재', 'MAR': '경기소비재', 'UBER': '경기소비재', 'JPM': '금융', 'V': '금융', 'MA': '금융', 'BAC': '금융', 'WFC': '금융', 'GS': '금융', 'MS': '금융', 'AXP': '금융', 'C': '금융', 'BLK': '금융', 'SCHW': '금융', 'SPGI': '금융', 'CB': '금융', 'BRK.B': '금융', 'COF': '금융', 'PGR': '금융', 'LLY': '헬스케어', 'JNJ': '헬스케어', 'ABBV': '헬스케어', 'UNH': '헬스케어', 'MRK': '헬스케어', 'TMO': '헬스케어', 'ABT': '헬스케어', 'ISRG': '헬스케어', 'DHR': '헬스케어', 'PFE': '헬스케어', 'AMGN': '헬스케어', 'GILD': '헬스케어', 'VRTX': '헬스케어', 'BMY': '헬스케어', 'SYK': '헬스케어', 'CVS': '헬스케어', 'GE': '산업재', 'CAT': '산업재', 'RTX': '산업재', 'UNP': '산업재', 'HON': '산업재', 'ETN': '산업재', 'DE': '산업재', 'LMT': '산업재', 'UPS': '산업재', 'BA': '산업재', 'PH': '산업재', 'GEV': '산업재', 'WMT': '필수소비재', 'COST': '필수소비재', 'PG': '필수소비재', 'KO': '필수소비재', 'PEP': '필수소비재', 'PM': '필수소비재', 'MO': '필수소비재', 'MDLZ': '필수소비재', 'XOM': '에너지', 'CVX': '에너지', 'COP': '에너지', 'EOG': '에너지', 'SLB': '에너지', 'MPC': '에너지', 'NEE': '유틸리티', 'CEG': '유틸리티', 'SO': '유틸리티', 'DUK': '유틸리티', 'WELL': '부동산', 'PLD': '부동산', 'AMT': '부동산', 'LIN': '소재', 'SHW': '소재', 'FCX': '소재', 'NEM': '소재'}
        self.NEWS_CACHE = self.ROOT_CACHE / 'korean_econ_news.json'
        self.NEWS_TTL_SECONDS = 600
        self.NEWS_QUERIES = QUERIES
        self.CAPE_URL = 'https://www.multpl.com/shiller-pe/table/by-month'
        self.SERIES_TTL_SECONDS = {'EFFR': 1800, 'DGS3MO': 1800, 'DGS2': 1800, 'DGS10': 1800, 'DGS30': 1800, 'SP500': 1800, 'VIXCLS': 1800, 'BAMLH0A0HYM2': 3600, 'BAMLC0A4CBBB': 3600, 'THREEFYTP10': 21600, 'ICSA': 21600, 'CPIAUCSL': 43200, 'CPILFESL': 43200, 'PCEPILFE': 43200, 'UNRATE': 43200}
        self.FX_TTL_SECONDS = 600
        self.CAPE_TTL_SECONDS = 86400
        self.TREASURY_TTL_SECONDS = 1800
        self.AUTO_REFRESH_CHECK_SECONDS = 600
        self._migrate_legacy_cache()
        self.INFLATION_SERIES = {'CPIAUCSL', 'CPILFESL', 'PCEPILFE'}

    def canonical_series(self, data, key):
        meta = self.CANONICAL_DATA.get(key, {})
        return data.get(meta.get('internal', ''), pd.Series(dtype=float))

    def _table_rows(self, html):
        from html.parser import HTMLParser

        class Parser(HTMLParser):

            def __init__(self):
                super().__init__(convert_charrefs=True)
                self.in_cell = False
                self.cell = []
                self.row = []
                self.rows = []

            def handle_starttag(self, tag, attrs):
                if tag == 'tr':
                    self.row = []
                elif tag in ('td', 'th'):
                    self.in_cell = True
                    self.cell = []

            def handle_data(self, data):
                if self.in_cell:
                    self.cell.append(data)

            def handle_endtag(self, tag):
                if tag in ('td', 'th') and self.in_cell:
                    self.row.append(' '.join(''.join(self.cell).split()))
                    self.in_cell = False
                elif tag == 'tr' and self.row:
                    self.rows.append(self.row)
        p = Parser()
        p.feed(html)
        return p.rows

    def _http_text(self, url, timeout=(3, 8)):
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.9'}
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.text

    def _read_heatmap_cache(self):
        try:
            return json.loads(self.HEATMAP_CACHE.read_text(encoding='utf-8'))
        except Exception:
            return {'updated': 0, 'items': []}

    def _read_sector_cache(self):
        try:
            return json.loads(self.HEATMAP_SECTOR_CACHE.read_text(encoding='utf-8'))
        except Exception:
            return {'updated': 0, 'map': {}}

    def _write_json_atomic(self, path, obj):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + '.tmp')
            tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')
            tmp.replace(path)
            return True
        except Exception:
            return False

    def _heatmap_cache_fresh(self):
        return self._file_fresh(self.HEATMAP_CACHE, self.HEATMAP_TTL_SECONDS)

    def _sector_cache_fresh(self):
        return self._file_fresh(self.HEATMAP_SECTOR_CACHE, self.HEATMAP_SECTOR_TTL_SECONDS)

    def _fetch_sector_map(self, force=False):
        cached = self._read_sector_cache()
        if not force and self._sector_cache_fresh() and cached.get('map'):
            return cached.get('map', {})
        mapping = dict(cached.get('map', {}))
        try:
            rows = self._table_rows(self._http_text(self.WIKI_SP500_URL, timeout=(3, 8)))
            found = {}
            for row in rows:
                if len(row) < 3:
                    continue
                sym = row[0].strip()
                sec = row[2].strip()
                if sec in self.SECTOR_KO and 1 <= len(sym) <= 8:
                    found[sym] = self.SECTOR_KO[sec]
                    found[sym.replace('-', '.')] = self.SECTOR_KO[sec]
            if found:
                mapping.update(found)
                self._write_json_atomic(self.HEATMAP_SECTOR_CACHE, {'updated': time.time(), 'map': mapping})
        except Exception:
            pass
        for k, v in self.FALLBACK_SECTOR.items():
            mapping.setdefault(k, v)
        return mapping

    def _pct(self, s):
        try:
            return float(str(s).replace('%', '').replace(',', '').strip())
        except Exception:
            return np.nan

    def _num(self, s):
        import re
        s = str(s).replace(',', '').replace('$', '').strip()
        try:
            return float(s)
        except Exception:
            m = re.search('(-?\\d+(?:\\.\\d+)?)', s)
            return float(m.group(1)) if m else np.nan

    def _fetch_slickcharts_top200(self, force=False):
        cached = self._read_heatmap_cache()
        if not force and self._heatmap_cache_fresh() and cached.get('items'):
            return cached
        sector_map = self._fetch_sector_map(force=False)
        try:
            rows = self._table_rows(self._http_text(self.SLICKCHARTS_SP500_URL, timeout=(3, 9)))
            parsed = []
            for row in rows:
                if len(row) < 7:
                    continue
                rank_txt = row[0].replace('#', '').strip()
                if not rank_txt.isdigit():
                    continue
                rank = int(rank_txt)
                company = row[1].strip()
                symbol = row[2].strip()
                weight = self._pct(row[3])
                price = self._num(row[4])
                change_pct = self._pct(row[6])
                if rank < 1 or not symbol or (not np.isfinite(weight)):
                    continue
                sector = sector_map.get(symbol) or sector_map.get(symbol.replace('-', '.')) or self.FALLBACK_SECTOR.get(symbol) or '기타'
                parsed.append({'rank': rank, 'symbol': symbol, 'name': company, 'weight': weight, 'price': price, 'change': change_pct, 'sector': sector, 'stale': False})
            parsed = sorted(parsed, key=lambda x: x['rank'])[:self.HEATMAP_TARGET_COUNT]
            if len(parsed) >= 150:
                snap = {'updated': time.time(), 'source': 'Slickcharts (SPY holdings-based weight)', 'items': parsed}
                self._write_json_atomic(self.HEATMAP_CACHE, snap)
                return snap
            raise ValueError(f'parsed only {len(parsed)} rows')
        except Exception:
            if cached.get('items'):
                cached = dict(cached)
                cached['stale'] = True
                for q in cached.get('items', []):
                    q['stale'] = True
                return cached
            return {'updated': 0, 'source': 'unavailable', 'items': [], 'stale': True}

    def _read_news_cache(self):
        try:
            return json.loads(self.NEWS_CACHE.read_text(encoding='utf-8'))
        except Exception:
            return {'updated': 0, 'items': []}

    def _news_cache_fresh(self):
        return self._file_fresh(self.NEWS_CACHE, self.NEWS_TTL_SECONDS)

    def _clean_news_title(self, title, source=''):
        title = ' '.join(str(title or '').split())
        if source:
            suffix = ' - ' + source.strip()
            if title.endswith(suffix):
                title = title[:-len(suffix)].rstrip()
        return title

    def _fetch_google_news_rss(self, label, query):
        import xml.etree.ElementTree as ET
        from email.utils import parsedate_to_datetime
        q = quote(query, safe='')
        url = f'https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko'
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=(3, 8))
        r.raise_for_status()
        root = ET.fromstring(r.content)
        out = []
        for item in root.findall('.//item')[:18]:
            title = item.findtext('title') or ''
            link = item.findtext('link') or ''
            pub = item.findtext('pubDate') or ''
            sn = item.find('source')
            source = (sn.text or '').strip() if sn is not None else ''
            title = self._clean_news_title(title, source)
            if not title or not link:
                continue
            try:
                dt = parsedate_to_datetime(pub)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                published = dt.timestamp()
            except Exception:
                published = 0
            out.append({'category': label, 'title': title, 'source': source or 'Google News', 'link': link, 'published': published})
        return out

    def _fetch_news_snapshot(self, force=False):
        cached = self._read_news_cache()
        if not force and self._news_cache_fresh() and cached.get('items'):
            return cached
        items = []
        errors = []
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(self._fetch_google_news_rss, l, q): l for l, q in self.NEWS_QUERIES}
            for fut in as_completed(futs):
                try:
                    items.extend(fut.result())
                except Exception as e:
                    errors.append(str(e))
        seen = set()
        clean = []
        for q in sorted(items, key=lambda z: float(z.get('published', 0)), reverse=True):
            k = ' '.join(q.get('title', '').lower().split())
            if not k or k in seen:
                continue
            seen.add(k)
            clean.append(q)
        if clean:
            snap = {'updated': time.time(), 'items': clean[:144], 'errors': errors, 'source': 'Google News RSS'}
            self._write_json_atomic(self.NEWS_CACHE, snap)
            return snap
        if cached.get('items'):
            cached = dict(cached)
            cached['stale'] = True
            return cached
        return {'updated': 0, 'items': [], 'stale': True}

    def _file_fresh(self, path, ttl):
        try:
            return time.time() - path.stat().st_mtime < ttl
        except Exception:
            return False

    def _series_fresh(self, sid):
        return self._file_fresh(self._cache_file(sid), self.SERIES_TTL_SECONDS.get(sid, 3600))

    def _auto_refresh_due(self):
        if not self.FX_CACHE.exists() or not self.CAPE_CACHE.exists():
            return True
        if not self.REFRESH_STATUS.exists():
            return True
        try:
            return time.time() - self.REFRESH_STATUS.stat().st_mtime >= self.AUTO_REFRESH_CHECK_SECONDS
        except Exception:
            return True

    def _migrate_legacy_cache(self):
        if any(self.CACHE_DIR.glob('*.csv')):
            return
        base = _Path(os.environ.get('LOCALAPPDATA', str(_Path.home())))
        for old_name in ('RiskMonitor_3_25_0', 'RiskMonitor_3_24_0', 'RiskMonitor_3_23_0'):
            old = base / old_name / 'data'
            if old.exists():
                for f in old.glob('*.csv'):
                    try:
                        shutil.copy2(f, self.CACHE_DIR / f.name)
                    except Exception:
                        pass
                break

    def _parse_fred(self, text, series):
        from io import StringIO
        lines = text.lstrip('\ufeff').splitlines()
        header = next((i for i, line in enumerate(lines[:30]) if 'observation_date' in next(csv.reader([line])) and series in next(csv.reader([line]))), None)
        if header is None:
            raise ValueError(f'{series}: FRED CSV 헤더 없음')
        df = pd.read_csv(StringIO('\n'.join(lines[header:])), usecols=['observation_date', series], dtype=str)
        df['date'] = pd.to_datetime(df['observation_date'], errors='coerce')
        df[series] = pd.to_numeric(df[series], errors='coerce')
        df = df.dropna(subset=['date', series]).drop_duplicates('date', keep='first').sort_values('date')
        if df.empty:
            raise ValueError(f'{series}: 유효 데이터 없음')
        return df.set_index('date')[series].astype(float)

    def _fetch(self, series, recent=False):
        if recent:
            since = (pd.Timestamp.now().normalize() - pd.Timedelta(days=self.RECENT_DAYS)).strftime('%Y-%m-%d')
            url = self.FRED_RECENT.format(series, since)
        else:
            url = self.FRED_CSV.format(series)
        r = requests.get(url, timeout=(3, 10))
        r.raise_for_status()
        return self._parse_fred(r.text, series)

    def _cache_file(self, series):
        return self.CACHE_DIR / f'{series}.csv'

    def _read_cache(self, series):
        f = self._cache_file(series)
        if not f.exists():
            return pd.Series(dtype=float)
        try:
            df = pd.read_csv(f, parse_dates=['date'])
            if 'value' not in df:
                return pd.Series(dtype=float)
            return pd.Series(df['value'].astype(float).values, index=pd.DatetimeIndex(df['date'])).dropna().sort_index()
        except Exception:
            return pd.Series(dtype=float)

    def _write_cache(self, series, s):
        if s is None or not len(s):
            return
        tmp = self._cache_file(series).with_suffix('.tmp')
        pd.DataFrame({'date': s.index, 'value': s.values}).to_csv(tmp, index=False)
        tmp.replace(self._cache_file(series))

    def _merge_and_write(self, series, new):
        old = self._read_cache(series)
        merged = pd.concat([old, new]).groupby(level=0).last().sort_index() if len(old) else new.sort_index()
        self._write_cache(series, merged)
        return merged

    def _recent_month_gaps(self, s, months=16):
        if s is None or not len(s):
            return []
        z = s.dropna().copy()
        z.index = pd.to_datetime(z.index).to_period('M')
        last = z.index.max()
        expected = pd.period_range(last - months + 1, last, freq='M')
        present = set(z.index)
        return [str(x) for x in expected if x not in present]

    def _treasury_latest(self):
        year = pd.Timestamp.now().year
        url = f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
        r = requests.get(url, headers=headers, timeout=(3, 6))
        r.raise_for_status()
        rows = list(csv.DictReader(r.text.lstrip('\ufeff').splitlines()))
        parsed = []
        for row in rows:
            d = pd.to_datetime(row.get('Date'), errors='coerce')
            if pd.isna(d):
                continue
            vals = {}
            for col, key in (('3 Mo', 'DGS3MO'), ('2 Yr', 'DGS2'), ('10 Yr', 'DGS10'), ('30 Yr', 'DGS30')):
                v = pd.to_numeric(row.get(col), errors='coerce')
                if pd.notna(v):
                    vals[key] = float(v)
            if vals:
                parsed.append((d, vals))
        if not parsed:
            raise ValueError('Treasury 최신 금리 데이터 없음')
        return max(parsed, key=lambda x: x[0])

    def _read_all_cache(self):
        out = {}
        for name, sid in self.SERIES.items():
            s = self._read_cache(sid)
            if name == '기준금리' and (not len(s)):
                legacy = self._read_cache('FEDFUNDS')
                if len(legacy):
                    s = legacy
            out[name] = s
        return out

    def _initial_fetch(self):
        out = {}
        errors = []

        def one(item):
            name, sid = item
            try:
                s = self._fetch(sid, recent=True)
                self._write_cache(sid, s)
                return (name, s, None)
            except Exception as e:
                return (name, pd.Series(dtype=float), f'{name} ({sid}): {e}')
        with ThreadPoolExecutor(max_workers=10) as ex:
            required = {'기준금리', '2년물', '10년물', '하이일드스프레드', 'CPI', '실업률', 'S&P500', 'VIX'}
            ordered = sorted(self.SERIES.items(), key=lambda item: item[0] not in required)
            futures = [ex.submit(one, x) for x in ordered]
            for f in as_completed(futures):
                name, s, err = f.result()
                out[name] = s
                if err:
                    errors.append(err)
        return (out, errors)

    def _refresh_series(self, name, sid, force=False):
        try:
            cached = self._read_cache(sid)
            if len(cached) and (not force) and self._series_fresh(sid):
                return (name, cached, None)
            new = self._fetch(sid, recent=bool(len(cached)))
            merged = self._merge_and_write(sid, new)
            if sid in self.INFLATION_SERIES and self._recent_month_gaps(merged):
                merged = self._merge_and_write(sid, self._fetch(sid, recent=False))
            return (name, merged, None)
        except Exception as e:
            return (name, self._read_cache(sid), f'{name}: {e}')

    def _fetch_yahoo_symbol(self, ticker):
        enc = quote(ticker, safe='')
        headers = {'User-Agent': 'Mozilla/5.0'}
        attempts = [('query1.finance.yahoo.com', '5d', '1m'), ('query2.finance.yahoo.com', '5d', '5m'), ('query1.finance.yahoo.com', '1mo', '15m'), ('query2.finance.yahoo.com', '1mo', '1d')]
        last_error = None
        for host, rng, interval in attempts:
            try:
                url = f'https://{host}/v8/finance/chart/{enc}?range={rng}&interval={interval}&includePrePost=false'
                r = requests.get(url, headers=headers, timeout=(3, 6))
                r.raise_for_status()
                result = r.json().get('chart', {}).get('result') or []
                if not result:
                    raise ValueError(f'{ticker}: Yahoo 데이터 없음')
                row = result[0]
                meta = row.get('meta', {})
                closes = [float(x) for x in row.get('indicators', {}).get('quote', [{}])[0].get('close') or [] if x is not None]
                cur = meta.get('regularMarketPrice')
                if cur is None and closes:
                    cur = closes[-1]
                prev = meta.get('chartPreviousClose', meta.get('previousClose'))
                if prev is None and len(closes) >= 2:
                    prev = closes[-2]
                if cur is None:
                    raise ValueError(f'{ticker}: 현재값 없음')
                return {'value': float(cur), 'prev': float(prev) if prev is not None else np.nan, 'time': time.time(), 'spark': closes[-60:], 'stale': False, 'interval': interval}
            except Exception as e:
                last_error = e
        raise ValueError(f'{ticker}: Yahoo 요청 실패 ({last_error})')

    def _refresh_fx(self, force=False):
        if not force and self._file_fresh(self.FX_CACHE, self.FX_TTL_SECONDS):
            return []
        tickers = {'원/달러': 'USDKRW=X', '엔/달러': 'USDJPY=X', '달러인덱스': 'DX-Y.NYB', 'WTI 유가': 'CL=F'}
        previous = self._read_fx().get('items', {})
        snap = {'updated': time.time(), 'source': 'Yahoo Finance', 'items': dict(previous)}
        errors = []
        successes = 0
        with ThreadPoolExecutor(max_workers=4) as ex:
            futs = {ex.submit(self._fetch_yahoo_symbol, t): name for name, t in tickers.items()}
            for f, name in [(f, n) for f, n in futs.items()]:
                try:
                    snap['items'][name] = f.result()
                    successes += 1
                except Exception as e:
                    errors.append(f'{name}: {e}')
                    if name in snap['items']:
                        snap['items'][name] = dict(snap['items'][name])
                        snap['items'][name]['stale'] = True
        if snap['items']:
            self.ROOT_CACHE.mkdir(parents=True, exist_ok=True)
            tmp = self.FX_CACHE.with_suffix('.tmp')
            tmp.write_text(json.dumps(snap, ensure_ascii=False), encoding='utf-8')
            tmp.replace(self.FX_CACHE)
        return errors

    def _read_fx(self):
        try:
            return json.loads(self.FX_CACHE.read_text(encoding='utf-8'))
        except Exception:
            return {'items': {}}

    def _read_cape(self):
        if not self.CAPE_CACHE.exists():
            return pd.Series(dtype=float)
        try:
            df = pd.read_csv(self.CAPE_CACHE, parse_dates=['date'])
            if 'cape' not in df:
                return pd.Series(dtype=float)
            out = pd.Series(pd.to_numeric(df['cape'], errors='coerce').values, index=pd.DatetimeIndex(df['date'])).dropna()
            return out[~out.index.duplicated(keep='last')].sort_index()
        except Exception:
            return pd.Series(dtype=float)

    def _refresh_cape(self, force=False):
        if not force and self._file_fresh(self.CAPE_CACHE, self.CAPE_TTL_SECONDS):
            return True
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36'}
        r = requests.get(self.CAPE_URL, headers=headers, timeout=(3, 7))
        r.raise_for_status()
        rows = re.findall('<tr[^>]*>\\s*<td[^>]*>(.*?)</td>\\s*<td[^>]*>(.*?)</td>\\s*</tr>', r.text, re.I | re.S)
        rec = []
        for d_raw, v_raw in rows:
            d_txt = re.sub('<[^>]+>', '', html.unescape(d_raw)).strip()
            v_txt = re.sub('<[^>]+>', '', html.unescape(v_raw)).replace('\xa0', '').strip()
            d = pd.to_datetime(d_txt, errors='coerce')
            v = pd.to_numeric(v_txt.replace(',', ''), errors='coerce')
            if pd.notna(d) and pd.notna(v):
                rec.append((d, float(v)))
        if len(rec) < 100:
            raise ValueError('CAPE 월별 표 파싱 실패')
        df = pd.DataFrame(rec, columns=['date', 'cape']).drop_duplicates('date', keep='last').sort_values('date')
        tmp = self.CAPE_CACHE.with_suffix('.tmp')
        df.to_csv(tmp, index=False)
        tmp.replace(self.CAPE_CACHE)
        return True

    def _write_refresh_status(self, ok, errors):
        self.ROOT_CACHE.mkdir(parents=True, exist_ok=True)
        payload = {'finished': time.time(), 'ok': bool(ok), 'errors': errors[:10]}
        tmp = self.REFRESH_STATUS.with_suffix('.tmp')
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        tmp.replace(self.REFRESH_STATUS)

    def _refresh_all_background(self, force=False):
        errors = []
        priority = [('기준금리', 'EFFR'), ('3개월물', 'DGS3MO'), ('2년물', 'DGS2'), ('10년물', 'DGS10'), ('30년물', 'DGS30')]
        need_treasury = force or not self._file_fresh(self._cache_file('DGS10'), self.TREASURY_TTL_SECONDS)
        with ThreadPoolExecutor(max_workers=6) as ex:
            fs = [ex.submit(self._refresh_series, *x, force) for x in priority]
            fx_future = ex.submit(self._refresh_fx, force)
            cape_future = ex.submit(self._refresh_cape, force)
            treasury_future = ex.submit(self._treasury_latest) if need_treasury else None
            for f in fs:
                _, _, err = f.result()
                if err:
                    errors.append(err)
            try:
                errors.extend(fx_future.result())
            except Exception as e:
                errors.append(f'환율: {e}')
            try:
                cape_future.result()
            except Exception as e:
                errors.append(f'CAPE: {e}')
            if treasury_future is not None:
                try:
                    d, vals = treasury_future.result()
                    for sid, v in vals.items():
                        self._merge_and_write(sid, pd.Series([v], index=pd.DatetimeIndex([d]), dtype=float))
                except Exception as e:
                    errors.append(f'미 재무부 최신 금리: {e}')
        rest = [x for x in self.SERIES.items() if x not in priority]
        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = [ex.submit(self._refresh_series, *x, force) for x in rest]
            for f in as_completed(futures):
                _, _, err = f.result()
                if err:
                    errors.append(err)
        self._write_refresh_status(not errors, errors)

    def _status_mtime(self):
        try:
            return self.REFRESH_STATUS.stat().st_mtime
        except Exception:
            return 0.0

    def _cache_ready(self, data):
        required = ('기준금리', '2년물', '10년물', '하이일드스프레드', 'CPI', '실업률', 'S&P500', 'VIX')
        return all((len(data.get(k, pd.Series(dtype=float)).dropna()) for k in required))
