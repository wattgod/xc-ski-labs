#!/usr/bin/env python3
"""
youtube_retry.py — Retry YouTube enrichment for races that should have content but don't.

Some races with empty youtube_data.videos definitely should have YouTube content
(well-known events). The original search query just didn't match. This script
tries multiple alternate query variations using language-specific and format-specific
patterns to find content that the standard search missed.

Usage:
    # Dry run — see what would be retried
    python scripts/youtube_retry.py --dry-run

    # Retry all eligible races (T1/T2 + strong XC culture countries)
    python scripts/youtube_retry.py

    # Retry only T1 races
    python scripts/youtube_retry.py --tier 1

    # Retry a single race
    python scripts/youtube_retry.py --slug birkebeinerrennet

    # Limit query variations per race
    python scripts/youtube_retry.py --max-retries 2
"""

import argparse
import json
import subprocess
import sys
import time
from datetime import date
from pathlib import Path

RACE_DATA_DIR = Path(__file__).resolve().parent.parent / "race-data"
RESEARCH_DIR = Path(__file__).resolve().parent.parent / "youtube-research-results"
SCRIPTS_DIR = Path(__file__).resolve().parent

# Countries with strong XC ski culture — races here are likely to have YouTube content
# even if they are T3/T4
STRONG_XC_COUNTRIES = {
    "Norway", "Sweden", "Finland", "Switzerland", "Germany",
    "Austria", "Italy", "USA", "Canada", "France", "Japan",
    "Estonia", "Czech Republic", "Russia", "Poland",
}

# Country-to-language-specific search term mappings
COUNTRY_LANGUAGE_QUERIES = {
    "Germany": [("langlauf", "{name} langlauf"), ("langlaufrennen", "{name} langlaufrennen")],
    "Austria": [("langlauf", "{name} langlauf"), ("langlaufrennen", "{name} langlaufrennen")],
    "Switzerland": [("langlauf", "{name} langlauf"), ("ski de fond", "{name} ski de fond")],
    "Finland": [("hiihto", "{name} hiihto"), ("hiihtolatu", "{name} hiihtolatu")],
    "Sweden": [("skidmaraton", "{name} skidmaraton"), ("skidlopp", "{name} skidlopp")],
    "Norway": [("skimarathon", "{name} skimarathon"), ("skirenn", "{name} skirenn")],
    "France": [("ski de fond", "{name} ski de fond course"), ("skiathlon", "{name} skiathlon")],
    "Italy": [("sci di fondo", "{name} sci di fondo"), ("granfondo sci", "{name} granfondo sci nordico")],
    "Japan": [("クロスカントリースキー", "{name} クロスカントリースキー")],
    "Estonia": [("suusamaraton", "{name} suusamaraton")],
    "Czech Republic": [("běh na lyžích", "{name} běh na lyžích")],
    "Russia": [("лыжный марафон", "{name} лыжный марафон")],
    "Poland": [("bieg narciarski", "{name} bieg narciarski")],
}


def load_race(slug: str) -> dict | None:
    """Load a race profile JSON by slug."""
    path = RACE_DATA_DIR / f"{slug}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def has_youtube_content(race_data: dict) -> bool:
    """Check if a race already has curated YouTube videos."""
    r = race_data.get("race", {})
    videos = r.get("youtube_data", {}).get("videos", [])
    return len(videos) > 0


def get_tier(race_data: dict) -> int:
    """Get the tier number for a race."""
    r = race_data.get("race", {})
    return r.get("nordic_lab_rating", {}).get("tier", 4)


def get_country(race_data: dict) -> str:
    """Get the country for a race."""
    r = race_data.get("race", {})
    return r.get("vitals", {}).get("country", "")


def is_retry_candidate(race_data: dict, tier_filter: int | None = None) -> bool:
    """Determine if a race should be retried.

    Candidates have empty youtube_data.videos AND are either:
    - T1 or T2 (likely to have YouTube content)
    - In a country with strong XC culture
    """
    if has_youtube_content(race_data):
        return False

    tier = get_tier(race_data)
    country = get_country(race_data)

    # If tier filter specified, only match that tier
    if tier_filter is not None:
        return tier == tier_filter

    # T1 or T2 — likely to have content
    if tier <= 2:
        return True

    # Strong XC culture country — worth trying even for T3/T4
    if country in STRONG_XC_COUNTRIES:
        return True

    return False


