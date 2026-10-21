# Plan Detallado de Implementación — Etapa 1
*Verificación de API, Pipeline de Ingestión, Validación y Almacenamiento Reproducible*

---

## 1. Objetivos de la Etapa 1

1. Proporcionar un cliente HTTP GET público para la API swap USDT-M de BingX sin credenciales ni endpoints de trading.
2. Descargar de forma reproducible las velas históricas de 15m para `BTC-USDT` con paginación robusta y respeto de rate limits.
3. Validar la integridad de los datos:
   - Detección y exclusión estricta de la vela abierta (incompleta).
   - Detección de huecos temporales (gaps $> 15$ minutos).
   - Detección de duplicados y orden cronológico ascendente estricto.
   - Validación de esquema de tipos y consistencia OHLCV ($High \ge \max(Open, Close)$, $Low \le \min(Open, Close)$, $Volume \ge 0$).
4. Almacenar los datos particionados en formato Apache Parquet (`data/historical/bingx_btc_usdt_15m.parquet`) con un archivo de metadatos `manifest.json` que incluya el hash SHA-256 para garantizar inmutabilidad.
5. Crear el módulo point-in-time para datos exógenos de Clase B (Fear & Greed y eventos macro).

---

## 2. Archivos a Construir

| Archivo | Responsabilidad Técnica |
|---|---|
| `src/data/bingx_client.py` | Cliente HTTP nativo (`urllib` o `requests`) para consultar `/openApi/swap/v3/quote/klines`, `/openApi/swap/v2/quote/fundingRate`, `/openApi/swap/v2/quote/openInterest`. Manejo de reintentos con retroceso exponencial (*exponential backoff*). |
| `src/data/validator.py` | Función `validate_market_data(df)`: comprueba continuidad temporal a 15m, identifica huecos, detecta timestamps repetidos y descarta velas donde `timestamp + 15m > current_utc_time`. |
| `src/data/storage.py` | Funciones `save_dataset(df, path)` y `load_dataset(path)`: escribe en Parquet comprimido (snappy/zstd), genera el hash SHA-256 del archivo binario y actualiza `data/manifest.json`. |
| `src/data/context_loader.py` | Conectores para Fear & Greed (`alternative.me`) y calendario económico con estricta asignación temporal point-in-time a las barras de 15m. |
| `tests/test_bingx_data.py` | Batería de pruebas unitarias automatizadas con mocks de red (sin depender de conexión a internet para pasar los tests). |

---

## 3. Pruebas Unitarias Planificadas (`tests/test_bingx_data.py`)

1. **`test_discard_open_candle`:** Simular una respuesta de API con una vela cuyo timestamp cierra en el futuro relativo al momento de consulta; verificar que es descartada del dataset limpio.
2. **`test_detect_time_gaps`:** Introducir un salto artificial de 30 minutos (omisión de 1 vela) y comprobar que el validador reporta el gap con timestamp de inicio y fin.
3. **`test_detect_duplicates`:** Introducir filas duplicadas con el mismo timestamp y verificar que se genera un error o se desduplica deterministamente.
4. **`test_ohlc_invariants`:** Simular una vela con $High < Low$ o $High < Open$ y comprobar que el validador la rechaza.
5. **`test_storage_manifest_sha256`:** Guardar un dataset de muestra, calcular su SHA-256, verificar coincidencia con el manifest, modificar un byte y validar que la verificación de integridad falla.
6. **`test_point_in_time_fng`:** Verificar que el valor del Fear & Greed de las 00:00 UTC no se asigna a barras anteriores a las 00:05 UTC del mismo día.

---

## 4. Criterios de Aceptación para Dar por Concluida la Etapa 1

- [ ] Todas las pruebas de `tests/test_bingx_data.py` pasan en verde (`pytest`).
- [ ] Ejecución exitosa de un script de descarga que genere el dataset Parquet de desarrollo/validación sin gaps no documentados.
- [ ] El archivo `data/manifest.json` contiene la URL de origen, fecha de descarga, número total de barras y el hash SHA-256 verificado.
- [ ] Cero dependencias de trading ni claves privadas.
