"""Módulo de persistencia determinista en Apache Parquet con verificación SHA-256."""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


def compute_sha256(file_path: Path) -> str:
    """Calcula el hash criptográfico SHA-256 del archivo dado."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def save_dataset_with_manifest(
    df: pd.DataFrame,
    target_parquet_path: Path,
    manifest_path: Optional[Path] = None,
    source_info: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Guarda un DataFrame validado en formato Parquet y actualiza el archivo de manifiesto con SHA-256."""
    target_parquet_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(target_parquet_path, index=False)

    file_hash = compute_sha256(target_parquet_path)
    file_size_bytes = target_parquet_path.stat().st_size

    manifest_entry = {
        "file": target_parquet_path.name,
        "rows": len(df),
        "sha256": file_hash,
        "size_bytes": file_size_bytes,
        "start_time": int(df["time"].iloc[0]) if not df.empty else None,
        "end_time": int(df["time"].iloc[-1]) if not df.empty else None,
        "source": source_info or {},
    }

    if manifest_path is None:
        manifest_path = target_parquet_path.parent / "manifest.json"

    manifest_data = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
        except Exception as e:
            logger.warning(f"No se pudo leer el manifest existente: {e}")

    manifest_data[target_parquet_path.name] = manifest_entry

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    logger.info(f"Guardado {target_parquet_path.name} con SHA-256={file_hash}")
    return manifest_entry


def load_dataset_verified(parquet_path: Path, manifest_path: Optional[Path] = None) -> pd.DataFrame:
    """Carga un dataset en Parquet comprobando que su hash SHA-256 coincide con el manifest."""
    if not parquet_path.exists():
        raise FileNotFoundError(f"Archivo {parquet_path} no existe.")

    if manifest_path is None:
        manifest_path = parquet_path.parent / "manifest.json"

    if manifest_path.exists():
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        entry = manifest_data.get(parquet_path.name)
        if entry and "sha256" in entry:
            actual_hash = compute_sha256(parquet_path)
            expected_hash = entry["sha256"]
            if actual_hash != expected_hash:
                raise ValueError(
                    f"Discrepancia de integridad en {parquet_path.name}: "
                    f"esperado {expected_hash}, calculado {actual_hash}"
                )

    return pd.read_parquet(parquet_path)
