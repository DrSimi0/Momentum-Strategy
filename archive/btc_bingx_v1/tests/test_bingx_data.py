"""Pruebas unitarias deterministas para el módulo de datos de BingX (sin llamadas reales a red)."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pandas as pd
import pytest

from src.data.bingx_client import BingXDataClient
from src.data.storage import load_dataset_verified, save_dataset_with_manifest
from src.data.validator import DataValidationError, parse_and_validate_klines


def create_sample_raw_klines(base_time: int = 1700000000000, n: int = 5, interval_ms: int = 15 * 60 * 1000):
    """Genera datos sintéticos válidos en formato devuelto por BingX swap v3 klines (orden descendente)."""
    klines = []
    # Generar de más reciente a más antiguo (orden descendente oficial)
    for i in range(n - 1, -1, -1):
        t = base_time + i * interval_ms
        klines.append({
            "time": t,
            "open": "50000.0",
            "high": "50500.0",
            "low": "49500.0",
            "close": "50200.0",
            "volume": "10.5",
        })
    return klines


def test_order_inversion_and_types():
    """Verifica que el orden descendente de BingX se convierta a ascendente y los tipos a float/int."""
    raw = create_sample_raw_klines(n=4)
    df = parse_and_validate_klines(raw, interval="15m")
    assert len(df) == 4
    # Verificar orden estrictamente creciente
    assert df["time"].is_monotonic_increasing
    assert df["open"].dtype == np.float64
    assert df["close"].iloc[0] == 50200.0


def test_discard_open_candle():
    """Verifica el descarte riguroso de la vela que aún está en formación."""
    interval_ms = 15 * 60 * 1000
    base_time = 1700000000000
    raw = create_sample_raw_klines(base_time=base_time, n=3, interval_ms=interval_ms)
    
    # La última vela tiene time = base_time + 2*interval_ms.
    # Si simulamos un current_time_ms donde esa última vela aún no ha terminado:
    current_time_ms = base_time + 2 * interval_ms + (5 * 60 * 1000)  # Solo han pasado 5 minutos de la última vela
    df = parse_and_validate_klines(raw, interval="15m", current_time_ms=current_time_ms)
    
    # Debe haber descartado la 3ra vela y dejado solo las 2 ya cerradas
    assert len(df) == 2
    assert df["time"].max() == base_time + 1 * interval_ms


def test_detect_ohlc_invariants():
    """Verifica que se lance DataValidationError si se violan las propiedades OHLC."""
    bad_candle = [{
        "time": 1700000000000,
        "open": "50000.0",
        "high": "49000.0",  # High menor que Open
        "low": "48000.0",
        "close": "48500.0",
        "volume": "1.0",
    }]
    with pytest.raises(DataValidationError, match="Invariante OHLC violado"):
        parse_and_validate_klines(bad_candle, interval="15m")

    negative_vol = [{
        "time": 1700000000000,
        "open": "50000.0",
        "high": "51000.0",
        "low": "49000.0",
        "close": "50500.0",
        "volume": "-2.0",  # Volumen negativo
    }]
    with pytest.raises(DataValidationError, match="Volumen negativo"):
        parse_and_validate_klines(negative_vol, interval="15m")


def test_detect_temporal_gaps():
    """Verifica que se detecten huecos temporales en los datos."""
    interval_ms = 15 * 60 * 1000
    raw = [
        {"time": 1700000000000, "open": "50", "high": "51", "low": "49", "close": "50", "volume": "1"},
        {"time": 1700000000000 + 2 * interval_ms, "open": "50", "high": "51", "low": "49", "close": "50", "volume": "1"},
    ]
    with pytest.raises(DataValidationError, match="huecos temporales"):
        parse_and_validate_klines(raw, interval="15m", allow_gaps=False)


def test_storage_manifest_sha256(tmp_path: Path):
    """Verifica que el almacenamiento en Parquet y manifest guarde y valide el hash SHA-256."""
    raw = create_sample_raw_klines(n=5)
    df = parse_and_validate_klines(raw, interval="15m")

    target_file = tmp_path / "btc_15m.parquet"
    manifest_file = tmp_path / "manifest.json"

    entry = save_dataset_with_manifest(df, target_file, manifest_file, {"symbol": "BTC-USDT"})
    assert entry["rows"] == 5
    assert len(entry["sha256"]) == 64

    # Carga verificada exitosa
    df_loaded = load_dataset_verified(target_file, manifest_file)
    assert len(df_loaded) == 5

    # Si se corrompe el archivo modificando un byte
    with open(target_file, "r+b") as f:
        f.seek(10)
        f.write(b"\xFF")

    with pytest.raises(ValueError, match="Discrepancia de integridad"):
        load_dataset_verified(target_file, manifest_file)


def test_bingx_client_mock():
    """Verifica que BingXDataClient formule correctamente la petición de klines."""
    client = BingXDataClient(base_url="https://mock-api.bingx.com")
    mock_response = {
        "code": 0,
        "msg": "",
        "data": [{"time": 1700000000000, "open": "50000", "high": "51000", "low": "49000", "close": "50500", "volume": "10"}],
    }
    with patch.object(client, "_http_get", return_value=mock_response) as mock_get:
        klines = client.get_klines(symbol="BTC-USDT", interval="15m", limit=50)
        mock_get.assert_called_once_with(
            "/openApi/swap/v3/quote/klines",
            {"symbol": "BTC-USDT", "interval": "15m", "limit": 50},
        )
        assert len(klines) == 1
        assert klines[0]["close"] == "50500"
