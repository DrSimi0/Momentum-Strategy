"""Generador de Señales para Forward Test en Vivo (Sin Ejecución de Órdenes).
Registra en bitácora inmutable las señales causales al cierre de vela para monitoreo fuera de muestra.
"""
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Dict, List, Optional
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.strategies.strategy_c_patterns import detect_candle_patterns_causal, detect_chartist_figures_causal
from src.indicators.technical import compute_ema, compute_macd, compute_rsi

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports/forward_test")
LOG_FILE = REPORTS_DIR / "forward_test_signals.log"
CSV_FILE = REPORTS_DIR / "forward_test_signals.csv"


def log_forward_signals(asset: str, timeframe: str, latest_bar: pd.Series, signals: Dict[str, str]):
    """Registra de forma inmutable las señales emitidas en la barra t."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts_now = datetime.now(timezone.utc).isoformat()
    bar_time = str(latest_bar.get("ts_event", "N/A"))
    close_price = float(latest_bar.get("close", 0.0))

    record = {
        "timestamp_utc": ts_now,
        "bar_timestamp": bar_time,
        "asset": asset,
        "timeframe": timeframe,
        "close_price": close_price,
        "signals": signals,
    }

    # Escribir en log plano
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    # Guardar en CSV acumulativo
    df_new = pd.DataFrame([{
        "timestamp_utc": ts_now,
        "bar_timestamp": bar_time,
        "asset": asset,
        "timeframe": timeframe,
        "close_price": close_price,
        **{f"sig_{k}": v for k, v in signals.items()}
    }])

    if CSV_FILE.exists():
        df_new.to_csv(CSV_FILE, mode="a", header=False, index=False)
    else:
        df_new.to_csv(CSV_FILE, mode="w", header=True, index=False)

    logger.info(f"Señal registrada para {asset} {timeframe} al precio {close_price}: {signals}")


def run_forward_signal_check():
    """Genera las señales de hoy con los datos más recientes disponibles."""
    logger.info("Iniciando escaneo de señales de Forward Test...")
    processed_dir = Path("data/processed")

    for sym in ["ES", "NQ"]:
        for tf in ["4h", "1h"]:
            p_file = processed_dir / f"{sym}_{tf}.parquet"
            if not p_file.exists():
                logger.warning(f"Archivo no disponible para forward test: {p_file}")
                continue

            df = pd.read_parquet(p_file)
            if len(df) < 50:
                continue

            latest_idx = len(df) - 1
            latest_bar = df.iloc[latest_idx]

            # 1. Estrategia A (Top EMAs candidatas: EMA 20 vs EMA 100)
            ema20 = compute_ema(df["close"], 20).values
            ema100 = compute_ema(df["close"], 100).values
            sig_a = "HOLD"
            if ema20[latest_idx] > ema100[latest_idx] and ema20[latest_idx-1] <= ema100[latest_idx-1]:
                sig_a = "BUY"
            elif ema20[latest_idx] < ema100[latest_idx] and ema20[latest_idx-1] >= ema100[latest_idx-1]:
                sig_a = "SELL"

            # 2. Estrategia B (Línea Base MACD Solo)
            macd_l, macd_s, _ = compute_macd(df["close"], 12, 26, 9)
            sig_b = "HOLD"
            if macd_l.values[latest_idx] > macd_s.values[latest_idx] and macd_l.values[latest_idx-1] <= macd_s.values[latest_idx-1]:
                sig_b = "BUY"
            elif macd_l.values[latest_idx] < macd_s.values[latest_idx] and macd_l.values[latest_idx-1] >= macd_s.values[latest_idx-1]:
                sig_b = "SELL"

            # 3. Estrategia C (Engulfing Bullish y Hammer)
            candle_pats = detect_candle_patterns_causal(df)
            sig_c = "HOLD"
            if candle_pats["engulfing_bull"][latest_idx]:
                sig_c = "BUY_ENGULFING"
            elif candle_pats["hammer"][latest_idx]:
                sig_c = "BUY_HAMMER"
            elif candle_pats["engulfing_bear"][latest_idx]:
                sig_c = "SELL_ENGULFING"

            signals = {
                "Strategy_A_EMA": sig_a,
                "Strategy_B_MACD": sig_b,
                "Strategy_C_Patterns": sig_c,
            }

            log_forward_signals(sym, tf, latest_bar, signals)

    logger.info("Escaneo de Forward Test completado exitosamente.")


if __name__ == "__main__":
    run_forward_signal_check()
