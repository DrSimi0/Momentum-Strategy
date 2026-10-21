"""Motor de backtesting vectorizado y barra por barra para la estrategia de confluencia SMA + MACD + RSI.
Garantiza:
1. Señal calculada al cierre de t, entrada en la apertura de t+1 (cero look-ahead).
2. Niveles de SL fijo y TP calculados con el ATR al momento de la señal.
3. Simulación intrawave de SL, TP y salida por cruce contrario de SMAs.
4. Soporte para modelos de costos de futuros (ticks/dólares) y cripto (%/funding).
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.indicators.technical import compute_sma, compute_macd, compute_rsi, compute_atr

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StrategyParams:
    num_smas: int = 2                 # 1, 2 o 3
    fast_sma: int = 20                # 10, 20, 21, 30
    mid_sma: int = 50                 # 50, 100 (solo si num_smas == 3)
    slow_sma: int = 100               # 100, 150, 200
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    rsi_period: int = 14              # 7, 14, 21
    atr_k: float = 2.0                # 1.5, 2.0, 3.0
    tp_m: float = 2.0                 # TP = m * (k * ATR)
    use_macd: bool = True             # False para versión solo-SMA
    use_rsi: bool = True              # False para versión solo-SMA
    close_at_session_end: bool = False # Forzar cierre al final de sesión en intradía


@dataclass(frozen=True)
class AssetCosts:
    asset_type: str = "futures"        # "futures" o "crypto"
    multiplier: float = 50.0          # Para futuros (ES: 50, NQ: 20)
    tick_size: float = 0.25
    commission_per_side: float = 2.00 # USD por lado en futuros / % en cripto (ej. 0.0005)
    slippage_per_side: float = 0.5    # ticks en futuros / % en cripto (ej. 0.0002)
    funding_rate_8h: float = 0.0001   # Solo cripto
    annualization_factor: float = 252.0


def run_sma_confluence_backtest(
    df: pd.DataFrame,
    params: StrategyParams,
    costs: AssetCosts,
) -> Dict[str, Any]:
    """Ejecuta el backtest completo para un DataFrame OHLCV con las reglas pre-registradas."""
    n = len(df)
    min_required = max(params.slow_sma, params.macd_slow, params.rsi_period) + 20
    if n < min_required:
        return {"n_trades": 0, "net_pnl_usd": 0.0, "sharpe": 0.0, "trades": []}

    # 1. Calcular indicadores
    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_ = df["open"]

    sma_slow = compute_sma(close, params.slow_sma)
    sma_fast = compute_sma(close, params.fast_sma)
    sma_mid = compute_sma(close, params.mid_sma) if params.num_smas == 3 else None

    macd_line, sig_line, macd_hist = compute_macd(close, params.macd_fast, params.macd_slow, params.macd_signal)
    rsi = compute_rsi(close, params.rsi_period)
    atr = compute_atr(high, low, close, window=14)

    # 2. Vectorizar condiciones de tendencia
    if params.num_smas == 1:
        trend_long = close > sma_slow
        trend_short = close < sma_slow
    elif params.num_smas == 2:
        trend_long = (close > sma_slow) & (sma_fast > sma_slow)
        trend_short = (close < sma_slow) & (sma_fast < sma_slow)
    else: # 3 SMAs
        trend_long = (close > sma_slow) & (sma_fast > sma_mid) & (sma_mid > sma_slow)
        trend_short = (close < sma_slow) & (sma_fast < sma_mid) & (sma_mid < sma_slow)

    # 3. Gatillo MACD (cruce por cero del histograma)
    prev_hist = macd_hist.shift(1)
    if params.use_macd:
        macd_trigger_long = (prev_hist <= 0) & (macd_hist > 0)
        macd_trigger_short = (prev_hist >= 0) & (macd_hist < 0)
    else:
        # Modo solo-SMA: gatillo en el cambio de tendencia
        prev_tl = trend_long.shift(1).fillna(False)
        prev_ts = trend_short.shift(1).fillna(False)
        macd_trigger_long = trend_long & (~prev_tl)
        macd_trigger_short = trend_short & (~prev_ts)

    # 4. Filtro RSI
    if params.use_rsi:
        rsi_long = (rsi >= 40.0) & (rsi <= 70.0)
        rsi_short = (rsi >= 30.0) & (rsi <= 60.0)
    else:
        rsi_long = pd.Series(True, index=close.index)
        rsi_short = pd.Series(True, index=close.index)

    # Señal generada al cierre de t
    raw_signal_long = (trend_long & macd_trigger_long & rsi_long).values
    raw_signal_short = (trend_short & macd_trigger_short & rsi_short).values
    trend_long_arr = trend_long.values
    trend_short_arr = trend_short.values

    open_arr = open_.values
    high_arr = high.values
    low_arr = low.values
    close_arr = close.values
    atr_arr = atr.values
    dates = df["ts_event"].values if "ts_event" in df.columns else df.index.values

    # 5. Simulación barra por barra sin look-ahead
    # Posición: 0 (fuera), 1 (long), -1 (short)
    pos = 0
    entry_price = 0.0
    sl_price = 0.0
    tp_price = 0.0
    entry_idx = 0

    trades = []
    
    # Pre-calcular costos constantes
    is_futures = (costs.asset_type == "futures")
    if is_futures:
        slip_points_per_side = costs.slippage_per_side * costs.tick_size
        comm_usd_rt = 2.0 * costs.commission_per_side
        slip_usd_rt = 2.0 * costs.slippage_per_side * (costs.tick_size * costs.multiplier)
        fixed_cost_usd_rt = comm_usd_rt + slip_usd_rt
    else:
        # Cripto porcentual
        cost_pct_rt = 2.0 * (costs.commission_per_side + costs.slippage_per_side)

    for i in range(1, n):
        # A) Si estamos en posición, evaluar salidas intrawave en la barra i
        if pos != 0:
            c_high = high_arr[i]
            c_low = low_arr[i]
            c_close = close_arr[i]
            c_open = open_arr[i]
            exit_reason = None
            exit_price = 0.0

            if pos == 1:
                # Long: SL si Low <= sl_price, TP si High >= tp_price
                sl_hit = c_low <= sl_price
                tp_hit = c_high >= tp_price

                if sl_hit and tp_hit:
                    # Supuesto conservador ante ambigüedad en la barra: SL primero
                    exit_reason = "SL"
                    exit_price = min(c_open, sl_price)
                elif sl_hit:
                    exit_reason = "SL"
                    exit_price = min(c_open, sl_price)
                elif tp_hit:
                    exit_reason = "TP"
                    exit_price = max(c_open, tp_price)
                elif trend_short_arr[i]:
                    # Salida por cruce contrario de tendencia al cierre
                    exit_reason = "SMA_REVERSAL"
                    exit_price = c_close

            elif pos == -1:
                # Short: SL si High >= sl_price, TP si Low <= tp_price
                sl_hit = c_high >= sl_price
                tp_hit = c_low <= tp_price

                if sl_hit and tp_hit:
                    exit_reason = "SL"
                    exit_price = max(c_open, sl_price)
                elif sl_hit:
                    exit_reason = "SL"
                    exit_price = max(c_open, sl_price)
                elif tp_hit:
                    exit_reason = "TP"
                    exit_price = min(c_open, tp_price)
                elif trend_long_arr[i]:
                    # Salida por cruce contrario de tendencia al cierre
                    exit_reason = "SMA_REVERSAL"
                    exit_price = c_close

            # Registrar trade si hubo salida
            if exit_reason:
                holding_bars = i - entry_idx
                if is_futures:
                    gross_diff = (exit_price - entry_price) if pos == 1 else (entry_price - exit_price)
                    gross_pnl = gross_diff * costs.multiplier
                    net_pnl = gross_pnl - fixed_cost_usd_rt
                    notional = entry_price * costs.multiplier
                    ret = net_pnl / notional if notional > 0 else 0.0
                else:
                    gross_ret = (exit_price / entry_price - 1.0) if pos == 1 else (1.0 - exit_price / entry_price)
                    # Funding proporcional a las barras retenidas (asumiendo 1h = 1/8 de funding_8h)
                    funding_cost = costs.funding_rate_8h * (holding_bars / 8.0)
                    net_ret = gross_ret - cost_pct_rt - funding_cost
                    notional = 10000.0 # Nocional estándar $10,000 USD
                    net_pnl = net_ret * notional
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

        # B) Si no estamos en posición, evaluar entrada en la apertura de i
        # La señal fue generada al cierre de i-1 (cero look-ahead)
        if pos == 0 and i < n - 1:
            sig_l = raw_signal_long[i - 1]
            sig_s = raw_signal_short[i - 1]
            cur_atr = atr_arr[i - 1]

            if (sig_l or sig_s) and not np.isnan(cur_atr) and cur_atr > 0:
                pos = 1 if sig_l else -1
                entry_idx = i
                entry_price = open_arr[i] # Entrada al OPEN de i
                stop_dist = params.atr_k * cur_atr
                tp_dist = params.tp_m * stop_dist

                if pos == 1:
                    sl_price = entry_price - stop_dist
                    tp_price = entry_price + tp_dist
                else:
                    sl_price = entry_price + stop_dist
                    tp_price = entry_price - tp_dist

    n_trades = len(trades)
    if n_trades == 0:
        return {
            "n_trades": 0,
            "net_pnl_usd": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "avg_expectancy_usd": 0.0,
            "trades": [],
        }

    trades_df = pd.DataFrame(trades)
    pnls = trades_df["net_pnl_usd"].values
    rets = trades_df["return"].values
    total_net_pnl = float(np.sum(pnls))
    win_rate = float(np.mean(pnls > 0))
    avg_expectancy = float(np.mean(pnls))

    pos_sum = float(np.sum(pnls[pnls > 0]))
    neg_sum = float(np.abs(np.sum(pnls[pnls < 0])))
    pf = (pos_sum / neg_sum) if neg_sum > 0 else np.nan

    # Sharpe anualizado: solo se reporta si la muestra tiene al menos 30 operaciones
    # para evitar artefactos extremos por muestra insuficiente (ej. -94.53)
    mean_ret = float(np.mean(rets))
    std_ret = float(np.std(rets, ddof=1)) if n_trades > 1 else 0.0
    if n_trades >= 30 and std_ret > 1e-9:
        sharpe = float((mean_ret / std_ret) * np.sqrt(costs.annualization_factor))
    else:
        sharpe = np.nan

    # Drawdown monetario
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
