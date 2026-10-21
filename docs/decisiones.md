# Registro de Decisiones Abiertas y Recomendaciones Técnicas (v2.0)
*Sistema multiagente de investigación y señales BTC-USDT (BingX, 15m)*

Este documento formaliza las decisiones metodológicas, cuantitativas y de infraestructura abiertas para la aprobación del usuario antes de la ejecución de backtests y agentes.

---

## 1. Historia de Datos a Descargar y Partición Temporal

- **Contexto:** Las velas de 15 minutos en BingX perpetuo BTC-USDT tienen alta liquidez y representatividad desde 2022. Necesitamos particiones con regímenes de mercado contrastados (mercado bajista 2022, recuperación 2023, ciclo alcista / lateral 2024–2026).
- **Opciones consideradas:**
  - *Opción A (Recomendada):* Partición cronológica 3 tramos:
    - **Desarrollo y Selección:** 2022-01-01 a 2024-06-30 (~87,000 barras de 15m, 2.5 años). Abarca mercado bajista completo de 2022, acumulación 2023 y rally inicial de ETFs.
    - **Validación / OOS intermedio:** 2024-07-01 a 2025-06-30 (~35,000 barras de 15m, 1 año). Evaluación de selección intermedia.
    - **Holdout Intocable:** 2025-07-01 a la fecha actual (~45,000 barras de 15m, >1.2 años). Se congela y solo se ejecuta **una sola vez** tras finalizar toda la investigación.
  - *Opción B:* Solo 2 años (2024–2026). Inadecuado: sesga la muestra a un solo régimen y produce menos de 70,000 barras totales.
- **Recomendación:** **Opción A**. Ofrece más de 160,000 barras de 15m, múltiples regímenes de volatilidad y suficiente potencia estadística sin consumir el holdout prematuramente.

---

## 2. Modelo de Costos de Ejecución (15m BTC-USDT BingX)

- **Contexto:** En temporalidad de 15m el turnover es elevado. Subestimar costos invalida cualquier conclusión de rentabilidad.
- **Opciones consideradas:**
  - *Opción A (Conservadora - Recomendada):* 
    - Comisión: **0.05% taker** por lado (0.10% round-trip) según la tabla oficial de BingX Swap USDT-M.
    - Deslizamiento (Slippage): **0.02%** por lado (asume cruce de libro en apertura de barra).
    - Funding rate: Tasa real histórica de BingX (`/quote/fundingRate`) aplicada a las posiciones abiertas a las 00:00, 08:00 y 16:00 UTC.
    - Costo round-trip base: **0.14% + funding**. Estrés de costos en evaluación: **x2 (0.28% round-trip)**.
  - *Opción B (Optimista):* Asumir ejecución maker al 0.02% con 0% de slippage. Peligroso: las órdenes límite en rupturas frecuentemente sufren de selección adversa (*adverse selection*).
- **Recomendación:** **Opción A**. La hipótesis solo es viable si sobrevive al costo de taker completo y al estrés x2.

---

## 3. Fuentes y Licencias de Datos Exógenos (Clase B)

- **Contexto:** Se requiere trazabilidad, gratuidad, APIs estables y disponibilidad point-in-time estricta.
- **Propuesta por variable:**
  1. **Fear & Greed Index:** API pública `https://api.alternative.me/fng/?limit=0&format=json`. Rango 0–100, actualización diaria. Regla point-in-time: disponible en el pipeline a partir de las 00:05 UTC.
  2. **Calendario Macroeconómico:** Extracción de eventos de alto impacto (3 estrellas: CPI, PPI, NFP, FOMC) mediante feed público ICS/JSON (TradingEconomics / ForexFactory público) con cache local inmutable en `data/macro/calendar_events.parquet`.
  3. **DXY & Futuros US (S&P 500, Nasdaq):** Datos diarios de Yahoo Finance (`yfinance` para descarga de cierre de 1D) o St. Louis FRED (Federal Reserve Economic Data). Solo barras de 1D cerradas del día anterior.
  4. **Gaps CME BTC:** Velas horarias del futuro CME BTC descargables desde Yahoo Finance (`BTC=F`) o investing.com. Definición estricta: ventana de gap de fin de semana, horizonte máximo de 5 días hábiles.
  5. **Funding & OI BingX:** Endpoints oficiales `/openApi/swap/v2/quote/fundingRate` y `/openApi/swap/v2/quote/openInterest`.

