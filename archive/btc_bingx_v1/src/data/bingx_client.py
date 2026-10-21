"""Cliente HTTP público de solo lectura para la API swap USDT-M de BingX.
No requiere ni admite claves privadas ni endpoints de trading.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BINGX_BASE_URL = "https://open-api.bingx.com"


class BingXDataClient:
    """Cliente para obtención de datos públicos de mercado desde BingX USDT-M Perpetual."""

    def __init__(self, base_url: str = BINGX_BASE_URL, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _http_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Ejecuta una petición HTTP GET con reintentos y control de errores."""
        query_string = f"?{urllib.parse.urlencode(params)}" if params else ""
        url = f"{self.base_url}{endpoint}{query_string}"
        headers = {"User-Agent": "QuantitativeResearch/3.0 (Deterministic)"}
        req = urllib.request.Request(url, headers=headers, method="GET")

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP error {resp.status} al consultar {url}")
                    raw_data = resp.read().decode("utf-8")
                    data = json.loads(raw_data)
                    if data.get("code") != 0:
                        raise RuntimeError(f"Error devuelto por la API de BingX: {data.get('msg')} (código {data.get('code')})")
                    return data
            except Exception as e:
                logger.warning(f"Intento {attempt + 1}/{max_retries} falló para {url}: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(1.0 * (2 ** attempt))
        raise RuntimeError("Reintentos agotados.")

    def get_klines(
        self,
        symbol: str = "BTC-USDT",
        interval: str = "15m",
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Obtiene velas históricas de la API de BingX swap USDT-M (/openApi/swap/v3/quote/klines).
        
        Args:
            symbol: Par comercial (ej. 'BTC-USDT').
            interval: Temporalidad ('15m', '1h', '4h', '1d').
            start_time: Timestamp milisegundos de inicio.
            end_time: Timestamp milisegundos de fin.
            limit: Límite por petición (máx 1000).
        """
        params: Dict[str, Any] = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        res = self._http_get("/openApi/swap/v3/quote/klines", params)
        raw_klines = res.get("data", [])
        return raw_klines

    def get_funding_rate_history(
        self, symbol: str = "BTC-USDT", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Obtiene historial reciente de tasas de financiación (/openApi/swap/v2/quote/fundingRate)."""
        params = {"symbol": symbol, "limit": limit}
        res = self._http_get("/openApi/swap/v2/quote/fundingRate", params)
        return res.get("data", [])

    def get_open_interest(self, symbol: str = "BTC-USDT") -> Dict[str, Any]:
        """Obtiene interés abierto actual (/openApi/swap/v2/quote/openInterest)."""
        params = {"symbol": symbol}
        res = self._http_get("/openApi/swap/v2/quote/openInterest", params)
        return res.get("data", {})
