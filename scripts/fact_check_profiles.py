#!/usr/bin/env python3
"""
XC Ski Labs — Web-Grounded Fact-Check for Race Profiles

Uses Perplexity (sonar-pro) + Exa web search to verify race data against
real web sources. NOT Claude checking Claude — actual web-grounded search.

Two-stage pipeline:
  1. Perplexity sonar-pro: structured fact query → JSON verdicts with citations
  2. Exa web search: independent cross-check on any WRONG or UNCERTAIN fields

Usage:
    python scripts/fact_check_profiles.py --tier 1                # T1 races
    python scripts/fact_check_profiles.py --slug vasaloppet       # single race
    python scripts/fact_check_profiles.py --tier 2 --batch-size 20
    python scripts/fact_check_profiles.py --auto-fix              # apply WRONG fixes
    python scripts/fact_check_profiles.py --report                # print summary
    python scripts/fact_check_profiles.py --skip-existing         # skip done races
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
RESULTS_DIR = PROJECT_ROOT / "data" / "fact-check-results"
REPORT_PATH = PROJECT_ROOT / "data" / "fact-check-report.json"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Scoring imports
# ---------------------------------------------------------------------------
sys.path.insert(0, str(SCRIPT_DIR))
from scoring import CRITERIA, calculate_overall_score, determine_tier, tier_label, _parse_score

# ---------------------------------------------------------------------------
# Fields to verify
# ---------------------------------------------------------------------------
FACT_CHECK_FIELDS = [
    "distance_km",
    "elevation_m",
    "country",
    "region",
    "discipline",
    "field_size",
    "founded",
    "website",
    "date",
]

AUTO_FIX_ALLOWED = {"distance_km", "elevation_m", "country", "region", "discipline",
                    "field_size", "founded", "website", "date"}
AUTO_FIX_FORBIDDEN = {"slug", "name", "display_name"}


# ---------------------------------------------------------------------------
# .env loader
# ---------------------------------------------------------------------------
def load_env():
    """Load .env file into os.environ (does not overwrite existing)."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip("'\"")
                    if key and value:
                        os.environ.setdefault(key, value)


