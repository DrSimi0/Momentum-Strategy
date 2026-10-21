# Documento de Pre-registro Metodológico (Protocolo Congelado)
**Proyecto:** Evaluación Rigurosa del Momentum Intradía en Futuros ES y NQ (Gao, Han, Li y Zhou, *JFE* 2018)  
**Versión:** 4.0  
**Fecha de Congelamiento:** 2026-10-21  
**Git Tag:** `preregistro-congelado`  

---

## 1. Pregunta de Investigación e Hipótesis

¿Posee el retorno de la primera media hora ($r_1$, desde el cierre previo hasta las 10:00 ET) y/o el de la penúltima media hora ($r_{12}$, 15:00 a 15:30 ET) capacidad predictiva estadísticamente significativa y económicamente explotable sobre el retorno de la última media hora ($r_{13}$, 15:30 a 16:00 ET) en los futuros E-mini S&P 500 (ES) y E-mini Nasdaq-100 (NQ), netos de costos de transacción y fuera de muestra?

### Hipótesis Primarias (8 pruebas principales: ES y NQ)
- **H1:** Señal direccional basada en el signo de la primera media hora: $\text{Señal}_t = \text{sign}(r_{1, t})$.
- **H2:** Señal direccional basada en el signo de la penúltima media hora: $\text{Señal}_t = \text{sign}(r_{12, t})$.
- **H3:** Señal combinada condicional: Opera solo si $\text{sign}(r_{1, t}) == \text{sign}(r_{12, t})$, con la dirección común; neutral ($0$) si difieren.
- **H4:** H1 filtrada por volatilidad: Opera la señal de H1 únicamente si la volatilidad realizada de los primeros 30 minutos supera la mediana histórica expansiva (calculada estrictamente con días anteriores $0 \dots t-1$, mínimo 250 días).

### Líneas Base de Comparación (Baselines)
- **B1 (Buy & Hold Intradía):** Siempre Long (+1) durante los últimos 30 minutos (15:30 a 16:00 ET).
- **B2 (Permutación):** Destrucción aleatoria del emparejamiento temporal entre señales y retornos objetivo.
- **B3 (Contraria a H1):** Señal invertida: $\text{Señal}_t = -\text{sign}(r_{1, t})$.

---

## 2. Datos y Particiones Temporales

- **Fuente:** Databento (`GLBX.MDP3`, esquema `ohlcv-1m`).
- **Instrumentos:** Contratos continuos por volumen `ES.v.0` y `NQ.v.0`.
- **Integridad y Hashes:** SHA-256 verificado en `data/metadata.json`.
- **Calendario:** XNYS (`America/New_York`), excluyendo feriados y cierres anticipados.
- **Horarios Críticos ET:**
  - Apertura regular: `09:30` ET
  - Cierre primera media hora: barra `09:59` ET (cierre a las 10:00)
  - Apertura penúltima media hora: barra `15:00` ET
  - Cierre penúltima media hora: barra `15:29` ET
  - Entrada de trading: barra `15:30` ET (precio Open)
  - Salida de trading: barra `15:59` ET (precio Close)

### Particiones Temporales (Fijadas antes de la prueba final)
1. **Desarrollo (In-Sample):** 2018-01-02 a 2021-12-31 (4 años, 999 sesiones).
2. **Validación (Out-of-Sample preliminar):** 2022-01-01 a 2023-12-31 (2 años, 498 sesiones).
3. **Prueba Final / Holdout Estricto:** 2024-01-01 a 2026-10-19 (~2.8 años, 696 sesiones).

---

## 3. Modelo de Costos de Transacción

Costos fijos por contrato por operación de ida y vuelta (round-turn = entrada + salida = 2 lados):
- **Caso Base:**
  - Deslizamiento (Slippage): 0.5 ticks por lado (1.0 tick round-turn).
  - Comisión de broker/exchange: \$2.00 por lado (\$4.00 round-turn).
  - Costo total por trade:
    - **ES:** Deslizamiento \$12.50 + Comisión \$4.00 = **\$16.50 / trade**.
    - **NQ:** Deslizamiento \$5.00 + Comisión \$4.00 = **\$9.00 / trade**.
- **Caso Estrés:**
  - Deslizamiento: 1.0 tick por lado (2.0 ticks round-turn).
  - Comisión: \$2.50 por lado (\$5.00 round-turn).
  - Costo total por trade:
    - **ES:** Deslizamiento \$25.00 + Comisión \$5.00 = **\$30.00 / trade**.
    - **NQ:** Deslizamiento \$10.00 + Comisión \$5.00 = **\$15.00 / trade**.

---

## 4. Criterios de Aceptación Pre-registrados (A1 – A6)

Una hipótesis se considerará validada únicamente si cumple simultáneamente en la **Partición Final (Holdout)** bajo el **Caso de Costos Base**:
1. **A1 (Significancia Estadística Multitest):** P-valor ajustado mediante el método step-down de Holm-Bonferroni $\le 0.05$ sobre el conjunto de las 8 pruebas primarias.
2. **A2 (Edge Económico Sustancial):** Sharpe Ratio neto anualizado ($\times \sqrt{252}$) $\ge 0.50$.
3. **A3 (Robustez ante Fricciones):** Sharpe Ratio neto en el caso de estrés $> 0.00$.
4. **A4 (Superioridad sobre Azar):** P-valor de la prueba de permutación $\le 0.05$.
5. **A6 (Consistencia Temporal):** Fracción de años con PnL neto positivo $\ge 0.50$ (al menos el 50% de los años con ganancia neta).

---

## 5. Garantía Anti-Lookahead y Bloqueo de Holdout

1. Ninguna señal ni variable explicativa utiliza información igual o posterior a las 15:30 ET del día $t$.
2. El filtro de volatilidad para el día $t$ se computa estrictamente sobre la muestra histórica previa ($0 \dots t-1$).
3. La evaluación de la partición final se ejecuta **exactamente una sola vez** mediante `--stage final`, la cual crea el candado `reports/FINAL_RUN.lock`. Cualquier intento posterior de ejecución sobre la partición final es bloqueado por el código.
