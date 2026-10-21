"""Módulo de validación estricta de datos OHLCV para velas de BingX.
Garantiza ausencia de lookahead por velas en formación, detecta huecos y verifica invariantes.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

INTERVAL_MS_MAP = {
    "1m": 60 * 1000,
    "3m": 3 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}


class DataValidationError(Exception):
    """Excepción lanzada cuando los datos de mercado violan invariantes no recuperables."""
    pass


def parse_and_validate_klines(
    raw_klines: List[Dict[str, Any]],
    interval: str = "15m",
    current_time_ms: Optional[int] = None,
    allow_gaps: bool = False,
) -> pd.DataFrame:
    """Convierte velas de BingX a DataFrame limpio, cronológicamente ordenado y validado.

    Reglas deterministas aplicadas:
    1. Orden descendente original se invierte a cronológico ascendente estricto.
    2. Si `timestamp + interval_ms > current_time_ms`, la vela se descarta por estar incompleta (vela abierta).
    3. Validación de invariantes OHLCV: High >= max(Open, Close), Low <= min(Open, Close), Volume >= 0.
    4. Detección y eliminación de timestamps duplicados.
    5. Detección de huecos temporales mayores al intervalo esperado.
    """
    if not raw_klines:
        return pd.DataFrame(columns=["time", "open", "high", "low", "close", "volume"])

    interval_ms = INTERVAL_MS_MAP.get(interval)
    if interval_ms is None:
        raise ValueError(f"Intervalo '{interval}' no soportado. Disponibles: {list(INTERVAL_MS_MAP.keys())}")

    # Estructurar registros
    parsed_records = []
    for k in raw_klines:
        try:
            t = int(k["time"])
            o = float(k["open"])
            h = float(k["high"])
            l = float(k["low"])
            c = float(k["close"])
            v = float(k.get("volume", 0.0))
        except (KeyError, ValueError, TypeError) as err:
            raise DataValidationError(f"Fila con formato inválido: {k}") from err

        # Invariantes OHLCV
        if h < max(o, c) - 1e-8 or l > min(o, c) + 1e-8:
            raise DataValidationError(f"Invariante OHLC violado en t={t}: O={o}, H={h}, L={l}, C={c}")
        if v < 0:
            raise DataValidationError(f"Volumen negativo en t={t}: {v}")

        parsed_records.append({"time": t, "open": o, "high": h, "low": l, "close": c, "volume": v})

    df = pd.DataFrame(parsed_records)

    # 1. Eliminar duplicados exactos en timestamp
    df = df.drop_duplicates(subset=["time"])

    # 2. Orden cronológico ascendente
    df = df.sort_values(by="time", ascending=True).reset_index(drop=True)

    # 3. Descarte de vela abierta (en formación)
    if current_time_ms is not None:
        closed_mask = (df["time"] + interval_ms) <= current_time_ms
        n_open = (~closed_mask).sum()
        if n_open > 0:
            logger.info(f"Descartadas {n_open} velas en formación (abiertas) para evitar lookahead.")
            df = df[closed_mask].reset_index(drop=True)

    if df.empty:
        return df

    # 4. Chequeo de continuidad temporal
    time_diffs = df["time"].diff().iloc[1:]
    unexpected_diffs = time_diffs[time_diffs != interval_ms]
    if not unexpected_diffs.empty:
        gap_indices = unexpected_diffs.index
        gaps_info = [
            (df.loc[idx - 1, "time"], df.loc[idx, "time"], df.loc[idx, "time"] - df.loc[idx - 1, "time"])
            for idx in gap_indices
        ]
        msg = f"Se detectaron {len(gaps_info)} huecos temporales en los datos de {interval}: {gaps_info[:3]}"
        if not allow_gaps:
            raise DataValidationError(msg)
        else:
            logger.warning(msg)

    # Añadir columna legible de fecha en UTC
    df["datetime_utc"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    return df
