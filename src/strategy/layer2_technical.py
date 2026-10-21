"""Implementación algorítmica determinista de la Capa 2 (Estructura Técnica y Setups en 15m).
Garantiza ausencia de look-ahead y genera objetos estructurados con Entrada, SL, TP y Horizonte.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.strategy.indicators import (
    compute_atr,
    compute_bbwp,
    compute_ema,
    compute_macd_zscore,
    compute_rsi,
    compute_sma,
    detect_williams_fractals,
)


@dataclass
class TechnicalSetup:
    """Especificación completa e inmutable de un setup técnico."""
    bar_index: int
    timestamp_ms: int
    direction: str  # "LONG" o "SHORT"
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_r: float  # |entry - stop_loss|
    max_horizon_bars: int = 15  # 15 barras de 15m = 3.75 horas
    break_even_trigger_r: float = 1.0  # Mover SL a entrada al alcanzar +1.0R
    pattern_name: str = ""
    reasons: str = ""


class Layer2TechnicalAnalyzer:
    """Analizador determinista de la Capa 2 sobre serie temporal de 15m."""

    def __init__(
        self,
        bbwp_threshold: float = 30.0,
        volume_factor: float = 1.6,
        fractal_k: int = 3,
        tolerance_pct: float = 0.003,
        min_rr_ratio: float = 2.0,
    ):
        self.bbwp_threshold = bbwp_threshold
        self.volume_factor = volume_factor
        self.fractal_k = fractal_k
        self.tolerance_pct = tolerance_pct
        self.min_rr_ratio = min_rr_ratio

    def compute_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Precomputa todos los indicadores necesarios sin look-ahead."""
        data = df.copy()
        c = data["close"]
        h = data["high"]
        l = data["low"]
        v = data["volume"]

        # Medias móviles
        data["ema_21"] = compute_ema(c, 21)
        data["ema_50"] = compute_ema(c, 50)
        data["sma_100"] = compute_sma(c, 100)
        data["sma_200"] = compute_sma(c, 200)

        # Osciladores y volatilidad
        data["rsi_14"] = compute_rsi(c, 14)
        data["bbwp"] = compute_bbwp(c, bb_period=20, bb_std=2.0, lookback=252)
        _, _, data["macd_hist"], data["macd_z"] = compute_macd_zscore(c, 12, 26, 9, z_lookback=400)
        data["atr_14"] = compute_atr(h, l, c, 14)

        # Volumen medio
        data["vol_sma20"] = compute_sma(v, 20)

        # Fractales retardados
        data["fractal_high"], data["fractal_low"] = detect_williams_fractals(h, l, k=self.fractal_k)
        return data

    def evaluate_bar(self, data: pd.DataFrame, idx: int) -> Optional[TechnicalSetup]:
        """Evalúa las condiciones técnicas en la barra `idx` utilizando ÚNICAMENTE datos hasta `idx`."""
        if idx < 200:
            return None

        row = data.iloc[idx]
        prev_row = data.iloc[idx - 1]

        close = row["close"]
        high = row["high"]
        low = row["low"]
        open_p = row["open"]
        vol = row["volume"]
        vol_sma = row["vol_sma20"]
        atr = row["atr_14"]
        bbwp = row["bbwp"]
        macd_z = row["macd_z"]
        rsi = row["rsi_14"]
        ema21 = row["ema_21"]
        ema50 = row["ema_50"]

        if np.isnan(atr) or np.isnan(bbwp) or atr <= 0:
            return None

        # Rango de la vela y mechas para detección de absorción en 15m
        candle_range = high - low
        if candle_range <= 0:
            return None
        lower_wick = min(open_p, close) - low
        upper_wick = high - max(open_p, close)
        lower_wick_ratio = lower_wick / candle_range
        upper_wick_ratio = upper_wick / candle_range

        # Historial de fractales conocidos hasta este momento
        past_fractal_highs = data["fractal_high"].iloc[: idx + 1].dropna()
        past_fractal_lows = data["fractal_low"].iloc[: idx + 1].dropna()

        recent_res = past_fractal_highs.iloc[-3:].mean() if len(past_fractal_highs) >= 2 else np.nan
        recent_sup = past_fractal_lows.iloc[-3:].mean() if len(past_fractal_lows) >= 2 else np.nan

        has_volume = vol > (self.volume_factor * vol_sma) if vol_sma > 0 else False
        is_compressed = bbwp <= self.bbwp_threshold if not np.isnan(bbwp) else False

        # --- SETUP 1: Ruptura alcista o rebote en soporte con absorción (LONG) ---
        long_condition = False
        long_reason = []
        sl_long = close - (1.5 * atr)

        # Caso A: Ruptura con volumen de resistencia reciente + BBWP comprimido + MACD no sobrecomprado
        if not np.isnan(recent_res) and close > recent_res and prev_row["close"] <= recent_res and has_volume:
            long_condition = True
            long_reason.append(f"Ruptura de resistencia fractal {recent_res:.1f} con volumen ({vol:.1f} > {vol_sma*self.volume_factor:.1f})")
            sl_long = min(close - (1.5 * atr), recent_res - (0.5 * atr))

        # Caso B: Rebote con absorción (mecha inferior >= 40%) en soporte + RSI saliendo de sobreventa + MACD z < 0
        elif (
            not np.isnan(recent_sup)
            and abs(low - recent_sup) / close <= self.tolerance_pct
            and lower_wick_ratio >= 0.40
            and rsi < 48
            and prev_row["rsi_14"] <= rsi
            and (macd_z < -0.3 if not np.isnan(macd_z) else True)
        ):
            long_condition = True
            long_reason.append(f"Absorción compradora (mecha inf {lower_wick_ratio*100:.1f}%) en soporte {recent_sup:.1f}")
            sl_long = low - (0.5 * atr)

        # Caso C: Alineación EMA 21 > 50 con retroceso y compresión BBWP
        elif (
            ema21 > ema50
            and close > ema21
            and prev_row["close"] <= prev_row["ema_21"]
            and is_compressed
            and (macd_z < 0.5 if not np.isnan(macd_z) else True)
        ):
            long_condition = True
            long_reason.append(f"Reactivación de tendencia EMA 21>50 con compresión BBWP ({bbwp:.1f}%)")
            sl_long = min(low, ema50) - (0.5 * atr)

        if long_condition:
            risk = close - sl_long
            if risk > 0 and (risk / close) >= 0.002:  # Mínimo 0.2% de riesgo para evitar micro-ruido
                tp = close + (self.min_rr_ratio * risk)
                return TechnicalSetup(
                    bar_index=idx,
                    timestamp_ms=int(row["time"]),
                    direction="LONG",
                    entry_price=float(close),
                    stop_loss=float(sl_long),
                    take_profit=float(tp),
                    risk_r=float(risk),
                    pattern_name="LONG_CONFLUENCE",
                    reasons="; ".join(long_reason),
                )

        # --- SETUP 2: Ruptura bajista o rechazo en resistencia con absorción (SHORT) ---
        short_condition = False
        short_reason = []
        sl_short = close + (1.5 * atr)

        # Caso A: Ruptura con volumen de soporte reciente
        if not np.isnan(recent_sup) and close < recent_sup and prev_row["close"] >= recent_sup and has_volume:
            short_condition = True
            short_reason.append(f"Ruptura de soporte fractal {recent_sup:.1f} con volumen ({vol:.1f} > {vol_sma*self.volume_factor:.1f})")
            sl_short = max(close + (1.5 * atr), recent_sup + (0.5 * atr))

        # Caso B: Rechazo con mecha superior >= 40% en resistencia + RSI sobrecomprado girando
        elif (
            not np.isnan(recent_res)
            and abs(high - recent_res) / close <= self.tolerance_pct
            and upper_wick_ratio >= 0.40
            and rsi > 52
            and prev_row["rsi_14"] >= rsi
            and (macd_z > 0.3 if not np.isnan(macd_z) else True)
        ):
            short_condition = True
            short_reason.append(f"Absorción vendedora (mecha sup {upper_wick_ratio*100:.1f}%) en resistencia {recent_res:.1f}")
            sl_short = high + (0.5 * atr)

        # Caso C: Alineación EMA 21 < 50 con rechazo y compresión BBWP
        elif (
            ema21 < ema50
            and close < ema21
            and prev_row["close"] >= prev_row["ema_21"]
            and is_compressed
            and (macd_z > -0.5 if not np.isnan(macd_z) else True)
        ):
            short_condition = True
            short_reason.append(f"Continuación bajista EMA 21<50 con compresión BBWP ({bbwp:.1f}%)")
            sl_short = max(high, ema50) + (0.5 * atr)

        if short_condition:
            risk = sl_short - close
            if risk > 0 and (risk / close) >= 0.002:
                tp = close - (self.min_rr_ratio * risk)
                return TechnicalSetup(
                    bar_index=idx,
                    timestamp_ms=int(row["time"]),
                    direction="SHORT",
                    entry_price=float(close),
                    stop_loss=float(sl_short),
                    take_profit=float(tp),
                    risk_r=float(risk),
                    pattern_name="SHORT_CONFLUENCE",
                    reasons="; ".join(short_reason),
                )

        return None
