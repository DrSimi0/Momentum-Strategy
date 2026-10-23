# INFORME DE AUDITORÍA FORENSE: RESOLUCIÓN DEL FALLO MOC EN 15M Y CONVENCIÓN UNIFICADA DE CAPITAL FIJO

**Fecha:** 23 de Octubre de 2026  
**Rama:** `feature/lower-tf-m5-m15`  
**Estatus Oficial Inmutable:** **EXPLORATORIA (SIN HOLDOUT VIRGEN)**  

---

## 1. HALLAZGO FORENSE EN 15M: DISTRIBUCIÓN OVERNIGHT Y DESGLOSE DE PNL

### Diagnóstico del Mecanismo Fallido
En las configuraciones de 15 minutos, la regla original pre-registró `moc_close_time = "15:50"`. Al auditar los sellos horarios de las velas de 15 minutos, se descubrió que los timestamps terminan en:
`... 15:00, 15:15, 15:30 y 15:45 ET`.  
Al no existir vela con timestamp `15:50`, la condición `t_str >= "15:50"` **nunca se activó**.

### Consecuencias Matemáticas del Fallo (2010–2026)
Esto convirtió a la supuesta "estrategia intradía" en una estrategia mayoritariamente **swing overnight**:

| Configuración 15m Pre-Fix | Total Trades | Trades Overnight | Trades Intradía Puro | % Trades Overnight | Barras Held Mediana | Barras Held Máx | Días Held Máx | PnL Total USD | PnL Intradía Puro ($) | PnL Overnight ($) | % PnL Proveniente de Overnight |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. NQ 15m Optimizada (Pre-Fix)** | 596 | **423** | 173 | **70.97%** | 18.0 barras | 151 barras | 9.95 días | +$136,951.46 | **-$100,089.19** | **+$237,040.65** | **173.08%** |
| **2. NQ 15m Línea Base** | 829 | **697** | 132 | **84.08%** | 28.0 barras | 401 barras | 22.11 días | +$96,147.77 | **-$162,304.18** | **+$258,451.95** | **268.81%** |
| **3. ES 15m Línea Base** | 829 | **702** | 127 | **84.68%** | 29.0 barras | 311 barras | 18.96 días | +$91,902.33 | **-$82,382.73** | **+$174,285.05** | **189.64%** |

> [!CAUTION]
> **REVELACIÓN CRÍTICA DE AUDITORÍA:**
> El **70.97% de los trades de NQ 15m pasaron la noche**, manteniéndose hasta casi 10 días abiertos.  
> Más revelador aún: **las operaciones que cerraron el mismo día generaron una pérdida de -\$100,089 USD**. Todo el beneficio informado previamente (+\$136,951 USD) provino exclusivamente de las operaciones que se quedaron abiertas *overnight* (+\$237,040 USD), capturando el drift alcista del mercado nocturno de futuros.

---

## 2. TABLA UNIFICADA DE LAS 10 CONFIGURACIONES (CONVENCIÓN CAPITAL FIJO $50,000 USD)

Se estandarizan todas las configuraciones bajo una sola métrica rigurosa e inmune a las distorsiones de patrimonio:
- **Retorno Anual Simple:** $\frac{\text{PnL Total USD}}{\$50,000} \div 16.36\text{ años} \times 100\%$
- **Drawdown % Capital Inicial:** $\frac{\text{Max Drawdown USD}}{\$50,000} \times 100\%$
- **Calmar Simple:** $\frac{\text{Retorno Anual Simple (\%)}}{\text{Drawdown \% Capital Inicial}}$

| Grupo | Configuración | Activo | TF | Capital Base ($) | N Trades | Win Rate % | Profit Factor | PnL Neto Total ($) | Retorno Anual Simple % | Sharpe Oficial (Cap. Fijo) | Max DD ($) | Max DD % Capital Inicial | Calmar Simple | ¿Llegó a Equity Negativo? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Swing** | Swing_1_ES_1h | ES | 1h | $50,000 | 269 | 40.15% | 1.39 | +$111,341.96 | **+13.61%** | **0.51** | $22,976.05 | 45.95% | **0.30** | NO |
| **Swing** | Swing_2_NQ_1h | NQ | 1h | $50,000 | 248 | 41.53% | 1.45 | +$174,665.62 | **+21.35%** | **0.50** | $53,954.51 | 107.91% | **0.20** | NO |
| **Swing** | Swing_3_ES_4h | ES | 4h | $50,000 | 257 | 35.80% | 1.15 | +$50,830.65 | **+6.21%** | **0.19** | $43,409.07 | 86.82% | **0.07** | NO |
| **Swing** | Swing_4_NQ_4h | NQ | 4h | $50,000 | 242 | 39.26% | 1.41 | +$182,218.20 | **+22.28%** | **0.41** | $47,418.68 | 94.84% | **0.23** | NO |
| **Intradía** | Intra_1_NQ_15m_Opt (PreFix)| NQ | 15m | $50,000 | 596 | 39.93% | 1.38 | +$136,951.46 | **+16.74%** | **0.58** | $32,821.78 | 65.64% | **0.26** | NO |
| **Intradía** | Intra_2_NQ_15m_Base | NQ | 15m | $50,000 | 829 | 38.36% | 1.12 | +$96,147.77 | **+11.75%** | **0.28** | $65,795.09 | 131.59% | **0.09** | NO |
| **Intradía** | Intra_3_ES_15m_Base | ES | 15m | $50,000 | 829 | 38.24% | 1.18 | +$91,902.33 | **+11.24%** | **0.43** | $24,306.26 | 48.61% | **0.23** | NO |
| **Intradía** | Intra_4_NQ_5m_Opt | NQ | 5m | $50,000 | 1373 | 42.68% | 1.13 | +$56,202.31 | **+6.87%** | **0.34** | $30,143.69 | 60.29% | **0.11** | NO |
| **Intradía** | Intra_5_ES_5m_Agr | ES | 5m | $50,000 | 1607 | 40.45% | 1.12 | +$37,020.58 | **+4.53%** | **0.40** | $12,018.85 | 24.04% | **0.19** | NO |
| **Intradía** | Intra_6_NQ_5m_SinVol | NQ | 5m | $50,000 | 2642 | 46.29% | 0.98 | -$12,601.78 | **-1.54%** | **-0.06** | $75,209.18 | 150.42% | **-0.01** | **SÍ (QUIEBRA)** |

