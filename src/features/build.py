"""Cálculo determinista de características (features) y señales intradía sin fuga de futuro (no look-ahead).
Implementa r1, r12, r13, E1-E3, volatilidad de la primera media hora y mediana expansiva.
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def compute_daily_intraday_features(
    day_df: pd.DataFrame,
    prev_close_price: Optional[float],
) -> Optional[Dict[str, float]]:
    """Calcula los retornos logarítmicos del día para barras de 1 minuto etiquetadas con time_et (HH:MM).
    
    Barras necesarias:
    - 09:30 (open de sesión regular)
    - 09:59 (cierre de primera media hora)
    - 15:00 (open de penúltima media hora)
    - 15:29 (cierre de penúltima media hora)
    - 15:30 (open de última media hora: ENTRADA)
    - 15:59 (cierre de última media hora: SALIDA)
    """
    if prev_close_price is None or prev_close_price <= 0:
        return None

    # Mapear barras por hora ET
    by_time = {}
    for _, row in day_df.iterrows():
        t_str = row["time_et_str"]
        by_time[t_str] = row

    # Verificar presencia de barras críticas
    critical = ["09:59", "15:00", "15:29", "15:30", "15:59"]
    for c in critical:
        if c not in by_time:
            return None

    c_0959 = float(by_time["09:59"]["close"])
    o_1500 = float(by_time["15:00"]["open"])
    c_1529 = float(by_time["15:29"]["close"])
    o_1530 = float(by_time["15:30"]["open"])
    c_1559 = float(by_time["15:59"]["close"])

    # Barra 09:30 (para E1 y E2, si está presente)
    o_0930 = float(by_time["09:30"]["open"]) if "09:30" in by_time else None

    # 1. Definiciones principales (§3.3)
    # r1: retorno desde el cierre previo hasta 10:00 ET (close 09:59)
    r1 = math.log(c_0959 / prev_close_price)
    # r12: retorno penúltima media hora (15:00 a 15:30)
    r12 = math.log(c_1529 / o_1500)
    # r13: retorno última media hora (15:30 a 16:00: OBJETIVO)
    r13 = math.log(c_1559 / o_1530)

    # 2. Variantes exploratorias (§3.5)
    e1 = math.log(c_0959 / o_0930) if o_0930 is not None else np.nan
    e2 = math.log(o_0930 / prev_close_price) if o_0930 is not None else np.nan
    e3 = math.log(o_1530 / c_0959)

    # 3. Volatilidad realizada de la primera media hora (09:30 a 09:59)
    first_half_hour = day_df[(day_df["time_et_str"] >= "09:30") & (day_df["time_et_str"] <= "09:59")]
    if len(first_half_hour) >= 20:
        minute_rets = first_half_hour["close"].pct_change().dropna()
        realized_vol = float(minute_rets.std(ddof=1)) if len(minute_rets) > 1 else np.nan
    else:
        realized_vol = np.nan

    return {
        "prev_close": prev_close_price,
        "entry_price": o_1530,
        "exit_price": c_1559,
        "r1": r1,
        "r12": r12,
        "r13": r13,
        "e1": e1,
        "e2": e2,
        "e3": e3,
        "first_30m_vol": realized_vol,
    }


def compute_expanding_volatility_filters(
    features_df: pd.DataFrame,
    min_history_days: int = 250,
) -> pd.DataFrame:
    """Calcula la mediana y los terciles de volatilidad mediante ventana EXPANSIVA estricta.
    
    Para el día t, el umbral se calcula ÚNICAMENTE con los datos disponibles antes de t (shift(1)).
    Prohibido usar datos del día t o posteriores (garantía anti-lookahead).
    """
    df = features_df.copy()
    n = len(df)
    vol_median = np.full(n, np.nan)
    vol_tercile_low = np.full(n, np.nan)
    vol_tercile_high = np.full(n, np.nan)

    vols = df["first_30m_vol"].values

    for i in range(min_history_days, n):
        # Tomar valores estrictamente anteriores a i (de 0 a i-1)
        history = vols[:i]
        valid_history = history[~np.isnan(history)]
        if len(valid_history) >= min_history_days:
            vol_median[i] = float(np.median(valid_history))
            vol_tercile_low[i] = float(np.quantile(valid_history, 1.0 / 3.0))
            vol_tercile_high[i] = float(np.quantile(valid_history, 2.0 / 3.0))

    df["vol_expanding_median"] = vol_median
    df["vol_tercile_low"] = vol_tercile_low
    df["vol_tercile_high"] = vol_tercile_high
    # Filtro H4: Volatilidad de hoy > mediana histórica
    df["h4_vol_filter_active"] = (df["first_30m_vol"] > df["vol_expanding_median"]) & (~df["vol_expanding_median"].isna())
    return df


def generate_hypothesis_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Genera las señales direccionales (-1, 0, +1) para cada una de las hipótesis."""
    out = df.copy()

    # H1: Signo de r1
    out["sig_H1"] = np.sign(out["r1"]).fillna(0).astype(int)

    # H2: Signo de r12
    out["sig_H2"] = np.sign(out["r12"]).fillna(0).astype(int)

    # H3: Combinada (solo opera si sign(r1) == sign(r12))
    h3_sig = np.where(out["sig_H1"] == out["sig_H2"], out["sig_H1"], 0)
    out["sig_H3"] = h3_sig

    # H4: H1 con filtro de volatilidad expansivo
    h4_sig = np.where(out["h4_vol_filter_active"], out["sig_H1"], 0)
    out["sig_H4"] = h4_sig

    # Líneas base
    out["sig_B1"] = 1  # Siempre long
    out["sig_B3"] = -out["sig_H1"]  # Contraria a H1

    # Exploratorias
    out["sig_E1"] = np.sign(out["e1"]).fillna(0).astype(int)
    out["sig_E2"] = np.sign(out["e2"]).fillna(0).astype(int)
    out["sig_E3"] = np.sign(out["e3"]).fillna(0).astype(int)

    return out
