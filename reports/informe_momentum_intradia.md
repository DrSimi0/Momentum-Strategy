# Informe de Investigación Cuantitativa: Evaluación Rigurosa del Momentum Intradía en Futuros CME (ES y NQ)

**Proyecto:** Momentum Intradía (Gao, Han, Li y Zhou, *Journal of Financial Economics*, 2018)  
**Instrumentos:** E-mini S&P 500 (`ES.v.0`) y E-mini Nasdaq-100 (`NQ.v.0`)  
**Fuente de Datos:** Databento (`GLBX.MDP3`, `ohlcv-1m`)  
**Periodo Evaluado:** 2018-01-02 a 2026-10-19 (2,193 sesiones regulares de mercado)  
**Fecha de Publicación:** 2026-10-21  
**Estado:** **RECHAZADO (FAIL)** — El momentum intradía no genera alfa económico tras costos de transacción y no supera la prueba estadística en el holdout fuera de muestra.

---

## 1. Resumen Ejecutivo y Veredicto Final

En este estudio evaluamos con rigor econométrico si la estrategia de **momentum intradía** documentada por Gao, Han, Li y Zhou (2018) genera retornos económicamente explotables en los futuros del S&P 500 (**ES**) y Nasdaq-100 (**NQ**) en CME Globex. La hipótesis postula que el retorno de la primera media hora ($r_1$, desde el cierre previo hasta las 10:00 ET) o el de la penúltima media hora ($r_{12}$, 15:00 a 15:30 ET) predicen la dirección del retorno de la última media hora ($r_{13}$, 15:30 a 16:00 ET).

### Veredicto Global: **RECHAZADA (FAIL)**

Las 8 hipótesis primarias evaluadas sobre la partición final de prueba (*Holdout* estricto 2024–2026, 696 sesiones) resultaron **unánimemente rechazadas**:
1. **Significancia Estadística (A1):** Ninguna hipótesis logró significancia estadística bajo control de errores múltiples (FWER). Todos los p-valores ajustados por **Holm-Bonferroni** fueron de **$1.0000$** frente al umbral requerido de $\le 0.05$.
2. **Rendimiento Económico Neto (A2 & A3):** Todos los ratios de Sharpe netos anualizados en el caso base fueron **negativos** (oscilando entre **$-0.76$** y **$-0.12$**), incumpliendo el mínimo requerido de $+0.50$. En el caso de estrés, todas las hipótesis ampliaron sus pérdidas.
3. **Distribución frente al Azar (A4):** En las pruebas de permutación (10,000 réplicas), las señales reales no mostraron superioridad frente a asignaciones temporales puramente aleatorias ($p > 0.50$).

| Instrumento | Hipótesis | PnL Neto Holdout | Sharpe Neto Base | P-valor Holm (A1) | P-valor Permutación (A4) | Veredicto |
|---|---|---|---|---|---|---|
| **ES** | **H1 ($r_1$)** | -\$15,456 | -0.53 | 1.0000 | 0.6073 | **REJECTED** |
| **ES** | **H2 ($r_{12}$)** | -\$21,790 | -0.76 | 1.0000 | 0.7377 | **REJECTED** |
| **ES** | **H3 (Confluencia)** | -\$13,028 | -0.62 | 1.0000 | 0.7224 | **REJECTED** |
| **ES** | **H4 (Filtro Vol)** | -\$4,630 | -0.31 | 1.0000 | 0.5698 | **REJECTED** |
| **NQ** | **H1 ($r_1$)** | -\$2,445 | -0.21 | 1.0000 | 0.5726 | **REJECTED** |
| **NQ** | **H2 ($r_{12}$)** | -\$34,743 | -0.70 | 1.0000 | 0.8324 | **REJECTED** |
| **NQ** | **H3 (Confluencia)** | -\$15,939 | -0.58 | 1.0000 | 0.7991 | **REJECTED** |
| **NQ** | **H4 (Filtro Vol)** | +\$2,057 | -0.12 | 1.0000 | 0.5280 | **REJECTED** |

---

## 2. Metodología y Protocolo Científico Pre-registrado

Para prevenir el sobreajuste (*overfitting*), la fuga de futuro (*look-ahead bias*) y la manipulación de resultados (*p-hacking*), el proceso se ejecutó bajo un protocolo pre-registrado e inmutable:
1. **Congelamiento de Parámetros:** Especificación formal en `docs/PREREGISTRO.md` bajo el commit y tag de git inmutable `preregistro-congelado` antes de evaluar el Holdout.
2. **Candado de Holdout:** La partición final fue ejecutada exactamente una sola vez, creando el candado `reports/FINAL_RUN.lock`. Cualquier ejecución posterior sobre el holdout fue bloqueada por código.
3. **Control de Presupuesto:** La estimación inicial de Databento para 2011–2026 superaba los \$25.00 USD. De conformidad con las reglas del proyecto, se consultó al usuario y se aprobó acotar el estudio al periodo 2018–2026 mediante contratos continuos por volumen (`ES.v.0` y `NQ.v.0`), con un costo total auditado de **\$22.74 USD**.

