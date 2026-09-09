"""Orchestrate the existing engine with an explicit observation cutoff."""
import pandas as pd
import numpy as np
from risk_engine import (compute_snapshot, fast_signal_scores, rapid_alert,
                         structural_signals, apply_risk_floors, delta_value)
from presentation import coverage
from data_contract import normalize_series


def report(data, cape, asof):
    cutoff = pd.Timestamp(asof)
    data = {k:normalize_series(v).loc[:cutoff] for k,v in data.items()}
    cape = normalize_series(cape).loc[:cutoff]
    sp, vix = data['S&P500'], data['VIX']
    snapshot = compute_snapshot(data,cape)
    previous = None
    prev_fast = {}
    if len(sp) >= 2:
        previous_date = sp.index[-2]
        prior = {k:v.loc[:previous_date].dropna() for k,v in data.items()}
        previous = compute_snapshot(prior,cape.loc[:previous_date],with_alerts=False)
        prev_fast = fast_signal_scores(previous['details'])
    rapid = rapid_alert(fast_signal_scores(snapshot['details']),prev_fast)
    final, floors = apply_risk_floors(snapshot['overall'],snapshot['structure'],rapid,
                                     sp,vix,rapid['scores'].get('신용',np.nan))
    prev_final = np.nan
    if previous is not None:
        structure = structural_signals(previous['details'],(prior['10년물']-prior['2년물']).dropna())
        prev_final,_ = apply_risk_floors(previous['overall'],structure,rapid_alert(prev_fast,{}),
                                        prior['S&P500'],prior['VIX'],prev_fast.get('신용',np.nan))
    return dict(snapshot, final=final, floors=floors, rapid=rapid, previous=prev_final,
                delta=delta_value(final,prev_final)[1], coverage=coverage(snapshot,rapid,data),
                asof=str(cutoff.date()))
