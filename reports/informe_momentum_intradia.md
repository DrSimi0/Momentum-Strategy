# Informe de Investigación Cuantitativa: Evaluación Rigurosa del Momentum Intradía en Futuros CME (ES y NQ)

**Proyecto:** Momentum Intradía en la Sesión Regular de EE.UU. (Gao, Han, Li y Zhou, *Journal of Financial Economics*, 2018)  
**Instrumentos:** E-mini S&P 500 (`ES.v.0`) y E-mini Nasdaq-100 (`NQ.v.0`)  
**Fuente de Datos:** Databento (`GLBX.MDP3`, esquema `ohlcv-1m`)  
**Periodo Evaluado:** 2018-01-02 a 2026-10-19 (2,193 sesiones regulares de mercado)  
**Fecha de Publicación:** 2026-10-21  
**Estado:** **RECHAZADO (FAIL)** — El momentum intradía no genera alfa económico neto y no supera la prueba estadística en el holdout fuera de muestra.

---

## 1. Resumen Ejecutivo y Veredicto Final

En este estudio evaluamos con rigor econométrico si la estrategia de **momentum intradía** documentada por Gao, Han, Li y Zhou (2018) genera retornos económicamente explotables en los futuros del S&P 500 (**ES**) y Nasdaq-100 (**NQ**) en CME Globex. La hipótesis postula que el retorno de la primera media hora ($r_1$, desde el cierre previo hasta las 10:00 ET) o el de la penúltima media hora ($r_{12}$, 15:00 a 15:30 ET) predicen la dirección del retorno de la última media hora ($r_{13}$, 15:30 a 16:00 ET).

### Veredicto Global: **RECHAZADA (FAIL)**

Las 8 hipótesis primarias evaluadas sobre la partición final de prueba (*Holdout* estricto 2024–2026, 696 sesiones) resultaron **unánimemente rechazadas**:
1. **Significancia Estadística (A1):** Ninguna hipótesis logró significancia estadística bajo control de errores múltiples (FWER). Todos los p-valores ajustados por **Holm-Bonferroni** fueron de **$1.0000$** frente al umbral requerido de $\le 0.05$.
2. **Rendimiento Económico Neto (A2 & A3):** Todos los ratios de Sharpe netos anualizados en el caso base fueron **negativos** (oscilando entre **$-0.76$** y **$-0.12$**), incumpliendo el mínimo requerido de $+0.50$. En el caso de estrés, todas las hipótesis ampliaron sus pérdidas.
3. **Distribución frente al Azar (A4):** En las pruebas de permutación (10,000 réplicas), las señales reales no mostraron superioridad frente a asignaciones temporales puramente aleatorias ($p > 0.50$).

### Tabla Resumen de Criterios de Aceptación en Holdout (2024–2026)

