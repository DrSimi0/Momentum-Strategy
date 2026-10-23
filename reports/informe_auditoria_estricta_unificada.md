# INFORME DE AUDITORÍA CUANTITATIVA ESTRICTA: ESTRATEGIA UNIFICADA

**Fecha:** 23 de Octubre de 2026  
**Auditoría y Análisis:** Antigravity Quant Research  
**Estatus Metodológico Oficial:** **EXPLORATORIA (SIN HOLDOUT VIRGEN)**  
**Principio de Honestidad Intelectual:** La Estrategia Cuantitativa Unificada fue diseñada e iterada utilizando la totalidad de la información disponible de 2010 a 2026. En consecuencia, **queda formalmente desprovista de cualquier calificación de "validada" o "ganadora"**. Este informe audita la realidad matemática cruda del sistema, sin filtros optimistas ni artefactos de cálculo.

---

## 1. ACLARACIÓN DE ANOMALÍAS METODOLÓGICAS PREVIAS

Antes de exponer las métricas corregidas, se auditan y explican formalmente las tres discrepancias detectadas:

### 1.1 El Artefacto del Sharpe de 2.45 con Drawdown de 108% en NQ 1h
- **Causa Matemática:** En las versiones preliminares, el Sharpe ratio se calculaba tomando la media y desviación estándar de los retornos **por trade** y multiplicándolas por $\sqrt{252}$. Esta fórmula asume falsamente que la estrategia ejecuta 252 operaciones al año (1 por día). En la realidad, la estrategia en 1h solo opera ~15 veces al año. Esta distorsión multiplicó artificialmente el Sharpe por casi 4 veces.
- **Inconsistencia de Quiebra:** Al mismo tiempo, el Max Drawdown en dólares fue de **\$53,954.51 USD**. Al contrastarlo contra un capital base nominal de \$50,000 USD, arrojaba una pérdida de **107.9%**, lo que representaba la **quiebra técnica total de la cuenta** en medio de un Sharpe supuestamente "estelar".
- **Corrección Aplicada:** El Sharpe se calcula ahora estrictamente sobre la **curva de equity diaria continua** (los 4,115 días de mercado reales entre 2010 y 2026), anualizado formalmente con $\times \sqrt{252}$ sobre los retornos diarios de la cuenta.

### 1.2 Por Qué NQ 5m Figuraba como 0.84 y 0.14
- **0.84:** Corresponde a la simulación *swing pura* en 5 minutos (con pernocta nocturna y salidas exclusivas por cruce de medias).
- **0.14:** Corresponde a la variante *intradiaria optimizada* (`3_Intraday_Medias_80_y_Volatilidad`), que aplica liquidación forzada diaria MOC a las 15:50 ET y filtro de volatilidad ATR. El cierre diario evita gaps desastrosos pero corta el recorrido de los mejores impulsos, reduciendo drásticamente la ganancia media por día.

### 1.3 Por Qué ES y NQ Registraron Exactamente 829 Trades en 15m
- **Verificación Empírica:** Se auditó la matriz de ejecuciones para descartar duplicación de código o fuga cruzada de datos. Se comprobó que se trata de una **coincidencia numérica**:
  - Solo 6 de las 829 fechas de entrada coinciden en el mismo minuto entre ambos índices (0.72% de solapamiento temporal).
  - Los precios, duraciones y PnL son totalmente independientes: el primer trade de ES fue el 2010-07-09 ganando +\$1,013 USD; el primer trade de NQ fue el 2010-06-22 perdiendo -\$493 USD. No existe contaminación de datos.

---

## 2. RE-CÁLCULO RIGUROSO SOBRE LA CURVA DE EQUITY DIARIA CONTINUA

> **Metodología de Cálculo:**  
> - Capital base fijo: **\$50,000 USD** por contrato E-mini.  
> - Periodo: **16.36 años continuos** (2010 a 2026, 4,115 sesiones diarias).  
> - Retorno diario: $r_d = (\text{Equity}_d - \text{Equity}_{d-1}) / \text{Equity}_{d-1}$.  
> - $\text{Sharpe Diario} = \frac{\bar{r}_d}{\sigma_d} \times \sqrt{252}$.  
> - $\text{CAGR} = (\text{Equity}_{final} / 50000)^{1 / 16.36} - 1$.  
> - $\text{Calmar} = \text{CAGR} / \text{Max DD \%}$.

