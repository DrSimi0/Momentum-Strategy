"""Estrategia A: Barrido Sistemático de Medias Móviles (SMA y EMA) y Selección Top 10 por Clustering.
Totalmente determinista, sin look-ahead, con comisiones y slippage reales.
"""
from dataclasses import asdict, dataclass
import itertools
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from src.indicators.technical import compute_sma, compute_ema, compute_atr
from src.backtest.engine_sma_confluence import AssetCosts

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MAParams:
    ma_type: str        # "SMA" o "EMA"
    structure: str      # "1MA", "2MA", "3MA"
    fast_period: int    # P1 (10, 20, 30, 50)
    mid_period: int     # P2 (50, 100) solo si 3MA
    slow_period: int    # P3 (100, 150, 200)
    atr_k: float        # 2.0, 3.0
    timeframe: str      # "1h" o "4h"


def generate_ma_grid_for_timeframe(tf: str) -> List[MAParams]:
    """Genera las 112 combinaciones pre-registradas para una temporalidad dada."""
    combos = []
    ma_types = ["SMA", "EMA"]
    atr_ks = [2.0, 3.0]

    # 1. Variante 1 MA (Precio vs MA): P3 in {100, 150, 200}
    for m_type in ma_types:
        for slow in [100, 150, 200]:
            for k in atr_ks:
                combos.append(MAParams(
                    ma_type=m_type, structure="1MA",
                    fast_period=0, mid_period=0, slow_period=slow,
                    atr_k=k, timeframe=tf
                ))

    # 2. Variante 2 MAs (Cruce de 2 Medias): P1 in {10, 20, 30, 50}, P3 in {100, 150, 200} con P1 < P3
    fast_opts = [10, 20, 30, 50]
    slow_opts = [100, 150, 200]
    for m_type in ma_types:
        for fast in fast_opts:
            for slow in slow_opts:
                if fast < slow:
                    for k in atr_ks:
                        combos.append(MAParams(
                            ma_type=m_type, structure="2MA",
                            fast_period=fast, mid_period=0, slow_period=slow,
                            atr_k=k, timeframe=tf
                        ))

    # 3. Variante 3 MAs (Alineación de 3 Medias): P1 < P2 < P3 con P2 in {50, 100}
    mid_opts = [50, 100]
    for m_type in ma_types:
        for fast in fast_opts:
            for mid in mid_opts:
                if fast < mid:
                    for slow in slow_opts:
                        if mid < slow:
                            for k in atr_ks:
                                combos.append(MAParams(
                                    ma_type=m_type, structure="3MA",
                                    fast_period=fast, mid_period=mid, slow_period=slow,
                                    atr_k=k, timeframe=tf
                                ))
    return combos


