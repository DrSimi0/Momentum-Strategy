"""Carga de datos con verificación de integridad (hash del manifiesto y continuidad de velas)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

from src.backtest.engine import BAR, prepare_bars

ROOT = Path(__file__).resolve().parents[2]


class DataIntegrityError(RuntimeError):
    pass


def load_bars(symbol: str = "BTCUSDT", interval: str = "4h", cutoff=None) -> pd.DataFrame:
    """Devuelve velas + funding. ``cutoff`` (exclusivo) impide cargar datos posteriores (p. ej. el holdout)."""
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))
    kp = ROOT / "data" / "processed" / f"{symbol}_{interval}.csv"
    fp = ROOT / "data" / "processed" / f"{symbol}_funding.csv"
    for p in (kp, fp):
        if hashlib.sha256(p.read_bytes()).hexdigest() != manifest[p.name]["sha256"]:
            raise DataIntegrityError(f"Hash distinto al manifiesto: {p.name}")
    k = pd.read_csv(kp)
    k["open_time"] = pd.to_datetime(k["open_time"], utc=True, format="ISO8601")
    f = pd.read_csv(fp)
    f["funding_time"] = pd.to_datetime(f["funding_time"], utc=True, format="ISO8601")
    gaps = k["open_time"].diff().dropna()
    if (gaps != BAR).any():
        raise DataIntegrityError(f"Velas no contiguas: {int((gaps != BAR).sum())} saltos")
    if (k[["open", "high", "low", "close"]] <= 0).any().any():
        raise DataIntegrityError("Precios no positivos")
    if cutoff is not None:
        c = pd.Timestamp(cutoff, tz="UTC")
        k, f = k[k["open_time"] < c], f[f["funding_time"] < c]
    return prepare_bars(k, f)
