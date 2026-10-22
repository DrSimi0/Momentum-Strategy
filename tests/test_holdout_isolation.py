"""Test de aislamiento del Holdout bloqueado (2010-2017).
Garantiza que ningún script de desarrollo/optimización importe ni modifique
los archivos bloqueados en data/locked_holdout/ y que sus hashes SHA-256 permanezcan intactos.
"""
import hashlib
from pathlib import Path
import pytest

HOLDOUT_DIR = Path("data/locked_holdout")
HASH_FILE = HOLDOUT_DIR / "HOLDOUT_2010_2017_SHA256.txt"


def test_holdout_files_exist_and_hashes_match():
    assert HOLDOUT_DIR.exists(), "El directorio data/locked_holdout/ debe existir."
    assert HASH_FILE.exists(), "El archivo de hashes SHA-256 debe existir."

    expected_hashes = {}
    with open(HASH_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    expected_hashes[parts[1]] = parts[0]

    assert len(expected_hashes) >= 4, "Debe haber al menos 4 archivos bloqueados registrados."

    for filename, expected_hash in expected_hashes.items():
        filepath = HOLDOUT_DIR / filename
        assert filepath.exists(), f"El archivo de holdout bloqueado {filename} debe existir."
        actual_hash = hashlib.sha256(open(filepath, "rb").read()).hexdigest()
        assert actual_hash == expected_hash, (
            f"VIOLACIÓN DE INTEGRIDAD DEL HOLDOUT: El hash de {filename} ha cambiado!\n"
            f"Esperado: {expected_hash}\nActual:   {actual_hash}"
        )


def test_no_research_script_references_locked_holdout():
    """Verifica que ningún script en src/ ni scripts/ de optimización lea data/locked_holdout/."""
    forbidden_pattern = "locked_holdout"
    code_dirs = [Path("src"), Path("scripts")]

    violating_files = []
    # Scripts permitidos exclusivamente: este test y el runner final del holdout
    allowed_exceptions = {
        "test_holdout_isolation.py",
        "prepare_preregistered_partitions.py",
        "evaluate_locked_holdout.py", # Script único al final
    }

    for d in code_dirs:
        for py_file in d.rglob("*.py"):
            if py_file.name in allowed_exceptions:
                continue
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if forbidden_pattern in content:
                violating_files.append(str(py_file))

    assert not violating_files, (
        f"VIOLACIÓN DE AISLAMIENTO: Los siguientes scripts contienen referencias al holdout bloqueado:\n"
        f"{violating_files}"
    )
