# Informe de Investigación Cuantitativa: Estudio Multiactivo de la Estrategia SMA + MACD + RSI

**Mercados e Instrumentos:**
- Futuros de Índices CME: E-mini S&P 500 (`ES.v.0`) y E-mini Nasdaq-100 (`NQ.v.0`)
- Criptoactivos Perpetuos: Bitcoin (`BTC-USDT`) y Ethereum (`ETH-USDT`)
**Timeframes Evaluados:** Intradía (1h) y Swing (4h)  
**Total de Ensayos / Combinaciones Probadas:** 15,120 simulaciones (1,890 combinaciones $\times$ 8 experimentos)  
**Protocolo:** 60% Entrenamiento, 20% Validación, 20% Test Final (Holdout)  
**Fecha de Publicación:** 2026-10-21  
**Estado / Veredicto:** **NO APROBADA (FAIL)** — Sobreajuste significativo en validación, degradación severa en Test Final, muestreo insuficiente (<100 trades en holdout) y Deflated Sharpe colapsado a cero.

---

## 1. Resumen Ejecutivo y Veredicto Final

En este estudio evaluamos rigurosamente cuántas Medias Móviles Simples (1, 2 o 3 SMAs) y qué periodos optimizan una estrategia de confluencia técnica que integra:
1. **Filtro de Tendencia:** 1 SMA ($\text{Close} > \text{SMA}_{\text{lenta}}$), 2 SMAs ($\text{Close} > \text{SMA}_{\text{lenta}}$ y $\text{rápida} > \text{lenta}$) o 3 SMAs ($\text{rápida} > \text{media} > \text{lenta}$).
2. **Gatillo de Entrada:** Cruce del histograma MACD por cero en dirección de la tendencia.
3. **Filtro de Impulso:** RSI acotado ($40 \le \text{RSI} \le 70$ en Long, $30 \le \text{RSI} \le 60$ en Short).
4. **Gestión de Salidas:** Stop Loss fijo $k \times \text{ATR}(14)$, Take Profit $m \times \text{Riesgo}$, o cruce contrario de SMAs.

### Veredicto Global: **NO APROBADA (FAIL)**
A pesar de que las combinaciones finalistas mostraron ratios de Sharpe aparentes muy elevados durante la fase de Validación ($3.13$ a $7.64$), **la estrategia fracasa de manera concluyente en el Test Final fuera de muestra**:
1. **Colapso Fuera de Muestra:** En 6 de los 8 experimentos (ES 1h, NQ 1h, BTC 1h, ETH 1h, BTC 4h, ETH 4h), los retornos netos en el Test Final fueron negativos, con pérdidas de hasta $-\$15,450$ USD en NQ 1h y Sharpes de hasta $-5.65$ en BTC 1h.
2. **Muestra Estadística Insuficiente (<100 Trades):** La estricta confluencia simultánea de 3 filtros (SMAs + cruce MACD + rango RSI) generó una frecuencia operativa muy baja. En el Test Final, ninguna configuración alcanzó el umbral mínimo pre-registrado de 100 operaciones (oscilando entre 19 y 43 trades).
3. **Penalización por Pruebas Múltiples (Deflated Sharpe Ratio = 0.00%):** Al contabilizar las 15,120 combinaciones probadas en el espacio paramétrico, el *Deflated Sharpe Ratio* (Bailey & López de Prado, 2014) colapsa a prácticamente $0.000$ en todas las configuraciones, demostrando que los picos de rendimiento en validación son producto del sobreajuste estadístico (*p-hacking* aleatorio).
4. **Falta de Robustez Cruzada entre Familias:** Los parámetros óptimos de futuros de índices fallan estrepitosamente al transferirse a criptoactivos (Sharpe $-1.04$ al aplicar la configuración de NQ sobre BTC).
5. **Inferioridad frente a la versión Simple (Solo-SMA):** En criptomonedas, eliminar los filtros de MACD y RSI (*Solo-SMA*) produjo un Sharpe superior ($+0.74$ en BTC 1h y $+5.63$ en ETH 4h), demostrando que los filtros adicionales actúan como destructores de alfa y no como protectores.