### Particiones Temporales (Calendario XNYS)
- **Desarrollo (In-Sample):** 2018-01-02 a 2021-12-31 (999 sesiones).
- **Validación (Out-of-Sample preliminar):** 2022-01-01 a 2023-12-31 (498 sesiones).
- **Prueba Final (Holdout estricto):** 2024-01-01 a 2026-10-19 (696 sesiones).

---

## 3. Verificación de Integridad de Datos y Microestructura

- **Total Barras 1-minuto Procesadas:** 3,113,979 barras en ES y 3,114,103 barras en NQ.
- **Hashes Criptográficos SHA-256:**
  - `data/raw/ES.v.0_ohlcv_1m.parquet`: `dc36c2418a82d0d63077033282f0b45dd3d49a967abed96f200807a51efe24dd`
  - `data/raw/NQ.v.0_ohlcv_1m.parquet`: `ef81bd0b5060113cec8e8fb1c047ff4f0ffc5a14b649447d2fde4065705fd3e7`
- **Invariantes OHLCV:** Se verificó que ningún precio fuera $\le 0$, que $high \ge low$, volumen $\ge 0$ y monotonicidad temporal estricta.

### Validación Empírica de la Convención Temporal (`ts_event`)
Se analizó la distribución de volumen intradiario en hora de Nueva York (ET) confirmando que `ts_event` marca el inicio del intervalo:
- **09:30 ET:** Salto abrupto de volumen de apertura regular (de 2,598 contratos a las 09:29 a **12,617 contratos/min** a las 09:30).
- **15:59 ET:** Pico máximo diario correspondiente a la subasta de cierre de contado y MOC (*Market-on-Close*) con una media de **50,117 contratos/min**.
- En consecuencia, la entrada se ejecuta en el precio *open* de las 15:30 ET y la liquidación en el precio *close* de las 15:59 ET.

---

## 4. Modelo de Fricciones y Costos de Ejecución

Los contratos de futuros sobre índices bursátiles en CME Globex conllevan costos de comisión y deslizamiento en cada operación:
- **E-mini S&P 500 (ES):** Multiplicador = \$50/punto, Tick = 0.25 (\$12.50/tick).
  - *Caso Base:* 0.5 ticks deslizamiento por lado (\$12.50) + \$2.00 comisión por lado (\$4.00) = **\$16.50 por operación (ida y vuelta)**.
  - *Caso Estrés:* 1.0 tick deslizamiento por lado (\$25.00) + \$2.50 comisión por lado (\$5.00) = **\$30.00 por operación**.
- **E-mini Nasdaq-100 (NQ):** Multiplicador = \$20/punto, Tick = 0.25 (\$5.00/tick).
  - *Caso Base:* 0.5 ticks deslizamiento por lado (\$5.00) + \$2.00 comisión por lado (\$4.00) = **\$9.00 por operación**.
  - *Caso Estrés:* 1.0 tick deslizamiento por lado (\$10.00) + \$2.50 comisión por lado (\$5.00) = **\$15.00 por operación**.

---

## 5. Análisis Econométrico: Regresiones Predictivas Newey-West (HAC)

Se estimó la regresión predictiva lineal:
$$r_{13, t} = \alpha + \beta X_t + \epsilon_t$$
con errores estándar robustos a heterocedasticidad y autocorrelación (HAC, 5 rezagos).

| Partición | Instrumento | Predictor ($X_t$) | Coeficiente $\beta$ | Error Estándar | Estadístico $t$ | P-valor HAC |
|---|---|---|---|---|---|---|
| **Desarrollo (2018–2021)** | ES | $r_1$ | +0.0309 | 0.0506 | 0.61 | 0.5434 |
| **Desarrollo (2018–2021)** | ES | $r_{12}$ | +0.0279 | 0.1706 | 0.16 | 0.8705 |
| **Desarrollo (2018–2021)** | NQ | $r_1$ | +0.0631 | 0.0531 | 1.19 | 0.2353 |
| **Desarrollo (2018–2021)** | NQ | $r_{12}$ | +0.0831 | 0.1456 | 0.57 | 0.5681 |
| **Validación (2022–2023)** | ES | $r_1$ | -0.0132 | 0.0230 | -0.57 | 0.5659 |
| **Validación (2022–2023)** | ES | $r_{12}$ | +0.2272 | 0.0802 | 2.83 | 0.0046 |
| **Validación (2022–2023)** | NQ | $r_1$ | -0.0051 | 0.0182 | -0.28 | 0.7800 |
| **Validación (2022–2023)** | NQ | $r_{12}$ | +0.2173 | 0.0778 | 2.79 | 0.0052 |
| **Holdout (2024–2026)** | ES | $r_1$ | -0.0232 | 0.0186 | -1.25 | 0.2118 |
| **Holdout (2024–2026)** | ES | $r_{12}$ | +0.0021 | 0.0664 | 0.03 | 0.9750 |
| **Holdout (2024–2026)** | NQ | $r_1$ | -0.0116 | 0.0144 | -0.81 | 0.4196 |
| **Holdout (2024–2026)** | NQ | $r_{12}$ | +0.0310 | 0.0768 | 0.40 | 0.6862 |

