# Catálogo de Hipótesis y Clasificación Crítica del Informe Discrecional
*Documento de referencia metodológica v2.0*  
*Propósito:* Traducir un informe descriptivo y discrecional en un catálogo riguroso de hipótesis científicas comprobables, categorizadas por su viabilidad de contrastación cuantitativa determinista.

---

## 1. Criterios de Clasificación

- **Clase A — Formalizable y Backtesteable Inmediatamente (OHLCV + Funding/OI en 15m):**  
  Reglas algorítmicas deterministas donde las condiciones de entrada, salida, stop-loss e invalidación están matematizadas sin juicio humano ni ambigüedad.
- **Clase B — Contexto de Temporalidad Superior / Exógeno (Point-in-Time estricto):**  
  Factores macroeconómicos, sentimiento y marcos temporales mayores (1h, 4h, 1D). Requieren timestamp exacto de publicación para impedir fuga de datos hacia el pasado (*look-ahead bias*).
- **Clase C — No Backtesteable con Datos Disponibles (Solo Observación / Exploratorio):**  
  Conceptos de flujo de órdenes de ultra-alta frecuencia (1s), lectura visual libre de gráficos, o patrones subjetivos sin algoritmo unívoco. No tienen capacidad de autorizar operaciones en esta fase.

---

## 2. Clasificación Detallada de Ideas e Hipótesis

### 2.1 Clase A: Reglas Cuantitativas y Estructura Técnica (15m)

| ID | Concepto Original | Definición Operacional Algorítmica Propuesta | Parámetros a Preregistrar |
|---|---|---|---|
| **A-1** | Soportes y Resistencias ("3 contactos") | Detección de pivotes locales (Fractales de Williams con retardo $k=3$ barras). Un nivel se confirma si existen $\ge 3$ pivotes dentro de una banda de tolerancia $\pm 0.25\% \times \text{Precio}$. | Lookback de fractales ($k=3$), banda de tolerancia ($\epsilon = 0.25\%$), mínimo toques ($N=3$). |
| **A-2** | Inversión de Roles (S/R Flip) | Perforación de un nivel confirmado por un cierre completo de barra ($C > R$ o $C < S$) con posterior retest dentro de $\epsilon$ en las siguientes $M$ barras sin cierre adverso. | Tolerancia retest ($\epsilon$), ventana máxima de retest ($M=12$ barras). |
| **A-3** | Filtro de Tendencia EMA/SMA | Alineación de medias móviles exponenciales: Sesgo Alcista si $\text{EMA}(21) > \text{EMA}(50) > \text{EMA}(200)$ y precio $> \text{EMA}(200)$. Sesgo Bajista simétrico. | Periodos de medias (21, 50, 100, 200). Se evalúa también su versión calculada en 1h/4h. |
| **A-4** | RSI y Divergencias Clásicas | Pivotes de RSI(14) contrastados con pivotes de precio con retraso fijo para evitar lookahead. Divergencia alcista: mínimo más bajo en precio y mínimo más alto en RSI. **Condición estricta:** Requiere ruptura del nivel de confirmación previo para activar señal. | Periodo RSI (14), retardo de confirmación de pivote ($k=3$), umbrales de sobreventa/sobrecompra (30/70). |
| **A-5** | MACD Normalizado en Extremos | **Corrección metodológica §3.1:** Se descartan umbrales fijos (-500/+1000). Se utiliza el MACD estandarizado z-score o normalizado por precio: $\text{MACD}_{\%} = (\text{EMA}_{12} - \text{EMA}_{26}) / \text{Close}$. Cruce en extremos definidos por percentiles históricos rodantes ($P_{95}$ / $P_{5}$). | Periodos (12, 26, 9), ventana rodante de normalización (1000 barras), percentil de extremo. |
| **A-6** | BBWP (Bollinger Band Width Percentile) | **Corrección metodológica §3.1:** El informe lo llama "Bull & Bear Power Volatility"; la definición cuantitativa válida es *Bollinger Band Width Percentile*. Percentil rodante del ancho de bandas $(Upper - Lower) / SMA_{20}$ sobre un histórico de $L$ periodos. Señal de compresión: $\text{BBWP} < 10\%$; expansión: $\text{BBWP} > 90\%$. | Periodo BB (20, std 2.0), lookback percentil ($L=252$ barras). Se evalúa en 15m y 1h/4h. |
| **A-7** | Volumen en Rupturas y Filtro de Falsa Ruptura | Ruptura válida exige $\text{Volumen} > 1.8 \times \text{SMA}_{20}(\text{Volumen})$. Falsa ruptura: cierre dentro de la zona en la barra inmediatamente posterior; señal de reversión contraria. | Multiplicador de volumen ($1.8\times$), ventana SMA volumen (20). |
| **A-8** | Patrones Geométricos Algorítmicos | Doble techo/suelo detectado por algoritmo determinista de extremos locales con cuello horizontal y tolerancia $\pm 0.2\%$. Triángulos solo si las líneas de tendencia convergentes tienen $\ge 2$ toques cada una y $R^2 > 0.90$. | Mínimo toques por directriz, $R^2$ lineal, tolerancia de cuello. |
| **A-9** | Gestión de Riesgo Basada en R | SL estructural fijado en la invalidación técnica (último pivote adverso o $\pm 2 \cdot \text{ATR}$). TP fijado en ratio beneficio/riesgo (ej. $1.5R, 2.0R$). Break-even activado al alcanzar $+1.0R$. | Distancia ATR para SL, ratios de R para TP y Break-Even. |

