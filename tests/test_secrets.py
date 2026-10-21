"""Escaneo de secretos: falla si algún archivo versionado contiene un patrón de clave de Databento."""
import os
import re
import subprocess
from pathlib import Path

import pytest

from src import settings

ROOT = Path(__file__).resolve().parents[1]
# Se arma por partes para que este mismo archivo no contenga un literal que coincida.
KEY_PATTERN = re.compile("d" + "b-" + r"[A-Za-z0-9]{20,}")


def _tracked_and_staged_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [ROOT / p for p in out.splitlines() if p.strip()]


def test_no_api_key_in_versionable_files():
    offenders = []
    for path in _tracked_and_staged_files():
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if KEY_PATTERN.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, f"Posible clave expuesta en: {offenders}"


def test_env_file_is_gitignored():
    res = subprocess.run(["git", "check-ignore", ".env"], cwd=ROOT, capture_output=True, text=True)
    assert res.returncode == 0, ".env debe estar en .gitignore"


def test_pattern_detects_fake_key():
    fake = "d" + "b-" + "A" * 30
    assert KEY_PATTERN.search(fake)


def test_missing_key_raises_clear_error(tmp_path, monkeypatch):
    monkeypatch.delenv(settings.ENV_VAR, raising=False)
    with pytest.raises(settings.MissingApiKeyError) as exc:
        settings.get_api_key(env_file=tmp_path / "no_existe.env")
    assert settings.ENV_VAR in str(exc.value)


def test_placeholder_key_is_rejected(tmp_path, monkeypatch):
    monkeypatch.delenv(settings.ENV_VAR, raising=False)
    env = tmp_path / ".env"
    env.write_text(f"{settings.ENV_VAR}=pon_tu_clave_aqui\n", encoding="utf-8")
    with pytest.raises(settings.MissingApiKeyError):
        settings.get_api_key(env_file=env)
    os.environ.pop(settings.ENV_VAR, None)
