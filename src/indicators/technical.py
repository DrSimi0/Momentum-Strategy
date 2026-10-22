"""Cálculo vectorizado y determinista de indicadores técnicos (SMA, MACD, RSI, ATR).
Estrictamente retrospectivo sin fuga de futuro (no look-ahead).
"""
from __future__ import annotations

from typing import Dict, Tuple
import numpy as np
import pandas as pd


def compute_sma(series: pd.Series, window: int) -> pd.Series:
    """Calcula la Media Móvil Simple (SMA)."""
    return series.rolling(window=window, min_periods=window).mean()


def compute_ema(series: pd.Series, window: int) -> pd.Series:
    """Calcula la Media Móvil Exponencial (EMA)."""
    return series.ewm(span=window, min_periods=window, adjust=False).mean()


def compute_macd(
    close: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calcula la línea MACD, la línea de señal y el histograma.
    
    Returns:
        (macd_line, signal_line, histogram)
    """
    ema_fast = close.ewm(span=fast_period, adjust=False).mean()
    ema_slow = close.ewm(span=slow_period, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Calcula el Índice de Fuerza Relativa (RSI de Wilder)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Suavizado exponencial tipo Wilder (alpha = 1 / window)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # Casos extremos
    rsi = rsi.fillna(50.0)
    rsi = np.where(avg_loss == 0, 100.0, rsi)
    rsi = np.where(avg_gain == 0, 0.0, rsi)
    return pd.Series(rsi, index=close.index)


def compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    window: int = 14,
) -> pd.Series:
    """Calcula el Rango Verdadero Promedio (ATR de Wilder)."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    return atr
