import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_import_main(app_env: str | None) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    if app_env is None:
        env.pop("APP_ENV", None)
    else:
        env["APP_ENV"] = app_env

    return subprocess.run(
        [sys.executable, "-c", "import main"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_invalid_app_env_fails_to_import_main_with_identifiable_error():
    result = _run_import_main("invalid")

    assert result.returncode != 0
    assert "app_env" in result.stderr
    assert "ValidationError" in result.stderr


def test_missing_app_env_imports_main_successfully():
    result = _run_import_main(None)

    assert result.returncode == 0


def test_allowed_app_env_imports_main_successfully():
    result = _run_import_main("development")

    assert result.returncode == 0
