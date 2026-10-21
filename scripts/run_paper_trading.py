"""Script CLI para ejecutar una ronda de Paper Trading en tiempo real o monitoreo continuo."""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.alerts.dispatcher import AlertDispatcher
from src.data.bingx_client import BingXDataClient
from src.data.validator import parse_and_validate_klines
from src.paper_trading.engine import PaperTradingEngine
from src.strategy.arbitrator import ConfluenceArbitrator
from src.strategy.layer1_macro import Layer1MacroAnalyzer
from src.strategy.layer2_technical import Layer2TechnicalAnalyzer
from src.strategy.layer3_orderflow import Layer3MicrostructureAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("paper_trader")


def run_paper_round(symbol: str = "BTC-USDT", interval: str = "15m") -> None:
    client = BingXDataClient()
    logger.info(f"Consultando últimas 300 velas de {symbol} ({interval}) en BingX...")

    raw_klines = client.get_klines(symbol=symbol, interval=interval, limit=300)
    current_time_ms = int(time.time() * 1000)

    # Validar y descartar estrictamente vela abierta
    df_clean = parse_and_validate_klines(
        raw_klines,
        interval=interval,
        current_time_ms=current_time_ms,
        allow_gaps=True,
    )
    logger.info(f"Velas cerradas y limpias disponibles: {len(df_clean)}")
    if df_clean.empty:
        logger.warning("No hay velas cerradas suficientes.")
        return

    # Inicializar componentes
    layer1 = Layer1MacroAnalyzer()
    layer2 = Layer2TechnicalAnalyzer()
    layer3 = Layer3MicrostructureAnalyzer()
    arbitrator = ConfluenceArbitrator(layer1=layer1, layer2=layer2, layer3=layer3)

    dispatcher = AlertDispatcher(log_file=ROOT / "reports" / "signals_log.jsonl")
    paper_engine = PaperTradingEngine(arbitrator=arbitrator, dispatcher=dispatcher, state_file=ROOT / "reports" / "paper_trading_state.json")

    decision = paper_engine.process_closed_bars(df_clean, symbol=symbol)
    logger.info(f"Decisión emitida para última barra cerrada: [{decision.action}] - {decision.primary_reason}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTC-USDT")
    parser.add_argument("--interval", default="15m")
    args = parser.parse_args()

    run_paper_round(symbol=args.symbol, interval=args.interval)
