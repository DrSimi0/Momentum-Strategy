"""Estrategia Intradía con Línea de Tendencia Única (EMA 200).
Soporta modo Solo Largos y modo Simétrico (Largos + Cortos).
Garantiza ejecución causal estricta en la Apertura de la barra t+1 y salida MOC obligatoria (0% overnight).
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
class IntradayEma200Params:
    trend_ema_period: int = 200
    atr_period: int = 14
    atr_k: float = 2.0
    tp_m: float = 2.0
    trigger_type: str = "candle_pattern"  # "candle_pattern", "price_cross", "macd_turn"
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    rsi_period: int = 14
    rsi_min: float = 45.0
    rsi_max: float = 75.0
    rth_start_time: str = "10:00"
    rth_end_time: str = "15:15"
    moc_close_time: str = "15:45"  # "15:45" para 15m, "15:50" para 5m
    use_volatility_filter: bool = True
    allow_short: bool = False
    short_only: bool = False


def generate_ema200_signals(
    df: pd.DataFrame,
    params: IntradayEma200Params,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Genera señales causales intradía al cierre de cada barra t para largos y cortos."""
    n = len(df)
    close_p = df["close"]

    # Conversión causal de zona horaria a America/New_York (ET)
    ts = pd.to_datetime(df["ts_event"], utc=True)
    ts_et = ts.dt.tz_convert("America/New_York")
    time_str = ts_et.dt.strftime("%H:%M").values

    # 1. Línea de tendencia única (EMA 200)
    ema_trend = compute_ema(close_p, params.trend_ema_period).values

    # 2. Momentum (MACD y RSI)
    _, _, macd_hist = compute_macd(close_p, params.macd_fast, params.macd_slow, params.macd_signal)
    hist_val = macd_hist.values
    rsi_val = compute_rsi(close_p, params.rsi_period).values

    # 3. Volatilidad (ATR) y filtro de expansión
    atr_val = compute_atr(df["high"], df["low"], close_p, params.atr_period).values
    atr_series = pd.Series(atr_val)
    atr_baseline = compute_sma(atr_series, 40).values

    # 4. Gatillos de velas
    candle_pats = detect_candle_patterns_causal(df)
    hammer = candle_pats["hammer"]
    engulfing_bull = candle_pats["engulfing_bull"]
    shooting_star = candle_pats.get("shooting_star", np.zeros(n, dtype=bool))
    engulfing_bear = candle_pats.get("engulfing_bear", np.zeros(n, dtype=bool))

    sig_long = np.zeros(n, dtype=bool)
    sig_short = np.zeros(n, dtype=bool)
    is_moc_bar = np.zeros(n, dtype=bool)

    min_warmup = max(params.trend_ema_period + 10, 220)
    close_arr = close_p.values

    for t in range(min_warmup, n):
        t_str = time_str[t]

        # Barra de cierre de sesión obligatoria
        if t_str >= params.moc_close_time:
            is_moc_bar[t] = True

        # Solo generar señales dentro del rango institucional RTH
        if not (params.rth_start_time <= t_str <= params.rth_end_time):
            continue

        c_p = close_arr[t]
        c_prev = close_arr[t - 1]
        e_trend = ema_trend[t]
        e_trend_prev = ema_trend[t - 1]
        h = hist_val[t]
        h_prev = hist_val[t - 1]
        r = rsi_val[t]
        atr = atr_val[t]
        atr_b = atr_baseline[t]

        if np.isnan(e_trend) or np.isnan(h) or np.isnan(r) or np.isnan(atr):
            continue

        # Filtro de Volatilidad común
        vol_ok = True
        if params.use_volatility_filter:
            vol_ok = not np.isnan(atr_b) and (atr >= atr_b * 0.95)

        # -----------------------------
        # SEÑAL LARGA (LONG)
        # -----------------------------
        regime_long_ok = (c_p > e_trend)
        momentum_long_ok = (h > 0) and (params.rsi_min <= r <= params.rsi_max)

        if params.trigger_type == "candle_pattern":
            trigger_long_ok = bool(hammer[t] or engulfing_bull[t])
        elif params.trigger_type == "price_cross":
            trigger_long_ok = (c_p > e_trend) and (c_prev <= e_trend_prev)
        elif params.trigger_type == "macd_turn":
            trigger_long_ok = (h > 0) and (h_prev <= 0)
        else:
            trigger_long_ok = bool(hammer[t] or engulfing_bull[t])

        if regime_long_ok and momentum_long_ok and vol_ok and trigger_long_ok:
            sig_long[t] = True

        # -----------------------------
        # SEÑAL CORTA (SHORT) - REGLA ESPEJO
        # -----------------------------
        regime_short_ok = (c_p < e_trend)
        # En RSI simétrico: rango 25 a 55 (espejo de 45 a 75)
        momentum_short_ok = (h < 0) and (100.0 - params.rsi_max <= r <= 100.0 - params.rsi_min)

        if params.trigger_type == "candle_pattern":
            trigger_short_ok = bool(shooting_star[t] or engulfing_bear[t])
        elif params.trigger_type == "price_cross":
            trigger_short_ok = (c_p < e_trend) and (c_prev >= e_trend_prev)
        elif params.trigger_type == "macd_turn":
            trigger_short_ok = (h < 0) and (h_prev >= 0)
        else:
            trigger_short_ok = (c_p < e_trend) and (c_prev >= e_trend_prev)

        if regime_short_ok and momentum_short_ok and vol_ok and trigger_short_ok:
            sig_short[t] = True

    return sig_long, sig_short, is_moc_bar, atr_val, ema_trend, time_str


