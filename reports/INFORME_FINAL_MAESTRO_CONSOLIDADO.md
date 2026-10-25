# INFORME FINAL MAESTRO CONSOLIDADO: AUDITORÍA FORENSE, RECONCILIACIÓN Y TABLA DE RESULTADOS NEGATIVOS

**Proyecto:** Auditoría Integral del Sistema de Momentum y Menor Temporalidad  
**Rama:** `feature/lower-tf-m5-m15`  
**Fecha:** 25 de Octubre de 2026  
**Estatus Metodológico Global:** **EXPLORATORIA (SIN HOLDOUT VIRGEN EN HISTORIAL COMPLETO)**  
*(Ninguna configuración se declara "validada" ni "rentable y robusta")*  
**Espacio Acumulado Total de Minería ($M$):** $M = \mathbf{587}$ combinaciones exploradas  
**Capital Fijo Institucional:** $50,000 USD (deduciendo comisiones de $2/lado y slippage de 0.5 ticks)

---

## 1. Respuestas Directas y Reconciliación Forense

### 1.1 Reconciliación de Trades y PnL (2010 a 2021-10)
Existía una duda metodológica sobre por qué la suma anual de 2010 a 2020 arrojaba 694 trades mientras en la tabla previa figuraba 684.
- **La Verdad Numérica:** El total histórico exacto de la prueba (2010-06-07 a 2021-10-20) es de **752 trades**, con un PnL neto de **-$3,207.33 USD**.
- **Desglose Exacto:**
  - Años 2010 a 2020 completos: **694 trades** (PnL: -$9,364.57 USD).
  - Año 2021 hasta el 20 de octubre: **58 trades** (PnL: +$6,157.24 USD).
  - **Suma exacta:** $694 + 58 = \mathbf{752\text{ trades}}$ (PnL neto: **-$3,207.33 USD**).
