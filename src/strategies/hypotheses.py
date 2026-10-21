"""Definiciones modulares de las hipótesis de trading intradía (Gao et al., 2018).
Implementa las señales direccionales para H1-H4, líneas base B1-B3 y exploratorias E1-E3.
"""
from __future__ import annotations

from typing import Dict, List
import numpy as np
import pandas as pd


def apply_hypotheses_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Añade las columnas de señales (-1: Short, 0: Neutral, +1: Long) al DataFrame diario de características."""
    out = df.copy()

    # H1: Signo de r1 (retorno desde el cierre previo hasta las 10:00 ET)
    out["sig_H1"] = np.sign(out["r1"]).fillna(0).astype(int)

    # H2: Signo de r12 (retorno de la penúltima media hora: 15:00 a 15:30 ET)
    out["sig_H2"] = np.sign(out["r12"]).fillna(0).astype(int)

    # H3: Confluencia (opera solo si r1 y r12 tienen el mismo signo)
    out["sig_H3"] = np.where(out["sig_H1"] == out["sig_H2"], out["sig_H1"], 0)

    # H4: H1 con filtro de volatilidad expansivo (volatilidad > mediana histórica previa, mín. 250 días)
    if "h4_vol_filter_active" in out.columns:
        out["sig_H4"] = np.where(out["h4_vol_filter_active"], out["sig_H1"], 0)
    else:
        out["sig_H4"] = 0

    # Líneas base (Benchmarks)
    out["sig_B1"] = 1  # Siempre Long (15:30 a 16:00 ET)
    out["sig_B3"] = -out["sig_H1"]  # Estrategia contraria a H1

    # Exploratorias (§3.5)
    if "e1" in out.columns:
        out["sig_E1"] = np.sign(out["e1"]).fillna(0).astype(int)
    if "e2" in out.columns:
        out["sig_E2"] = np.sign(out["e2"]).fillna(0).astype(int)
    if "e3" in out.columns:
        out["sig_E3"] = np.sign(out["e3"]).fillna(0).astype(int)

    return out
