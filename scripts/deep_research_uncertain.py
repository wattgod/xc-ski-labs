#!/usr/bin/env python3
"""
XC Ski Labs — Deep Research on UNCERTAIN Fields via Perplexity

Uses sonar-deep-research (slower, more thorough) to resolve fields that
sonar-pro couldn't verify. Targets races with 3+ UNCERTAIN fields.

Usage:
    python scripts/deep_research_uncertain.py                    # all
    python scripts/deep_research_uncertain.py --min-uncertain 4  # only 4+
    python scripts/deep_research_uncertain.py --tier 2           # by tier
    python scripts/deep_research_uncertain.py --skip-existing
    python scripts/deep_research_uncertain.py --report
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
FACT_CHECK_DIR = PROJECT_ROOT / "data" / "fact-check-results"
DEEP_DIR = PROJECT_ROOT / "data" / "deep-research-results"
REPORT_PATH = PROJECT_ROOT / "data" / "deep-research-report.json"

DEEP_DIR.mkdir(parents=True, exist_ok=True)

FIELDS = ["distance_km", "elevation_m", "discipline", "field_size", "founded", "website"]


def load_env():
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def find_uncertain_races(min_uncertain=3, tier=None, slug=None):
    """Find races with N+ UNCERTAIN fields from fact-check results."""
    candidates = []

    for rp in sorted(FACT_CHECK_DIR.glob("*.json")):
        try:
            fc = json.load(open(rp))
        except:
            continue

        race_slug = fc.get("slug", rp.stem)
        if slug and race_slug != slug:
            continue

        results = fc.get("results", {})
        uncertain_fields = []
        for field in FIELDS:
            v = results.get(field)
            if isinstance(v, dict) and v.get("status") == "UNCERTAIN":
                uncertain_fields.append(field)

        if len(uncertain_fields) < min_uncertain:
            continue

        # Get tier from profile
        profile_path = RACE_DATA_DIR / f"{race_slug}.json"
        if not profile_path.exists():
            continue
        profile = json.load(open(profile_path))
        race_tier = profile["race"]["nordic_lab_rating"]["tier"]

        if tier is not None and race_tier != tier:
            continue

        candidates.append({
            "slug": race_slug,
            "name": fc.get("name", race_slug),
            "tier": race_tier,
            "uncertain_fields": uncertain_fields,
            "facts": fc.get("facts", {}),
            "profile_path": profile_path,
        })

    return candidates


def deep_research(api_key, race_name, country, uncertain_fields, current_values):
    """Use sonar-deep-research to find data for uncertain fields."""

    field_lines = []
    field_labels = {
        "distance_km": "Main race distance in kilometers",
        "elevation_m": "Total elevation gain in meters",
        "discipline": "Technique: classic, skate, or both",
        "field_size": "Typical number of participants/starters",
        "founded": "Year the race was first held",
        "website": "Official website URL",
    }

    for field in uncertain_fields:
        label = field_labels.get(field, field)
        current = current_values.get(field, "unknown")
        field_lines.append(f"- {label}: currently listed as {current}")

    prompt = f"""Research the cross-country ski race "{race_name}" in {country}. I need verified data for these specific fields that I could not confirm via regular web search:

{chr(10).join(field_lines)}

Search thoroughly:
- Official race website
- Worldloppet.com, euroloppet.com, skiclassics.com race listings
- Race results databases (FIS, zone4, sportstats, mylaps)
- Wikipedia articles
- Strava segments or routes
- News articles and race reports
- YouTube race videos and descriptions
- Social media event pages

For each field, provide:
1. The verified value (or null if truly unfindable)
2. The source URL
3. Your confidence: HIGH (official source), MEDIUM (reliable secondary), LOW (indirect/inferred)

