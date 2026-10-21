"""Rutas, carga de configuración YAML y lectura segura de la clave de Databento.

La clave se lee únicamente de la variable de entorno ``DATABENTO_API_KEY``. Si existe
un archivo ``.env`` local (ignorado por git), se usa solo para poblar esa variable.
El valor de la clave nunca se imprime, se registra ni se devuelve en mensajes de error.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"
ENV_VAR = "DATABENTO_API_KEY"


class MissingApiKeyError(RuntimeError):
    """La variable DATABENTO_API_KEY no está definida o está vacía."""


def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_dotenv(path: Path) -> None:
    """Carga pares CLAVE=valor de ``.env`` en os.environ sin sobrescribir variables ya definidas."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def get_api_key(env_file: Path | None = None) -> str:
    """Devuelve la clave desde la variable de entorno; lanza un error claro si falta."""
    _load_dotenv(env_file or ROOT / ".env")
    key = os.environ.get(ENV_VAR, "").strip()
    if not key or key == "pon_tu_clave_aqui":
        raise MissingApiKeyError(
            f"Falta la variable de entorno {ENV_VAR}. Crea un archivo .env (ver .env.example) "
            "o define la variable antes de ejecutar la etapa de datos."
        )
    return key
