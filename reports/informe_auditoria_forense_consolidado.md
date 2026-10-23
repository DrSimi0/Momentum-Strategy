# INFORME DE AUDITORÍA CUANTITATIVA FORENSE Y COMPARATIVA INTEGRAL
## ESTRATEGIAS SWING (H1/H4) VS MENOR TEMPORALIDAD (M15/M5)

**Fecha:** 23 de Octubre de 2026  
**Rama:** `feature/lower-tf-m5-m15`  
**Estatus Metodológico Oficial:** **EXPLORATORIA (SIN HOLDOUT VIRGEN)**  
**Principio Rector:** Honestidad matemática absoluta, auditoría forense sin sesgos y preservación estricta de las reglas.

---

## 1. ACLARACIÓN DEL SHARPE DE NQ 15m (0.75 vs 0.58), FÓRMULA EXACTA Y CAPITAL BASE

### Comparación de Ambas Métricas
En los informes previos se presentaron dos mediciones distintas para `NQ 15m Optimizada`: **0.75** y **0.58**. A continuación se detalla su origen matemático exacto:

1. **Sharpe Diario Compuesto sobre Equity Móvil (0.75):**
   - **Capital Base Inicial:** \$50,000 USD.
   - **Fórmula de Retorno Diario:**
     $$R_t^{\text{comp}} = \frac{E_t - E_{t-1}}{E_{t-1}} = \frac{\Delta \text{PnL}_t}{E_{t-1}}$$
   - **Fórmula de Sharpe:**
     $$\text{Sharpe}_{\text{comp}} = \frac{\overline{R^{\text{comp}}}}{\sigma_{R^{\text{comp}}}} \times \sqrt{252} = \mathbf{0.7549} \approx \mathbf{0.75}$$
   - **Efecto Matemático:** Conforme la cuenta crece desde \$50,000 hasta \$186,951 USD acumulados, los mismos movimientos en dólares representan un menor porcentaje de retorno sobre la base expandida. Esto reduce artificialmente la volatilidad porcentual de la serie en el tramo final, comprimiendo $\sigma$ y elevando el Sharpe a **0.75**.

2. **Sharpe Diario Estandarizado sobre Capital Fijo (0.58) — [VALOR OFICIAL]:**
   - **Capital Base Fijo Inmutable:** $C_0 = \$50,000\text{ USD}$ durante todos los 4,115 días de mercado.
   - **Fórmula de Retorno Diario:**
     $$R_t^{\text{fijo}} = \frac{\Delta \text{PnL}_t}{\$50,000}$$
   - **Fórmula de Sharpe:**
     $$\text{Sharpe}_{\text{oficial}} = \frac{\overline{R^{\text{fijo}}}}{\sigma_{R^{\text{fijo}}}} \times \sqrt{252} = \frac{\text{Mean}(\Delta \text{PnL})}{\text{Std}(\Delta \text{PnL})} \times \sqrt{252} = \mathbf{0.5786} \approx \mathbf{0.58}$$
   - **Veredicto Oficial:** **El Sharpe oficial es 0.58**. Dado que la estrategia se opera a tamaño fijo (1 contrato constante sin reinversión de utilidades), la métrica rigurosa debe medir el rendimiento por unidad de volatilidad monetaria normalizada por el capital fijo inicial, sin depender de la dilatación del capital móvil.

---

## 2. RECÁLCULO INTEGRAL DE TODAS LAS CONFIGURACIONES SOBRE CAPITAL FIJO ($50,000 USD)

Se recalcularon todas las configuraciones del repositorio normalizando estrictamente los retornos sobre capital fijo (\$50,000 USD). Esta formulación es completamente inmune a las distorsiones de signo por balances negativos.

### Tabla Comparativa Integral: Swing (H1/H4) vs Menor Temporalidad (M15/M5)

