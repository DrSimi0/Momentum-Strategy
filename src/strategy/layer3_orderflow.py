"""Módulo de la Capa 3: Validación de Microestructura y Flujo de Órdenes.
Incluye evaluador determinista de mechas de absorción y grabador liviano para datos fuera de muestra futuros.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MicrostructureOutput:
    """Salida estructurada de la Capa 3."""
    timestamp_ms: int
    status: str  # "CONFIRMA", "NO CONFIRMA", "NO DISPONIBLE"
    absorption_ratio: float
    volume_ratio: float
    reasons: str


class Layer3MicrostructureAnalyzer:
    """Validador de microestructura determinista y conector de registro en vivo."""

    def __init__(self, min_wick_ratio: float = 0.35, min_volume_ratio: float = 1.2):
        self.min_wick_ratio = min_wick_ratio
        self.min_volume_ratio = min_volume_ratio

    def evaluate_bar(
        self,
        open_p: float,
        high: float,
        low: float,
        close: float,
        volume: float,
        vol_sma: float,
        intended_direction: str,
        timestamp_ms: int,
    ) -> MicrostructureOutput:
        """Evalúa la presencia de absorción de liquidez en la vela de 15m.
        
        Para LONG: Requiere absorción en mínimos (mecha inferior prominente con rechazo comprador).
        Para SHORT: Requiere absorción en máximos (mecha superior prominente con rechazo vendedor).
        """
        candle_range = high - low
        if candle_range <= 0 or vol_sma <= 0:
            return MicrostructureOutput(
                timestamp_ms=timestamp_ms,
                status="NO DISPONIBLE",
                absorption_ratio=0.0,
                volume_ratio=0.0,
                reasons="Rango nulo o volumen no disponible",
            )

        lower_wick = min(open_p, close) - low
        upper_wick = high - max(open_p, close)
        vol_ratio = volume / vol_sma

        if intended_direction == "LONG":
            wick_ratio = lower_wick / candle_range
            confirms = (wick_ratio >= self.min_wick_ratio) and (vol_ratio >= self.min_volume_ratio)
            reasons = (
                f"Mecha inferior {wick_ratio*100:.1f}% >= {self.min_wick_ratio*100:.0f}% "
                f"con ratio volumen {vol_ratio:.2f}x"
            )
        elif intended_direction == "SHORT":
            wick_ratio = upper_wick / candle_range
            confirms = (wick_ratio >= self.min_wick_ratio) and (vol_ratio >= self.min_volume_ratio)
            reasons = (
                f"Mecha superior {wick_ratio*100:.1f}% >= {self.min_wick_ratio*100:.0f}% "
                f"con ratio volumen {vol_ratio:.2f}x"
            )
        else:
            return MicrostructureOutput(
                timestamp_ms=timestamp_ms,
                status="NO DISPONIBLE",
                absorption_ratio=0.0,
                volume_ratio=vol_ratio,
                reasons="Dirección no especificada",
            )

        status = "CONFIRMA" if confirms else "NO CONFIRMA"
        return MicrostructureOutput(
            timestamp_ms=timestamp_ms,
            status=status,
            absorption_ratio=float(wick_ratio),
            volume_ratio=float(vol_ratio),
            reasons=reasons,
        )
