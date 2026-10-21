# Sistema Multiagente de Investigación y Señales BTC-USDT (BingX, 15m)
*Versión 2.0 — Proyecto Académico y de Experimentación Cuantitativa Determinista*

---

## 1. Resumen Ejecutivo y Alcance

Este repositorio implementa un entorno de investigación cuantitativa, simulación y generación de señales en modo solo-observación para el contrato perpetuo **BTC-USDT de BingX (USDT-M)** en temporalidad de **15 minutos**.

### Límites y Restricciones Operativas (No Negociables)
- **Cero Ejecución de Órdenes:** El sistema solo emite salidas `LONG / SHORT / NEUTRAL` con parámetros de invalidación y registro de razones. No se ejecutan órdenes de compra ni venta.
- **Sin Claves Privadas de Trading:** No se requiere ni permite el uso de endpoints de trading ni gestión de capital.
- **Evaluación Base 1x:** Sin apalancamiento en las métricas base.
- **Aislamiento Determinista:** Los modelos LLM y agentes nunca aprueban estrategias, calculan métricas ni modifican datos de backtest. Todo cálculo estadístico es determinista y probado contra ejemplos numéricos manuales.

---

## 2. Documentación Metodológica y Primer Entregable

Todos los componentes de diseño, arquitectura y pre-registro se encuentran formalizados en la carpeta [`docs/`](docs/):

1. **[docs/repo_inspection.md](docs/repo_inspection.md):** Inspección exhaustiva del repositorio. Diagnóstico de componentes reutilizables de la v1 (métricas de riesgo, bootstrap, DSR) y componentes por construir para la v2.
2. **[docs/bingx_api_notes.md](docs/bingx_api_notes.md):** Especificación técnica de la API swap USDT-M de BingX (símbolo `BTC-USDT`, comisiones maker 0.02% / taker 0.05%, paginación, descarte de vela abierta).
3. **[docs/hipotesis_informe.md](docs/hipotesis_informe.md):** Catálogo crítico clasificado en **Clase A** (formalizable y backtesteable en 15m), **Clase B** (contexto point-in-time exógeno) y **Clase C** (no falsable / observación), con las 10 correcciones metodológicas de §3.1.
4. **[docs/decisiones.md](docs/decisiones.md):** Lista formal de decisiones abiertas con opciones, análisis de impacto y recomendación técnica.
5. **[docs/preregistro.md](docs/preregistro.md):** Protocolo de evaluación científica, hipótesis nula, fórmulas con anualización para 15m ($\sqrt{35,040}$), experimentos A/B/C/D (ablación) y robustez estadística.
6. **[docs/etapa1_plan.md](docs/etapa1_plan.md):** Plan detallado de la Etapa 1 (módulo de datos, validación temporal y almacenamiento inmutable con hash SHA-256).

---

## 3. Estado de la Suite de Pruebas

Los 57 tests unitarios existentes continúan en estado verde:
```bash
python -m pytest
# 57 passed in 16.81s
```
