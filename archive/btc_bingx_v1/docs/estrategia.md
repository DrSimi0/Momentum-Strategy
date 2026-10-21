# Especificación Formal de la Estrategia de Confluencia en Tres Capas (v3.0)
*BTC-USDT Perpetuo (BingX, 15m)*

---

## 1. Filosofía y Principio de Confluencia Jerárquica

La estrategia no se basa en un indicador aislado ni en la detección ingenua de patrones geométricos. Se fundamenta en una **confluencia jerárquica descendente de tres capas independientes** donde la temporalidad y la escala de información mayor condicionan estrictamente a la menor.

Su objetivo primordial, en orden estricto de prelación, es:
1. **Preservación absoluta del capital y prevención de liquidación.**
2. **Filtrado selectivo de trampas de mercado (*bull/bear traps*).**
3. **Captura de movimientos direccionales con asimetría positiva beneficio/riesgo.**

Por diseño, el estado natural y más frecuente del sistema es **`NEUTRAL`** (abstención operativa). Solo se autoriza una posición cuando existe alineación coherente en los tres niveles de análisis.

---

## 2. Las Tres Capas de Decisión

```
┌────────────────────────────────────────────────────────┐
│ CAPA 1: Macroeconomía y Sentimiento de Mercado         │
│ (¿Hacia qué dirección está permitido operar?)          │
└───────────────────────────┬────────────────────────────┘
                            │ Filtro direccional / Abstención
                            ▼
┌────────────────────────────────────────────────────────┐
│ CAPA 2: Estructura Técnica y Setup Cuantitativo (15m)  │
│ (¿Existe un punto de entrada, invalidación y objetivo?)│
└───────────────────────────┬────────────────────────────┘
                            │ Setup formalizado (Entrada, SL, TP, Tau)
                            ▼
┌────────────────────────────────────────────────────────┐
│ CAPA 3: Microestructura y Validación de Flujo          │
│ (¿Confirma el flujo de órdenes y la absorción ahora?)   │
└───────────────────────────┬────────────────────────────┘
                            │ Confirmación / No Confirmación
                            ▼
                DECISIÓN DETERMINISTA FINAL
               (LONG / SHORT / NEUTRAL)
```

### 2.1 Capa 1 — Filtro Direccional Macro y Sentimiento
Esta capa opera en escala macro y temporalidades superiores (1D / 1W). **Nunca genera puntos de entrada específicos**, sino que establece el régimen de permisividad:
- **Calendario Macroeconómico de Alto Impacto (3 estrellas):** IPC (CPI), IPP (PPI), Nóminas no agrícolas (NFP) y decisiones del FOMC/Fed. Durante la ventana de $\pm 60$ minutos en torno al evento, el mercado sufre choques de liquidez exógenos que invalidan los niveles técnicos; se impone un estado de **`ABSTENCIÓN`** obligatoria.
- **Índice DXY (Dólar estadounidense):** Actúa como contraindicador de liquidez global. Canal o tendencia alcista en DXY impone sesgo bajista en BTC; ruptura bajista en DXY libera apetito por riesgo (sesgo alcista).
- **Índice Fear & Greed:** Contraindicador de posicionamiento minorista con publicación diaria point-in-time a las 00:00 UTC. Miedo extremo ($< 30$) favorece compras o cierre de cortos; codicia extrema ($> 70$, y especialmente $> 75$) prohíbe la apertura de posiciones largas por agotamiento de compradores marginales.
- **Gaps de Futuros CME (BTC):** Discontinuidades del fin de semana utilizadas como sesgo secundario hacia el objetivo de relleno, sujetas a un horizonte máximo temporal prefijado.
- **Estructura Técnica Superior (1D/1W):** Si la estructura semanal es bajista o presenta divergencias bajistas no confirmadas, se prohíbe taxativamente abrir largos intradiarios.

**Salida de Capa 1:** `ALCISTA`, `BAJISTA`, `NEUTRO` o `ABSTENCIÓN`.

