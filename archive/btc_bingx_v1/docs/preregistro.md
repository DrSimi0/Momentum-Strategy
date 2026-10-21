# Protocolo de Pre-registro Metodológico Congelado (v3.0)
*Estrategia de Confluencia en 3 Capas — BTC-USDT (BingX, 15m)*  
*Fecha de Congelamiento:* 2026-10-20 22:00:00 UTC  
*Dataset Inmutable:* `data/historical/bingx_btc_usdt_15m.parquet`  
*Hash SHA-256:* `ca781c92468bf0092b79263b2af0d7318fa09dc7bc549517ecb243e253a5320e`  

---

## 1. Hipótesis Científica y Regla de Decisión

- **Pregunta:** ¿El sistema de confluencia jerárquica en tres capas (donde el filtro macro previene trampas de mercado y la Capa 2 formaliza el setup con SL/TP/horizonte) genera un Sharpe Ratio neto superior y menor drawdown que la Capa 2 aislada y que los benchmarks convencionales (Buy & Hold y entradas aleatorias)?
- **Hipótesis Nula ($H_0$):** La confluencia macro-técnica no añade alfa estadísticamente significativo tras descontar comisiones taker del 0.05%, deslizamiento del 0.02% por lado y tasa de financiación proporcional.

---

## 2. Partición Temporal Estricta (Total 9,599 barras de 15m)

1. **Desarrollo y Calibración (IS):** Barras 0 a 5,500 (~2026-07-13 04:00 a 2026-09-08 12:00 UTC).
2. **Validación / OOS Intermedio:** Barras 5,501 a 7,500 (~2026-09-08 12:15 a 2026-09-29 07:00 UTC).
3. **Holdout Final Intocable:** Barras 7,501 a 9,598 (~2026-09-29 07:15 a 2026-10-20 21:00 UTC). Evaluado **una sola vez**.

---

## 3. Modelo de Costos de Ejecución (Obligatorio en Toda Evaluación)

- **Comisión:** $0.05\%$ por lado (taker oficial BingX swap USDT-M).
- **Deslizamiento (*Slippage*):** $0.02\%$ por lado (ejecución al precio de apertura de la siguiente vela $t+1$).
- **Financiación (*Funding*):** $0.01\%$ prorrateado cada 8 horas (32 barras de 15m).
- **Costo Round-Trip Base:** $0.14\% + \text{funding}$.
- **Estrés de Costos x2:** $0.28\% + \text{funding}$.

---

## 4. Matriz de Ablación Pre-registrada

- **Variante V1:** Capa 2 aislada (Estructura técnica pura: fractales, BBWP, MACD z-score, SL/TP/horizonte).
- **Variante V2:** Confluencia Capa 1 + Capa 2 (Filtro macro anti-trampa + abstención de eventos de 3 estrellas).
- **Benchmark 1:** Buy & Hold sobre el mismo periodo a 1x.
- **Benchmark 2:** 500 ejecuciones Monte Carlo de entradas aleatorias pareadas en número, duración media y apalancamiento.

---

## 5. Umbrales de Aceptación Cuantitativos

- **Expectativa neta por operación:** $> 0.00$ USDT tras costos completos.
- **Sharpe Ratio Anualizado (15m, $N=35,040$):** $\ge 1.00$.
- **Deflated Sharpe Ratio (DSR):** $\ge 0.95$ (corrigiendo por múltiples pruebas).
- **Máximo Drawdown:** $\le 15.0\%$ a 1x.
- **Estrés de Costos x2:** Expectativa neta permanece positiva.
- **Concentración:** El top 5% de operaciones no explica más del 60% del beneficio neto.
- **Ablación:** V2 debe exhibir menor drawdown y mejor Sharpe neto que V1 (demostración de la utilidad del filtro anti-trampa).
