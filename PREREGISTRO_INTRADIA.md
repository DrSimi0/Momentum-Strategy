# PRE-REGISTRO METODOLÓGICO: AUDITORÍA DE ESTRATEGIAS INTRADÍA M15 Y M5 (EXPLORATORIA)

**Fecha:** 2026-10-23  
**Rama de Desarrollo:** `feature/lower-tf-m5-m15`  
**Estado:** CONGELADO PREVIO A AUDITORÍA  
**Declaración Metodológica:** Todas las configuraciones intradiarias evaluadas en este documento fueron diseñadas, calibradas o probadas sobre el periodo 2010–2026. En consecuencia, quedan formalmente catalogadas como **EXPLORATORIAS (SIN HOLDOUT VIRGEN)**. Queda vetado el uso de términos como "validada" o "ganadora".

---

## 1. Configuraciones Exactas a Auditar (Fijadas, Sin Añadir Otras)

1. **`NQ 15m (Optimizada)`**: `EMA(20)` y `EMA(80)` + Horario RTH `10:00 - 15:15 ET` + Cierre forzoso MOC `15:50 ET` + Filtro de expansión `ATR(14) >= 0.95 * SMA(ATR, 40)`.
2. **`NQ 15m (Línea Base)`**: `EMA(30)` y `EMA(200)` swing sin filtros intradiarios ni cierre MOC.
3. **`ES 15m (Línea Base)`**: `EMA(30)` y `EMA(200)` swing sin filtros intradiarios ni cierre MOC.
4. **`NQ 5m (Optimizada)`**: `EMA(20)` y `EMA(80)` + Horario RTH `10:00 - 15:15 ET` + Cierre MOC `15:50 ET` + Filtro ATR.
5. **`ES 5m (Agresiva)`**: `EMA(10)` y `EMA(50)` + Stop $1.5 \times \text{ATR}$ + Horario RTH + Cierre MOC + Filtro ATR.
6. **`NQ 5m (Cierre MOC Sin Volatilidad)`**: `EMA(30)` y `EMA(200)` + Cierre forzoso MOC `15:50 ET` sin filtro de volatilidad.

---

## 2. Reglas Comunes y Costos Reales

- **Dirección Operativa:** Exclusivamente **Long-Only** (las ventas en corto quedan vetadas por el drift alcista del mercado).
- **Gatillos de Entrada:** Vela envolvente alcista (`Engulfing Bullish`) o martillo (`Hammer`) confirmada al cierre de la barra $t$.
- **Ejecución Causal:** Entrada estricta en el `Open` de la barra $t+1$.
- **Costos Transaccionales CME:**
  - Futuros E-mini (ES / NQ): Comisión \$2.00 por lado + Slippage 0.5 ticks (\$6.25 en ES, \$2.50 en NQ). Fricción RT = \$16.50 en ES, \$9.00 en NQ.
  - Futuros Micro (MES / MNQ): Comisión \$0.60 por lado + Slippage 0.5 ticks (\$0.625 en MES, \$0.25 en MNQ). Fricción RT = \$2.45 en MES, \$1.70 en MNQ.

---

## 3. Contabilidad de Pruebas para DSR

- Espacio acumulado total de minería: $M = 344$ configuraciones (224 de Medias, 40 de RSI/MACD, 42 de Patrones, 12 Unificadas y 26 Intradiarias).
- Espacio local intradiario: $M_{intra} = 26$ pruebas.

---

## 4. Criterios de Rechazo

Una configuración será declarada **RECHAZADA / INVIABLE** si:
1. **Límite Prop Firm:** La pérdida máxima diaria (Daily Max Loss) excede \$1,000 USD (cuenta \$50k) o \$1,500 USD (cuenta \$100k), o el Trailing Drawdown excede \$2,000 USD / \$3,000 USD en contratos estándar o micro.
2. **Azar Estadístico:** El p-valor del test de permutación (10,000 iteraciones con entradas aleatorias intradiarias) es $p \ge 0.05$.
3. **Fragilidad de Concentración:** Más del 50% del PnL depende de los 5 mejores trades.
4. **DSR:** Deflated Sharpe Ratio $< 95\%$.
