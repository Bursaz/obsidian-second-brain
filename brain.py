#!/usr/bin/env python3
"""Unified OSB + Avenox Beyin command line."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MEMORY_COMMANDS = (
    "context",
    "doctor-memory",
    "history",
    "ingest",
    "jev",
    "jev-answer",
    "jev-memory",
    "jev-review",
    "note-create",
    "preferences",
    "receipt",
    "recover",
    "rollback",
    "skill-import",
    "skill-sync",
    "sync",
    "task-create",
    "task-update",
    "update",
)


def run_json(command: list[str]) -> dict:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    stream = result.stdout if result.returncode == 0 else result.stderr
    try:
        payload = json.loads(stream)
    except json.JSONDecodeError as exc:
        raise RuntimeError(stream.strip() or f"command failed with exit {result.returncode}") from exc
    if result.returncode != 0:
        raise RuntimeError(payload.get("message", payload.get("error", "command failed")))
    return payload


def avenox(vault: Path, arguments: list[str]) -> dict:
    entry = vault / "beyin.py"
    if not entry.is_file():
        raise RuntimeError("Avenox V3 is not installed in this vault")
    return run_json([sys.executable, str(entry), *arguments, "--json"])


def combined_doctor(vault: Path) -> dict:
    sys.path.insert(0, str(ROOT / "scripts"))
    from vault_health import run_health_check

    osb = run_health_check(vault)
    memory = avenox(vault, ["doctor"])
    healthy = osb["total_issues"] == 0 and memory.get("status") not in {
        "needs_attention",
        "pending",
    }
    return {
        "status": "healthy" if healthy else "needs_attention",
        "vault": str(vault),
        "osb": osb,
        "avenox": memory,
    }


def install_osb_skills(vault: Path) -> dict:
    build = subprocess.run(
        ["bash", str(ROOT / "scripts" / "build.sh"), "--platform", "agent-skills"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if build.returncode != 0:
        raise RuntimeError(build.stderr.strip() or build.stdout.strip())
    source = ROOT / "dist" / "agent-skills" / "skills"
    names = sorted(path.name for path in source.iterdir() if path.is_dir())
    for destination in (vault / ".agents" / "skills", vault / ".claude" / "skills"):
        destination.mkdir(parents=True, exist_ok=True)
        for name in names:
            shutil.copytree(source / name, destination / name, dirs_exist_ok=True)
    return {"status": "installed", "count": len(names), "skills": names}


def install(args: argparse.Namespace) -> dict:
    vault = args.vault.expanduser().resolve()
    if not vault.exists() or not (vault / "_CLAUDE.md").is_file():
        if not args.name:
            raise RuntimeError("--name is required when creating a new vault")
        command = [
            sys.executable,
            str(ROOT / "scripts" / "bootstrap_vault.py"),
            "--path",
            str(vault),
            "--name",
            args.name,
            "--preset",
            args.preset,
        ]
        if args.no_sidebiz:
            command.append("--no-sidebiz")
        created = subprocess.run(command, text=True, capture_output=True, check=False)
        if created.returncode != 0:
            raise RuntimeError(created.stderr.strip() or created.stdout.strip())

    osb_skills = install_osb_skills(vault)
    command = [
        sys.executable,
        str(ROOT / "scripts" / "install_avenox_v3.py"),
        "--vault",
        str(vault),
    ]
    if args.state:
        command.extend(["--state", str(args.state.expanduser().resolve())])
    installed = run_json(command)
    memory_sync = avenox(vault, ["sync"])
    skill_sync = avenox(vault, ["skill-sync"])
    doctor = combined_doctor(vault)
    if memory_sync.get("status") != "succeeded" or skill_sync.get("conflicts"):
        doctor["status"] = "needs_attention"
    return {
        "status": "installed" if doctor["status"] == "healthy" else "needs_attention",
        "install": installed,
        "osb_skills": osb_skills,
        "memory_sync": memory_sync,
        "skill_sync": skill_sync,
        "doctor": doctor,
    }


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("install", help="Create or adopt a vault and install the unified system")
    setup.add_argument("--vault", required=True, type=Path)
    setup.add_argument("--state", type=Path)
    setup.add_argument("--name")
    setup.add_argument(
        "--preset",
        default="default",
        choices=("default", "executive", "builder", "creator", "researcher"),
    )
    setup.add_argument("--no-sidebiz", action="store_true")

    doctor = sub.add_parser("doctor", help="Run OSB and Avenox health checks together")
    doctor.add_argument("--vault", required=True, type=Path)

    runtime = sub.add_parser("avenox", help="Run an installed Avenox command")
    runtime.add_argument("--vault", required=True, type=Path)
    runtime.add_argument("arguments", nargs=argparse.REMAINDER)
    for command in MEMORY_COMMANDS:
        direct = sub.add_parser(command, help=f"Run the integrated Avenox {command} command")
        direct.add_argument("--vault", required=True, type=Path)
        direct.add_argument("arguments", nargs=argparse.REMAINDER)
    return root


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    argument_parser = parser()
    args, extra = argument_parser.parse_known_args(raw)
    passthrough = args.command == "avenox" or args.command in MEMORY_COMMANDS
    if extra and not passthrough:
        argument_parser.error("unrecognized arguments: " + " ".join(extra))
    if passthrough:
        forwarded: list[str] = []
        index = 1
        while index < len(raw):
            value = raw[index]
            if value == "--vault":
                index += 2
                continue
            if value.startswith("--vault="):
                index += 1
                continue
            forwarded.append(value)
            index += 1
        args.arguments = forwarded
    try:
        if args.command == "install":
            result = install(args)
        elif args.command == "doctor":
            result = combined_doctor(args.vault.expanduser().resolve())
        elif args.command == "avenox":
            result = avenox(args.vault.expanduser().resolve(), args.arguments or ["doctor"])
        else:
            command = "doctor" if args.command == "doctor-memory" else args.command
            result = avenox(args.vault.expanduser().resolve(), [command, *args.arguments])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