def build_retry_queries(race_data: dict) -> list[tuple[str, str]]:
    """Build alternate search query variations for a race.

    Returns list of (label, query) tuples, ordered by likelihood of success.
    """
    r = race_data.get("race", {})
    name = r.get("name") or r.get("display_name", "")
    display_name = r.get("display_name") or name
    country = get_country(race_data)
    current_year = date.today().year

    queries = []

    # Universal queries (try for all races)
    queries.append(("quoted+xc", f'"{name}" cross country skiing'))
    queries.append(("name+year", f'"{name}" {current_year} race'))
    queries.append(("display+ski", f'"{display_name}" ski race'))
    queries.append(("name+marathon", f'"{name}" ski marathon'))
    queries.append(("name+loppet", f'"{name}" loppet'))

    # If display_name differs from name, try display_name variants too
    if display_name != name:
        queries.append(("display+xc", f'"{display_name}" cross country skiing'))
        queries.append(("display+year", f'"{display_name}" {current_year} race'))

    # Country-specific language queries
    if country in COUNTRY_LANGUAGE_QUERIES:
        for label, template in COUNTRY_LANGUAGE_QUERIES[country]:
            query = template.format(name=name)
            queries.append((f"lang:{label}", query))

    # Last resort: bare name + skiing
    queries.append(("bare+skiing", f"{name} skiing"))

    return queries


def run_youtube_research(slug: str, query: str, max_results: int = 8) -> dict | None:
    """Run youtube_research.py search_youtube for a custom query.

    Instead of shelling out (which would use the default query builder),
    we import and call the search function directly.
    """
    # Import from youtube_research.py
    sys.path.insert(0, str(SCRIPTS_DIR))
    from youtube_research import search_youtube, extract_video_summary, is_wrong_sport

    videos = search_youtube(query, max_results=max_results)

    # Filter wrong-sport results
    videos = [v for v in videos if not is_wrong_sport(v)]

    if not videos:
        return None

    # Build research-format output (matches what youtube_enrich.py expects)
    results = []
    for v in videos:
        summary = extract_video_summary(v, include_transcript=True)
        results.append(summary)

    return {
        "slug": slug,
        "query": query,
        "video_count": len(results),
        "videos": results,
    }


def run_youtube_enrich(slug: str, research_file: str) -> bool:
    """Run youtube_enrich.py for a race using a research file.

    Returns True if enrichment succeeded (videos were written to profile).
    """
    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "youtube_enrich.py"),
        "--slug", slug,
        "--research-file", research_file,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"    [ERROR] Enrichment failed: {result.stderr[:300]}", file=sys.stderr)
            return False
    except subprocess.TimeoutExpired:
        print(f"    [TIMEOUT] Enrichment timed out for {slug}", file=sys.stderr)
        return False

    # Verify: reload the race and check if videos were written
    race_data = load_race(slug)
    if race_data and has_youtube_content(race_data):
        return True

    return False


def find_candidates(tier_filter: int | None = None) -> list[tuple[str, dict]]:
    """Find all retry candidate races.

    Returns list of (slug, race_data) tuples.
    """
    candidates = []
    for f in sorted(RACE_DATA_DIR.glob("*.json")):
        if f.name.startswith("_"):
            continue
        slug = f.stem
        race_data = load_race(slug)
        if race_data and is_retry_candidate(race_data, tier_filter=tier_filter):
            candidates.append((slug, race_data))
    return candidates


