#!/usr/bin/env python3
"""
XC Ski Labs — QC Gate for New Race Profiles

Mandatory quality control pipeline for any new profiles added to the database.
Runs 4 stages in sequence — a profile must pass ALL stages to be accepted.

Stages:
  1. SCHEMA   — required fields, types, scoring math, slug format
  2. EXISTENCE — Perplexity sonar-pro web search (is this a real race?)
  3. FACT-CHECK — Perplexity sonar-pro data verification (are the facts correct?)
  4. NORMALIZE  — clean up any junk fields, coerce types

Usage:
    python scripts/qc_new_profiles.py --slug my-new-race     # single race
    python scripts/qc_new_profiles.py --new                   # auto-detect new (no existence result)
    python scripts/qc_new_profiles.py --slug my-race --fix    # auto-apply fact corrections
    python scripts/qc_new_profiles.py --dry-run               # validate only, no API calls
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
EXISTENCE_DIR = PROJECT_ROOT / "data" / "existence-check-results"
FACT_CHECK_DIR = PROJECT_ROOT / "data" / "fact-check-results"

EXISTENCE_DIR.mkdir(parents=True, exist_ok=True)
FACT_CHECK_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_CRITERIA = [
    "distance", "elevation", "altitude", "field_size", "prestige",
    "international_draw", "course_technicality", "snow_reliability",
    "grooming_quality", "accessibility", "community", "scenery",
    "organization", "competitive_depth",
]
VALID_DISCIPLINES = {"classic", "skate", "both"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

try:
    import requests
except ImportError:
    print("ERROR: requests library required. pip install requests")
    sys.exit(1)


def load_env():
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def find_new_profiles():
    """Find profiles that haven't been through existence verification."""
    existing = {p.stem for p in EXISTENCE_DIR.glob("*.json")}
    new = []
    for p in sorted(RACE_DATA_DIR.glob("*.json")):
        if p.name == "_schema.json":
            continue
        if p.stem not in existing:
            new.append(p)
    return new


def load_profile(path):
    with open(path) as f:
        return json.load(f)


# ── Stage 1: Schema Validation ──────────────────────────────────────

def check_schema(path, data):
    """Validate required fields, types, scoring math."""
    errors = []
    race = data.get("race", {})

    # Required top-level keys
    slug = race.get("slug", "")
    if not slug:
        errors.append("Missing race.slug")
    elif not SLUG_RE.match(slug):
        errors.append(f"Invalid slug format: {slug!r}")
    elif slug != path.stem:
        errors.append(f"Slug {slug!r} doesn't match filename {path.stem!r}")

    if not race.get("name"):
        errors.append("Missing race.name")

    # Vitals
    vitals = race.get("vitals", {})
    if not vitals.get("country"):
        errors.append("Missing vitals.country")
    if not vitals.get("discipline"):
        errors.append("Missing vitals.discipline")
    elif vitals["discipline"] not in VALID_DISCIPLINES:
        errors.append(f"Invalid discipline: {vitals['discipline']!r}")

    distance = vitals.get("distance_km")
    if distance is not None and not isinstance(distance, (int, float)):
        errors.append(f"distance_km must be numeric, got {type(distance).__name__}")

    # Rating
    rating = race.get("nordic_lab_rating", {})
    if not rating:
        errors.append("Missing race.nordic_lab_rating")
    else:
        # Check all 14 criteria present and in range
        for c in REQUIRED_CRITERIA:
            val = rating.get(c)
            if val is None:
                errors.append(f"Missing criterion: {c}")
            elif not isinstance(val, (int, float)) or val < 1 or val > 5:
                errors.append(f"Criterion {c}={val!r} out of range [1,5]")

        # Verify scoring math
        if all(rating.get(c) is not None for c in REQUIRED_CRITERIA):
            total = sum(rating[c] for c in REQUIRED_CRITERIA)
            expected_score = round((total / 70) * 100)
            actual_score = rating.get("overall_score")
            if actual_score != expected_score:
                errors.append(f"Score mismatch: computed {expected_score}, stored {actual_score}")

            # Tier check
            prestige = rating.get("prestige", 1)
            if prestige == 5 and expected_score >= 75:
                expected_tier = 1
            elif prestige == 5:
                expected_tier = 2
            elif expected_score >= 80:
                tier_from_score = 1
                expected_tier = min(tier_from_score, 2) if prestige == 4 else tier_from_score
            elif expected_score >= 60:
                tier_from_score = 2
                expected_tier = max(1, tier_from_score - 1) if prestige == 4 else tier_from_score
            elif expected_score >= 45:
                tier_from_score = 3
                expected_tier = max(1, tier_from_score - 1) if prestige == 4 else tier_from_score
            else:
                tier_from_score = 4
                expected_tier = max(1, tier_from_score - 1) if prestige == 4 else tier_from_score

            actual_tier = rating.get("tier")
            if actual_tier != expected_tier:
                errors.append(f"Tier mismatch: computed {expected_tier}, stored {actual_tier}")

    # No junk fields
    junk = {"race_date", "typical_race_date", "official_website",
            "official_website_url", "typical_participants", "year_founded",
            "region_state_province"}
    found_junk = junk & set(vitals.keys())
    if found_junk:
        errors.append(f"Junk fields in vitals: {found_junk}")

    # No underscore-prefixed metadata
    for key in list(data.get("race", {}).keys()):
        if key.startswith("_"):
            errors.append(f"Metadata key in race: {key}")

    return errors


