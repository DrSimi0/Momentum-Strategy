# Informe Final de Investigación Cuantitativa: Veredicto del Holdout Bloqueado (2010–2017)

**Instrumentos Evaluados:**
- E-mini S&P 500 (`ES.v.0`) y E-mini Nasdaq-100 (`NQ.v.0`) en Futuros CME (CME Globex)
- **Periodo de Desarrollo:** `2017-12-15` a `2026-10-19` (Train 2017–2024, Validación 2024–2026, datos ya vistos)
- **Periodo de Holdout Bloqueado:** `2010-06-07` a `2017-12-15` (**7.5 años de datos totalmente vírgenes**)
- **Timeframe:** 4 horas (4h)
- **Fecha de Emisión:** 2026-10-21  
- **Veredicto Definitivo:** **REJECTED (FAIL)** — Ambas configuraciones finalistas fracasaron categóricamente en el Holdout fuera de muestra.

---

## 1. Resumen Ejecutivo y Veredicto Final

En estricto cumplimiento del protocolo pre-registrado congelado en [`PREREGISTRO.md`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/PREREGISTRO.md), se evaluaron las dos configuraciones finalistas seleccionadas imparcialmente durante la fase de desarrollo (2017–2026) sobre el **Holdout Bloqueado de 7.5 años (2010 a 2017)**.

### Veredicto Global: **REJECTED (NO APROBADA)**
Ambas estrategias entran en pérdidas severas y sistemáticas en el periodo virgen de prueba:
1. **Pérdidas Netas Severas:** 
   - **ES:** Pérdida neta de **-\$39,519.56 USD** (Sharpe anualizado de **-2.70**).
   - **NQ:** Pérdida neta de **-\$27,581.67 USD** (Sharpe anualizado de **-1.88**).
2. **Incumplimiento de Criterios de Riesgo:**
   - En ES, el Drawdown Máximo alcanzó los **\$48,012.69 USD** (**48.0%** del capital base de \$100k USD), violando holgadamente el límite pre-registrado del $\le 20\%$.
   - En NQ, el Drawdown Máximo alcanzó los **\$32,663.61 USD** (**21.8%** del capital base de \$150k USD).
3. **Muestra Estadística Robusta ($N \ge 100$):**
   - El criterio de muestra se cumplió ampliamente: **169 trades en ES** y **114 trades en NQ**, confirmando que el fallo **no es atribuible a falta de observaciones**, sino a la ausencia intrínseca de una ventaja estadística (*edge*).
4. **Colapso frente a Buy & Hold:**
   - Durante este mismo periodo de 7.5 años, la tenencia pasiva generó **+\$81,300 USD (+153.8%)** en ES y **+\$93,590 USD (+257.0%)** en NQ.
5. **Deflated Sharpe Ratio (DSR = 0.00%):** Con Sharpes fuertemente negativos, la probabilidad de que el rendimiento observado sea estadísticamente superior a cero es del 0.00%.

---

## 2. Tabla de Resultados Auditados en el Holdout Bloqueado (2010 a 2017)

| Métrica Pre-registrada | Criterio de Aceptación | Resultado ES (`ES.v.0`) | Resultado NQ (`NQ.v.0`) | Estado de Cumplimiento |
|---|:---:|:---:|:---:|:---:|
| **Configuración Finalista** | Pre-fijada en Val | 3 SMAs (30/100/200), MACD(16,35), k=2.0, m=2.0 | 3 SMAs (30/100/200), MACD(16,35), k=3.0, m=2.0 | — |
| **Número de Operaciones ($N$)** | $\ge 100$ trades | **169 trades** | **114 trades** | **CUMPLIDO** (Muestra suficiente) |
| **Tasa de Acierto (Win Rate)** | — | 24.3% (41 ganadoras / 128 perdedoras) | 30.7% (35 ganadoras / 79 perdedoras) | Muy baja |
| **Factor de Beneficio (Profit Factor)** | $\ge 1.30$ | **0.61** | **0.72** | **INCUMPLIDO** (< 1.0) |
| **Expectativa por Operación** | $> \$0.00$ | **-\$233.84 USD / trade** | **-\$241.94 USD / trade** | **INCUMPLIDO** (Expectativa negativa) |
| **Resultado Neto Acumulado** | $> \$0.00$ | **-\$39,519.56 USD** | **-\$27,581.67 USD** | **INCUMPLIDO** (Pérdidas severas) |
| **Sharpe Ratio Anualizado ($\sqrt{252}$)** | $\ge 1.00$ | **-2.70** | **-1.88** | **INCUMPLIDO** (Fuertemente negativo) |
| **Drawdown Máximo Relativo** | $\le 20.0\%$ | **48.0%** (-\$48,012.69 de \$100k) | **21.8%** (-\$32,663.61 de \$150k) | **INCUMPLIDO** (Riesgo inaceptable) |
| **Intervalo Confianza Sharpe 95% (Bootstrap)** | $> 0.0$ | `[-6.49, -0.06]` | `[-4.89, +0.87]` | **INCUMPLIDO** |
| **Deflated Sharpe Ratio (DSR, M=32)** | $\ge 95.0\%$ | **0.00%** | **0.00%** | **INCUMPLIDO** |
| **Resultado Línea Base Buy & Hold** | — | +\$81,300.00 (+153.8%) | +\$93,590.00 (+257.0%) | Buy & Hold superior |
| **Resultado Línea Base Solo-SMA** | — | -\$81,021.63 (Sharpe -2.01) | -\$57,335.97 (Sharpe -1.89) | Ambas destruyen capital |
| **VEREDICTO FINAL** | Todos cumplidos | **REJECTED (FAIL)** | **REJECTED (FAIL)** | **NO APROBADA** |

---

## 3. Diagnóstico Técnico del Fracaso Fuera de Muestra

1. **La Ilusión del Desarrollo (2017–2026):**
   * Durante la fase de desarrollo reciente (2017 a 2026), el mercado estuvo marcado por una fuerte tendencia alcista alimentada por estímulos fiscales y el auge tecnológico, lo cual infló artificialmente los Sharpes de validación (+1.85 en ES y +4.20 en NQ).
   * Al enfrentar el régimen del Holdout (2010 a 2017) —caracterizado por correcciones recurrentes, rangos de consolidación post-crisis de 2011 y 2015-2016—, la estrategia generó señales tardías en techos locales y liquidó en fondos por el stop loss ATR.
2. **La Salida por Cruce Contrario de SMAs y ATR Whipsaws:**
   * La combinación de stop loss ajustado ($k \in \{2.0, 3.0\}$) con reversión de SMAs liquidó el 75.7% de las operaciones de ES con pérdidas.
3. **Criptoactivos (BTC y ETH):**
   * En el universo exploratorio descriptivo, Bitcoin arrojó Sharpe negativo (-0.35) en validación y ninguno superó el filtro de 100 operaciones independientes. No tienen cabida en una cartera.

---

## 4. Conclusión Final y Lección Metodológica

El protocolo pre-registrado ha demostrado su efectividad como salvaguarda contra el autoengaño:
* Una estrategia que "parecía excelente" en datos vistos recientemente (2024–2026) demostró ser un destructor masivo de capital cuando fue confrontada con 7.5 años de datos reales fuera de muestra.
* **La estrategia SMA + MACD + RSI queda formalmente RECHAZADA.**
* Queda operativo en [`scripts/forward_test_signal_generator.py`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/scripts/forward_test_signal_generator.py) el generador de señales diarias para registrar cualquier comportamiento a futuro sin arriesgar capital real.
