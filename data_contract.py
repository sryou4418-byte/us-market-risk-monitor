"""Canonical dated numeric series; no filling or guessed release timestamps."""
import pandas as pd
import numpy as np


def normalize_series(series):
    if series is None or not len(series):
        return pd.Series(dtype=float,index=pd.DatetimeIndex([]))
    if not isinstance(series.index,(pd.DatetimeIndex,pd.PeriodIndex)):
        raise ValueError('관측일을 가진 시계열이 필요합니다.')
    index=series.index.to_timestamp() if isinstance(series.index,pd.PeriodIndex) else series.index
    # Daily date labels preserve the provider calendar date, not an inferred release time.
    if index.tz is not None:index=index.tz_localize(None)
    result=pd.Series(pd.to_numeric(series,errors='coerce').to_numpy(),index=index)
    result=result[~result.index.isna()].replace([np.inf,-np.inf],np.nan).dropna()
    return result[~result.index.duplicated(keep='last')].sort_index()