### Diagnóstico Econométrico:
- **Inexistencia de predictibilidad lineal para $r_1$:** Tanto en Desarrollo como en Holdout, los coeficientes $\beta$ de la primera media hora fueron indistinguibles de cero ($p > 0.20$), e incluso adoptaron signo negativo en la muestra reciente.
- **Inestabilidad del predictor $r_{12}$:** Si bien $r_{12}$ mostró un $t$-stat aparente de $+2.8$ en el periodo de validación 2022–2023, en el Holdout final (2024–2026) su capacidad predictiva se evaporó por completo ($\beta = +0.0021, t = 0.03, p = 0.975$ en ES; $\beta = +0.0310, t = 0.40, p = 0.686$ en NQ). Esto demuestra que el patrón transitorio en 2022–2023 era espurio o propio del régimen inflacionario de ese bienio.

---

## 6. Descomposición del PnL y Destrucción por Fricciones

El backtesting reveló que incluso cuando una estrategia logra un PnL bruto marginalmente positivo (como H1 en NQ con +\$3,810 USD en holdout), los costos fijos acumulados (\$6,255 USD) arrastran el resultado final a territorio negativo (-\$2,445 USD).

En ES, el arrastre de costos fue determinante:
- **H1 (ES):** PnL Bruto = -\$4,038 USD | Costos = \$11,418 USD | **PnL Neto = -\$15,456 USD**.
- **H2 (ES):** PnL Bruto = -\$10,488 USD | Costos = \$11,302 USD | **PnL Neto = -\$21,790 USD**.

Los gráficos generados en `reports/figures/cumulative_pnl.png` y `reports/figures/costs_breakdown_holdout.png` ilustran con claridad la caída monótona del capital neto bajo todas las configuraciones primarias y exploratorias.

---

## 7. Razones del Fracaso de la Estrategia en Mercados Modernos

¿Por qué el hallazgo publicado en el *JFE* (2018) con datos de 1993 a 2013 no es rentable en 2018–2026?
1. **Arbitraje y Eficiencia de Microestructura:** La anomalía reportada por Gao et al. se basaba en la digestión diferida de flujos de noticias de la apertura. En la última década, la proliferación de creadores de mercado algorítmicos y el volumen institucional en la subasta de cierre de CME han eliminado cualquier rezago informativo predecible.
2. **Impacto Desproporcionado de Costos en Temporalidad Corta (30 min):** Capturar un spread de solo 30 minutos significa que la relación señal/ruido es extraordinariamente baja. Pagar medio tick de deslizamiento y comisiones de ida y vuelta en cada trade de 30 minutos requiere una ventaja teórica masiva para alcanzar rentabilidad neta; ventaja que el mercado no ofrece.
3. **Efecto de Rebalanceo Neutralizador en el Cierre:** El flujo de fin de sesión está dominado por rebalanceos de fondos indexados y ETF pasivos (órdenes MOC/LOC). Estos flujos obedecen a objetivos de minimización de *tracking error* y liquidez, no a momentum respecto a la primera media hora de la mañana.

---

## 8. Conclusión Final

La hipótesis de **momentum intradía entre la primera y la última media hora en futuros ES y NQ no tiene soporte empírico fuera de muestra en el mercado actual**. Su aplicación práctica destruye capital sistemáticamente debido a la ausencia de edge direccional neto y a la acumulación implacable de costos transaccionales.

El protocolo pre-registrado se ejecutó de extremo a extremo sin intervenciones discrecionales, respetando el candado de holdout y documentando con honestidad los resultados negativos tal como exige la investigación cuantitativa seria.

---
*Archivo de resultados auditables: `reports/results.json`*  
*Registro de decisiones metodológicas: `docs/DECISIONS.md`*  
*Protocolo inmutable: `docs/PREREGISTRO.md`*