---

### 2.2 Capa 2 — Estructura Técnica y Definición del Setup (15m)
Define de forma unívoca y determinista las coordenadas de la operación:
1. **Soportes y Resistencias Algorítmicos:** Identificados mediante fractales locales con confirmación de al menos **3 puntos de contacto** dentro de una tolerancia porcentual $\epsilon$. Incorpora la regla de **inversión de roles** (*S/R flip*) tras ruptura confirmada por cierre de vela y posterior retest.
2. **Medias Móviles:** EMA 21 y 50 para evaluar la inercia del precio a corto plazo; SMA 100 y 200 como filtros de fondo tendencial.
3. **Patrones Geométricos Deterministas:** Triángulos (alcista, bajista, simétrico), cuñas convergentes, banderas (*flags*) y doble suelo/techo ($W / M$). Para considerarse válidos, requieren:
   - Identificación matemática de directrices con $R^2$ lineal riguroso.
   - **Expansión obligatoria de volumen** en el punto de ruptura ($\text{Volumen} > 1.8 \times \text{SMA}_{20}$). Rupturas con volumen declinante se descartan como falsas rupturas.
4. **Indicadores de Confirmación:**
   - **RSI (14):** Las divergencias clásicas sólo se activan si están acompañadas de la ruptura del último nivel pivote de confirmación.
   - **MACD Normalizado:** Evaluado en valores extremos relativos (z-score rodante). Un cruce alcista sólo es válido si ocurre en territorio fuertemente negativo (inicio de impulso); cruces en territorio alto se descartan por considerarse tardíos o trampas.
   - **BBWP (Bollinger Band Width Percentile):** Percentil histórico del ancho de bandas. Valores cercanos al 0% indican compresión extrema previa a una explosión de volatilidad. Debe combinarse obligatoriamente con el sesgo direccional de RSI/MACD.

**Salida de Capa 2:** Un objeto estructurado `Setup` con dirección, precio de entrada, precio de stop-loss, precio de take-profit y horizonte temporal máximo; o bien `Sin Setup`.

---

### 2.3 Capa 3 — Microestructura y Validación de Flujo (Ejecución Fina)
Verifica la absorción de liquidez y el comportamiento de las órdenes institucionales en el nivel clave:
- **Barrido de Liquidaciones:** Agotamiento de caídas por barrido masivo de posiciones largas (bloques compradores) o absorción de cortos en resistencias.
- **Patrón de Absorción:** Mechas prominentes en la vela de 15m acompañadas de volumen anómalo y reversión inmediata.

**Salida de Capa 3:** `CONFIRMA`, `NO CONFIRMA` o `NO DISPONIBLE`.  
*(Nota metodológica: Debido a que la microestructura de órdenes de 1s no está en el histórico de velas de 15m, la Capa 3 se valida en modo observación/paper trading en vivo mediante el registro continuo de flujos).*

---

## 3. Regla de Conflicto y Arbitraje (La Regla Anti-Trampa)

La jerarquía es inviolable: **la capa superior prevalece siempre sobre la inferior**.

$$\text{Decisión Final} = 
\begin{cases} 
\text{NEUTRAL (Motivo: Datos inválidos o vela en formación)} & \text{si datos no vigentes} \\
\text{NEUTRAL (Motivo: Abstención Macro)} & \text{si Capa 1} = \text{ABSTENCIÓN} \\
\text{NEUTRAL (Motivo: Sin setup técnico)} & \text{si Capa 2 no genera setup} \\
\text{NEUTRAL (Motivo: Conflicto - Trampa de Mercado)} & \text{si Dirección(Capa 2)} \ne \text{Capa 1 y Capa 1} \ne \text{NEUTRO} \\
\text{NEUTRAL (Motivo: Sin confirmación de microestructura)} & \text{si Capa 3} = \text{NO CONFIRMA} \\
\text{LONG} & \text{si Capa 1 ALCISTA} \land \text{Capa 2 LONG} \land \text{Capa 3 CONFIRMA/N.A.} \\
\text{SHORT} & \text{si Capa 1 BAJISTA} \land \text{Capa 2 SHORT} \land \text{Capa 3 CONFIRMA/N.A.}
\end{cases}$$

