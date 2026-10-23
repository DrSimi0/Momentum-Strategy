# PRE-REGISTRO METODOLÓGICO: CORRECCIÓN DE EJECUCIÓN MOC EN 15M (SALIDA 15:45 ET)

**Fecha:** 2026-10-23  
**Estrategia:** Unificada Intradiaria con Cierre MOC Corregido para Timeframe 15m  
**Rama:** `feature/lower-tf-m5-m15`  
**Estado:** CONGELADO ANTES DE CUALQUIER EJECUCIÓN O MEDICIÓN  
**Estatus Oficial Inmutable:** **EXPLORATORIA (SIN HOLDOUT VIRGEN)**  

---

## 1. Justificación y Diagnóstico del Fallo Previo
En la auditoría forense se descubrió que la condición `moc_close_time = "15:50"` **nunca se activó en velas de 15 minutos** debido a que los sellos horarios de las barras de 15m son `... 15:15, 15:30, 15:45` ET. Al no existir barra con timestamp `15:50`, las posiciones quedaron abiertas *overnight*, transformando la supuesta "estrategia intradía" en una estrategia swing donde el 70.97% de los trades pasaron la noche.

Para cumplir estrictamente con el principio de intradía (cero riesgo *overnight* y cierre obligatorio dentro de la sesión regular), se corrige la regla de ejecución de forma causal y pre-registrada.

---

## 2. Regla Exacta e Inmutable de Salida MOC en 15m

- **Barra de Salida MOC Decidida Previamente:** Barra con timestamp **`15:45 ET`** (cubre el intervalo de 15:45 a 16:00 ET, fin oficial del RTH en CME).
- **Precio y Momento de Ejecución Causal:**
  - Al abrirse la barra de las `15:45 ET`, el sistema detecta de forma inmediata que dicha barra corresponde a la ventana de cierre de sesión (`t_str >= "15:45"`).
  - Cualquier posición Long abierta se cierra de forma obligatoria e incondicional en el **`Open` de la barra 15:45 ET**.
  - **Ausencia de Look-Ahead:** La decisión de cierre es conocida con certeza matemática al inicio de la barra `15:45 ET`; no se utiliza ninguna información posterior (ni `High`, ni `Low`, ni `Close` de las 15:45, ni la subasta de las 16:00 ET).
- **Filtro de Entrada:**
  - La última barra donde se permite generar una señal de compra sigue siendo `15:15 ET`. Prohibido entrar en las barras `15:30` o `15:45`.

---

## 3. Contabilidad del Espacio de Minería ($M$)

Esta corrección metodológica añade formalmente nuevas variantes al espacio acumulado de minería:
- Espacio previo acumulado: $M = 377$.
- Nuevas variantes evaluadas con la corrección MOC 15:45 ET:
  - NQ 15m Optimizada (MOC 15:45)
  - NQ 15m Línea Base (MOC 15:45)
  - ES 15m Línea Base (MOC 15:45)
- **Nuevo $M_{\text{total}}$ Acumulado:** $M = 377 + 3 = \mathbf{380}$ pruebas.
- **Nuevo $M_{\text{intraday}}$ Local:** $M_{\text{intra}} = 53 + 3 = \mathbf{56}$ pruebas.

---

## 4. Criterios de Aprobación / Rechazo Inmutables

La configuración corregida `NQ 15m Optimizada (MOC 15:45 ET)` será calificada objetivamente sin relajar ningún umbral:
1. **Sharpe Diario sobre Capital Fijo (\$50,000 USD):** $\ge 1.00$.
2. **Test de Permutación Monte Carlo (10,000 iteraciones):** $p < 0.05$.
3. **Deflated Sharpe Ratio con $M=380$:** $\ge 95\%$.
4. **Prop Firm en Micro Contratos (MNQ):** No exceder pérdida diaria de \$1,000 USD ni Trailing Drawdown de \$2,000 USD.
5. **Condición Intradía Absoluta:** $0.00\%$ de los trades pueden cruzar las 16:00 ET ni pasar la noche.