### Tabla 1: Métricas de Equity Diaria Corregidas

| Activo | TF | Trades | Win Rate % | PnL Neto Total ($) | Retorno Total (%) | CAGR (%) | Sharpe Diario | Max DD ($) | Max DD (%) | Calmar Ratio | DSR (M=338) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **NQ** | **1h** | 248 | 41.53% | +$174,665.62 | +349.33% | **+9.42%** | **0.63** | $53,954.51 | **35.82%** | **0.26** | **13.27%** |
| **NQ** | **4h** | 242 | 39.26% | +$182,218.20 | +364.44% | **+7.92%** | **0.56** | $47,418.68 | **29.77%** | **0.27** | **12.36%** |
| **ES** | **1h** | 269 | 40.15% | +$111,341.96 | +222.68% | **+7.27%** | **0.55** | $22,976.05 | **22.65%** | **0.32** | **7.49%** |
| **ES** | **4h** | 257 | 35.80% | +$50,830.65 | +101.66% | **+3.54%** | **0.27** | $43,409.07 | **52.51%** | **0.07** | **0.68%** |

### Diagnóstico de la Realidad Matemática:
1. El verdadero Sharpe ratio de la estrategia sobre la curva diaria no es 2.45, sino **0.63 en NQ 1h** y **0.55 en ES 1h**.
2. El retorno anual compuesto real (**CAGR**) ronda entre **+7.2% y +9.4% anual**, con drawdowns monetarios de \$23k a \$54k USD.
3. El Calmar Ratio se sitúa en un modesto **0.26 – 0.32** (gana menos de un tercio de su drawdown máximo al año).
4. El **Deflated Sharpe Ratio (DSR)** penalizado por las 338 pruebas históricas acumuladas es de apenas **13.27% en NQ** y **7.49% en ES**. Falla holgadamente el umbral mínimo del 95% para descartar la minería de datos espuria.

---

## 3. VIABILIDAD EN PROP FIRMS Y CONTRATOS MICRO (MES / MNQ)

Las Prop Firms imponen límites estrictos de Max Trailing Drawdown:
- Cuenta de \$50,000 USD: Drawdown máximo permitido de **\$2,000 USD**.
- Cuenta de \$100,000 USD: Drawdown máximo permitido de **\$3,000 USD**.

### Tabla 2: Análisis de Supervivencia en Prop Firms

| Activo / TF | Contrato Simulado | Max Drawdown ($) | Max Drawdown (%) | PnL Neto ($) | Cabe en Prop Firm $50k (Límite $2k)? | Cabe en Prop Firm $100k (Límite $3k)? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **NQ 1h** | 1 E-mini (NQ) | $53,954.51 | 35.82% | +$174,665 | **NO (Quiebra inmediata)** | **NO (Quiebra inmediata)** |
| **NQ 1h** | 1 Micro (MNQ - 1/10) | $5,395.45 | 8.98% | +$17,466 | **NO (Excede $2,000)** | **NO (Excede $3,000)** |
| **NQ 1h** | Riesgo Fijo 0.5% | $13,121.21 | 20.80% | +$42,850 | **NO (Excede $2,000)** | **NO (Excede $3,000)** |
| **ES 1h** | 1 E-mini (ES) | $22,976.05 | 22.65% | +$111,341 | **NO (Quiebra inmediata)** | **NO (Quiebra inmediata)** |
| **ES 1h** | 1 Micro (MES - 1/10) | $2,297.61 | 3.78% | +$11,134 | **NO (Excede $2,000)** | **SÍ (Margen de solo $700)** |
| **ES 1h** | Riesgo Fijo 0.5% | $11,776.64 | 18.20% | +$28,400 | **NO (Excede $2,000)** | **NO (Excede $3,000)** |

### Veredicto Explícito sobre Prop Firms:
> [!CAUTION]
> **LA ESTRATEGIA NO ES APTA PARA PROP FIRMS.**  
> Ni siquiera operando el tamaño más pequeño posible (1 micro-contrato MNQ), el sistema cabe dentro de los límites de drawdown de cuentas fondeadas de \$50k o \$100k. Un drawdown histórico de \$5,395 USD en MNQ y \$2,297 USD en MES descalifica cualquier cuenta con límites de \$2,000 o \$3,000 USD. Ajustar el tamaño con riesgo fijo al 0.5% tampoco soluciona el problema, acumulando \$13,121 USD de drawdown durante las rachas de pérdidas prolongadas.

