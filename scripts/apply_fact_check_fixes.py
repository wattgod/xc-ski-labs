#!/usr/bin/env python3
"""
Apply web-grounded fact-check fixes with a blacklist of known false positives.

Reads data/fact-check-results/*.json and applies WRONG corrections to race profiles,
skipping entries in the FALSE_POSITIVES blacklist (verified wrong by Exa cross-check).
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
RESULTS_DIR = PROJECT_ROOT / "data" / "fact-check-results"

# ---------------------------------------------------------------------------
# False positives: Perplexity said WRONG but Exa/manual confirmed our value is correct
# Format: (slug, field)
# ---------------------------------------------------------------------------
FALSE_POSITIVES = {
    # Birkebeinerrennet is classic ONLY — birken.no race rules confirm
    ("birkebeinerrennet", "discipline"),
    # "skate" and "freestyle" are the same discipline in our schema
    ("etoile-des-saisies", "discipline"),
    ("california-gold-rush", "discipline"),
    ("owl-creek-chase", "discipline"),
    ("storlirennet", "discipline"),
    ("oregon-nordic-invitational", "discipline"),
    # "United States" is correct country format (not "Idaho, United States")
    ("boulder-mountain-tour", "country"),
    ("wasa-ski-club-loppet", "country"),
    # Cross-border race — keep existing country
    ("storlirennet", "country"),
    # Same value flagged as WRONG (false positive)
    ("engadin-la-diagonela", "founded"),
    ("baikal-ski-marathon", "distance_km"),
    ("bieg-grunwaldzki", "distance_km"),
    ("stowe-derby", "elevation_m"),
    ("boulder-mountain-tour", "founded"),
    ("lake-louise-loppet", "founded"),
    ("nattvasan", "distance_km"),
    ("kangaroo-hoppet", "distance_km"),
    ("marcialonga-bodo", "distance_km"),
    ("la-sgambeda", "distance_km"),
    ("yllas-pallas", "distance_km"),
    ("ganghoferlauf", "distance_km"),
    ("finlandia-hiihto", "founded"),
    ("transjurassienne", "founded"),
    ("marathon-des-glieres", "founded"),
    ("tana-varangerrennet", "founded"),
    ("ski-north-ultra", "founded"),
    ("sisu-ski-fest", "distance_km"),
    ("tug-hill-tourathon", "distance_km"),
    ("white-pine-stampede", "distance_km"),
    # "libre" means freestyle/skate in our schema — not a real correction
    ("marathon-du-grand-bec", "discipline"),
    # Sovereign Lake: Exa found 50km SnowFun race at same venue
    ("sovereign-lake-loppet", "distance_km"),
    # Nattvasan is freestyle (same as Vasaloppet course)
    # Founded date off by 1 year — low confidence
    ("stafettvasan", "founded"),
    ("koasalauf", "founded"),
    ("marathon-de-bessans", "founded"),
    # Suomen Hiihto distance 60 vs 62 — within 3km tolerance, shouldn't be WRONG
    ("suomen-hiihto", "distance_km"),
    # Bieg Piastow distance 51 vs 50 — within tolerance
    ("bieg-piastow", "distance_km"),
    # Transjurassienne distance 68 vs 70 — within tolerance
    ("transjurassienne", "distance_km"),
    # Valdres 67 vs 65 — within tolerance
    ("valdres-skimaraton", "distance_km"),
    # Fossavatnsgangan elevation — Perplexity confused "highest point" with "elevation gain"
    ("fossavatnsgangan", "elevation_m"),
    # Foulee Blanche field_size 2000 vs 1824 — within 20% tolerance
    ("foulee-blanche", "field_size"),
    # Ugra distance — multiple distances offered, 50km is correct for main race
    ("ugra-ski-marathon", "distance_km"),
    # Viru Maraton distance 42 — standard distance, shortened in bad weather years
    ("viru-maraton", "distance_km"),
    # Tartu Maratoni Retrosoit 30 vs 31 — within tolerance
    ("tartu-maratoni-retrosoit", "distance_km"),
    # Tour de Gaspe — multi-day event, distance debatable
    ("tour-de-gaspe", "distance_km"),
    ("tour-de-gaspe", "discipline"),
    # Snow Farm Challenge — separate from Merino Muster
    ("snow-farm-challenge", "distance_km"),
    # Rajalta Rajalle 440 vs 420 — multi-day ultra, both cited
    ("rajalta-rajalle-hiihto", "distance_km"),
    # Romjulsrennet distance — Perplexity unsure, no confirmed correction
    ("romjulsrennet", "distance_km"),
    # Tallinn discipline — "skate" and "Free Technique" are equivalent
    ("tallinn-ski-marathon", "discipline"),
    # Sonot Kkaazoot field size — single year data, not representative
    ("sonot-kkaazoot", "field_size"),
    # Ski North Ultra field size — 72 vs 100, small race variance
    ("ski-north-ultra", "field_size"),
}

# Races that should be REMOVED (not XC skiing)
REMOVE_PROFILES = [
    "valtellina-orobie-ski-marathon",  # Ski-mountaineering, not XC
]

# Races where Perplexity confused with a different race (needs manual review)
SKIP_ENTIRELY = {
    # salpausselka-hiihto may be confused with Finlandia Hiihto
    "salpausselka-hiihto",
    # traversee-de-la-haute-jura may be confused with Transjurassienne
    "traversee-de-la-haute-jura",
    # Rovaniemi may be confused with Jätkänkynttilä
    "rovaniemi-arctic-ski-marathon",
    # Wasa Ski Club Loppet may be confused with Vasaloppet USA
    "wasa-ski-club-loppet",
}

NUMERIC_FIELDS = {"distance_km", "elevation_m", "founded", "field_size"}


def apply_fixes():
    total_fixes = 0
    total_skipped = 0
    fixed_races = []

    for result_path in sorted(RESULTS_DIR.glob("*.json")):
        try:
            with open(result_path) as f:
                result = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        slug = result.get("slug", result_path.stem)
        results = result.get("results", {})

        if slug in SKIP_ENTIRELY:
            print(f"  SKIP (manual review needed): {slug}")
            continue

        # Find fixes to apply
        fixes_for_race = []
        for field, verdict in results.items():
            if not isinstance(verdict, dict):
                continue
            if verdict.get("status") != "WRONG":
                continue
            if (slug, field) in FALSE_POSITIVES:
                total_skipped += 1
                continue

            correct_value = verdict.get("correct_value")
            if correct_value is None:
                continue

            # Skip same-value false positives
            profile_value = result.get("facts", {}).get(field)
            if str(profile_value).strip() == str(correct_value).strip():
                total_skipped += 1
                continue

            fixes_for_race.append((field, correct_value, verdict.get("source_url", ""), verdict.get("note", "")))

        if not fixes_for_race:
            continue

        # Load the race profile
        race_path = RACE_DATA_DIR / f"{slug}.json"
        if not race_path.exists():
            print(f"  WARN: {slug}.json not found")
            continue

        with open(race_path) as f:
            data = json.load(f)

        race = data.get("race", {})
        vitals = race.setdefault("vitals", {})
        history = race.setdefault("history", {})

        race_fixed = False
        for field, correct_value, source, note in fixes_for_race:
            # Get old value
            if field == "founded":
                old_value = history.get("founded") or vitals.get("founded")
            else:
                old_value = vitals.get(field)

            # Coerce types
            if field in NUMERIC_FIELDS:
                try:
                    if isinstance(correct_value, str):
                        correct_value = int(float(correct_value.replace(",", "")))
                    else:
                        correct_value = int(correct_value)
                except (ValueError, TypeError):
                    print(f"  SKIP {slug}.{field}: cannot coerce {correct_value!r}")
                    total_skipped += 1
                    continue

            # Apply
            if field == "founded":
                history["founded"] = correct_value
            elif field == "elevation_m":
                # Update both elevation fields if they exist
                if "elevation_m" in vitals:
                    vitals["elevation_m"] = correct_value
                if "elevation_gain_m" in vitals:
                    vitals["elevation_gain_m"] = correct_value
                if "elevation_m" not in vitals and "elevation_gain_m" not in vitals:
                    vitals["elevation_m"] = correct_value
            else:
                vitals[field] = correct_value

            print(f"  FIX {slug}.{field}: {old_value!r} → {correct_value!r}")
            total_fixes += 1
            race_fixed = True

        if race_fixed:
            with open(race_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
            fixed_races.append(slug)

    print(f"\n{'=' * 60}")
    print(f"Applied {total_fixes} fixes across {len(fixed_races)} races")
    print(f"Skipped {total_skipped} false positives/ambiguous")
    print(f"Races needing manual review: {SKIP_ENTIRELY}")
    print(f"Races to REMOVE (not XC): {REMOVE_PROFILES}")

    return fixed_races


if __name__ == "__main__":
    apply_fixes()
