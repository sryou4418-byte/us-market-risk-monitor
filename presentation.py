"""Display contract: finite value, unit, engine state, observation and coverage.

Observation dates are not release timestamps. Coverage describes calculable
components, never confidence/probability, and does not modify engine scores.
"""
from dataclasses import dataclass
from html import escape
from math import isfinite
import pandas as pd


def number(value):
    try:
        result = float(value)
        return result if isfinite(result) else None
    except (ValueError, TypeError):
        return None


def text(value):
    return escape(str(value))


def fmt(value, digits=1):
    value = number(value)
    return f'{value:,.{digits}f}' if value is not None else '—'


def signal_names(result):
    return [str(item[0] if isinstance(item, (list, tuple)) else item)
            for item in result.get('items', result.get('active', []))]


def tone(state):
    return {'매우 낮음':'calm','낮음':'calm','정상':'calm',
            '보통':'watch','관찰':'watch','주의':'watch',
            '높음':'alert','매우 높음':'alert','경계':'alert',
            '급변 경보':'alert','강한 스트레스':'alert','위험':'alert'}.get(state,'unknown')


@dataclass(frozen=True)
class Metric:
    title: str
    value: float | None
    unit: str
    state: str
    observed: str | None
    reason: str = ''
    release_time: str | None = None

    @classmethod
    def from_series(cls, title, series, unit='', state='참고', reason=''):
        valid = pd.to_numeric(series, errors='coerce').replace([float('inf'),-float('inf')],float('nan')).dropna()
        value = number(valid.iloc[-1]) if len(valid) else None
        observed = str(pd.Timestamp(valid.index[-1]).date()) if len(valid) else None
        return cls(title,value,unit,state if value is not None else '자료 없음',observed,reason)


def coverage(snapshot, rapid, data):
    d = snapshot['details']
    structure = (
        len((data['10년물']-data['2년물']).dropna()) >= 21,
        number(d['market'].get('valuation')) is not None,
        number(d['inflation'].get('recent')) is not None,
        number(d['economy'].get('sahm_value')) is not None and number(d['economy'].get('claims_trend')) is not None,
    )
    return {
        'risk': (sum(number(v) is not None for v in snapshot['scores'].values()), 6),
        'structure': (sum(structure), 4),
        'rapid': (sum(number(v) is not None for v in rapid['scores'].values()), 4),
    }
