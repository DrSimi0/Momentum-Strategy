"""Pruebas unitarias para el despachador de alertas, paper trading y la salvaguarda del ejecutor."""
from pathlib import Path
import json
import pytest
import pandas as pd

from src.alerts.dispatcher import AlertDispatcher
from src.execution.executor_interface import SafeNullExecutor
from src.paper_trading.engine import PaperTradingEngine, PaperPosition
from src.strategy.arbitrator import ConfluenceDecision
from src.strategy.layer1_macro import MacroContextOutput
from src.strategy.layer2_technical import TechnicalSetup


def test_safe_null_executor_blocks_orders():
    """Verifica que el ejecutor seguro bloquee cualquier orden real por defecto."""
    executor = SafeNullExecutor(allow_real_execution=False)
    res = executor.place_order(symbol="BTC-USDT", side="BUY", order_type="MARKET", quantity=0.1)
    assert res["status"] == "BLOCKED_BY_SAFETY_GUARD"
    assert "Ejecución bloqueada deterministamente" in res["message"]


def test_alert_dispatcher_records_jsonl(tmp_path: Path):
    """Verifica que las alertas se registren fielmente en formato JSONL inmutable."""
    log_file = tmp_path / "test_signals.jsonl"
    dispatcher = AlertDispatcher(log_file=log_file)

    macro_out = MacroContextOutput(timestamp_ms=1700000000000, bias="ALCISTA", reasons=["F&G bajo"])
    setup = TechnicalSetup(
        bar_index=5, timestamp_ms=1700000000000, direction="LONG",
        entry_price=60000.0, stop_loss=59000.0, take_profit=63000.0, risk_r=1000.0
    )
    decision = ConfluenceDecision(
        bar_index=5,
        timestamp_ms=1700000000000,
        action="LONG",
        setup=setup,
        macro_output=macro_out,
        micro_output=None,
        primary_reason="Alineación alcista confirmada",
    )

    payload = dispatcher.dispatch(decision, symbol="BTC-USDT")
    assert payload["action"] == "LONG"
    assert payload["symbol"] == "BTC-USDT"

    # Verificar lectura de JSONL
    assert log_file.exists()
    with open(log_file, "r", encoding="utf-8") as f:
        line = json.loads(f.readline())
    assert line["action"] == "LONG"
    assert line["setup"]["entry_price"] == 60000.0


def test_paper_trading_breakeven_update(tmp_path: Path):
    """Verifica que el motor de paper trading active break-even ante movimientos favorables."""
    engine = PaperTradingEngine(
        arbitrator=None, # No se evalúa barra en este test unitario aislado
        dispatcher=AlertDispatcher(log_file=tmp_path / "paper_log.jsonl"),
        state_file=tmp_path / "paper_state.json",
    )
    # Simular posición activa LONG con R = 1000 USDT (Entrada 60000, SL 59000)
    engine.active_position = PaperPosition(
        symbol="BTC-USDT",
        direction="LONG",
        entry_price=60000.0,
        entry_time_utc="2026-10-20T20:00:00Z",
        stop_loss=59000.0,
        take_profit=63000.0,
        risk_r=1000.0,
        max_bars=15,
    )

    # Barra donde el precio alcanza High = 61100 (supera Entrada + 1.0R = 61000)
    bar = pd.Series({"high": 61100.0, "low": 60200.0, "close": 60800.0})
    engine._update_active_position(bar)

    assert engine.active_position is not None
    assert engine.active_position.be_active is True
    assert engine.active_position.stop_loss == 60000.0  # Stop desplazado a la entrada
