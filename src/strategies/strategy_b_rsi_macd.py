"""Estrategia B: Relación Dinámica RSI / Histograma MACD.
Calcula correlación móvil rodante, estados de acuerdo/desacuerdo,
divergencias confirmadas causales y contrasta contra RSI Solo y MACD Solo.
"""
from dataclasses import asdict, dataclass
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from src.indicators.technical import compute_macd, compute_rsi, compute_atr
from src.backtest.engine_sma_confluence import AssetCosts

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RSIMACDParams:
    model_type: str     # "REL_AGREEMENT", "REL_DIVERGENCE", "RSI_SOLO", "MACD_SOLO", "STATIC_AGREEMENT"
    timeframe: str      # "1h", "4h"
    atr_k: float        # 2.0, 3.0
    tp_m: float         # 1.5, 2.0
    corr_window: int = 20


def compute_rsi_macd_features(df: pd.DataFrame, corr_window: int = 20) -> Dict[str, np.ndarray]:
    """Calcula características dinámicas entre RSI e Histograma MACD de forma puramente causal."""
    close = df["close"]
    high = df["high"]
    low = df["low"]

    _, _, hist = compute_macd(close, fast_period=12, slow_period=26, signal_period=9)
    rsi = compute_rsi(close, window=14)
    atr = compute_atr(high, low, close, window=14)

    # 1. Correlación móvil rodante de Pearson
    rolling_corr = rsi.rolling(window=corr_window).corr(hist).fillna(0.0).values

    # 2. Estados de acuerdo / desacuerdo
    rsi_vals = rsi.values
    hist_vals = hist.values

    agree_long = (rsi_vals > 50.0) & (hist_vals > 0.0)
    agree_short = (rsi_vals < 50.0) & (hist_vals < 0.0)
    disagree = ~agree_long & ~agree_short

    # 3. Divergencias causales con retraso n=2 barras
    n = len(df)
    close_vals = close.values
    div_long = np.zeros(n, dtype=bool)
    div_short = np.zeros(n, dtype=bool)

    # Detección causal de pivotes locales con 2 barras a izquierda y derecha
    for i in range(4, n):
        # Pivote mínimo local en i-2
        is_pivot_low = (close_vals[i-2] < close_vals[i-4]) and (close_vals[i-2] < close_vals[i-3]) and (close_vals[i-2] < close_vals[i-1]) and (close_vals[i-2] <= close_vals[i])
        if is_pivot_low:
            # Buscar pivote previo en [i-20, i-4]
            for j in range(max(2, i-20), i-3):
                is_prev_pivot_low = (close_vals[j] < close_vals[j-2]) and (close_vals[j] < close_vals[j-1]) and (close_vals[j] < close_vals[j+1]) and (close_vals[j] <= close_vals[j+2])
                if is_prev_pivot_low:
                    # Divergencia regular alcista: precio hace mínimo más bajo, pero RSI o Hist hace mínimo más alto
                    if close_vals[i-2] < close_vals[j] and (rsi_vals[i-2] > rsi_vals[j] or hist_vals[i-2] > hist_vals[j]):
                        div_long[i] = True
                    break

        # Pivote máximo local en i-2
        is_pivot_high = (close_vals[i-2] > close_vals[i-4]) and (close_vals[i-2] > close_vals[i-3]) and (close_vals[i-2] > close_vals[i-1]) and (close_vals[i-2] >= close_vals[i])
        if is_pivot_high:
            for j in range(max(2, i-20), i-3):
                is_prev_pivot_high = (close_vals[j] > close_vals[j-2]) and (close_vals[j] > close_vals[j-1]) and (close_vals[j] > close_vals[j+1]) and (close_vals[j] >= close_vals[j+2])
                if is_prev_pivot_high:
                    if close_vals[i-2] > close_vals[j] and (rsi_vals[i-2] < rsi_vals[j] or hist_vals[i-2] < hist_vals[j]):
                        div_short[i] = True
                    break

    return {
        "rsi": rsi_vals,
        "hist": hist_vals,
        "atr": atr.values,
        "rolling_corr": rolling_corr,
        "agree_long": agree_long,
        "agree_short": agree_short,
        "disagree": disagree,
        "div_long": div_long,
        "div_short": div_short,
    }


