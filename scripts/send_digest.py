#!/usr/bin/env python3
"""
XC Ski Labs — Immune System digest email.

Renders immune/report.json into the morning digest and sends it via Resend.
Called at the end of the nightly immune run. Safe to run any time; if there's
nothing to report and --only-if-findings is set, it sends nothing.

Env (.env or environment):
    RESEND_API_KEY   required — your Resend key
    DIGEST_TO        recipient (default: gravelgodcoaching@gmail.com)
    DIGEST_FROM      sender    (default: immune@xcskilabs.com — must be a Resend-verified domain)

Usage:
    python3 scripts/send_digest.py                 # always send
    python3 scripts/send_digest.py --only-if-findings   # send only when something needs attention
    python3 scripts/send_digest.py --print          # print the digest, don't send (dry run)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except Exception:  # noqa: BLE001
    pass

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_FILE = PROJECT_ROOT / "immune" / "report.json"
SCANS_FILE = PROJECT_ROOT / "immune" / "scans.jsonl"


def clean_scan_streak() -> int:
    """Count consecutive most-recent scans with zero findings (trust streak)."""
    if not SCANS_FILE.exists():
        return 0
    scans = [json.loads(l) for l in SCANS_FILE.read_text().splitlines() if l.strip()]
    streak = 0
    for rec in reversed(scans):
        if rec.get("counts", {}).get("total", 1) == 0:
            streak += 1
        else:
            break
    return streak


def render(report: dict) -> tuple[str, str, str]:
    """Return (subject, text_body, html_body)."""
    c = report["counts"]
    findings = report["findings"]
    date = report["generated_at"][:10]
    need = c["yellow"] + c["red"]
    subject = f"🩺 Immune report — {date} ({need} need you)" if need else \
              f"🩺 Immune report — {date} (all clear)"

    def lane(name):
        return [f for f in findings if f["lane"] == name]

    lines = [f"XC Ski Labs — Immune report · {date}", ""]
    if lane("green"):
        lines.append(f"✅ AUTO-HEALABLE ({len(lane('green'))})")
        lines += [f"   • {f['title']}: {f['detail']}" for f in lane("green")]
        lines.append("")
    if lane("yellow"):
        lines.append(f"⚠️ NEEDS YOU ({len(lane('yellow'))})")
        lines += [f"   • {f['title']}: {f['detail']}\n     → {f['remedy']}" for f in lane("yellow")]
        lines.append("")
    if lane("red"):
        lines.append(f"🔴 ISSUE ({len(lane('red'))})")
        lines += [f"   • {f['title']}: {f['detail']}\n     → {f['remedy']}" for f in lane("red")]
        lines.append("")
    if not findings:
        lines.append("🧬 All clear — nothing broke.")
    n = clean_scan_streak()
    lines.append(f"🧬 {n} clean scan{'s' if n != 1 else ''} in a row.")
    text = "\n".join(lines)

    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = "<div style='font-family:monospace;white-space:pre-wrap;font-size:14px'>" \
           + esc(text) + "</div>"
    return subject, text, html


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-if-findings", action="store_true")
    ap.add_argument("--print", dest="dry", action="store_true")
    args = ap.parse_args()

    if not REPORT_FILE.exists():
        print("No report.json — run immune_check.py first.", file=sys.stderr)
        return 1
    report = json.loads(REPORT_FILE.read_text())
    subject, text, html = render(report)

    if args.only_if_findings and report["counts"]["total"] == 0:
        print("No findings; skipping email.")
        return 0
    if args.dry:
        print(subject + "\n" + "-" * 60 + "\n" + text)
        return 0

    key = os.environ.get("RESEND_API_KEY")
    if not key:
        print("RESEND_API_KEY not set — printing digest instead of sending.\n", file=sys.stderr)
        print(subject + "\n" + text)
        return 0
    to = os.environ.get("DIGEST_TO", "gravelgodcoaching@gmail.com")
    sender = os.environ.get("DIGEST_FROM", "immune@xcskilabs.com")
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"from": sender, "to": [to], "subject": subject, "text": text, "html": html},
        timeout=30)
    if resp.status_code >= 300:
        print(f"Resend error {resp.status_code}: {resp.text}", file=sys.stderr)
        return 1
    print(f"Digest sent to {to}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
