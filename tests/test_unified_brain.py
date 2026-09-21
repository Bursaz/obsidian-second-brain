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
    assert payload["memory_sync"]["status"] == "succeeded"
    assert payload["memory_sync"]["warnings"] == []
    assert payload["memory_sync"]["indexed"] > 0
    assert payload["skill_sync"]["conflicts"] == []
    assert payload["osb_skills"]["count"] > 40
    assert (vault / ".agents/skills/obsidian-capture/SKILL.md").is_file()
    assert (vault / ".claude/skills/obsidian-capture/SKILL.md").is_file()
    assert (vault / ".agents/skills/beyin/SKILL.md").is_file()
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

    preferences = run("preferences", "--vault", str(vault))
    assert preferences.returncode == 0, preferences.stderr
    payload = json.loads(preferences.stdout)
    assert payload["preferences"]["context_mode"] == "turn"
    assert payload["preferences"]["context_chars"] == 5000

    changed = run("preferences", "--vault", str(vault), "--profile", "economical")
    assert changed.returncode == 0, changed.stderr
    assert json.loads(changed.stdout)["preferences"]["context_mode"] == "session"

    context = run("context", "--vault", str(vault), "Synthetic Owner")
    assert context.returncode == 0, context.stderr
    recalled = json.loads(context.stdout)
    assert recalled["records"]


def test_legacy_avenox_namespace_remains_available(tmp_path):
    vault = tmp_path / "vault"
    state = tmp_path / "state"
    installed = run(
        "install", "--vault", str(vault), "--state", str(state),
        "--name", "Synthetic Owner", "--no-sidebiz",
    )
    assert installed.returncode == 0, installed.stderr
    result = run("avenox", "--vault", str(vault), "doctor")
    assert result.returncode == 0, result.stderr
    assert "status" in json.loads(result.stdout)