---

## 3. CORRECCIÓN CAUSAL DE EJECUCIÓN EN 15M: SALIDA PLANA OBLIGATORIA A LAS 15:45 ET

### Pre-registro y Decisión Previa
Se congeló formalmente bajo Git en `PREREGISTRO_MOC15_FIX.md` (commit `a009a1e`) la regla exacta:
- **Barra de Salida MOC Decidida:** `15:45 ET` (cubre el intervalo de 15:45 a 16:00 ET).
- **Momento y Precio de Ejecución:** Salida obligatoria en el **`Open` de la barra de las 15:45 ET**.
- **Causalidad Inmutable:** Al abrirse la barra 15:45, la condición se cumple con certeza conocida; no se utiliza información posterior ni se espera al cierre de sesión.
- **Espacio de Minería Actualizado:** Se incorporaron 3 variantes al conteo: **$M_{\text{total}} = 380$** y **$M_{\text{intra}} = 56$**.

### Comparativa: NQ 15m Pre-Fix vs Post-Fix (Salida Obligatoria 15:45 ET)

| Métrica Cuantitativa | NQ 15m Pre-Fix (MOC 15:50 Fallido) | NQ 15m Post-Fix (MOC 15:45 Efectivo) | Variación |
| :--- | :---: | :---: | :---: |
| **Trades Totales** | 596 | **654** | +58 trades |
| **Trades Overnight (%)** | **70.97% (423 trades)** | **0.31% (2 trades)** *(Cierres festivos 13:00)* | **-99.6%** |
| **Salidas Ejecutadas por MOC** | 0 trades (0%) | **474 trades (72.5%)** | +474 trades |
| **PnL Neto Total USD** | +$136,951.46 | **+$63,586.81** | **-$73,364.65 (-53.6%)** |
| **Retorno Anual Simple %** | +16.74% | **+7.77%** | -8.97% |
| **Sharpe Oficial (Capital Fijo)** | **0.58** | **0.60** | +0.02 |
| **Max Drawdown USD** | $32,821.78 | **$23,505.09** | **-$9,316.69 (Mejora DD)** |
| **Max DD % Capital Inicial** | 65.64% | **47.01%** | -18.63% |
| **Calmar Simple** | 0.26 | **0.17** | -0.09 |
| **Permutación Monte Carlo (10,000 it.)**| **p = 0.1793** | **p = 0.2695** | **REPROBADO (Inferior al azar)** |
| **DSR ($M=380$)** | 9.41% | **11.69%** | **REPROBADO (Umbral >= 95%)** |

---

## 4. AUDITORÍA DE PROP FIRM TRAS LA CORRECCIÓN MOC EN 15M (MNQ)

Se evaluó la versión estrictamente intradiaria en micro contratos (MNQ) con riesgo fijo de 0.5% (2 micros) y 1.0% (4 micros):

| Riesgo % | Contratos MNQ | PnL Total USD | CAGR % | Peor Día Intradía ($) | Max Trailing Drawdown ($) | Pasa Pérdida Diaria ($1,000)? | Pasa Trailing DD ($2,000)? | ¿Apta Prop Firm $50k? | ¿Apta Prop Firm $100k? |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0.5%** | **2 micros** | +$11,670.96 | +1.29% | **-$930.40** | **$4,725.02** | **SÍ (Al límite)** | **NO (Excede $2,000)** | **NO** | **NO (Excede $3,000)** |
| **1.0%** | **4 micros** | +$23,341.93 | +2.37% | **-$1,860.80** | **$9,450.04** | **NO (Quiebra)** | **NO (Quiebra)** | **NO** | **NO** |

> [!CAUTION]
> **DICTAMEN PARA PROP FIRMS TRAS EL FIX:**
> Aunque forzar la salida a las 15:45 ET logró reducir la pérdida máxima diaria a **-\$930.40 USD** (evitando la quiebra diaria inmediata en cuenta de \$50k a 0.5% de riesgo), el **Max Trailing Drawdown es de \$4,725.02 USD**, violando rotundamente el límite máximo de \$2,000 USD de una cuenta de \$50k y el de \$3,000 USD de una cuenta de \$100k. **La estrategia corregida sigue siendo NO APTA para prop firms**.

---

## 5. SUITE DE TESTS UNITARIOS DE CONFORMIDAD
Se implementó y verificó con éxito `test_no_trade_in_15m_crosses_moc_1545_when_configured` en [tests/test_intraday_audit_compliance.py](file:///C:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/tests/test_intraday_audit_compliance.py) (**6/6 tests pasando al 100%**):
- Se comprobó exhaustivamente sobre los datos históricos reales que, bajo la configuración corregida, ningún trade ejecutado en sesión regular permanece abierto después de las 15:45 ET.
