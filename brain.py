#!/usr/bin/env python3
"""Unified OSB + Avenox Beyin command line."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


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

    command = [
        sys.executable,
        str(ROOT / "scripts" / "install_avenox_v3.py"),
        "--vault",
        str(vault),
    ]
    if args.state:
        command.extend(["--state", str(args.state.expanduser().resolve())])
    installed = run_json(command)
    return {"status": "installed", "install": installed, "doctor": combined_doctor(vault)}


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
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "install":
            result = install(args)
        elif args.command == "doctor":
            result = combined_doctor(args.vault.expanduser().resolve())
        else:
            result = avenox(args.vault.expanduser().resolve(), args.arguments or ["doctor"])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