| Instrumento | Hipótesis | PnL Neto Holdout | Sharpe Neto Base | A1 (Holm adj $p \le 0.05$) | A2 (Sharpe $\ge 0.50$) | A3 (Estrés $> 0$) | A4 (Permutación $\le 0.05$) | A6 (Años Positivos $\ge 50\%$) | Veredicto |
|---|---|---|---|---|---|---|---|---|---|
| **ES** | **H1 ($r_1$)** | -\$15,456 | -0.53 | 1.0000 (Falla) | -0.53 (Falla) | -0.85 (Falla) | 0.6073 (Falla) | 0.0% (Falla) | **REJECTED** |
| **ES** | **H2 ($r_{12}$)** | -\$21,790 | -0.76 | 1.0000 (Falla) | -0.76 (Falla) | -1.08 (Falla) | 0.7377 (Falla) | 0.0% (Falla) | **REJECTED** |
| **ES** | **H3 (Confluencia)** | -\$13,028 | -0.62 | 1.0000 (Falla) | -0.62 (Falla) | -0.85 (Falla) | 0.7224 (Falla) | 0.0% (Falla) | **REJECTED** |
| **ES** | **H4 (Filtro Vol)** | -\$4,630 | -0.31 | 1.0000 (Falla) | -0.31 (Falla) | -0.47 (Falla) | 0.5698 (Falla) | 33.3% (Falla) | **REJECTED** |
| **NQ** | **H1 ($r_1$)** | -\$2,445 | -0.21 | 1.0000 (Falla) | -0.21 (Falla) | -0.29 (Falla) | 0.5726 (Falla) | 33.3% (Falla) | **REJECTED** |
| **NQ** | **H2 ($r_{12}$)** | -\$34,743 | -0.70 | 1.0000 (Falla) | -0.70 (Falla) | -0.78 (Falla) | 0.8324 (Falla) | 0.0% (Falla) | **REJECTED** |
| **NQ** | **H3 (Confluencia)** | -\$15,939 | -0.58 | 1.0000 (Falla) | -0.58 (Falla) | -0.64 (Falla) | 0.7991 (Falla) | 33.3% (Falla) | **REJECTED** |
| **NQ** | **H4 (Filtro Vol)** | +\$2,057 | -0.12 | 1.0000 (Falla) | -0.12 (Falla) | -0.17 (Falla) | 0.5280 (Falla) | 66.7% (Cumple) | **REJECTED** |

---

## 2. Comparación con los Números del Paper Original (Gao et al., 2018)

| Dimensión | Gao, Han, Li y Zhou (*JFE* 2018) | Este Estudio Cuantitativo (2026) |
|---|---|---|
| **Instrumento** | ETF SPY (mercado de contado) | Futuros E-mini S&P 500 (ES) y Nasdaq-100 (NQ) |
| **Periodo de Datos** | 1993 a 2013 (21 años históricos) | 2018 a 2026 (8.8 años modernos en Globex) |
| **Frecuencia / Barras** | Barras intradía consolidadas TAQ | Barras 1-minuto con libro MDP3 de Databento |
| **Retorno Anualizado** | ~6.67% anual (estrategia timing $r_1$) | Negativo en todos los instrumentos (-1.8% a -5.4% s/nocional) |
| **Sharpe Ratio** | **+1.08** (antes de costos modernos) | **-0.53 en ES** y **-0.21 en NQ** (neto de costos base) |
| **Costos de Transacción** | Asumen fricciones despreciables en SPY | Modelo explícito de comisiones y deslizamiento real en futuros |
| **Veredicto Moderno** | Reportan anomalía persistente | **La anomalía ha decaído o fue completamente arbitrada** |

---

## 3. Metodología y Protocolo Científico Pre-registrado

Para prevenir el sobreajuste (*overfitting*), la fuga de futuro (*look-ahead bias*) y la manipulación de resultados (*p-hacking*), el proceso se ejecutó bajo un protocolo pre-registrado e inmutable:
1. **Congelamiento de Parámetros:** Especificación formal en `docs/PREREGISTRO.md` bajo el commit y tag de git inmutable `preregistro-congelado` antes de evaluar el Holdout.
2. **Candado de Holdout:** La partición final fue ejecutada exactamente una sola vez, creando el candado `reports/FINAL_RUN.lock`. Cualquier ejecución posterior sobre el holdout fue bloqueada por código.
3. **Control de Presupuesto:** La estimación inicial de Databento para 2011–2026 superaba los \$25.00 USD. De conformidad con las reglas del proyecto, se consultó al usuario y se aprobó acotar el estudio al periodo 2018–2026 mediante contratos continuos por volumen (`ES.v.0` y `NQ.v.0`), con un costo total auditado de **\$22.74 USD**.

### Particiones Temporales (Calendario XNYS)
- **Desarrollo (In-Sample):** 2018-01-02 a 2021-12-31 (999 sesiones).
- **Validación (Out-of-Sample preliminar):** 2022-01-01 a 2023-12-31 (498 sesiones).
- **Prueba Final (Holdout estricto):** 2024-01-01 a 2026-10-19 (696 sesiones).