---

## 4. PRUEBA ÁCIDA: TEST DE PERMUTACIÓN MONTE CARLO (10,000 ITERACIONES)

Para determinar si la estrategia posee una ventaja predictiva real o si simplemente se benefició del mercado alcista general, se ejecutó un test de permutación con **10,000 series de entradas aleatorias** con el mismo número de trades y duración media en el mismo periodo histórico (2010–2026).

### Tabla 3: Resultados del Test de Permutación vs Señales Aleatorias

| Activo / TF | PnL Real Estrategia ($) | PnL Medio Aleatorio ($) | Desv. Est. Aleatorio ($) | Z-Score | P-Valor Empírico | Percentil Real (%) | ¿Bate al Azar (p < 0.05)? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **NQ 1h** | **+$174,665.62** | +$164,182.43 | $104,351.06 | +0.10 | **p = 0.4586** | 54.14% | **NO (Idéntico al azar)** |
| **ES 1h** | **+$111,341.96** | +$111,315.16 | $64,749.57 | +0.00 | **p = 0.5062** | 49.38% | **NO (Idéntico al azar)** |
| **NQ 4h** | **+$182,218.20** | +$209,776.29 | $117,223.76 | -0.24 | **p = 0.5951** | 40.49% | **NO (Inferior al azar)** |
| **ES 4h** | **+$50,830.65** | +$139,874.35 | $71,152.10 | -1.25 | **p = 0.8962** | 10.38% | **NO (Muy inferior al azar)** |

### Demostración Matemática Definitiva:
1. En **NQ 1h**, comprar en fechas completamente aleatorias generó un PnL medio de **+\$164,182 USD**, prácticamente idéntico al de la estrategia (+\$174,665 USD). El p-valor empírico de **0.4586** indica que casi el **46% de las simulaciones tirando una moneda superaron a la estrategia**.
2. En **ES 1h**, el PnL aleatorio medio (+\$111,315 USD) es exactamente el mismo que el de la estrategia (+\$111,341 USD, $p = 0.5062$).
3. **Conclusión Científica:** El PnL positivo de la Estrategia Unificada **proviene al 100% del drift secular alcista de la economía estadounidense** durante 2010–2026. Los indicadores técnicos (EMA, MACD, RSI, Velas) **no aportan ningún alfa predictivo frente a entradas aleatorias**.

---

## 5. COMPARACIÓN CONTRA BUY & HOLD AJUSTADO POR EXPOSICIÓN

- **Tiempo en Mercado (Market Exposure):** La estrategia en NQ 1h solo mantiene posición abierta el **30.69% del tiempo**.
- **Buy & Hold Total (NQ 2010–2026):** **+1,514.22%**.
- **Buy & Hold Ponderado por Exposición (30.69%):** **+464.64%**.
- **Retorno Real de la Estrategia:** **+349.33%**.
- **Diferencia:** La estrategia generó **115 puntos porcentuales MENOS** que la compra pasiva durante el mismo tiempo de exposición, debido a las salidas prematuras y a los costos transaccionales.

---

## 6. MAPA DE SENSIBILIDAD DE VECINOS (NQ 1h, MATRIZ 3x3x3)

Se evaluaron 27 configuraciones alrededor de la base `(EMA 30, EMA 200, Stop 3.0 ATR)`:

| EMA Rápida | EMA Lenta | Stop ATR | Trades | Win Rate % | PnL Neto ($) | Sharpe Diario | CAGR % | Max DD ($) | Calmar |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 20 | 150 | 3.0 | 245 | 42.04% | +$248,779 | 0.79 | 11.31% | $28,700 | 0.66 |
| 20 | 200 | 3.0 | 255 | 41.96% | +$204,052 | 0.71 | 10.23% | $38,183 | 0.45 |
| 20 | 250 | 3.0 | 256 | 42.19% | +$213,037 | 0.70 | 10.46% | $45,353 | 0.35 |
| 30 | 150 | 3.0 | 244 | 40.98% | +$164,820 | 0.63 | 9.13% | $38,183 | 0.38 |
| **30** | **200** | **3.0 (BASE)** | **248** | **41.53%** | **+$174,666** | **0.63** | **9.42%** | **$53,954** | **0.26** |
| 30 | 250 | 3.0 | 251 | 41.83% | +$162,036 | 0.63 | 9.04% | $45,353 | 0.31 |
| 40 | 150 | 3.0 | 242 | 40.91% | +$139,835 | 0.58 | 8.32% | $53,954 | 0.26 |
| 40 | 200 | 3.0 | 243 | 41.15% | +$148,484 | 0.58 | 8.61% | $53,954 | 0.24 |
| 40 | 250 | 3.0 | 252 | 40.87% | +$140,835 | 0.56 | 8.36% | $49,541 | 0.25 |

