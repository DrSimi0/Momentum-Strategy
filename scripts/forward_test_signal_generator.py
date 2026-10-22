"""Script de Forward Testing / Generador de Señales Diarias.
Ejecuta la estrategia finalista al cierre de mercado sin emitir órdenes reales,
registrando la señal (LONG, SHORT, NEUTRAL) y los niveles de Stop Loss y Take Profit
en un log estructurado (reports/forward_signals.jsonl).
"""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import numpy as np
import pandas as pd

from src.backtest.engine_sma_confluence import StrategyParams
from src.indicators.technical import compute_sma, compute_macd, compute_rsi, compute_atr

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

SIGNALS_LOG = Path("reports/forward_signals.jsonl")


def generate_signal_for_asset(df_4h: pd.DataFrame, params: StrategyParams, asset_name: str):
    """Genera la señal de trading estricta al cierre de la última vela cerrada (t)."""
    if len(df_4h) < params.slow_sma + 10:
        logger.warning(f"{asset_name}: Datos insuficientes ({len(df_4h)} barras)")
        return None

    close = df_4h["close"]
    high = df_4h["high"]
    low = df_4h["low"]

    sma_f = compute_sma(close, params.fast_sma)
    sma_s = compute_sma(close, params.slow_sma)
    if params.num_smas == 3:
        sma_m = compute_sma(close, params.mid_sma)
        trend_long = (sma_f > sma_m) & (sma_m > sma_s) & (close > sma_f)
        trend_short = (sma_f < sma_m) & (sma_m < sma_s) & (close < sma_f)
    else:
        trend_long = (close > sma_s) & (sma_f > sma_s)
        trend_short = (close < sma_s) & (sma_f < sma_s)

    macd_line, macd_sig, macd_hist = compute_macd(close, params.macd_fast, params.macd_slow, params.macd_signal)
    hist_prev = macd_hist.shift(1)
    macd_cross_up = (hist_prev <= 0) & (macd_hist > 0)
    macd_cross_down = (hist_prev >= 0) & (macd_hist < 0)

    rsi = compute_rsi(close, params.rsi_period)
    rsi_long = (rsi >= 40.0) & (rsi <= 70.0)
    rsi_short = (rsi >= 30.0) & (rsi <= 60.0)

    atr = compute_atr(high, low, close, 14)

    # Última vela cerrada (índice -1)
    last_idx = -1
    last_ts = df_4h["ts_event"].iloc[last_idx]
    last_close = float(close.iloc[last_idx])
    last_atr = float(atr.iloc[last_idx])

    signal = "NEUTRAL"
    sl_price = None
    tp_price = None

    if trend_long.iloc[last_idx] and macd_cross_up.iloc[last_idx] and rsi_long.iloc[last_idx]:
        signal = "LONG"
        stop_dist = params.atr_k * last_atr
        sl_price = last_close - stop_dist
        tp_price = last_close + (params.tp_m * stop_dist)
    elif trend_short.iloc[last_idx] and macd_cross_down.iloc[last_idx] and rsi_short.iloc[last_idx]:
        signal = "SHORT"
        stop_dist = params.atr_k * last_atr
        sl_price = last_close + stop_dist
        tp_price = last_close - (params.tp_m * stop_dist)

    record = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "bar_ts_event": str(last_ts),
        "asset": asset_name,
        "signal": signal,
        "last_close": last_close,
        "atr_14": last_atr,
        "stop_loss_price": sl_price,
        "take_profit_price": tp_price,
        "strategy_params": asdict(params),
    }

    SIGNALS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(SIGNALS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    logger.info(f"Señal generada para {asset_name}: {signal} (Cierre: {last_close:.2f})")
    return record


if __name__ == "__main__":
    # Prueba del generador de señales con datos actuales
    p_es = StrategyParams(num_smas=3, fast_sma=30, mid_sma=100, slow_sma=150, macd_fast=16, macd_slow=35, macd_signal=9, rsi_period=14, atr_k=2.0, tp_m=2.0)
    df_es = pd.read_parquet("data/processed/ES_4h.parquet")
    res = generate_signal_for_asset(df_es, p_es, "ES")
    print("Forward test signal demo:", res)
