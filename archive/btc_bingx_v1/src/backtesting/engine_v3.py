"""Motor de simulación determinista para velas de 15m con costos reales y ejecución en t+1.
Aplica reglas estrictas de Stop-Loss, Take-Profit, Break-Even al alcanzar +1.0R y expiración temporal.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from src.strategy.layer2_technical import TechnicalSetup

SQRT_35040 = math.sqrt(35040)  # Factor de anualización para barras de 15m en mercado cripto 24/7/365


@dataclass
class TradeRecord:
    """Registro detallado de una operación simulada."""
    trade_id: int
    direction: str
    entry_bar: int
    exit_bar: int
    entry_time: int
    exit_time: int
    entry_price: float
    exit_price: float
    initial_sl: float
    initial_tp: float
    risk_r: float
    exit_reason: str  # "SL", "TP", "BREAK_EVEN", "TIME_EXPIRATION"
    bars_held: int
    gross_pnl_pct: float
    commission_pct: float
    slippage_pct: float
    funding_pct: float
    net_pnl_pct: float
    net_pnl_usdt: float
    net_pnl_r: float
    capital_before: float
    capital_after: float


class BacktestEngineV3:
    """Simulador de eventos determinista para la estrategia de 15m."""

    def __init__(
        self,
        initial_capital: float = 10000.0,
        taker_fee_pct: float = 0.0005,  # 0.05% taker oficial BingX
        slippage_pct: float = 0.0002,   # 0.02% slippage por lado
        funding_rate_8h: float = 0.0001, # 0.01% cada 8 horas (~32 barras)
        risk_per_trade_pct: float = 0.015, # 1.5% de riesgo del capital por operación
    ):
        self.initial_capital = initial_capital
        self.taker_fee_pct = taker_fee_pct
        self.slippage_pct = slippage_pct
        self.funding_rate_8h = funding_rate_8h
        self.risk_per_trade_pct = risk_per_trade_pct

    def run_simulation(
        self,
        df: pd.DataFrame,
        setups: List[Optional[TechnicalSetup]],
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
        """Ejecuta la simulación cronológica vela a vela.
        
        Args:
            df: DataFrame de mercado limpio con time, open, high, low, close.
            setups: Lista de setups técnicos (o None) generados al cierre de cada barra i.
            
        Returns:
            trades_df: DataFrame con el registro de cada operación.
            equity_curve: Serie temporal de equity por barra.
            summary_stats: Diccionario de métricas financieras calculadas con código determinista.
        """
        n_bars = len(df)
        equity = np.full(n_bars, self.initial_capital, dtype=np.float64)
        trades: List[TradeRecord] = []
        current_capital = self.initial_capital

        active_trade = None
        trade_counter = 0

        # Iterar barra a barra
        for i in range(n_bars):
            # 1. Gestionar posición activa si existe
            if active_trade is not None:
                o_curr = df["open"].iloc[i]
                h_curr = df["high"].iloc[i]
                l_curr = df["low"].iloc[i]
                c_curr = df["close"].iloc[i]
                t_curr = int(df["time"].iloc[i])

                bars_in_trade = i - active_trade["entry_bar"]
                exit_price = None
                exit_reason = None

                direction = active_trade["direction"]
                entry_p = active_trade["entry_price"]
                sl_p = active_trade["current_sl"]
                tp_p = active_trade["take_profit"]
                risk_r = active_trade["risk_r"]
                be_active = active_trade["be_active"]

                if direction == "LONG":
                    # Chequeo de Break-Even: si el precio superó Entrada + 1.0R
                    if not be_active and (h_curr - entry_p) >= risk_r:
                        active_trade["current_sl"] = entry_p
                        active_trade["be_active"] = True
                        sl_p = entry_p

                    # Chequeo de Stop-Loss (invalidez)
                    if l_curr <= sl_p:
                        # Si hay gap de apertura por debajo del SL
                        exit_price = min(o_curr, sl_p)
                        exit_reason = "BREAK_EVEN" if be_active and sl_p >= entry_p else "SL"
                    # Chequeo de Take-Profit
                    elif h_curr >= tp_p:
                        exit_price = max(o_curr, tp_p)
                        exit_reason = "TP"
                    # Chequeo de expiración temporal (15 barras = 3.75 horas)
                    elif bars_in_trade >= active_trade["max_bars"]:
                        exit_price = c_curr
                        exit_reason = "TIME_EXPIRATION"

                elif direction == "SHORT":
                    if not be_active and (entry_p - l_curr) >= risk_r:
                        active_trade["current_sl"] = entry_p
                        active_trade["be_active"] = True
                        sl_p = entry_p

                    if h_curr >= sl_p:
                        exit_price = max(o_curr, sl_p)
                        exit_reason = "BREAK_EVEN" if be_active and sl_p <= entry_p else "SL"
                    elif l_curr <= tp_p:
                        exit_price = min(o_curr, tp_p)
                        exit_reason = "TP"
                    elif bars_in_trade >= active_trade["max_bars"]:
                        exit_price = c_curr
                        exit_reason = "TIME_EXPIRATION"

                if exit_price is not None:
                    # Cerrar operación y liquidar costos
                    trade_counter += 1
                    pos_size_usd = active_trade["pos_size_usd"]

                    if direction == "LONG":
                        gross_return = (exit_price - entry_p) / entry_p
                    else:
                        gross_return = (entry_p - exit_price) / entry_p

                    # Costos: dos lados de taker fee y slippage + funding devengado
                    comm_cost = 2.0 * self.taker_fee_pct
                    slip_cost = 2.0 * self.slippage_pct
                    # Funding proporcional (tasa 8h prorrateada a 32 barras de 15m)
                    funding_cost = (bars_in_trade / 32.0) * self.funding_rate_8h
                    total_costs_pct = comm_cost + slip_cost + funding_cost

                    net_return = gross_return - total_costs_pct
                    net_pnl_usd = pos_size_usd * net_return
                    net_pnl_r = (exit_price - entry_p) / risk_r if direction == "LONG" else (entry_p - exit_price) / risk_r

                    cap_before = current_capital
                    current_capital += net_pnl_usd

                    trades.append(TradeRecord(
                        trade_id=trade_counter,
                        direction=direction,
                        entry_bar=active_trade["entry_bar"],
                        exit_bar=i,
                        entry_time=active_trade["entry_time"],
                        exit_time=t_curr,
                        entry_price=entry_p,
                        exit_price=exit_price,
                        initial_sl=active_trade["initial_sl"],
                        initial_tp=tp_p,
                        risk_r=risk_r,
                        exit_reason=exit_reason,
                        bars_held=bars_in_trade,
                        gross_pnl_pct=gross_return,
                        commission_pct=comm_cost,
                        slippage_pct=slip_cost,
                        funding_pct=funding_cost,
                        net_pnl_pct=net_return,
                        net_pnl_usdt=net_pnl_usd,
                        net_pnl_r=net_pnl_r,
                        capital_before=cap_before,
                        capital_after=current_capital,
                    ))
                    active_trade = None

            # 2. Si no hay posición activa, comprobar si la barra PREVIA (i-1) generó un setup para entrar al OPEN de i
            if active_trade is None and i > 0 and setups[i - 1] is not None:
                setup = setups[i - 1]
                entry_price = float(df["open"].iloc[i])  # Ejecución al Open de t+1
                initial_sl = setup.stop_loss
                risk_per_unit = abs(entry_price - initial_sl)

                if risk_per_unit > 0:
                    # Tamaño de posición ajustado por riesgo fijo monetario
                    risk_capital = current_capital * self.risk_per_trade_pct
                    units = risk_capital / risk_per_unit
                    pos_size_usd = min(units * entry_price, current_capital * 1.0)  # Evaluación base 1x max exposición

                    active_trade = {
                        "direction": setup.direction,
                        "entry_bar": i,
                        "entry_time": int(df["time"].iloc[i]),
                        "entry_price": entry_price,
                        "initial_sl": initial_sl,
                        "current_sl": initial_sl,
                        "take_profit": setup.take_profit,
                        "risk_r": risk_per_unit,
                        "max_bars": setup.max_horizon_bars,
                        "be_active": False,
                        "pos_size_usd": pos_size_usd,
                    }

            equity[i] = current_capital

        trades_df = pd.DataFrame([t.__dict__ for t in trades]) if trades else pd.DataFrame()
        equity_series = pd.Series(equity, index=df.index)
        metrics = self._calculate_metrics(trades_df, equity_series, df)
        return trades_df, pd.DataFrame({"time": df["time"], "equity": equity_series}), metrics

    def _calculate_metrics(
        self,
        trades_df: pd.DataFrame,
        equity: pd.Series,
        market_df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Calcula métricas financieras deterministas conforme al protocolo v3."""
        if trades_df.empty or len(trades_df) == 0:
            return {
                "n_trades": 0,
                "net_profit_usdt": 0.0,
                "total_return_pct": 0.0,
                "sharpe_annual": 0.0,
                "sortino_annual": 0.0,
                "max_drawdown_pct": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "expectancy_usdt": 0.0,
                "expectancy_r": 0.0,
                "top5pct_share": 0.0,
            }

        n_trades = len(trades_df)
        net_profit_usdt = float(equity.iloc[-1] - equity.iloc[0])
        total_return_pct = float(net_profit_usdt / equity.iloc[0])

        # Retornos periódicos barra a barra para cálculo de Sharpe anualizado en 15m
        bar_returns = equity.pct_change().dropna()
        mean_ret = float(bar_returns.mean())
        std_ret = float(bar_returns.std(ddof=1))
        sharpe_annual = (mean_ret / std_ret * SQRT_35040) if std_ret > 1e-12 else 0.0

        downside_returns = bar_returns[bar_returns < 0]
        downside_std = float(downside_returns.std(ddof=1)) if len(downside_returns) > 1 else 1e-6
        sortino_annual = (mean_ret / downside_std * SQRT_35040) if downside_std > 1e-12 else 0.0

        # Drawdown
        running_max = np.maximum.accumulate(equity.values)
        drawdowns = (equity.values - running_max) / running_max
        max_dd_pct = float(np.min(drawdowns) * -1.0)

        # Operaciones
        wins = trades_df[trades_df["net_pnl_usdt"] > 0]
        losses = trades_df[trades_df["net_pnl_usdt"] < 0]
        win_rate = float(len(wins) / n_trades)

        total_gain = wins["net_pnl_usdt"].sum()
        total_loss = abs(losses["net_pnl_usdt"].sum())
        profit_factor = float(total_gain / total_loss) if total_loss > 0 else (99.0 if total_gain > 0 else 0.0)

        expectancy_usdt = float(trades_df["net_pnl_usdt"].mean())
        expectancy_r = float(trades_df["net_pnl_r"].mean())

        # Concentración de ganancias: peso del 5% superior
        k_top = max(1, int(math.ceil(0.05 * n_trades)))
        top_k_gains = trades_df["net_pnl_usdt"].nlargest(k_top).sum()
        top5pct_share = float(top_k_gains / total_gain) if total_gain > 0 else 1.0

        return {
            "n_trades": n_trades,
            "net_profit_usdt": net_profit_usdt,
            "total_return_pct": total_return_pct,
            "sharpe_annual": sharpe_annual,
            "sortino_annual": sortino_annual,
            "max_drawdown_pct": max_dd_pct,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "expectancy_usdt": expectancy_usdt,
            "expectancy_r": expectancy_r,
            "top5pct_share": top5pct_share,
        }
