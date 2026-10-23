# Informe Gráfico de Drawdown: Relación Tiempo vs Porcentaje
**Proyecto:** Momentum Trend-Following Strategy  
**Temporalidades Analizadas:** H4 (4 horas), H1 (1 hora), M15 (15 minutos), M5 (5 minutos)  
**Ventana Temporal:** 2010 - 2026 (16 años continuos de futuros NQ y ES)  
**Capital Base:** $50,000 USD fijo  
**Estado:** Exploratorio (sin holdout virgen)

---

## 1. Introducción y Conceptos Clave en Español Sencillo

### ¿Qué es el Drawdown y por qué se mide contra el tiempo?
En trading cuantitativo, el **Drawdown** representa la caída acumulada desde el punto más alto de ganancias (*Peak* o "pico histórico") hasta el punto más bajo antes de lograr un nuevo récord.

No basta con saber *cuánto dinero se pierde* (la profundidad del drawdown); es igual o más importante saber **cuánto tiempo dura el sufrimiento** (la duración del drawdown):
1. **Profundidad (% y $):** Cuánto porcentaje del capital inicial se pierde en la peor racha negativa. Un drawdown del 50% significa que de una cuenta de $50,000 USD se perdieron $25,000 USD desde el último pico.
2. **Duración en el Tiempo (Días / Meses de mercado):** Cuántos días o meses transcurren desde que la cuenta empieza a caer hasta que logra recuperarse y marcar un nuevo máximo histórico. Si una estrategia pasa 2 años sumergida en pérdidas, la mayoría de los traders o fondos abandonan el sistema antes de que se recupere.

---

## 2. Metodología de Cálculo

Para garantizar consistencia y comparabilidad entre todas las temporalidades:
* **Fórmula de Drawdown Porcentual:**
  $$\text{Drawdown}_t (\%) = \frac{\text{Peak}_t - \text{Equity}_t}{\$50,000} \times 100\%$$
* **Duración del Drawdown:** Número de días hábiles de negociación que transcurren entre el pico histórico y la recuperación total a un nuevo pico.
* **Capital Fijo:** $50,000 USD para 1 contrato completo (H4/H1/M15/M5).

---

## 3. Gráfica 1: Curvas de Drawdown Submarino en el Tiempo (2010 - 2026)

Esta gráfica muestra la "inmersión bajo el agua" diaria de cada estrategia a lo largo de los 16 años evaluados. El eje horizontal es el año cronológico y el eje vertical es el porcentaje de drawdown (donde 0% representa nuevos máximos históricos y caídas negativas representan pérdidas acumuladas):

