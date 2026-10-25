# PRE-REGISTRO METODOLÓGICO: ESTRATEGIA INTRADÍA CON LÍNEA DE TENDENCIA ÚNICA (EMA 200)

**Fecha:** 2026-10-25  
**Estrategia:** Unificada Intradía con Tendencia EMA 200 y Salida Forzada MOC  
**Rama:** `feature/lower-tf-m5-m15`  
**Temporalidades:** 15m y 5m  
**Activos:** NQ (E-mini Nasdaq 100) y ES (E-mini S&P 500)  
**Estado:** CONGELADO ANTES DE CUALQUIER EJECUCIÓN O OPTIMIZACIÓN  
**Estatus Metodológico:** Protocolo Walk-Forward / Partición Limpia Train-Test (Holdout Virgen de 2 Años)

---

## 1. Definición de la Estrategia

### 1.1 Línea de Tendencia Única
Se sustituye el sistema previo de cruce de dos medias móviles (rápida/lenta) por **una sola media móvil exponencial de 200 períodos (EMA 200)**:
- **Filtro de Régimen Alcista:** Solo se permiten compras si el precio de cierre está por encima de la EMA 200 (`Close[t] > EMA_200[t]`).
- **Pérdida de Régimen:** Si el precio cierra por debajo de la EMA 200 (`Close[t-1] < EMA_200[t-1]`), se invalida cualquier señal de compra y, si hay una posición abierta, se liquida inmediatamente en la apertura de la barra actual.

### 1.2 Reglas Operativas Intradía
- **Horario RTH Permitido para Nuevas Entradas:** Entre las **10:00 ET** y las **15:15 ET**.
- **Cierre Forzado de Sesión (MOC):**
  - **Timeframe 15m:** Salida obligatoria e incondicional en la apertura de la barra **15:45 ET** (cero riesgo nocturno).
  - **Timeframe 5m:** Salida obligatoria e incondicional en la apertura de la barra **15:50 ET**.
  - **Condición Absoluta:** 0% de trades overnight (ninguna posición cruza el cierre de mercado de las 16:00 ET).
- **Filtro de Expansión de Volatilidad:** ATR(14) $\ge$ SMA(ATR, 40) $\times 0.95$ (evita falsas señales en rangos estrechos de baja volatilidad).
- **Gestión de Riesgo:**
  - Stop Loss: $k \times \text{ATR}(14)$ por debajo del precio de entrada.
  - Take Profit: $m \times \text{Stop Loss}$ (o trailing según variante).

---

## 2. Partición Temporal Estricta (5 Años Totales)

Para evitar la contaminación de datos (*data snooping / overfitting*), los 5 años disponibles se dividen de forma estricta:
1. **Período In-Sample (Entrenamiento y Optimización Acotada - 3 Años):**
   - **Fechas:** Del **2021-10-20** al **2024-10-19**.
   - **Objetivo:** Calibrar los hiperparámetros (gatillo de entrada, múltiplo de stop ATR $k$, y múltiplo de take profit $m$).
2. **Período Out-of-Sample (Verificación Ciega / Holdout Virgen - 2 Años):**
   - **Fechas:** Del **2024-10-20** al **2026-10-19**.
   - **Objetivo:** Evaluar la configuración óptima sin realizar ningún cambio ni re-optimización.

---

## 3. Espacio de Búsqueda en Entrenamiento ($M_{\text{train}}$)

En los 3 años de entrenamiento se evalúan de forma acotada las siguientes combinaciones:
1. **Gatillos de Entrada (`trigger_type`):**
   - `candle_pattern`: Patrón de vela Martillo o Envolvente alcista mientras `Close > EMA 200`.
   - `price_cross`: Cruce alcista del precio sobre la EMA 200 (`Close[t] > EMA 200` y `Close[t-1] <= EMA 200`).
   - `macd_turn`: `Close > EMA 200` + giro alcista del histograma MACD (`Hist[t] > 0` y `Hist[t-1] <= 0`).
2. **Stop Loss ATR (`atr_k`):** $\{1.5, 2.0, 2.5, 3.0\}$.
3. **Take Profit Multiplier (`tp_m`):** $\{1.5, 2.0, 3.0\}$.

Total de combinaciones por activo y temporalidad: $3 \times 4 \times 3 = 36$ configuraciones.
Todas estas pruebas se sumarán al contador formal de minería $M$.

---

## 4. Criterios de Aceptación Fuera de Muestra (Out-of-Sample)

Una configuración se considerará exitosa y con ventaja estadística real si en los 2 años fuera de muestra cumple:
1. **PnL Neto Positivo:** Retorno $> 0$ tras descontar comisiones ($2/lado) y slippage (0.5 ticks/lado).
2. **Sharpe Diario sobre Capital Fijo ($50k):** $\ge 0.50$ (mínimo aceptable) y deseable $\ge 1.00$.
3. **Ratio de Degradación de Sharpe:** $\frac{\text{Sharpe}_{\text{Test}}}{\text{Sharpe}_{\text{Train}}} \ge 0.50$ (no perder más del 50% de consistencia).
4. **Profit Factor:** $\ge 1.15$.
5. **Drawdown:** No exceder el 20% del capital inicial en intradía.
