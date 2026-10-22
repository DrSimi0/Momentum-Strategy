# Informe Final de Investigación Cuantitativa: Evaluación Rigurosa Pre-registrada de la Estrategia SMA + MACD + RSI

**Instrumentos Evaluados:**
- Futuros CME: E-mini S&P 500 (`ES.v.0`) y E-mini Nasdaq-100 (`NQ.v.0`) — Histórico Continuo 2010–2026 (16.36 años)
- Criptoactivos Perpetuos: Bitcoin (`BTC-USDT`) y Ethereum (`ETH-USDT`) — Histórico BingX 2022–2026 (4.1 años, universo exploratorio)  
**Timeframe:** 4 horas (4h)  
**Protocolo:** 60% Entrenamiento, 20% Validación, 20% Holdout Estrictamente Bloqueado  
**Espacio Paramétrico Pre-registrado:** Exactamente 32 combinaciones por activo  
**Fecha de Emisión:** 2026-10-21  
**Veredicto Final:** **REJECTED (NO APROBADA)** — Ninguno de los activos superó los criterios objetivos de aceptación en el Holdout fuera de muestra.

---

## 1. Resumen Ejecutivo y Veredicto Final

Siguiendo el protocolo inmutable congelado en [`PREREGISTRO.md`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/PREREGISTRO.md), se evaluó de forma rigurosa si la estrategia de confluencia técnica **SMA + MACD + RSI + ATR** posee una ventaja estadística (*edge*) real y reproducible.

### Veredicto Global: **REJECTED (FAIL)**
La estrategia fracasa de manera concluyente en el periodo de Holdout final (2023–2026 en futuros; 2025–2026 en cripto) bajo condiciones reales de ejecución:
1. **Rendimiento Negativo Fuera de Muestra:** A pesar de mostrar ratios de Sharpe atractivos en Validación (+2.82 en ES y +3.96 en NQ), ambas estrategias entraron en pérdidas netas en el Holdout final: **-\$16,118.40 USD** en ES (Sharpe -0.52) y **-\$2,862.69 USD** en NQ (Sharpe -0.20).
2. **Fracaso en Robustez Temporal (Walk-Forward):** En las 14 ventanas rodantes fuera de muestra (3 años entrenamiento / 1 año prueba), la tasa de ventanas positivas fue de apenas el **35.7% en ES** y **42.9% en NQ**, muy por debajo del umbral mínimo pre-registrado del 60%.
3. **Pérdida frente al Buy & Hold:** Durante el mismo periodo de holdout, la tenencia pasiva generó **+\$160,362 USD (+70.7%)** en ES y **+\$280,735 USD (+89.3%)** en NQ.
4. **Deflated Sharpe Ratio (DSR):** Ajustado por las 32 combinaciones pre-registradas, el DSR se ubicó en **0.12% en ES** y **0.18% en NQ**, demostrando que el rendimiento de validación fue producto del azar y la selección sobreajustada.

---

## 2. Tabla de Resultados Auditados en el Holdout (20% Fuera de Muestra)

| Activo | Configuración Elegida en Validación | Trades Holdout | Tasa Acierto | Profit Factor | Expectativa / Trade | PnL Neto Holdout | Sharpe Holdout | Tiempo Expuesto | Buy & Hold PnL | Sharpe Solo-SMA | WF Ventanas Positivas | Deflated Sharpe (DSR) | Veredicto |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **ES (S&P 500)** | 3 SMAs (20/100/200), MACD(16,35), k=3.0, m=2.0 | 46 | 30.4% | 0.89 | -\$350.40 | **-\$16,118.40** | **-0.52** | 32.1% | +\$160,362 (+70.7%) | -1.39 | 35.7% (14 vent.) | **0.12%** | **REJECTED** |
| **NQ (Nasdaq)** | 3 SMAs (30/100/150), MACD(16,35), k=2.0, m=2.0 | 68 | 29.4% | 0.99 | -\$42.10 | **-\$2,862.69** | **-0.20** | 25.6% | +\$280,735 (+89.3%) | -1.83 | 42.9% (14 vent.) | **0.18%** | **REJECTED** |
| **BTC-USDT** | 2 SMAs (30/200), MACD(12,26), k=2.0, m=2.0 | 32 | 31.2% | 0.84 | -\$29.33 | **-\$938.40** | **-1.30** | 33.3% | -\$416.00 (-4.2%) | +1.47 | 0.0% (3 vent.) | **0.08%** | **REJECTED** |
| **ETH-USDT** | 2 SMAs (20/150), MACD(12,26), k=2.0, m=2.0 | 38 | 34.2% | 0.90 | -\$22.29 | **-\$847.10** | **-0.73** | 36.2% | -\$1,561.69 (-15.6%) | +1.66 | 100.0% (2 vent.) | **0.11%** | **REJECTED** |