| Grupo | Configuración | Activo | TF | Trades | Win Rate % | Profit Factor | PnL Neto Total ($) | CAGR % | Sharpe Oficial (Cap. Fijo $50k) | Sharpe Compuesto (Equity Móvil) | Max DD ($) | Max DD % Pico | Mínimo Equity ($) | Días Insolvente | ¿Llegó a Equity Negativo? | Time in Mkt % | B&H Ajustado CAGR % | B&H Ajustado Sharpe | ¿Bate B&H Ajustado? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Swing** | Swing_1_ES_1h | ES | 1h | 269 | 40.15% | 1.39 | +$111,341.96 | +7.27% | **0.51** | 0.55 | $22,976.05 | 22.65% | $46,551.37 | 0 | **NO** | 35.72% | +7.43% | 0.47 | **SÍ** |
| **Swing** | Swing_2_NQ_1h | NQ | 1h | 248 | 41.53% | 1.45 | +$174,665.62 | +9.42% | **0.50** | 0.63 | $53,954.51 | 35.82% | $49,591.00 | 0 | **NO** | 30.69% | +11.18% | 0.51 | **NO** |
| **Swing** | Swing_3_ES_4h | ES | 4h | 257 | 35.80% | 1.15 | +$50,830.65 | +3.54% | **0.19** | 0.27 | $43,409.07 | 52.51% | $33,845.98 | 0 | **NO** | 43.21% | +8.39% | 0.47 | **NO** |
| **Swing** | Swing_4_NQ_4h | NQ | 4h | 242 | 39.26% | 1.41 | +$182,218.20 | +7.92% | **0.41** | 0.56 | $47,418.68 | 29.77% | $38,856.06 | 0 | **NO** | 38.03% | +12.47% | 0.51 | **NO** |
| **Intradía** | **Intra_1_NQ_15m_Opt**| **NQ** | **15m**| **596** | **39.93%**| **1.38**| **+$136,951.46** | **+8.22%**| **0.58** | **0.75** | **$32,821.78** | **15.62%** | **$48,093.75** | **0** | **NO** | **13.86%**| **+7.19%** | **0.34** | **SÍ** |
| **Intradía** | Intra_2_NQ_15m_Base| NQ | 15m| 829 | 38.36% | 1.12 | +$96,147.77 | +6.64% | **0.28** | 0.48 | $65,795.09 | 31.87% | $48,383.24 | 0 | **NO** | 30.51% | +11.17% | 0.51 | **NO** |
| **Intradía** | Intra_3_ES_15m_Base| ES | 15m| 829 | 38.24% | 1.18 | +$91,902.33 | +6.45% | **0.43** | 0.52 | $24,306.26 | 20.38% | $45,075.57 | 0 | **NO** | 32.56% | +7.05% | 0.45 | **NO** |
| **Intradía** | Intra_4_NQ_5m_Opt | NQ | 5m | 1373| 42.68% | 1.13 | +$56,202.31 | +4.62% | **0.34** | 0.34 | $30,143.69 | 49.32% | $25,928.09 | 0 | **NO** | 12.42% | +6.69% | 0.33 | **SÍ** |
| **Intradía** | Intra_5_ES_5m_Agr | ES | 5m | 1607| 40.45% | 1.12 | +$37,020.58 | +3.38% | **0.40** | 0.44 | $12,018.85 | 14.48% | $47,614.41 | 0 | **NO** | 9.32% | +2.85% | 0.24 | **SÍ** |
| **Intradía** | Intra_6_NQ_5m_SinVol| NQ | 5m | 2642| 46.29% | 0.98 | -$12,601.78 | -1.72% | **-0.06** | 0.20 | $75,209.18 | 143.00% | -$22,613.63| 672 | **SÍ (QUIEBRA)**| 25.96%| +10.25% | 0.47 | **NO** |

> [!CAUTION]
> **Identificación de Cuentas Quebradas (Equity $\le 0$):**
> De las 10 configuraciones evaluadas a lo largo de los 16 años (2010–2026), **únicamente una llegó a equity negativo: `Intra_6_NQ_5m_MOC_Sin_Volatilidad`**, cayendo a un mínimo de **-\$22,613.63 USD** y permaneciendo 672 días insolvente.
> Las otras 9 configuraciones mantuvieron siempre su balance por encima de cero (su mínimo equity osciló entre \$25,928 y \$49,591 USD).

---

## 3. AUDITORÍA FORENSE DEL CIERRE MOC A LAS 15:50 ET EN VELAS DE 15M

### Mecánica Temporal y Sellos Horarios
La especificación de la estrategia pre-registró una regla de salida: `moc_close_time = "15:50"`.  
Al auditar los sellos horarios reales del dataset `NQ_15m.parquet`:
- Las barras intradiarias de 15m terminan a: `15:00`, `15:15`, `15:30` y **`15:45` ET**.
- **No existe ninguna barra con etiqueta temporal `15:50` ET**. La barra de las `15:45` ET cubre el intervalo causal de 15:45 a 16:00 ET (fin de la sesión regular RTH).
- **Consecuencia Matemática Directa:** En `NQ 15m Optimizada`, la condición `t_str >= "15:50"` **nunca se cumplió**, por lo que **exactamente 0 trades fueron cerrados por la etiqueta MOC**.
- **Desglose Exacto de las 596 Salidas en NQ 15m:**
  - **Stop Loss (SL):** 341 trades (57.2%).
  - **Take Profit (TP):** 234 trades (39.3%).
  - **Cruce de Medias Contrario (Signal Flip):** 21 trades (3.5%).
  - **MOC:** 0 trades (0.0%).

