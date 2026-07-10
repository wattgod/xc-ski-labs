#!/usr/bin/env python3
"""Validate official website URLs in all race profiles.

Checks each race's vitals.website for dead links, redirects, and timeouts.
Outputs a JSON report and prints a summary table of issues.

Usage:
    python scripts/validate_urls.py
    python scripts/validate_urls.py --tier 1
    python scripts/validate_urls.py --slug american-birkebeiner
    python scripts/validate_urls.py --concurrent 20
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RACE_DATA_DIR = Path(__file__).resolve().parent.parent / "race-data"
REPORT_DIR = Path(__file__).resolve().parent.parent / "data"
REPORT_PATH = REPORT_DIR / "url-validation-report.json"

TIMEOUT_SECONDS = 10
DEFAULT_CONCURRENT = 10
RATE_LIMIT_SECONDS = 0.2

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Status classifications
STATUS_OK = "OK"
STATUS_REDIRECT = "REDIRECT"
STATUS_DEAD = "DEAD"
STATUS_TIMEOUT = "TIMEOUT"
STATUS_MISSING = "MISSING"


# ---------------------------------------------------------------------------
# Rate limiter (per-domain)
# ---------------------------------------------------------------------------

class DomainRateLimiter:
    """Enforces minimum delay between requests to the same domain."""

    def __init__(self, min_interval: float = RATE_LIMIT_SECONDS):
        self._lock = Lock()
        self._last_request: dict[str, float] = {}
        self._min_interval = min_interval

    def wait(self, domain: str) -> None:
        with self._lock:
            now = time.monotonic()
            last = self._last_request.get(domain, 0.0)
            elapsed = now - last
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_request[domain] = time.monotonic()


# ---------------------------------------------------------------------------
# Profile loading
# ---------------------------------------------------------------------------

def load_profiles(tier: int | None = None, slug: str | None = None) -> list[dict]:
    """Load race profiles from race-data/, applying optional filters."""
    profiles = []
    for filepath in sorted(RACE_DATA_DIR.glob("*.json")):
        if filepath.name == "_schema.json":
            continue
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  WARNING: Could not read {filepath.name}: {exc}", file=sys.stderr)
            continue

        race = data.get("race", {})
        race_slug = race.get("slug", filepath.stem)

        if slug and race_slug != slug:
            continue

        if tier is not None:
            race_tier = race.get("nordic_lab_rating", {}).get("tier")
            if race_tier != tier:
                continue

        profiles.append({
            "slug": race_slug,
            "name": race.get("display_name") or race.get("name", race_slug),
            "tier": race.get("nordic_lab_rating", {}).get("tier"),
            "website": race.get("vitals", {}).get("website"),
        })

    return profiles


# ---------------------------------------------------------------------------
# URL checking
# ---------------------------------------------------------------------------

def _domains_differ(url_a: str, url_b: str) -> bool:
    """Return True if two URLs have meaningfully different domains.

    Ignores www. prefix differences (e.g. example.com vs www.example.com).
    """
    def _norm(url: str) -> str:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host

    return _norm(url_a) != _norm(url_b)


def check_url(
    url: str,
    rate_limiter: DomainRateLimiter,
) -> dict:
    """Check a single URL. Returns result dict with status, code, final_url, response_time."""
    domain = urlparse(url).netloc
    rate_limiter.wait(domain)

    session = requests.Session()
    session.headers.update(HEADERS)
    session.max_redirects = 10

    result = {
        "original_url": url,
        "final_url": None,
        "status_code": None,
        "response_time_ms": None,
        "error": None,
    }

    # Try HEAD first, fall back to GET
    for method in (session.head, session.get):
        try:
            start = time.monotonic()
            resp = method(
                url,
                timeout=TIMEOUT_SECONDS,
                allow_redirects=True,
            )
            elapsed_ms = round((time.monotonic() - start) * 1000)

            result["status_code"] = resp.status_code
            result["final_url"] = resp.url
            result["response_time_ms"] = elapsed_ms

            if resp.status_code < 400:
                # Success — classify
                if _domains_differ(url, resp.url):
                    result["classification"] = STATUS_REDIRECT
                else:
                    result["classification"] = STATUS_OK
                return result

            # 4xx/5xx on HEAD — try GET before giving up
            if method == session.head:
                rate_limiter.wait(domain)
                continue
            else:
                result["classification"] = STATUS_DEAD
                result["error"] = f"HTTP {resp.status_code}"
                return result

        except requests.exceptions.Timeout:
            result["classification"] = STATUS_TIMEOUT
            result["error"] = "Connection timed out"
            return result

        except requests.exceptions.TooManyRedirects:
            result["classification"] = STATUS_DEAD
            result["error"] = "Too many redirects"
            return result

        except requests.exceptions.ConnectionError as exc:
            # On HEAD connection error, try GET
            if method == session.head:
                rate_limiter.wait(domain)
                continue
            result["classification"] = STATUS_DEAD
            result["error"] = f"Connection error: {_short_error(exc)}"
            return result

        except requests.exceptions.RequestException as exc:
            if method == session.head:
                rate_limiter.wait(domain)
                continue
            result["classification"] = STATUS_DEAD
            result["error"] = f"Request error: {_short_error(exc)}"
            return result

    # Should not reach here, but guard anyway
    result["classification"] = STATUS_DEAD
    result["error"] = "All request methods failed"
    return result


def _short_error(exc: Exception) -> str:
    """Return a short, readable error string."""
    msg = str(exc)
    # Trim overly verbose connection error messages
    if len(msg) > 120:
        msg = msg[:120] + "..."
    return msg


# ---------------------------------------------------------------------------
# Main validation logic
# ---------------------------------------------------------------------------

def validate_all(
    profiles: list[dict],
    concurrent: int = DEFAULT_CONCURRENT,
) -> list[dict]:
    """Validate URLs for all profiles. Returns list of result dicts."""
    rate_limiter = DomainRateLimiter()
    results = []

    # Separate profiles with and without URLs
    to_check = []
    for profile in profiles:
        url = profile["website"]
        if not url:
            results.append({
                "slug": profile["slug"],
                "name": profile["name"],
                "tier": profile["tier"],
                "classification": STATUS_MISSING,
                "original_url": None,
                "final_url": None,
                "status_code": None,
                "response_time_ms": None,
                "error": None,
            })
        else:
            to_check.append(profile)

    if not to_check:
        return results

    print(f"Checking {len(to_check)} URLs with {concurrent} threads...\n")

    futures = {}
    with ThreadPoolExecutor(max_workers=concurrent) as executor:
        for profile in to_check:
            future = executor.submit(check_url, profile["website"], rate_limiter)
            futures[future] = profile

        done_count = 0
        for future in as_completed(futures):
            done_count += 1
            profile = futures[future]
            try:
                url_result = future.result()
            except Exception as exc:
                url_result = {
                    "original_url": profile["website"],
                    "final_url": None,
                    "status_code": None,
                    "response_time_ms": None,
                    "classification": STATUS_DEAD,
                    "error": f"Unexpected error: {exc}",
                }

            result = {
                "slug": profile["slug"],
                "name": profile["name"],
                "tier": profile["tier"],
                **url_result,
            }
            results.append(result)

            # Progress indicator
            status = url_result["classification"]
            marker = "." if status == STATUS_OK else status[0]
            print(f"\r  [{done_count}/{len(to_check)}] {marker}", end="", flush=True)

    print()  # Newline after progress
    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary(results: list[dict]) -> None:
    """Print summary counts and issue table."""
    counts = defaultdict(int)
    for r in results:
        counts[r["classification"]] += 1

    total = len(results)
    print("\n" + "=" * 70)
    print("URL VALIDATION SUMMARY")
    print("=" * 70)
    print(f"  Total profiles:  {total}")
    print(f"  OK:              {counts.get(STATUS_OK, 0)}")
    print(f"  REDIRECT:        {counts.get(STATUS_REDIRECT, 0)}")
    print(f"  DEAD:            {counts.get(STATUS_DEAD, 0)}")
    print(f"  TIMEOUT:         {counts.get(STATUS_TIMEOUT, 0)}")
    print(f"  MISSING:         {counts.get(STATUS_MISSING, 0)}")
    print("=" * 70)

    # Issue table: DEAD, TIMEOUT, REDIRECT
    issues = [
        r for r in results
        if r["classification"] in (STATUS_DEAD, STATUS_TIMEOUT, STATUS_REDIRECT)
    ]

    if not issues:
        print("\nNo issues found. All URLs are healthy.")
        return

    # Sort: DEAD first, then TIMEOUT, then REDIRECT
    priority = {STATUS_DEAD: 0, STATUS_TIMEOUT: 1, STATUS_REDIRECT: 2}
    issues.sort(key=lambda r: (priority.get(r["classification"], 9), r["slug"]))

    print(f"\nISSUES ({len(issues)}):")
    print("-" * 70)
    print(f"  {'STATUS':<10} {'TIER':<5} {'SLUG':<35} {'DETAIL'}")
    print("-" * 70)

    for r in issues:
        tier_str = f"T{r['tier']}" if r["tier"] else "—"
        if r["classification"] == STATUS_REDIRECT:
            detail = f"{r['original_url']} -> {r['final_url']}"
        elif r["error"]:
            detail = f"{r['original_url']}  ({r['error']})"
        else:
            detail = r["original_url"] or "—"

        # Truncate detail for display
        max_detail = 80
        if len(detail) > max_detail:
            detail = detail[: max_detail - 3] + "..."

        print(f"  {r['classification']:<10} {tier_str:<5} {r['slug']:<35} {detail}")

    print("-" * 70)


def save_report(results: list[dict]) -> Path:
    """Save full results as JSON report."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_profiles": len(results),
        "summary": {},
        "results": results,
    }

    counts = defaultdict(int)
    for r in results:
        counts[r["classification"]] += 1
    report["summary"] = dict(counts)

    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return REPORT_PATH


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate official website URLs in race profiles.",
    )
    parser.add_argument(
        "--tier",
        type=int,
        choices=[1, 2, 3, 4],
        help="Filter to a specific tier (1-4).",
    )
    parser.add_argument(
        "--slug",
        type=str,
        help="Check a single race by slug.",
    )
    parser.add_argument(
        "--concurrent",
        type=int,
        default=DEFAULT_CONCURRENT,
        help=f"Number of concurrent requests (default: {DEFAULT_CONCURRENT}).",
    )
    args = parser.parse_args()

    if not RACE_DATA_DIR.is_dir():
        print(f"ERROR: Race data directory not found: {RACE_DATA_DIR}", file=sys.stderr)
        sys.exit(1)

    profiles = load_profiles(tier=args.tier, slug=args.slug)
    if not profiles:
        filter_desc = []
        if args.tier:
            filter_desc.append(f"tier={args.tier}")
        if args.slug:
            filter_desc.append(f"slug={args.slug}")
        print(f"No profiles found matching filters: {', '.join(filter_desc) or 'none'}")
        sys.exit(0)

    print(f"Loaded {len(profiles)} race profile(s) from {RACE_DATA_DIR.name}/")

    results = validate_all(profiles, concurrent=args.concurrent)

    report_path = save_report(results)
    print(f"\nFull report saved to: {report_path}")

    print_summary(results)

    # Exit code: 1 if any DEAD links found
    dead_count = sum(1 for r in results if r["classification"] == STATUS_DEAD)
    sys.exit(1 if dead_count > 0 else 0)


if __name__ == "__main__":
    main()