> **Principio de la Trampa:** Un setup técnico alcista de 15m que aparezca bajo un entorno macro restrictivo o una estructura semanal bajista **no es una oportunidad; es una trampa de liquidez (*bull trap*)**. El sistema se abstiene deterministamente.

---

## 4. Los Tres Escenarios de Decisión

1. **Alineación Alcista Total $\rightarrow$ `LONG`:**
   - Capa 1: Macro permisivo / DXY rompiendo a la baja / Fear & Greed en zona neutral o saliendo de pánico ($<30$).
   - Capa 2: Ruptura técnica alcista con volumen (ej. bandera o cuña descendente) + MACD cruzando en terreno negativo + BBWP saliendo de compresión.
   - Capa 3: Absorción compradora confirmada con mecha inferior prominente.
   - Ejecución: Orden al precio de apertura de la siguiente barra ($t+1$). SL bajo la mecha de invalidación; TP al objetivo proyectado por el patrón técnico.

2. **Alineación Bajista Total $\rightarrow$ `SHORT`:**
   - Capa 1: Macro restrictivo / DXY en canal alcista / Fear & Greed en complacencia o codicia ($>70$).
   - Capa 2: Doble techo o ruptura bajista de soporte con volumen + divergencia bajista en RSI + MACD en extremo positivo girando a la baja.
   - Capa 3: Absorción vendedora confirmada en re-test de la resistencia rota.
   - Ejecución: Orden al precio de apertura de la siguiente barra ($t+1$). SL sobre el máximo del patrón técnico; TP en el soporte estructural inferior.

3. **Conflicto entre Capas o Falta de Confluencia $\rightarrow$ `NEUTRAL`:**
   - Cualquier discordancia entre el sesgo de Capa 1 y el patrón de Capa 2.
   - Ausencia de volumen en la ruptura técnica.
   - Publicación inminente de un evento macroeconómico de 3 estrellas.
   - Resultado: Abstención operativa completa.

---

## 5. Reglas Inviolables de Gestión de Riesgo

1. **Definición Previa del Plan:** Ninguna señal puede emitirse sin tener calculados e inmutables: precio de entrada, precio de Stop-Loss ($SL$), precio de Take-Profit ($TP$) y horizonte temporal máximo ($\tau$).
2. **Prohibición de Alejamiento del Stop-Loss:** El $SL$ sólo puede mantenerse fijo o desplazarse a favor de la operación (reducción de riesgo). Jamás puede aumentarse la distancia al $SL$ inicial.
3. **Regla de Break-Even:** Al alcanzar una ganancia no realizada equivalente a $+1.0 R$ (donde $R = |\text{Entrada} - SL|$), el stop-loss se desplaza automáticamente al precio de entrada para eliminar el riesgo financiero.
4. **Horizonte Temporal Fijo ($\tau$):** Para temporalidad de 15m, la duración máxima esperada de la operación es de **12 a 15 barras (3.0 a 3.75 horas)**. Si tras 15 barras la posición no ha alcanzado el $TP$ ni el $SL$, se cierra automáticamente al precio de mercado por decaimiento temporal.
5. **Apalancamiento Base 1x:** La evaluación formal y métricas de Sharpe se calculan estrictamente a 1x (sin margen prestado). Se calcula adicionalmente la excursión adversa máxima (*Maximum Adverse Excursion - MAE*) para cuantificar el apalancamiento físicamente admisible antes de liquidación.
6. **Tamaño de Posición Fijo por $R$:** Tamaño normalizado según el riesgo monetario tolerado por operación ($1\% - 2\%$ del equity disponible). Prohibida cualquier progresión geométrica, martingala o incremento de exposición tras operaciones perdedoras.
