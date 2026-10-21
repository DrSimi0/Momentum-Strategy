"""Descarga el historial de Fear & Greed desde alternative.me y lo almacena localmente."""
import json
import logging
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


def fetch_fear_and_greed(limit: int = 200, output_file: Path = Path("data/macro/fear_and_greed.json")) -> dict:
    url = f"https://api.alternative.me/fng/?limit={limit}&format=json"
    headers = {"User-Agent": "QuantitativeResearch/3.0"}
    req = urllib.request.Request(url, headers=headers)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Guardados {len(data.get('data', []))} registros de Fear & Greed en {output_file}")
            return data
    except Exception as e:
        logger.warning(f"No se pudo descargar Fear & Greed de la API: {e}. Usando fallback.")
        return {}


if __name__ == "__main__":
    fetch_fear_and_greed()
