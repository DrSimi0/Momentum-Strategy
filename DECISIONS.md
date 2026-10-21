# Registro de Decisiones de Diseño y Evaluación (DECISIONS.md)

Este documento registra de forma inmutable y transparente todas las decisiones técnicas tomadas para cumplir con los objetivos del protocolo sin intervención ni preguntas al usuario.

---

### DEC-001: Fuente de Datos y Rango Temporal
- **Decisión:** Se utiliza Binance USDT-M Futures (datos oficiales descargados de `data.binance.vision` y funding rate de `fapi.binance.com`).
- **Detalle de Fechas:** Las velas 4h de BTCUSDT en Binance Vision comienzan en enero de 2020 (`2020-01`).
- **Partición temporal fijada a priori:**
  - *Calentamiento de indicadores:* `2020-01-01` a `2020-03-01` (2 meses, >300 barras de 4h).
  - *Desarrollo (In-Sample):* `2020-03-01` a `2023-07-01` (3.3 años).
  - *Validación:* `2023-07-01` a `2025-01-01` (1.5 años).
  - *Holdout (Fuera de muestra estricto):* `2025-01-01` a `2026-10-01` (1.75 años, ~21 meses).
- **Justificación:** Es un diseño canónico que preserva un holdout de casi 2 años para verificar la rentabilidad en regímenes recientes, con suficiente histórico para desarrollo.

---

### DEC-002: Modelo de Costos y Mercado 24/7
- **Decisión:**
  - Comisiones: 0.05% (5 bps) por lado taker (tarifa estándar VIP0 de Binance USDT-M).
  - Deslizamiento (Slippage): 0.05% (5 bps) por lado sobre el precio de referencia en cada fill de entrada y salida.
  - Tasa de financiación (Funding Rate): Funding histórico exacto devengado cada 8 horas (00:00, 08:00, 16:00 UTC) asignado a la posición abierta si se mantenía durante el timestamp de corte.
  - En pruebas de estrés de costos (factor x2): comisiones y deslizamiento se multiplican por 2. El funding rate pagado (flujo adverso) se duplica; el cobrado permanece idéntico (conservadurismo financiero).
  - Anualización 24/7: Retornos diarios medidos al cierre de cada día UTC. Se anualiza con $365$ días (factor $\sqrt{365}$ para volatilidad y Sharpe), tasa libre de riesgo = 0.
- **Justificación:** Cripto opera ininterrumpidamente 365 días al año. Asumir 252 días sobrestimaría el Sharpe en un ~20%.

---

### DEC-003: Lógica del Motor de Ejecución Barra a Barra
- **Decisión:**
  - Regla Donchian: Ruptura de máximo/mínimo de las $N$ barras previas (excluyendo estrictamente la barra actual para evitar lookahead bias).
  - Señal confirmada al cierre de la barra $i$; ejecución en la apertura de la barra $i+1$ al precio `Open[i+1] * (1 + Side * Slippage)`.
  - Tamaño de posición (Position Sizing): Riesgo fijo del 1% del equity actual por operación hasta el stop inicial ($k \times \text{ATR}(14)$).
  - Apalancamiento techo: Máximo $3.0\times$ del equity.
  - Trailing Stop tipo Chandelier: Se ajusta exclusivamente a favor del trade barra a barra en base al precio extremo alcanzado $\pm k \times \text{ATR}$.
  - Liquidación simulada: Margen de mantenimiento del 0.5% (Binance Tier 1). Si durante la barra el precio extremo adverso alcanza o perfora el precio de liquidación, la posición se liquida forzosamente al precio de liquidación con penalización por liquidación.
  - Cierre al vencimiento: En la última barra del periodo evaluado, cualquier posición abierta se liquida a precio de cierre con comisión y deslizamiento.

---

### DEC-004: Rejilla de Hiperparámetros y Selección Ciega
- **Decisión:**
  - Espacio de búsqueda fijado previamente: $N \in [20, 50, 100]$ barras de 4h ($\approx 3.3, 8.3, 16.6$ días) y multiplicador ATR $k \in [2.0, 3.0, 4.0]$. Total: 9 configuraciones candidatas.
  - Selección: Configuración con mayor Sharpe neto anualizado exclusivamente en el conjunto de *Desarrollo*.
  - El holdout permanece completamente ciego e inaccesible hasta que los parámetros seleccionados y los umbrales de aceptación quedan congelados y comprometidos en Git con hashes verificables.

---

### DEC-005: Baselines de Comparación
- **Decisión:**
  - *Buy & Hold:* Posición larga $1\times$ en el contrato perpetuo abierta al inicio del periodo y cerrada al final, deduciendo comisiones de entrada/salida, deslizamiento y el cobro/pago de funding acumulado real a lo largo de todo el periodo.
  - *Baseline Aleatorio con Misma Exposición:* 500 réplicas Monte Carlo que colocan las operaciones reales (mismas duraciones en barras, mismos lados y mismos apalancamientos de entrada) distribuidas uniformemente al azar en el tiempo sin solapamiento, calculando su PnL con costos exactos.

---

### DEC-006: Protocolo de Congelado y Evaluación Única del Holdout
- **Decisión:**
  - El archivo `config/acceptance.yaml` se congela con commit en Git y se genera `config/freeze.json` con los hashes SHA-256 de `acceptance.yaml`, `strategy.yaml`, `strategy_frozen.yaml` y `manifest.json`.
  - Código en `src/evaluation/protocol.py` verifica previo a la ejecución del holdout:
    1. Que `freeze.json` exista y esté en un commit limpio.
    2. Que los archivos congelados coincidan byte a byte con su hash.
    3. Que no existan cambios locales sin commitear en dichos archivos.
  - Creación atómica del archivo lock `reports/.holdout_used`. Si ya existe, cualquier intento posterior de re-ejecución sobre el holdout genera una excepción irrecuperable (`HoldoutAlreadyUsed`).

---

### DEC-007: Definición de Criterios y Veredicto
- **Decisión:**
  - **FAIL:** Si se viola cualquier criterio eliminatorio: expectativa neta $\le 0$, eventos de liquidación $> 0$, expectativa con costos x2 $\le 0$, o retención $< 25\%$.
  - **INCONCLUSIVE:** Si no hay fallo eliminatorio pero el número de operaciones OOS $< 50$ (si $< 30$, INCONCLUSIVE automático), o si el IC 95% de la expectativa incluye el cero, o si el Deflated Sharpe Ratio no alcanza el umbral de $0.95$, o si algún otro criterio estándar no se cumple.
  - **PASS:** Exclusivamente si la totalidad de los criterios de `acceptance.yaml` son satisfechos.
  - El reporte manifiesta explícitamente: *"PASS significa evidencia consistente de edge en el pasado bajo este protocolo, nunca garantía de rentabilidad futura"*.
