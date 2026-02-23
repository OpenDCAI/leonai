#!/usr/bin/env python3
"""Surface open PR entries that are missing proposer markers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

MARKER_PATTERN = re.compile(r"\[proposer:[A-Za-z0-9_-]+\]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check exported open PR metadata and list entries without "
            "a [proposer:<id>] marker in title or body first line."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to JSON array from gh pr list --json number,title,body,url",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Return exit code 1 when missing markers are found.",
    )
    return parser.parse_args()


def load_prs(path: Path) -> list[dict[str, Any]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"input file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"input file is not valid JSON: {path}") from exc

    if not isinstance(raw, list):
        raise RuntimeError("input JSON must be a list of PR metadata objects")

    prs: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise RuntimeError(f"entry #{idx} is not an object")
        prs.append(item)
    return prs


def first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def has_marker(pr: dict[str, Any]) -> bool:
    title = str(pr.get("title") or "")
    body = str(pr.get("body") or "")

    if MARKER_PATTERN.search(title):
        return True

    # @@@body-first-line-policy - Only the first non-empty body line is eligible by policy.
    return bool(MARKER_PATTERN.search(first_non_empty_line(body)))


def format_missing_line(pr: dict[str, Any]) -> str:
    number = pr.get("number", "?")
    title = " ".join(str(pr.get("title") or "").split())
    url = str(pr.get("url") or "")
    return f"- #{number}: {title} ({url})"


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    prs = load_prs(input_path)

    missing = [pr for pr in prs if not has_marker(pr)]

    print(f"Checked {len(prs)} open PR entr{'y' if len(prs) == 1 else 'ies'} from {input_path}")
    if not missing:
        print("All entries include a proposer marker in title or first body line.")
        return 0

    print(f"Missing proposer markers: {len(missing)}")
    for pr in missing:
        print(format_missing_line(pr))

    return 1 if args.fail_on_missing else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
