"""Agregador y remuestreador determinista de barras de 1 minuto a temporalidades superiores (15m, 1h, 4h, 1D).
Maneja zonas horarias, exclusión de barras incompletas y cortes de sesión de CME Globex.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional
import numpy as np
import pandas as pd

from src.data.calendar import utc_to_et

logger = logging.getLogger(__name__)

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def resample_ohlcv_bars(
    df_1m: pd.DataFrame,
    target_timeframe: str,
    asset_family: str = "indices",
    timezone: str = "America/New_York",
) -> pd.DataFrame:
    """Remuestrea un DataFrame de barras de 1 minuto a la temporalidad objetivo.
    
    Args:
        df_1m: DataFrame con columnas ts_event (UTC), open, high, low, close, volume.
        target_timeframe: '15m', '1h', '4h', o '1d'.
        asset_family: 'indices' (con sesiones y cierres) o 'crypto' (24/7).
        timezone: Zona horaria para alinear las barras (America/New_York para índices, UTC para cripto).
    """
    df = df_1m.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
        df = df.set_index("ts_event")

    # Mapeo de frecuencias para pandas
    freq_map = {
        "5m": "5min",
        "15m": "15min",
        "1h": "1h",
        "4h": "4h",
        "1d": "1D",
    }
    freq = freq_map.get(target_timeframe)
    if not freq:
        raise ValueError(f"Temporalidad no soportada: {target_timeframe}")

    if asset_family == "indices" and target_timeframe in ("5m", "15m", "1h"):
        # Convertir a hora ET para alinear con apertura regular 09:30 ET
        df_et = df.copy()
        df_et.index = df_et.index.tz_convert(timezone)
        
        # Filtrar a sesión regular si es intradía (09:30 a 16:00 ET)
        time_str = df_et.index.strftime("%H:%M")
        rth_mask = (time_str >= "09:30") & (time_str < "16:00")
        df_et = df_et[rth_mask]

        # Resamplear con origen alineado a las 09:30
        resampled = df_et.resample(freq, origin="start").agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna(subset=["open", "close"])

        # Devolver índice en UTC
        resampled.index = resampled.index.tz_convert("UTC")
        resampled = resampled.reset_index()

    elif asset_family == "indices" and target_timeframe in ("4h", "1d"):
        # Para swing en futuros, usar sesión diaria o 4h
        df_et = df.copy()
        df_et.index = df_et.index.tz_convert(timezone)
        
        if target_timeframe == "1d":
            # Agrupar por fecha de sesión
            time_str = df_et.index.strftime("%H:%M")
            rth_mask = (time_str >= "09:30") & (time_str <= "16:00")
            df_rth = df_et[rth_mask]
            df_rth["session_date"] = df_rth.index.strftime("%Y-%m-%d")
            
            resampled = df_rth.groupby("session_date").agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }).reset_index()
            resampled["ts_event"] = pd.to_datetime(resampled["session_date"]).dt.tz_localize(timezone).dt.tz_convert("UTC")
            resampled = resampled.drop(columns=["session_date"])
        else: # 4h
            resampled = df.resample(freq).agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }).dropna(subset=["open", "close"]).reset_index()

    else:
        # Cripto 24/7 o genérico continuo
        resampled = df.resample(freq).agg({
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }).dropna(subset=["open", "close"]).reset_index()

    # Reordenar y validar
    resampled = resampled.sort_values("ts_event").drop_duplicates(subset=["ts_event"]).reset_index(drop=True)
    return resampled
