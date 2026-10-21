# Protocolo de Pre-registro Metodológico v2.0
*Sistema de Investigación Cuantitativa y Señales BTC-USDT (BingX, 15m)*

---

## 1. Pregunta Científica e Hipótesis Nula

- **Pregunta:** ¿Puede un sistema multiagente que combina reglas cuantitativas deterministas, contexto macro/sentimiento exógeno e interpretación visual de gráficos generar señales con expectativa matemática neta positiva en BTC-USDT (15m, BingX) tras comisiones completas de taker, slippage y funding?
- **Hipótesis Nula ($H_0$):** La expectativa neta y el Sharpe Ratio del sistema multiagente no superan a una estrategia de referencias simples (Buy & Hold, cruce de medias EMA 21/50, o entradas aleatorias con idéntica duración y distribución de exposición). Ningún componente añade alfa estadísticamente significativo tras costos.

---

## 2. Convenciones Matemáticas y Anualización (Mercado Cripto 24/7)

El mercado de perpetuos de BingX opera 24 horas al día, 365 días al año de forma continua:
- Horas por año: $365 \times 24 = 8,760$ horas.
- Barras de 15 minutos por año:
  $$N_{\text{periodos}} = 8,760 \times 4 = 35,040 \text{ barras/año}$$
- **Factor de escala anual del Sharpe Ratio:**
  $$\text{Sharpe}_{\text{anual}} = \frac{\mu_{\Delta t} - r_f}{\sigma_{\Delta t}} \times \sqrt{35,040} \approx \text{Sharpe}_{15m} \times 187.1897$$
  *(donde $\mu_{\Delta t}$ y $\sigma_{\Delta t}$ son la media y desviación estándar del retorno neto por barra de 15 minutos, y la tasa libre de riesgo $r_f$ se asume 0 para horizontes intradiarios).*

- **Expectativa neta por operación ($E$):**
  $$E = \frac{1}{N} \sum_{i=1}^{N} \text{PnL}_{net, i}$$
  Expresada en USDT y en unidades de riesgo inicial $R = |\text{Precio Entrada} - \text{Stop Loss}|$.

---

## 3. Particiones Temporales y Protección Anti-Fuga

Para garantizar cero contaminación y validez estadística:
1. **Desarrollo y Ajuste (IS):** `2022-01-01` a `2024-06-30` (~87,600 barras). Usada para formular y calibrar reglas.
2. **Validación Cruzada / OOS Intermedio:** `2024-07-01` a `2025-06-30` (~35,040 barras). Evaluación walk-forward con purga de operaciones solapadas (*purged & embargoed*).
3. **Holdout Final Intocable:** `2025-07-01` a la fecha actual (`2026-10-20`). Bloqueado mediante hash SHA-256 en `reports/.holdout_used`. Prohibido correr backtests sobre este tramo hasta que las reglas y umbrales estén inmutables.

---

## 4. Matriz de Experimentos Diseñados

| Experimento | Objetivo Científico | Comparativa |
|---|---|---|
| **Experimento A** | Alfa vs. Benchmarks Tradicionales | Estrategia propuesta vs. Buy & Hold, cruce EMA 21/50 y 1,000 runs de Monte Carlo con entradas aleatorias pareadas en exposición. |
| **Experimento B** | Valor añadido de la Visión Computacional (LLM) | Reglas cuantitativas Clase A solas vs. Reglas Clase A + confirmación del Agente Visual (inspección de gráficos renderizados). Se contrasta además contra agente visual ciego (gráficos mezclados/placebo). |
| **Experimento C** | Proceso Multiagente vs. Selección Simple | Comparar la tasa de degradación OOS entre reglas seleccionadas por optimización clásica de parámetros vs. reglas filtradas por el tribunal multiagente. |
| **Experimento D (Ablación)** | Descomposición de la jerarquía de capas | Evaluar rendimiento bajo 4 configuraciones aisladas: <br>1. Solo técnico Clase A <br>2. Técnico + Filtro de Eventos Macro (Clase B-2) <br>3. Técnico + Filtro Sentimiento/Funding (Clase B-1 / B-5) <br>4. Técnico + Filtros Contextuales completos. |

---

## 5. Medición de Robustez Estadística

1. **Deflated Sharpe Ratio (DSR):**
   Calcula la probabilidad de que el Sharpe observado sea fruto del azar dada la varianza de los ensayos y el número total de configuraciones probadas ($K$):
   $$\text{DSR} = \Phi \left( \frac{(\widehat{\text{SR}} - \text{SR}^*) \sqrt{T-1}}{\sqrt{1 - \widehat{\gamma}_3 \widehat{\text{SR}} + \frac{\widehat{\gamma}_4 - 1}{4} \widehat{\text{SR}}^2}} \right)$$
   donde $\text{SR}^* = \sqrt{2 \ln K} \dots$
2. **Bootstrap por Bloques Circulares:**
   1,000 remuestreos con bloques de longitud equivalente a 5 días bursátiles (480 barras) para preservar la autocorrelación serial y heterocedasticidad.
3. **Prueba de Estrés de Costos x2:**
   Multiplicar comisiones y deslizamiento por 2.0 ($0.28\%$ round-trip) para verificar resistencia a picos de volatilidad y ensanchamiento de spreads.