def run_rsi_macd_backtest(df: pd.DataFrame, p: RSIMACDParams, costs: AssetCosts, feats: Dict[str, np.ndarray]) -> Dict[str, Any]:
    """Ejecuta backtest causal sin look-ahead para los modelos de la Estrategia B."""
    n = len(df)
    if n < 50:
        return {"n_trades": 0, "net_pnl_usd": 0.0, "sharpe": np.nan, "win_rate": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "avg_expectancy_usd": 0.0, "trades": []}

    rsi = feats["rsi"]
    hist = feats["hist"]
    atr = feats["atr"]
    rolling_corr = feats["rolling_corr"]
    agree_l = feats["agree_long"]
    agree_s = feats["agree_short"]
    disagree = feats["disagree"]
    div_l = feats["div_long"]
    div_s = feats["div_short"]

    raw_long = np.zeros(n, dtype=bool)
    raw_short = np.zeros(n, dtype=bool)

    if p.model_type == "REL_AGREEMENT":
        # Acuerdo tras desacuerdo previo con correlación > 0.50
        for i in range(1, n):
            raw_long[i] = disagree[i-1] and agree_l[i] and (rolling_corr[i] > 0.50)
            raw_short[i] = disagree[i-1] and agree_s[i] and (rolling_corr[i] > 0.50)
    elif p.model_type == "REL_DIVERGENCE":
        # Divergencia confirmada en las últimas 5 barras + cruce o impulso
        div_l_rolling = pd.Series(div_l).rolling(5).max().values > 0
        div_s_rolling = pd.Series(div_s).rolling(5).max().values > 0
        for i in range(1, n):
            raw_long[i] = div_l_rolling[i] and (hist[i] > 0 or rsi[i] > 50)
            raw_short[i] = div_s_rolling[i] and (hist[i] < 0 or rsi[i] < 50)
    elif p.model_type == "RSI_SOLO":
        for i in range(1, n):
            raw_long[i] = (rsi[i-1] <= 50.0) and (rsi[i] > 50.0)
            raw_short[i] = (rsi[i-1] >= 50.0) and (rsi[i] < 50.0)
    elif p.model_type == "MACD_SOLO":
        for i in range(1, n):
            raw_long[i] = (hist[i-1] <= 0.0) and (hist[i] > 0.0)
            raw_short[i] = (hist[i-1] >= 0.0) and (hist[i] < 0.0)
    else: # STATIC_AGREEMENT
        raw_long = agree_l
        raw_short = agree_s

    open_arr = df["open"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    dates = df["ts_event"].values

    is_futures = (costs.asset_type == "futures")
    fixed_cost_rt = (2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier) if is_futures else 0.0

    trades = []
    pos = 0
    entry_price = 0.0
    sl_price = 0.0
    tp_price = 0.0
    entry_idx = 0

    for i in range(1, n):
        if pos != 0:
            c_high = high_arr[i]
            c_low = low_arr[i]
            c_open = open_arr[i]
            exit_reason = None
            exit_price = 0.0

            if pos == 1:
                if c_low <= sl_price:
                    exit_reason = "SL"
                    exit_price = min(c_open, sl_price)
                elif c_high >= tp_price:
                    exit_reason = "TP"
                    exit_price = max(c_open, tp_price)
                elif raw_short[i-1]:
                    exit_reason = "SIGNAL"
                    exit_price = c_open
            elif pos == -1:
                if c_high >= sl_price:
                    exit_reason = "SL"
                    exit_price = max(c_open, sl_price)
                elif c_low <= tp_price:
                    exit_reason = "TP"
                    exit_price = min(c_open, tp_price)
                elif raw_long[i-1]:
                    exit_reason = "SIGNAL"
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
                    net_ret = gross_ret - (2.0 * (costs.commission_per_side + costs.slippage_per_side))
                    net_pnl = net_ret * 10000.0
                    ret = net_ret

                trades.append({
                    "entry_date": dates[entry_idx],
                    "exit_date": dates[i],
                    "direction": pos,
                    "net_pnl_usd": net_pnl,
                    "return": ret,
                    "exit_reason": exit_reason,
                    "bars_held": holding_bars,
                })
                pos = 0

        # Entrada
        if pos == 0 and i < n - 1:
            sig_l = raw_long[i-1]
            sig_s = raw_short[i-1]
            cur_atr = atr[i-1]
            if (sig_l or sig_s) and not np.isnan(cur_atr) and cur_atr > 0:
                pos = 1 if sig_l else -1
                entry_idx = i
                entry_price = open_arr[i]
                stop_dist = p.atr_k * cur_atr
                tp_dist = p.tp_m * stop_dist
                sl_price = (entry_price - stop_dist) if pos == 1 else (entry_price + stop_dist)
                tp_price = (entry_price + tp_dist) if pos == 1 else (entry_price - tp_dist)

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
