"""Descarga de historia 2010-2017 de Databento y consolidación con la historia 2017-2026
para obtener 16.3 años continuos de ES y NQ en ohlcv-1m.
"""
from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
import time
import databento as db
import pandas as pd

from src.settings import get_api_key
from src.data.databento_client import estimate_total_cost
from src.data.validate import validate_ohlcv_invariants
from src.data.resampler import resample_ohlcv_bars

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    symbols = ["ES.v.0", "NQ.v.0"]
    start_date = "2010-06-07"
    end_date = "2017-12-16"
    dataset = "GLBX.MDP3"
    schema = "ohlcv-1m"

    # 1. Verificar costo
    costs = estimate_total_cost(symbols, start=start_date, end=end_date, dataset=dataset, schema=schema)
    total_cost = costs["total"]
    logger.info(f"Costo confirmado para {symbols} ({start_date} a {end_date}): USD {total_cost:.2f}")
    if total_cost > 25.0:
        raise ValueError(f"Costo {total_cost} supera el límite de seguridad de 25.0 USD")

    # 2. Cliente Databento
    api_key = get_api_key()
    client = db.Historical(api_key)

    # 3. Comprobar o enviar trabajo batch
    existing_jobs = client.batch.list_jobs(since=start_date)
    matching_job_id = None
    for j in existing_jobs:
        if (
            j.get("dataset") == dataset
            and j.get("schema") == schema
            and j.get("state") == "done"
            and all(s in str(j.get("symbols")) for s in symbols)
            and "2010-06-07" in str(j.get("start"))
        ):
            matching_job_id = j["id"]
            logger.info(f"Trabajo batch existente encontrado: {matching_job_id}")
            break

    if not matching_job_id:
        logger.info(f"Enviando nuevo trabajo batch para {symbols} ({start_date} a {end_date})...")
        job = client.batch.submit_job(
            dataset=dataset,
            symbols=symbols,
            schema=schema,
            start=start_date,
            end=end_date,
            stype_in="continuous",
            encoding="dbn",
            compression="zstd",
            split_symbols=True,
            split_duration="none",
            delivery="download",
        )
        matching_job_id = job["id"]
        logger.info(f"Trabajo batch enviado. Job ID: {matching_job_id}")

    # 4. Esperar finalización
    start_wait = time.time()
    while True:
        details = client.batch.get_job_details(matching_job_id)
        state = details.get("state")
        progress = details.get("progress", 0)
        logger.info(f"Estado de {matching_job_id}: {state} ({progress}%)")
        if state == "done":
            break
        elif state in ("expired", "cancelled"):
            raise RuntimeError(f"El trabajo batch {matching_job_id} falló con estado {state}")
        if time.time() - start_wait > 1800:
            raise TimeoutError("Tiempo de espera agotado.")
        time.sleep(15)

    # 5. Descargar archivos
    dl_dir = RAW_DIR / f"batch_{matching_job_id}"
    dl_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Descargando archivos a {dl_dir}...")
    downloaded = client.batch.download(job_id=matching_job_id, output_dir=dl_dir)

    # 6. Procesar y concatenar con historia existente
    for sym in ["ES", "NQ"]:
        cont_sym = f"{sym}.v.0"
        # Encontrar el archivo DBN descargado para este símbolo
        dbn_file = None
        for p in downloaded:
            if sym.lower() in p.name.lower() and str(p).endswith((".dbn", ".dbn.zst")):
                dbn_file = p
                break
        
        if not dbn_file:
            raise FileNotFoundError(f"No se encontró archivo DBN para {sym}")

        logger.info(f"Cargando DBN 2010-2017 para {sym} desde {dbn_file}...")
        store = db.DBNStore.from_file(dbn_file)
        df_old = store.to_df()
        if "ts_event" not in df_old.columns and df_old.index.name == "ts_event":
            df_old = df_old.reset_index()

        df_old = df_old[["ts_event", "open", "high", "low", "close", "volume"]].copy()

        # Cargar historia existente 2017-2026
        existing_p = RAW_DIR / f"{cont_sym}_ohlcv_1m.parquet"
        if existing_p.exists():
            logger.info(f"Cargando historia existente 2017-2026 para {sym}...")
            df_existing = pd.read_parquet(existing_p, columns=["ts_event", "open", "high", "low", "close", "volume"])
            df_consolidated = pd.concat([df_old, df_existing], ignore_index=True)
        else:
            df_consolidated = df_old

        df_consolidated = df_consolidated.sort_values("ts_event").drop_duplicates(subset=["ts_event"]).reset_index(drop=True)
        
        # Validar invariantes
        validate_ohlcv_invariants(df_consolidated)

        # Guardar 1m consolidado
        df_consolidated.to_parquet(existing_p, index=False)
        logger.info(
            f"Consolidado {sym} guardado en {existing_p}: "
            f"{len(df_consolidated)} barras desde {df_consolidated['ts_event'].iloc[0]} hasta {df_consolidated['ts_event'].iloc[-1]}"
        )

        # 7. Remuestrear a 4h
        logger.info(f"Remuestreando {sym} a 4h...")
        df_4h = resample_ohlcv_bars(df_consolidated, target_timeframe="4h", asset_family="indices")
        out_4h = PROCESSED_DIR / f"{sym}_4h.parquet"
        df_4h.to_parquet(out_4h, index=False)
        logger.info(f"Guardado {out_4h}: {len(df_4h)} barras de 4h.")


if __name__ == "__main__":
    main()