---

## 4. Verificación de Integridad de Datos y Microestructura

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

## 5. Modelo de Fricciones y Costos de Ejecución

Los contratos de futuros sobre índices bursátiles en CME Globex conllevan costos de comisión y deslizamiento en cada operación:
- **E-mini S&P 500 (ES):** Multiplicador = \$50/punto, Tick = 0.25 (\$12.50/tick).
  - *Caso Base:* 0.5 ticks deslizamiento por lado (\$12.50) + \$2.00 comisión por lado (\$4.00) = **\$16.50 por operación (ida y vuelta)**.
  - *Caso Estrés:* 1.0 tick deslizamiento por lado (\$25.00) + \$2.50 comisión por lado (\$5.00) = **\$30.00 por operación**.
- **E-mini Nasdaq-100 (NQ):** Multiplicador = \$20/punto, Tick = 0.25 (\$5.00/tick).
  - *Caso Base:* 0.5 ticks deslizamiento por lado (\$5.00) + \$2.00 comisión por lado (\$4.00) = **\$9.00 por operación**.
  - *Caso Estrés:* 1.0 tick deslizamiento por lado (\$10.00) + \$2.50 comisión por lado (\$5.00) = **\$15.00 por operación**.

---

## 6. Resultados Comparativos en las Tres Etapas (Brutos y Netos)

### E-mini S&P 500 (ES)

| Partición | Hipótesis | Trades | PnL Bruto (USD) | Costos (USD) | PnL Neto (USD) | Retorno Medio Neto / Trade | Tasa Acierto | Sharpe Neto Anualizado |
|---|---|---|---|---|---|---|---|---|
| **Desarrollo (2018–2021)** | H1 | 994 | -\$8,825 | \$16,401 | -\$25,226 | -\$25.38 | 45.4% | -0.78 |
| **Desarrollo (2018–2021)** | H2 | 988 | +\$22,662 | \$16,302 | +\$6,360 | +\$6.44 | 48.5% | +0.22 |
| **Desarrollo (2018–2021)** | H3 | 508 | +\$5,462 | \$8,382 | -\$2,920 | -\$5.75 | 45.9% | -0.10 |
| **Desarrollo (2018–2021)** | H4 | 362 | -\$6,500 | \$5,973 | -\$12,473 | -\$34.46 | 42.5% | -0.52 |
| **Desarrollo (2018–2021)** | B1 | 999 | -\$7,075 | \$16,484 | -\$23,559 | -\$23.58 | 46.2% | -0.73 |
| **Validación (2022–2023)** | H1 | 496 | -\$1,562 | \$8,184 | -\$9,746 | -\$19.65 | 49.4% | -0.42 |
| **Validación (2022–2023)** | H2 | 495 | +\$16,812 | \$8,168 | +\$8,645 | +\$17.46 | 49.9% | +0.37 |
| **Validación (2022–2023)** | H3 | 258 | +\$9,312 | \$4,257 | +\$5,055 | +\$19.60 | 50.4% | +0.22 |
| **Validación (2022–2023)** | H4 | 203 | -\$4,875 | \$3,350 | -\$8,225 | -\$40.51 | 49.7% | -0.45 |
| **Validación (2022–2023)** | B1 | 498 | -\$3,188 | \$8,217 | -\$11,405 | -\$22.90 | 47.6% | -0.49 |
| **Holdout (2024–2026)** | H1 | 692 | -\$4,038 | \$11,418 | -\$15,456 | -\$22.33 | 48.0% | -0.53 |
| **Holdout (2024–2026)** | H2 | 685 | -\$10,488 | \$11,302 | -\$21,790 | -\$31.81 | 46.6% | -0.76 |
| **Holdout (2024–2026)** | H3 | 357 | -\$7,138 | \$5,890 | -\$13,028 | -\$36.49 | 45.7% | -0.62 |
| **Holdout (2024–2026)** | H4 | 270 | -\$175 | \$4,455 | -\$4,630 | -\$17.15 | 48.5% | -0.31 |
| **Holdout (2024–2026)** | B1 | 696 | +\$1,200 | \$11,484 | -\$10,284 | -\$14.78 | 49.3% | -0.23 |

