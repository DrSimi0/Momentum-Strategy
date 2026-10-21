"""Cliente robusto de descarga y caché de datos históricos de Databento.
Utiliza la API Batch de Databento para descargas masivas de múltiples años sin riesgo de timeout por gateway.
Garantiza:
1. Control estricto de costos antes de cualquier petición de datos.
2. Descarga comprimida (.dbn.zst) por símbolo y conversión a Parquet estructurado.
3. Generación determinista de metadatos (data/metadata.json) con hashes SHA-256 de los archivos descargados.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import databento as db
import pandas as pd

from src.settings import get_api_key

logger = logging.getLogger(__name__)

RAW_DATA_DIR = Path("data/raw")
METADATA_PATH = Path("data/metadata.json")


def compute_file_sha256(filepath: Path) -> str:
    """Calcula el hash SHA-256 de un archivo en disco."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192 * 1024):
            h.update(chunk)
    return h.hexdigest()


def get_databento_client() -> db.Historical:
    """Instancia el cliente de Databento con la clave configurada."""
    api_key = get_api_key()
    return db.Historical(api_key)


def estimate_total_cost(
    symbols: List[str],
    start: str,
    end: str,
    dataset: str = "GLBX.MDP3",
    schema: str = "ohlcv-1m",
    stype_in: str = "continuous",
) -> Dict[str, float]:
    """Consulta los costos exactos por símbolo antes de iniciar descargas."""
    client = get_databento_client()
    costs = {}
    total = 0.0
    for sym in symbols:
        c = float(client.metadata.get_cost(
            dataset=dataset,
            symbols=[sym],
            schema=schema,
            start=start,
            end=end,
            stype_in=stype_in,
        ))
        costs[sym] = c
        total += c
    costs["total"] = total
    return costs


def submit_and_download_batch(
    symbols: List[str],
    start_date: str,
    end_date: str,
    dataset: str = "GLBX.MDP3",
    schema: str = "ohlcv-1m",
    stype_in: str = "continuous",
    max_allowed_cost_usd: float = 25.0,
    poll_interval_sec: int = 15,
    timeout_sec: int = 1800,
) -> Dict[str, Path]:
    """Envía un trabajo Batch asíncrono a Databento, espera a que termine y procesa los archivos a Parquet.
    
    Evita los errores 504 Gateway Timeout de las peticiones HTTP directas.
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    client = get_databento_client()

    # 1. Verificación previa de costos
    costs = estimate_total_cost(
        symbols=symbols,
        start=start_date,
        end=end_date,
        dataset=dataset,
        schema=schema,
        stype_in=stype_in,
    )
    total_cost = costs["total"]
    logger.info(f"Costo total estimado verificado: USD {total_cost:.2f} (Límite: USD {max_allowed_cost_usd:.2f})")
    if total_cost > max_allowed_cost_usd:
        raise ValueError(f"Costo estimado ({total_cost:.2f} USD) excede el límite de {max_allowed_cost_usd:.2f} USD.")

    # 2. Comprobar si ya existe un trabajo previo completado para estos símbolos
    existing_jobs = client.batch.list_jobs(since=start_date)
    matching_job_id = None
    for j in existing_jobs:
        if (
            j.get("dataset") == dataset
            and j.get("schema") == schema
            and j.get("state") == "done"
            and all(s in str(j.get("symbols")) for s in symbols)
        ):
            matching_job_id = j["id"]
            logger.info(f"Se encontró trabajo batch previo completado: {matching_job_id}")
            break

    # 3. Si no existe, enviar el nuevo trabajo batch
    if not matching_job_id:
        logger.info(f"Enviando trabajo batch a Databento para {symbols} ({start_date} a {end_date})...")
        job = client.batch.submit_job(
            dataset=dataset,
            symbols=symbols,
            schema=schema,
            start=start_date,
            end=end_date,
            stype_in=stype_in,
            encoding="dbn",
            compression="zstd",
            split_symbols=True,
            split_duration="none",
            delivery="download",
        )
        matching_job_id = job["id"]
        logger.info(f"Trabajo batch enviado exitosamente. Job ID: {matching_job_id}")

    # 4. Esperar a que el trabajo finalice en los servidores de Databento
    start_wait = time.time()
    while True:
        details = client.batch.get_job_details(matching_job_id)
        state = details.get("state")
        progress = details.get("progress", 0)
        logger.info(f"Estado del trabajo {matching_job_id}: {state} ({progress}%)")

        if state == "done":
            break
        elif state in ("expired", "cancelled"):
            raise RuntimeError(f"El trabajo batch {matching_job_id} falló con estado: {state}")

        if time.time() - start_wait > timeout_sec:
            raise TimeoutError(f"Tiempo de espera agotado ({timeout_sec}s) para el trabajo {matching_job_id}.")

        time.sleep(poll_interval_sec)

    # 5. Descargar los archivos del trabajo
    batch_dir = RAW_DATA_DIR / f"batch_{matching_job_id}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Descargando archivos del trabajo {matching_job_id} hacia {batch_dir}...")
    downloaded_paths = client.batch.download(job_id=matching_job_id, output_dir=batch_dir)
    logger.info(f"Archivos descargados ({len(downloaded_paths)}): {[p.name for p in downloaded_paths]}")

    # 6. Convertir los archivos DBN a Parquet consolidado por símbolo
    result_parquets = {}
    for p in downloaded_paths:
        if str(p).endswith((".dbn", ".dbn.zst")):
            logger.info(f"Cargando DBN store desde {p}...")
            store = db.DBNStore.from_file(p)
            df = store.to_df()
            if "ts_event" not in df.columns and df.index.name == "ts_event":
                df = df.reset_index()

            # Identificar a qué símbolo corresponde
            found_sym = None
            if "symbol" in df.columns:
                symbols_in_df = df["symbol"].unique()
                for s in symbols:
                    if any(s in str(val) for val in symbols_in_df):
                        found_sym = s
                        break
            if not found_sym:
                for s in symbols:
                    if s.lower().replace(".", "_") in p.name.lower() or s.lower() in p.name.lower():
                        found_sym = s
                        break

            target_sym = found_sym or symbols[0]
            parquet_path = RAW_DATA_DIR / f"{target_sym}_ohlcv_1m.parquet"
            logger.info(f"Escribiendo {len(df)} barras a {parquet_path}...")
            df = df.sort_values("ts_event").drop_duplicates(subset=["ts_event"]).reset_index(drop=True)
            df.to_parquet(parquet_path, index=False)
            result_parquets[target_sym] = parquet_path

    return result_parquets


def update_data_metadata(
    downloaded_files: Dict[str, Path],
    dataset: str,
    schema: str,
    start_date: str,
    end_date: str,
    costs: Dict[str, float],
) -> Path:
    """Escribe o actualiza data/metadata.json con hashes criptográficos y detalles de la descarga."""
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    metadata = {
        "dataset": dataset,
        "schema": schema,
        "date_range": {
            "start": start_date,
            "end": end_date,
        },
        "costs_usd": costs,
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "files": {},
    }

    for name, path in downloaded_files.items():
        if path.exists():
            metadata["files"][name] = {
                "path": str(path.as_posix()),
                "size_bytes": path.stat().st_size,
                "sha256": compute_file_sha256(path),
            }

    with open(METADATA_PATH, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Metadatos guardados en {METADATA_PATH}")
    return METADATA_PATH
