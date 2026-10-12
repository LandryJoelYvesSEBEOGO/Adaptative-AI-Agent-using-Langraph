"""Scripts de sauvegarde / restauration (L5.4) : nécessitent PostgreSQL et pg_dump."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
URL = os.environ.get("DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not URL.startswith("postgresql") or not shutil.which("pg_dump") or not shutil.which("psql"),
    reason="PostgreSQL et les outils pg_dump/psql sont requis",
)


def _run(script: str, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["sh", str(SCRIPTS / script), *args],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_backup_then_verify(tmp_path: Path) -> None:
    done = _run("backup_db.sh", BACKUP_URL=URL, BACKUP_DIR=str(tmp_path))
    assert done.returncode == 0, done.stderr
    dumps = list(tmp_path.glob("rag-*.dump"))
    assert len(dumps) == 1 and dumps[0].stat().st_size > 0
    assert not list(tmp_path.glob("*.partial"))

    admin = URL.rsplit("/", 1)[0] + "/postgres"
    checked = _run("verify_backup.sh", str(dumps[0]), ADMIN_URL=admin)
    assert checked.returncode == 0, checked.stderr
    assert "restaurable" in checked.stdout


def test_backup_requires_url(tmp_path: Path) -> None:
    env = {k: v for k, v in os.environ.items() if k not in {"BACKUP_URL", "DATABASE_URL"}}
    done = subprocess.run(
        ["sh", str(SCRIPTS / "backup_db.sh")], env=env, capture_output=True, text=True, check=False
    )
    assert done.returncode == 2