### E-mini Nasdaq-100 (NQ)

| Partición | Hipótesis | Trades | PnL Bruto (USD) | Costos (USD) | PnL Neto (USD) | Retorno Medio Neto / Trade | Tasa Acierto | Sharpe Neto Anualizado |
|---|---|---|---|---|---|---|---|---|
| **Desarrollo (2018–2021)** | H1 | 997 | +\$14,460 | \$8,973 | +\$5,487 | +\$5.50 | 51.2% | +0.13 |
| **Desarrollo (2018–2021)** | H2 | 994 | +\$24,670 | \$8,946 | +\$15,724 | +\$15.82 | 49.5% | +0.39 |
| **Desarrollo (2018–2021)** | H3 | 513 | +\$22,170 | \$4,617 | +\$17,553 | +\$34.22 | 51.5% | +0.43 |
| **Desarrollo (2018–2021)** | H4 | 362 | +\$6,960 | \$3,258 | +\$3,702 | +\$10.23 | 50.0% | +0.10 |
| **Desarrollo (2018–2021)** | B1 | 999 | -\$5,570 | \$8,991 | -\$14,561 | -\$14.58 | 49.9% | -0.36 |
| **Validación (2022–2023)** | H1 | 496 | -\$24,400 | \$4,464 | -\$28,864 | -\$58.20 | 47.8% | -1.10 |
| **Validación (2022–2023)** | H2 | 496 | +\$22,660 | \$4,464 | +\$18,196 | +\$36.69 | 49.8% | +0.69 |
| **Validación (2022–2023)** | H3 | 259 | -\$1,890 | \$2,331 | -\$4,221 | -\$16.30 | 48.3% | -0.16 |
| **Validación (2022–2023)** | H4 | 203 | -\$15,080 | \$1,827 | -\$16,907 | -\$83.28 | 48.3% | -0.63 |
| **Validación (2022–2023)** | B1 | 498 | -\$1,120 | \$4,482 | -\$5,602 | -\$11.25 | 46.8% | -0.21 |
| **Holdout (2024–2026)** | H1 | 695 | +\$3,810 | \$6,255 | -\$2,445 | -\$3.52 | 48.5% | -0.21 |
| **Holdout (2024–2026)** | H2 | 692 | -\$28,515 | \$6,228 | -\$34,743 | -\$50.21 | 47.7% | -0.70 |
| **Holdout (2024–2026)** | H3 | 361 | -\$12,690 | \$3,249 | -\$15,939 | -\$44.15 | 47.1% | -0.58 |
| **Holdout (2024–2026)** | H4 | 307 | +\$4,820 | \$2,763 | +\$2,057 | +\$6.70 | 48.2% | -0.12 |
| **Holdout (2024–2026)** | B1 | 696 | +\$11,200 | \$6,264 | +\$4,936 | +\$7.09 | 51.4% | +0.19 |

---

## 7. Análisis Econométrico: Regresiones Predictivas Newey-West (HAC)

Se estimó la regresión predictiva lineal:
$$r_{13, t} = \alpha + \beta X_t + \epsilon_t$$
con errores estándar robustos a heterocedasticidad y autocorrelación (HAC, 5 rezagos).

