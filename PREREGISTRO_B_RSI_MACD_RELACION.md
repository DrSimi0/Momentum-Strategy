# PRE-REGISTRO METODOLÓGICO: ESTRATEGIA B (RELACIÓN DINÁMICA RSI / HISTOGRAMA MACD)

**Fecha:** 2026-10-22  
**Estado:** CONGELADO PREVIO A EVALUACIÓN  
**Principio de Inmutabilidad:** Este pre-registro define las reglas matemáticas para calcular la correlación móvil RSI-MACD, la detección causal de divergencias, los estados de acuerdo/desacuerdo y los criterios de contraste frente a líneas base.

---

## 1. Hipótesis de Investigación

¿Aporta valor predictivo estadísticamente medible la **relación dinámica** entre el RSI(14) y el Histograma MACD(12,26,9) (correlación rodante, divergencias confirmadas y sincronización acuerdo tras desacuerdo) frente a usar el RSI solo, el MACD solo o una regla estática de ambos en acuerdo?

---

## 2. Variables y Estados de la Relación

1. **Correlación Móvil Rodante ($\rho_{t}$):**
   * Correlación de Pearson en ventana rodante de $W=20$ barras entre la serie de $\text{RSI}(14)$ y el $\text{Histograma MACD}(12,26,9)$.
2. **Estados de Acuerdo vs. Desacuerdo:**
   * **Acuerdo Alcista:** $\text{RSI} > 50$ y $\text{Hist MACD} > 0$.
   * **Acuerdo Bajista:** $\text{RSI} < 50$ y $\text{Hist MACD} < 0$.
   * **Desacuerdo:** Uno alcista y el otro bajista (conflicto de momento).
3. **Divergencias Confirmadas Causales (Retardo $n=2$ barras):**
   * **Divergencia Regular Alcista:** Precio marca un mínimo local más bajo ($P_{t} < P_{t-k}$), pero RSI o Histograma MACD marcan un mínimo más alto.
   * **Divergencia Regular Bajista:** Precio marca un máximo local más alto ($P_{t} > P_{t-k}$), pero RSI o Histograma MACD marcan un máximo más bajo.
   * *Regla causal:* Un pivote local en $t-2$ solo se declara si $P_{t-2}$ es extremo respecto a $t-4, t-3, t-1, t$. Cero look-ahead.

---

## 3. Reglas de Entrada Pre-registradas (Casos Concretos)

Se definen 4 arquitecturas de entrada para contrastar:
* **Caso 1 (Relación A - Acuerdo tras Desacuerdo):**
  * Entrada Long: La barra previa $t-1$ estaba en Desacuerdo, y al cierre de $t$ se produce Acuerdo Alcista con $\rho_{t} > 0.50$ (re-sincronización de impulso).
  * Entrada Short: Desacuerdo en $t-1$, y Acuerdo Bajista en $t$ con $\rho_{t} > 0.50$.
* **Caso 2 (Relación B - Divergencia Confirmada con Re-alineación):**
  * Entrada Long: Divergencia alcista confirmada en los últimos 5 periodos + cruce alcista de MACD o RSI cruza 50 al alza.
  * Entrada Short: Divergencia bajista confirmada + cruce bajista de MACD o RSI cruza 50 a la baja.
* **Líneas Base de Comparación Obligatorias:**
  * **Línea Base 1 (RSI Solo):** Cruce del RSI por encima de 50 (Long) o por debajo de 50 (Short).
  * **Línea Base 2 (MACD Solo):** Cruce del Histograma MACD por encima de cero (Long) o por debajo de cero (Short).
  * **Línea Base 3 (Acuerdo Simple Estático):** Long si $\text{RSI} > 50$ y $\text{Hist} > 0$ sin exigir estado previo de desacuerdo.

---

## 4. Gestión de Salidas y Espacio Paramétrico

* **Salidas:**
  * Stop Loss fijo $k \times \text{ATR}(14)$ con $k \in \{2.0, 3.0\}$.
  * Take Profit fijo $m \times \text{Stop}$ con $m \in \{1.5, 2.0\}$.
  * Salida por señal contraria confirmada.
* **Timeframes:** 1h y 4h.
* **Total Combinaciones por Activo:**
  4 modelos (2 casos de relación + 2 líneas base aisladas) $\times$ 2 valores de $k$ $\times$ 2 valores de $m$ $\times$ 2 timeframes = **32 configuraciones**.

---

## 5. Criterios de Aceptación Cuantitativos

1. **Superioridad de la Relación:** La estrategia basada en la relación dinámica debe superar en Sharpe neto y Profit Factor tanto a RSI Solo como a MACD Solo en validación y walk-forward.
2. **Muestra Mínima:** $N \ge 100$ trades agregados en las ventanas OOS del Walk-Forward.
3. **Sharpe Neto Anualizado:** $\ge 1.00$.
4. **Walk-Forward:** $\ge 60\%$ de ventanas rodantes positivas.
5. **Deflated Sharpe (DSR):** $\ge 95\%$ considerando $M=32$.
