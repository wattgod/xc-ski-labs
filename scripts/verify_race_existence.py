#!/usr/bin/env python3
"""
XC Ski Labs — Race Existence Verification via Perplexity

Verifies that every race in the database actually exists as a real event.
Uses Perplexity sonar-pro to search for evidence: official website, results,
news articles, Worldloppet/Euroloppet listing, social media, etc.

Classifications:
  CONFIRMED  — multiple independent web sources confirm the race exists
  LIKELY     — some evidence found but limited (e.g., one mention)
  SUSPICIOUS — very little or no web evidence; may be AI-hallucinated
  FICTIONAL  — strong evidence the race does NOT exist

Usage:
    python scripts/verify_race_existence.py                    # all races
    python scripts/verify_race_existence.py --tier 3           # T3 only
    python scripts/verify_race_existence.py --slug foo-bar     # single
    python scripts/verify_race_existence.py --skip-existing    # skip done
    python scripts/verify_race_existence.py --report           # summary
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
RESULTS_DIR = PROJECT_ROOT / "data" / "existence-check-results"
REPORT_PATH = PROJECT_ROOT / "data" / "existence-check-report.json"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_env():
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def load_profiles(tier=None, slug=None):
    profiles = []
    for path in sorted(RACE_DATA_DIR.glob("*.json")):
        if path.name == "_schema.json":
            continue
        try:
            data = json.load(open(path))
        except (json.JSONDecodeError, OSError):
            continue
        race = data.get("race", {})
        race_slug = race.get("slug", path.stem)
        if slug and race_slug != slug:
            continue
        if tier is not None and race.get("nordic_lab_rating", {}).get("tier") != tier:
            continue
        profiles.append((path, data))
    return profiles


def verify_existence(api_key, race_name, country, slug):
    """Ask Perplexity to verify a race exists with web evidence."""

    prompt = f"""Does the cross-country ski race "{race_name}" in {country} actually exist as a real, organized event?

Search for concrete evidence:
1. Official website URL (that actually works)
2. Race results from any year (timing results, finish lists)
3. News articles mentioning the race
4. Worldloppet, Euroloppet, Ski Classics, or FIS listing
5. Social media presence (Facebook event, Instagram, Strava)
6. YouTube race videos
7. Registration pages (ski signup, zone4, etc.)

Respond ONLY with valid JSON (no markdown fences):
{{
  "status": "CONFIRMED|LIKELY|SUSPICIOUS|FICTIONAL",
  "evidence_count": <number of independent sources found>,
  "official_website": "<URL or null>",
  "results_url": "<URL to any race results, or null>",
  "evidence_summary": "<2-3 sentence summary of what you found>",
  "sources": ["url1", "url2", ...]
}}