---

### 2.2 Clase B: Contexto Exógeno y Temporalidad Superior (Point-in-Time)

| ID | Concepto | Fuente Oficial / API Propuesta | Tratamiento Temporal y Regla de Uso |
|---|---|---|---|
| **B-1** | Índice Fear & Greed | `https://api.alternative.me/fng/?limit=...` | **Corrección metodológica §3.1:** Rango oficial 0–100. Publicado a las 00:00 UTC diariamente. Se aplica a las barras de 15m **únicamente a partir de las 00:05 UTC** del día respectivo para garantizar point-in-time. Umbral de abstención pre-registrado (<25 o >75). |
| **B-2** | Calendario Macroeconómico (Eventos de 3 estrellas) | API pública (ForexFactory / TradingEconomics / Bureau of Labor Statistics) | Filtro de **abstención operativa obligatoria:** Prohibido emitir señales 60 minutos antes y 30 minutos después de CPI, PPI, NFP y FOMC Decisions. No se utiliza para predecir dirección. |
| **B-3** | DXY y Futuros S&P 500 / Nasdaq | Yahoo Finance / Fred / AlphaVantage | Variables de régimen de apetito por riesgo (Risk-On / Risk-Off). Retorno diario rodante y correlación a 30 días. Vela de 1D cerrada únicamente. |
| **B-4** | Gaps de Futuros CME (BTC) | Velas horarias del contrato BTC de CME | **Corrección metodológica §3.1:** Gap definido como $\text{Low}_{lunes} > \text{High}_{viernes}$ (o viceversa) en apertura de mercado dominical CME. Hipótesis de relleno con horizonte máximo prefijado (ej. 5 días bursátiles). Si no se rellena en 5 días, se declara expirado. |
| **B-5** | Funding Rate y Open Interest de BingX | API BingX Swap USDT-M (`/quote/fundingRate`, `/quote/openInterest`) | Funding positivo extremo (>0.03% por 8h) o negativo (< -0.01%): filtro de sobre-apalancamiento del mercado minorista. Variación de OI como confirmación de flujo. |

---

### 2.3 Clase C: No Backtesteable con Datos OHLCV Estándar (Observación / Futuro)

| ID | Concepto | Motivo de Inviabilidad Actual | Decisión de Proyecto |
|---|---|---|---|
| **C-1** | Order Flow / Aggr.trade (Ticks 1s, Órdenes >$100k) | Requiere feed tick-by-tick y libro de órdenes L2 continuo de alta frecuencia no disponible en histórico 15m. | No puede aprobar ni gobernar señales actuales. Se propone script opcional para registrar streams en vivo hacia el futuro. |
| **C-2** | "Absorción" en velas de 1 a 10 segundos | Sin datos de microestructura ni footprint de órdenes de BingX. | Excluida de las reglas de decisión de Nivel 0 y Nivel 1. |
| **C-3** | Lectura visual discrecional / subjetiva de figuras | Juicio cualitativo que no puede ser replicado por una función matemática determinista. | El agente visual solo puede emitir una *hipótesis estructurada* sujeta a contraste frente a placebo y validación de concordancia. |

---

## 3. Discrepancias y Correcciones Metodológicas Incorporadas (§3.1)

1. **BBWP:** Formalizado como *Bollinger Band Width Percentile*. Se evalúa de forma prioritaria en temporalidades superiores (1h, 4h, 1D) como filtro de régimen, y su aplicación directa a 15m se define como experimento de prueba explícita.
2. **MACD:** Umbrales fijos desestimados por violar la no-estacionariedad del precio de BTC; sustituidos por el ratio estandarizado respecto al precio y desviación típica.
3. **Probabilidades de Ruptura (ej. "70%"):** Tratadas como afirmaciones no fundamentadas; cualquier porcentaje será medido con su respectivo intervalo de confianza por bootstrap empírico.
4. **Gaps CME:** Sometidos a un horizonte de expiración estricto con costos de acarreo incluidos para evitar el sesgo de supervivencia ("eventualmente se llena").
5. **Apalancamiento:** Restringido a 1x en la evaluación base; toda gestión se estandariza en múltiplos del riesgo inicial $R$.
6. **Jerarquía "La capa superior prevalece":** Sometida a prueba formal de **ablación** (Experimento D) para verificar si el filtro macro/sentimiento añade o destruye valor frente a las reglas técnicas aisladas.
7. **Casos anecdóticos (2017, 2022):** Descartados como evidencia; solo se aceptan resultados derivados del protocolo pre-registrado.
