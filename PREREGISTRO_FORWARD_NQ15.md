# PRE-REGISTRO METODOLÓGICO: FORWARD TEST EN VIVO - NQ 15M (EXPLORATORIA)

**Fecha:** 2026-10-23  
**Estrategia:** Unificada Intradiaria NQ 15m (RTH + MOC + Volatilidad)  
**Rama de Desarrollo:** `feature/lower-tf-m5-m15`  
**Estado:** REGLAS CONGELADAS PARA FORWARD TEST  
**Estatus Oficial:** **EXPLORATORIA (SIN HOLDOUT VIRGEN)**  

---

## 1. Justificación y Propósito
El propósito exclusivo de este pre-registro es someter a prueba prospectiva estricta (Forward Testing en tiempo real sin look-ahead ni ajuste posterior de parámetros) la configuración de menor temporalidad con mejor perfil empírico (`NQ 15m Optimizada`), con el fin de evaluar si genera alfa genuino o si su desempeño histórico fue producto de sobreajuste/drift del mercado.

Queda explícitamente establecido que la estrategia fue descalificada en la auditoría retrospectiva ($p = 0.1793$ en test de permutación y DSR de 29.4%), por lo que **no se considera aprobada para capital real ni prop firms**.

---

## 2. Parámetros Exactos e Inmutables de la Estrategia

- **Activo:** Micro E-mini Nasdaq-100 (`MNQ`) o E-mini Nasdaq-100 (`NQ`).
- **Timeframe:** 15 minutos (`15m`).
- **Régimen de Tendencia:**
  - $EMA_{rápida} = 20$ barras.
  - $EMA_{lenta} = 80$ barras.
  - Condición de Régimen: $EMA_{20} > EMA_{80}$ Y $Close_t > EMA_{80}$.
- **Filtro de Momentum:**
  - $MACD(12, 26, 9)$: Histograma $> 0$.
  - $RSI(14)$: Entre $45.0$ y $75.0$ (ambos inclusive).
- **Filtro de Volatilidad:**
  - $ATR(14) \ge 0.95 \times SMA(ATR_{14}, 40)$.
- **Gatillo de Entrada:**
  - Vela japonesa de confirmación: Martillo (`Hammer`) O Envolvente Alcista (`Bullish Engulfing`) confirmada al cierre de la barra $t$.
- **Ventana Horaria de Generación de Señales (RTH):**
  - Desde las `10:00 ET` hasta las `15:15 ET`. Prohibido abrir posiciones fuera de esta ventana.
- **Cierre Forzoso de Sesión (MOC):**
  - Cualquier posición abierta se cierra incondicionalmente a las `15:50 ET` en la apertura de la barra. No se permite mantener posiciones *overnight*.
- **Gestión de Salida:**
  - Stop Loss: $2.0 \times ATR(14)$ por debajo del precio de entrada.
  - Take Profit: $2.0 \times \text{Distancia Stop} = 4.0 \times ATR(14)$.
  - Inversión de Régimen: Cierre si $EMA_{20} < EMA_{80}$.

---

## 3. Protocolo de Ejecución Causal

1. La señal se calcula única y exclusivamente al **cierre formal de la barra $t$** (a las `XX:14:59`, `XX:29:59`, `XX:44:59`, `XX:59:59`).
2. La orden de entrada se registra causalmente en el **Open de la barra $t+1$**.
3. Se registran todas las señales en `reports/forward_signals.jsonl` con timestamp UTC inmutable.

---

## 4. Criterios de Evaluación y Veredicto Futuro

- **Muestra Mínima Estadística:** $N \ge 100$ trades en vivo completados.
- **Sharpe Diario Neto:** $\ge 1.00$ con costos reales aplicados.
- **P-valor Monte Carlo vs Azar:** $p < 0.05$.
- **Pérdida Máxima Diaria:** No exceder $\$1,000$ USD en cuenta micro equivalente.
