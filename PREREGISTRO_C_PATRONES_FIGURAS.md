# PRE-REGISTRO METODOLÓGICO: ESTRATEGIA C (PATRONES DE VELA Y FIGURAS CHARTISTAS CAUSALES)

**Fecha:** 2026-10-22  
**Estado:** CONGELADO PREVIO A EVALUACIÓN  
**Principio de Inmutabilidad:** Este pre-registro define las reglas matemáticas objetivas para detectar patrones de velas y figuras chartistas de forma causal y determinista sin fuga de información futura.

---

## 1. Hipótesis de Investigación

¿Poseen los patrones clásicos de velas japonesas y las figuras geométricas chartistas (triángulos, cuñas, dobles techos/suelos) una ventaja estadística persistente y rentable ($N \ge 100$ trades, Sharpe $\ge 1.00$) tras deducir costos transaccionales en futuros CME (ES y NQ)?

---

## 2. Regla Causal de Confirmación de Pivotes (Zigzag / Fractales)

* **Retardo Fijo de Confirmación ($n=3$ barras):**
  Un pivote de Máximo Local en la barra $t-3$ se confirma formalmente en el cierre de la barra $t$ si y solo si:
  $$P_{t-3} > \max(P_{t-6}, P_{t-5}, P_{t-4}, P_{t-2}, P_{t-1}, P_t)$$
  Un pivote de Mínimo Local en la barra $t-3$ se confirma en el cierre de la barra $t$ si:
  $$P_{t-3} < \min(P_{t-6}, P_{t-5}, P_{t-4}, P_{t-2}, P_{t-1}, P_t)$$
* **Prohibición de Look-Ahead:** La señal de trading solo puede emitirse en la barra $t$ (la barra donde el pivote quedó matemáticamente confirmado).

---

## 3. Catálogo de Patrones de Vela Objetivos

1. **Martillo (Hammer) / Hombre Colgado:**
   * Sombra inferior $\ge 2.0 \times \text{Cuerpo}$.
   * Sombra superior $\le 0.2 \times \text{Cuerpo}$.
   * Entrada Long en $t+1$ si se produce en mínimos de 10 periodos. Stop Loss en el mínimo de la mecha.
2. **Vela Envolvente (Bullish / Bearish Engulfing):**
   * $\text{Cuerpo}_t > \text{Cuerpo}_{t-1}$ con color opuesto y envolviendo completamente el rango de apertura y cierre previo.
   * Stop Loss en el extremo opuesto de la vela envolvente.
3. **Estrella de la Mañana / Vespertina (Morning / Evening Star):**
   * Patrón de 3 velas: Vela tendencial amplia $\to$ Vela pequeña en gap/indecisión $\to$ Vela contraria que penetra $> 50\%$ del cuerpo de la primera.
4. **Doji en Soporte/Resistencia:**
   * $\text{Cuerpo} \le 0.1 \times \text{Rango total}$. Confirmación con rotura de máximo/mínimo.

---

## 4. Catálogo de Figuras Chartistas Causales

1. **Doble Suelo / Doble Techo (Double Bottom / Top):**
   * Dos pivotes confirmados consecutivos con diferencia de precio $\le 0.5\%$. Duración entre 10 y 60 barras. Entrada en la rotura de la línea de cuello (*neckline*).
2. **Triángulo / Cuña:**
   * Convergencia de líneas de tendencia trazadas sobre los últimos 4 pivotes confirmados alternados. Rotura confirmada por cierre de vela fuera del triángulo.
3. **Banderas / Canales de Continuación:**
   * Fuerte impulso previo (mástil $\ge 3 \times \text{ATR}$) seguido de consolidación estrecha de 5 a 15 barras en contra de la tendencia previa.

---

## 5. Regla de Muestra Mínima Estadística

* Muchos patrones geométricos son de baja frecuencia. Todo patrón que no alcance **$N \ge 100$ trades en el periodo de desarrollo (2010–2026)** queda formalmente descartado como no evaluable o estadísticamente insignificante.
