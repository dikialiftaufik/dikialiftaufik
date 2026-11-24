"""CLI entry point: python -m metrics --user NAME --out dist."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from . import compute, fetch, render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate profile metrics.")
    parser.add_argument("--user", required=True)
    parser.add_argument("--out", type=Path, default=Path("dist"))
    parser.add_argument("--config", type=Path, default=Path("metrics.config.json"))
    parser.add_argument("--fixture", type=Path, help="read repos/calendar from JSON instead of the API")
    parser.add_argument("--include-private", action="store_true", help="aggregate private repos (needs a PAT)")
    args = parser.parse_args(argv)

    config = json.loads(args.config.read_text(encoding="utf-8")) if args.config.exists() else {}
    skip = frozenset(config.get("exclude_repos", []))
    token = os.environ.get("GITHUB_TOKEN")

    if args.fixture:
        data = json.loads(args.fixture.read_text(encoding="utf-8"))
        repos, calendar = data["repos"], data.get("calendar")
    else:
        repos = fetch.fetch_repos(args.user, token, args.include_private)
        calendar = fetch.fetch_calendar(args.user, token)

    summary = compute.summarize(repos, calendar, date.today(), skip)
    args.out.mkdir(parents=True, exist_ok=True)
    for theme in render.THEMES:
        (args.out / f"metrics.{theme}.svg").write_text(render.render_svg(summary, theme), encoding="utf-8")
    (args.out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(render.THEMES)} SVGs and summary.json to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