---

## 2. Tabla Resumen de Resultados por Activo y Timeframe

| Activo | TF | Configuración Finalista (SMAs / MACD / RSI / ATR) | Trades Test | Retorno Neto Test (USD) | Sharpe Test Final | Deflated Sharpe (DSR) | Sharpe Buy & Hold | Sharpe Solo-SMA | Veredicto |
|---|---|---|---|---|---|---|---|---|---|
| **ES** | **1h** | 3 SMAs (10, 100, 200), MACD (12,26,9), RSI 7, k=1.5, m=1.5 | 31 | -\$1,156 | +0.45 | 0.00% | +0.39 | -0.93 | **FAIL (<100 trades, PnL neg)** |
| **NQ** | **1h** | 3 SMAs (30, 50, 150), MACD (8,17,9), RSI 7, k=1.5, m=2.0 | 43 | -\$15,450 | -0.93 | 0.00% | +0.39 | -1.31 | **FAIL (Pérdidas severas)** |
| **BTC-USDT** | **1h** | 3 SMAs (30, 50, 200), MACD (12,26,9), RSI 7, k=3.0, m=1.5 | 34 | -\$1,987 | -5.65 | 0.00% | +0.13 | +0.74 | **FAIL (Pérdidas, Solo-SMA mejor)** |
| **ETH-USDT** | **1h** | 3 SMAs (10, 100, 200), MACD (16,35,9), RSI 7, k=3.0, m=1.5 | 30 | -\$788 | -1.95 | 0.00% | +0.10 | +1.88 | **FAIL (Pérdidas, Solo-SMA mejor)** |
| **ES** | **4h** | 3 SMAs (30, 100, 200), MACD (16,35,9), RSI 14, k=3.0, m=2.0 | 23 | +\$8,795 | +0.60 | 0.00% | +0.40 | +0.12 | **FAIL (<100 trades, DSR 0%)** |
| **NQ** | **4h** | 3 SMAs (20, 100, 150), MACD (16,35,9), RSI 7, k=1.5, m=1.5 | 31 | +\$64,433 | +5.09 | 0.43% | +0.40 | -0.63 | **FAIL (<100 trades, pico aislado)** |
| **BTC-USDT** | **4h** | 1 SMA (lenta 200), MACD (8,17,9), RSI 21, k=3.0, m=2.0 | 35 | -\$1,236 | -1.41 | 0.00% | +0.03 | +0.73 | **FAIL (Pérdidas netas)** |
| **ETH-USDT** | **4h** | 2 SMAs (21, 200), MACD (16,35,9), RSI 7, k=3.0, m=1.5 | 19 | -\$596 | -0.99 | 0.00% | -0.04 | +5.63 | **FAIL (Pérdidas netas)** |

---

## 3. Inspección de Activos y Fuentes de Datos

### Futuros CME (ES y NQ)
- **Archivos Fuente Reutilizados:** `data/raw/ES.v.0_ohlcv_1m.parquet` y `data/raw/NQ.v.0_ohlcv_1m.parquet`.
- **Rango:** 2017-12-15 a 2026-10-19 (~8.8 años).
- **Manejo de Rollovers:** Símbolos continuos por volumen (`ES.v.0` y `NQ.v.0`) sin ajuste de precio, reflejando contratos transados reales.
- **Sesiones:** Remuestreo intradía respetando la sesión regular de contado (RTH 09:30–16:00 ET). Los fines de semana y pausas diarias de 17:00–18:00 ET se trataron como intervalos no transables naturales.
- **Costos Reales:** \$4.00 USD round-turn de comisión + 1.0 tick de deslizamiento total (\$12.50 en ES, \$5.00 en NQ).