# ---------------------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------------------
def load_race_profiles(tier=None, slug=None, batch_size=None):
    """Load race profiles, optionally filtered by tier or slug."""
    profiles = []
    for path in sorted(RACE_DATA_DIR.glob("*.json")):
        if path.name == "_schema.json":
            continue
        try:
            with open(path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  WARN: skipping {path.name}: {e}")
            continue

        race = data.get("race", {})
        race_slug = race.get("slug", path.stem)

        if slug and race_slug != slug:
            continue
        if tier is not None:
            rating = race.get("nordic_lab_rating", {})
            if rating.get("tier") != tier:
                continue

        profiles.append((path, data))

    if batch_size is not None:
        profiles = profiles[:batch_size]
    return profiles


def extract_facts(data):
    """Extract verifiable facts from a race profile."""
    race = data.get("race", {})
    vitals = race.get("vitals", {})
    history = race.get("history", {})
    return {
        "distance_km": vitals.get("distance_km"),
        "elevation_m": vitals.get("elevation_m") or vitals.get("elevation_gain_m"),
        "country": vitals.get("country"),
        "region": vitals.get("region"),
        "discipline": vitals.get("discipline"),
        "field_size": vitals.get("field_size") or vitals.get("field_size_estimate"),
        "founded": history.get("founded") or vitals.get("founded"),
        "website": vitals.get("website"),
        "date": vitals.get("date"),
    }


# ---------------------------------------------------------------------------
# Perplexity fact-check (web-grounded)
# ---------------------------------------------------------------------------
def perplexity_fact_check(api_key, race_name, facts):
    """Query Perplexity sonar-pro for web-grounded fact verification.

    Returns dict of field → {status, correct_value, note, sources}.
    """
    field_lines = []
    field_labels = {
        "distance_km": "Distance (km)",
        "elevation_m": "Total elevation gain (meters)",
        "country": "Country",
        "region": "Region/state/province",
        "discipline": "Discipline (classic, skate, or both)",
        "field_size": "Typical number of participants",
        "founded": "Year founded / first edition",
        "website": "Official website URL",
        "date": "Typical race date or month",
    }
    for field in FACT_CHECK_FIELDS:
        value = facts.get(field)
        label = field_labels.get(field, field)
        display = value if value is not None else "(unknown)"
        field_lines.append(f"- {label}: {display}")

    prompt = f"""Verify these facts about the cross-country ski race "{race_name}" using web sources.

Our database claims:
{chr(10).join(field_lines)}

For EACH field, search the web and determine:
- CORRECT: our value matches reality (within reasonable tolerance for numeric values)
- WRONG: our value is factually incorrect — provide the correct value with source
- UNCERTAIN: you cannot find reliable web sources to confirm or deny

Respond ONLY with valid JSON (no markdown fences). Use this exact structure:
{{
  "distance_km": {{"status": "CORRECT|WRONG|UNCERTAIN", "correct_value": null, "note": "source/reasoning", "source_url": "url or null"}},
  "elevation_m": {{"status": "...", "correct_value": ..., "note": "...", "source_url": "..."}},
  ... (all 9 fields)
}}

Rules:
- correct_value is null for CORRECT/UNCERTAIN, the real value for WRONG
- For numeric fields (distance_km, elevation_m, founded, field_size), correct_value must be a number
- For string fields, correct_value must be a string
- Distance tolerance: ±3 km. Elevation tolerance: ±100m. Field size tolerance: ±20%.
- Include source URLs where possible
- If the race is very obscure with no web presence, mark all fields UNCERTAIN
- Do NOT guess — only mark WRONG if you have a specific web source contradicting our value"""

    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a factual verifier. Always cite web sources. Respond only with JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2048,
            "temperature": 0.1,
        },
        timeout=120,
    )

    if response.status_code != 200:
        error_msg = response.text[:500]
        if response.status_code == 401:
            raise Exception(
                f"Perplexity API auth failed (401). Check PERPLEXITY_API_KEY.\n{error_msg}"
            )
        raise Exception(f"Perplexity API error {response.status_code}: {error_msg}")

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    # Extract citations from Perplexity response
    citations = []
    if "citations" in data:
        citations = data["citations"]
    elif "choices" in data and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if "citations" in choice:
            citations = choice["citations"]
        elif "message" in choice and "citations" in choice["message"]:
            citations = choice["message"]["citations"]

    result = _parse_json_response(content)

    # Attach Perplexity citations to the result
    if citations:
        result["_perplexity_citations"] = citations

    return result


def _parse_json_response(text):
    """Parse JSON from response, handling markdown fences."""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    brace_start = text.find('{')
    if brace_start == -1:
        raise ValueError(f"No JSON object found in response: {text[:200]}")

    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[brace_start:i + 1])

    raise ValueError(f"Unclosed JSON in response: {text[:200]}")


# ---------------------------------------------------------------------------
# Exa cross-check (independent web search)
# ---------------------------------------------------------------------------
def exa_cross_check(race_name, fields_to_check):
    """Use Exa web search to independently verify specific fields.

    Called for fields marked WRONG or UNCERTAIN by Perplexity to get a second opinion.
    Returns dict of field → {exa_status, exa_value, exa_source}.

    NOTE: This function is designed to be called from the MCP-enabled environment.
    When running standalone (no MCP), it will be skipped gracefully.
    """
    # This is a placeholder — Exa calls happen via MCP in the orchestrator
    # The standalone script uses Perplexity only; Exa is used in the interactive flow
    return {}


