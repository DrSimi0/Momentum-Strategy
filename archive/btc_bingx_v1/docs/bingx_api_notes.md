# Notas de Verificación de la API Oficial de BingX (Swap USDT-M)
*Fecha de verificación:* 2026-10-21 UTC  
*Documentación oficial de referencia:* [BingX Open API Documentation](https://bingx-api.github.io/docs/#/swapV2/)  
*Base URL Pública:* `https://open-api.bingx.com`

---

## 1. Identificación del Instrumento y Especificaciones
- **Símbolo exacto:** `BTC-USDT` (nótese el guion medio `-`, a diferencia de Binance que usa `BTCUSDT`).
- **Tipo de contrato:** Perpetuo Swap USDT-M (margen y liquidación en USDT).
- **Precisión de precio (`pricePrecision`):** 1 decimal (mínimo tick = $0.10 USDT).
- **Precisión de cantidad (`quantityPrecision`):** 4 decimales (mínimo paso = $0.0001$ BTC).
- **Tamaño mínimo de orden (`tradeMinUSDT`):** 2 USDT (o $0.0001$ BTC).
- **Tarifas base oficiales (VIP0):**
  - **Maker Fee Rate:** `0.0002` ($0.02\%$).
  - **Taker Fee Rate:** `0.0005` ($0.05\%$).
- **Fecha de lanzamiento del contrato (`launchTime`):** `1586275200000` (8 de abril de 2020 00:00:00 UTC).

---

## 2. Endpoints Públicos de Consulta (Solo Lectura, sin autenticación)

### 2.1 Velas Históricas (Klines)
- **Endpoint:** `GET /openApi/swap/v3/quote/klines`
- **Autenticación:** Pública (no requiere clave API ni firma).
- **Parámetros:**
  - `symbol`: `BTC-USDT` (obligatorio)
  - `interval`: `15m` (soportados: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 1w, 1M)
  - `limit`: Máximo **1000** velas por petición (peticiones solicitando $>1000$ son limitadas automáticamente por el servidor a 1000).
  - `startTime`: Timestamp Unix en milisegundos (opcional).
  - `endTime`: Timestamp Unix en milisegundos (opcional).
- **Estructura de respuesta:**
  ```json
  {
    "code": 0,
    "msg": "",
    "data": [
      {
        "time": 1792553400000,
        "open": "82754.6",
        "close": "82737.9",
        "high": "82837.8",
        "low": "82737.9",
        "volume": "26.6703"
      }
    ]
  }
  ```
- **Orden de los datos:** **DESCENDENTE** (la primera vela `data[0]` es la más reciente; la última `data[-1]` es la más antigua dentro de la ventana consultada).
- **Detección de vela abierta:**
  - La vela en curso (abierta) tiene timestamp $T_{open}$ tal que:
    $$\text{now}() < T_{open} + \Delta T$$
    Para 15m ($\Delta T = 15 \times 60 \times 1000\text{ ms} = 900,000\text{ ms}$), si $\text{now}() < \text{time} + 900,000$, la vela **está incompleta y debe descartarse** para evitar look-ahead bias y datos cambiantes.

### 2.2 Tasa de Financiación (Funding Rate)
- **Endpoint:** `GET /openApi/swap/v2/quote/fundingRate`
- **Autenticación:** Pública.
- **Parámetros:** `symbol=BTC-USDT`
- **Frecuencia:** Cada 8 horas (00:00, 08:00, 16:00 UTC). Devuelve el histórico de liquidaciones de funding recientes con `{symbol, fundingRate, fundingTime, markPrice}`.

### 2.3 Interés Abierto (Open Interest)
- **Endpoint:** `GET /openApi/swap/v2/quote/openInterest`
- **Autenticación:** Pública.
- **Parámetros:** `symbol=BTC-USDT`
- **Respuesta:** Snapshot puntual `{openInterest, symbol, time}` expresado en USDT.

---

## 3. Límites de Tasa (Rate Limits) y Buenas Prácticas
- Límite por IP para endpoints públicos de cotización: hasta 100 peticiones por minuto de forma segura.
- Paginación histórica: Para descargar años de velas de 15m (~35,040 velas/año), se debe iterar en lotes de 1000 velas en sentido ascendente o descendente respetando un intervalo de espera pasivo de 200–300 ms entre llamadas para evitar bloqueos HTTP 429.
