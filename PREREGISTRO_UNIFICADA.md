# PRE-REGISTRO METODOLÓGICO: ESTRATEGIA CUANTITATIVA UNIFICADA (EXPLORATORIA)

**Fecha:** 2026-10-23  
**Estado:** CONGELADO PREVIO A AUDITORÍA  
**Declaración Metodológica:** La Estrategia Cuantitativa Unificada fue diseñada utilizando información del periodo 2010–2026. En consecuencia, queda formalmente declarada como **EXPLORATORIA** y carece de un holdout virgen independiente. Se prohíbe el uso de términos como "validada" o "ganadora".

---

## 1. Hipótesis de Investigación

¿Posee la confluencia multicapa de:
1. Filtro de régimen tendencial (`EMA 30` vs `EMA 200`),
2. Filtro de momentum (`MACD 12,26,9` acelerando e impulso `45 <= RSI(14) <= 75`),
3. Gatillo de acción del precio causal al cierre (`Engulfing Bullish` o `Hammer`),
una ventaja estadística persistente tras deducir comisiones y slippage reales en futuros CME, que no sea explicable por el drift alcista del mercado, el azar de muestreo o la concentración en un puñado de operaciones atípicas?

---

## 2. Reglas Formales del Sistema (Inmutables)

- **Universo Principal:** Futuros CME S&P 500 E-mini (`ES`) y Nasdaq-100 E-mini (`NQ`) en 1h y 4h.
- **Dirección Operativa:** Estrictamente **Long-Only** (las ventas en corto quedan vetadas en índices bursátiles debido al sesgo alcista secular).
- **Señal al Cierre de la Vela $t$:**
  1. Régimen: $\text{EMA}(30)_t > \text{EMA}(200)_t$ y $\text{Close}_t > \text{EMA}(200)_t$.
  2. Momentum: $\text{MACD\_Hist}_t > 0$ y $45.0 \le \text{RSI}(14)_t \le 75.0$.
  3. Gatillo: Aparición en la barra $t$ de patrón `Hammer` o `Engulfing Bullish`.
- **Ejecución Causal en $t+1$:** Entrada obligatoria en el `Open` de la vela $t+1$.
- **Gestión de Salida:**
  - $\text{Stop Loss} = \text{Open}_{t+1} - 3.0 \times \text{ATR}(14)_t$.
  - $\text{Take Profit} = \text{Open}_{t+1} + 6.0 \times \text{ATR}(14)_t$ (Ratio 1:2).
  - Salida de Emergencia: Cruce contrario $\text{EMA}(30)_{i-1} < \text{EMA}(200)_{i-1}$.
- **Costos Reales CME:** Comisión institucional (\$2.00 por lado) + Slippage institucional (0.5 ticks por lado).

---

## 3. Contabilidad del Espacio de Búsqueda ($M$)

Para el cálculo del *Deflated Sharpe Ratio* (DSR), se contabilizan todas las configuraciones probadas en el proyecto:
- Estrategia A (Barrido Medias Móviles): $M_A = 224$.
- Estrategia B (Relación Dinámica RSI/MACD): $M_B = 40$.
- Estrategia C (Patrones y Figuras Chartistas): $M_C = 42$.
- Estrategia Unificada (Variantes Long-Only, Long-Short, No-Trigger en 1h, 4h, 15m, 5m): $M_U = 12$.
- Optimización Intradía M15/M5: $M_{intra} = 20$.
- **Total Acumulado de Pruebas:** $M = 338$.

---

## 4. Criterios de Auditoría y Rechazo

La estrategia será catalogada como **NO APÓSITA PARA PRODUCCIÓN / RECHAZADA** si:
1. El Max Drawdown histórico sobre contratos estándar o micro excede el límite operativo de control de riesgo (\$2,000–\$3,000 USD en prop firms).
2. El p-valor del test de permutación (10,000 iteraciones vs señales aleatorias) es $p > 0.05$ (no bate al azar).
3. El *Deflated Sharpe Ratio* (DSR) ajustado por $M=338$ es $< 95\%$.
4. El rendimiento neto colapsa al retirar los 5 mejores trades (hipótesis de concentración frágil).
5. El mapa de sensibilidad paramétrica alrededor de `EMA 30/200` y `Stop 3 ATR` revela un pico aislado y no una meseta estable.
