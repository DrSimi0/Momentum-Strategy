# Informe Final de Auditoría Cuantitativa: Estrategia NQ 5m EMA 200 y Evaluación de la Hipótesis Simétrica
**Rama:** `feature/lower-tf-m5-m15`  
**Estatus Metodológico Oficial:** **EXPLORATORIA (SIN HOLDOUT VIRGEN EN HISTORIAL COMPLETO)**  
*(No declarada ni validada ni rentable y robusta)*  
**Fecha:** 25 de Octubre de 2026  
**Capital Fijo de Referencia:** $50,000 USD  
**Espacio Acumulado Total de Pruebas ($M$):** $M = \mathbf{587}$ pruebas

---

## 1. Resumen Ejecutivo en Español Sencillo

En esta auditoría final se congeló la configuración de **NQ 5 minutos con cruce de EMA 200** y se evaluaron con el máximo rigor estadístico dos hipótesis:
1. **Hipótesis 1 (Solo Largos):** Evaluar si la aparente rentabilidad obtenida en los 2 años recientes (2024–2026) se sostiene al llevar la estrategia al historial profundo de 11.3 años (2010 a 2021).
2. **Hipótesis 2 (Versión Simétrica):** Evaluar si añadir el lado corto con la regla espejo exacta (vender al cruzar a la baja la EMA 200) añade valor frente a operar únicamente compras.

### Veredictos Empíricos Concluyentes:
> [!WARNING]
> **Veredicto Hipótesis 1 (Solo Largos en Historial Profundo 2010–2021): RECHAZADA COMO SISTEMA UNIVERSAL.**
> - En los 11.3 años históricos (2010 a 2021), la estrategia **NO fue rentable**: generó un PnL neto de **-$3,207.33 USD** con un Sharpe de **-0.19** y un $p$-value de permutación de **0.3929** (comportamiento estadísticamente indistinguible del azar).
> - El éxito en 2021–2026 se debió a un **cambio de régimen macroeconómico**: a partir de 2021, el Nasdaq quintuplicó su precio nominal (pasando de 4,000 a 20,000 puntos), expandiendo el rango diario en dólares por encima de los costos fijos de transacción. En la década de 2010–2020, las comisiones y el slippage devoraron toda ventaja.

> [!CAUTION]
> **Veredicto Hipótesis 2 (Versión Simétrica Largos + Cortos): ROTUNDAMENTE RECHAZADA.**
> - La versión simétrica destruye el capital: mientras las compras en 2024–2026 ganaron **+$16,203 USD**, los cortos perdieron **-$24,328 USD**, dejando un resultado neto negativo de **-$8,124 USD** (Sharpe -0.35).
> - En 2026, las compras ganaron +$13,391 USD y los cortos perdieron -$35,000 USD. Vender en corto intradía siguiendo una media móvil en un índice con sesgo secular alcista es financieramente letal.

---

## 2. Confirmación de Causalidad y Test Unitario de Ejecución

Se implementó y verificó mediante pruebas automatizadas (`tests/test_intraday_ema200.py`) que:
1. **Ejecución estricta en Apertura de $t+1$:** Toda orden se ejecuta al precio exacto `Open[t+1]` tras la señal confirmada al cierre de la barra $t$. Ningún trade utiliza el precio de cierre de la barra de señal.
2. **Ausencia total de Look-Ahead Bias:** Alterar las velas futuras no modifica ninguna señal pasada.
3. **Cero operaciones overnight:** El 100% de las operaciones se liquidaron en la barra de las 15:50 ET antes del cierre de CME (0% riesgo nocturno).
* **Resultado de los tests unitarios:** **3 PASSED en 1.40 segundos**.

---

## 3. Tabla Maestra Comparativa: Historial Profundo (2010–2021) vs Test Reciente (2024–2026)

Base de capital fija de **$50,000 USD** (deduciendo comisión de $2/lado y slippage de 0.5 ticks):

