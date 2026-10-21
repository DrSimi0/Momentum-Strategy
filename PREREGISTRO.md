# PRE-REGISTRO METODOLÓGICO INMUTABLE

**Fecha:** 2026-10-21  
**Estado:** CONGELADO PREVIO A EVALUACIÓN  
**Principio de Inmutabilidad:** Este documento define todas las hipótesis, reglas operativas, espacio paramétrico cerrado y criterios cuantitativos de aceptación antes de ejecutar cualquier análisis de optimización o abrir la partición de prueba. Queda terminantemente prohibido alterar cualquier umbral, parámetro o partición tras observar los resultados.

---

## 1. Hipótesis Única de Investigación

¿Puede un sistema de seguimiento de tendencia por confluencia técnica en velas de 4 horas (4h) que combina:
1. **Filtro de Tendencia Macro:** Alineación de Medias Móviles Simples (2 SMAs: $\text{Close} > \text{SMA}_{\text{lenta}}$ y $\text{SMA}_{\text{rápida}} > \text{SMA}_{\text{lenta}}$; o 3 SMAs: $\text{SMA}_{\text{rápida}} > \text{SMA}_{\text{media}} > \text{SMA}_{\text{lenta}}$).
2. **Gatillo de Impulso:** Cruce alcista del histograma MACD por encima de cero en dirección de la tendencia (o cruce bajista por debajo de cero para cortos).
3. **Filtro de Sobreextensión:** RSI(14) en zona de confirmación sin agotamiento ($40 \le \text{RSI} \le 70$ para largos; $30 \le \text{RSI} \le 60$ para cortos).
4. **Gestión de Salida:** Stop Loss inicial a $k \times \text{ATR}(14)$ y Take Profit a $m \times \text{Riesgo}$ (o reversión contraria de las SMAs).

Generar un rendimiento ajustado por riesgo estadísticamente significativo (Sharpe neto anualizado $\ge 1.00$, Deflated Sharpe $\ge 95\%$ y robustez temporal en Walk-Forward $\ge 60\%$) en futuros CME (ES y NQ) tras deducir comisiones y deslizamientos reales?

---

## 2. Espacio Paramétrico Reducido (Contabilidad Exacta de Pruebas: 32 Combinaciones)

Se evalúa un único timeframe: **4 horas (4h)**.
El espacio de búsqueda queda estrictamente acotado a **32 combinaciones por activo**:

1. **Arquitecturas de Medias Móviles (8 variantes):**
   * 2 SMAs: (20, 150), (20, 200), (30, 150), (30, 200)
   * 3 SMAs: (20, 100, 150), (20, 100, 200), (30, 100, 150), (30, 100, 200)
2. **Configuraciones MACD (2 variantes):**
   * Estándar: (12, 26, 9)
   * Lento / Suave: (16, 35, 9)
3. **Filtro RSI (1 variante fija):**
   * Periodo 14
4. **Stop Loss ATR (2 variantes):**
   * $k = 2.0$ y $k = 3.0$
5. **Take Profit Multiplier (2 variantes):**
   * $m = 1.5$ y $m = 2.0$

$$\text{Total combinaciones por activo} = 8 \times 2 \times 1 \times 2 \times 2 = 32 \text{ combinaciones.}$$

---

## 3. Protocolo de Partición Cronológica y Aislamiento del Holdout

Para garantizar la integridad científica, el histórico total (2010 a 2026, 16.36 años, 26,084 barras de 4h) se divide en tres bloques temporales disjuntos:
1. **Entrenamiento (60%):** ~Junio 2010 a Mayo 2020 (~10 años). Aquí y solo aquí se ejecuta la exploración de la grilla de 32 combinaciones.
2. **Validación (20%):** ~Junio 2020 a Febrero 2023 (~2.7 años). Aquí se selecciona la **única configuración finalista** (máximo Sharpe en validación).
3. **HOLDOUT / Test Final (20%):** ~Marzo 2023 a Octubre 2026 (~3.6 años).
   * **Regla de Bloqueo Físico:** Se almacena en `data/locked_holdout/`. Ningún script de optimización ni grid search tiene acceso a este directorio.
   * **Regla de Un Solo Intento:** Se evalúa **UNA sola vez** con la única configuración finalista elegida en validación. El resultado se reporta tal cual, sin posibilidad de reajuste.

---

## 4. Criterios Cuantitativos de Aceptación (Condiciones para Aprobación)

Para que la estrategia se considere validada para implementación, debe cumplir **todos y cada uno** de los siguientes criterios en el Holdout fuera de muestra:

1. **Muestra Mínima:** $N \ge 100$ operaciones cerradas en el periodo total evaluado ($\ge 30$ en holdout).
2. **Sharpe Neto Anualizado:** $\ge 1.00$ tras comisiones y deslizamiento.
3. **Factor de Beneficio (Profit Factor):** $\ge 1.30$.
4. **Drawdown Máximo Relativo:** $\le 25\%$ del capital nocional.
5. **Robustez Temporal Walk-Forward:** $\ge 60\%$ de las ventanas rodantes fuera de muestra deben tener PnL neto estrictamente positivo y Sharpe medio positivo.
6. **Significancia frente al Azar (Deflated Sharpe Ratio):** $\ge 95\%$ ($p < 0.05$) ajustado por las 32 pruebas del pre-registro.
7. **Superioridad frente a Líneas Base:** Superar al Buy & Hold del mismo periodo y a la versión Solo-SMA.

Si la estrategia incumple cualquiera de estos criterios, el veredicto será **REJECTED (NO APROBADA)**. Un resultado negativo documentado con honestidad es un resultado científico válido.