### Diagnóstico de Sensibilidad:
- La región paramétrica se comporta como una **meseta estable y no como un pico aislado**: los Sharpes oscilan gradualmente entre 0.56 y 0.79 en todas las variaciones.
- Sin embargo, **toda la meseta comparte el mismo problema de fondo**: es una meseta de captura de beta de mercado con Sharpe diario moderado (~0.60–0.70) y drawdowns severos (\$28k a \$58k USD).

---

## 7. TEST DE CONCENTRACIÓN (ELIMINANDO LOS TOP 5 TRADES)

### Tabla 4: Fragilidad ante Trades Atípicos

| Activo / TF | PnL Total Original ($) | Ganancia de solo 5 Trades ($) | % PnL en Top 5 | PnL SIN Top 5 Trades ($) | Sharpe Original | Sharpe SIN Top 5 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **NQ 1h** | +$174,665.62 | **$88,389.84** | **50.61%** | +$86,275.78 | 0.63 | **0.45** |
| **NQ 4h** | +$182,218.20 | **$107,910.82** | **59.22%** | +$74,307.38 | 0.56 | **0.37** |
| **ES 1h** | +$111,341.96 | **$53,035.06** | **47.63%** | +$58,306.90 | 0.55 | **0.39** |
| **ES 4h** | +$50,830.65 | **$56,901.60** | **111.94%** | **-$6,070.95** | 0.27 | **0.08** |

### Hallazgo Crítico:
- En NQ 1h, **más de la mitad (50.6%) de todo el beneficio de 16 años dependió de únicamente 5 trades**.
- En ES 4h, la dependencia es absoluta: los 5 mejores trades aportaron el **111.9%** del beneficio total. Si el trader se perdió esos 5 trades, **el sistema perdió dinero (-\$6,070 USD)**.

---

## 8. DESGLOSE DE PnL AÑO POR AÑO (NQ 1h, 2010 A 2026)

| Año | Trades | Win Rate % | PnL Neto ($ USD) | Retorno Anual % | Equity Fin de Año ($) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **2010** | 5 | 60.0% | +$3,477.88 | +6.96% | $53,477.88 |
| **2011** | 16 | 31.25% | **-$3,411.59** | -6.38% | $50,066.29 |
| **2012** | 16 | 43.75% | +$1,812.47 | +3.62% | $51,878.77 |
| **2013** | 18 | 55.56% | +$9,671.59 | +18.64% | $61,550.35 |
| **2014** | 18 | 27.78% | **-$3,395.02** | -5.52% | $58,155.33 |
| **2015** | 12 | 25.00% | **-$786.27** | -1.35% | $57,369.06 |
| **2016** | 15 | 40.00% | +$3,267.12 | +5.69% | $60,636.19 |
| **2017** | 21 | 42.86% | +$5,376.88 | +8.87% | $66,013.07 |
| **2018** | 10 | 60.00% | +$15,384.61 | +23.31% | $81,397.68 |
| **2019** | 19 | 42.11% | +$11,962.01 | +14.70% | $93,359.69 |
| **2020** | 24 | 45.83% | +$41,042.25 | +43.96% | $134,401.94 |
| **2021** | 22 | 31.82% | **-$10,282.97** | -7.65% | $124,118.97 |
| **2022** | 3 | 0.00% | **-$13,843.45** | -11.15% | $110,275.52 |
| **2023** | 13 | 30.77% | **-$1,452.73** | -1.32% | $108,822.79 |
| **2024** | 14 | 57.14% | +$49,509.41 | +45.50% | $158,332.20 |
| **2025** | 14 | 50.00% | +$40,053.15 | +25.30% | $198,385.35 |
| **2026** | 8 | 50.00% | +$26,280.27 | +13.25% | $224,665.62 |

> [!WARNING]
> **Racha de Tres Años Consecutivos en Pérdidas (2021–2023):**  
> Durante 3 años enteros el sistema perdió capital de forma ininterrumpida (-\$10k en 2021, -\$13.8k en 2022 con 0% de aciertos, y -\$1.4k en 2023), acumulando un drawdown de más de **-\$25,500 USD**. Casi el 70% de todo el beneficio del sistema se concentró exclusivamente en los rallies de 2020 y 2024–2025.