![Curvas de Drawdown Submarino 2010-2026](file:///C:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/figures/drawdown_temporal_series_comparative.png)

*(Copia en directorio de artefactos para renderizado en plataforma: [drawdown_temporal_series_comparative.png](file:///C:/Users/leono/.gemini/antigravity/brain/bad9add8-21bd-44f6-a0bb-469902521894/drawdown_temporal_series_comparative.png))*

### Interpretación por Paneles:
1. **Panel Superior (H4 - Swing Largo):** NQ 4h y ES 4h pasan períodos muy prolongados bajo el agua (especialmente 2015-2016 y 2022-2023). Aunque generan grandes ganancias al final, los retrocesos superan el 45% y pueden tardar más de 700 días de mercado (casi 3 años) en salir a flote.
2. **Segundo Panel (H1 - Swing Intermedio):** Presenta caídas aún más pronunciadas (ES 1h llega a 63% y NQ 1h a 107%). NQ 1h pierde más del 100% de la cuenta inicial durante su peor drawdown, lo que técnicamente representaría una llamada de margen o liquidación si no se utilizara apalancamiento micro.
3. **Tercer Panel (M15 - Intradía con Salida MOC):** La versión con cierre obligatorio a las 15:50 ET (*NQ 15m MOC Fix*) recorta significativamente las caídas prolongadas. No obstante, en 2022 sufre un drawdown del 47.0% ($23,505 USD), pero con recuperaciones más dinámicas al no cargar riesgo overnight.
4. **Panel Inferior (M5 - Intradía Alta Frecuencia):** Muestra el contraste más extremo:
   - *ES 5m Agresiva:* Registra el menor drawdown del proyecto (24.0% o $12,018 USD), con curvas submarinas muy cortas.
   - *NQ 5m Sin Volatilidad:* Se hunde hasta el 150.4% ($75,209 USD), pasando a terreno de patrimonio negativo (quiebra técnica) durante más de 2 años y medio consecutivos.

---

## 4. Gráfica 2: Relación Profundidad vs Duración (Dispersión)

Esta gráfica ubica a cada estrategia en un plano cartesiano de **Riesgo Profundo (Eje Y: Max Drawdown %)** frente a **Desgaste Temporal (Eje X: Duración en días de mercado)**:

![Relación Max Drawdown vs Duración](file:///C:/Users/leono/OneDrive/Documentos/QUANT%20TRADING/Momentum-Strategy/reports/figures/max_drawdown_vs_duracion_scatter.png)

*(Copia en directorio de artefactos: [max_drawdown_vs_duracion_scatter.png](file:///C:/Users/leono/.gemini/antigravity/brain/bad9add8-21bd-44f6-a0bb-469902521894/max_drawdown_vs_duracion_scatter.png))*

### Los Cuatro Cuadrantes del Riesgo:
* **Zona Verde (Bajo Drawdown y Rápida Recuperación):** *ES 5m Agresiva* es la única que reside aquí (Max DD 24%, duración menor a 350 días). Su limitación es que su ganancia anual es muy baja (+4.5%).
* **Zona Naranja (Drawdown Moderado / Alto con Larga Duración):** *NQ 4h* y *ES 4h*. El drawdown es del 45% al 47%, pero su recuperación requiere de 600 a 700 días de mercado.
* **Zona Roja (Riesgo Extremo / Quiebra):** *NQ 1h* (107% de drawdown) y *NQ 5m Sin Volatilidad* (150% de drawdown con más de 660 días sumergida). Estas estrategias son inviables para cualquier operador de futuros o prop firm.

---

## 5. Tabla Maestra de Duración y Profundidad del Drawdown

| Temporalidad | Estrategia | Max Drawdown ($ USD) | Max Drawdown (% s/$50k) | Duración Máxima (Días de mercado) | Duración Máxima (Meses aprox.) | ¿Apta para Prop Firm? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **H4** | NQ 4h EMA 20/200 + ATR 3.0 | -$23,800 USD | **47.6%** | 684 días | ~32 meses | ❌ No (Supera límite $3,000) |
| **H4** | ES 4h EMA 20/200 + ATR 3.0 | -$22,662 USD | **45.3%** | 618 días | ~29 meses | ❌ No |
| **H1** | NQ 1h EMA 20/200 + ATR 3.0 | -$53,730 USD | **107.5%** | 742 días | ~35 meses | ❌ No (Pérdida > 100%) |
| **H1** | ES 1h EMA 20/200 + ATR 3.0 | -$31,737 USD | **63.5%** | 815 días | ~38 meses | ❌ No |
| **M15** | NQ 15m EMA 20/80 + MOC Fix (15:45) | -$23,505 USD | **47.0%** | 412 días | ~19 meses | ❌ No en contrato completo |
| **M15** | NQ 15m Pre-Fix (Overnight accidental) | -$22,695 USD | **45.4%** | 405 días | ~19 meses | ❌ No |
| **M15** | ES 15m Línea Base | -$33,187 USD | **66.4%** | 710 días | ~33 meses | ❌ No |
| **M5** | ES 5m EMA 10/50 Agresiva | -$12,018 USD | **24.0%** | 335 días | ~15 meses | ⚠️ Requiere Micro (MES) |
| **M5** | NQ 5m EMA 20/80 + MOC + ATR | -$17,735 USD | **35.5%** | 390 días | ~18 meses | ⚠️ Requiere Micro (MNQ) |
| **M5** | NQ 5m MOC Sin Volatilidad | -$75,209 USD | **150.4%** | 668+ días | >31 meses (Quiebra) | ❌ Inviable |

---

## 6. Conclusiones y Aprendizaje Cuantitativo

1. **La falacia del retorno sin tiempo:** Una estrategia puede prometer un retorno acumulado alto (como NQ 1h con +$157k), pero su gráfica submarina demuestra que el inversor habría estado casi 3 años enteros perdiendo dinero o recuperando pérdidas previas, con una caída máxima de -$53,730 USD (destruyendo el capital inicial).
2. **El beneficio real del intradía:** Las estrategias intradía con salida obligatoria diaria antes del cierre (MOC) reducen a la mitad la duración máxima de los drawdowns (de 700-800 días a 300-400 días) porque eliminan el riesgo de gaps adversos del mercado nocturno.
3. **Escalamiento obligatorio a Contratos Micro:** Para que cualquiera de estas estrategias encaje en una cuenta con límites de drawdown de prop firm ($2,000 - $3,000 USD), el tamaño de posición debe reducirse obligatoriamente a contratos micro (MNQ / MES), operando con un riesgo por operación no mayor al 0.5% del capital disponible.
