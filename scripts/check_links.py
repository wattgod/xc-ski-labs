#!/usr/bin/env python3
"""Live-site link checker for XC Ski Labs.

Crawls URLs from the sitemap, shared nav/footer links embedded in the race page
generator, and CTA hrefs from a sample of live race pages. Exits 1 with a
broken-link summary if anything a visitor can click is dead.

Deliberately polite to the SiteGround WAF: capped URL count, a bounded worker
pool with a small jittered per-worker pause, identifiable User-Agent, GET
requests, and the same 15s timeout pattern as the Roadie Labs reference checker.

Usage:
    python3 scripts/check_links.py [--max-urls 300] [--delay 0.4] [--workers 10]
"""

from __future__ import annotations

import argparse
import http.client
import json
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path

SITE = "https://xcskilabs.com"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = PROJECT_ROOT / "scripts" / "generate_race_pages.py"
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
LOCAL_SITEMAPS = (
    PROJECT_ROOT / "output" / "sitemap.xml",
    PROJECT_ROOT / "web" / "sitemap.xml",
)

EXTRA_URLS = [
    f"{SITE}/sitemap.xml",
    f"{SITE}/robots.txt",
    f"{SITE}/race-dates.json",
    f"{SITE}/llms.txt",
    f"{SITE}/feed/races.xml",
]

CTA_CLASSES = {"gl-training-cta", "gl-sticky-cta-btn"}
CTA_PATH_MARKERS = ("/questionnaire/", "/coaching/")
UA = "XCSkiLabs-LinkCheck/1.0 (+https://xcskilabs.com; weekly self-audit)"

DEFAULT_MAX_URLS = 300
DEFAULT_DELAY = 0.4      # jittered pause after each request, per worker
DEFAULT_WORKERS = 10     # bounded pool (immune_check's prep-kit check uses 12)
DEFAULT_TIMEOUT = 15     # per-request socket timeout


def normalize_url(raw: str, base: str = SITE + "/", keep_query: bool = False) -> str | None:
    """Return a normalized same-site absolute URL, or None for ignored links."""
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith(("#", "mailto:", "tel:", "data:", "javascript:")):
        return None

    url = urllib.parse.urljoin(base, raw)
    parsed = urllib.parse.urlparse(url)
    site_host = urllib.parse.urlparse(SITE).netloc
    if parsed.netloc != site_host:
        return None

    query = f"?{parsed.query}" if keep_query and parsed.query else ""
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}{query}"


class LinkExtractor(HTMLParser):
    """Collect same-site links/assets plus CTA links that must not be missed."""

    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.urls: set[str] = set()
        self.cta_urls: set[str] = set()

    def handle_starttag(self, tag, attrs):
        attr = dict(attrs)
        class_names = set(attr.get("class", "").split())

        for key in ("href", "src"):
            val = attr.get(key)
            url = normalize_url(val or "", self.base_url)
            if url:
                self.urls.add(url)

        href = attr.get("href")
        if not href:
            return

        path = urllib.parse.urlparse(urllib.parse.urljoin(self.base_url, href)).path
        is_cta = bool(class_names & CTA_CLASSES) or any(marker in path for marker in CTA_PATH_MARKERS)
        if is_cta:
            cta_url = normalize_url(href, self.base_url, keep_query=True)
            if cta_url:
                self.cta_urls.add(cta_url)


# SiteGround's bot protection answers with HTTP 202 + an `sg-captcha` header
# instead of the page (Roadie Labs, 2026-07-22: 18 false "dead" findings, all
# 202). A 202 is never a real response from this static site, so exactly 202
# is treated as a challenge (a real 404/500 stays dead even if it carries the
# header): back off, retry, and report still-challenged URLs separately
# rather than as dead links. Retries draw from a scan-wide sleep budget so a
# long WAF window can't blow the caller's timeout (immune_check allows 900s
# for the whole subprocess) — once the budget is spent, challenged URLs are
# recorded immediately without retrying.
#
# Connection-level failures (socket timeout, reset, SSL, DNS/URLError) get the
# same treatment (2026-08-31, #12): under WAF pressure SiteGround also stalls
# or drops connections, and a checker cannot tell "site down" from "the WAF
# dropped me". They are retried from the same budget and, if they persist,
# reported as inconclusive (status 0, printed as ERR) — never as dead. Only a
# real HTTP status (an HTTPError such as 404/500) is a dead link.
CHALLENGE_BACKOFF = (20, 45)   # seconds to wait before each retry
CHALLENGE_RETRY_BUDGET = 180   # total seconds of backoff sleep per scan

_challenge_budget = CHALLENGE_RETRY_BUDGET
# Workers share the budget (2026-09-03, #15): the check-and-decrement is done
# under a lock so a concurrent burst of challenges can't race it negative.
_budget_lock = threading.Lock()