Respond ONLY with valid JSON (no markdown fences):
{{
  "fields": {{
    "field_name": {{
      "value": <verified value or null>,
      "source_url": "<URL>",
      "confidence": "HIGH|MEDIUM|LOW",
      "note": "brief explanation"
    }}
  }},
  "race_exists": true|false,
  "best_source": "<most authoritative URL found>"
}}"""

    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": "sonar-deep-research",
            "messages": [
                {"role": "system", "content": "You are a thorough researcher. Always cite URLs."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 4096,
            "temperature": 0.1,
        },
        timeout=300,  # Deep research can take a while
    )

    if response.status_code != 200:
        raise Exception(f"Perplexity API error {response.status_code}: {response.text[:300]}")

    content = response.json()["choices"][0]["message"]["content"]

    citations = []
    data = response.json()
    for loc in [data, data.get("choices", [{}])[0], data.get("choices", [{}])[0].get("message", {})]:
        if "citations" in loc:
            citations = loc["citations"]
            break

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
        raise ValueError(f"No JSON: {text[:200]}")
    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return json.loads(text[brace_start:i + 1])
    raise ValueError(f"Unclosed JSON: {text[:200]}")


def apply_deep_findings(profile_path, findings):
    """Apply HIGH/MEDIUM confidence findings to the profile."""
    fields = findings.get("fields", {})
    if not fields:
        return 0

    data = json.load(open(profile_path))
    vitals = data["race"].setdefault("vitals", {})
    history = data["race"].setdefault("history", {})
    fixes = 0

    valid_disciplines = {"classic", "skate", "both"}

    for field_name, info in fields.items():
        if not isinstance(info, dict):
            continue
        confidence = info.get("confidence", "LOW")
        if confidence == "LOW":
            continue  # Skip low confidence

        value = info.get("value")
        if value is None:
            continue

        # Get current value
        if field_name == "founded":
            current = history.get("founded") or vitals.get("founded")
        elif field_name == "field_size":
            current = vitals.get("field_size") or vitals.get("field_size_estimate")
        else:
            current = vitals.get(field_name)

        # Skip if we already have a value (don't overwrite with deep research)
        # Only fill in missing/null values
        if current is not None and current != "" and current != 0:
            continue

        # Type coercion
        if field_name in ("distance_km", "elevation_m", "founded", "field_size"):
            try:
                if isinstance(value, str):
                    value = int(float(value.replace(",", "")))
                else:
                    value = int(value)
            except (ValueError, TypeError):
                continue

        if field_name == "discipline" and value not in valid_disciplines:
            dl = str(value).lower()
            if "both" in dl or ("classic" in dl and "skate" in dl):
                value = "both"
            elif "classic" in dl:
                value = "classic"
            elif "skate" in dl or "freestyle" in dl or "free" in dl:
                value = "skate"
            else:
                continue

        # Apply
        if field_name == "founded":
            history["founded"] = value
        else:
            vitals[field_name] = value

        fixes += 1

    if fixes:
        with open(profile_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return fixes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4])
    parser.add_argument("--slug", type=str)
    parser.add_argument("--min-uncertain", type=int, default=3)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--auto-apply", action="store_true", help="Apply HIGH/MEDIUM findings to profiles")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()

    if args.report:
        # Quick report from existing results
        total = resolved = 0
        for rp in sorted(DEEP_DIR.glob("*.json")):
            r = json.load(open(rp))
            total += 1
            fields = r.get("result", {}).get("fields", {})
            for f, info in fields.items():
                if isinstance(info, dict) and info.get("value") is not None:
                    resolved += 1
        print(f"Deep research: {total} races, {resolved} fields resolved")
        return

    load_env()
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        print("ERROR: PERPLEXITY_API_KEY not set")
        sys.exit(1)

    candidates = find_uncertain_races(
        min_uncertain=args.min_uncertain, tier=args.tier, slug=args.slug
    )
    print(f"Found {len(candidates)} races with {args.min_uncertain}+ uncertain fields.\n")

    checked = 0
    skipped = 0
    errors = 0
    total_resolved = 0

    for i, c in enumerate(candidates):
        slug = c["slug"]
        result_path = DEEP_DIR / f"{slug}.json"

        if args.skip_existing and result_path.exists():
            skipped += 1
            continue

        uf = c["uncertain_fields"]
        print(f"[{i+1}/{len(candidates)}] {c['name']} (T{c['tier']}, {len(uf)} uncertain: {', '.join(uf)})")

        try:
            result = deep_research(
                api_key, c["name"],
                c["facts"].get("country", "unknown"),
                uf, c["facts"],
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            errors += 1
            time.sleep(5)
            continue

        citations = result.pop("_citations", [])
        fields = result.get("fields", {})
        resolved = sum(1 for f, info in fields.items()
                      if isinstance(info, dict) and info.get("value") is not None)
        total_resolved += resolved
        exists = result.get("race_exists", True)

        status = "✓" if exists else "⚠ MAY NOT EXIST"
        print(f"  {status} — resolved {resolved}/{len(uf)} fields")

        if not exists:
            print(f"  ⚠ RACE MAY NOT EXIST: {result.get('best_source', 'no source')}")

        # Save
        with open(result_path, "w") as f:
            json.dump({
                "slug": slug, "name": c["name"], "tier": c["tier"],
                "uncertain_fields": uf,
                "result": result,
                "citations": citations,
                "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, f, indent=2, ensure_ascii=False)
            f.write("\n")

        # Auto-apply if requested
        if args.auto_apply:
            fixes = apply_deep_findings(c["profile_path"], result)
            if fixes:
                print(f"  Applied {fixes} findings to profile")

        checked += 1
        if i < len(candidates) - 1:
            time.sleep(5)  # Longer pause for deep research

    print(f"\nDone. Checked: {checked}, Skipped: {skipped}, Errors: {errors}")
    print(f"Total fields resolved: {total_resolved}")


if __name__ == "__main__":
    main()