### Verificación de Causalidad y Test Unitario
En velas de menor temporalidad donde sí existe la barra de las 15:50 (como en M5, donde hubo 474 cierres MOC):
- La orden MOC se ejecuta rigurosamente en el **`Open` de la barra de las 15:50 ET**.
- Se verificó en `tests/test_intraday_audit_compliance.py::test_moc_execution_causality_and_timestamps` que:
  1. No se accede a los precios `High`, `Low` ni `Close` de las 15:50 ni de velas posteriores.
  2. La salida ocurre instantáneamente al abrir la vela causal sin ningún tipo de *look-ahead bias*.

---

## 4. TEST DE PERMUTACIÓN MONTE CARLO (10,000 ITERACIONES) PARA LOS 9 VECINOS DEL GRID DE NQ 15M

Se ejecutó un test de permutación Monte Carlo independiente con **10,000 iteraciones para cada uno de los 9 vecinos paramétricos** de la grilla de medias móviles $\{10, 20, 30\} \times \{50, 80, 120\}$ en NQ 15m:

| Fast EMA | Slow EMA | Trades | PnL Real ($) | Sharpe Fijo | PnL Medio Aleatorio ($) | Std PnL Aleatorio ($) | P-Valor Empírico | Percentil Real % | ¿Significativo ($p < 0.05$)? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 10 | 50 | 681 | +$144,498.95 | 0.56 | +$72,101.88 | $73,139.83 | **p = 0.1629** | 83.71% | **NO** |
| 10 | 80 | 658 | +$165,697.69 | 0.65 | +$73,594.45 | $74,305.92 | **p = 0.1082** | 89.18% | **NO** |
| 10 | 120 | 649 | +$131,418.77 | 0.54 | +$72,534.76 | $74,011.19 | **p = 0.2143** | 78.57% | **NO** |
| 20 | 50 | 605 | +$142,767.43 | 0.60 | +$67,786.14 | $71,451.35 | **p = 0.1448** | 85.52% | **NO** |
| **20** | **80** | **596** | **+$136,951.46** | **0.58** | **+$70,137.37** | **$72,131.31** | **p = 0.1793** | **82.07%** | **NO** |
| 20 | 120 | 608 | +$121,541.31 | 0.51 | +$71,468.27 | $72,868.31 | **p = 0.2478** | 75.22% | **NO** |
| 30 | 50 | 558 | +$126,044.71 | 0.52 | +$65,631.66 | $69,796.72 | **p = 0.1930** | 80.70% | **NO** |
| 30 | 80 | 577 | +$118,872.79 | 0.51 | +$64,795.50 | $69,925.00 | **p = 0.2206** | 77.94% | **NO** |
| 30 | 120 | 597 | +$100,531.67 | 0.44 | +$70,282.12 | $72,159.37 | **p = 0.3371** | 66.29% | **NO** |

> [!CAUTION]
> **CONTEO OFICIAL DE VECINOS SIGNIFICATIVOS ($p < 0.05$):**
> **EXACTAMENTE 0 DE 9 VECINOS TIENEN $p < 0.05$**.
> Todos los p-valores oscilan entre **0.1082 y 0.3371**. Esto demuestra empíricamente que la rentabilidad de toda la meseta es un reflejo de la tendencia alcista estructural del Nasdaq-100 durante las horas de la tarde, y no de la capacidad predictiva de los cruces de medias móviles.

---

## 5. FÓRMULA EXACTA DEL BUY & HOLD AJUSTADO POR TIEMPO EN MERCADO

Para evaluar objetivamente si la estrategia aporta alfa genuino o solo captura pasivamente una fracción del mercado mientras está invertida, se definió la siguiente formulación estandarizada:

1. **Exposición Temporal al Mercado ($T_{\text{market}}$):**
   $$T_{\text{market}} = \frac{\sum_{i=1}^N \text{Barras en Posición}}{\text{Total de Barras en el Dataset}}$$

2. **CAGR del Buy & Hold Ajustado:**
   Se pondera el retorno acumulado total del subyacente ($R_{\text{B\&H}} = P_{\text{final}} / P_{\text{inicial}} - 1$) por la fracción del tiempo en posición:
   $$\text{CAGR}_{\text{B\&H Ajustado}} = \left( 1 + R_{\text{B\&H}} \times T_{\text{market}} \right)^{\frac{1}{Y}} - 1$$
   Donde $Y = 16.36$ años.

