"""Árbitro de Confluencia Jerárquica: Aplica la regla de conflicto anti-trampa y coordina las 3 capas."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import pandas as pd

from src.strategy.layer1_macro import Layer1MacroAnalyzer, MacroContextOutput
from src.strategy.layer2_technical import Layer2TechnicalAnalyzer, TechnicalSetup
from src.strategy.layer3_orderflow import Layer3MicrostructureAnalyzer, MicrostructureOutput


@dataclass
class ConfluenceDecision:
    """Decisión final estructurada emitida por el sistema multi-capa."""
    bar_index: int
    timestamp_ms: int
    action: str  # "LONG", "SHORT", "NEUTRAL"
    setup: Optional[TechnicalSetup]
    macro_output: MacroContextOutput
    micro_output: Optional[MicrostructureOutput]
    primary_reason: str
    is_trap_prevented: bool = False


class ConfluenceArbitrator:
    """Motor determinista que aplica las reglas jerárquicas y resuelve conflictos entre capas."""

    def __init__(
        self,
        layer1: Layer1MacroAnalyzer,
        layer2: Layer2TechnicalAnalyzer,
        layer3: Optional[Layer3MicrostructureAnalyzer] = None,
        require_layer3_confirmation: bool = False,
    ):
        self.layer1 = layer1
        self.layer2 = layer2
        self.layer3 = layer3 or Layer3MicrostructureAnalyzer()
        self.require_layer3_confirmation = require_layer3_confirmation

    def evaluate_bar(
        self,
        market_data_with_indicators: pd.DataFrame,
        idx: int,
        dxy_trend_bearish: Optional[bool] = None,
    ) -> ConfluenceDecision:
        """Evalúa una barra aplicando estrictamente la prelación jerárquica."""
        row = market_data_with_indicators.iloc[idx]
        ts = int(row["time"])

        # 1. Evaluación de Capa 1 (Macro & Sentimiento)
        macro_out = self.layer1.evaluate_bar(ts, dxy_trend_bearish=dxy_trend_bearish)

        # Regla 1.1: Si la Capa 1 dicta abstención, salida obligatoria NEUTRAL
        if macro_out.bias == "ABSTENCION":
            return ConfluenceDecision(
                bar_index=idx,
                timestamp_ms=ts,
                action="NEUTRAL",
                setup=None,
                macro_output=macro_out,
                micro_output=None,
                primary_reason=f"ABSTENCIÓN MACRO: {macro_out.reasons[0]}",
                is_trap_prevented=False,
            )

        # 2. Evaluación de Capa 2 (Estructura Técnica)
        setup = self.layer2.evaluate_bar(market_data_with_indicators, idx)
        if setup is None:
            return ConfluenceDecision(
                bar_index=idx,
                timestamp_ms=ts,
                action="NEUTRAL",
                setup=None,
                macro_output=macro_out,
                micro_output=None,
                primary_reason="Sin setup técnico válido en Capa 2",
                is_trap_prevented=False,
            )

        # 3. Regla de Conflicto (La regla anti-trampa más importante):
        # La capa superior (Capa 1) prevalece sobre la inferior (Capa 2).
        # Un setup alcista frente a un sesgo macro bajista es una trampa de toros (bull trap).
        # Un setup bajista frente a un sesgo macro alcista es una trampa de osos (bear trap).
        if macro_out.bias == "BAJISTA" and setup.direction == "LONG":
            return ConfluenceDecision(
                bar_index=idx,
                timestamp_ms=ts,
                action="NEUTRAL",
                setup=None,
                macro_output=macro_out,
                micro_output=None,
                primary_reason="TRAMPA EVITADA (Bull Trap): Setup técnico LONG contradice sesgo macro BAJISTA",
                is_trap_prevented=True,
            )

        if macro_out.bias == "ALCISTA" and setup.direction == "SHORT":
            return ConfluenceDecision(
                bar_index=idx,
                timestamp_ms=ts,
                action="NEUTRAL",
                setup=None,
                macro_output=macro_out,
                micro_output=None,
                primary_reason="TRAMPA EVITADA (Bear Trap): Setup técnico SHORT contradice sesgo macro ALCISTA",
                is_trap_prevented=True,
            )

        # 4. Evaluación de Capa 3 (Microestructura y confirmación de absorción)
        vol_sma = row.get("vol_sma20", 0.0)
        micro_out = self.layer3.evaluate_bar(
            open_p=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
            vol_sma=float(vol_sma),
            intended_direction=setup.direction,
            timestamp_ms=ts,
        )

        if self.require_layer3_confirmation and micro_out.status == "NO CONFIRMA":
            return ConfluenceDecision(
                bar_index=idx,
                timestamp_ms=ts,
                action="NEUTRAL",
                setup=None,
                macro_output=macro_out,
                micro_output=micro_out,
                primary_reason=f"Sin confirmación de microestructura: {micro_out.reasons}",
                is_trap_prevented=False,
            )

        # 5. Alineación total alcanzada -> Señal operativa válida
        action = setup.direction  # "LONG" o "SHORT"
        return ConfluenceDecision(
            bar_index=idx,
            timestamp_ms=ts,
            action=action,
            setup=setup,
            macro_output=macro_out,
            micro_output=micro_out,
            primary_reason=f"Confluencia alineada: Capa 1={macro_out.bias}, Capa 2={setup.pattern_name}, Capa 3={micro_out.status}",
            is_trap_prevented=False,
        )
