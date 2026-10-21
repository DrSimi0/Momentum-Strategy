"""Validaciones obligatorias de datos OHLCV de 1 minuto (Databento).
Verifica invariantes, monotonicidad, ausencia de duplicados y presencia de barras críticas.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Set, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

CRITICAL_BAR_TIMES = {"09:59", "15:00", "15:29", "15:30", "15:59"}


class DataIntegrityError(Exception):
    """Lanzada cuando se violan invariantes numéricos o de orden temporal."""
    pass


def validate_ohlcv_invariants(df: pd.DataFrame) -> None:
    """Verifica que no existan precios <= 0, high < low o volumen negativo."""
    if df.empty:
        return

    # Invariantes numéricos
    if (df["open"] <= 0).any() or (df["high"] <= 0).any() or (df["low"] <= 0).any() or (df["close"] <= 0).any():
        raise DataIntegrityError("Se encontraron precios menores o iguales a cero.")

    if (df["high"] < df["low"] - 1e-6).any():
        raise DataIntegrityError("Se encontraron barras donde high < low.")

    if (df["volume"] < 0).any():
        raise DataIntegrityError("Se encontró volumen negativo.")

    # Invariantes de envolvente OHLC
    max_oc = np.maximum(df["open"], df["close"])
    min_oc = np.minimum(df["open"], df["close"])
    if (df["high"] < max_oc - 1e-4).any():
        raise DataIntegrityError("Se encontraron barras donde high < max(open, close).")
    if (df["low"] > min_oc + 1e-4).any():
        raise DataIntegrityError("Se encontraron barras donde low > min(open, close).")

    # Monotonicidad temporal
    if not df["ts_event"].is_monotonic_increasing:
        raise DataIntegrityError("Los timestamps ts_event no son estrictamente crecientes.")

    # Duplicados
    if df["ts_event"].duplicated().any():
        raise DataIntegrityError("Se encontraron timestamps ts_event duplicados.")


def check_critical_bars(day_bars_et: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Verifica si en las barras del día están presentes las 5 barras críticas.
    
    day_bars_et debe tener un índice o columna datetime en hora ET.
    Retorna: (is_complete, missing_bars)
    """
    times_present = set(day_bars_et["time_et_str"].values)
    missing = [b for b in CRITICAL_BAR_TIMES if b not in times_present]
    return (len(missing) == 0, missing)
