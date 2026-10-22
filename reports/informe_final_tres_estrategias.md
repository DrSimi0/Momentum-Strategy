# INFORME FINAL DE AUDITORÍA CUANTITATIVA: EVALUACIÓN DE TRES ESTRATEGIAS INDEPENDIENTES (A, B, C) Y ESTUDIO DE COMBINACIÓN

**Fecha:** 22 de Octubre de 2026  
**Autor:** Auditoría e Ingeniería Cuantitativa  
**Universo de Datos:** 
- Futuros CME: S&P 500 E-mini (`ES`) y Nasdaq-100 E-mini (`NQ`) en temporalidades 1h y 4h continuos (2010 a 2026, 16.36 años, Databento).
- Criptoactivos (Exploratorio): `BTC-USDT` y `ETH-USDT` en temporalidad 4h (BingX Perpetual Swaps).
**Criterio Metodológico:** Pre-registro formal previo, ejecución causal sin *look-ahead* (señal al cierre de $t$, ejecución al open de $t+1$), deducción estricta de costos reales (comisión CME \$2.00/lado + slippage 0.5 ticks/lado) y penalización por minería de datos (Deflated Sharpe Ratio).

---

## 1. RESUMEN EJECUTIVO Y VEREDICTOS

| Estrategia | Metodología Evaluada | Espacio de Búsqueda ($M$) | Rendimiento en Validación | Rendimiento OOS / Walk-Forward | Veredicto Final |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Estrategia A** | Barrido de Medias Móviles (SMA/EMA) y Selección Top 10 por Clustering | 224 combinaciones | Sharpe 1.55 a 2.42 | WF Positivas: 21% a 50% (< 60%). DSR: 0.3% a 1.5% | **REJECTED (FAIL)** |
| **Estrategia B** | Relación Dinámica RSI(14) / MACD vs Líneas Base | 40 combinaciones | Ganancia aparente en MACD Solo (+$72k) | Relación Dinámica destruye alfa (-$79k en divergencias) | **REJECTED (FAIL)** |
| **Estrategia C** | Patrones de Vela y Figuras Chartistas Causales ($n=3$) | 42 variantes | Pocos patrones Long ganan por drift alcista | Figuras complejas con $N < 100$; patrones bajistas destructivos (-$256k) | **REJECTED (FAIL)** |
| **Combinación** | Risk Parity / Ensamble Multiactivo | N/A | No procede despliegue | Evitar ensamble de sistemas con expectativa neta negativa | **NO PROCEDE** |

**Decisión del Holdout / Validación Futura:** Se adoptó la **Opción C** (Forward test causal diario sin ejecución de órdenes ni costos adicionales de API). El script `scripts/forward_test_signal_generator.py` queda operativo y registrando señales en bitácora inmutable.

---

## 2. AUDITORÍA DETALLADA: ESTRATEGIA A (MEDIAS MÓVILES TOP 10)

### 2.1 Metodología y Pre-registro
- Se evaluó una grilla exhaustiva de $M = 224$ configuraciones de medias móviles (SMA y EMA, períodos rápidos {10, 20, 21, 30, 50}, períodos lentos {50, 100, 150, 200}, timeframes 1h y 4h).
- En el período de validación (2021–2026), se seleccionaron las 10 mejores configuraciones no correlacionadas mediante clustering jerárquico ortogonal.

### 2.2 Resultados del Top 10 de Validación
El ranking de validación estuvo totalmente dominado por EMAs rápidas en temporalidad de 1 hora:
1. `EMA_20_50_1h` (Sharpe Val: 2.42, PnL Val: +$145,200 USD)
2. `EMA_10_50_1h` (Sharpe Val: 2.37, PnL Val: +$141,600 USD)
3. `EMA_20_100_1h` (Sharpe Val: 2.21, PnL Val: +$130,500 USD)
4. `EMA_30_50_1h` (Sharpe Val: 2.14, PnL Val: +$128,100 USD)

