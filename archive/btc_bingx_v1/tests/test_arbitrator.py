"""Pruebas unitarias para el Árbitro de Confluencia y la regla de conflicto anti-trampa."""
from unittest.mock import MagicMock
import pandas as pd
import pytest

from src.strategy.arbitrator import ConfluenceArbitrator
from src.strategy.layer1_macro import Layer1MacroAnalyzer
from src.strategy.layer2_technical import Layer2TechnicalAnalyzer, TechnicalSetup
from src.strategy.layer3_orderflow import Layer3MicrostructureAnalyzer


def test_macro_blackout_forces_neutral():
    """Verifica que una ventana de evento macro fuerce abstención (NEUTRAL)."""
    l1 = Layer1MacroAnalyzer(event_blackout_minutes=60)
    # Evento de CPI en t=1000000000
    l1.load_economic_events([{"timestamp_ms": 1000000000, "name": "US CPI MoM", "impact": "HIGH"}])
    
    l2 = MagicMock(spec=Layer2TechnicalAnalyzer)
    # Simulamos que Capa 2 tiene un setup alcista espectacular
    fake_setup = TechnicalSetup(
        bar_index=10, timestamp_ms=1000000000, direction="LONG",
        entry_price=65000, stop_loss=64000, take_profit=68000, risk_r=1000
    )
    l2.evaluate_bar.return_value = fake_setup

    arbitrator = ConfluenceArbitrator(layer1=l1, layer2=l2)
    fake_df = pd.DataFrame([{"time": 1000000000, "open": 65000, "high": 65100, "low": 64900, "close": 65050, "volume": 100, "vol_sma20": 80}])

    decision = arbitrator.evaluate_bar(fake_df, idx=0)
    assert decision.action == "NEUTRAL"
    assert "ABSTENCIÓN MACRO" in decision.primary_reason
    assert decision.setup is None


def test_anti_trap_rule_bull_trap():
    """Verifica que un setup LONG frente a un sesgo macro BAJISTA sea neutralizado como trampa."""
    l1 = Layer1MacroAnalyzer()
    # F&G en 85 (codicia extrema -> sesgo BAJISTA pro-toma de ganancias / prohíbe largos)
    l1.load_fng_data([{"timestamp": "1700000", "value": "85"}])

    l2 = MagicMock(spec=Layer2TechnicalAnalyzer)
    fake_setup = TechnicalSetup(
        bar_index=10, timestamp_ms=1700000000 + 360000, direction="LONG",
        entry_price=65000, stop_loss=64000, take_profit=68000, risk_r=1000
    )
    l2.evaluate_bar.return_value = fake_setup

    arbitrator = ConfluenceArbitrator(layer1=l1, layer2=l2)
    fake_df = pd.DataFrame([{"time": 1700000000 + 360000, "open": 65000, "high": 65100, "low": 64900, "close": 65050, "volume": 100, "vol_sma20": 80}])

    decision = arbitrator.evaluate_bar(fake_df, idx=0)
    assert decision.action == "NEUTRAL"
    assert decision.is_trap_prevented is True
    assert "TRAMPA EVITADA (Bull Trap)" in decision.primary_reason
    assert decision.setup is None


def test_full_alignment_emits_trade():
    """Verifica que con alineación total se apruebe la operación."""
    l1 = Layer1MacroAnalyzer()
    # F&G en 20 (miedo extremo -> sesgo ALCISTA)
    l1.load_fng_data([{"timestamp": "1700000", "value": "20"}])

    l2 = MagicMock(spec=Layer2TechnicalAnalyzer)
    fake_setup = TechnicalSetup(
        bar_index=10, timestamp_ms=1700000000 + 360000, direction="LONG",
        entry_price=65000, stop_loss=64000, take_profit=68000, risk_r=1000,
        pattern_name="LONG_CONFLUENCE"
    )
    l2.evaluate_bar.return_value = fake_setup

    l3 = MagicMock(spec=Layer3MicrostructureAnalyzer)
    l3.evaluate_bar.return_value = MagicMock(status="CONFIRMA", reasons="Mecha inferior 45%")

    arbitrator = ConfluenceArbitrator(layer1=l1, layer2=l2, layer3=l3, require_layer3_confirmation=True)
    fake_df = pd.DataFrame([{"time": 1700000000 + 360000, "open": 65000, "high": 65100, "low": 64900, "close": 65050, "volume": 100, "vol_sma20": 80}])

    decision = arbitrator.evaluate_bar(fake_df, idx=0)
    assert decision.action == "LONG"
    assert decision.setup is not None
    assert decision.setup.direction == "LONG"
    assert "Confluencia alineada" in decision.primary_reason
