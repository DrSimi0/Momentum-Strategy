# Sistema Multiagente de Confluencia en 3 Capas — BTC-USDT (BingX, 15m)
*Versión 3.0 — Proyecto Académico y de Experimentación Cuantitativa Determinista*

---

## 1. Resumen de la Estrategia (Prompt v3)

El sistema implementa una **confluencia jerárquica descendente en tres capas**:
- **Capa 1 (Macro y Sentimiento):** Filtro direccional Point-in-Time y ventana de abstención de $\pm 60$ minutos en torno a eventos macroeconómicos de 3 estrellas (CPI, FOMC, NFP) y posicionamiento según el índice Fear & Greed.
- **Capa 2 (Estructura Técnica):** Detección determinista de soportes/resistencias fractales con confirmación retardada ($k=3$), BBWP, MACD z-score, setups de ruptura/rebote con volumen, Stop-Loss prefijado, Take-Profit ($R:R \ge 2.0$), Break-Even al alcanzar $+1.0R$ y horizonte temporal máximo de 15 barras (3.75 horas).
- **Capa 3 (Microestructura):** Validación de absorción de liquidez en la vela de 15m y registro en segundo plano para datos fuera de muestra futuros.
- **Regla de Conflicto (Anti-Trampa):** La capa superior prevalece siempre sobre la inferior. Un setup técnico contra-tendencia macro se descarta deterministamente como trampa de mercado (`NEUTRAL`).

---

## 2. Comandos de Reproducibilidad

### 2.1 Ejecutar Suite Completa de Pruebas Unitarias (75 tests)
```bash
python -m pytest
```

### 2.2 Descargar Dataset Histórico Verificado desde BingX (Solo Lectura)
```bash
python scripts/download_bingx_15m.py --start 2023-01-01 --out data/historical/bingx_btc_usdt_15m.parquet
```

### 2.3 Ejecutar Evaluación y Reporte de Ablación (V1 vs V2)
```bash
python scripts/run_v3_evaluation.py
```
*El reporte detallado se genera en [`reports/v3_evaluation_report.md`](reports/v3_evaluation_report.md).*

### 2.4 Ejecutar Monitoreo en Tiempo Real / Paper Trading (Nivel 1 y 2)
```bash
python scripts/run_paper_trading.py
```
*Registra las señales en [`reports/signals_log.jsonl`](reports/signals_log.jsonl) y mantiene el estado en [`reports/paper_trading_state.json`](reports/paper_trading_state.json). La ejecución real está DESACTIVADA por defecto mediante `SafeNullExecutor`.*

---

## 3. Documentación Metodológica

- [`docs/estrategia.md`](docs/estrategia.md): Especificación matemática y conceptual de la estrategia de confluencia.
- [`docs/preregistro.md`](docs/preregistro.md): Protocolo de evaluación científica congelado con hash SHA-256 del dataset.
- [`docs/decisiones.md`](docs/decisiones.md): Registro histórico y justificación técnica de todas las decisiones adoptadas.
- [`docs/bingx_api_notes.md`](docs/bingx_api_notes.md): Especificación técnica de la API pública USDT-M de BingX.