def run_ma_backtest(df: pd.DataFrame, p: MAParams, costs: AssetCosts) -> Dict[str, Any]:
    """Ejecuta simulación barra por barra sin look-ahead para la Estrategia A."""
    n = len(df)
    if n < p.slow_period + 20:
        return {"n_trades": 0, "net_pnl_usd": 0.0, "sharpe": np.nan, "trades": [], "daily_returns": pd.Series()}

    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_p = df["open"]

    calc_fn = compute_ema if p.ma_type == "EMA" else compute_sma
    slow_ma = calc_fn(close, p.slow_period)

    if p.structure == "1MA":
        raw_long = (close > slow_ma).values
        raw_short = (close < slow_ma).values
    elif p.structure == "2MA":
        fast_ma = calc_fn(close, p.fast_period)
        raw_long = ((fast_ma > slow_ma) & (close > slow_ma)).values
        raw_short = ((fast_ma < slow_ma) & (close < slow_ma)).values
    else: # 3MA
        fast_ma = calc_fn(close, p.fast_period)
        mid_ma = calc_fn(close, p.mid_period)
        raw_long = ((fast_ma > mid_ma) & (mid_ma > slow_ma) & (close > fast_ma)).values
        raw_short = ((fast_ma < mid_ma) & (mid_ma < slow_ma) & (close < fast_ma)).values

    atr = compute_atr(high, low, close, 14).values
    open_arr = open_p.values
    high_arr = high.values
    low_arr = low.values
    close_arr = close.values
    dates = df["ts_event"].values

    is_futures = (costs.asset_type == "futures")
    fixed_cost_rt = (2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier) if is_futures else 0.0
    cost_pct_rt = 2.0 * (costs.commission_per_side + costs.slippage_per_side)

    trades = []
    pos = 0
    entry_price = 0.0
    sl_price = 0.0
    entry_idx = 0

    for i in range(1, n):
        # A) Evaluar salidas de la posición actual
        if pos != 0:
            c_high = high_arr[i]
            c_low = low_arr[i]
            c_open = open_arr[i]
            c_close = close_arr[i]
            exit_reason = None
            exit_price = 0.0

            if pos == 1:
                if c_low <= sl_price:
                    exit_reason = "SL"
                    exit_price = min(c_open, sl_price)
                elif raw_short[i - 1]: # Señal contraria generada al cierre de i-1
                    exit_reason = "REVERSAL"
                    exit_price = c_open
            elif pos == -1:
                if c_high >= sl_price:
                    exit_reason = "SL"
                    exit_price = max(c_open, sl_price)
                elif raw_long[i - 1]:
                    exit_reason = "REVERSAL"
                    exit_price = c_open

            if exit_reason:
                holding_bars = i - entry_idx
                if is_futures:
                    gross_pnl = ((exit_price - entry_price) if pos == 1 else (entry_price - exit_price)) * costs.multiplier
                    net_pnl = gross_pnl - fixed_cost_rt
                    notional = entry_price * costs.multiplier
                    ret = net_pnl / notional if notional > 0 else 0.0
                else:
                    gross_ret = (exit_price / entry_price - 1.0) if pos == 1 else (1.0 - exit_price / entry_price)
                    funding = costs.funding_rate_8h * (holding_bars / 2.0 if p.timeframe == "4h" else holding_bars / 8.0)
                    net_ret = gross_ret - cost_pct_rt - funding
                    net_pnl = net_ret * 10000.0
                    ret = net_ret

                trades.append({
                    "entry_date": dates[entry_idx],
                    "exit_date": dates[i],
                    "direction": pos,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "net_pnl_usd": net_pnl,
                    "return": ret,
                    "exit_reason": exit_reason,
                    "bars_held": holding_bars,
                })
                pos = 0

        # B) Evaluar entrada en apertura de i si la señal cerró en i-1
        if pos == 0 and i < n - 1:
            sig_l = raw_long[i - 1]
            sig_s = raw_short[i - 1]
            cur_atr = atr[i - 1]
            if (sig_l or sig_s) and not np.isnan(cur_atr) and cur_atr > 0:
                pos = 1 if sig_l else -1
                entry_idx = i
                entry_price = open_arr[i]
                stop_dist = p.atr_k * cur_atr
                sl_price = (entry_price - stop_dist) if pos == 1 else (entry_price + stop_dist)

    n_trades = len(trades)
    if n_trades == 0:
        return {"n_trades": 0, "net_pnl_usd": 0.0, "sharpe": np.nan, "win_rate": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "avg_expectancy_usd": 0.0, "trades": []}

    pnls = np.array([t["net_pnl_usd"] for t in trades])
    rets = np.array([t["return"] for t in trades])
    total_net_pnl = float(np.sum(pnls))
    win_rate = float(np.mean(pnls > 0))
    avg_expectancy = float(np.mean(pnls))

    pos_sum = float(np.sum(pnls[pnls > 0]))
    neg_sum = float(np.abs(np.sum(pnls[pnls < 0])))
    pf = (pos_sum / neg_sum) if neg_sum > 0 else np.nan

    mean_ret = float(np.mean(rets))
    std_ret = float(np.std(rets, ddof=1)) if n_trades > 1 else 0.0
    sharpe = float((mean_ret / std_ret) * np.sqrt(costs.annualization_factor)) if n_trades >= 30 and std_ret > 1e-9 else np.nan

    cum_pnl = np.cumsum(pnls)
    peaks = np.maximum.accumulate(cum_pnl)
    dd = peaks - cum_pnl
    max_dd = float(np.max(dd)) if len(dd) > 0 else 0.0

    return {
        "n_trades": n_trades,
        "net_pnl_usd": total_net_pnl,
        "sharpe": sharpe,
        "win_rate": win_rate,
        "profit_factor": pf,
        "max_drawdown": max_dd,
        "avg_expectancy_usd": avg_expectancy,
        "trades": trades,
    }
