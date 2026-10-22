# PRE-REGISTRO METODOLÓGICO INMUTABLE (VERSIÓN 2 — HOLDOUT 2010–2017)

**Fecha:** 2026-10-21  
**Estado:** CONGELADO PREVIO A CUALQUIER SIMULACIÓN  
**Inmutabilidad:** Este documento define la hipótesis única, la grilla de parámetros, los conjuntos de datos, los criterios de aceptación y las reglas de aislamiento antes de ejecutar cualquier backtest. Queda prohibido alterar cualquier umbral posterior a los resultados.

---

## 1. Hipótesis Única de Investigación

¿Puede un sistema de momentum técnico en velas de 4 horas (4h) que combina:
1. **Filtro de Tendencia:** Alineación de SMAs (2 SMAs: Close > SMA lenta y rápida > lenta; o 3 SMAs: rápida > media > lenta).
2. **Gatillo de Impulso:** Cruce del histograma MACD por encima de cero en dirección de la tendencia.
3. **Filtro de Sobreextensión:** RSI(14) en zona de impulso ($40 \le \text{RSI} \le 70$ para largos; $30 \le \text{RSI} \le 60$ para cortos).
4. **Gestión de Salida:** Stop Loss $k \times \text{ATR}(14)$, Take Profit $m \times \text{Riesgo}$, o **salida al cierre por cruce contrario de SMAs** (ej. reversión bajista de la alineación de medias).

Generar un rendimiento ajustado por riesgo positivo y robusto (Sharpe neto $\ge 1.00$, Deflated Sharpe $\ge 95\%$ y $N \ge 100$ trades) en futuros CME (ES y NQ)?

---

## 2. Grilla Reducida (Exactamente 32 Combinaciones por Activo)

La salida por cruce contrario de SMAs es una regla intrínseca de salida de la estrategia y **no añade combinaciones a la grilla**.
El espacio cerrado queda fijado en **32 combinaciones por activo**:

1. **Arquitecturas SMA (8 variantes):**
   * 2 SMAs: (20, 150), (20, 200), (30, 150), (30, 200)
   * 3 SMAs: (20, 100, 150), (20, 100, 200), (30, 100, 150), (30, 100, 200)
2. **Variantes MACD (2 variantes):**
   * Estándar: (12, 26, 9)
   * Lento / Suave: (16, 35, 9)
3. **Filtro RSI (1 variante fija):** Periodo 14
4. **Stop Loss ATR (2 variantes):** $k \in \{2.0, 3.0\}$
5. **Take Profit (1 variante fija):** $m = 2.0$ (Risk/Reward 1:2)

$$\text{Total combinaciones por activo} = 8 \times 2 \times 1 \times 2 \times 1 = 32 \text{ combinaciones.}$$

---

## 3. Partición de Datos y Aislamiento del Holdout

### A. Futuros CME (ES y NQ):
* **DESARROLLO (2017-12 a 2026-10):** Datos ya inspeccionados en pruebas previas (declarado explícitamente).
  * **Entrenamiento (70%):** 2017-12-15 a 2024-02-23 (9,902 barras de 4h). Se corre la grilla de 32 combinaciones.
  * **Validación (30%):** 2024-02-23 a 2026-10-19 (4,245 barras de 4h). Se elige la mejor configuración.
  * **Walk-Forward:** Evaluado **exclusivamente dentro de este tramo 2017-2026** (ventanas rodantes de 3 años train / 1 año test).
* **HOLDOUT BLOQUEADO (2010-06 a 2017-12):** 
  * Totalmente virgen, jamás visto en desarrollo.
  * Guardado en `data/locked_holdout/` con hashes SHA-256 registrados.
  * **NO se abre, grafica ni analiza hasta la evaluación final única.**

### B. Criptoactivos (BTC y ETH):
* **Estatus:** Exclusivamente **exploratorio y descriptivo**.
* No otorga veredicto de aprobación ni se incluye en cartera combinada a menos que cumpla $N \ge 100$ trades independientes.

---

## 4. Criterios de Aprobación Cuantitativos (Fijados de Antemano)

1. **Muestra Mínima:**
   * $N \ge 100$ trades agregados en las ventanas OOS del Walk-Forward (periodo 2017-2026).
   * $N \ge 100$ trades en el Holdout bloqueado (periodo 2010-2017) por activo (ES y NQ por separado).
2. **Sharpe Neto Anualizado:** $\ge 1.00$ en Holdout (anualizado por $\sqrt{252}$).
3. **Factor de Beneficio:** $\ge 1.30$.
4. **Drawdown Relativo Máximo:** $\le 20\%$ sobre un capital base fijado de:
   * **ES:** \$100,000 USD de capital base operando 1 contrato E-mini (Max DD en dólares $\le \$20,000$ USD).
   * **NQ:** \$150,000 USD de capital base operando 1 contrato E-mini (Max DD en dólares $\le \$30,000$ USD).
5. **Robustez Temporal Walk-Forward:** $\ge 60\%$ de las ventanas fuera de muestra con PnL neto positivo en el periodo 2017-2026.
6. **Deflated Sharpe Ratio (DSR):** $\ge 95\%$ ($p < 0.05$) ajustado por las 32 combinaciones de la grilla.
