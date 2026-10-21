"""Motor de Paper Trading (Nivel 2) para ejecución simulada en tiempo real.
Mantiene el estado de la cartera virtual, aplica trailing a break-even y emite alertas.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from src.alerts.dispatcher import AlertDispatcher
from src.execution.executor_interface import SafeNullExecutor
from src.strategy.arbitrator import ConfluenceArbitrator, ConfluenceDecision

logger = logging.getLogger(__name__)


@dataclass
class PaperPosition:
    """Posición simulada en la cartera de paper trading."""
    symbol: str
    direction: str
    entry_price: float
    entry_time_utc: str
    stop_loss: float
    take_profit: float
    risk_r: float
    max_bars: int
    bars_held: int = 0
    be_active: bool = False
    size_usdt: float = 1000.0


class PaperTradingEngine:
    """Gestor de ciclo de vida de paper trading en tiempo real."""

    def __init__(
        self,
        arbitrator: ConfluenceArbitrator,
        dispatcher: Optional[AlertDispatcher] = None,
        state_file: Optional[Path] = None,
        initial_capital: float = 10000.0,
    ):
        self.arbitrator = arbitrator
        self.dispatcher = dispatcher or AlertDispatcher()
        self.state_file = state_file or Path("reports/paper_trading_state.json")
        self.executor = SafeNullExecutor(allow_real_execution=False)
        self.capital = initial_capital
        self.active_position: Optional[PaperPosition] = None
        self.trade_history: List[Dict[str, Any]] = []
        self._load_state()

    def process_closed_bars(self, df_closed: pd.DataFrame, symbol: str = "BTC-USDT") -> ConfluenceDecision:
        """Procesa el último cierre de vela, actualiza la posición simulada y genera señales."""
        if len(df_closed) < 200:
            raise ValueError("Se requieren al menos 200 barras cerradas para evaluar indicadores técnicos.")

        # Precomputar indicadores en Capa 2
        data_ind = self.arbitrator.layer2.compute_all_indicators(df_closed)
        last_idx = len(data_ind) - 1
        last_bar = data_ind.iloc[last_idx]

        # 1. Gestionar posición activa si existe
        if self.active_position is not None:
            self._update_active_position(last_bar)

        # 2. Evaluar árbitro de confluencia en la última barra cerrada
        decision = self.arbitrator.evaluate_bar(data_ind, last_idx)

        # 3. Despachar alerta y registrar decisión
        self.dispatcher.dispatch(decision, symbol=symbol)

        # 4. Si no hay posición activa y la decisión es LONG o SHORT, abrir posición de papel
        if self.active_position is None and decision.action in ("LONG", "SHORT") and decision.setup is not None:
            s = decision.setup
            self.active_position = PaperPosition(
                symbol=symbol,
                direction=decision.action,
                entry_price=s.entry_price,
                entry_time_utc=str(last_bar.get("datetime_utc", "")),
                stop_loss=s.stop_loss,
                take_profit=s.take_profit,
                risk_r=s.risk_r,
                max_bars=s.max_horizon_bars,
                size_usdt=1000.0,
            )
            # Registrar llamada al executor seguro (desactivado por defecto)
            self.executor.place_order(
                symbol=symbol,
                side="BUY" if decision.action == "LONG" else "SELL",
                order_type="MARKET",
                quantity=1000.0 / s.entry_price,
                price=s.entry_price,
                stop_loss=s.stop_loss,
                take_profit=s.take_profit,
            )

        self._save_state()
        return decision

    def _update_active_position(self, bar: pd.Series) -> None:
        """Actualiza el trailing a Break-Even o cierra la posición por SL, TP o tiempo."""
        pos = self.active_position
        if pos is None:
            return

        pos.bars_held += 1
        h = float(bar["high"])
        l = float(bar["low"])
        c = float(bar["close"])

        closed = False
        exit_price = c
        reason = ""

        if pos.direction == "LONG":
            # Break-Even trigger
            if not pos.be_active and (h - pos.entry_price) >= pos.risk_r:
                pos.stop_loss = pos.entry_price
                pos.be_active = True
                logger.info("Paper Trading: Break-Even activado para posición LONG.")

            if l <= pos.stop_loss:
                closed = True
                exit_price = pos.stop_loss
                reason = "BREAK_EVEN" if pos.be_active and pos.stop_loss >= pos.entry_price else "STOP_LOSS"
            elif h >= pos.take_profit:
                closed = True
                exit_price = pos.take_profit
                reason = "TAKE_PROFIT"
            elif pos.bars_held >= pos.max_bars:
                closed = True
                exit_price = c
                reason = "TIME_EXPIRATION"

        elif pos.direction == "SHORT":
            if not pos.be_active and (pos.entry_price - l) >= pos.risk_r:
                pos.stop_loss = pos.entry_price
                pos.be_active = True
                logger.info("Paper Trading: Break-Even activado para posición SHORT.")

            if h >= pos.stop_loss:
                closed = True
                exit_price = pos.stop_loss
                reason = "BREAK_EVEN" if pos.be_active and pos.stop_loss <= pos.entry_price else "STOP_LOSS"
            elif l <= pos.take_profit:
                closed = True
                exit_price = pos.take_profit
                reason = "TAKE_PROFIT"
            elif pos.bars_held >= pos.max_bars:
                closed = True
                exit_price = c
                reason = "TIME_EXPIRATION"

        if closed:
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price if pos.direction == "LONG" else (pos.entry_price - exit_price) / pos.entry_price
            pnl_usdt = pos.size_usdt * pnl_pct
            self.capital += pnl_usdt
            self.trade_history.append({
                "direction": pos.direction,
                "entry_price": pos.entry_price,
                "exit_price": exit_price,
                "bars_held": pos.bars_held,
                "reason": reason,
                "pnl_usdt": pnl_usdt,
            })
            logger.info(f"Paper Trading: Posición cerrada ({reason}) PnL: {pnl_usdt:+.2f} USDT")
            self.active_position = None

    def _save_state(self) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "capital": self.capital,
            "active_position": self.active_position.__dict__ if self.active_position else None,
            "history_count": len(self.trade_history),
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def _load_state(self) -> None:
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.capital = state.get("capital", 10000.0)
            except Exception:
                pass
