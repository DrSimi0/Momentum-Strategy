"""Script ejecutable para descargar y validar los datos de 1 minuto de ES y NQ desde Databento mediante la API Batch.
Ajustado al rango 2017-12-15 a 2026-10-20 (Decisión D-005, costo verificado: USD 22.74 < USD 25.00).
"""
import logging
from pathlib import Path
import pandas as pd

from src.data.databento_client import (
    submit_and_download_batch,
    estimate_total_cost,
    update_data_metadata,
)
from src.data.validate import validate_ohlcv_invariants

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

START_DATE = "2017-12-15"
END_DATE = "2026-10-20"
DATASET = "GLBX.MDP3"
SYMBOLS = ["ES.v.0", "NQ.v.0"]


def main():
    logger.info("=== PASO 1: Comprobación estricta de costos estimados ===")
    costs = estimate_total_cost(
        symbols=SYMBOLS,
        start=START_DATE,
        end=END_DATE,
        dataset=DATASET,
        schema="ohlcv-1m",
        stype_in="continuous",
    )
    logger.info(f"Costos calculados por Databento: {costs}")
    if costs["total"] > 25.0:
        raise RuntimeError(f"Costo total excedido ({costs['total']:.2f} USD > 25.00 USD). Abortando.")

    logger.info("=== PASO 2: Envío y descarga mediante trabajo Batch ===")
    downloaded_files = submit_and_download_batch(
        symbols=SYMBOLS,
        start_date=START_DATE,
        end_date=END_DATE,
        dataset=DATASET,
        schema="ohlcv-1m",
        stype_in="continuous",
        max_allowed_cost_usd=25.0,
    )

    logger.info("=== PASO 3: Validación de integridad OHLCV de los archivos ===")
    for sym, p in downloaded_files.items():
        logger.info(f"Validando invariantes de {p}...")
        df = pd.read_parquet(p)
        validate_ohlcv_invariants(df)
        logger.info(f"Validación exitosa para {sym}: {len(df)} barras OHLCV sin violaciones.")

    logger.info("=== PASO 4: Generación de data/metadata.json con SHA-256 ===")
    meta_path = update_data_metadata(
        downloaded_files=downloaded_files,
        dataset=DATASET,
        schema="ohlcv-1m",
        start_date=START_DATE,
        end_date=END_DATE,
        costs=costs,
    )
    logger.info(f"Descarga y validación finalizadas exitosamente. Metadatos en {meta_path}")


if __name__ == "__main__":
    main()
