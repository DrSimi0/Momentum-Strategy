# INFORME DE AUDITORÍA CUANTITATIVA ESTRICTA: RAMA INTRADÍA (M15 Y M5)

**Fecha:** 23 de Octubre de 2026  
**Rama de Desarrollo:** `feature/lower-tf-m5-m15`  
**Estatus Metodológico Oficial:** **EXPLORATORIA (SIN HOLDOUT VIRGEN)**  
**Principio de Honestidad Intelectual:** Todas las configuraciones intradiarias fueron desarrolladas, calibradas y evaluadas utilizando datos del periodo 2010–2026. Por tanto, quedan formalmente desprovistas de cualquier calificación de "validada" o "ganadora". Este informe audita la realidad matemática cruda de la rama intradiaria sin sesgos optimistas.

---

## 1. EXPLICACIÓN MATEMÁTICA DE LAS DISCREPANCIAS PREVIAS (NQ 15m: Sharpe 1.88 y Calmar 4.17)

En los reportes preliminares se informaron para la configuración `NQ 15m Optimizada` un Sharpe de **1.88** y un Calmar de **4.17**. La auditoría matemática revela el origen de ambos números:

1. **El Artefacto del Sharpe de 1.88:**  
   - En el motor `run_intraday_backtest`, el Sharpe se calculó sobre los retornos **por trade** multiplicados directamente por $\sqrt{252}$.  
   - La estrategia ejecutó 596 trades en 16.36 años, lo que equivale a solo **~36 trades al año**. Asumir 252 trades anuales infló artificialmente el ratio por un factor de $\sqrt{252 / 36.4} \approx 2.63$.  
   - Al calcular el Sharpe estrictamente sobre la **curva de retornos diarios de los 4,115 días de mercado reales** anualizado con $\times \sqrt{252}$, el verdadero **Sharpe Diario es de 0.75**.

2. **El Artefacto del Calmar Ratio de 4.17:**  
   - El valor de 4.17 se obtuvo calculando:  
     $$\frac{\text{Retorno Total Acumulado en 16 Años}}{\text{Max Drawdown \% sobre Capital Inicial}} = \frac{+273.90\%}{65.64\%} = \mathbf{4.17}$$  
   - **Error de Definición:** Esto representa la relación acumulada de PnL a Drawdown a lo largo de 16 años, **NO el Calmar Ratio**.  
   - **Calmar Ratio Real:** La definición financiera estándar exige comparar la tasa de crecimiento anual compuesta (**CAGR**) contra el **Max Drawdown % sobre el pico de equity**:  
     $$\text{Calmar Real} = \frac{\text{CAGR}}{\text{Max DD \% sobre Pico}} = \frac{+8.22\%}{15.62\%} = \mathbf{0.53}$$  
     (O bien $8.22\% / 65.64\% = \mathbf{0.13}$ si se toma como base el capital inicial).

---

## 2. TABLA MAESTRA DE RENDIMIENTOS DIARIOS (CAPITAL BASE FIJO $50,000 USD)

> **Bases de Drawdown Documentadas:**  
> - **Max DD % sobre Pico:** Mide la caída porcentual respecto al punto más alto alcanzado por la cuenta ($\text{Peak}$).  
> - **Max DD % sobre Capital Inicial:** Mide la pérdida máxima en dólares dividida entre los \$50,000 USD iniciales.

| Configuración | Activo | TF | Trades | Win Rate % | Profit Factor | PnL Neto Total ($) | Retorno Total % | CAGR % | Sharpe Diario (sqrt 252) | Max DD ($) | Max DD % (Pico) | Max DD % (Inicial) | Calmar Real | DSR (M=344) | DSR (M=26) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. NQ 15m Optimizada (EMA 20/80 + RTH + MOC + ATR)** | **NQ** | **15m** | **596** | **39.93%** | **1.38** | **+$136,951.46** | **+273.90%** | **+8.22%** | **0.75** | **$32,821.78** | **15.62%** | **65.64%** | **0.53** | **29.40%** | **62.90%** |
| 2. NQ 15m Línea Base (Sin filtros) | NQ | 15m | 829 | 38.36% | 1.12 | +$96,147.77 | +192.30% | +6.64% | 0.48 | $65,795.09 | 31.87% | 131.59% | 0.21 | 4.78% | 20.15% |
| 3. ES 15m Línea Base (Sin filtros) | ES | 15m | 829 | 38.24% | 1.18 | +$91,902.33 | +183.80% | +6.45% | 0.52 | $24,306.26 | 20.38% | 48.61% | 0.32 | 6.71% | 25.27% |
| 4. NQ 5m Optimizada (EMA 20/80 + RTH + MOC + ATR) | NQ | 5m | 1373 | 42.68% | 1.13 | +$56,202.31 | +112.40% | +4.62% | 0.34 | $30,143.69 | 49.32% | 60.29% | 0.09 | 1.25% | 7.85% |
| 5. ES 5m Agresiva (EMA 10/50 + ATR) | ES | 5m | 1607 | 40.45% | 1.12 | +$37,020.58 | +74.04% | +3.38% | 0.44 | $12,018.85 | 14.48% | 24.04% | 0.23 | 3.47% | 16.08% |
| 6. NQ 5m MOC Sin Volatilidad | NQ | 5m | 2642 | 46.29% | 0.98 | -$12,601.78 | -25.20% | -1.72% | 0.20 | $75,209.18 | 143.00% | 150.42% | -0.01 | 0.33% | 2.76% |