---

## 3. Contabilidad de Pruebas y Mitigación del P-Hacking

* **Reducción del Espacio de Búsqueda:** Se redujo el espacio paramétrico de más de 1,890 combinaciones exploratorias a una grilla cerrada de **exactamente 32 combinaciones por activo**:
  * 8 arquitecturas SMA (4 variantes de 2 SMAs y 4 de 3 SMAs).
  * 2 variantes MACD: Estándar (12, 26, 9) y Lento (16, 35, 9).
  * 1 filtro RSI fijo: periodo 14.
  * 2 niveles de Stop Loss ATR: $k \in \{2.0, 3.0\}$.
  * 1 nivel de Take Profit fijo: $m = 2.0$.
  * Total: $8 \times 2 \times 1 \times 2 \times 1 = 32$ combinaciones.
* **Aislamiento Físico del Holdout:** La partición final del 20% se separó en `data/locked_holdout/` con hash SHA-256 inmutable y ningún script de optimización tuvo acceso a ella hasta la evaluación final única.

---

## 4. Análisis de Estabilidad Multirégimen (2010 a 2026)

Se evaluó la estabilidad de las 32 combinaciones en tres regímenes macroeconómicos históricos:
* **Régimen 1 (2010–2016):** Expansión monetaria cuantitativa (QE), tasas en cero (ZIRP) y baja volatilidad.
* **Régimen 2 (2017–2020):** Guerra comercial, tensiones geopolíticas y shock pandémico Covid-19.
* **Régimen 3 (2021–2026):** Ciclo inflacionario, alza abrupta de tasas de interés y concentración en megacapitalizaciones tecnológicas.

**Hallazgo:** Los mapas de calor multirégimen ([`regime_stability_ES.png`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/figures/regime_stability_ES.png) y [`regime_stability_NQ.png`](file:///c:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/figures/regime_stability_NQ.png)) demuestran que las configuraciones que generaron rendimientos positivos en un régimen sufren pérdidas severas en los otros dos. No existe una combinación de SMAs, MACD y RSI que mantenga estabilidad a lo largo de ciclos monetarios cambiantes.

---

## 5. Diseño Metodológico de Cartera: Volatility Targeting (No Implementada)

De acuerdo con el mandato de pre-registro, **la cartera multiactivo NO se ensambla para producción**, ya que ninguno de los activos base demostró edge predictivo independiente. Crear una cartera combinada sobre estrategias perdedoras solo diversifica pérdidas netas.

Para fines académicos, se documenta la metodología formal de dimensionamiento por **Objetivo de Volatilidad (*Volatility Targeting*)** sin factores arbitrarios:
1. **Volatilidad Objetivo:** Se fija una volatilidad anualizada idéntica para cada sleeve: $\sigma_{\text{target}} = 10\%$ anual.
2. **Ponderación Inversa a la Volatilidad Real:**
   $$w_i = \frac{\sigma_{\text{target}}}{\hat{\sigma}_i \times \sqrt{252}}$$
   Donde $\hat{\sigma}_i$ es la desviación estándar de los retornos diarios observada en una ventana móvil de 60 días.
3. **Escalamiento de Contratos:** El número de contratos de futuros y unidades de criptoactivos se dimensiona diariamente para que el riesgo en dólares de un movimiento de $1\sigma$ sea estrictamente equivalente entre el sleeve de futuros y el de cripto.

---

## 6. Lista de Limitaciones del Estudio

1. **Retardo Estructural de los Indicadores Técnicos Clásicos:** Las medias móviles simples y el histograma del MACD reaccionan con desfase (*lag*) frente a movimientos bruscos del precio, comprando cerca de los máximos de oscilación y vendiendo cerca de los mínimos locales.
2. **Asimetría de Costos en Estrategias de Frecuencia Media:** Con una tasa de acierto del 29% al 34%, el impacto de comisiones continuas y deslizamiento (*slippage*) de 1 tick por contrato en futuros destruye el factor de beneficio en mercados que consolidan lateralmente.
3. **Profundidad Histórica Dispar:** Los futuros CME cuentan con 16.36 años continuos de ticks reales, mientras que los contratos perpetuos de BingX solo existen desde septiembre de 2022 (4.1 años), limitando la significancia temporal del análisis en criptomonedas.
4. **Sesgo de Selección Evitado:** Al no permitir el ajuste de parámetros tras observar el holdout, se preservó la honestidad científica y se evitó la trampa del sobreajuste que hacía parecer rentable a la versión exploratoria previa.

---

## 7. Conclusión Definitiva

La hipótesis de investigación queda **RECHAZADA**. La estrategia técnica de confluencia SMA + MACD + RSI en velas de 4 horas no presenta robustez estadística suficiente para justificar su despliegue con capital real en futuros de índices CME ni en criptoactivos.
