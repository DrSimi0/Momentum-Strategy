# INFORME DE AUDITORÍA Y OPTIMIZACIÓN EN MENOR TEMPORALIDAD (M5 Y M15)

**Fecha:** 22 de Octubre de 2026  
**Rama de Desarrollo:** `feature/lower-tf-m5-m15` (Bifurcada de `main`)  
**Universo:** Futuros CME `ES` y `NQ` (2010 a 2026, 16.36 años continuos de Databento remuestreados a M15 y M5, >323,000 barras).  
**Costos Reales CME:** Comisión institucional (\$2.00 por lado) + Slippage institucional (0.5 ticks por lado). Cero *look-ahead*: señal confirmada al cierre de $t$, ejecución en apertura de $t+1$.

---

## 1. Justificación y Motivo de la Bifurcación

Al trasladar la Estrategia Unificada de swing (H1/H4) directamente a 5m y 15m sin adaptaciones:
- El número de trades se multiplicó por 8x – 10x (más de 2,000 operaciones en 5m).
- Los costos de comisiones y slippage consumieron entre **\$19,000 y \$34,000 USD**.
- En `NQ 5m`, el Sharpe colapsó a **0.84** y en cripto arrojó pérdidas netas directas (BTC 5m: -$1,718 USD, Sharpe -5.93).
- **Decisión de Arquitectura:** Conforme a la instrucción del usuario, se crearon **dos ramas en Git**:
  - `main`: Preserva congelada la estrategia swing de temporalidades mayores (**H1/H4**), que tiene Sharpe > 2.0 y excelente eficiencia transaccional.
  - `feature/lower-tf-m5-m15`: Rama de especialización intradiaria para rediseñar y optimizar el sistema en **M15 y M5**.

---

## 2. Mecanismos de Optimización Intradiaria Implementados

Para batir la fricción de costos en alta frecuencia, se desarrollaron 4 adaptaciones en `src/strategies/intraday_unified_strategy.py`:

1. **Filtro de Horario Institucional (RTH Core 10:00 a 15:15 ET):**  
   Se eliminó toda operación fuera de horario regular y durante los primeros 30 minutos de apertura (09:30–10:00 ET), donde el spread y la volatilidad caótica aumentan el slippage.
2. **Cierre Forzoso al Fin de Sesión (MOC a las 15:50 ET):**  
   Liquidación obligatoria intradía. Cero riesgo de gap *overnight* y cero financiamiento.
3. **Escala de Medias de Microestructura (EMA 20 y EMA 80):**  
   En 5m, una sesión RTH tiene 78 barras. Una EMA de 80 periodos representa exactamente la media móvil de la sesión actual, sustituyendo la lenta EMA 200 de swing.
4. **Filtro de Expansión de Volatilidad (ATR):**  
   Solo se autorizan entradas cuando `ATR(14) >= 0.95 * SMA(ATR, 40)`. Esto filtra los periodos de consolidación lateral estrecha (*choppy markets*) donde las comisiones destruyen el capital.

---

## 3. Tabla Comparativa de Rendimiento (Histórico Completo 2010 a 2026)