---

## 3. AUDITORÍA DE SUPERVIVENCIA EN PROP FIRMS

Las firmas de fondeo imponen dos reglas inmutables de control de riesgo:
- **Límite de Pérdida Diaria (Daily Loss Limit):** -\$1,000 USD (cuenta de \$50k) o -\$1,500 / -\$2,000 USD (cuenta de \$100k).
- **Límite de Max Trailing Drawdown:** \$2,000 USD (cuenta de \$50k) o \$3,000 USD (cuenta de \$100k).

### Tabla de Evaluación: E-mini vs Micro Contratos (MNQ / MES)

| Configuración | E-mini Peor Día ($) | E-mini Trailing DD ($) | E-mini Cabe Prop? | Micro Peor Día ($) | Micro Trailing DD ($) | Micro Pasa Pérdida Diaria? | Micro Pasa Trailing DD? | ¿Apta Prop Firm $50k? | ¿Apta Prop Firm $100k? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. NQ 15m Optimizada** | -$17,109.00 | $32,821.78 | **NO (Quiebra)** | **-$1,710.90** | **$3,282.18** | **NO (Excede $1,000)** | **NO (Excede $2,000)** | **NO** | **NO (Excede $3,000)** |
| **2. NQ 15m Línea Base** | -$17,109.00 | $65,795.09 | **NO (Quiebra)** | -$1,710.90 | $6,579.51 | **NO (Excede $1,000)** | **NO (Excede $2,000)** | **NO** | **NO** |
| **3. ES 15m Línea Base** | -$6,554.00 | $24,306.26 | **NO (Quiebra)** | -$655.40 | $2,430.63 | SÍ | **NO (Excede $2,000)** | **NO** | **SÍ (Margen $570)** |
| **4. NQ 5m Optimizada** | -$8,328.03 | $30,143.69 | **NO (Quiebra)** | -$832.80 | $3,014.37 | SÍ | **NO (Excede $2,000)** | **NO** | **NO (Excede $3,000)** |
| **5. ES 5m Agresiva** | -$4,016.50 | $12,018.85 | **NO (Quiebra)** | -$401.65 | $1,201.89 | SÍ | SÍ | **SÍ** | **SÍ** |
| **6. NQ 5m MOC Sin Volatilidad**| -$5,758.83 | $75,209.18 | **NO (Quiebra)** | -$575.88 | $7,520.92 | SÍ | **NO (Excede $2,000)** | **NO** | **NO** |

> [!CAUTION]
> **VEREDICTO SOBRE PROP FIRMS:**
> 1. **Contratos E-mini Estándar:** **Ninguna configuración es viable**. Un solo mal día en NQ genera pérdidas de -\$17,109 USD, provocando la liquidación inmediata de la cuenta.
> 2. **`NQ 15m Optimizada` en Micro MNQ:** **NO CABE**. Su peor día en micro fue de **-\$1,710.90 USD** (viola el límite diario de \$1,000 de una cuenta de \$50k y el de \$1,500 de una de \$100k). Además, su Max Trailing Drawdown fue de **\$3,282.18 USD** (viola los límites de \$2,000 y \$3,000 USD).
> 3. **La Única Configuración que Cumple los Límites (`ES 5m Agresiva` en Micro MES):** Cabe dentro de los límites de drawdown (\$1,201 USD trailing DD y -\$401 USD peor día), **PERO genera un CAGR de apenas +3.38% anual**. En una prueba de prop firm donde se exige un beneficio de 8% a 10% en pocas semanas, una estrategia que rinde 3.3% al año **jamás superaría el examen de evaluación**.

---

## 4. TEST DE PERMUTACIÓN MONTE CARLO (10,000 ITERACIONES)

Para cada configuración, se generaron **10,000 simulaciones de entradas aleatorias independientes** dentro del mismo horario intradiario y con duraciones idénticas:

