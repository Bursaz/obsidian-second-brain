from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "brain.py"


def run(*arguments: str):
    return subprocess.run(
        [sys.executable, str(CLI), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )


def test_clean_install_and_combined_doctor(tmp_path):
    vault = tmp_path / "vault"
    state = tmp_path / "state"
    result = run(
        "install",
        "--vault",
        str(vault),
        "--state",
        str(state),
        "--name",
        "Synthetic Owner",
        "--no-sidebiz",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "installed"
    assert payload["doctor"]["status"] == "healthy"
    assert payload["doctor"]["osb"]["total_issues"] == 0
    assert (vault / "beyin.py").is_file()
    assert (vault / "🔮 850-Companion/Core.md").is_file()

    doctor = run("doctor", "--vault", str(vault))
    assert doctor.returncode == 0, doctor.stderr
    report = json.loads(doctor.stdout)
    assert report["status"] == "healthy"


def test_runtime_commands_are_available_through_one_front_door(tmp_path):
    vault = tmp_path / "vault"
    state = tmp_path / "state"
    installed = run(
        "install", "--vault", str(vault), "--state", str(state),
        "--name", "Synthetic Owner", "--no-sidebiz",
    )
    assert installed.returncode == 0, installed.stderr

    preferences = run("avenox", "--vault", str(vault), "preferences")
    assert preferences.returncode == 0, preferences.stderr
    payload = json.loads(preferences.stdout)
    assert payload["preferences"]["context_mode"] == "turn"
    assert payload["preferences"]["context_chars"] == 5000