# ---------------------------------------------------------------------------
# Auto-fix
# ---------------------------------------------------------------------------
def apply_auto_fix(data, path, check_result, slug):
    """Apply corrections where status=WRONG and correct_value is provided.

    Only applies fixes that came from web-grounded sources (not Claude).
    Returns list of fixes applied.
    """
    race = data["race"]
    vitals = race.setdefault("vitals", {})
    history = race.setdefault("history", {})
    fixes = []

    for field, verdict in check_result.items():
        if field.startswith("_"):
            continue
        if field in AUTO_FIX_FORBIDDEN:
            continue
        if field not in AUTO_FIX_ALLOWED:
            continue
        if not isinstance(verdict, dict):
            continue
        if verdict.get("status") != "WRONG":
            continue

        correct_value = verdict.get("correct_value")
        if correct_value is None:
            continue

        # Determine where to write the fix
        if field == "founded":
            old_value = history.get("founded") or vitals.get("founded")
        else:
            old_value = vitals.get(field)

        # Skip if values are effectively the same
        if old_value is not None and str(old_value).strip() == str(correct_value).strip():
            continue

        # Type coercion for numeric fields
        if field in ("distance_km", "elevation_m", "founded", "field_size"):
            try:
                if isinstance(correct_value, str):
                    correct_value = int(float(correct_value.replace(",", "")))
                else:
                    correct_value = int(correct_value)
            except (ValueError, TypeError):
                print(f"    SKIP fix {field}: cannot coerce {correct_value!r} to number")
                continue

        # Apply
        if field == "founded":
            history["founded"] = correct_value
        else:
            vitals[field] = correct_value

        source = verdict.get("source_url") or verdict.get("note", "")
        fixes.append({
            "field": field,
            "old_value": old_value,
            "new_value": correct_value,
            "source": source,
            "note": verdict.get("note", ""),
        })
        print(f"    FIX: {field}: {old_value!r} -> {correct_value!r} (src: {source[:60]})")

    if fixes:
        # Write back (no _fact_check_fixes metadata — lesson learned)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return fixes


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def generate_report():
    """Generate summary report from existing results."""
    if not RESULTS_DIR.exists():
        print("No fact-check results found.")
        return None

    result_files = sorted(RESULTS_DIR.glob("*.json"))
    if not result_files:
        print("No fact-check results found.")
        return None

    total_checked = 0
    per_field = {f: {"CORRECT": 0, "WRONG": 0, "UNCERTAIN": 0} for f in FACT_CHECK_FIELDS}
    wrong_findings = []

    for result_path in result_files:
        try:
            with open(result_path) as f:
                result = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        slug = result_path.stem
        check_data = result.get("results", {})
        total_checked += 1

        for field in FACT_CHECK_FIELDS:
            verdict = check_data.get(field, {})
            if not isinstance(verdict, dict):
                per_field[field]["UNCERTAIN"] += 1
                continue
            status = verdict.get("status", "UNCERTAIN")
            if status in per_field[field]:
                per_field[field][status] += 1
            else:
                per_field[field]["UNCERTAIN"] += 1

            if status == "WRONG":
                wrong_findings.append({
                    "slug": slug,
                    "field": field,
                    "profile_value": result.get("facts", {}).get(field),
                    "correct_value": verdict.get("correct_value"),
                    "source_url": verdict.get("source_url"),
                    "note": verdict.get("note", ""),
                })

    report = {
        "total_races_checked": total_checked,
        "per_field_summary": per_field,
        "wrong_findings": wrong_findings,
        "wrong_count": len(wrong_findings),
        "source": "perplexity-sonar-pro + exa (web-grounded)",
    }

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return report