# ── Stage 2: Existence Verification ─────────────────────────────────

def _parse_json(text):
    text = text.strip()
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    brace_start = text.find('{')
    if brace_start == -1:
        raise ValueError(f"No JSON: {text[:200]}")
    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[brace_start:i + 1])
    raise ValueError(f"Unclosed JSON: {text[:200]}")


def check_existence(api_key, name, country, slug):
    """Verify race exists via Perplexity sonar-pro. Returns (status, result)."""

    # Check cache first
    cached = EXISTENCE_DIR / f"{slug}.json"
    if cached.exists():
        r = json.load(open(cached))
        status = r.get("result", {}).get("status", "UNKNOWN")
        return status, r.get("result", {})

    prompt = f"""Does the cross-country ski race "{name}" in {country} actually exist as a real, organized event?

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
    result = _parse_json(content)

    # Extract citations
    citations = []
    data = response.json()
    for loc in [data, data.get("choices", [{}])[0], data.get("choices", [{}])[0].get("message", {})]:
        if "citations" in loc:
            citations = loc["citations"]
            break

    # Cache
    with open(cached, "w") as f:
        json.dump({
            "slug": slug, "name": name, "country": country,
            "result": result, "citations": citations,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return result.get("status", "UNKNOWN"), result


# ── Stage 3: Fact-Check ──────────────────────────────────────────────

def check_facts(api_key, name, country, facts, slug):
    """Verify key facts via Perplexity sonar-pro. Returns (verdicts, result)."""

    cached = FACT_CHECK_DIR / f"{slug}.json"
    if cached.exists():
        r = json.load(open(cached))
        return r.get("results", {}), r

    fields_to_check = {}
    field_labels = {
        "distance_km": ("Main race distance in km", facts.get("distance_km")),
        "elevation_m": ("Total elevation gain in meters", facts.get("elevation_m") or facts.get("elevation_gain_m")),
        "discipline": ("Technique: classic, skate, or both", facts.get("discipline")),
        "field_size": ("Typical number of participants", facts.get("field_size") or facts.get("field_size_estimate")),
        "founded": ("Year the race was first held", facts.get("founded")),
        "website": ("Official website URL", facts.get("website")),
    }

    field_lines = []
    for field, (label, value) in field_labels.items():
        if value is not None:
            field_lines.append(f"- {field}: {label} — currently listed as: {value}")
            fields_to_check[field] = value

    if not field_lines:
        return {}, {}

    prompt = f"""Fact-check these data fields for the cross-country ski race "{name}" in {country}:

{chr(10).join(field_lines)}

For each field, verify against real web sources and respond with ONLY valid JSON (no markdown fences):
{{
  "field_name": {{
    "status": "CORRECT|WRONG|UNCERTAIN",
    "correct_value": <the correct value if WRONG, else null>,
    "source_url": "<URL>",
    "note": "brief explanation"
  }}
}}