| Configuración | PnL Real Estrategia ($) | PnL Medio Aleatorio ($) | P-Valor Empírico | Percentil Real % | ¿Bate al Azar (p < 0.05)? |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **1. NQ 15m Optimizada** | **+$136,951.46** | +$70,137.37 | **p = 0.1793** | 82.07% | **NO (Sin significancia)** |
| **2. NQ 15m Línea Base** | **+$96,147.77** | +$156,008.12 | **p = 0.7140** | 28.60% | **NO (Inferior al azar)** |
| **3. ES 15m Línea Base** | **+$91,902.33** | +$91,690.73 | **p = 0.4998** | 50.02% | **NO (Idéntico al azar)** |
| **4. NQ 5m Optimizada** | **+$56,202.31** | +$55,061.96 | **p = 0.4938** | 50.62% | **NO (Idéntico al azar)** |
| **5. ES 5m Agresiva** | **+$37,020.58** | +$1,188.26 | **p = 0.1404** | 85.96% | **NO (Sin significancia)** |
| **6. NQ 5m MOC Sin Volatilidad**| **-$12,601.78** | +$113,718.00 | **p = 0.9057** | 9.43% | **NO (Destrucción vs azar)**|

### Demostración Matemática:
- En **`NQ 15m Optimizada`**, aunque el PnL real (+\$136k) fue superior a la media aleatoria (+\$70k), el **p-valor empírico fue de 0.1793**. En estadística cuantitativa, un p-valor de casi 18% significa que existe casi un 18% de probabilidad de obtener ese resultado por pura suerte o varianza favorable. Falla holgadamente el criterio estándar de $p < 0.05$.
- En las configuraciones de 5m y líneas base, el p-valor ronda entre **0.49 y 0.71**, lo que demuestra que **comprar al azar con un dado produjo resultados idénticos o mejores**.

---

## 5. TEST DE CONCENTRACIÓN (ELIMINANDO LOS 5 MEJORES TRADES)

| Configuración | PnL Total Con Top 5 ($) | Ganancia de solo 5 Trades ($) | % PnL en Top 5 | PnL SIN Top 5 Trades ($) | Sharpe Diario Con Top 5 | Sharpe Diario SIN Top 5 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. NQ 15m Optimizada** | +$136,951.46 | **$59,055.00** | **43.12%** | +$77,896.46 | **0.75** | **0.56** |
| **2. NQ 15m Línea Base** | +$96,147.77 | **$68,576.02** | **71.32%** | +$27,571.75 | 0.48 | 0.24 |
| **3. ES 15m Línea Base** | +$91,902.33 | **$38,758.55** | **42.17%** | +$53,143.78 | 0.52 | 0.38 |
| **4. NQ 5m Optimizada** | +$56,202.31 | **$30,006.45** | **53.39%** | +$26,195.85 | 0.34 | 0.23 |
| **5. ES 5m Agresiva** | +$37,020.58 | **$12,126.38** | **32.76%** | +$24,894.20 | 0.44 | 0.32 |
| **6. NQ 5m MOC Sin Volatilidad**| -$12,601.78 | **$26,630.11** | N/A | **-$39,231.89** | 0.20 | -0.03 |

- En `NQ 15m Optimizada`, el **43.1% del beneficio total dependió de solo 5 días de mercado** de los 596 trades.
- En la línea base de NQ 15m, el **71.3%** del PnL estuvo concentrado en solo 5 operaciones.

---

## 6. VEREDICTO FINAL DE AUDITORÍA: RAMA INTRADÍA

| Criterio Evaluado | Umbral Requerido | Resultado Real en NQ 15m Optimizada | Veredicto |
| :--- | :---: | :---: | :---: |
| **Sharpe Diario Real** | $\ge 1.00$ | **0.75** | **REPROBADO** |
| **Pérdida Máxima Diaria** | $\le \$1,000$ (en Micro) | **-\$1,710.90 USD** | **REPROBADO** |
| **Trailing Drawdown** | $\le \$2,000$ (en Micro) | **\$3,282.18 USD** | **REPROBADO** |
| **Permutación vs Azar** | $p < 0.05$ (10k it.) | **$p = 0.1793$** | **REPROBADO** |
| **Deflated Sharpe Ratio** | $\ge 95\%$ ($M=344$) | **29.40%** | **REPROBADO** |

> [!CAUTION]
> **VEREDICTO FINAL DE LA RAMA INTRADÍA:** **REJECTED (DESCALIFICADA PARA PRODUCCIÓN)**.  
> La optimización intradiaria en M15 logró mitigar las pérdidas extremas de la línea base, pero su Sharpe diario real es de apenas **0.75**, no alcanza significancia estadística frente a entradas aleatorias ($p = 0.1793$), su DSR es de solo 29.4% y **descalifica en cuentas de Prop Firm** tanto por pérdida máxima diaria como por trailing drawdown. La rama intradía queda archivada formalmente como exploratoria y no apta para trading institucional ni evaluación de fondeo.
