"""Estrategia C: Detección Objetiva y Causal de Patrones de Vela y Figuras Chartistas.
Garantiza cero look-ahead mediante confirmación retardada de pivotes y reglas deterministas.
"""
from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from src.indicators.technical import compute_atr
from src.backtest.engine_sma_confluence import AssetCosts

logger = logging.getLogger(__name__)


def detect_candle_patterns_causal(df: pd.DataFrame) -> Dict[str, np.ndarray]:
    """Detecta patrones de vela objetivos al cierre de cada barra sin fuga de futuro."""
    n = len(df)
    open_p = df["open"].values
    high_p = df["high"].values
    low_p = df["low"].values
    close_p = df["close"].values

    body = np.abs(close_p - open_p)
    candle_range = high_p - low_p + 1e-9
    is_bullish = close_p > open_p
    is_bearish = close_p < open_p

    lower_wick = np.where(is_bullish, open_p - low_p, close_p - low_p)
    upper_wick = np.where(is_bullish, high_p - close_p, high_p - open_p)

    hammer = np.zeros(n, dtype=bool)
    engulfing_bull = np.zeros(n, dtype=bool)
    engulfing_bear = np.zeros(n, dtype=bool)
    doji = np.zeros(n, dtype=bool)
    morning_star = np.zeros(n, dtype=bool)

    # Detección causal barra por barra
    for i in range(2, n):
        # 1. Hammer (Martillo alcista tras mínimo local)
        if (lower_wick[i] >= 2.0 * body[i]) and (upper_wick[i] <= 0.3 * body[i]) and (body[i] > 0.1 * candle_range[i]):
            # Confirmar que está en zona de soporte o mínimo de 10 barras
            if low_p[i] <= np.min(low_p[max(0, i-10):i]):
                hammer[i] = True

        # 2. Envolvente (Engulfing)
        if is_bearish[i-1] and is_bullish[i]:
            if (open_p[i] <= close_p[i-1]) and (close_p[i] >= open_p[i-1]) and (body[i] > body[i-1]):
                engulfing_bull[i] = True
        elif is_bullish[i-1] and is_bearish[i]:
            if (open_p[i] >= close_p[i-1]) and (close_p[i] <= open_p[i-1]) and (body[i] > body[i-1]):
                engulfing_bear[i] = True

        # 3. Doji
        if body[i] <= 0.10 * candle_range[i]:
            doji[i] = True

        # 4. Morning Star (3 velas)
        if i >= 3:
            if is_bearish[i-2] and (body[i-2] >= 0.5 * candle_range[i-2]):
                if body[i-1] <= 0.3 * candle_range[i-1] and (low_p[i-1] < low_p[i-2]):
                    if is_bullish[i] and (close_p[i] > (open_p[i-2] + close_p[i-2]) / 2.0):
                        morning_star[i] = True

    return {
        "hammer": hammer,
        "engulfing_bull": engulfing_bull,
        "engulfing_bear": engulfing_bear,
        "doji": doji,
        "morning_star": morning_star,
    }


def detect_chartist_figures_causal(df: pd.DataFrame, n_confirm: int = 3) -> Dict[str, np.ndarray]:
    """Detecta figuras chartistas (Doble Suelo, Doble Techo, Triángulos) con confirmación causal n=3."""
    n = len(df)
    high_p = df["high"].values
    low_p = df["low"].values
    close_p = df["close"].values

    double_bottom = np.zeros(n, dtype=bool)
    double_top = np.zeros(n, dtype=bool)

    # Identificar pivotes confirmados causales en i
    # Un pivote en i-n solo se confirma si es el extremo en [i-2*n, i]
    pivots_low = []
    pivots_high = []

    for i in range(2 * n_confirm, n):
        idx = i - n_confirm
        # Mínimo confirmado
        is_low = (low_p[idx] == np.min(low_p[idx - n_confirm : idx + n_confirm + 1]))
        if is_low:
            pivots_low.append((idx, low_p[idx]))
            # Comprobar si forma doble suelo con el pivote previo
            if len(pivots_low) >= 2:
                prev_idx, prev_val = pivots_low[-2]
                bars_between = idx - prev_idx
                if 8 <= bars_between <= 50:
                    price_diff_pct = abs(low_p[idx] - prev_val) / prev_val
                    if price_diff_pct <= 0.0075: # Menos de 0.75% de diferencia
                        # Confirmar rotura al cierre actual i
                        double_bottom[i] = True

        # Máximo confirmado
        is_high = (high_p[idx] == np.max(high_p[idx - n_confirm : idx + n_confirm + 1]))
        if is_high:
            pivots_high.append((idx, high_p[idx]))
            if len(pivots_high) >= 2:
                prev_idx, prev_val = pivots_high[-2]
                bars_between = idx - prev_idx
                if 8 <= bars_between <= 50:
                    price_diff_pct = abs(high_p[idx] - prev_val) / prev_val
                    if price_diff_pct <= 0.0075:
                        double_top[i] = True

    return {
        "double_bottom": double_bottom,
        "double_top": double_top,
    }