### Criptoactivos (BTC-USDT y ETH-USDT)
- **Fuente de Datos:** Descarga pública desde la API REST de BingX Swap USDT-M (`/openApi/swap/v3/quote/klines`), sin utilizar Binance ni requerir credenciales de trading.
- **Rango Obtenido:** Desde 2021-06-01 hasta la actualidad (21,779 barras en 1h; 9,000 barras en 4h; 1,968 barras en 1D). En 15m la API pública limitó la profundidad histórica a 9,630 barras (~100 días), por lo que se priorizaron 1h y 4h para garantizar validez estadística multi-anual.
- **Costos Reales:** 0.05% de comisión por lado (Taker) + 0.02% (BTC) / 0.03% (ETH) de deslizamiento por lado + tasa de financiación (*funding rate*) acumulada por tiempo de retención.

---

## 4. Análisis de Cuántas SMAs Funcionan Mejor

El Grid Search probó sistemáticamente arquitecturas de 1, 2 y 3 SMAs:
1. **Arquitectura de 3 SMAs (Rápida > Media > Lenta):**
   - Resultó elegida en la mayoría de finalistas de validación debido a que reduce drásticamente las señales falsas en mercados laterales.
   - Sin embargo, esta alta selectividad es un arma de doble filo: redujo la muestra operativa por debajo de 50 trades en la ventana de test, lo que invalida su significancia estadística.
2. **Arquitectura de 1 y 2 SMAs:**
   - En cripto swing (4h), las variantes con 1 o 2 SMAs (ej. SMA 200 pura o cruce 21/200) superaron a la de 3 SMAs porque permiten entrar antes en las tendencias violentas de Bitcoin y Ethereum.
3. **Periodos Óptimos:**
   - La SMA lenta de **200 periodos** dominó consistentemente en casi todos los activos como el filtro de tendencia macro más estable.
   - Las SMAs rápidas óptimas se ubicaron entre **10 y 30 periodos**, dependiendo de la volatilidad del activo.

---

## 5. Análisis de Mapas de Calor: ¿Meseta Estable o Picos Aislados?

Se generaron mapas de calor paramétricos graficando la SMA Rápida frente a la SMA Lenta:
- En **ES y NQ (1h)** ([`heatmap_stability_ES_1h.png`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/figures/heatmap_stability_ES_1h.png) y [`heatmap_stability_NQ_1h.png`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/figures/heatmap_stability_NQ_1h.png)), los rendimientos forman **islas o picos aislados**: cambiar la SMA rápida de 10 a 20 con la misma SMA lenta de 200 causa que el Sharpe caiga bruscamente de positivo a fuertemente negativo.
- Esta falta de continuidad espacial es la firma clásica del **sobreajuste paramétrico (*curve-fitting*)**. En un sistema verdaderamente robusto, los parámetros adyacentes deben formar una meseta suave con rendimientos similares.

---

## 6. Pruebas de Robustez Cruzada entre Activos

Se transfirieron los parámetros de la mejor configuración de un activo a otro:
- **NQ $\to$ ES (1h):** Sharpe $= +1.84$, PnL $= +\$63,834$. Existe correlación estructural positiva dentro de la familia de índices de renta variable estadounidense.
- **ES $\to$ NQ (1h):** Sharpe $= +0.58$, PnL $= -\$3,732$ (resultado discordante por mayor volatilidad intrínseca de NQ).
- **BTC $\to$ ETH (1h):** Sharpe $= +0.18$, PnL $= +\$533$ (rendimiento marginal casi nulo).
- **ETH $\to$ BTC (1h):** Sharpe $= -1.05$, PnL $= -\$1,934$ (fracaso total al transferir la configuración de Ethereum a Bitcoin).
- **NQ $\to$ BTC (1h - Cross-Family):** Sharpe $= -1.04$, PnL $= -\$2,776$. **Fracaso absoluto entre familias.** Los parámetros que capturan tendencias en índices bursátiles tradicionales destruyen capital al aplicarse a criptomonedas 24/7.