Tolerances (do NOT mark as WRONG if within tolerance):
- distance_km: ±3 km
- elevation_m: ±100 m
- field_size: ±20%
- founded: exact year only"""

    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sonar-pro",
            "messages": [
                {"role": "system", "content": "You fact-check race data against web sources. Respond with JSON only."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 2048,
            "temperature": 0.1,
        },
        timeout=120,
    )

    if response.status_code != 200:
        raise Exception(f"Perplexity API error {response.status_code}: {response.text[:300]}")

    content = response.json()["choices"][0]["message"]["content"]
    result = _parse_json(content)

    citations = []
    data = response.json()
    for loc in [data, data.get("choices", [{}])[0], data.get("choices", [{}])[0].get("message", {})]:
        if "citations" in loc:
            citations = loc["citations"]
            break

    # Cache
    with open(cached, "w") as f:
        json.dump({
            "slug": slug, "name": name,
            "facts": facts, "results": result,
            "citations": citations,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return result, {"results": result, "citations": citations}


# ── Stage 4: Normalize ───────────────────────────────────────────────

def normalize_profile(path, data):
    """Fix common issues: junk fields, type coercion, URL cleanup."""
    fixes = []
    race = data.get("race", {})
    vitals = race.get("vitals", {})

    # Remove junk fields
    junk_fields = {"race_date", "typical_race_date", "official_website",
                   "official_website_url", "typical_participants",
                   "year_founded", "region_state_province"}
    for junk in junk_fields:
        if junk in vitals:
            del vitals[junk]
            fixes.append(f"removed vitals.{junk}")

    # Coerce field_size to int
    for key in ("field_size", "field_size_estimate"):
        val = vitals.get(key)
        if isinstance(val, str):
            nums = re.findall(r'\d+', val.replace(",", ""))
            if nums:
                vitals[key] = int(nums[0])
                fixes.append(f"coerced {key}: {val!r} → {vitals[key]}")

    # Normalize discipline
    discipline = vitals.get("discipline")
    if discipline and discipline not in VALID_DISCIPLINES:
        dl = str(discipline).lower()
        if "both" in dl or ("classic" in dl and ("skate" in dl or "free" in dl)):
            vitals["discipline"] = "both"
        elif "classic" in dl:
            vitals["discipline"] = "classic"
        elif "skate" in dl or "freestyle" in dl or "free" in dl:
            vitals["discipline"] = "skate"
        if vitals.get("discipline") != discipline:
            fixes.append(f"normalized discipline: {discipline!r} → {vitals['discipline']!r}")

    # Clean overly long website URLs
    website = vitals.get("website")
    if website and len(website) > 100:
        vitals["website"] = None
        fixes.append("cleaned website (too long, probably a note)")

    # Upgrade http to https
    if website and website.startswith("http://"):
        vitals["website"] = website.replace("http://", "https://", 1)
        fixes.append("upgraded website to https")

    # Remove underscore-prefixed metadata
    for key in list(race.keys()):
        if key.startswith("_"):
            del race[key]
            fixes.append(f"removed metadata key: {key}")

    if fixes:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return fixes


# ── Main Pipeline ────────────────────────────────────────────────────

def run_qc(profile_path, api_key=None, auto_fix=False, dry_run=False):
    """Run full QC pipeline on a single profile. Returns (passed, report)."""
    data = load_profile(profile_path)
    race = data.get("race", {})
    slug = race.get("slug", profile_path.stem)
    name = race.get("name", slug)
    country = race.get("vitals", {}).get("country", "unknown")

    report = {"slug": slug, "name": name, "stages": {}}
    passed = True

    # ── Stage 1: Schema ──
    print(f"\n  [1/4] Schema validation...")
    schema_errors = check_schema(profile_path, data)
    report["stages"]["schema"] = {
        "passed": len(schema_errors) == 0,
        "errors": schema_errors,
    }
    if schema_errors:
        for e in schema_errors:
            print(f"    FAIL: {e}")
        passed = False
    else:
        print(f"    PASS")

    # ── Stage 2: Existence ──
    print(f"  [2/4] Existence verification...")
    if dry_run:
        cached = EXISTENCE_DIR / f"{slug}.json"
        if cached.exists():
            r = json.load(open(cached))
            status = r.get("result", {}).get("status", "UNKNOWN")
            print(f"    {status} (cached)")
            report["stages"]["existence"] = {"passed": status in ("CONFIRMED", "LIKELY"), "status": status}
            if status not in ("CONFIRMED", "LIKELY"):
                passed = False
        else:
            print(f"    SKIP (dry run, no cache)")
            report["stages"]["existence"] = {"passed": None, "status": "SKIPPED"}
    elif api_key:
        try:
            status, result = check_existence(api_key, name, country, slug)
            evidence = result.get("evidence_count", 0)
            print(f"    {status} ({evidence} sources)")
            report["stages"]["existence"] = {"passed": status in ("CONFIRMED", "LIKELY"), "status": status}
            if status in ("SUSPICIOUS", "FICTIONAL"):
                print(f"    BLOCKED: {result.get('evidence_summary', '')[:150]}")
                passed = False
        except Exception as e:
            print(f"    ERROR: {e}")
            report["stages"]["existence"] = {"passed": False, "status": "ERROR"}
            passed = False
    else:
        print(f"    SKIP (no API key)")
        report["stages"]["existence"] = {"passed": None, "status": "NO_KEY"}

    # ── Stage 3: Fact-Check ──
    print(f"  [3/4] Fact verification...")
    if dry_run or not api_key:
        cached = FACT_CHECK_DIR / f"{slug}.json"
        if cached.exists():
            r = json.load(open(cached))
            results = r.get("results", {})
            wrongs = [f for f, v in results.items() if isinstance(v, dict) and v.get("status") == "WRONG"]
            if wrongs:
                print(f"    {len(wrongs)} WRONG fields (cached): {', '.join(wrongs)}")
            else:
                print(f"    PASS (cached)")
            report["stages"]["fact_check"] = {"passed": len(wrongs) == 0, "wrong_fields": wrongs}
        else:
            reason = "dry run" if dry_run else "no API key"
            print(f"    SKIP ({reason}, no cache)")
            report["stages"]["fact_check"] = {"passed": None, "status": "SKIPPED"}
    elif passed:  # Only fact-check if existence passed
        vitals = race.get("vitals", {})
        history = race.get("history", {})
        facts = {**vitals}
        if history.get("founded"):
            facts["founded"] = history["founded"]

        try:
            time.sleep(2)  # Rate limit
            verdicts, _ = check_facts(api_key, name, country, facts, slug)
            wrongs = [f for f, v in verdicts.items() if isinstance(v, dict) and v.get("status") == "WRONG"]
            uncertain = [f for f, v in verdicts.items() if isinstance(v, dict) and v.get("status") == "UNCERTAIN"]

            if wrongs:
                print(f"    {len(wrongs)} WRONG: {', '.join(wrongs)}")
                for f in wrongs:
                    v = verdicts[f]
                    print(f"      {f}: {facts.get(f)} → {v.get('correct_value')} ({v.get('source_url', 'no source')})")
            if uncertain:
                print(f"    {len(uncertain)} UNCERTAIN: {', '.join(uncertain)}")
            if not wrongs and not uncertain:
                print(f"    PASS (all fields verified)")

            report["stages"]["fact_check"] = {
                "passed": len(wrongs) == 0,
                "wrong_fields": wrongs,
                "uncertain_fields": uncertain,
            }
        except Exception as e:
            print(f"    ERROR: {e}")
            report["stages"]["fact_check"] = {"passed": False, "status": "ERROR"}
    else:
        print(f"    SKIP (existence failed)")
        report["stages"]["fact_check"] = {"passed": None, "status": "SKIPPED"}

    # ── Stage 4: Normalize ──
    print(f"  [4/4] Normalize...")
    if dry_run:
        print(f"    SKIP (dry run)")
        report["stages"]["normalize"] = {"passed": True, "fixes": []}
    else:
        fixes = normalize_profile(profile_path, data)
        if fixes:
            for fix in fixes:
                print(f"    FIX: {fix}")
        else:
            print(f"    PASS (clean)")
        report["stages"]["normalize"] = {"passed": True, "fixes": fixes}

    return passed, report


def main():
    parser = argparse.ArgumentParser(description="QC gate for new race profiles")
    parser.add_argument("--slug", type=str, help="Check a specific race by slug")
    parser.add_argument("--new", action="store_true", help="Auto-detect profiles without existence check")
    parser.add_argument("--fix", action="store_true", help="Auto-apply fact-check corrections")
    parser.add_argument("--dry-run", action="store_true", help="Schema validation only, no API calls")
    args = parser.parse_args()

    load_env()
    api_key = os.environ.get("PERPLEXITY_API_KEY")

    if not api_key and not args.dry_run:
        print("WARNING: PERPLEXITY_API_KEY not set. Running schema checks only.")
        args.dry_run = True

    # Find profiles to check
    profiles = []
    if args.slug:
        path = RACE_DATA_DIR / f"{args.slug}.json"
        if not path.exists():
            print(f"ERROR: {path} not found")
            sys.exit(1)
        profiles.append(path)
    elif args.new:
        profiles = find_new_profiles()
        if not profiles:
            print("No new profiles found (all have existence check results).")
            return
    else:
        print("ERROR: specify --slug or --new")
        sys.exit(1)

    print(f"{'=' * 60}")
    print(f"XC SKI LABS — QC GATE ({len(profiles)} profile(s))")
    print(f"{'=' * 60}")

    total_passed = 0
    total_failed = 0
    blocked = []

    for path in profiles:
        data = load_profile(path)
        name = data.get("race", {}).get("name", path.stem)
        print(f"\n{'─' * 60}")
        print(f"  {name} ({path.stem})")
        print(f"{'─' * 60}")

        passed, report = run_qc(path, api_key=api_key, auto_fix=args.fix, dry_run=args.dry_run)

        if passed:
            total_passed += 1
            print(f"\n  ✓ PASSED")
        else:
            total_failed += 1
            blocked.append(path.stem)
            print(f"\n  ✗ BLOCKED")

        if not args.dry_run and api_key:
            time.sleep(2)  # Rate limit between races

    # Summary
    print(f"\n{'=' * 60}")
    print(f"QC RESULTS: {total_passed} passed, {total_failed} blocked")
    print(f"{'=' * 60}")

    if blocked:
        print(f"\nBLOCKED profiles (do NOT deploy):")
        for slug in blocked:
            print(f"  - {slug}")
        print(f"\nAction: Fix issues or remove profiles before deploying.")
        sys.exit(1)
    else:
        print(f"\nAll profiles passed QC. Safe to regenerate and deploy.")


if __name__ == "__main__":
    main()
