# Inventario inicial del repositorio (antes de v4)

Fecha: 2026-10-21. Commit de partida: `ade44f5` (rama `main`).

## Contenido versionado

| Ruta | Contenido | Estrategia |
|---|---|---|
| `src/strategy/` | Capas 1–3, árbitro de confluencia, indicadores (RSI, MACD, BBWP, fractales) | BTC-USDT BingX 15m (v3) |
| `src/data/bingx_client.py`, `validator.py`, `storage.py` | Conector y validación de velas BingX | BTC-USDT BingX 15m (v3) |
| `src/data/download.py`, `loader.py` | Descarga de velas 4h y funding de Binance | BTC momentum 4h (v1.x) |
| `src/backtest/engine.py`, `src/backtesting/engine_v3.py` | Motores de backtest de cripto (funding, apalancamiento) | v1.x / v3 |
| `src/evaluation/` | Métricas, robustez, veredicto, potencia, reportes | v1.x |
| `src/alerts/`, `src/execution/`, `src/paper_trading/` | Alertas, executor desactivado, paper trading | v3 |
| `src/run_evaluation.py`, `scripts/` | Puntos de entrada de v1.x y v3 | v1.x / v3 |
| `config/` | `acceptance.yaml`, `strategy*.yaml`, `freeze.json`, `lifecycle.json` | v1.x |
| `docs/` | Notas de API BingX, hipótesis, preregistro y decisiones de v2/v3 | v2 / v3 |
| `data/macro/`, `data/manifest.json` | Fear & Greed, eventos macro, manifiesto de datos BTC | v1.x / v3 |
| `reports/signals_log.jsonl` | Registro de señales en paper trading | v3 |
| `tests/` | 75 pruebas de las estrategias anteriores | v1.x / v3 |
| `DECISIONS.md`, `README.md`, `.gitignore` | Documentación raíz | v1.x / v3 |

## No versionado (ignorado por git)

- `data/historical/bingx_btc_usdt_15m.parquet`, `data/test_sample_15m.parquet`, `data/processed/BTCUSDT_*.csv`: datos de BTC.
- `reports/*.md|*.json|*.png`, `reports/.holdout_used`: reportes y candado de holdout de v1.x / v3.

## Diagnóstico

Todo el contenido pertenece a estrategias sobre BTC (momentum 4h en Binance y confluencia 15m en BingX). Nada es específico de futuros ES/NQ. Se archiva completo en `archive/btc_bingx_v1/`. La infraestructura genérica (pruebas, logging) se reescribe en lugar de reutilizarse, porque está acoplada a cripto (funding, apalancamiento, anualización 24/7). Ver `docs/DECISIONS.md`, D-001.
