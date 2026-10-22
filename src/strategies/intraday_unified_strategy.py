"""Estrategia Cuantitativa Unificada Optimizada para Menor Temporalidad (M5 y M15).
Incorpora filtro de horario institucional RTH, cierre forzado al fin de sesión (MOC),
escala de medias intradiarias y filtro de expansión de volatilidad para batir el costo de comisiones.
"""
from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.indicators.technical import compute_ema, compute_macd, compute_rsi, compute_atr, compute_sma
from src.strategies.strategy_c_patterns import detect_candle_patterns_causal
from src.backtest.engine_sma_confluence import AssetCosts

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IntradayStrategyParams:
    fast_ema: int = 20
    slow_ema: int = 80
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    rsi_period: int = 14
    rsi_min: float = 45.0
    rsi_max: float = 75.0
    atr_period: int = 14
    atr_k: float = 2.0
    tp_m: float = 2.0
    rth_start_time: str = "10:00"
    rth_end_time: str = "15:15"
    moc_close_time: str = "15:50"
    use_volatility_filter: bool = True
    use_candle_trigger: bool = True
    long_only: bool = True


def generate_intraday_signals(
    df: pd.DataFrame,
    params: IntradayStrategyParams,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Genera señales intradiarias al cierre de t con filtros de sesión y volatilidad."""
    n = len(df)
    close_p = df["close"]
    
    # Asegurar hora en ET para alineación con RTH (09:30 - 16:00 ET)
    ts = pd.to_datetime(df["ts_event"], utc=True)
    ts_et = ts.dt.tz_convert("America/New_York")
    time_str = ts_et.dt.strftime("%H:%M").values

    # 1. Medias Móviles Intradiarias
    ema_fast = compute_ema(close_p, params.fast_ema).values
    ema_slow = compute_ema(close_p, params.slow_ema).values

    # 2. Momentum
    _, _, macd_hist = compute_macd(close_p, params.macd_fast, params.macd_slow, params.macd_signal)
    hist_val = macd_hist.values
    rsi_val = compute_rsi(close_p, params.rsi_period).values

    # 3. Volatilidad y filtro de expansión
    atr_val = compute_atr(df["high"], df["low"], close_p, params.atr_period).values
    atr_series = pd.Series(atr_val)
    atr_baseline = compute_sma(atr_series, 40).values

    # 4. Gatillos de velas
    candle_pats = detect_candle_patterns_causal(df)
    hammer = candle_pats["hammer"]
    engulfing_bull = candle_pats["engulfing_bull"]

    sig_long = np.zeros(n, dtype=bool)
    is_moc_bar = np.zeros(n, dtype=bool)

    min_warmup = max(params.slow_ema, params.macd_slow + params.macd_signal, 50)
    close_arr = close_p.values

    for t in range(min_warmup, n):
        t_str = time_str[t]
        
        # Marcar barras de cierre de sesión
        if t_str >= params.moc_close_time:
            is_moc_bar[t] = True

        # Solo generar señales dentro del rango horario institucional
        if not (params.rth_start_time <= t_str <= params.rth_end_time):
            continue

        c_p = close_arr[t]
        ef = ema_fast[t]
        es = ema_slow[t]
        h = hist_val[t]
        r = rsi_val[t]
        atr = atr_val[t]
        atr_b = atr_baseline[t]

        if np.isnan(ef) or np.isnan(es) or np.isnan(h) or np.isnan(r) or np.isnan(atr):
            continue

        # Filtro de régimen
        regime_ok = (ef > es) and (c_p > es)
        
        # Filtro de momentum
        momentum_ok = (h > 0) and (params.rsi_min <= r <= params.rsi_max)
        
        # Filtro de volatilidad
        vol_ok = True
        if params.use_volatility_filter:
            vol_ok = not np.isnan(atr_b) and (atr >= atr_b * 0.95)

        # Gatillo de vela
        if params.use_candle_trigger:
            trigger_ok = bool(hammer[t] or engulfing_bull[t])
        else:
            trigger_ok = (ema_fast[t] > ema_slow[t] and ema_fast[t-1] <= ema_slow[t-1]) or (h > 0 and hist_val[t-1] <= 0)

        if regime_ok and momentum_ok and vol_ok and trigger_ok:
            sig_long[t] = True

    return sig_long, is_moc_bar, atr_val, time_str


def run_intraday_backtest(
    df: pd.DataFrame,
    params: IntradayStrategyParams,
    costs: AssetCosts,
) -> Dict[str, Any]:
    """Ejecuta backtest intradiario estricto con cierre MOC y deducción de comisiones."""
    sig_long, is_moc_bar, atr_val, time_str = generate_intraday_signals(df, params)

    n = len(df)
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

    ema_fast = compute_ema(df["close"], params.fast_ema).values
    ema_slow = compute_ema(df["close"], params.slow_ema).values

    for i in range(1, n):
        # 1. Monitoreo de posición
        if pos != 0:
            c_high = high_arr[i]
            c_low = low_arr[i]
            c_open = open_arr[i]
            exit_reason = None
            exit_price = 0.0

            # Prioridad 1: Cierre Forzoso al Fin de Sesión (MOC)
            if is_moc_bar[i]:
                exit_reason = "MOC_SESSION_END"
                exit_price = c_open
            # Prioridad 2: Stop Loss
            elif c_low <= sl_price:
                exit_reason = "SL"
                exit_price = min(c_open, sl_price)
            # Prioridad 3: Take Profit
            elif c_high >= tp_price:
                exit_reason = "TP"
                exit_price = max(c_open, tp_price)
            # Prioridad 4: Cruce de medias contrario
            elif ema_fast[i-1] < ema_slow[i-1]:
                exit_reason = "SIGNAL_FLIP"
                exit_price = c_open

            if exit_reason:
                holding_bars = i - entry_idx
                if is_futures:
                    gross_pnl = (exit_price - entry_price) * costs.multiplier
                    net_pnl = gross_pnl - fixed_cost_rt
                    notional = entry_price * costs.multiplier
                    ret = net_pnl / notional if notional > 0 else 0.0
                else:
                    gross_ret = exit_price / entry_price - 1.0
                    net_ret = gross_ret - (2.0 * (costs.commission_per_side + costs.slippage_per_side))
                    net_pnl = net_ret * 10000.0
                    ret = net_ret

                trades.append({
                    "entry_date": dates[entry_idx],
                    "exit_date": dates[i],
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "net_pnl_usd": net_pnl,
                    "return": ret,
                    "exit_reason": exit_reason,
                    "bars_held": holding_bars,
                })
                pos = 0

        # 2. Entrada causal en apertura de i tras señal en i-1
        if pos == 0 and i < n - 1:
            s_long = sig_long[i-1]
            cur_atr = atr_val[i-1]

            # No entrar si la barra actual ya es de cierre MOC
            if s_long and not is_moc_bar[i] and not np.isnan(cur_atr) and cur_atr > 0:
                pos = 1
                entry_idx = i
                entry_price = open_arr[i]
                stop_dist = params.atr_k * cur_atr
                tp_dist = params.tp_m * stop_dist
                sl_price = entry_price - stop_dist
                tp_price = entry_price + tp_dist

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