Rules:
- CONFIRMED: 3+ independent sources (results, news, official site)
- LIKELY: 1-2 sources or indirect mentions only
- SUSPICIOUS: no race results found, no official site, only AI-generated content or directory listings
- FICTIONAL: evidence that the race does NOT exist or was confused with another event
- Be skeptical — many races in our database were AI-generated and may be fictional
- A working official website with race results is the strongest evidence
- Directory listings alone (ahotu, eventsinrussia) are weak evidence"""

    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": "You verify whether events exist. Be skeptical. Respond only with JSON."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
            "temperature": 0.1,
        },
        timeout=120,
    )

    if response.status_code != 200:
        raise Exception(f"Perplexity API error {response.status_code}: {response.text[:300]}")

    content = response.json()["choices"][0]["message"]["content"]

    # Extract citations
    citations = []
    data = response.json()
    if "citations" in data:
        citations = data["citations"]
    elif "choices" in data and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if "citations" in choice:
            citations = choice["citations"]
        elif "message" in choice and "citations" in choice["message"]:
            citations = choice["message"]["citations"]

    result = _parse_json(content)
    result["_citations"] = citations
    return result


def _parse_json(text):
    text = text.strip()
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    brace_start = text.find('{')
    if brace_start == -1:
        raise ValueError(f"No JSON in response: {text[:200]}")
    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[brace_start:i + 1])
    raise ValueError(f"Unclosed JSON: {text[:200]}")


def generate_report():
    if not RESULTS_DIR.exists():
        return None
    results = []
    for rp in sorted(RESULTS_DIR.glob("*.json")):
        try:
            results.append(json.load(open(rp)))
        except:
            continue

    if not results:
        return None

    by_status = {"CONFIRMED": [], "LIKELY": [], "SUSPICIOUS": [], "FICTIONAL": []}
    for r in results:
        status = r.get("result", {}).get("status", "SUSPICIOUS")
        by_status.setdefault(status, []).append(r)

    report = {
        "total": len(results),
        "confirmed": len(by_status.get("CONFIRMED", [])),
        "likely": len(by_status.get("LIKELY", [])),
        "suspicious": len(by_status.get("SUSPICIOUS", [])),
        "fictional": len(by_status.get("FICTIONAL", [])),
        "suspicious_races": [
            {"slug": r["slug"], "name": r["name"], "tier": r.get("tier"),
             "summary": r.get("result", {}).get("evidence_summary", "")}
            for r in by_status.get("SUSPICIOUS", [])
        ],
        "fictional_races": [
            {"slug": r["slug"], "name": r["name"], "tier": r.get("tier"),
             "summary": r.get("result", {}).get("evidence_summary", "")}
            for r in by_status.get("FICTIONAL", [])
        ],
    }

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return report


def print_report(report):
    if not report:
        return
    print(f"\n{'=' * 70}")
    print(f"RACE EXISTENCE VERIFICATION — {report['total']} races")
    print(f"{'=' * 70}")
    print(f"  CONFIRMED:  {report['confirmed']}")
    print(f"  LIKELY:     {report['likely']}")
    print(f"  SUSPICIOUS: {report['suspicious']}")
    print(f"  FICTIONAL:  {report['fictional']}")

    if report["suspicious_races"]:
        print(f"\n{'=' * 70}")
        print(f"SUSPICIOUS RACES ({len(report['suspicious_races'])})")
        print(f"{'=' * 70}")
        for r in report["suspicious_races"]:
            print(f"\n  {r['slug']} (T{r.get('tier', '?')})")
            print(f"    {r['summary']}")

    if report["fictional_races"]:
        print(f"\n{'=' * 70}")
        print(f"FICTIONAL RACES ({len(report['fictional_races'])})")
        print(f"{'=' * 70}")
        for r in report["fictional_races"]:
            print(f"\n  {r['slug']} (T{r.get('tier', '?')})")
            print(f"    {r['summary']}")


def main():
    parser = argparse.ArgumentParser(description="Verify race existence via Perplexity")
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--slug", type=str)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    if args.report:
        report = generate_report()
        print_report(report)
        return

    load_env()
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        print("ERROR: PERPLEXITY_API_KEY not set")
        sys.exit(1)

    profiles = load_profiles(tier=args.tier, slug=args.slug)
    print(f"Verifying existence of {len(profiles)} race(s)...\n")

    checked = 0
    skipped = 0
    errors = 0

    for i, (path, data) in enumerate(profiles):
        race = data.get("race", {})
        slug = race.get("slug", path.stem)
        name = race.get("name", slug)
        country = race.get("vitals", {}).get("country", "unknown")
        tier = race.get("nordic_lab_rating", {}).get("tier")

        result_path = RESULTS_DIR / f"{slug}.json"
        if args.skip_existing and result_path.exists():
            skipped += 1
            continue

        print(f"[{i+1}/{len(profiles)}] {name} ({country}, T{tier})")

        try:
            result = verify_existence(api_key, name, country, slug)
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1
            time.sleep(2)
            continue

        citations = result.pop("_citations", [])
        status = result.get("status", "SUSPICIOUS")
        evidence = result.get("evidence_count", 0)
        print(f"  → {status} ({evidence} sources)")

        if status in ("SUSPICIOUS", "FICTIONAL"):
            summary = result.get("evidence_summary", "")
            print(f"  ⚠ {summary[:120]}")

        # Save
        with open(result_path, "w") as f:
            json.dump({
                "slug": slug, "name": name, "country": country, "tier": tier,
                "result": result, "citations": citations,
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, f, indent=2, ensure_ascii=False)
            f.write("\n")

        checked += 1
        if i < len(profiles) - 1:
            time.sleep(2)

    report = generate_report()
    print(f"\nDone. Checked: {checked}, Skipped: {skipped}, Errors: {errors}")
    if report:
        print_report(report)


if __name__ == "__main__":
    main()
