# PRE-REGISTRO METODOLÓGICO: ESTRATEGIA A (BARRIDO DE MEDIAS MÓVILES TOP 10)

**Fecha:** 2026-10-22  
**Estado:** CONGELADO PREVIO A EVALUACIÓN  
**Principio de Inmutabilidad:** Este pre-registro define la grilla amplia, las reglas de señal y salida, el método de clustering ortogonal y los criterios de evaluación.

---

## 1. Hipótesis de Investigación

¿Puede una selección objetiva de las 10 mejores combinaciones de medias móviles (SMA y EMA) agrupadas por descorrelación de señales en la fase de validación mantener una expectativa positiva y estadísticamente significativa en el análisis temporal fuera de muestra (Walk-Forward) en futuros CME (ES y NQ)?

---

## 2. Espacio Paramétrico Cerrado (Grilla Pre-registrada)

### A. Tipos de Medias y Periodos:
* **Tipos de Media:** SMA y EMA.
* **Periodos Evaluados:**
  * Rápida ($P_1$): $\{10, 20, 30, 50\}$
  * Media ($P_2$): $\{50, 100\}$ (solo para variante de 3 medias)
  * Lenta ($P_3$): $\{100, 150, 200\}$
* **Variantes de Estructura:**
  1. **Precio vs. Media (1 MA):** Long si $\text{Close} > \text{MA}(P_3)$, Short si $\text{Close} < \text{MA}(P_3)$. (2 tipos MA $\times$ 3 periodos = 6 combinaciones).
  2. **Cruce de 2 Medias (2 MAs):** Long si $\text{MA}(P_1) > \text{MA}(P_3)$, Short si $\text{MA}(P_1) < \text{MA}(P_3)$ con $P_1 < P_3$. (2 tipos MA $\times$ 11 pares válidos = 22 combinaciones).
  3. **Alineación de 3 Medias (3 MAs):** Long si $\text{MA}(P_1) > \text{MA}(P_2) > \text{MA}(P_3)$, Short si $\text{MA}(P_1) < \text{MA}(P_2) < \text{MA}(P_3)$ con $P_1 < P_2 < P_3$. (2 tipos MA $\times$ 14 ternas válidas = 28 combinaciones).
* **Gestión de Salida:**
  * Salida por cruce contrario de señal.
  * Stop Loss fijo $k \times \text{ATR}(14)$ con $k \in \{2.0, 3.0\}$.
* **Timeframes Evaluados:** 1h y 4h (ambos cuentan en la multiplicidad total de pruebas).

$$\text{Total combinaciones por timeframe} = (6 + 22 + 28) \times 2 \text{ (ATR } k\text{)} = 112 \text{ combinaciones.}$$
$$\text{Total por activo (1h y 4h)} = 112 \times 2 = 224 \text{ combinaciones.}$$

---

## 3. Protocolo de Selección y Clustering de las Top 10

1. **Optimización en Train (70%):** Se calcula el rendimiento de las 224 combinaciones en el periodo de entrenamiento 2010–2021.
2. **Ranking en Validación (30%):** Se evalúan en el periodo de validación 2021–2026 y se ordenan por Ratio de Sharpe neto.
3. **Clustering por Descorrelación de Señales:**
   * Para evitar que el Top 10 esté compuesto por variantes casi idénticas (ej. SMA 20/200 vs SMA 21/200):
   * Se calcula la matriz de correlación de retornos diarios entre las candidatas de validación.
   * Se aplica un algoritmo de filtrado por distancia: si una candidata tiene una correlación $\rho \ge 0.75$ con una de rango superior ya seleccionada, se descarta.
   * Se extraen exactamente **10 finalistas ortogonales**.
4. **Contabilidad de Pruebas para DSR:**
   * El cálculo del *Deflated Sharpe Ratio* penaliza por el total de **$M = 224$ combinaciones exploradas**, no por las 10 elegidas.

---

## 4. Criterios de Aceptación Cuantitativos

1. **Muestra Mínima:** $N \ge 100$ trades agregados en las ventanas OOS del Walk-Forward.
2. **Sharpe Neto Anualizado:** $\ge 1.00$ en validación y walk-forward.
3. **Robustez Temporal (Walk-Forward):** $\ge 60\%$ de ventanas rodantes con PnL neto positivo.
4. **Deflated Sharpe Ratio (DSR):** $\ge 95\%$ ajustado por $M=224$.
5. **Drawdown Relativo:** $\le 20\%$ sobre capital base (\$100k ES, \$150k NQ).
