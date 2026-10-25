# PRE-REGISTRO METODOLÓGICO: CONFIGURACIÓN CONGELADA NQ 5M EMA 200 (SOLO LARGOS)

**Fecha:** 2026-10-25  
**Estrategia:** NQ 5m Cruce EMA 200 Intradía (Solo Largos)  
**Rama:** `feature/lower-tf-m5-m15`  
**Estado:** CONGELADO ANTES DE CUALQUIER EJECUCIÓN O MEDICIÓN  
**Estatus Oficial Inmutable:** **EXPLORATORIA (SIN HOLDOUT VIRGEN EN HISTORIAL COMPLETO)**  
*(No llamarla "validada" ni "rentable y robusta" bajo ninguna circunstancia)*

---

## 1. Reglas Operativas Congeladas

- **Instrumento Principal:** NQ (E-mini Nasdaq 100) y Micro E-mini (MNQ).
- **Temporalidad:** 5 minutos (5m).
- **Línea de Tendencia:** Media Móvil Exponencial de 200 períodos (EMA 200).
- **Regla de Entrada (Señal al Cierre de $t$):**
  - Cruce alcista del precio de cierre sobre la EMA 200:
    $$\text{Close}[t] > \text{EMA}_{200}[t] \quad \text{y} \quad \text{Close}[t-1] \le \text{EMA}_{200}[t-1]$$
- **Momento y Precio de Ejecución:**
  - Ejecución causal estricta en la **Apertura de la siguiente barra ($t+1$)**: $\text{Entry Price} = \text{Open}[t+1]$.
  - Prohibido utilizar información posterior o precio de cierre de la barra de señal.
- **Filtro de Horario Institucional RTH:**
  - Solo se admiten nuevas entradas si la señal se genera entre las **10:00 ET** y las **15:15 ET**.
- **Filtro de Expansión de Volatilidad:**
  $$\text{ATR}(14) \ge 0.95 \times \text{SMA}(\text{ATR}(14), 40)$$
- **Gestión de Riesgo:**
  - **Stop Loss:** $\text{Open}[t+1] - 2.5 \times \text{ATR}(14)$.
  - **Take Profit:** $\text{Open}[t+1] + 3.0 \times (2.5 \times \text{ATR}(14))$ (Ratio Riesgo-Beneficio 1:3).
  - **Pérdida de Tendencia:** Si la barra anterior cierra por debajo de la EMA 200 ($\text{Close}[i-1] < \text{EMA}_{200}[i-1]$), salida obligatoria en $\text{Open}[i]$.
  - **Cierre de Sesión Obligatorio (MOC):** Salida plana forzosa en la apertura de la barra **15:50 ET**. Cero riesgo nocturno ($0\%$ trades overnight).

---

## 2. Protocolo de Pruebas Fuera de Muestra

1. **Prueba Única e Inmutable en Historial Profundo:**
   - **Período:** 2010-06 a 2021-10 (11.3 años continuos).
   - **Activos:** NQ 5m y ES 5m como contraste (mismas reglas idénticas).
   - **Compromiso Categórico:** No se modificará ningún parámetro ni regla tras observar los resultados. Un resultado negativo o destructivo será documentado fielmente.
2. **Evaluación Reciente:** Período 2024-10 a 2026-10.
3. **Métricas Obligatorias:**
   - Retornos diarios sobre capital fijo institucional ($50,000 USD).
   - Sharpe anualizado ($\sqrt{252}$).
   - Test de permutación Monte Carlo (10,000 iteraciones) restringido a la ventana RTH.
   - Intervalos de confianza por Bootstrap de Bloques (bloques de 10 días).
   - Deflated Sharpe Ratio con el contador total acumulado de pruebas $M$.
   - Simulación de Prop Firm con MNQ y comisiones reales de micro.
