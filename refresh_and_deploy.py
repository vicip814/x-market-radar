#!/usr/bin/env python3
"""Refresh X data and deploy only when the snapshot meaningfully changes."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data.json"


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=ROOT, text=True, check=check)


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def comparable(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if payload is None:
        return None
    clean = dict(payload)
    clean.pop("generated_at", None)
    clean.pop("generated_ts", None)
    return clean


def has_git_change(pathspec: str) -> bool:
    proc = subprocess.run(
        ["git", "status", "--porcelain", "--", pathspec],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return bool(proc.stdout.strip())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh, commit, push, and deploy changed X Market Radar data.")
    parser.add_argument("--limit", type=int, default=8, help="tweets per channel")
    parser.add_argument("--no-deploy", action="store_true", help="commit and push, but skip Vercel deploy")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    before_text = DATA_PATH.read_text(encoding="utf-8") if DATA_PATH.exists() else None
    before = load_json(DATA_PATH)

    run(["python3", "aggregator.py", "--limit", str(args.limit)])
    after = load_json(DATA_PATH)

    if comparable(before) == comparable(after):
        if before_text is not None:
            DATA_PATH.write_text(before_text, encoding="utf-8")
        print("No meaningful data changes; skipping commit, push, and deploy.")
        return 0

    if not has_git_change("data.json"):
        print("No Git-visible data changes; skipping commit, push, and deploy.")
        return 0

    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    run(["git", "add", "data.json"])
    run(["git", "commit", "-m", f"Refresh X market snapshot {stamp}"])
    run(["git", "push"])

    if args.no_deploy:
        print("Skipped Vercel deploy because --no-deploy was set.")
        return 0

    run(["npx", "--yes", "vercel@latest", "deploy", "--prod", "--yes", "--archive=tgz", "--force"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
