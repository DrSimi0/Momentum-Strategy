"""Implementación determinista de la Capa 1: Sesgo Macro y Sentimiento (Point-in-Time).
Filtro direccional y ventanas de abstención obligatorias en torno a eventos de 3 estrellas.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd


@dataclass
class MacroContextOutput:
    """Salida estructurada de la Capa 1."""
    timestamp_ms: int
    bias: str  # "ALCISTA", "BAJISTA", "NEUTRO", "ABSTENCION"
    reasons: List[str]
    fng_value: Optional[float] = None
    in_event_window: bool = False
    event_name: Optional[str] = None


class Layer1MacroAnalyzer:
    """Analizador de contexto macro y sentimiento con garantía Point-in-Time."""

    def __init__(
        self,
        fng_fear_threshold: float = 30.0,
        fng_greed_threshold: float = 70.0,
        event_blackout_minutes: int = 60,
    ):
        self.fng_fear_threshold = fng_fear_threshold
        self.fng_greed_threshold = fng_greed_threshold
        self.event_blackout_minutes = event_blackout_minutes
        self._events_cache: List[Dict[str, Any]] = []
        self._fng_df: Optional[pd.DataFrame] = None

    def load_economic_events(self, events: List[Dict[str, Any]]) -> None:
        """Carga lista de eventos macroeconómicos de 3 estrellas (CPI, PPI, NFP, FOMC).
        Formato esperado por evento: {'timestamp_ms': int, 'name': str, 'impact': 'HIGH'}
        """
        self._events_cache = sorted(events, key=lambda x: x["timestamp_ms"])

    def load_fng_data(self, fng_records: List[Dict[str, Any]]) -> None:
        """Carga serie temporal histórica de Fear & Greed de alternative.me.
        Formato: {'timestamp': '1700000000', 'value': '45'}
        """
        if not fng_records:
            return
        rows = []
        for r in fng_records:
            ts = int(r["timestamp"]) * 1000
            val = float(r["value"])
            rows.append({"time_ms": ts, "fng_value": val})
        df = pd.DataFrame(rows).sort_values("time_ms").reset_index(drop=True)
        # Point-in-Time: El dato de las 00:00 UTC solo está disponible en el pipeline a partir de las 00:05 UTC (+5 min)
        df["available_time_ms"] = df["time_ms"] + (5 * 60 * 1000)
        self._fng_df = df

    def evaluate_bar(self, timestamp_ms: int, dxy_trend_bearish: Optional[bool] = None) -> MacroContextOutput:
        """Evalúa las condiciones macroeconómicas para la barra con timestamp_ms."""
        reasons = []

        # 1. Filtro de abstención por calendario económico (3 estrellas)
        blackout_ms = self.event_blackout_minutes * 60 * 1000
        for ev in self._events_cache:
            ev_ts = ev["timestamp_ms"]
            # Si el timestamp actual está dentro de la ventana de [-60m, +60m] respecto al evento
            if abs(timestamp_ms - ev_ts) <= blackout_ms:
                ev_name = ev.get("name", "Evento Macro de Alto Impacto")
                return MacroContextOutput(
                    timestamp_ms=timestamp_ms,
                    bias="ABSTENCION",
                    reasons=[f"Ventana de abstención activa por evento: {ev_name}"],
                    in_event_window=True,
                    event_name=ev_name,
                )

        # 2. Evaluación de Fear & Greed Point-in-Time
        current_fng = None
        if self._fng_df is not None and not self._fng_df.empty:
            # Obtener el último valor publicado estrictamente antes o en timestamp_ms
            available_records = self._fng_df[self._fng_df["available_time_ms"] <= timestamp_ms]
            if not available_records.empty:
                current_fng = float(available_records["fng_value"].iloc[-1])

        bias = "NEUTRO"
        if current_fng is not None:
            if current_fng < self.fng_fear_threshold:
                bias = "ALCISTA"  # Miedo extremo favorece acumulación / sesgo alcista
                reasons.append(f"Fear & Greed en pánico ({current_fng:.0f} < {self.fng_fear_threshold}): sesgo pro-compras")
            elif current_fng > self.fng_greed_threshold:
                bias = "BAJISTA"  # Codicia extrema favorece toma de beneficios / prohíbe largos
                reasons.append(f"Fear & Greed en euforia ({current_fng:.0f} > {self.fng_greed_threshold}): prohíbe largos")
            else:
                reasons.append(f"Fear & Greed en zona neutral ({current_fng:.0f})")

        # 3. Contexto DXY complementario si está disponible
        if dxy_trend_bearish is True:
            reasons.append("DXY rompiendo a la baja: liquidez macro favorable para cripto")
            if bias == "NEUTRO":
                bias = "ALCISTA"
        elif dxy_trend_bearish is False:
            reasons.append("DXY en tendencia alcista firme: presión bajista sobre cripto")
            if bias == "NEUTRO":
                bias = "BAJISTA"

        if not reasons:
            reasons.append("Contexto macroeconómico en rango neutral sin restricciones activas.")

        return MacroContextOutput(
            timestamp_ms=timestamp_ms,
            bias=bias,
            reasons=reasons,
            fng_value=current_fng,
            in_event_window=False,
        )