---

## 9. PROPUESTA DE HOLDOUT VIRGEN Y PROYECCIÓN DE FORWARD TEST

### 9.1 Costo Oficial en Databento API (`metadata.get_cost`) — SIN DESCARGAR
Se consultó el endpoint de costos de Databento para el periodo completo 2010–2026 en `ohlcv-1m`:
- **YM.c.0 (Dow Jones E-mini):** \$19.67 USD
- **RTY.c.0 (Russell 2000 E-mini):** \$10.90 USD
- **GC.c.0 (Oro - Gold):** \$0.92 USD
- **CL.c.0 (Crudo - Crude Oil):** \$19.82 USD
- **Costo Total Combinado:** **\$51.31 USD** (ningún dato fue descargado).

### 9.2 Proyección de Tiempo para $N \ge 100$ Trades en Forward Test
Dado el ratio medio histórico de operaciones:
- En 1h: 248 trades en 16.36 años = **15.16 trades/año**.  
  $\text{Años requeridos} = 100 / 15.16 = \mathbf{6.6\text{ años}}$.
- En 4h: 242 trades en 16.36 años = **14.79 trades/año**.  
  $\text{Años requeridos} = 100 / 14.79 = \mathbf{6.76\text{ años}}$.
- **Conclusión:** Para validar esta estrategia fuera de muestra exclusivamente con forward test diario en vivo hasta alcanzar significancia estadística ($N \ge 100$), se requerirían **más de 6 años y medio de monitoreo**.

---

## 10. ESTADO ACTUAL DEL FORWARD TEST EN VIVO

El generador causal inmutable [`scripts/forward_test_signal_generator.py`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/scripts/forward_test_signal_generator.py) se encuentra activo.
La última lectura registrada en la bitácora inmutable (`reports/forward_test/forward_test_signals.log`) muestra:
- `ES 4h`: **HOLD** (Precio: 7744.5)
- `ES 1h`: **HOLD** (Precio: 7735.0, señal aislada `SELL_ENGULFING` descartada por la regla Long-Only)
- `NQ 4h`: **HOLD** (Precio: 29753.0)
- `NQ 1h`: **HOLD** (Precio: 29721.75, señal aislada `SELL_ENGULFING` descartada por la regla Long-Only)
- **Estado de la Estrategia Unificada:** En liquidez total (**HOLD** en todos los activos).

---

## 11. VEREDICTO FINAL DE AUDITORÍA

| Criterio Evaluado | Umbral de Aprobación | Resultado Real | Veredicto |
| :--- | :---: | :---: | :---: |
| **Sharpe Diario Real** | $\ge 1.00$ | **0.63** (NQ 1h), **0.55** (ES 1h) | **REPROBADO** |
| **Max Trailing Drawdown** | Apto para Prop Firm ($\le \$2,000$) | **\$53,954** en E-mini, **\$5,395** en Micro | **REPROBADO** |
| **Deflated Sharpe Ratio (DSR)** | $\ge 95\%$ ($M=338$) | **13.27%** | **REPROBADO** |
| **Test de Permutación vs Azar** | $p < 0.05$ (10,000 iteraciones) | **$p = 0.4586$** (NQ), **$p = 0.5062$** (ES) | **REPROBADO (Azar Puro)** |
| **Concentración de Beneficios** | Top 5 trades $< 25\%$ del PnL | **50.61%** en NQ, **111.94%** en ES 4h | **REPROBADO (Frágil)** |
| **Consistencia Temporal** | Sin rachas $> 2$ años en pérdida | **3 años seguidos en negativo (2021–2023)** | **REPROBADO** |

> [!CAUTION]
> **VEREDICTO FINAL:** **REJECTED (DESCALIFICADA PARA PRODUCCIÓN)**.  
> La Estrategia Unificada carece de ventaja estadística genuina frente al azar ($p = 0.4586$). Todo su rendimiento histórico fue producto de haber estado invertido en activos que subieron secularmente entre 2010 y 2026. No supera los filtros de Prop Firms, depende en más del 50% de solo 5 trades y posee un DSR de apenas 13.27%. El proceso cuantitativo cumplió su meta: evitar arriesgar capital en una estrategia sin alfa real.
