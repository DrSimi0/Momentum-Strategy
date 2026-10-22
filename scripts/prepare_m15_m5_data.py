"""Remuestrea ES y NQ de 1m a 15m y 5m para el historial completo 2010-2026."""
import logging
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from src.data.resampler import resample_ohlcv_bars

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("resample_m15_m5")

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    timeframes = ["15m", "5m"]

    for sym in ["ES", "NQ"]:
        raw_p = RAW_DIR / f"{sym}.v.0_ohlcv_1m.parquet"
        if not raw_p.exists():
            logger.warning(f"No encontrado: {raw_p}")
            continue

        logger.info(f"Cargando 1m de {sym} desde {raw_p}...")
        df_1m = pd.read_parquet(raw_p, columns=["ts_event", "open", "high", "low", "close", "volume"])

        for tf in timeframes:
            out_p = PROCESSED_DIR / f"{sym}_{tf}.parquet"
            logger.info(f"Remuestreando {sym} a {tf}...")
            df_tf = resample_ohlcv_bars(df_1m, target_timeframe=tf, asset_family="indices")
            df_tf.to_parquet(out_p, index=False)
            logger.info(f"Guardado {out_p}: {len(df_tf)} barras desde {df_tf['ts_event'].min()} hasta {df_tf['ts_event'].max()}")

    logger.info("Resampleo M15/M5 completado.")


if __name__ == "__main__":
    main()
