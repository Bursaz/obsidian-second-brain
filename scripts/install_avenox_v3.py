#!/usr/bin/env python3
"""Install the pinned Avenox V3 runtime beside OSB without altering this repo.

The vendored installer remains the source of truth for install, migration,
doctor, updater, rollback and recovery behavior. This front door prevents the
integration from silently drifting to a different Avenox release.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AVENOX = ROOT / "integrations" / "avenox-v3"
PINNED_VERSION = "3.2.0"


def main(argv: list[str] | None = None) -> int:
    version = (AVENOX / "VERSION").read_text(encoding="utf-8").strip()
    if version != PINNED_VERSION:
        print(
            f"Refusing unreviewed Avenox version {version!r}; expected {PINNED_VERSION!r}.",
            file=sys.stderr,
        )
        return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True, type=Path)
    parser.add_argument("--state", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--uninstall", action="store_true")
    mode.add_argument("--plan", action="store_true")
    parser.add_argument("--accept-customized-legacy", action="append", default=[])
    args = parser.parse_args(argv)

    installer_path = AVENOX / "scripts" / "install_v3.py"
    installer_spec = importlib.util.spec_from_file_location("osb_avenox_installer", installer_path)
    assert installer_spec is not None and installer_spec.loader is not None
    installer = importlib.util.module_from_spec(installer_spec)
    installer_spec.loader.exec_module(installer)

    cli_path = AVENOX / "scripts" / "beyin_v3.py"
    cli_spec = importlib.util.spec_from_file_location("osb_avenox_cli", cli_path)
    assert cli_spec is not None and cli_spec.loader is not None
    cli = importlib.util.module_from_spec(cli_spec)
    cli_spec.loader.exec_module(cli)

    os.umask(0o077)
    state = args.state or cli.default_state(args.vault.resolve())
    accepted = tuple(name.replace("\\", "/") for name in args.accept_customized_legacy)
    try:
        result = installer.install(
            args.vault,
            state,
            uninstall=args.uninstall,
            plan_only=args.plan,
            version=PINNED_VERSION,
            accept_customized=accepted,
        )
        print(json.dumps(installer.plan_report(result) if args.plan else result))
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