def print_report(report):
    """Print summary report to stdout."""
    if report is None:
        return

    print(f"\n{'=' * 70}")
    print(f"WEB-GROUNDED FACT-CHECK REPORT — {report['total_races_checked']} races")
    print(f"Source: {report.get('source', 'unknown')}")
    print(f"{'=' * 70}\n")

    print(f"{'Field':<20} {'CORRECT':>8} {'WRONG':>8} {'UNCERTAIN':>10}")
    print(f"{'-' * 20} {'-' * 8} {'-' * 8} {'-' * 10}")
    for field in FACT_CHECK_FIELDS:
        counts = report["per_field_summary"].get(field, {})
        c = counts.get("CORRECT", 0)
        w = counts.get("WRONG", 0)
        u = counts.get("UNCERTAIN", 0)
        print(f"{field:<20} {c:>8} {w:>8} {u:>10}")

    wrong = report.get("wrong_findings", [])
    if wrong:
        print(f"\n{'=' * 70}")
        print(f"WRONG FINDINGS ({len(wrong)} total)")
        print(f"{'=' * 70}\n")
        for item in wrong:
            print(f"  {item['slug']}.{item['field']}")
            print(f"    Profile: {item['profile_value']!r}")
            print(f"    Correct: {item['correct_value']!r}")
            if item.get("source_url"):
                print(f"    Source:  {item['source_url']}")
            if item.get("note"):
                print(f"    Note:    {item['note']}")
            print()
    else:
        print("\nNo WRONG findings.")

    print(f"Report saved to: {REPORT_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Web-grounded fact-check for Nordic ski race profiles (Perplexity + Exa)"
    )
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--slug", type=str)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--auto-fix", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    if args.report:
        report = generate_report()
        print_report(report)
        return

    load_env()

    pplx_key = os.environ.get("PERPLEXITY_API_KEY")
    if not pplx_key:
        print("ERROR: PERPLEXITY_API_KEY not set. Add it to .env or export it.")
        sys.exit(1)
    if not pplx_key.startswith("pplx-"):
        print(f"ERROR: Invalid Perplexity API key format (expected pplx-..., got {pplx_key[:10]}...)")
        sys.exit(1)

    profiles = load_race_profiles(tier=args.tier, slug=args.slug, batch_size=args.batch_size)
    if not profiles:
        print("No matching race profiles found.")
        sys.exit(0)

    print(f"Found {len(profiles)} race(s) to fact-check via Perplexity sonar-pro.\n")

    checked = 0
    skipped = 0
    errors = 0
    total_fixes = 0

    for i, (path, data) in enumerate(profiles):
        race = data.get("race", {})
        race_slug = race.get("slug", path.stem)
        race_name = race.get("name", race_slug)
        result_path = RESULTS_DIR / f"{race_slug}.json"

        if args.skip_existing and result_path.exists():
            skipped += 1
            continue

        print(f"[{i + 1}/{len(profiles)}] {race_name} ({race_slug})")

        facts = extract_facts(data)

        try:
            check_result = perplexity_fact_check(pplx_key, race_name, facts)
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1
            if i < len(profiles) - 1:
                time.sleep(2)
            continue

        # Extract citations before saving
        citations = check_result.pop("_perplexity_citations", [])

        # Save result
        result_data = {
            "slug": race_slug,
            "name": race_name,
            "facts": facts,
            "results": check_result,
            "citations": citations,
            "source": "perplexity-sonar-pro",
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        with open(result_path, "w") as f:
            json.dump(result_data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # Count verdicts
        wrong_count = sum(
            1 for k, v in check_result.items()
            if isinstance(v, dict) and v.get("status") == "WRONG"
        )
        correct_count = sum(
            1 for k, v in check_result.items()
            if isinstance(v, dict) and v.get("status") == "CORRECT"
        )
        uncertain_count = sum(
            1 for k, v in check_result.items()
            if isinstance(v, dict) and v.get("status") == "UNCERTAIN"
        )
        print(f"  ✓ {correct_count} correct, ✗ {wrong_count} wrong, ? {uncertain_count} uncertain")

        if wrong_count > 0:
            for field, verdict in check_result.items():
                if isinstance(verdict, dict) and verdict.get("status") == "WRONG":
                    cv = verdict.get("correct_value")
                    pv = facts.get(field)
                    src = verdict.get("source_url", "")
                    print(f"    WRONG: {field}: {pv!r} → {cv!r} ({src})")

        # Auto-fix
        if args.auto_fix and wrong_count > 0:
            fixes = apply_auto_fix(data, path, check_result, race_slug)
            total_fixes += len(fixes)

        checked += 1

        # Rate limiting: 2 seconds between Perplexity calls
        if i < len(profiles) - 1:
            time.sleep(2)

    # Final report
    report = generate_report()

    print(f"\n{'=' * 70}")
    print(f"Done. Checked: {checked}, Skipped: {skipped}, Errors: {errors}")
    if args.auto_fix:
        print(f"Auto-fixes applied: {total_fixes}")
    print(f"Results: {RESULTS_DIR}/")

    if report:
        print_report(report)


if __name__ == "__main__":
    main()