---

## 4. Proveedor y Modelo LLM para Agentes y Visión

- **Contexto:** Los agentes deben generar salidas estructuradas JSON con Pydantic. El agente visual debe interpretar imágenes renderizadas deterministas.
- **Opciones consideradas:**
  - *Opción A (Recomendada):* Modelos Gemini (Flash para investigación textual/código por velocidad y bajo costo de tokens; Flash/Pro para análisis visual con inspección de charts generados con matplotlib).
  - *Opción B:* OpenAI (GPT-4o / GPT-4o-mini) o modelos locales (Ollama / Llama-3-vision).
- **Recomendación:** **Opción A** o el proveedor preferido por el usuario mediante variables de entorno (`GEMINI_API_KEY` o `OPENAI_API_KEY`). Si no hay API key configurada en `.env`, el sistema opera en modo "mock determinista" para pruebas sin costo.

---

## 5. Canal de Alertas (Nivel 1)

- **Contexto:** El sistema de Nivel 1 emite alertas `LONG / SHORT / NEUTRAL`.
- **Opciones consideradas:**
  - *Opción A (Recomendada):* Alerta por **Telegram Bot** (vía webhook/bot API simple HTTP POST, solo requiere `TELEGRAM_BOT_TOKEN` y `CHAT_ID`) y guardado simultáneo en archivo local JSONL estructurado (`reports/signals_log.jsonl`).
  - *Opción B:* Alerta por correo electrónico (SMTP). Menos interactiva y con mayor latencia.
  - *Opción C:* Registro exclusivo en consola / archivo JSONL local (modo silencioso).
- **Recomendación:** **Opción A** con fallback a Opción C si no hay credenciales de Telegram configuradas en `.env`.

---

## 6. Registro de Flujo de Órdenes y Liquidaciones en Vivo (Clase C)

- **Contexto:** Los datos de microestructura de 1 segundo / aggr.trade no están en el histórico de velas de BingX.
- **Opciones:**
  - *Opción A (Recomendada):* Crear un script de fondo liviano e independiente (`scripts/recorder_orderflow.py`) que se conecte al WebSocket público de trades/liquidaciones de BingX y almacene los eventos grandes (>$100k) en SQLite o Parquet diario. Esto acumulará datos reales fuera de muestra para futuras versiones sin interferir en la versión actual.
  - *Opción B:* Ignorar completamente la Clase C en esta versión.
- **Recomendación:** **Opción A**. Permite sembrar la base de datos futura sin violar las restricciones actuales.

---

## 7. Umbrales de Aceptación Cuantitativos (Pre-registro Propuesto)

Los siguientes umbrales se proponen para el archivo `config/acceptance.yaml` antes de tocar el holdout:
- **Muestra mínima:** $\ge 50$ operaciones fuera de muestra ($< 30$ operaciones = veredicto `INCONCLUSIVE` automático).
- **Expectativa neta por operación:** $> 0.00$ USDT, con cota inferior del IC 95% bootstrap $> -0.10R$.
- **Profit Factor neto:** $\ge 1.30$.
- **Sharpe Ratio anualizado (15m):** $\ge 1.00$ y **Deflated Sharpe Ratio (DSR):** $\ge 0.95$ (corrigiendo por el número total acumulado de variantes probadas).
- **Máximo Drawdown:** $\le 20.0\%$ con duración máxima $\le 90$ días.
- **Retención fuera de muestra (Sharpe OOS / Sharpe IS):** $\ge 50\%$.
- **Estrés de costos x2:** Expectativa neta permanece positiva ($> 0$).
- **Concentración de ganancias:** El 5% superior de operaciones no debe explicar más del 60% de la ganancia neta total.
- **Superación de benchmarks:** Sharpe neto superior a Buy & Hold y superior a la distribución de 1,000 simulaciones de entradas aleatorias pareadas por duración/exposición ($p < 0.05$).