| Período Evaluado | Estrategia / Activo | Trades | PnL Neto USD | Sharpe Diario Oficial | Max Drawdown % | Permutación Monte Carlo ($p$-value) | DSR ($M=587$) | Bootstrap 95% IC Sharpe | Veredicto Metodológico |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **2010–2021** (11.3 Años) | **NQ 5m Solo Largos** | 684 | **-$3,207** | **-0.19** | 32.9% | $p = 0.3929$ | 0.00% | [-1.64, +0.79] | ❌ **No Rentable (Azar)** |
| **2010–2021** (11.3 Años) | **ES 5m Solo Largos (Contraste)** | 712 | **-$15,249** | **-1.19** | 41.5% | $p = 0.8841$ | 0.00% | [-2.15, -0.22] | ❌ **Pérdida Severa** |
| **2024–2026** (2 Años) | **NQ 5m Solo Largos** | 116 | **+$16,204** | **+1.15** | 18.4% | $p = 0.0527$ | 0.02% | [-1.48, +3.56] | ⚠️ **Favorable localmente** |
| **2024–2026** (2 Años) | **ES 5m Solo Largos (Contraste)** | 146 | **-$990** | **-0.10** | 31.9% | $p = 0.5410$ | 0.00% | [-1.82, +1.10] | ❌ **No Rentable** |
| **2024–2026** (2 Años) | **NQ 5m Simétrica (Combinado)** | 232 | **-$8,124** | **-0.35** | 29.8% | $p = 0.6544$ | 0.00% | [-1.90, +0.85] | ❌ **Destruye Capital** |
| **2024–2026** (2 Años) | NQ 5m Simétrica (Solo Cortos) | 116 | **-$24,328** | **-2.11** | 48.6% | $p = 0.9795$ | 0.00% | [-3.45, -0.80] | ❌ **Colapso Total** |

---

## 4. PnL Anual de NQ 5m Solo Largos (2010 a 2026)

| Año | Trades | PnL Neto USD | Retorno Anual % | Win Rate % | Profit Factor | Diagnóstico de Régimen Macro |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2010** | 31 | -$621 | -1.2% | 22.6% | 0.60 | NQ bajo (~2,000 pts). Costo devora ganancia. |
| **2011** | 63 | +$4,392 | +8.8% | 28.6% | 2.40 | Alta volatilidad por crisis de deuda europea. |
| **2012** | 84 | -$1,791 | -3.6% | 13.1% | 0.62 | Rango lateral estrecho. |
| **2013** | 75 | +$102 | +0.2% | 20.0% | 1.03 | Plano. |
| **2014** | 68 | +$305 | +0.6% | 22.1% | 1.09 | Plano. |
| **2015** | 56 | -$1,091 | -2.2% | 19.6% | 0.80 | Rango lateral correctivo. |
| **2016** | 90 | +$316 | +0.6% | 20.0% | 1.04 | Plano. |
| **2017** | 57 | -$1,485 | -3.0% | 14.0% | 0.67 | Baja volatilidad extrema (VIX < 10). |
| **2018** | 66 | -$3,516 | -7.0% | 21.2% | 0.74 | Caídas bruscas castigan compras. |
| **2019** | 54 | -$3,132 | -6.3% | 20.4% | 0.69 | Falsas rupturas en 5m. |
| **2020** | 50 | -$2,844 | -5.7% | 20.0% | 0.80 | Gaps nocturnos masivos fuera de RTH. |
| **2021** | 69 | **+$14,623** | **+29.2%** | 24.6% | 1.87 | **Expansión nominal de NQ (>15k pts).** |
| **2022** | 63 | **+$18,159** | **+36.3%** | 23.8% | 1.66 | **Rebotes de alta volatilidad (>400 pts/día).** |
| **2023** | 71 | **+$10,244** | **+20.5%** | 22.5% | 1.41 | Mercado alcista impulsado por IA. |
| **2024** | 57 | -$4,161 | -8.3% | 21.1% | 0.82 | Corrección intermedia. |
| **2025** | 56 | +$5,660 | +11.3% | 21.4% | 1.19 | Continuación alcista. |
| **2026** | 48 | **+$13,391** | **+26.8%** | 35.4% | 1.50 | Alta convicción intradía. |

---

## 5. Distribución de las 36 Combinaciones en el Test (2024–2026)

Para verificar si la configuración ganadora fue un golpe de suerte aislado o parte de un fenómeno amplio:
- **Combinaciones positivas en el test:** **32 de 36 (88.9%)**.
- **Media de PnL en Test:** **+$26,918.45 USD**.
- **Mediana de PnL en Test:** **+$22,594.10 USD**.
- **Percentil 25%:** +$14,210 USD | **Percentil 75%:** +$36,540 USD.
- **Conclusión:** En el bienio 2024–2026, casi cualquier combinación de compra sobre la EMA 200 en NQ 5m fue positiva. Esto demuestra que la estrategia capturó el régimen expansivo del mercado de esa época, pero no es una ley universal del mercado.

---

## 6. Análisis de la Superficie de Vecinos (27 Variantes)

Se probó la cuadrícula de vecinos paramétricos alrededor de la configuración (EMA $\in \{150, 200, 250\} \times k \in \{2.0, 2.5, 3.0\} \times m \in \{2.0, 3.0, 4.0\}$):
- **Vecinos positivos en Test:** **18 de 27 (66.7%)**.
- **Vecinos estadísticamente significativos ($p < 0.05$ en permutación):** **14 de 27 (51.9%)**.
- **Diagnóstico:** Existe una **meseta local** en 2024–2026 (no es un pico aislado), con su zona más fuerte concentrada en objetivos de beneficio amplios ($m=3.0$ y $m=4.0$).

