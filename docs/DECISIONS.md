# Registro de decisiones (v4 — momentum intradía ES/NQ)

Formato: decisión · alternativas · motivo. Ordenadas por fecha de adopción.

## D-001 · Archivo completo de lo anterior, sin reutilizar infraestructura (F0, 2026-10-21)
- **Decisión:** se archiva todo el contenido versionado en `archive/btc_bingx_v1/` con `git mv`, más el tag `archive-btc-bingx-v1`. Los datos y reportes no versionados se mueven a `archive/btc_bingx_v1/local_untracked/` (ignorado por git).
- **Alternativas:** reutilizar métricas o bootstrap de v1.x; rama de archivo en vez de tag.
- **Motivo:** el código anterior está acoplado a cripto (funding, apalancamiento, anualización 24/7, velas de 4h/15m). Reescribir unas pocas funciones genéricas es más limpio que adaptar y arrastrar supuestos ajenos. El tag es inmutable y basta para restaurar.

## D-002 · Manejo de la clave (F0)
- **Decisión:** `src/settings.get_api_key()` lee `DATABENTO_API_KEY`; si existe `.env` local se usa solo para poblar esa variable (lector propio de 15 líneas, sin `python-dotenv`). `.env` y `.env.*` están en `.gitignore` desde antes del primer commit; `tests/test_secrets.py` escanea los archivos versionables con el patrón `db-` + 20 o más alfanuméricos.
- **Alternativas:** `python-dotenv`; exigir que la variable se exporte manualmente.
- **Motivo:** una dependencia menos y el mismo comportamiento.
- **Nota:** el usuario pegó la clave en el chat. Se guardó solo en `.env` local (ignorado por git). Se recomienda rotarla.

## D-003 · Configuración de pytest
- **Decisión:** `pythonpath = ["."]` en `pyproject.toml` para importar `src` desde las pruebas, sin `tests/__init__.py`.

## D-004 · Métricas, simulación y bootstrap estacionario (F2/F3)
- **Decisión:** 
  1. El ratio de Sharpe se calcula sobre la serie diaria de todos los días hábiles regulares (retorno = PnL neto / nocional de entrada a las 15:30; 0.0 en días sin operación) anualizado por $\sqrt{252}$. Esto garantiza que hipótesis con distinta selectividad sean estrictamente comparables.
  2. El p-valor no paramétrico bajo $H_0$ se obtiene mediante Bootstrap Estacionario (Politis & Romano, 1994) sobre la serie de retornos centrada ($r_t - \bar{r}$), evaluando la probabilidad unilateral de generar un Sharpe tan extremo como el observado.
  3. Para las 8 hipótesis primarias (H1 a H4 en ES y NQ) se implementa el procedimiento de control de FWER de Holm-Bonferroni sobre los p-valores.
- **Alternativas:** Sharpe calculado únicamente sobre los días con trade; prueba t ordinaria dependiente de supuestos de normalidad.
- **Motivo:** Cumple estrictamente con la especificación de rigor econométrico del prompt maestro v4 y las decisiones acordadas en el plan de implementación.

## D-005 · Ajuste del rango temporal a 2018–2026 para respetar el límite de costo (F1)
- **Decisión:** El costo total original de 2011–2026 superaba los USD 25.00 establecidos como límite duro en la especificación. Tras consultar al usuario, se aprobó acotar el análisis al periodo 2018–2026 utilizando contratos continuos por volumen (`ES.v.0` y `NQ.v.0`), con un costo total verificado de USD 22.74 (incluyendo los últimos días de diciembre de 2017 para el cierre previo). Las particiones quedan: Desarrollo (2018–2021, 4 años), Validación (2022–2023, 2 años), y Prueba Final / Holdout (2024–2026, ~2.8 años).
- **Alternativas:** Descargar únicamente ES 2011–2026 por USD 20.16; autorizar consumo de USD 39.77 o USD 56.95.
- **Motivo:** Mantiene el análisis comparativo completo en ambos instrumentos (ES y NQ) con más de 2,100 sesiones de mercado, cumpliendo estrictamente con el presupuesto máximo fijado.

## D-006 · Confirmación empírica de la convención de `ts_event` con datos reales (F1)
- **Decisión:** Se ratifica que `ts_event` representa el inicio del intervalo de la barra de 1 minuto. Los picos de volumen sobre más de 3.1 millones de barras reales confirman:
  - Apertura regular: `09:30` ET pasa de 2,598 contratos a 12,617 contratos medios/minuto.
  - Cierre regular / MOC: `15:59` ET registra el máximo absoluto con 50,117 contratos medios/minuto.
  - En consecuencia, la entrada de la estrategia opera en el open de `15:30` ET y la salida liquida en el close de `15:59` ET.
- **Alternativas:** Asumir `ts_event` como fin del intervalo.
- **Motivo:** Verificación empírica rigurosa exigida en el plan de implementación.

## D-007 · Congelamiento del pre-registro metodológico previo a la prueba final (F5)
- **Decisión:** Se congelan formalmente todas las hipótesis, particiones temporales (Desarrollo: 2018–2021, Validación: 2022–2023, Final: 2024–2026), modelo de costos de transacción y criterios de aceptación (A1 a A6) en `docs/PREREGISTRO.md` bajo el tag de git inmutable `preregistro-congelado`.
- **Alternativas:** Ajustar parámetros o descartar hipótesis tras observar el periodo de desarrollo/validación antes de ir a holdout.
- **Motivo:** Garantizar máxima honestidad estadística y eliminar por diseño el sesgo de selección y sobreajuste p-hacking.

## D-008 · Veredicto final del Holdout: Rechazo unánime de las hipótesis de momentum intradía (F6/F7)
- **Decisión:** Se declara formalmente el veredicto **REJECTED** para las 8 hipótesis primarias evaluadas en los futuros ES y NQ. Se genera el candado `reports/FINAL_RUN.lock`, se guarda el desglose cuantitativo reproducible en `reports/results.json`, y se publica el informe en `reports/informe_momentum_intradia.md`.
- **Alternativas:** Re-optimizar umbrales, filtrar por subregímenes o alterar reglas tras ver los resultados del holdout.
- **Motivo:** En investigación cuantitativa rigurosa, un resultado negativo fuera de muestra es un resultado definitivo. Modificar parámetros tras consumir el holdout violaría los principios científicos del pre-registro y generaría resultados espurios.