### 2.3 La Prueba Ácida: Walk-Forward Multi-Anual y Deflated Sharpe Ratio
Al someter estas 10 configuraciones a la prueba Walk-Forward rodante multi-anual sobre el histórico completo (2010–2026):
- **Consistencia Temporal:** Solo entre el **21.4% y el 50.0%** de las ventanas anuales generaron PnL positivo (el criterio mínimo pre-registrado era $\ge 60\%$).
- **Deflated Sharpe Ratio (DSR):** Al penalizar el Sharpe por haber probado $M = 224$ combinaciones y ajustar por asimetría y curtosis, el DSR resultó entre **0.3% y 1.5%** (muy lejos del umbral de significancia del $\ge 95\%$).
- **Diagnóstico:** Los excelentes números en 2021–2026 fueron un artefacto del fuerte rally tendencial post-pandemia en la renta variable estadounidense, no una ventaja matemática persistente de los cruces de medias.

---

## 3. AUDITORÍA DETALLADA: ESTRATEGIA B (RELACIÓN DINÁMICA RSI / MACD VS LÍNEAS BASE)

### 3.1 Hipótesis y Modelos Comparados
Se contrastó la hipótesis de que analizar la relación de segundo orden entre RSI(14) y el histograma del MACD(12,26,9) aporta valor predictivo frente a las líneas base simples:
1. `REL_AGREEMENT`: Correlación rodante $\rho(RSI, Hist) > 0.50$ con dirección concordante.
2. `REL_DIVERGENCE`: Divergencias causales confirmadas entre el precio y el histograma.
3. `STATIC_AGREEMENT`: Confluencia estática binaria (RSI > 50 y Hist > 0).
4. `MACD_SOLO`: Cruce estándar de línea de señal MACD (línea base).
5. `RSI_SOLO`: Rotura de niveles 50/70/30 (línea base).

### 3.2 Rendimiento Comparativo en Desarrollo y Validación (ES y NQ)

| Activo / TF | Modelo Evaluado | N Trades | Win Rate % | PnL Desarrollo ($ USD) | PnL Validación ($ USD) | Sharpe Neto | Veredicto |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **ES 4h** | `MACD_SOLO` (Línea Base) | 260 | 36.5% | +$72,400 | +$12,500 | 0.82 | Candidata Base |
| **ES 4h** | `REL_AGREEMENT` | 84 | 33.3% | -$14,200 | -$8,900 | -0.45 | Destruye Alfa |
| **ES 4h** | `REL_DIVERGENCE` | 142 | 29.5% | -$79,150 | -$24,600 | -1.18 | Severamente Destructivo |
| **NQ 4h** | `MACD_SOLO` (Línea Base) | 275 | 38.1% | +$112,300 | +$18,400 | 0.95 | Candidata Base |
| **NQ 4h** | `REL_DIVERGENCE` | 138 | 28.2% | -$115,200 | -$41,200 | -1.42 | Severamente Destructivo |

### 3.3 Diagnóstico Cuantitativo
- La relación dinámica y el cálculo de divergencias no solo no mejoran a los indicadores individuales, sino que **destruyen sistemáticamente el rendimiento**.
- Las divergencias oscilatorias generan señales contratendenciales prematuras que son devastadas en mercados institucionales guiados por flujos direccionales.

---

## 4. AUDITORÍA DETALLADA: ESTRATEGIA C (PATRONES DE VELA Y FIGURAS CHARTISTAS CAUSALES)

### 4.1 Principio de Detección Causal
- **Cero Fuga de Futuro:** Los pivotes de fractales y figuras complejas (dobles suelos/techos) se confirmaron con retardo estricto de $n=3$ barras. La señal se emite en el cierre de la barra de confirmación $t$, y la orden entra en la apertura de $t+1$.
- **Filtro de Muestra:** Se descartaron todas las figuras con $N < 100$ operaciones.

### 4.2 Resultados Consolidados

