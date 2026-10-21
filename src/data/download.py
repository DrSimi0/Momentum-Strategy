"""Descarga datos públicos de Binance USDT-M Futures (velas y funding).

Uso: python -m src.data.download
Genera data/processed/*.csv y data/manifest.json (hash SHA-256 de cada archivo).
"""
from __future__ import annotations

import hashlib
import io
import json
import time
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
VISION = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/{i}/{s}-{i}-{y}-{m:02d}.zip"
FAPI_FUNDING = "https://fapi.binance.com/fapi/v1/fundingRate?symbol={s}&startTime={st}&limit=1000"
KCOLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
         "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]


def _get(url: str) -> bytes:
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except Exception:  # noqa: BLE001 - reintento simple de red
            if attempt == 4:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def download_klines(symbol: str, interval: str, start: str, end: str) -> pd.DataFrame:
    frames = []
    for p in pd.period_range(start, end, freq="M"):
        raw = _get(VISION.format(s=symbol, i=interval, y=p.year, m=p.month))
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            txt = z.read(z.namelist()[0]).decode()
        df = pd.read_csv(io.StringIO(txt), header=None, names=KCOLS)
        df = df[pd.to_numeric(df["open_time"], errors="coerce").notna()]  # quita cabecera si existe
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    ot = df["open_time"].astype("int64")
    ot = ot.where(ot < 10**14, ot // 1000)  # microsegundos -> milisegundos
    out = pd.DataFrame({"open_time": pd.to_datetime(ot, unit="ms", utc=True)})
    for c in ["open", "high", "low", "close", "volume"]:
        out[c] = df[c].astype(float).values
    return out.drop_duplicates("open_time").sort_values("open_time").reset_index(drop=True)


def download_funding(symbol: str, start: str, end: str) -> pd.DataFrame:
    st = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = int(pd.Timestamp(end, tz="UTC").timestamp() * 1000)
    rows = []
    while st < end_ms:
        batch = json.loads(_get(FAPI_FUNDING.format(s=symbol, st=st)))
        if not batch:
            break
        rows += batch
        st = int(batch[-1]["fundingTime"]) + 1
        time.sleep(0.3)
    df = pd.DataFrame(rows)
    df["funding_time"] = pd.to_datetime(df["fundingTime"].astype("int64"), unit="ms", utc=True)
    df["funding_rate"] = df["fundingRate"].astype(float)
    df["mark_price"] = pd.to_numeric(df.get("markPrice"), errors="coerce")
    df = df[df["funding_time"] < pd.Timestamp(end, tz="UTC")]
    return df[["funding_time", "funding_rate", "mark_price"]].drop_duplicates("funding_time").reset_index(drop=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    cfg = yaml.safe_load((ROOT / "config" / "strategy.yaml").read_text(encoding="utf-8"))
    d = cfg["data"]
    out = ROOT / "data" / "processed"
    out.mkdir(parents=True, exist_ok=True)
    k = download_klines(d["symbol"], d["interval"], d["download_start"], d["download_end_month"])
    f = download_funding(d["symbol"], d["download_start"] + "-01", d["data_end_exclusive"])
    k = k[k["open_time"] < pd.Timestamp(d["data_end_exclusive"], tz="UTC")]
    kp, fp = out / f"{d['symbol']}_{d['interval']}.csv", out / f"{d['symbol']}_funding.csv"
    k.to_csv(kp, index=False)
    f.to_csv(fp, index=False)
    manifest = {p.name: {"sha256": sha256(p), "rows": n} for p, n in [(kp, len(k)), (fp, len(f))]}
    (ROOT / "data" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
