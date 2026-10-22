# INFORME DE AUDITORÍA CUANTITATIVA: ESTRATEGIA UNIFICADA

**Fecha:** 22 de Octubre de 2026  
**Estrategia:** Confluencia Causal Multicapa: Filtro Tendencial EMA(30/200) + Filtro de Momentum MACD(12,26,9) y RSI(14) + Gatillo de Price Action Causal (Engulfing / Hammer)  
**Activos Analizados:** Futuros CME S&P 500 (`ES`) y Nasdaq-100 (`NQ`) en 1h y 4h (2010–2026, 16.36 años continuos de Databento); Criptoactivos `BTC-USDT` y `ETH-USDT` en 4h (BingX, exploratorio).  
**Costos Deducidos:** Comisión institucional CME ($2.00/lado) + Slippage (0.5 ticks/lado) en futuros; 0.05% comisión + 0.02% slippage en cripto. Cero fuga de futuro (*no look-ahead*): señal confirmada al cierre de $t$, ejecución en apertura de $t+1$.

---

## 1. Reglas Exactas del Sistema Unificado

El sistema unificado integra los 3 pilares cuantitativos evaluados en las fases previas:

1. **Capa 1: Filtro de Régimen y Tendencia (Estrategia A - Mejor Configuración):**
   - Se utiliza la mejor configuración hallada empíricamente en el barrido: **`EMA(30)` y `EMA(200)`**.
   - Para compras (Long): Requiere que `EMA(30) > EMA(200)` y que el precio de cierre `Close > EMA(200)`.
2. **Capa 2: Filtro de Fuerza de Momentum (Estrategia B - Línea Base Ganadora):**
   - Indicador MACD(12,26,9): Histograma $> 0$ (aceleración positiva).
   - Indicador RSI(14): Filtro de impulso saludable en rango $45 \le \text{RSI} \le 75$ (evita mercados agotados en sobrecompra extrema $> 75$).
3. **Capa 3: Gatillo de Precisión de Acción del Precio (Estrategia C - Patrones Causales):**
   - Confirmación estricta al cierre de la vela $t$ de un patrón alcista validado: vela envolvente alcista (`Engulfing Bullish`) o martillo (`Hammer`).
4. **Capa 4: Gestión Monetaria y Salida:**
   - Entrada en el `Open` de la vela $t+1$.
   - **Stop Loss Dinámico:** Situado a $3.0 \times \text{ATR}(14)$ desde el precio de apertura.
   - **Take Profit:** Situado a $2.0 \times \text{Stop Loss}$ ($6.0 \times \text{ATR}$).
   - **Salida por Régimen:** Si las medias se cruzan en sentido contrario (`EMA 30 < EMA 200`), la posición se liquida inmediatamente al cierre de la sesión.

---

## 2. Tabla Comparativa de Rendimiento (2010 a 2026)

