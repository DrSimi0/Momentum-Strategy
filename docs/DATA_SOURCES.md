# Documentación de Fuentes de Datos y Mecanismos de Ajuste

## 1. Futuros de Índices CME: E-mini S&P 500 (`ES`) y E-mini Nasdaq-100 (`NQ`)

* **Proveedor de Datos:** Databento.
* **Dataset:** `GLBX.MDP3` (CME Globex MDP 3.0 Market Data).
* **Esquema:** `ohlcv-1m` (barras de 1 minuto con open, high, low, close, volume).
* **Convención Temporal:** `ts_event` en UTC representando el inicio del intervalo (validado empíricamente por picos de volumen en `09:30` apertura regular y `15:59` cierre de contado).
* **Manejo de Rollovers y Símbolos Continuos:**
  * Se utilizan las series continuas por volumen de Databento: `ES.v.0` y `NQ.v.0`.
  * **Regla de Rollover:** El contrato continuo rollea automáticamente al contrato de futuros con mayor volumen de negociación.
  * **Ajuste de Precios:** **Sin ajuste artificial (unadjusted).** En backtesting institucional de futuros, los precios no se concatenan mediante sumas o factores multiplicativos retrospectivos (como en backtests de acciones), para preservar los niveles reales de liquidación de márgenes, puntos de tick y cash flow exacto de las cuentas de futuros.
* **Agregación a 4 Horas:** Remuestreo a partir de velas de 1 minuto, respetando el horario de negociación regular y excluyendo las pausas diarias de 17:00–18:00 ET.

---

## 2. Criptoactivos Perpetuos: Bitcoin (`BTC-USDT`) y Ethereum (`ETH-USDT`)

* **Proveedor de Datos:** BingX (API REST Pública de Swap USDT-M).
* **Endpoint de Lectura:** `GET https://open-api.bingx.com/openApi/swap/v3/quote/klines`
* **Credenciales:** Endpoints públicos de solo lectura. No se utilizan claves privadas ni permisos de trading.
* **Símbolos:** `BTC-USDT` y `ETH-USDT` (contratos perpetuos lineales con margen en USDT).
* **Profundidad Histórica:** La API pública de contratos perpetuos de BingX inició el **12 de septiembre de 2022**. La profundidad máxima verificada es de **4.1 años** (9,001 barras de 4h). Solicitudes a fechas anteriores a septiembre de 2022 retornan 0 barras.
* **Horario y Agregación:** Mercado continuo 24 horas al día, 7 días a la semana (24/7). Barras agregadas a 4 horas alineadas en UTC (00:00, 04:00, 08:00, 12:00, 16:00, 20:00).
* **Costos Transaccionales Modelados:**
  * Comisión Taker: 0.05% por lado (0.10% round-turn).
  * Deslizamiento (*Slippage*): 0.02% por lado en BTC, 0.03% por lado en ETH.
  * Tasa de Financiación (*Funding Rate*): 0.01% cada 8 horas (acumulada proporcionalmente al tiempo de retención de cada posición).