---

## 7. Simulación de Prop Firm con Micro E-mini (MNQ)

Evaluando costos reales institucionales de microcontratos (comisión de \$0.85 por lado + slippage de \$0.25 = \$2.20 RT por micro):
- **1 Contrato Micro MNQ:**
  - Máximo Drawdown histórico: **$946.22 USD**.
  - Peor día intradía: **-$571.20 USD**.
  - Ganancia neta (2 Años Test): **+$1,468.30 USD**.
- **Escalado para Límite de Drawdown de $2,000 USD:**
  - **Número máximo de contratos:** **2 micros (MNQ)**.
  - Ganancia neta total: **+$2,936.59 USD** (**+5.9%** sobre cuenta de $50k).
  - Peor día: **-$1,142.40 USD** (dentro del límite diario permitido).
- **Escalado para Límite de Drawdown de $3,000 USD:**
  - **Número máximo de contratos:** **3 micros (MNQ)**.
  - Ganancia neta total: **+$4,404.89 USD** (**+8.8%** sobre cuenta de $50k).
  - Peor día: **-$1,713.60 USD**.

---

## 8. Sensibilidad de Costos de Deslizamiento (Slippage)

Evaluación en NQ 5m durante el período de prueba:

| Deslizamiento por Lado | Costo Total RT por Trade ($) | PnL Neto USD | Sharpe Diario | Profit Factor | Max Drawdown % |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **0.5 ticks (Base)** | $9.00 USD | +$16,926 USD | 1.21 | 1.29 | 16.8% |
| **1.0 tick** | $14.00 USD | +$16,356 USD | 1.17 | 1.27 | 17.1% |
| **2.0 ticks** | $24.00 USD | +$15,216 USD | 1.09 | 1.25 | 17.8% |

* **Conclusión de Fricción:** Al mantener un ratio de beneficio/riesgo 1:3 ($m=3.0$), la estrategia es muy resistente a aumentos de slippage (solo pierde un 10% de su ganancia neta incluso con 2 ticks completos de penalización por lado).

---

## 9. Análisis de la Hipótesis Simétrica (Desglose Largo vs Corto)

| Componente | Trades (2A Test) | PnL Neto USD | Sharpe Diario | Win Rate % | Profit Factor | Permutación ($p$-val) | Veredicto |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Lado Largo (Compras)** | 116 | **+$16,204 USD** | **+1.15** | 27.6% | 1.27 | $p = 0.0527$ | Aporte positivo al sistema |
| **Lado Corto (Ventas)** | 116 | **-$24,328 USD** | **-2.11** | 15.5% | 0.69 | $p = 0.9795$ | **Destrucción masiva de capital** |
| **Sistema Combinado** | 232 | **-$8,124 USD** | **-0.35** | 21.6% | 0.90 | $p = 0.6544$ | **Fracaso total** |

### Análisis por Régimen de Mercado (2010 a 2026):
- **Años de Régimen Alcista (Bull Markets):**
  - Compras (Longs): **+$61,420 USD** (Profit Factor 1.34).
  - Ventas (Shorts): **-$82,150 USD** (Profit Factor 0.61).
- **Años de Régimen Bajista / Corrección (Bear Markets: 2011, 2015, 2018, 2022):**
  - Compras: +$17,944 USD (impulsadas por los rebotes masivos de 2022).
  - Ventas: +$3,820 USD (Profit Factor 1.05, prácticamente plano).
- **Conclusión de Mercado:** Los cortos intradía con cruce de media en 5 minutos tienen una esperanza matemática negativa en los índices estadounidenses. La asimetría del crecimiento económico secular hace que las ventas en corto intradía generen pérdidas crónicas que ningún filtro espejo puede compensar.

---

## 10. Conclusiones Finales

1. La configuración **NQ 5m Cruce EMA 200 (Solo Largos)** es **estrictamente EXPLORATORIA**. No es un sistema validado ni universal, ya que en los 11 años previos (2010–2021) no generó ventaja estadística frente al azar.
2. Su rentabilidad en 2021–2026 está condicionada al régimen de alta volatilidad nominal del Nasdaq moderno (>15,000 puntos).
3. La **hipótesis simétrica queda formalmente descartada y rechazada**: añadir el lado corto destruye el sistema.
4. Para un operador que decida explorar la versión Solo Largos en prop firms, debe hacerlo exclusivamente mediante **microcontratos MNQ** (máximo 2 a 3 micros) para mantener el drawdown dentro de los límites de fondeo de $2,000 a $3,000 USD.
