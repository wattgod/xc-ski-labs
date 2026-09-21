#!/usr/bin/env python3
"""Add a flag-only Jev review to uncertain XC race-existence results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts import jev_client
except ImportError:  # pragma: no cover - direct script execution
    import jev_client


ROOT = Path(__file__).resolve().parent.parent
RACE_DATA = ROOT / "race-data"
RESULTS = ROOT / "data" / "existence-check-results"
DEFAULT_OUT = ROOT / "data" / "jev" / "existence-triage-report.json"
TARGET_CLASSES = {"SUSPICIOUS", "LIKELY"}


def _profiles(args: argparse.Namespace) -> list[tuple[str, dict[str, Any]]]:
    paths = sorted(RACE_DATA.glob("*.json"))
    profiles = [(path.stem, json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    if args.slug:
        profiles = [item for item in profiles if item[0] == args.slug]
    if args.limit is not None:
        profiles = profiles[: args.limit]
    return profiles


def _state(data: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    race = data.get("race", {})
    return {
        "profile": {
            "name": race.get("name"),
            "vitals": race.get("vitals", {}),
            "history": race.get("history", {}),
            "series_membership": race.get("series_membership"),
        },
        "existence_result": json.dumps(result, ensure_ascii=False)[:6000],
    }


def _row(slug: str, data: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    Noul = jev_client.question_types()[2]
    response = jev_client.ask(
        _state(data, result),
        {
            "real_event": Noul(
                instructions=(
                    "Taken together, does this evidence show the event is a real, "
                    "currently or recently held race (not a fabricated or defunct one)?"
                )
            )
        },
    )
    probability = jev_client.probability(jev_client.noul(response, "real_event"))
    verdict = (
        "reinforce_real" if probability is not None and probability >= 0.8
        else "reinforce_doubt" if probability is not None and probability <= 0.3
        else "unclear"
    )
    return {
        "slug": slug,
        "prior_class": result.get("status"),
        "real_probability": probability,
        "verdict": verdict,
        "model": jev_client.model(response),
        "response_available": response is not None,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    report = jev_client.base_report(None, available=False)
    if not RESULTS.is_dir():
        report.update({
            "rows": [],
            "summary": {"profiles_considered": 0, "skipped": True},
            "skipped_reason": "data/existence-check-results does not exist",
        })
        return report
    rows = []
    considered = 0
    for slug, data in _profiles(args):
        path = RESULTS / f"{slug}.json"
        if not path.exists():
            continue
        result_data = json.loads(path.read_text(encoding="utf-8"))
        result = result_data.get("result", result_data)
        prior = str(result.get("status", "")).upper()
        if prior not in TARGET_CLASSES:
            continue
        considered += 1
        rows.append(_row(slug, data, result))
    response_model = next((row["model"] for row in rows if row["model"]), None)
    report = jev_client.base_report(
        type("Response", (), {"model": response_model})() if response_model else None,
        available=any(row["response_available"] for row in rows),
    )
    report.update({
        "rows": rows,
        "summary": {
            "profiles_considered": considered,
            "reinforce_real": sum(row["verdict"] == "reinforce_real" for row in rows),
            "reinforce_doubt": sum(row["verdict"] == "reinforce_doubt" for row in rows),
            "unclear": sum(row["verdict"] == "unclear" for row in rows),
        },
    })
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--slug")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = run(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