1. **Patrones Bajistas (Shorts):**
   - `Engulfing_Bearish`: Pérdidas masivas en todos los activos (-\$256,796 USD en ES 4h, -\$220,930 USD en ES 1h, -\$295,850 USD en NQ 4h, -\$249,023 USD en NQ 1h).
   - `Double_Top_Short`: Pérdidas netas en todas las configuraciones.
   - *Razón estructural:* El sesgo secular alcista (*equity risk premium*) de los índices estadounidenses castiga de forma sistemática cualquier estrategia que venda en corto rupturas o patrones gráficos sin cobertura macroeconómica.

2. **Patrones Alcistas (Longs) y Figuras Geométricas:**
   - `Engulfing_Bullish` en 4h: Mostró ganancias globales en desarrollo (+$129,650 en ES), pero en validación OOS (2021–2026) su Sharpe colapsó a **-0.03** y su PnL se estancó en solo +$10,189 USD en 5 años con comisiones.
   - `Double_Bottom_Long` en 4h: PnL en validación fuera de muestra fuertemente negativo (-\$42,314 USD en ES, Sharpe Val -1.09; -\$64,982 USD en NQ, Sharpe Val -2.06).
   - `Hammer_Long` en 1h: Aunque generó Sharpe positivo, su baja frecuencia en validación ($N=22$ en ES y $N=30$ en NQ a lo largo de 5 años) no alcanza significancia estadística robusta y sufre alta dispersión muestral.

3. **Criptoactivos (BTC y ETH):**
   - El 100% de los patrones gráficos individuales no superaron el filtro mínimo de $N \ge 100$ trades o arrojaron expectativa matemática negativa fuera de muestra.

---

## 5. ESTUDIO DE COMBINACIÓN MULTIACTIVO Y RISK PARITY

El pre-registro metodológico estableció una condición de compuerta inmutable:
> *"Condición de despliegue: Solo se combinan estrategias que hayan SUPERADO independientemente los criterios de validación. Si ninguna o solo una supera el criterio, se documenta que no procede la combinación y se archiva."*

### Veredicto del Ensamble:
- **NO PROCEDE EL DESPLIEGUE EN PRODUCCIÓN.**
- Fundamento Matemático: Combinar subcarteras o estrategias mediante *Risk Parity* (ponderación por volatilidad inversa o paridad de riesgo) solo reduce el riesgo si los activos o estrategias subyacentes poseen una expectativa matemática positiva ($\mu_i > 0$). Si los componentes individuales tienen $\mu_i \le 0$ tras comisiones y slippage, la cartera ponderada tiene un retorno esperado negativo $\mu_p \le 0$ y solo diversifica la trayectoria hacia la pérdida de capital.

---

## 6. PROTOCOLO OPERATIVO: FORWARD TEST EN VIVO (OPCIÓN C)

Conforme a la instrucción del usuario, se implementó el entorno para registrar el comportamiento futuro sin consumir datos de pago ni arriesgar capital:
1. **Script Automatizado:** [forward_test_signal_generator.py](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/scripts/forward_test_signal_generator.py).
2. **Bitácora Inmutable:** Registros en formato JSON append-only en `reports/forward_test/forward_test_signals.log` y CSV estructurado en `reports/forward_test/forward_test_signals.csv`.
3. **Métricas a Monitorear:** Cada día al cierre, el sistema registra el estado de los indicadores de las tres estrategias para ES y NQ, permitiendo auditar con datos vírgenes a partir de hoy si alguna de las hipótesis candidatas despierta edge en el régimen de mercado venidero.

---

## 7. CONCLUSIÓN GENERAL

El proceso de auditoría cuantitativa independiente ha demostrado de forma irrefutable que:
1. Las estrategias convencionales del análisis técnico clásico (cruces de medias, divergencias de RSI/MACD y figuras chartistas de manual de trading) **no superan las pruebas estadísticas rigurosas tras considerar los costos transaccionales reales** en los mercados de futuros modernos.
2. Todo intento de optimizar parámetros sobre datos pasados sin penalización DSR crea la ilusión de rentabilidad, la cual se evapora de inmediato en pruebas OOS y walk-forward.
3. El proceso de pre-registro científico y control estricto de datos cumplió su objetivo primordial: proteger el capital y evitar el despliegue de estrategias sin ventaja competitiva real.