---

## 7. Comparación con Líneas Base: Buy & Hold y Solo-SMA

1. **Frente a Buy & Hold:**
   - En ES y NQ, el Buy & Hold pasivo generó un Sharpe estable de $+0.39$ a $+0.40$ sin incurrir en comisiones repetitivas ni deslizamientos constantes. La estrategia activa generó drawdowns y costos que superaron el beneficio del timing.
2. **Frente a Solo-SMA (sin MACD ni RSI):**
   - El hallazgo más revelador del estudio ocurrió en los activos cripto: la estrategia de **Solo-SMA** (seguir la tendencia pura de la media móvil) superó ampliamente a la estrategia de confluencia completa.
   - En ETH 4h, Solo-SMA obtuvo un Sharpe de **$+5.63$** frente a **$-0.99$** de la estrategia con MACD y RSI.
   - *Razón técnica:* En criptoactivos, los movimientos tendenciales son parabólicos. Exigir que el RSI esté en rango ($40-70$) y esperar un cruce del histograma MACD genera señales tardías en zonas donde el movimiento principal ya ocurrió, comprando en el agotamiento del impulso y saliendo en el retroceso.

---

## 8. Diagnóstico de Pruebas Múltiples y Deflated Sharpe Ratio (DSR)

Dado que se evaluaron $1,890$ combinaciones por activo y timeframe ($15,120$ ensayos acumulados), el riesgo de seleccionar una regla por simple azar es casi del 100%.
- El **Deflated Sharpe Ratio (DSR)** penaliza la métrica en función de $\sqrt{2 \ln(M)}$.
- Para un espacio de 15,120 pruebas, el Sharpe mínimo requerido para ser estadísticamente significativo al 95% supera un Sharpe anualizado de **$+2.8$**.
- Con la excepción aparente de NQ 4h (que tuvo apenas 31 trades y DSR de $0.43\%$), todas las demás configuraciones arrojaron un DSR inferior al **$0.01\%$**.
- **Conclusión estadística:** Ninguna de las configuraciones probadas posee significancia estadística comprobable una vez ajustada por la multiplicidad de pruebas.

---

## 9. Pruebas en Temporalidades Cortas (15 minutos y 5 minutos)

Para responder a la pregunta de si la estrategia mejora o consigue mayor significancia en horizontes intradiarios más veloces, se remuestrearon y descargaron datos en **15m** y **5m** para los 4 activos (ES, NQ, BTC-USDT, ETH-USDT), reejecutando la rejilla completa de **1,890 combinaciones** por activo y temporalidad (otras 15,120 simulaciones adicionales).

### Tabla de Resultados en Temporalidades Cortas (Test Final Fuera de Muestra)

