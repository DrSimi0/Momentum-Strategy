# PRE-REGISTRO METODOLÓGICO: HIPÓTESIS ADICIONAL - ESTRATEGIA SIMÉTRICA (LARGOS + CORTOS) NQ 5M EMA 200

**Fecha:** 2026-10-25  
**Hipótesis:** La versión simétrica de la estrategia NQ 5m EMA 200 (operando tanto compras como ventas en corto con reglas espejo) añade valor frente a la versión de solo largos.  
**Rama:** `feature/lower-tf-m5-m15`  
**Estado:** CONGELADO ANTES DE CUALQUIER EJECUCIÓN O MEDICIÓN  
**Estatus Oficial Inmutable:** **EXPLORATORIA (HIPÓTESIS NUEVA NO VALIDADA)**  

---

## 1. Reglas Espejo Exactas para el Lado Corto (Short)

- **Regla Espejo de Señal Bajista (Cierre de $t$):**
  - Cruce bajista del precio de cierre por debajo de la EMA 200:
    $$\text{Close}[t] < \text{EMA}_{200}[t] \quad \text{y} \quad \text{Close}[t-1] \ge \text{EMA}_{200}[t-1]$$
- **Momento y Precio de Ejecución:**
  - Apertura causal estricta de la siguiente barra ($t+1$): $\text{Entry Price} = \text{Open}[t+1]$.
- **Horario RTH Permitido:** Mismo horario institucional: **10:00 ET a 15:15 ET**.
- **Filtro de Expansión de Volatilidad:** Idéntico:
  $$\text{ATR}(14) \ge 0.95 \times \text{SMA}(\text{ATR}(14), 40)$$
- **Sin Parámetros Propios para el Lado Corto:**
  - **Stop Loss:** $\text{Open}[t+1] + 2.5 \times \text{ATR}(14)$.
  - **Take Profit:** $\text{Open}[t+1] - 3.0 \times (2.5 \times \text{ATR}(14))$ (Ratio Riesgo-Beneficio 1:3).
  - **Pérdida de Tendencia Bajista:** Si la barra anterior cierra por encima de la EMA 200 ($\text{Close}[i-1] > \text{EMA}_{200}[i-1]$), salida obligatoria en $\text{Open}[i]$.
  - **Cierre Forzoso de Sesión (MOC):** Cierre plano en la apertura de las **15:50 ET**. Cero trades overnight.

---

## 2. Protocolo de Evaluación

1. **Protocolo Idéntico al de Solo Largos:**
   - Selección / Calibración previa en 2021–2024.
   - Test una vez en **2024–2026** (2 años) y una vez en **2010–2021** (11.3 años). Sin ajustes posteriores.
2. **Desglose Obligatorio de Métricas por Separado:**
   - Lado Largo (Long-Only)
   - Lado Corto (Short-Only)
   - Combinado (Lados Largo + Corto)
   - Métricas: PnL neto USD, número de operaciones, Win Rate, Profit Factor, Sharpe diario sobre capital fijo ($50,000 USD) y Max Drawdown en $ y %.
3. **Test de Permutación Monte Carlo (10,000 iteraciones) por Separado:**
   - Permutación para compras (entradas aleatorias dentro de RTH con misma duración).
   - Permutación para ventas cortas (entradas aleatorias dentro de RTH con misma duración).
   - Permutación para el sistema combinado.
4. **Desglose por Régimen de Mercado:**
   - Rendimiento por año individual (2010 a 2026).
   - Rendimiento en años de régimen alcista (*Bull markets*) vs años de régimen bajista / lateral (*Bear / Sideways*).
5. **Contabilidad del Espacio de Minería ($M$):**
   - Se añaden formalmente las variantes simétricas al contador acumulado para el Deflated Sharpe Ratio.
6. **Prop Firm con MNQ:**
   - Simulación comparativa con costos de micro para solo largos vs versión simétrica.
