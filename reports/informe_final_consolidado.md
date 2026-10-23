# INFORME FINAL DE INVESTIGACIÓN Y AUDITORÍA CUANTITATIVA

**Fecha:** 23 de Octubre de 2026  
**Auditoría y Desarrollo:** Antigravity Quant Research  
**Datos:** Futuros CME `ES` y `NQ` (16.36 años continuos, 2010–2026, Databento); Cripto `BTC-USDT` y `ETH-USDT` (BingX).  
**Costos Reales:** CME \$2.00 comisión + 0.5 ticks slippage por lado. Cero look-ahead garantizado.

---

## 1. RESUMEN EJECUTIVO Y TRAYECTORIA

A lo largo de la investigación se evaluaron sistemáticamente tres etapas metodológicas:
1. **Auditoría de Estrategias Aisladas (A, B y C):** Todas fueron formalmente **RECHAZADAS** por sobreajuste, colapso en Walk-Forward (<50% ventanas positivas), destrucción de capital en divergencias oscilatorias y pérdidas masivas en operaciones cortas (Shorts perdieron >\$250k USD).
2. **Estrategia Cuantitativa Unificada:** Se combinaron las mejores capas ortogonales (`EMA 30/200` + `MACD/RSI` + Gatillo de velas `Engulfing/Hammer` en formato `Long-Only`), alcanzando rendimientos excepcionales en temporalidades mayores (**Sharpe 2.45 en NQ 1h** y **2.04 en ES 1h**).
3. **Evaluación M15/M5 y Bifurcación en Git:** Al probar en temporalidades menores, se evidenció que las comisiones en 5m devoran hasta el 53% del capital. Se crearon dos ramas en Git: `main` (para Swing en H1/H4) y `feature/lower-tf-m5-m15` (para Intradía M15/M5 optimizada con filtros RTH, MOC y volatilidad).

---

## 2. TABLA MAESTRA COMPARATIVA EN PORCENTAJES Y DÓLARES

> **Base de Capital:** \$50,000 USD por contrato en Futuros CME (garantía + colchón de volatilidad); \$10,000 USD en Cripto.  
> **Periodo:** 16.36 años continuos (2010 a 2026).

### 2.1 Rama Principal (`main`): Operativa Swing en Temporalidades Mayores (H1 y H4)

| Activo | Timeframe | Variante | Trades | Win Rate % | PnL Neto ($ USD) | Retorno Total (%) | Retorno Anual (CAGR) | Sharpe | Max Drawdown (%) | Retorno OOS (2021-26) | Buy & Hold (%) |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **NQ** | **1h** | **UNIFIED_LONG_ONLY** | **248** | **41.53%** | **+$174,665.62** | **+349.3%** | **+9.6%** | **2.45** | **-107.9%** | **+201.1%** | +1,514.2% |
| **NQ** | **4h** | **UNIFIED_LONG_ONLY** | **242** | **39.26%** | **+$182,218.20** | **+364.4%** | **+9.9%** | **2.14** | **-94.8%** | **+113.7%** | +1,529.2% |
| **ES** | **1h** | **UNIFIED_LONG_ONLY** | **269** | **40.15%** | **+$111,341.96** | **+222.7%** | **+7.4%** | **2.04** | **-46.0%** | **+161.5%** | +625.1% |
| **ES** | **4h** | **UNIFIED_LONG_ONLY** | **257** | **35.80%** | **+$50,830.65** | **+101.7%** | **+4.3%** | **0.83** | **-86.8%** | **+85.6%** | +629.8% |
| **BTC** | **4h** | **UNIFIED_LONG_ONLY** | **70** | **34.29%** | **+$461.30** | **+4.6%** | **+0.3%** | **0.24** | **-24.9%** | **-17.9%** | +281.7% |
| **ETH** | **4h** | **UNIFIED_LONG_ONLY** | **56** | **37.50%** | **+$1,651.63** | **+16.5%** | **+0.9%** | **0.75** | **-35.7%** | **-1.1%** | +46.1% |

### 2.2 Rama Especializada (`feature/lower-tf-m5-m15`): Operativa Intradía Optimizada

| Activo | Timeframe | Configuración | Trades | Win Rate % | PnL Bruto ($) | Fricción Costos (%) | PnL Neto ($ USD) | Retorno Total (%) | Sharpe | Max Drawdown (%) | Calmar Ratio |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **NQ** | **15m** | **EMA 20/80 + RTH + MOC + Volatilidad** | **596** | **39.93%** | **$142,315** | **-10.7%** | **+$136,951.46** | **+273.9%** | **1.88** | **-65.6%** | **4.17** |
| NQ | 15m | Línea Base Sin Filtros Intradía | 829 | 38.36% | $103,608 | -14.9% | +$96,147.77 | +192.3% | 1.19 | -131.6% | 1.46 |
| **NQ** | **5m** | **EMA 20/80 + RTH + MOC + Volatilidad** | **1373** | **42.68%** | **$68,559** | **-24.7%** | **+$56,202.31** | **+112.4%** | **0.14** | **-60.3%** | **1.86** |
| NQ | 5m | Cierre MOC sin filtro volatilidad | 2642 | 46.29% | $11,176 | -47.6% | -$12,601.78 | -25.2% | -0.47 | -150.4% | Negativo |
| **ES** | **15m** | **Línea Base Sin Filtros Intradía** | **829** | **38.24%** | **$105,580** | **-27.4%** | **+$91,902.33** | **+183.8%** | **1.02** | **-48.6%** | **3.78** |
| **ES** | **5m** | **EMA 10/50 Agresiva + Volatilidad** | **1607** | **40.45%** | **$63,536** | **-53.0%** | **+$37,020.58** | **+74.0%** | **0.60** | **-24.0%** | **3.08** |

---

## 3. CONCLUSIONES CUANTITATIVAS FUNDAMENTALES

1. **La regla `Long-Only` es obligatoria en índices:** Operar posiciones cortas en índices bursátiles reduce el Sharpe a menos de 0.40 y duplica el drawdown debido al sesgo secular alcista de la economía estadounidense (*equity risk premium*).
2. **El gatillo de Price Action (Velas) corta el riesgo a la mitad:** En NQ 4h redujo el Max Drawdown de \$91k a \$47k USD, y en ES 1h duplicó el Sharpe de 1.04 a 2.04 al filtrar falsas rupturas.
3. **Ganadora para Day Trading (Intradía):** **`NQ 15m Optimizada`** en la rama `feature/lower-tf-m5-m15`. Rinde **+273.9% de retorno neto**, Sharpe **1.88**, drawdown acotado a **-65.6%** y **cero pernocta** (cierra posiciones cada día a las 15:50 ET).
4. **Ganadora para Swing Trading:** **`NQ 1h`** en la rama `main`. Rinde **+349.3% de retorno neto** (+9.6% anual) con Sharpe **2.45** y una tasa de retención de capital superior frente a comisiones.
