"""Estrategia Cuantitativa Unificada: EMA 30/200 + MACD/RSI Momentum + Price Action Causal.
Garantiza cero look-ahead: señal al cierre de la vela t, ejecución en la apertura de t+1.
"""
from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from src.indicators.technical import compute_ema, compute_macd, compute_rsi, compute_atr
from src.strategies.strategy_c_patterns import detect_candle_patterns_causal
from src.backtest.engine_sma_confluence import AssetCosts

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UnifiedStrategyParams:
    fast_ema: int = 30
    slow_ema: int = 200
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    rsi_period: int = 14
    rsi_long_min: float = 45.0
    rsi_long_max: float = 75.0
    rsi_short_min: float = 25.0
    rsi_short_max: float = 55.0
    atr_period: int = 14
    atr_k: float = 3.0
    tp_m: float = 2.0
    long_only: bool = True
    use_candle_trigger: bool = True


def generate_unified_signals(
    df: pd.DataFrame,
    params: UnifiedStrategyParams,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Genera señales booleanas al cierre de cada vela t sin fuga de información futura."""
    n = len(df)
    close_p = df["close"]
    
    # 1. Medias Móviles (Estrategia A)
    ema_fast = compute_ema(close_p, params.fast_ema).values
    ema_slow = compute_ema(close_p, params.slow_ema).values
    
    # 2. Momentum (Estrategia B)
    _, _, macd_hist = compute_macd(close_p, params.macd_fast, params.macd_slow, params.macd_signal)
    hist_val = macd_hist.values
    rsi_val = compute_rsi(close_p, params.rsi_period).values
    
    # 3. Volatilidad
    atr_val = compute_atr(df["high"], df["low"], close_p, params.atr_period).values
    
    # 4. Gatillos de Acción del Precio (Estrategia C)
    candle_pats = detect_candle_patterns_causal(df)
    hammer = candle_pats["hammer"]
    engulfing_bull = candle_pats["engulfing_bull"]
    engulfing_bear = candle_pats["engulfing_bear"]

    sig_long = np.zeros(n, dtype=bool)
    sig_short = np.zeros(n, dtype=bool)

    min_warmup = max(params.slow_ema, params.macd_slow + params.macd_signal, params.rsi_period, 20)
    close_arr = close_p.values

    for t in range(min_warmup, n):
        c_p = close_arr[t]
        ef = ema_fast[t]
        es = ema_slow[t]
        h = hist_val[t]
        r = rsi_val[t]

        if np.isnan(ef) or np.isnan(es) or np.isnan(h) or np.isnan(r):
            continue

        # Condiciones Long
        regime_long = (ef > es) and (c_p > es)
        momentum_long = (h > 0) and (params.rsi_long_min <= r <= params.rsi_long_max)
        if params.use_candle_trigger:
            trigger_long = bool(hammer[t] or engulfing_bull[t])
        else:
            trigger_long = (ema_fast[t] > ema_slow[t] and ema_fast[t-1] <= ema_slow[t-1]) or (h > 0 and hist_val[t-1] <= 0)

        if regime_long and momentum_long and trigger_long:
            sig_long[t] = True

        # Condiciones Short (si no es Long Only)
        if not params.long_only:
            regime_short = (ef < es) and (c_p < es)
            momentum_short = (h < 0) and (params.rsi_short_min <= r <= params.rsi_short_max)
            if params.use_candle_trigger:
                trigger_short = bool(engulfing_bear[t])
            else:
                trigger_short = (ema_fast[t] < ema_slow[t] and ema_fast[t-1] >= ema_slow[t-1]) or (h < 0 and hist_val[t-1] >= 0)

            if regime_short and momentum_short and trigger_short:
                sig_short[t] = True

    return sig_long, sig_short, atr_val


def run_unified_backtest(
    df: pd.DataFrame,
    params: UnifiedStrategyParams,
    costs: AssetCosts,
) -> Dict[str, Any]:
    """Ejecuta simulación retrospectiva con deducción de costos transaccionales reales."""
    sig_long, sig_short, atr_val = generate_unified_signals(df, params)
    
    n = len(df)
    open_arr = df["open"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    close_arr = df["close"].values
    dates = df["ts_event"].values

    is_futures = (costs.asset_type == "futures")
    fixed_cost_rt = (2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier) if is_futures else 0.0

    trades = []
    pos = 0 # 1: Long, -1: Short, 0: Flat
    entry_price = 0.0
    sl_price = 0.0
    tp_price = 0.0
    entry_idx = 0

    ema_fast = compute_ema(df["close"], params.fast_ema).values
    ema_slow = compute_ema(df["close"], params.slow_ema).values

    for i in range(1, n):
        # 1. Gestión de posición abierta en barra i
        if pos != 0:
            c_high = high_arr[i]
            c_low = low_arr[i]
            c_open = open_arr[i]
            exit_reason = None
            exit_price = 0.0

            if pos == 1:
                # Comprobar SL y TP
                if c_low <= sl_price:
                    exit_reason = "SL"
                    exit_price = min(c_open, sl_price)
                elif c_high >= tp_price:
                    exit_reason = "TP"
                    exit_price = max(c_open, tp_price)
                # Salida por cruce contrario de medias o señal short contraria
                elif (ema_fast[i-1] < ema_slow[i-1]) or sig_short[i-1]:
                    exit_reason = "SIGNAL_FLIP"
                    exit_price = c_open
            elif pos == -1:
                if c_high >= sl_price:
                    exit_reason = "SL"
                    exit_price = max(c_open, sl_price)
                elif c_low <= tp_price:
                    exit_reason = "TP"
                    exit_price = min(c_open, tp_price)
                elif (ema_fast[i-1] > ema_slow[i-1]) or sig_long[i-1]:
                    exit_reason = "SIGNAL_FLIP"
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
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "net_pnl_usd": net_pnl,
                    "return": ret,
                    "exit_reason": exit_reason,
                    "bars_held": holding_bars,
                })
                pos = 0

        # 2. Apertura causal de posición en el open de i si hubo señal en i-1
        if pos == 0 and i < n - 1:
            s_long = sig_long[i-1]
            s_short = sig_short[i-1]
            cur_atr = atr_val[i-1]

            if (s_long or s_short) and not np.isnan(cur_atr) and cur_atr > 0:
                pos = 1 if s_long else -1
                entry_idx = i
                entry_price = open_arr[i]
                stop_dist = params.atr_k * cur_atr
                tp_dist = params.tp_m * stop_dist

                sl_price = (entry_price - stop_dist) if pos == 1 else (entry_price + stop_dist)
                tp_price = (entry_price + tp_dist) if pos == 1 else (entry_price - tp_dist)

    n_trades = len(trades)
    if n_trades == 0:
        return {
            "n_trades": 0,
            "net_pnl_usd": 0.0,
            "sharpe": np.nan,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "avg_expectancy_usd": 0.0,
            "trades": [],
        }

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
        "trades": trades,
    }
