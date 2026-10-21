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