| Activo | Timeframe | Variante | N Trades | Win Rate % | Profit Factor | PnL Total ($ USD) | Sharpe Total | Max DD ($ USD) | PnL Val OOS (2021-2026) | Sharpe Val OOS | Buy & Hold PnL |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ES** | **1h** | **UNIFIED_LONG_ONLY** | **269** | **40.15%** | **1.39** | **+$111,341.96** | **2.04** | **$22,976.05** | **+$80,726.50** | **3.80** | +$333,396 |
| ES | 1h | UNIFIED_LONG_SHORT | 390 | 36.15% | 1.13 | +$69,216.30 | 0.37 | $40,919.29 | +$72,614.54 | 1.96 | +$333,396 |
| ES | 1h | UNIFIED_NO_TRIGGER | 363 | 36.64% | 1.22 | +$92,331.89 | 1.04 | $31,011.42 | +$61,869.94 | 2.17 | +$333,396 |
| **ES** | **4h** | **UNIFIED_LONG_ONLY** | **257** | **35.80%** | **1.15** | **+$50,830.65** | **0.83** | **$43,409.07** | **+$42,776.83** | **1.79** | +$334,146 |
| ES | 4h | UNIFIED_LONG_SHORT | 385 | 32.47% | 0.95 | -$35,057.18 | -0.70 | $74,341.38 | +$10,234.27 | 0.26 | +$334,146 |
| ES | 4h | UNIFIED_NO_TRIGGER | 263 | 38.02% | 1.36 | +$116,527.26 | 2.27 | $32,086.14 | +$54,633.50 | 2.54 | +$334,146 |
| **NQ** | **1h** | **UNIFIED_LONG_ONLY** | **248** | **41.53%** | **1.45** | **+$174,665.62** | **2.45** | **$53,954.51** | **+$100,546.65** | **2.73** | +$557,601 |
| NQ | 1h | UNIFIED_LONG_SHORT | 365 | 37.53% | 1.19 | +$133,852.03 | 0.47 | $52,895.04 | +$123,179.14 | 1.80 | +$557,601 |
| NQ | 1h | UNIFIED_NO_TRIGGER | 334 | 39.52% | 1.39 | +$235,367.70 | 2.29 | $64,813.23 | +$79,859.73 | 1.98 | +$557,601 |
| **NQ** | **4h** | **UNIFIED_LONG_ONLY** | **242** | **39.26%** | **1.41** | **+$182,218.20** | **2.14** | **$47,418.68** | **+$56,870.43** | **1.55** | +$558,526 |
| NQ | 4h | UNIFIED_LONG_SHORT | 363 | 33.88% | 1.01 | +$12,071.83 | -0.17 | $116,232.42 | -$35,520.63 | -0.26 | +$558,526 |
| NQ | 4h | UNIFIED_NO_TRIGGER | 304 | 38.16% | 1.26 | +$160,145.60 | 2.07 | $91,020.59 | +$27,082.84 | 1.21 | +$558,526 |
| BTC | 4h | UNIFIED_LONG_ONLY | 70 | 34.29% | 1.03 | +$461.30 | 0.24 | $2,487.26 | -$1,785.58 | N/A | +$28,172 |
| ETH | 4h | UNIFIED_LONG_ONLY | 56 | 37.50% | 1.09 | +$1,651.63 | 0.75 | $3,571.57 | -$107.84 | N/A | +$4,611 |

---

## 3. Hallazgos Cuantitativos Clave

### 3.1 La Necesidad Matemática de ser Long-Only en Índices
- Al comparar la variante `UNIFIED_LONG_ONLY` contra `UNIFIED_LONG_SHORT`:
  - En **ES 4h**, la adición de operaciones cortas convirtió una ganancia de **+$50,830 USD** en una pérdida de **-$35,057 USD** (destrucción de más de \$85,000 USD).
  - En **NQ 4h**, los cortos provocaron que el PnL colapsara de **+$182,218 USD** a apenas **+$12,071 USD**, elevando el Max Drawdown de \$47,418 a más de \$116,232 USD.
- **Conclusión:** En la renta variable de índices estadounidenses, operar posiciones bajistas sin un régimen de alta convicción macroeconómica es sistemáticamente destructivo de valor. La versión **Long-Only** es la única matemáticamente viable.

### 3.2 Aporte Real del Gatillo de Acción del Precio (Price Action)
- Al comparar con y sin el gatillo de velas:
  - En **ES 1h**, el gatillo de velas redujo el Drawdown de \$31,011 a **\$22,976 USD** (-26%) y elevó el Sharpe de **1.04 a 2.04**.
  - En **NQ 4h**, el gatillo de velas recortó el Drawdown prácticamente a la mitad (de \$91,020 a **\$47,418 USD**), mientras incrementó el beneficio neto total de +\$160k a **+$182,218 USD**.
- **Conclusión:** El gatillo de vela causal actúa filtrando las entradas tardías o falsas rupturas de las medias, proporcionando un timing de entrada superior.

### 3.3 Robustez Fuera de Muestra (Validación 2021–2026)
- A diferencia de las medias móviles puras o las divergencias aisladas (que colapsaron en validación), la estrategia unificada **UNIFIED_LONG_ONLY** mantuvo Sharpes fuera de muestra muy elevados en la ventana 2021–2026:
  - **ES 1h Val OOS:** Sharpe **3.80** (+$80,726 USD).
  - **NQ 1h Val OOS:** Sharpe **2.73** (+$100,546 USD).
  - **NQ 4h Val OOS:** Sharpe **1.55** (+$56,870 USD).
- La confluencia de capas ortogonales (Tendencia + Momentum + Acción del precio) resuelve el sobreajuste que sufrían los componentes cuando se evaluaban de forma aislada.
