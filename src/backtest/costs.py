"""Cálculo determinista de costos de transacción para futuros CME (ES y NQ).
Incluye comisiones de broker/exchange y deslizamiento (slippage) por contrato.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class CostSpec:
    slippage_ticks_per_side: float
    commission_usd_per_side: float


DEFAULT_COST_CASES: Dict[str, CostSpec] = {
    "base": CostSpec(slippage_ticks_per_side=0.5, commission_usd_per_side=2.00),
    "stress": CostSpec(slippage_ticks_per_side=1.0, commission_usd_per_side=2.50),
}


def calculate_trade_costs(
    tick_size_points: float,
    tick_value_usd: float,
    cost_spec: CostSpec,
    num_contracts: int = 1,
) -> Dict[str, float]:
    """Calcula los costos de ida y vuelta (round-turn: entrada + salida = 2 lados) para una operación.
    
    Returns:
        slippage_usd: Deslizamiento total en USD (2 lados).
        commission_usd: Comisión total en USD (2 lados).
        total_cost_usd: Suma de comisiones y deslizamiento.
        slippage_points_per_side: Puntos de deslizamiento por lado.
    """
    if num_contracts <= 0:
        return {
            "slippage_usd": 0.0,
            "commission_usd": 0.0,
            "total_cost_usd": 0.0,
            "slippage_points_per_side": 0.0,
        }

    # 2 lados: entrada y salida
    total_sides = 2 * num_contracts
    slippage_usd = cost_spec.slippage_ticks_per_side * tick_value_usd * total_sides
    commission_usd = cost_spec.commission_usd_per_side * total_sides
    total_cost_usd = slippage_usd + commission_usd
    slippage_points_per_side = cost_spec.slippage_ticks_per_side * tick_size_points

    return {
        "slippage_usd": float(slippage_usd),
        "commission_usd": float(commission_usd),
        "total_cost_usd": float(total_cost_usd),
        "slippage_points_per_side": float(slippage_points_per_side),
    }
