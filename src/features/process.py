"""Procesamiento y generación del dataset diario de características y señales para futuros CME.
Transforma los datos crudos de 1 minuto en una serie temporal diaria limpia y validada,
garantizando estrictamente:
1. Calendario XNYS con exclusión de feriados y cierres anticipados.
2. Identificación del cierre del día hábil anterior (15:59 ET) como base para r1 y el gap overnight.
3. Ausencia de look-ahead mediante filtros de volatilidad expansivos con shift(1) estricto.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from src.data.calendar import get_market_sessions, utc_to_et, TIMEZONE_ET
from src.features.build import (
    compute_daily_intraday_features,
    compute_expanding_volatility_filters,
    generate_hypothesis_signals,
)

logger = logging.getLogger(__name__)

PROCESSED_DATA_DIR = Path("data/processed")


def process_symbol_features(
    raw_parquet_path: Path,
    symbol: str,
    start_session: str = "2018-01-02",
    end_session: str = "2026-10-20",
    min_expanding_history: int = 250,
) -> pd.DataFrame:
    """Procesa el archivo crudo de 1 minuto y genera el DataFrame diario de features y señales."""
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Cargando datos crudos de 1 minuto desde {raw_parquet_path}...")
    
    # Cargar solo columnas necesarias
    cols = ["ts_event", "open", "high", "low", "close", "volume"]
    df = pd.read_parquet(raw_parquet_path, columns=cols)

    # Convertir timestamps a America/New_York
    logger.info("Convirtiendo marcas temporales a zona horaria America/New_York...")
    df["ts_event_dt"] = pd.to_datetime(df["ts_event"], utc=True)
    df["dt_et"] = utc_to_et(df["ts_event_dt"])
    df["session_date"] = df["dt_et"].dt.strftime("%Y-%m-%d")
    df["time_et_str"] = df["dt_et"].dt.strftime("%H:%M")

    # Obtener sesiones hábiles regulares según calendario XNYS
    valid_sessions, early_closes = get_market_sessions(start_date="2017-12-15", end_date=end_session)
    valid_sessions_set = set(s.strftime("%Y-%m-%d") for s in valid_sessions)

    # Filtrar solo sesiones regulares
    df = df[df["session_date"].isin(valid_sessions_set)].copy()

    # Agrupar por sesión
    grouped = {k: v for k, v in df.groupby("session_date")}
    sorted_sessions = sorted(list(grouped.keys()))

    # Mapear precio de cierre de la barra 15:59 ET por sesión
    session_closes: Dict[str, float] = {}
    for sess, day_data in grouped.items():
        bar_1559 = day_data[day_data["time_et_str"] == "15:59"]
        if not bar_1559.empty:
            session_closes[sess] = float(bar_1559.iloc[-1]["close"])

    daily_rows = []
    # Procesar desde la fecha de inicio solicitada (usando la sesión previa para prev_close)
    target_sessions = [s for s in sorted_sessions if s >= start_session and s <= end_session]
    logger.info(f"Calculando features intradía para {len(target_sessions)} sesiones regulares...")

    for i, sess in enumerate(target_sessions):
        # Encontrar la sesión previa que tenga cierre 15:59 registrado
        sess_idx = sorted_sessions.index(sess)
        prev_sess = sorted_sessions[sess_idx - 1] if sess_idx > 0 else None
        prev_close = session_closes.get(prev_sess) if prev_sess else None

        day_data = grouped[sess]
        feats = compute_daily_intraday_features(day_df=day_data, prev_close_price=prev_close)
        if feats is not None:
            feats["date"] = sess
            daily_rows.append(feats)

    features_df = pd.DataFrame(daily_rows)
    features_df["date"] = pd.to_datetime(features_df["date"])
    features_df = features_df.sort_values("date").reset_index(drop=True)

    # Aplicar filtros de volatilidad expansivos (estricto shift(1))
    logger.info("Aplicando filtros de volatilidad expansivos...")
    features_df = compute_expanding_volatility_filters(
        features_df,
        min_history_days=min_expanding_history,
    )

    # Generar señales direccionales
    logger.info("Generando señales direccionales para hipótesis H1-H4, B1, B3, E1-E3...")
    features_df = generate_hypothesis_signals(features_df)

    # Guardar en data/processed
    out_path = PROCESSED_DATA_DIR / f"{symbol}_daily_features.parquet"
    features_df.to_parquet(out_path, index=False)
    logger.info(f"Dataset de features diario guardado en {out_path} ({len(features_df)} sesiones).")

    return features_df
