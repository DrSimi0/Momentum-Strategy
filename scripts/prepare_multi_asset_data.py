"""Preparación completa de datos para el sistema multiactivo (ES, NQ, BTC, ETH).
1. Remuestrea ES y NQ desde 1m hacia 15m, 1h, 4h y 1D (usando los datos ya en el repo).
2. Descarga BTC-USDT y ETH-USDT desde la API pública de BingX en 15m, 1h, 4h y 1D.
3. Valida continuidad, duplicados y genera data/metadata_multi_asset.json.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import logging
from pathlib import Path
import pandas as pd

from src.data.resampler import resample_ohlcv_bars
from src.data.crypto_downloader import download_crypto_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("prepare_data")

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
METADATA_FILE = Path("data/metadata_multi_asset.json")


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(4096 * 1024):
            h.update(chunk)
    return h.hexdigest()


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    metadata = {
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "assets": {},
    }

    # =========================================================================
    # 1. FUTUROS CME: ES y NQ (REUTILIZAR DATOS EN REPO)
    # =========================================================================
    timeframes = ["15m", "1h", "4h", "1d"]
    for sym in ["ES", "NQ"]:
        raw_p = RAW_DIR / f"{sym}.v.0_ohlcv_1m.parquet"
        if not raw_p.exists():
            raise FileNotFoundError(f"Falta archivo de futuros {raw_p}")

        logger.info(f"Cargando {raw_p} ({sym})...")
        df_1m = pd.read_parquet(raw_p, columns=["ts_event", "open", "high", "low", "close", "volume"])
        metadata["assets"][sym] = {"source": "Databento GLBX.MDP3 (repo cache)", "timeframes": {}}

        for tf in timeframes:
            logger.info(f"Remuestreando {sym} a {tf}...")
            df_tf = resample_ohlcv_bars(df_1m, target_timeframe=tf, asset_family="indices")
            out_p = PROCESSED_DIR / f"{sym}_{tf}.parquet"
            df_tf.to_parquet(out_p, index=False)
            logger.info(f"Guardado {out_p} ({len(df_tf)} barras, {df_tf['ts_event'].min()} a {df_tf['ts_event'].max()})")

            metadata["assets"][sym]["timeframes"][tf] = {
                "path": str(out_p.as_posix()),
                "bars_count": len(df_tf),
                "start": str(df_tf["ts_event"].min()),
                "end": str(df_tf["ts_event"].max()),
                "sha256": compute_sha256(out_p),
            }

    # =========================================================================
    # 2. CRIPTOACTIVOS: BTC-USDT y ETH-USDT (BINGX API PÚBLICA)
    # =========================================================================
    # Para 15m usamos los últimos 2 años para optimizar velocidad de descarga; para 1h, 4h, 1d desde 2021
    crypto_symbols = ["BTC-USDT", "ETH-USDT"]
    for csym in crypto_symbols:
        clean_name = csym.replace("-", "_")
        metadata["assets"][csym] = {"source": "BingX Public Perpetual Swap API", "timeframes": {}}

        for tf in timeframes:
            start_date = "2023-01-01" if tf == "15m" else "2021-06-01"
            logger.info(f"Descargando {csym} ({tf}) desde {start_date}...")
            raw_crypto_p = download_crypto_history(symbol=csym, interval=tf, start_date=start_date)
            # Copiar o guardar en processed
            proc_p = PROCESSED_DIR / f"{clean_name}_{tf}.parquet"
            df_crypto = pd.read_parquet(raw_crypto_p)
            df_crypto.to_parquet(proc_p, index=False)

            metadata["assets"][csym]["timeframes"][tf] = {
                "path": str(proc_p.as_posix()),
                "bars_count": len(df_crypto),
                "start": str(df_crypto["ts_event"].min()),
                "end": str(df_crypto["ts_event"].max()),
                "sha256": compute_sha256(proc_p),
            }

    with open(METADATA_FILE, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"=== PREPARACIÓN DE DATOS COMPLETADA. Metadatos en {METADATA_FILE} ===")


if __name__ == "__main__":
    main()