| Partición | Instrumento | Predictor ($X_t$) | Coeficiente $\beta$ | Error Estándar | Estadístico $t$ | P-valor HAC | $R^2$ OOS (Campbell-Thompson) |
|---|---|---|---|---|---|---|---|
| **Desarrollo (2018–2021)** | ES | $r_1$ | +0.0309 | 0.0506 | 0.61 | 0.5434 | - |
| **Desarrollo (2018–2021)** | ES | $r_{12}$ | +0.0279 | 0.1706 | 0.16 | 0.8705 | - |
| **Desarrollo (2018–2021)** | NQ | $r_1$ | +0.0631 | 0.0531 | 1.19 | 0.2353 | - |
| **Desarrollo (2018–2021)** | NQ | $r_{12}$ | +0.0831 | 0.1456 | 0.57 | 0.5681 | - |
| **Validación (2022–2023)** | ES | $r_1$ | -0.0132 | 0.0230 | -0.57 | 0.5659 | - |
| **Validación (2022–2023)** | ES | $r_{12}$ | +0.2272 | 0.0802 | 2.83 | 0.0046 | - |
| **Validación (2022–2023)** | NQ | $r_1$ | -0.0051 | 0.0182 | -0.28 | 0.7800 | - |
| **Validación (2022–2023)** | NQ | $r_{12}$ | +0.2173 | 0.0778 | 2.79 | 0.0052 | - |
| **Holdout (2024–2026)** | ES | $r_1$ | -0.0232 | 0.0186 | -1.25 | 0.2118 | -0.0049 (Falla) |
| **Holdout (2024–2026)** | ES | $r_{12}$ | +0.0021 | 0.0664 | 0.03 | 0.9750 | -0.0321 (Falla) |
| **Holdout (2024–2026)** | NQ | $r_1$ | -0.0116 | 0.0144 | -0.81 | 0.4196 | -0.0031 (Falla) |
| **Holdout (2024–2026)** | NQ | $r_{12}$ | +0.0310 | 0.0768 | 0.40 | 0.6862 | -0.0278 (Falla) |

> **Conclusión del $R^2$ fuera de muestra:** En todas las especificaciones, el $R^2_{OOS}$ de Campbell-Thompson fue estrictamente negativo ($< 0$), lo que demuestra empíricamente que pronosticar con la media histórica simple supera al modelo de regresión de momentum.

---

## 8. Diagnósticos Avanzados: Deciles, Breakeven y Estacionalidad

### 8.1 Retorno de $r_{13}$ por Deciles de $r_1$ (Holdout 2024–2026)
Si el momentum intradía fuese válido, los deciles más altos de $r_1$ (decil 10) deberían generar retornos promedio de $r_{13}$ significativamente superiores a los deciles bajos (decil 1).
- **ES:** Decil 1 (más negativo) promedió **+2.41 bps**, mientras que el Decil 10 (más positivo) promedió **-1.54 bps**.
- **NQ:** Decil 1 promedió **+1.98 bps**, mientras que el Decil 10 promedió **+0.82 bps**.
*No existe monotonicidad ascendente.* De hecho, en ES el decil más alcista de la mañana cerró la tarde con pendiente negativa, contradiciendo frontalmente la hipótesis de Gao et al.

### 8.2 Costo de Equilibrio (*Breakeven Cost per Trade*)
Calculamos el costo total máximo por operación (comisión + deslizamiento) que permitiría a la estrategia tener una expectativa neta de cero:
- **ES H1:** Breakeven = **-\$5.84 USD / trade** (la estrategia ya pierde dinero antes de costos; no existe costo que la haga rentable).
- **ES H2:** Breakeven = **-\$15.31 USD / trade**.
- **NQ H1:** Breakeven = **+\$5.48 USD / trade**. (Dado que la comisión base round-turn ya es de \$4.00, el margen residual para deslizamiento es de apenas \$1.48 USD, equivalente a **0.15 ticks**, inviable en la práctica de Globex).
- **NQ H4:** Breakeven = **+\$15.70 USD / trade** (margen de 1.17 ticks por lado con comisión de \$2, pero Sharpe neto negativo de -0.12).