3. **Sharpe del Buy & Hold Ajustado:**
   A partir de la serie diaria de retornos del índice subyacente ($R_{t,\text{B\&H}}$), su Sharpe diario anualizado ($\text{Sharpe}_{\text{B\&H}}$) se escala según la raíz del tiempo de exposición:
   $$\text{Sharpe}_{\text{B\&H Ajustado}} = \text{Sharpe}_{\text{B\&H}} \times \sqrt{T_{\text{market}}}$$

### Resultados en NQ 15m:
- Exposición: **13.86%** del tiempo en mercado.
- Buy & Hold Ajustado: CAGR de **+7.19%** y Sharpe de **0.34**.
- Estrategia `NQ 15m Optimizada`: CAGR de **+8.22%** y Sharpe Oficial de **0.58**.
- **Conclusión:** La estrategia supera al Buy & Hold ajustado por exposición (0.58 vs 0.34), pero captura solo una pequeña porción del +1525% del Buy & Hold total continuo.

---

## 6. MODELO ANALÍTICO DE POTENCIA ESTADÍSTICA DEL FORWARD TEST

Para contrastar formalmente la hipótesis $H_0: \text{Sharpe} \le 0$ frente a $H_1: \text{Sharpe} > 0$ a un nivel de significancia del 95% ($\alpha = 0.05$ unilateral, $Z_{0.95} = 1.6449$), el tiempo de muestreo requerido en años depende críticamente del verdadero Sharpe poblacional y de la potencia estadística deseada ($1 - \beta$):

$$N_{\text{años}} = \left( \frac{Z_{1-\alpha} + Z_{1-\beta}}{\text{Sharpe}_{\text{anual}}} \right)^2$$

### Matriz de Años y Trades Requeridos en Forward Test (NQ 15m a 36.4 trades/año)

| Sharpe Verdadero Poblacional | Potencia Deseada ($1-\beta$) | Nivel de Confianza ($1-\alpha$) | Años Requeridos en Vivo | Meses Requeridos | Trades Necesarios ($N$) |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0.6** | **50%** | **95%** | **7.52 años** | 90.2 meses | 274 trades |
| **0.6** | **80% (Estándar)** | **95%** | **17.17 años** | **206.1 meses** | **626 trades** |
| **0.6** | **95% (Alta Certeza)**| **95%** | **30.06 años** | 360.7 meses | 1,095 trades |
| **0.4** | **50%** | **95%** | **16.91 años** | 202.9 meses | 616 trades |
| **0.4** | **80% (Estándar)** | **95%** | **38.64 años** | **463.7 meses** | **1,408 trades** |
| **0.4** | **95% (Alta Certeza)**| **95%** | **67.64 años** | 811.7 meses | 2,464 trades |
| **0.2** | **50%** | **95%** | **67.64 años** | 811.7 meses | 2,464 trades |
| **0.2** | **80% (Estándar)** | **95%** | **154.56 años** | **1,854.8 meses** | **5,631 trades** |
| **0.2** | **95% (Alta Certeza)**| **95%** | **270.55 años** | 3,246.7 meses | 9,856 trades |

> [!IMPORTANT]
> **DICTAMEN MATEMÁTICO SOBRE EL FORWARD TEST:**
> Si el Sharpe real de la estrategia fuera de **0.6** (cercano al 0.58 observado):
> - Se necesitarían **17.2 años de forward testing en vivo** para tener un 80% de probabilidad de rechazar el azar con significancia del 95%.
> - Si el Sharpe real fuera de **0.4**, se requerirían **38.6 años**.
> - En un periodo comercial típico de 1 a 2 años de forward test, **la potencia estadística es inferior al 15%**, lo que significa que un forward test a corto plazo es prácticamente incapaz de distinguir cuantitativamente la habilidad del azar.

---

## 7. VEREDICTO GENERAL DEFINITIVO

1. **Sharpe Oficial:** Queda fijado en **0.58** sobre capital base inmutable de \$50,000 USD.
2. **Quiebras Reales:** De las 10 configuraciones estudiadas, **solo `NQ 5m MOC Sin Volatilidad` quebró** (equity mínima -\$22,613 USD).
3. **MOC en 15m:** No gatilló debido a que las barras de 15m cierran a las `15:45` ET. Las salidas se ejecutaron limpiamente por SL (57%), TP (39%) y Flip (3%).
4. **Permutación en Vecinos:** **0 de los 9 vecinos lograron $p < 0.05$** en 10,000 iteraciones Monte Carlo (p-valores entre 0.10 y 0.33).
5. **Estatus del Proyecto:** La estrategia se mantiene formalmente catalogada como **EXPLORATORIA Y DESCALIFICADA** para capital institucional y evaluaciones de Prop Firm.