# socket.timeout/TimeoutError, ConnectionResetError, ssl.SSLError and
# urllib.error.URLError are all OSError subclasses; RemoteDisconnected and
# IncompleteRead are http.client.HTTPException subclasses.
TRANSPORT_ERRORS = (OSError, http.client.HTTPException)


def _reserve_backoff(pause: int) -> bool:
    """Atomically take `pause` seconds from the scan-wide retry budget."""
    global _challenge_budget
    with _budget_lock:
        if _challenge_budget < pause:
            return False
        _challenge_budget -= pause
        return True


def _polite_pause(delay: float) -> None:
    """Small jittered pause after a request. Runs inside each worker, so it
    spreads the pool's requests out rather than serialising the whole scan."""
    if delay > 0:
        time.sleep(random.uniform(0.5, 1.5) * delay)


def fetch_once(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str, bool]:
    """GET a URL following redirects; return (final_status, body, inconclusive).

    `inconclusive` is True for a WAF challenge (status 202) and for a
    connection-level failure (status 0: timeout / reset / SSL / DNS). Both mean
    "could not verify", never "dead". A real HTTP error keeps its status and is
    conclusive.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read(800_000).decode("utf-8", "replace") if "text/" in content_type or "xml" in content_type else ""
            return resp.status, body, resp.status == 202
    except urllib.error.HTTPError as e:
        return e.code, "", e.code == 202
    except TRANSPORT_ERRORS:
        return 0, "", True
    except Exception:  # noqa: BLE001 — a non-transport failure (e.g. malformed URL) is a real problem
        return 0, "", False


def fetch(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str, bool]:
    """fetch_once, retrying with backoff (budget-capped) while the result is inconclusive."""
    status, body, inconclusive = fetch_once(url, timeout)
    for pause in CHALLENGE_BACKOFF:
        if not inconclusive:
            break
        kind = "WAF challenge" if status == 202 else "Connection error"
        if not _reserve_backoff(pause):
            print(f"  {kind} on {url} — retry budget spent, recording as inconclusive")
            break
        print(f"  {kind} on {url} — retrying in {pause}s")
        time.sleep(pause)
        status, body, inconclusive = fetch_once(url, timeout)
    return status, body, inconclusive


def parse_sitemap_xml(xml_text: str) -> set[str]:
    """Extract same-site URLs from a sitemap XML document."""
    urls: set[str] = set()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return urls

    for loc in root.findall(".//{*}loc"):
        if loc.text:
            url = normalize_url(loc.text)
            if url:
                urls.add(url)
    return urls


def load_sitemap_urls(delay: float) -> tuple[set[str], str, int | None]:
    """Prefer the LIVE sitemap (deployed truth), fall back to local generated ones.

    Local sitemaps include races generated but not yet deployed — seeding from
    them reports 'not deployed yet' as 'dead', which is noise for a live checker.
    Returns (urls, source, inconclusive_status): None when the live sitemap was
    fetched cleanly, else the status the live fetch ended on (202 = WAF
    challenge, 0 = connection failure) — an unverifiable live sitemap falls back
    to local files but must be surfaced, not silently absorbed.
    """
    live_url = f"{SITE}/sitemap.xml"
    status, body, inconclusive = fetch(live_url)
    _polite_pause(delay)
    if status == 200 and not inconclusive:
        return parse_sitemap_xml(body), live_url, None

    blocked = status if inconclusive else None
    for sitemap in LOCAL_SITEMAPS:
        if sitemap.exists():
            return parse_sitemap_xml(sitemap.read_text(encoding="utf-8")), str(sitemap), blocked

    return set(), f"{live_url} ({status or 'ERR'})", blocked


def load_race_slugs() -> set[str]:
    """Read race slugs so the checker can sample actual race pages from sitemap URLs."""
    slugs: set[str] = set()
    for path in sorted(RACE_DATA_DIR.glob("*.json")):
        if path.name == "_schema.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        race = data.get("race", {})
        slug = race.get("slug") or path.stem
        if slug:
            slugs.add(str(slug))
    return slugs


def extract_generator_hrefs() -> set[str]:
    """Collect static same-site hrefs embedded in scripts/generate_race_pages.py."""
    try:
        source = GENERATOR.read_text(encoding="utf-8")
    except OSError:
        return set()

    urls: set[str] = set()
    for match in re.finditer(r"""href=(["'])(.*?)\1""", source):
        href = match.group(2)
        if "{" in href or "}" in href:
            continue
        url = normalize_url(href)
        if url:
            urls.add(url)
    return urls


def race_sample_from_sitemap(sitemap_urls: set[str], sample_size: int = 10) -> list[str]:
    """Choose a deterministic sample of race page URLs from the sitemap."""
    race_slugs = load_race_slugs()
    sampled: list[str] = []
    for url in sorted(sitemap_urls):
        path = urllib.parse.urlparse(url).path.strip("/")
        slug = path[len("race/"):] if path.startswith("race/") else path
        if slug in race_slugs:
            sampled.append(url)
        if len(sampled) == sample_size:
            break
    return sampled


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-urls", type=int, default=DEFAULT_MAX_URLS)
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help="jittered pause after each request, per worker (seconds)")
    parser.add_argument("--race-sample-size", type=int, default=10)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help="concurrent fetch workers (1 = fully serial)")
    args = parser.parse_args()

    sitemap_urls, sitemap_source, sitemap_blocked = load_sitemap_urls(args.delay)
    generator_urls = extract_generator_hrefs()
    race_sample = race_sample_from_sitemap(sitemap_urls, args.race_sample_size)

    to_check: set[str] = set(EXTRA_URLS) | sitemap_urls | generator_urls
    cta_urls: set[str] = set()
    seed_failures: list[tuple[int, str]] = []

    if len(race_sample) < args.race_sample_size:
        seed_failures.append((
            0,
            f"CONFIG: sampled {len(race_sample)} race pages from sitemap; "
            f"expected {args.race_sample_size}",
        ))

    def probe(url: str) -> tuple[int, str, bool]:
        result = fetch(url)
        _polite_pause(args.delay)
        return result

    challenged_urls: list[tuple[int, str]] = []
    if sitemap_blocked is not None:
        challenged_urls.append((sitemap_blocked, f"{SITE}/sitemap.xml"))

    # Bounded pool (#15): the fully serial loop (15s timeout + budgeted backoff
    # + 0.4s pause per URL, up to 300 URLs) blew immune_check's 900s subprocess
    # budget on heavy-WAF days. pool.map keeps result order == input order, so
    # the classification below is unchanged; only the fetches overlap.
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        for url, (status, body, inconclusive) in zip(race_sample, pool.map(probe, race_sample)):
            if inconclusive:
                challenged_urls.append((status, url))
            elif status != 200:
                seed_failures.append((status, url))
            else:
                extractor = LinkExtractor(url)
                extractor.feed(body)
                to_check |= extractor.urls
                cta_urls |= extractor.cta_urls

        urls = sorted(to_check - cta_urls)
        if len(urls) > args.max_urls:
            print(f"NOTE: capping at {args.max_urls} of {len(urls)} discovered non-CTA URLs "
                  f"(raise --max-urls to cover all)")
            urls = urls[:args.max_urls]

        dead = list(seed_failures)
        ordered = sorted(cta_urls) + urls
        for url, (status, _, inconclusive) in zip(ordered, pool.map(probe, ordered)):
            if inconclusive:
                challenged_urls.append((status, url))
            elif status != 200:
                dead.append((status, url))

    challenged_set = {u for _, u in challenged_urls}
    n_challenged_seeds = len(challenged_set & set(race_sample))
    print(f"Sitemap source: {sitemap_source}"
          + (" (LIVE sitemap unverifiable — fell back to local)" if sitemap_blocked is not None else ""))
    print(f"Checked {len(race_sample) - n_challenged_seeds} of {len(race_sample)} live race sample pages"
          + (f" ({n_challenged_seeds} unverifiable — their outbound links NOT crawled "
             f"this run)" if n_challenged_seeds else ""))
    print(f"Checked {len(cta_urls)} CTA URLs + {len(urls)} discovered URLs")
    # Print challenged BEFORE dead: immune_check parses everything after the
    # "DEAD LINKS" header as dead links. The header must keep starting with
    # "WAF-CHALLENGED" — immune_check keys its section parse on that prefix.
    if challenged_urls:
        rows = sorted(set(challenged_urls), key=lambda d: d[1])
        print(f"\nWAF-CHALLENGED ({len(rows)}): still behind SiteGround's bot challenge "
              f"(202) or failing at the connection level (ERR) after retries — "
              f"scan inconclusive, NOT dead links")
        for status, url in rows:
            print(f"  {status or 'ERR':>4}  {url}")
    if dead:
        rows = sorted(set(dead), key=lambda d: d[1])
        print(f"\nDEAD LINKS ({len(rows)}):")
        for status, url in rows:
            print(f"  {status or 'ERR':>4}  {url}")
        return 1
    if challenged_urls:
        # Exit 2, not 0: an inconclusive scan must not read as a green one in
        # the weekly workflow. immune_check treats rc 2 + WAF block as YELLOW.
        print("No dead links found, but the scan is INCONCLUSIVE (WAF challenges / connection errors).")
        return 2
    print("All links alive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