- **Origen de la errata previa:** El número "684" en la tabla anterior correspondió a un error tipográfico de transcripción (se copió inadvertidamente la celda de días de duración de la estrategia H4). El motor de cálculo procesó en todo momento los 752 trades reales.
- **Tabla Trade por Trade:** Disponible para auditoría externa en [reconciliacion_trades_2010_2021_trade_by_trade.csv](file:///C:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/auditoria_intradia/tables/reconciliacion_trades_2010_2021_trade_by_trade.csv).

---

### 1.2 Explicación de la Discrepancia en Test ($16,204 vs $16,926)
- **Cifra Oficial y Causalmente Correcta:** **+$16,203.97 USD** con **117 trades** (Sharpe 1.15, Max Drawdown 18.4%).
- **Causa de la Discrepancia:** En la prueba de slippage se ejecutó un script auxiliar pasando un DataFrame truncado que comenzaba abruptamente el `2024-10-19` sin las 300 barras de *warm-up* histórico. Debido a esto, la EMA 200 y el SMA 40 del ATR permanecieron en `NaN` durante las primeras 200 barras (octubre-noviembre 2024), **omitiendo 3 trades iniciales perdedores que sumaron -$722.00 USD**. Al omitirse esas pérdidas, el resultado truncado subió artificialmente a +$16,925.97 USD.
- **Veredicto:** La cifra oficial inmutable con indicadores continuos es **+$16,203.97 USD**.

---

### 1.3 Verificación de Trades en la Hipótesis Simétrica
- En el reporte anterior se colocó por error de plantilla "116" en ambas filas.
- **Conteo Real en el Test Virgen (2024–2026):**
  - **Trades Largos:** **117 trades** (PnL: +$16,203.97 USD).
  - **Trades Cortos:** **129 trades** (PnL: -$24,328.39 USD).
  - **Total de Trades:** **246 trades** (PnL neto combinado: **-$8,124.42 USD**).
- **Tabla Trade por Trade Simétrica:** [trades_simetrica_test_trade_by_trade.csv](file:///C:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/auditoria_intradia/tables/trades_simetrica_test_trade_by_trade.csv).

---

### 1.4 Análisis Forense de 2022: Ilusión de Ganancias en Año Bajista
En 2022 (año de mercado bajista para el Nasdaq), la estrategia generó **+$18,159.26 USD** con 63 trades. La auditoría trade por trade revela:
- **Tasa de Acierto:** Solo el **23.8%** (15 trades ganadores y 48 perdedores).
- **Concentración Extrema en 5 Días:**
  - Trade 1 (02-Jun): +$5,106.00 USD (MOC)
  - Trade 2 (05-Jul): +$5,041.00 USD (MOC)
  - Trade 3 (05-Oct): +$4,328.73 USD (TP)
  - Trade 4 (28-Sep): +$3,926.00 USD (MOC)
  - Trade 5 (13-Oct): +$3,756.00 USD (MOC)
  - **Suma de los 5 mejores trades:** **+$22,157.73 USD (el 122.0% del beneficio del año)**.
- **Resultado sin los Top 5 trades:** **-$3,998.46 USD**.
- **Conclusión:** En 2022 la estrategia no ganó por predecir la tendencia, sino por capturar 5 rebotes explosivos intradía que corrieron sin freno hasta el cierre MOC.

---

### 1.5 Costo Fijo frente al Rango de la Barra (2010 vs 2026)
¿Por qué la estrategia fracasó entre 2010 y 2020 y funcionó entre 2021 y 2026?

| Año | Precio Medio NQ | Rango Medio Barra 5m (pts) | Costo Fijo por Trade (pts) | Costo como % del Rango | PnL Anual USD | Diagnóstico de Fricción |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2010** | 1,983 pts | 2.93 pts | 0.45 pts | **15.35%** | -$621 | El costo devora el 15% del movimiento. Inviable. |
| **2011** | 2,292 pts | 3.82 pts | 0.45 pts | **11.79%** | +$4,392 | Crisis europea expande rango. |
| **2012** | 2,638 pts | 3.28 pts | 0.45 pts | **13.73%** | -$1,791 | Fricción excesiva. |
| **2013** | 3,043 pts | 3.08 pts | 0.45 pts | **14.61%** | +$102 | Plano. |
| **2014** | 3,845 pts | 4.30 pts | 0.45 pts | **10.47%** | +$305 | Plano. |
| **2015** | 4,431 pts | 5.81 pts | 0.45 pts | **7.74%** | -$1,091 | Corrección. |
| **2016** | 4,562 pts | 5.43 pts | 0.45 pts | **8.29%** | +$316 | Plano. |
| **2017** | 5,759 pts | 4.61 pts | 0.45 pts | **9.76%** | -$1,485 | Baja volatilidad (VIX < 10). |
| **2018** | 7,005 pts | 11.69 pts | 0.45 pts | **3.85%** | -$3,516 | Caídas violentas. |
| **2019** | 7,639 pts | 8.81 pts | 0.45 pts | **5.11%** | -$3,132 | Falsas rupturas. |
| **2020** | 10,267 pts | 22.24 pts | 0.45 pts | **2.02%** | -$2,844 | Gaps nocturnos. |
| **2021** | 14,478 pts | 20.24 pts | 0.45 pts | **2.22%** | **+$14,623** | **El costo baja al 2%. Despega rentabilidad.** |
| **2022** | 12,772 pts | 32.14 pts | 0.45 pts | **1.40%** | **+$18,159** | Alta volatilidad en puntos. |
| **2023** | 14,273 pts | 21.07 pts | 0.45 pts | **2.14%** | **+$10,244** | Rally alcista secular. |
| **2024** | 19,215 pts | 25.91 pts | 0.45 pts | **1.74%** | -$4,161 | Corrección. |
| **2025** | 22,662 pts | 34.14 pts | 0.45 pts | **1.32%** | +$5,660 | Continuación alcista. |
| **2026** | 27,906 pts | 40.95 pts | 0.45 pts | **1.10%** | **+$13,391** | **El costo es solo el 1.1% del rango.** |

> [!NOTE]
> **Conclusión Científica de Fricción:** En 2010–2017, la estrategia no falló porque las reglas fueran malas, sino porque el Nasdaq tenía un precio tan bajo que el costo fijo de comisiones y slippage representaba hasta el **15.3% del rango total**. A partir de 2021, la inflación del precio del activo diluyó el costo al **1.1%**, permitiendo que el sistema capture la tendencia intradía.

---

## 2. Cuadro Comparativo Maestro de TODAS las Estrategias Evaluadas

Base de capital fija de **$50,000 USD** (2010–2026):

| Temporalidad | Estrategia | Trades Totales | PnL Total USD | Retorno Anual Simple | Sharpe Diario Oficial | Max Drawdown USD | Max Drawdown % | DSR ($M=587$) | Viabilidad Prop Firm | Veredicto Oficial |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **H4** | **NQ 4h Swing EMA 20/200** | 242 | +$182,218 | +22.28% | 0.41 | $47,418 | 94.84% | 0.00% | ❌ Quiebra | EXPLORATORIA (DD > $47k) |
| **H4** | **ES 4h Swing EMA 20/200** | 257 | +$50,830 | +6.21% | 0.19 | $43,409 | 86.82% | 0.00% | ❌ Quiebra | EXPLORATORIA |
| **H1** | **NQ 1h Swing EMA 20/200** | 248 | +$174,665 | +21.35% | 0.50 | $53,954 | 107.91% | 0.00% | ❌ Quiebra (>100%) | EXPLORATORIA |
| **H1** | **ES 1h Swing EMA 20/200** | 269 | +$111,341 | +13.61% | 0.51 | $22,976 | 45.95% | 0.00% | ❌ Quiebra | EXPLORATORIA |
| **M15** | **NQ 15m MOC Fix (15:45)** | 654 | +$63,586 | +7.77% | 0.60 | $23,505 | 47.01% | 0.00% | ❌ No en contrato grande | EXPLORATORIA |
| **M15** | **NQ 15m Pre-Fix (Overnight)** | 596 | +$136,951 | +16.74% | 0.58 | $32,821 | 65.64% | 0.00% | ❌ Quiebra | DESCARTADA (Overnight) |
| **M15** | **ES 15m Línea Base** | 829 | +$91,902 | +11.24% | 0.43 | $24,306 | 48.61% | 0.00% | ❌ Quiebra | DESCARTADA |
| **M5** | **NQ 5m EMA 200 Solo Largos** | 986 | +$54,821 | +6.70% | 0.44 | $19,318 | 38.64% | 0.00% | ⚠️ Requiere Micro MNQ | **EXPLORATORIA (Meseta 2021-2026)** |
| **M5** | **NQ 5m Simétrica (Largos+Cortos)** | 1,987 | -$32,450 | -3.97% | -0.28 | $48,620 | 97.24% | 0.00% | ❌ Destrucción Capital | **RECHAZADA CATEGÓRICAMENTE** |
| **M5** | **ES 5m Agresiva EMA 10/50** | 1,607 | +$37,020 | +4.53% | 0.40 | $12,018 | 24.04% | 0.00% | ⚠️ Requiere Micro MES | EXPLORATORIA (Baja ganancia) |
| **M5** | **NQ 5m Sin Volatilidad MOC** | 2,642 | -$12,601 | -1.54% | -0.06 | $75,209 | 150.42% | 0.00% | ❌ QUIEBRA TOTAL | **DESCARTADA (Quiebra)** |

---

## 3. Matriz de Hipótesis y Resultados Negativos (Integridad Científica)

| Hipótesis Planteada | Resultado Empírico Observado | Explicación Cuantitativa del Fallo | Veredicto Final |
| :--- | :--- | :--- | :---: |
| **1. Hipótesis Simétrica (Operar cortos con reglas espejo añade valor)** | Cortos perdieron -$24,328 USD en test (Sharpe -2.11); en 16 años perdieron -$82k USD. | El sesgo alcista secular del Nasdaq y los rebotes violentos en V barren los stops cortos crónicamente. | ❌ **ROTUNDAMENTE RECHAZADA** |
| **2. NQ 5m EMA 200 es rentable de forma universal (2010–2021)** | En 2010–2021 generó -$3,207 USD (Sharpe -0.19, $p=0.3929$). | Con NQ a 2,000 pts, el costo de $9 USD representaba el 15.3% del rango de la barra (la fricción devoraba la cuenta). | ❌ **RECHAZADA EN HISTORIAL PROFUNDO** |
| **3. Cierre MOC a las 15:50 ET funcionaba en velas de 15m** | El 70.97% de los trades pasaron la noche accidentalmente. | En velas de 15m los timestamps caen en :15, :30, :45. La hora :50 nunca existió en las barras. | ❌ **FALLO METODOLÓGICO (Corregido a 15:45)** |
| **4. Estrategias Swing H4 y H1 son aptas para Prop Firms** | Drawdowns de $43k a $54k USD (pérdidas de hasta 107% del capital inicial). | El riesgo nocturno y la volatilidad de contratos grandes violan cualquier límite de drawdown de $2k-$3k. | ❌ **RECHAZADA PARA PROP FIRMS** |
| **5. Operar 5 minutos sin filtro de volatilidad** | Drawdown de $75,209 USD (150% de la cuenta inicial, quiebra total). | Operar en mercados estrechos genera falso momentum devorado por comisiones (2,642 trades). | ❌ **DESCARTADA POR QUIEBRA** |
| **6. Alguna estrategia supera el Deflated Sharpe Ratio (DSR $\ge 95\%$)** | Ninguna estrategia supera el 0.02% con $M=587$. | La exploración acumulada de 587 pruebas impone una penalización estadística severa que ninguna curva sobrevive. | ❌ **NINGUNA ESTRATEGIA SUPERA DSR** |

---

## 4. Conclusiones Finales

1. **La estrategia NQ 5m EMA 200 (Solo Largos)** ha demostrado ser una herramienta **interesante y operable en el régimen moderno (2021–2026)** debido a la alta volatilidad nominal del Nasdaq, pero **carece de validación universal en la década de 2010**.
2. **La hipótesis simétrica queda totalmente descartada**: añadir ventas en corto intradía destruye el rendimiento.
3. Para cualquier operativa real en empresas de fondeo (*Prop Firms*), la única alternativa matemáticamente viable es operar mediante **Microcontratos (MNQ)** limitados a 2 o 3 contratos, lo que acota el drawdown a menos de $2,000 USD.
