"""Módulo determinista de cálculo de indicadores técnicos sin fuga de futuro (no look-ahead).
Implementa fractales de Williams con confirmación retardada, BBWP, MACD z-score y RSI de Wilder.
"""
from __future__ import annotations

from typing import List, Optional, Tuple
import numpy as np
import pandas as pd


def compute_ema(series: pd.Series, span: int) -> pd.Series:
    """Calcula Media Móvil Exponencial."""
    return series.ewm(span=span, adjust=False).mean()


def compute_sma(series: pd.Series, window: int) -> pd.Series:
    """Calcula Media Móvil Simple."""
    return series.rolling(window=window, min_periods=window).mean()


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calcula el Relative Strength Index (RSI) clásico de Wilder."""
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    # Suavizado exponencial de Wilder (alpha = 1 / period)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    # Casos donde loss == 0 -> RSI = 100; gain == 0 -> RSI = 0
    rsi = rsi.fillna(100.0 * (avg_gain > 0))
    return rsi


def compute_bbwp(close: pd.Series, bb_period: int = 20, bb_std: float = 2.0, lookback: int = 252) -> pd.Series:
    """Bollinger Band Width Percentile (BBWP).
    
    1. Calcula el ancho de las bandas: (Upper - Lower) / SMA_period.
    2. Calcula el percentil del ancho actual relativo a las últimas `lookback` barras cerradas.
    Retorna un valor entre 0.0 y 100.0.
    """
    sma = compute_sma(close, bb_period)
    rolling_std = close.rolling(window=bb_period, min_periods=bb_period).std(ddof=0)
    upper = sma + (bb_std * rolling_std)
    lower = sma - (bb_std * rolling_std)
    
    band_width = (upper - lower) / sma.replace(0, np.nan)
    
    # Percentil rodante estricto: fracción de barras en lookback donde band_width < band_width_actual
    def _rolling_percentile(window_values: np.ndarray) -> float:
        current = window_values[-1]
        if np.isnan(current):
            return np.nan
        valid = window_values[~np.isnan(window_values)]
        if len(valid) < 2:
            return np.nan
        return float((valid < current).sum() / len(valid) * 100.0)

    bbwp = band_width.rolling(window=lookback, min_periods=max(bb_period, 50)).apply(_rolling_percentile, raw=True)
    return bbwp


def compute_macd_zscore(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    z_lookback: int = 500,
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Calcula MACD normalizado porcentualmente respecto al precio y estandarizado como z-score.
    
    Retorna:
    - macd_pct: (EMA_fast - EMA_slow) / Close
    - signal_pct: EMA_signal(macd_pct)
    - hist_pct: macd_pct - signal_pct
    - macd_zscore: z-score rodante de macd_pct sobre `z_lookback` barras
    """
    ema_fast = compute_ema(close, fast)
    ema_slow = compute_ema(close, slow)
    macd_pct = (ema_fast - ema_slow) / close.replace(0, np.nan)
    signal_pct = compute_ema(macd_pct, signal)
    hist_pct = macd_pct - signal_pct

    rolling_mean = macd_pct.rolling(window=z_lookback, min_periods=50).mean()
    rolling_std = macd_pct.rolling(window=z_lookback, min_periods=50).std(ddof=0).replace(0, np.nan)
    macd_zscore = (macd_pct - rolling_mean) / rolling_std
    return macd_pct, signal_pct, hist_pct, macd_zscore


def detect_williams_fractals(
    high: pd.Series,
    low: pd.Series,
    k: int = 3,
) -> Tuple[pd.Series, pd.Series]:
    """Detecta fractales locales de Williams con confirmación estrictamente retardada en k barras.
    
    Una barra i es un fractal alcista (pivote de techo) si:
        high[i] > high[i-j] para todo j in 1..k
        high[i] > high[i+j] para todo j in 1..k
    
    CRÍTICO PARA LOOKAHEAD: Esta condición SOLO se conoce en el tiempo i + k.
    Por lo tanto, la serie retornada marca el pivote en el índice `i + k` con el valor `high[i]`.
    """
    n = len(high)
    fractal_high = pd.Series(np.nan, index=high.index)
    fractal_low = pd.Series(np.nan, index=low.index)

    high_arr = high.values
    low_arr = low.values

    for i in range(k, n - k):
        # Chequeo máximo fractal
        is_high = True
        for j in range(1, k + 1):
            if high_arr[i] <= high_arr[i - j] or high_arr[i] <= high_arr[i + j]:
                is_high = False
                break
        if is_high:
            # Se conoce y confirma en la barra i + k
            fractal_high.iloc[i + k] = high_arr[i]

        # Chequeo mínimo fractal
        is_low = True
        for j in range(1, k + 1):
            if low_arr[i] >= low_arr[i - j] or low_arr[i] >= low_arr[i + j]:
                is_low = False
                break
        if is_low:
            # Se conoce y confirma en la barra i + k
            fractal_low.iloc[i + k] = low_arr[i]

    return fractal_high, fractal_low


def compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Calcula el Average True Range (ATR) de Wilder."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return atr
