# Inspección del Repositorio y Diagnóstico de Reutilización
*Transición de Momentum-Strategy v1.x a Sistema Multiagente v2.0*

---

## 1. Estado Actual del Repositorio

El repositorio albergaba la estrategia Momentum Trend-Following v1.1.0 en temporalidad de 4 horas, la cual concluyó con veredicto formal `rejected` en el ciclo de vida tras evaluar el holdout intocable (`reports/profitability_report.md` y `reports/final_report.md`).

### 1.1 Componentes Existentes y Potencial de Reutilización

| Componente Existente | Estado / Ubicación | Diagnóstico y Plan de Reutilización |
|---|---|---|
| **Métricas Estadísticas** | `src/evaluation/metrics.py` | **100% Reutilizable:** Cálculo de Sharpe, Sortino, Calmar, Max Drawdown, VaR/CVaR, Expectativa por operación y Profit Factor. Requiere adaptar el factor de anualización a 15m ($\sqrt{35,040}$). |
| **Robustez Estadística** | `src/evaluation/robustness.py` | **100% Reutilizable:** Módulos de Block Bootstrap (Politis & Romano), Deflated Sharpe Ratio (Bailey & López de Prado) y Monte Carlo de orden de operaciones. |
| **Pruebas Unitarias Previas** | `tests/test_metrics.py`, `tests/test_verdict.py` | **100% Reutilizable:** Pruebas contra ejemplos numéricos manuales pequeños. |
| **Motor de Backtesting** | `src/backtesting/engine.py` | **Adaptable:** Motor determinista orientado a eventos con cálculo de costos (taker fee, slippage, funding). Se reutilizará el núcleo de simulación con ejecución estricta en $t+1$ (open de la siguiente barra). |
| **Gestión de Ciclo de Vida** | `config/lifecycle.json` | **Reutilizable:** Mantener el estado `rejected` para v1.1.0 (bloqueo permanente) y abrir un nuevo espacio de nombres para v2.0 (`btc_multiagent_v2`). |

---

## 2. Componentes Faltantes que Requieren Construcción

1. **Módulo de Ingestión BingX:**
   - No existía cliente para BingX (la v1 usaba Binance/Coinbase en 4h). Se requiere `src/data/bingx_client.py`.
2. **Validador de Velas de 15m:**
   - Descarte determinista de vela abierta en tiempo real, detección de gaps de 15m y chequeo de invariantes OHLCV (`src/data/validator.py`).
3. **Capa de Datos Exógenos Point-in-Time:**
   - Ingestor de Fear & Greed y calendario macroeconómico con estricta marca de tiempo de publicación (`src/data/context_loader.py`).
4. **Catálogo de Estrategias Formalizadas Clase A:**
   - Implementaciones algorítmicas de fractales S/R, divergencias de RSI con retardo fijo, MACD normalizado y BBWP (`src/signals/technical.py`).
5. **Arquitectura Multiagente Estructurada:**
   - Esquemas Pydantic para salidas de agentes (`Investigador`, `Cuantitativo`, `Contexto`, `Visual`, `Evaluador`) y el orquestador de estados (`src/agents/`).
6. **Módulo de Renderizado para Agente Visual:**
   - Generación determinista de gráficos estáticos con Matplotlib hasta el tiempo $t$ para que el modelo multimodal los inspeccione sin fuga de futuro (`src/agents/chart_renderer.py`).
7. **Motor de Alertas (Nivel 1):**
   - Publicador de señales `LONG / SHORT / NEUTRAL` vía Telegram/JSONL con registro inmutable de razones y parámetros de invalidación (`src/alerts/dispatcher.py`).
