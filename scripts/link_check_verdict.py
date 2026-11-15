#!/usr/bin/env python3
"""Turn a check_links.py exit code into the weekly workflow's verdict.

check_links.py exits 0 (all alive), 1 (dead links) or 2 (inconclusive: the
SiteGround WAF challenged the runner, so nothing was proven dead or alive).
One inconclusive week passes with a warning, because runner IPs get
challenged often; two in a row fail, because by then the site has gone
unchecked for two weeks. Every run records its outcome so the next run can
see the streak.

Usage:
  link_check_verdict.py --rc 2 --previous prev/status.txt --out status/status.txt
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

OUTCOMES = {0: "checked", 1: "dead", 2: "inconclusive"}


def previous_outcome(path: Path | None) -> str | None:
    """The last run's recorded outcome, or None when there is no record."""
    if not path or not path.is_file():
        return None
    value = path.read_text(encoding="utf-8").strip()
    return value if value in OUTCOMES.values() else None


def verdict(rc: int, previous: str | None) -> tuple[int, str]:
    """Return (exit code, one-line summary)."""
    outcome = OUTCOMES.get(rc)
    if outcome is None:
        return 1, f"check_links.py exited {rc}, which is not a known outcome: treat as broken"
    if outcome == "checked":
        return 0, "Checked: every link answered."
    if outcome == "dead":
        return 1, "Dead links found (list in the log)."
    if previous == "inconclusive":
        return 1, ("NOT CHECKED two runs in a row: the WAF challenged the runner both times, "
                   "so the site has gone unchecked. Re-run, or check from another network.")
    known = "no record of the previous run" if previous is None else f"previous run: {previous}"
    return 0, f"NOT CHECKED this run (WAF challenge); {known}. Two in a row fails."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rc", type=int, required=True)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    prev = previous_outcome(args.previous)
    code, summary = verdict(args.rc, prev)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(OUTCOMES.get(args.rc, "broken") + "\n", encoding="utf-8")

    level = "error" if code else ("warning" if args.rc == 2 else "notice")
    print(f"::{level}::Link check: {summary}")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(f"## Link check\n\n{summary}\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