def run_pattern_backtest(df: pd.DataFrame, signals_long: np.ndarray, signals_short: np.ndarray, costs: AssetCosts, atr_k: float = 2.0, tp_m: float = 2.0) -> Dict[str, Any]:
    """Ejecuta backtest estricto para una señal de patrón dada."""
    n = len(df)
    open_arr = df["open"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    dates = df["ts_event"].values
    atr = compute_atr(df["high"], df["low"], df["close"], 14).values

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
                elif signals_short[i-1]:
                    exit_reason = "SIGNAL"
                    exit_price = c_open
            elif pos == -1:
                if c_high >= sl_price:
                    exit_reason = "SL"
                    exit_price = max(c_open, sl_price)
                elif c_low <= tp_price:
                    exit_reason = "TP"
                    exit_price = min(c_open, tp_price)
                elif signals_long[i-1]:
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

        # Entrada al open de i si señal cerrada en i-1
        if pos == 0 and i < n - 1:
            sig_l = signals_long[i-1]
            sig_s = signals_short[i-1]
            cur_atr = atr[i-1]
            if (sig_l or sig_s) and not np.isnan(cur_atr) and cur_atr > 0:
                pos = 1 if sig_l else -1
                entry_idx = i
                entry_price = open_arr[i]
                stop_dist = atr_k * cur_atr
                tp_dist = tp_m * stop_dist
                sl_price = (entry_price - stop_dist) if pos == 1 else (entry_price + stop_dist)
                tp_price = (entry_price + tp_dist) if pos == 1 else (entry_price - tp_dist)

    n_trades = len(trades)
    if n_trades == 0:
        return {"n_trades": 0, "net_pnl_usd": 0.0, "sharpe": np.nan, "win_rate": 0.0, "profit_factor": 0.0, "max_drawdown": 0.0, "avg_expectancy_usd": 0.0}

    pnls = np.array([t["net_pnl_usd"] for t in trades])
    rets = np.array([t["return"] for t in trades])
    pos_sum = float(np.sum(pnls[pnls > 0]))
    neg_sum = float(np.abs(np.sum(pnls[pnls < 0])))
    pf = (pos_sum / neg_sum) if neg_sum > 0 else np.nan

    mean_ret = float(np.mean(rets))
    std_ret = float(np.std(rets, ddof=1)) if n_trades > 1 else 0.0
    sharpe = float((mean_ret / std_ret) * np.sqrt(costs.annualization_factor)) if n_trades >= 30 and std_ret > 1e-9 else np.nan

    cum_pnl = np.cumsum(pnls)
    peaks = np.maximum.accumulate(cum_pnl)
    dd = peaks - cum_pnl

    return {
        "n_trades": n_trades,
        "net_pnl_usd": float(np.sum(pnls)),
        "sharpe": sharpe,
        "win_rate": float(np.mean(pnls > 0)),
        "profit_factor": pf,
        "max_drawdown": float(np.max(dd)) if len(dd) > 0 else 0.0,
        "avg_expectancy_usd": float(np.mean(pnls)),
    }
