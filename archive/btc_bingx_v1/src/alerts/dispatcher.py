"""Módulo despachador de señales y alertas (Nivel 1).
Registra en JSONL inmutable y emite notificaciones a Telegram si está configurado.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.strategy.arbitrator import ConfluenceDecision

logger = logging.getLogger(__name__)


class AlertDispatcher:
    """Distribuye señales del sistema a logs locales y canales de mensajería seguros."""

    def __init__(
        self,
        log_file: Optional[Path] = None,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
    ):
        self.log_file = log_file or Path("reports/signals_log.jsonl")
        self.telegram_token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def dispatch(self, decision: ConfluenceDecision, symbol: str = "BTC-USDT") -> Dict[str, Any]:
        """Formatea y registra la decisión."""
        utc_now = datetime.now(timezone.utc).isoformat()
        candle_dt = datetime.fromtimestamp(decision.timestamp_ms / 1000.0, tz=timezone.utc).isoformat()

        payload = {
            "timestamp_utc": utc_now,
            "candle_time_utc": candle_dt,
            "symbol": symbol,
            "action": decision.action,  # "LONG", "SHORT", "NEUTRAL"
            "primary_reason": decision.primary_reason,
            "is_trap_prevented": decision.is_trap_prevented,
            "macro_bias": decision.macro_output.bias,
            "macro_reasons": decision.macro_output.reasons,
        }

        if decision.setup is not None:
            payload["setup"] = {
                "entry_price": decision.setup.entry_price,
                "stop_loss": decision.setup.stop_loss,
                "take_profit": decision.setup.take_profit,
                "risk_r": decision.setup.risk_r,
                "pattern": decision.setup.pattern_name,
                "max_horizon_bars": decision.setup.max_horizon_bars,
                "break_even_trigger_r": decision.setup.break_even_trigger_r,
            }

        # 1. Guardar en registro local persistente JSONL
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

        # 2. Si hay señal operativa (no neutral) y credenciales de Telegram, notificar
        if decision.action in ("LONG", "SHORT") and self.telegram_token and self.telegram_chat_id:
            self._send_telegram(payload)

        return payload

    def _send_telegram(self, payload: Dict[str, Any]) -> None:
        """Envía alerta vía Telegram Bot API."""
        setup = payload.get("setup", {})
        action_emoji = "🟢" if payload["action"] == "LONG" else "🔴"
        text = (
            f"{action_emoji} *SEÑAL DE CONFLUENCIA v3: {payload['action']} ({payload['symbol']})*\n"
            f"🕒 *Vela:* `{payload['candle_time_utc']}`\n"
            f"🎯 *Entrada:* `{setup.get('entry_price', 'N/A')}`\n"
            f"🛑 *Stop-Loss:* `{setup.get('stop_loss', 'N/A')}`\n"
            f"💰 *Take-Profit:* `{setup.get('take_profit', 'N/A')}`\n"
            f"⏱ *Horizonte:* `15 barras (3.75h)`\n"
            f"🛡 *Break-Even:* `Activación en +1.0R`\n"
            f"📋 *Motivo:* {payload['primary_reason']}\n"
        )
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": self.telegram_chat_id, "text": text, "parse_mode": "Markdown"}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info(f"Alerta enviada a Telegram (status {resp.status})")
        except Exception as e:
            logger.warning(f"No se pudo enviar alerta a Telegram: {e}")