def main():
    parser = argparse.ArgumentParser(
        description="Retry YouTube enrichment for races that should have content but don't"
    )
    parser.add_argument("--tier", type=int, choices=[1, 2, 3, 4],
                        help="Only retry races of this tier")
    parser.add_argument("--slug", type=str,
                        help="Retry a single race by slug")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be retried without making API calls")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Max query variations to try per race (default: 3)")
    parser.add_argument("--max-results", type=int, default=8,
                        help="Max YouTube results per query (default: 8)")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds between API calls (default: 2.0)")
    args = parser.parse_args()

    # Build candidate list
    if args.slug:
        race_data = load_race(args.slug)
        if not race_data:
            print(f"Race not found: {args.slug}", file=sys.stderr)
            sys.exit(1)
        if has_youtube_content(race_data):
            print(f"{args.slug} already has YouTube content ({len(race_data['race'].get('youtube_data', {}).get('videos', []))} videos)")
            print("Use --slug with a race that has no videos, or re-run youtube_enrich.py directly.")
            sys.exit(0)
        candidates = [(args.slug, race_data)]
    else:
        candidates = find_candidates(tier_filter=args.tier)

    if not candidates:
        print("No retry candidates found.")
        sys.exit(0)

    # Summary header
    print(f"\n{'='*70}")
    print(f"YOUTUBE RETRY — {len(candidates)} candidate(s)")
    print(f"{'='*70}")

    # Group by tier for display
    by_tier = {}
    for slug, rd in candidates:
        t = get_tier(rd)
        by_tier.setdefault(t, []).append(slug)

    for t in sorted(by_tier):
        print(f"  Tier {t}: {len(by_tier[t])} races")

    print()

    # Dry run: show candidates and their alternate queries
    if args.dry_run:
        for slug, race_data in candidates:
            r = race_data.get("race", {})
            name = r.get("display_name") or r.get("name", slug)
            tier = get_tier(race_data)
            country = get_country(race_data)
            queries = build_retry_queries(race_data)

            print(f"  {slug} (T{tier}, {country}) — {name}")
            for i, (label, query) in enumerate(queries[:args.max_retries]):
                print(f"    [{i+1}] {label}: {query}")
            if len(queries) > args.max_retries:
                print(f"    ... and {len(queries) - args.max_retries} more (increase --max-retries)")
            print()

        print(f"Total: {len(candidates)} races, up to {args.max_retries} queries each")
        print("Run without --dry-run to execute.")
        return

    # Ensure research output dir exists
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)

    # Execute retries
    successes = []
    failures = []
    skipped = []

    for idx, (slug, race_data) in enumerate(candidates):
        r = race_data.get("race", {})
        name = r.get("display_name") or r.get("name", slug)
        tier = get_tier(race_data)
        country = get_country(race_data)
        queries = build_retry_queries(race_data)[:args.max_retries]

        print(f"\n[{idx+1}/{len(candidates)}] {slug} (T{tier}, {country}) — {name}")

        enriched = False
        for q_idx, (label, query) in enumerate(queries):
            print(f"  Query {q_idx+1}/{len(queries)} ({label}): {query}")

            # Rate limit
            if q_idx > 0 or idx > 0:
                time.sleep(args.delay)

            # Run YouTube search with this query
            research = run_youtube_research(slug, query, max_results=args.max_results)

            if not research or research["video_count"] == 0:
                print(f"    No results")
                continue

            print(f"    Found {research['video_count']} video(s)")

            # Save research results
            research_file = RESEARCH_DIR / f"{slug}-retry.json"
            with open(research_file, "w") as f:
                json.dump(research, f, indent=2)

            # Run enrichment
            print(f"    Running enrichment...")
            time.sleep(args.delay)  # Rate limit before Claude API call

            success = run_youtube_enrich(slug, str(research_file))
            if success:
                print(f"    SUCCESS — enrichment complete")
                successes.append(slug)
                enriched = True
                break
            else:
                print(f"    Enrichment did not produce videos, trying next query...")

        if not enriched:
            failures.append(slug)
            print(f"  FAILED — no query variation produced results")

    # Final summary
    print(f"\n{'='*70}")
    print(f"RETRY SUMMARY")
    print(f"{'='*70}")
    print(f"  Candidates:  {len(candidates)}")
    print(f"  Successes:   {len(successes)}")
    print(f"  Still empty: {len(failures)}")

    if successes:
        print(f"\n  Enriched:")
        for s in successes:
            print(f"    + {s}")

    if failures:
        print(f"\n  Still empty (no YouTube content found):")
        for s in failures:
            print(f"    - {s}")

    print()


if __name__ == "__main__":
    main()
