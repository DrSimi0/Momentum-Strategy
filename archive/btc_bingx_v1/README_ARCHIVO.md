# Archivo: estrategias BTC (v1.x y v3)

- **Fecha de archivo:** 2026-10-21
- **Motivo:** reemplazada por momentum intradía en ES/NQ (proyecto v4).
- **Estado:** solo lectura. El código nuevo no importa ni referencia nada de aquí.

## Qué contiene

1. **Momentum 4h en BTCUSDT perpetuo (v1.0.0 / v1.1.0, Binance):** `src/evaluation/`, `src/backtest/engine.py`, `src/data/download.py`, `src/data/loader.py`, `src/run_evaluation.py`, `config/*.yaml`, `config/freeze.json`, `config/lifecycle.json`, `DECISIONS.md`. Veredicto: FAIL (lifecycle `rejected`).
2. **Sistema multiagente / confluencia en 3 capas en BTC-USDT BingX 15m (v2/v3):** `src/strategy/`, `src/data/bingx_client.py`, `validator.py`, `storage.py`, `src/backtesting/engine_v3.py`, `src/alerts/`, `src/execution/`, `src/paper_trading/`, `scripts/`, `docs/`, `data/macro/`, `reports/signals_log.jsonl`. Veredicto: FAIL.
3. `tests/`: las 75 pruebas de ambas estrategias.
4. `local_untracked/` (**no versionado**, solo en esta máquina): parquet/csv de BTC y reportes generados. Se regeneran con los scripts archivados.

## Cómo restaurarlo

```bash
# Opción A: ver el estado exacto anterior al archivo
git checkout archive-btc-bingx-v1

# Opción B: recuperar una ruta concreta en la rama actual
git checkout archive-btc-bingx-v1 -- src/strategy/
```

Los archivos también están aquí, con la misma estructura relativa, bajo `archive/btc_bingx_v1/`.
