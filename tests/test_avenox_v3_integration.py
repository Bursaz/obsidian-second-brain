from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.vault_health import load_vault, load_vault_config, run_health_check

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "hooks" / "load_vault_context.py"


def test_vendored_avenox_is_exactly_the_reviewed_release():
    assert (ROOT / "integrations/avenox-v3/VERSION").read_text().strip() == "3.2.0"
    assert (ROOT / "integrations/avenox-v3/scripts/install_v3.py").is_file()
    assert (ROOT / "integrations/avenox-v3/template/.claude/scripts/beyin_v3.py").is_file()


def test_osb_defers_duplicate_manual_context_to_avenox(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "_CLAUDE.md").write_text("SECRET-MANUAL-CONTEXT", encoding="utf-8")
    (vault / ".beyin-runtime.json").write_text("{}", encoding="utf-8")
    (vault / "beyin.py").write_text("# installed entrypoint", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps({"cwd": str(vault)}),
        env=dict(os.environ, OBSIDIAN_VAULT_PATH=str(vault)),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "Avenox Beyin V3 owns SessionStart" in context
    assert "SECRET-MANUAL-CONTEXT" not in context
    assert "Skill root" in context


def test_install_front_door_supports_non_mutating_plan(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/install_avenox_v3.py"), "--vault", str(vault), "--plan"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "plan"
    assert report["version"] == "3.2.0"
    assert not (vault / "beyin.py").exists()


def test_clean_hybrid_vault_has_no_system_file_health_noise(tmp_path):
    vault = tmp_path / "vault"
    state = tmp_path / "state"
    vault.mkdir()
    state.mkdir()
    (vault / "_CLAUDE.md").write_text("# Vault manual\n", encoding="utf-8")
    (vault / "Home.md").write_text("---\ntype: index\ndate: 2026-09-21\ntags: [index]\nai-first: true\n---\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/install_avenox_v3.py"),
            "--vault",
            str(vault),
            "--state",
            str(state),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    excludes = load_vault_config(vault)
    notes = load_vault(vault, excludes)
    assert "CLAUDE.md" not in notes
    assert not any(path.startswith("🔮 850-Companion/") for path in notes)
    findings = run_health_check(vault)["issues"]
    noisy = [
        finding
        for finding in findings
        if any("850-Companion" in file or file == "CLAUDE.md" for file in finding.get("files", []))
    ]
    assert noisy == []