def run_ema200_backtest(
    df: pd.DataFrame,
    params: IntradayEma200Params,
    costs: AssetCosts,
    initial_capital: float = 50000.0,
) -> Dict[str, Any]:
    """Ejecuta backtest causal deduciendo comisiones y calculando curva diaria de equity.
    Garantiza ejecución estricta en el Open de la barra t+1 tras señal generada al cierre de t.
    """
    sig_long, sig_short, is_moc_bar, atr_val, ema_trend, time_str = generate_ema200_signals(df, params)

    n = len(df)
    open_arr = df["open"].values
    high_arr = df["high"].values
    low_arr = df["low"].values
    close_arr = df["close"].values
    dates = pd.to_datetime(df["ts_event"], utc=True)

    is_futures = (costs.asset_type == "futures")
    fixed_cost_rt = (2.0 * costs.commission_per_side + 2.0 * costs.slippage_per_side * costs.tick_size * costs.multiplier) if is_futures else 0.0

    trades: List[Dict[str, Any]] = []
    pos = 0  # 0: plano, 1: long, -1: short
    entry_price = 0.0
    sl_price = 0.0
    tp_price = 0.0
    entry_idx = 0
    trade_dir = ""

    daily_pnl_map: Dict[str, float] = {}

    for i in range(1, n):
        cur_date_str = str(dates.iloc[i].date())
        if cur_date_str not in daily_pnl_map:
            daily_pnl_map[cur_date_str] = 0.0

        # -------------------------------------------------------------
        # 1. Monitoreo de posición abierta (evaluación intra-barra i)
        # -------------------------------------------------------------
        if pos != 0:
            c_high = high_arr[i]
            c_low = low_arr[i]
            c_open = open_arr[i]
            exit_reason = None
            exit_price = 0.0

            if pos == 1:
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
                # Prioridad 4: Pérdida de la EMA 200 (cierre previo cayó por debajo)
                elif close_arr[i - 1] < ema_trend[i - 1]:
                    exit_reason = "TREND_LOST"
                    exit_price = c_open

            elif pos == -1:
                # Prioridad 1: Cierre Forzoso al Fin de Sesión (MOC)
                if is_moc_bar[i]:
                    exit_reason = "MOC_SESSION_END"
                    exit_price = c_open
                # Prioridad 2: Stop Loss
                elif c_high >= sl_price:
                    exit_reason = "SL"
                    exit_price = max(c_open, sl_price)
                # Prioridad 3: Take Profit
                elif c_low <= tp_price:
                    exit_reason = "TP"
                    exit_price = min(c_open, tp_price)
                # Prioridad 4: Pérdida de tendencia bajista (cierre previo superó EMA 200)
                elif close_arr[i - 1] > ema_trend[i - 1]:
                    exit_reason = "TREND_LOST"
                    exit_price = c_open

            if exit_reason:
                holding_bars = i - entry_idx
                if is_futures:
                    if pos == 1:
                        gross_pnl = (exit_price - entry_price) * costs.multiplier
                    else:
                        gross_pnl = (entry_price - exit_price) * costs.multiplier
                    net_pnl = gross_pnl - fixed_cost_rt
                    notional = entry_price * costs.multiplier
                    ret = net_pnl / notional if notional > 0 else 0.0
                else:
                    if pos == 1:
                        gross_ret = exit_price / entry_price - 1.0
                    else:
                        gross_ret = 1.0 - exit_price / entry_price
                    net_ret = gross_ret - (2.0 * (costs.commission_per_side + costs.slippage_per_side))
                    net_pnl = net_ret * initial_capital
                    ret = net_ret

                daily_pnl_map[cur_date_str] += net_pnl

                trades.append({
                    "entry_date": dates.iloc[entry_idx],
                    "exit_date": dates.iloc[i],
                    "direction": trade_dir,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "net_pnl_usd": net_pnl,
                    "return": ret,
                    "exit_reason": exit_reason,
                    "bars_held": holding_bars,
                    "entry_bar_idx": entry_idx,
                    "exit_bar_idx": i,
                })
                pos = 0

        # -------------------------------------------------------------
        # 2. Entrada Causal en Apertura de i (Open[i]) si hubo señal en i-1
        # -------------------------------------------------------------
        if pos == 0 and i < n - 1 and not is_moc_bar[i]:
            s_long = sig_long[i - 1]
            s_short = sig_short[i - 1]
            cur_atr = atr_val[i - 1]

            if not np.isnan(cur_atr) and cur_atr > 0:
                # Compras (Long)
                if s_long and not params.short_only:
                    pos = 1
                    entry_idx = i
                    trade_dir = "LONG"
                    entry_price = open_arr[i]
                    stop_dist = params.atr_k * cur_atr
                    tp_dist = params.tp_m * stop_dist
                    sl_price = entry_price - stop_dist
                    tp_price = entry_price + tp_dist

                # Ventas (Short)
                elif s_short and (params.allow_short or params.short_only):
                    pos = -1
                    entry_idx = i
                    trade_dir = "SHORT"
                    entry_price = open_arr[i]
                    stop_dist = params.atr_k * cur_atr
                    tp_dist = params.tp_m * stop_dist
                    sl_price = entry_price + stop_dist
                    tp_price = entry_price - tp_dist

    n_trades = len(trades)
    if n_trades == 0:
        return {
            "n_trades": 0,
            "net_pnl_usd": 0.0,
            "sharpe_daily": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_usd": 0.0,
            "max_drawdown_pct": 0.0,
            "cagr": 0.0,
            "simple_annual_return": 0.0,
            "calmar": 0.0,
            "trades": [],
            "daily_series": pd.Series(dtype=float),
        }

    pnls = np.array([t["net_pnl_usd"] for t in trades])
    pos_sum = float(np.sum(pnls[pnls > 0]))
    neg_sum = float(np.abs(np.sum(pnls[pnls < 0])))
    pf = (pos_sum / neg_sum) if neg_sum > 0 else (999.0 if pos_sum > 0 else 0.0)

    daily_s = pd.Series(daily_pnl_map).sort_index()
    daily_rets = daily_s / initial_capital
    mean_d = float(daily_rets.mean())
    std_d = float(daily_rets.std(ddof=1)) if len(daily_rets) > 1 else 0.0
    sharpe_daily = (mean_d / std_d * np.sqrt(252.0)) if std_d > 1e-9 else 0.0

    cum_pnl = daily_s.cumsum()
    equity_curve = initial_capital + cum_pnl
    peaks = np.maximum.accumulate(equity_curve)
    dd_usd = peaks - equity_curve
    max_dd_usd = float(dd_usd.max()) if len(dd_usd) > 0 else 0.0
    max_dd_pct = (max_dd_usd / initial_capital) * 100.0

    total_net_pnl = float(np.sum(pnls))
    n_days = len(daily_s)
    years = max(n_days / 252.0, 0.1)
    simple_annual_ret = (total_net_pnl / initial_capital) / years * 100.0

    final_equity = initial_capital + total_net_pnl
    if final_equity > 0:
        cagr = ((final_equity / initial_capital) ** (1.0 / years) - 1.0) * 100.0
    else:
        cagr = -100.0

    calmar = (simple_annual_ret / max_dd_pct) if max_dd_pct > 0 else 0.0

    return {
        "n_trades": n_trades,
        "net_pnl_usd": total_net_pnl,
        "sharpe_daily": sharpe_daily,
        "win_rate": float(np.mean(pnls > 0)) * 100.0,
        "profit_factor": pf,
        "max_drawdown_usd": max_dd_usd,
        "max_drawdown_pct": max_dd_pct,
        "cagr": cagr,
        "simple_annual_return": simple_annual_ret,
        "calmar": calmar,
        "trades": trades,
        "daily_series": daily_s,
    }