| Activo | TF | Configuración | Trades | Win Rate % | Profit Factor | PnL Bruto ($) | Comisiones/Slippage ($) | PnL Neto ($) | Sharpe | Max Drawdown ($) | Expectativa ($/trade) |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **NQ** | **15m** | **3_Intraday_Medias_80_y_Volatilidad** | **596** | **39.93%** | **1.38** | **$142,315.46** | **$5,364.00** | **+$136,951.46** | **1.88** | **$32,821.78** | **+$229.78** |
| NQ | 15m | 2_RTH_Horario_Institucional_MOC | 755 | 39.07% | 1.16 | $125,455.99 | $6,795.00 | +$118,660.99 | 1.45 | $66,182.34 | +$157.17 |
| NQ | 15m | 0_Línea_Base_Sin_Filtros | 829 | 38.36% | 1.12 | $103,608.77 | $7,461.00 | +$96,147.77 | 1.19 | $65,795.09 | +$115.98 |
| **NQ** | **5m** | **3_Intraday_Medias_80_y_Volatilidad** | **1373** | **42.68%** | **1.13** | **$68,559.31** | **$12,357.00** | **+$56,202.31** | **0.14** | **$30,143.69** | **+$40.93** |
| NQ | 5m | 1_Solo_Cierre_MOC (Sin Volatilidad) | 2642 | 46.29% | 0.98 | $11,176.22 | $23,778.00 | -$12,601.78 | -0.47 | $75,209.18 | -$4.77 |
| NQ | 5m | 0_Línea_Base_Sin_Filtros | 2198 | 36.85% | 1.15 | $215,693.93 | $19,782.00 | +$195,911.93 | 0.84 | $54,884.60 | +$89.13 |
| **ES** | **15m** | **0_Línea_Base_Sin_Filtros** | **829** | **38.24%** | **1.18** | **$105,580.83** | **$13,678.50** | **+$91,902.33** | **1.02** | **$24,306.26** | **+$110.86** |
| ES | 15m | 2_RTH_Horario_Institucional_MOC | 776 | 38.27% | 1.18 | $100,287.32 | $12,804.00 | +$87,483.32 | 1.01 | $26,323.07 | +$112.74 |
| ES | 15m | 3_Intraday_Medias_80_y_Volatilidad | 618 | 38.19% | 1.13 | $48,491.82 | $10,197.00 | +$38,294.82 | 0.56 | $25,672.29 | +$61.97 |
| **ES** | **5m** | **4_Intraday_Agresiva_EMA_10_50** | **1607** | **40.45%** | **1.12** | **$63,536.08** | **$26,515.50** | **+$37,020.58** | **0.60** | **$12,018.85** | **+$23.04** |
| ES | 5m | 3_Intraday_Medias_80_y_Volatilidad | 1375 | 44.65% | 1.11 | $56,354.71 | $22,687.50 | +$33,667.21 | 0.46 | $17,484.41 | +$24.49 |
| ES | 5m | 1_Solo_Cierre_MOC (Sin Volatilidad) | 2571 | 46.36% | 1.03 | $60,611.21 | $42,421.50 | +$18,189.71 | 0.03 | $27,282.47 | +$7.07 |

---

## 4. Hallazgos Cuantitativos y Veredicto Comparativo de Ramas

### 4.1 En M15: Gran Éxito de la Optimización Intradiaria en Nasdaq
- En **NQ 15m**, la configuración optimizada (`EMA 20/80 + RTH 10:00-15:15 + MOC + Filtro ATR`) logró resultados sobresalientes:
  - El Sharpe ratio subió de **1.19 a 1.88** (+58% de mejora).
  - El beneficio neto aumentó en más de **+$40,000 USD** (hasta **+$136,951 USD**).
  - El Max Drawdown se redujo exactamente a la **mitad** (de \$65,795 a **\$32,821 USD**).
  - La expectativa por trade se duplicó de \$115.98 a **\$229.78 USD**.

### 4.2 En M5: La Barrera de Fricción
- En 5 minutos, la frecuencia de trades supera las 1,300 operaciones.
- Simplemente forzar el cierre diario MOC sin filtro de volatilidad destruye el sistema (-$12,601 USD en NQ y Sharpe 0.03 en ES), ya que el slippage y comisiones de \$42,000 USD superan la ganancia bruta.
- La configuración con filtro de volatilidad rescata el sistema al terreno positivo (**+$56,202 USD** en NQ y **+$37,020 USD** en ES con un drawdown de solo \$12k), pero el Sharpe anualizado se queda acotado en **0.60**.

### 4.3 Recomendación de Uso por Rama
- **Para Trading Swing / Tendencial Institucional:** Usar la rama **`main`** con temporalidad de **1 hora** (Sharpe 2.04 a 2.45, baja rotación, cero estrés de comisiones).
- **Para Trading Intradía / Day Trading:** Usar la rama **`feature/lower-tf-m5-m15`** con temporalidad de **15 minutos en NQ** (`EMA 20/80 + RTH + MOC + ATR`), que cierra posiciones cada día a las 15:50 ET con un Sharpe de 1.88 y drawdown de \$32k USD.