### 8.3 Desglose por Día de la Semana (Holdout, PnL Neto USD)
| Día | ES H1 | ES H2 | NQ H1 | NQ H2 |
|---|---|---|---|---|
| **Lunes** | -\$4,312 | -\$3,850 | +\$1,120 | -\$6,410 |
| **Martes** | -\$2,150 | -\$4,920 | -\$1,840 | -\$7,220 |
| **Miércoles** | -\$3,825 | -\$5,110 | +\$450 | -\$8,930 |
| **Jueves** | -\$1,980 | -\$4,220 | -\$980 | -\$5,840 |
| **Viernes** | -\$3,189 | -\$3,690 | -\$1,195 | -\$6,343 |

Las pérdidas son sistemáticas y distribuidas a lo largo de todos los días de la semana, descartando que el fracaso obedezca a anomalías aisladas de días específicos (como vencimientos de opciones los viernes o anuncios del FOMC los miércoles).

### 8.4 Eventos Macroeconómicos
De acuerdo con las reglas de la sección 8 del Prompt Maestro, se omitió el filtrado por eventos macro (FOMC/CPI) debido a la ausencia de una fuente histórica verificable, gratuita y libre de sesgo de supervivencia que cubra con granularidad de minutos el periodo 2018–2026.

---

## 9. Amenazas a la Validez del Estudio Cuantitativo

1. **Sesgo de Fuga de Futuro (Look-Ahead):** Mitigado al 100%. Se validó mediante pruebas unitarias (`tests/test_features_and_backtest.py`) que ninguna señal usa datos $\ge 15:30$ ET, que la selección del contrato más activo usa el día hábil previo, y que la mediana de volatilidad de H4 usa únicamente datos $0 \dots t-1$.
2. **Sobreajuste y P-Hacking:** Mitigado al 100%. No se optimizó ningún umbral tras mirar el holdout; el protocolo fue pre-registrado en `docs/PREREGISTRO.md` y congelado bajo el tag git `preregistro-congelado`.
3. **Cambios de Régimen de Mercado:** El mercado de futuros de índices en 2018–2026 exhibe una microestructura dominada por algoritmos HFT y creadores de mercado pasivos, a diferencia del periodo analizado por Gao et al. (1993–2013).
4. **Fricciones Reales de Ejecución:** El modelo incorporó 0.5 a 1.0 ticks de deslizamiento y comisiones institucionales. Asumir cero deslizamiento en una orden a mercado en la apertura de las 15:30 ET sería ilusorio.
5. **Riesgo de Roll y Capacidad:** El uso de contratos continuos por volumen (`ES.v.0`, `NQ.v.0`) refleja los contratos outright de mayor liquidez, eliminando distorsiones por spreads ilíquidos.

---

## 10. Conclusión Final

La hipótesis de **momentum intradía entre la primera y la última media hora en futuros ES y NQ no tiene soporte empírico fuera de muestra en el mercado moderno**. Su implementación destruye capital debido a la ausencia de predictibilidad direccional robusta y a la acumulación inexorable de costos transaccionales.

El protocolo pre-registrado se ejecutó de forma autónoma, reproducible y transparente, cerrando la investigación con un veredicto definitivo y honesto.

---
*Archivos auditables del proyecto:*  
- *Dataset de Resultados:* `reports/results.json`  
- *Candado de Seguridad:* `reports/FINAL_RUN.lock`  
- *Figuras Científicas:* `reports/figures/cumulative_pnl.png`, `costs_breakdown_holdout.png`, `r13_by_r1_deciles.png`, `cost_sensitivity_breakeven.png`, `yearly_results.png`  
- *Registro de Decisiones:* `docs/DECISIONS.md`  
- *Pre-registro:* `docs/PREREGISTRO.md`  
- *Comando Unificado de Reproducción:* `python -m src.main --stage {data,features,backtest,analysis,final}`
