"""Protocolo anti-sesgo: congelado de umbrales/parámetros (hash + git) y bloqueo de uso único del holdout."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

FROZEN_FILES = ["config/acceptance.yaml", "config/strategy.yaml", "config/strategy_frozen.yaml",
                "data/manifest.json"]
FREEZE_FILE = "config/freeze.json"
LOCK_FILE = "reports/.holdout_used"


class HoldoutRejected(RuntimeError):
    """La evaluación del holdout se rechaza (hash distinto, archivo sin commit, etc.)."""


class HoldoutAlreadyUsed(RuntimeError):
    """El holdout ya fue evaluado una vez."""


class HoldoutPermanentlyBlocked(RuntimeError):
    """La estrategia está en estado rejected en el ciclo de vida y el holdout está consumido permanentemente."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)


def committed_and_clean(root: Path, rel: str) -> bool:
    tracked = _git(root, "ls-files", "--error-unmatch", rel).returncode == 0
    return tracked and _git(root, "status", "--porcelain", "--", rel).stdout.strip() == ""


def head_commit(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def freeze(root: Path, files: list[str] = FROZEN_FILES) -> dict:
    """Exige que los archivos estén en un commit sin cambios y guarda sus hashes en config/freeze.json."""
    root = Path(root)
    dirty = [f for f in files if not committed_and_clean(root, f)]
    if dirty:
        raise HoldoutRejected(f"Haz commit antes de congelar: {dirty}")
    acc = yaml.safe_load((root / "config/acceptance.yaml").read_text(encoding="utf-8"))
    info = {"frozen_at": datetime.now(timezone.utc).isoformat(), "commit": head_commit(root),
            "acceptance_version": acc.get("version"),
            "hashes": {f: sha256_file(root / f) for f in files}}
    (root / FREEZE_FILE).write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def verify_freeze(root: Path) -> dict:
    """Recalcula los hashes y comprueba git. Cualquier discrepancia rechaza la evaluación del holdout."""
    root = Path(root)
    fp = root / FREEZE_FILE
    if not fp.exists():
        raise HoldoutRejected("No existe config/freeze.json: los umbrales no están congelados")
    if not committed_and_clean(root, FREEZE_FILE):
        raise HoldoutRejected("config/freeze.json no está en un commit sin cambios")
    info = json.loads(fp.read_text(encoding="utf-8"))
    problems = []
    for rel, h in info["hashes"].items():
        p = root / rel
        if not p.exists():
            problems.append(f"falta {rel}")
        elif sha256_file(p) != h:
            problems.append(f"hash cambiado: {rel}")
        elif not committed_and_clean(root, rel):
            problems.append(f"cambios sin commit: {rel}")
    if problems:
        raise HoldoutRejected("; ".join(problems))
    return info


def acquire_holdout_lock(root: Path, info: dict) -> Path:
    """Crea reports/.holdout_used de forma atómica; si ya existe, el holdout ya se usó."""
    root = Path(root)
    lifecycle_file = root / "config" / "lifecycle.json"
    if lifecycle_file.exists():
        try:
            lc = json.loads(lifecycle_file.read_text(encoding="utf-8"))
            if lc.get("lifecycle_status") == "rejected" or lc.get("holdout_exhausted"):
                raise HoldoutPermanentlyBlocked(
                    f"Estrategia rechazada ('{lc.get('lifecycle_status')}'). El holdout está consumido y bloqueado permanentemente."
                )
        except json.JSONDecodeError:
            pass

    p = root / LOCK_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise HoldoutAlreadyUsed(f"El holdout ya fue evaluado ({p}). No se permite una segunda evaluación.") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"status": "started", "started_at": datetime.now(timezone.utc).isoformat()} | info, fh, indent=2)
    return p


def finalize_lock(path: Path, extra: dict) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data |= {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()} | extra
    Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