| Activo | TF | Configuración Óptima (SMAs / MACD / RSI / ATR) | Trades Test | Retorno Neto Test (USD) | Sharpe Test Final | Win Rate | Profit Factor | Deflated Sharpe (DSR) | Sharpe Buy & Hold | Sharpe Solo-SMA |
|---|---|---|---|---|---|---|---|---|---|---|
| **ES** | **15m** | 3 SMAs (10, 50, 100), MACD (8,17,9), RSI 21, k=3.0, m=2.0 | 130 | -\$67,969 | -2.45 | 30.77% | 0.68 | 0.00% | +0.20 | -0.58 |
| **NQ** | **15m** | 2 SMAs (21, 100), MACD (16,35,9), RSI 14, k=3.0, m=2.0 | 149 | -\$109,690 | -1.83 | 28.86% | 0.76 | 0.00% | +0.20 | -0.54 |
| **BTC-USDT** | **15m** | 3 SMAs (10, 100, 150), MACD (12,26,9), RSI 7, k=3.0, m=2.0 | 14 | +\$45.85 | +0.71 | 50.00% | 1.08 | 0.01% | +0.02 | -5.26 |
| **ETH-USDT** | **15m** | 2 SMAs (30, 100), MACD (8,17,9), RSI 21, k=3.0, m=2.0 | 36 | -\$174.97 | -0.74 | 33.33% | 0.91 | 0.00% | -0.31 | -3.68 |
| **ES** | **5m** | 3 SMAs (10, 50, 100), MACD (12,26,9), RSI 7, k=3.0, m=2.0 | 202 | -\$74,982 | -2.91 | 29.70% | 0.64 | 0.00% | +0.12 | -1.16 |
| **NQ** | **5m** | 3 SMAs (30, 50, 100), MACD (8,17,9), RSI 14, k=3.0, m=1.5 | 495 | -\$11,944 | -0.13 | 41.41% | 0.99 | 0.00% | +0.12 | -0.34 |
| **BTC-USDT** | **5m** | 3 SMAs (30, 100, 150), MACD (8,17,9), RSI 7, k=3.0, m=2.0 | 21 | -\$752.04 | -11.16 | 19.05% | 0.28 | 0.00% | +0.15 | -11.32 |
| **ETH-USDT** | **5m** | 3 SMAs (30, 100, 200), MACD (12,26,9), RSI 21, k=3.0, m=2.0 | 27 | -\$672.31 | -4.85 | 25.93% | 0.57 | 0.00% | -0.03 | -5.82 |

### Hallazgos Clave en 15m y 5m:
1. **La Fricción y el Ruido Intradía Destruyen el Capital:**
   - En futuros de índices (ES y NQ), el número de operaciones sube a niveles con alta significancia muestral (entre 130 y 495 trades en holdout). Sin embargo, las pérdidas netas son masivas: $-\$109,690$ USD en NQ 15m y $-\$74,982$ USD en ES 5m.
   - El ruido aleatorio en velas cortas genera continuos falsos quiebres de medias y whipsaws de MACD. Al sumar comisiones y deslizamiento por cada operación, la curva de balance tiene pendiente sistemáticamente negativa.
2. **Cripto en Temporalidades Rápidas:**
   - En BTC y ETH de 5m, los resultados son catastróficos: Sharpes de $-11.16$ y $-4.85$, con tasas de acierto de apenas 19% a 26%.
   - En BTC 15m se obtuvo una ganancia testimonial de $+\$45.85$ USDT, pero con solo 14 trades en la muestra final, lo cual no posee ninguna significancia estadística (DSR de $0.01\%$).
3. **Tendencia por Horizonte Temporal:**
   - La regla general observada en los 4 activos es: **a menor temporalidad ($4\text{h} \to 1\text{h} \to 15\text{m} \to 5\text{m}$), mayor es el impacto de la fricción y peor es el desempeño neto**.

---

## 10. Conclusión Final

La estrategia de confluencia **SMA + MACD + RSI no es apta para implementación real en ninguna de las temporalidades evaluadas (4h, 1h, 15m o 5m)**. 

- En temporalidades altas (4h y 1h), la confluencia es tan restrictiva que genera muy pocas operaciones (<45 trades), sufriendo de sobreajuste masivo y colapso fuera de muestra.
- En temporalidades bajas (15m y 5m), el volumen de operaciones aumenta, pero los costos de transacción y el ruido aleatorio del mercado destruyen el capital de forma sistemática y acelerada.

---
*Archivos generados en el estudio:*
- *Tabla Resumen 1h y 4h:* [`reports/tables/summary_multi_asset_results.csv`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/tables/summary_multi_asset_results.csv)
- *Tabla Resumen 15m y 5m:* [`reports/tables/summary_short_timeframes.csv`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/tables/summary_short_timeframes.csv)
- *Resultados JSON 15m y 5m:* [`reports/results_short_timeframes.json`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/results_short_timeframes.json)
- *Mapas de Calor de Estabilidad:* Directorio [`reports/figures/`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/figures)
