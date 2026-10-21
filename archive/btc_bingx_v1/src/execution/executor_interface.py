"""Interfaz de ejecución desacoplada y desactivada por defecto.
Garantiza que bajo ninguna circunstancia se envíen órdenes reales sin autorización explícita.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ExecutionDisabledError(RuntimeError):
    """Lanzada si se intenta ejecutar una orden cuando el ejecutor está en modo seguro (desactivado)."""
    pass


class OrderExecutor(ABC):
    """Contrato abstracto para el enrutamiento de órdenes."""

    @abstractmethod
    def place_order(
        self,
        symbol: str,
        side: str,  # "BUY" o "SELL"
        order_type: str,  # "MARKET" o "LIMIT"
        quantity: float,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Envía una orden al mercado."""
        pass


class SafeNullExecutor(OrderExecutor):
    """Implementación de ejecución segura para Nivel 0 y Nivel 1.
    Está DESACTIVADA por diseño y por defecto. Solo simula o rechaza.
    """

    def __init__(self, allow_real_execution: bool = False):
        # La variable de entorno BINGX_ENABLE_LIVE_TRADING debe estar explícitamente en "TRUE"
        env_override = os.getenv("BINGX_ENABLE_LIVE_TRADING", "FALSE").upper() == "TRUE"
        self.is_enabled = allow_real_execution and env_override

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not self.is_enabled:
            msg = (
                f"[MODO SEGURO ACTIVO] Ejecución bloqueada deterministamente para {side} {quantity} {symbol}. "
                "La interfaz de ejecución está DESACTIVADA por defecto para proteger el capital. "
                "Para habilitar paper trading, use el módulo PaperTradingEngine."
            )
            logger.warning(msg)
            return {
                "status": "BLOCKED_BY_SAFETY_GUARD",
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "message": msg,
            }

        # Si en el futuro el usuario autoriza la activación:
        raise ExecutionDisabledError("Ejecución real en vivo no implementada en Nivel 1.")
