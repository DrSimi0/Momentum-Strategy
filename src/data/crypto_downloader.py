"""Descargador de datos históricos de criptomonedas (BTC-USDT y ETH-USDT) desde la API pública de BingX.
Utiliza únicamente endpoints públicos de solo lectura.
Garantiza:
1. Validación de duplicados, monotonía temporal y precios inválidos.
2. Exclusión de velas incompletas (vela en curso).
3. Almacenamiento en Parquet con registro de metadatos y hashes criptográficos SHA-256.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request
import pandas as pd

logger = logging.getLogger(__name__)

BINGX_BASE_URL = "https://open-api.bingx.com"
RAW_DATA_DIR = Path("data/raw")
METADATA_CRYPTO_PATH = Path("data/metadata_crypto.json")


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(4096 * 1024):
            h.update(chunk)
    return h.hexdigest()


class BingXPublicClient:
    def __init__(self, base_url: str = BINGX_BASE_URL, timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Consulta velas históricas públicas (/openApi/swap/v3/quote/klines)."""
        params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        url = f"{self.base_url}/openApi/swap/v3/quote/klines?{urllib.parse.urlencode(params)}"
        headers = {"User-Agent": "QuantitativeResearch/4.0"}
        req = urllib.request.Request(url, headers=headers, method="GET")

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"HTTP status {resp.status} al consultar {url}")
                    raw = resp.read().decode("utf-8")
                    data = json.loads(raw)
                    if data.get("code") != 0:
                        raise RuntimeError(f"Error devuelto por BingX: {data.get('msg')} (código {data.get('code')})")
                    return data.get("data", [])
            except Exception as e:
                logger.warning(f"Intento {attempt + 1}/3 falló para {url}: {e}")
                if attempt == 2:
                    raise
                time.sleep(1.0 * (2 ** attempt))
        return []


def download_crypto_history(
    symbol: str = "BTC-USDT",
    interval: str = "1h",
    start_date: str = "2021-06-01",
    end_date: Optional[str] = None,
) -> Path:
    """Descarga todo el historial disponible para el símbolo y temporalidad indicada."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RAW_DATA_DIR / f"{symbol}_{interval}.parquet"

    client = BingXPublicClient()
    start_ts = int(pd.Timestamp(start_date, tz="UTC").timestamp() * 1000)
    end_ts = int(pd.Timestamp(end_date, tz="UTC").timestamp() * 1000) if end_date else int(time.time() * 1000)

    # Determinar delta aproximado según interval para retroceder
    interval_minutes = {
        "5m": 5,
        "15m": 15,
        "1h": 60,
        "4h": 240,
        "1d": 1440,
    }.get(interval, 60)
    delta_ms = interval_minutes * 60 * 1000

    logger.info(f"Descargando {symbol} ({interval}) desde {start_date} hasta {end_date or 'actualidad'}...")

    all_bars = []
    current_end = end_ts

    while current_end > start_ts:
        batch = client.get_klines(symbol=symbol, interval=interval, end_time=current_end, limit=1000)
        if not batch:
            logger.info("Fin de datos devueltos por el servidor.")
            break

        all_bars.extend(batch)
        oldest_ts = int(batch[-1]["time"])

        if oldest_ts <= start_ts:
            break
        if oldest_ts >= current_end:
            current_end -= 1000 * delta_ms
        else:
            current_end = oldest_ts - 1

        time.sleep(0.12)  # Respetar rate limits

    if not all_bars:
        raise RuntimeError(f"No se obtuvieron velas para {symbol} {interval}")

    # Convertir a DataFrame
    df = pd.DataFrame(all_bars)
    # Parsear tipos
    df["ts_event"] = pd.to_datetime(df["time"].astype(int), unit="ms", utc=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)

    # Validaciones obligatorias:
    # 1. Duplicados y orden
    df = df.drop_duplicates(subset=["ts_event"]).sort_values("ts_event").reset_index(drop=True)

    # 2. Exclusión de vela en curso (incompleta): eliminar la última vela si su cierre es en el futuro
    now_utc = pd.Timestamp.now(tz="UTC")
    df = df[df["ts_event"] + pd.Timedelta(minutes=interval_minutes) <= now_utc].reset_index(drop=True)

    # 3. Filtrar al rango de fechas solicitado
    df = df[df["ts_event"] >= pd.Timestamp(start_date, tz="UTC")].reset_index(drop=True)

    # 4. Invariantes de precios y volumen
    if (df["open"] <= 0).any() or (df["close"] <= 0).any() or (df["high"] < df["low"]).any() or (df["volume"] < 0).any():
        raise ValueError(f"Violación de invariantes OHLCV en datos descargados de {symbol}")

    cols_to_save = ["ts_event", "open", "high", "low", "close", "volume"]
    df = df[cols_to_save]
    df.to_parquet(out_file, index=False)
    logger.info(f"Guardado {out_file} con {len(df)} velas limpias.")
    return out_file


def update_crypto_metadata(downloaded_paths: Dict[str, Path]) -> Path:
    METADATA_CRYPTO_PATH.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "source": "BingX Public Perpetual Swap API",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "files": {},
    }
    for key, p in downloaded_paths.items():
        if p.exists():
            meta["files"][key] = {
                "path": str(p.as_posix()),
                "size_bytes": p.stat().st_size,
                "sha256": compute_sha256(p),
            }
    with open(METADATA_CRYPTO_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return METADATA_CRYPTO_PATH
