"""Script para descargar y validar datos históricos de velas de 15m de BingX swap USDT-M.
Almacena en formato Apache Parquet y genera el manifiesto con hash SHA-256.
"""
from __future__ import annotations

import argparse
import datetime
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from src.data.bingx_client import BingXDataClient
from src.data.storage import save_dataset_with_manifest
from src.data.validator import parse_and_validate_klines

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_bingx")


def fetch_historical_klines(
    symbol: str = "BTC-USDT",
    interval: str = "15m",
    start_dt: str = "2023-01-01",
    end_dt: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> pd.DataFrame:
    client = BingXDataClient()

    start_ts = int(pd.to_datetime(start_dt, utc=True).timestamp() * 1000)
    if end_dt:
        end_ts = int(pd.to_datetime(end_dt, utc=True).timestamp() * 1000)
    else:
        end_ts = int(time.time() * 1000)

    logger.info(f"Iniciando descarga de {symbol} ({interval}) desde {start_dt} hasta {end_dt or 'ahora'}...")
    
    interval_ms = 15 * 60 * 1000
    all_klines = []
    current_end = end_ts
    
    # Descargar hacia atrás desde end_ts hasta start_ts (1000 velas por petición)
    while current_end > start_ts:
        batch = client.get_klines(symbol=symbol, interval=interval, end_time=current_end, limit=1000)
        if not batch:
            logger.info("No se devolvieron más velas. Fin de historial disponible.")
            break
            
        all_klines.extend(batch)
        # El batch viene en orden descendente; el último elemento es el más antiguo del lote
        oldest_ts = int(batch[-1]["time"])
        logger.info(f"Descargadas {len(batch)} velas. Más antigua en lote: {pd.to_datetime(oldest_ts, unit='ms', utc=True)}")
        
        if oldest_ts <= start_ts:
            break
        if oldest_ts >= current_end:
            # Prevenir bucle infinito si la API no avanza
            current_end -= 1000 * interval_ms
        else:
            current_end = oldest_ts - 1
            
        time.sleep(0.15)  # Respetar rate limits

    logger.info(f"Total de registros crudos obtenidos: {len(all_klines)}")
    # Validar y limpiar
    clean_df = parse_and_validate_klines(
        all_klines,
        interval=interval,
        current_time_ms=int(time.time() * 1000),
        allow_gaps=True,
    )
    # Filtrar estrictamente al rango solicitado
    clean_df = clean_df[(clean_df["time"] >= start_ts) & (clean_df["time"] <= end_ts)].reset_index(drop=True)
    logger.info(f"Total de velas limpias tras validación: {len(clean_df)}")

    if output_path:
        save_dataset_with_manifest(
            clean_df,
            output_path,
            source_info={
                "symbol": symbol,
                "interval": interval,
                "start": str(clean_df["datetime_utc"].iloc[0]) if not clean_df.empty else None,
                "end": str(clean_df["datetime_utc"].iloc[-1]) if not clean_df.empty else None,
                "download_time_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        )
    return clean_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC-USDT")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--start", default="2023-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument("--out", default="data/historical/bingx_btc_usdt_15m.parquet")
    args = parser.parse_args()

    out_file = Path(args.out)
    fetch_historical_klines(
        symbol=args.symbol,
        interval=args.interval,
        start_dt=args.start,
        end_dt=args.end,
        output_path=out_file,
    )
