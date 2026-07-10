#!/usr/bin/env python3
"""Live-site link checker for XC Ski Labs.

Crawls URLs from the sitemap, shared nav/footer links embedded in the race page
generator, and CTA hrefs from a sample of live race pages. Exits 1 with a
broken-link summary if anything a visitor can click is dead.

Deliberately polite to the SiteGround WAF: capped URL count, small delay,
identifiable User-Agent, GET requests, and the same 15s timeout pattern as the
Roadie Labs reference checker.

Usage:
    python3 scripts/check_links.py [--max-urls 300] [--delay 0.4]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
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


def fetch(url: str, timeout: int = 15) -> tuple[int, str]:
    """GET a URL following redirects; return (final_status, body_or_empty)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read(800_000).decode("utf-8", "replace") if "text/" in content_type or "xml" in content_type else ""
            return resp.status, body
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


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


def load_sitemap_urls(delay: float) -> tuple[set[str], str]:
    """Prefer the LIVE sitemap (deployed truth), fall back to local generated ones.

    Local sitemaps include races generated but not yet deployed — seeding from
    them reports 'not deployed yet' as 'dead', which is noise for a live checker.
    """
    live_url = f"{SITE}/sitemap.xml"
    status, body = fetch(live_url)
    time.sleep(delay)
    if status == 200:
        return parse_sitemap_xml(body), live_url

    for sitemap in LOCAL_SITEMAPS:
        if sitemap.exists():
            return parse_sitemap_xml(sitemap.read_text(encoding="utf-8")), str(sitemap)

    return set(), f"{live_url} ({status or 'ERR'})"


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
    parser.add_argument("--max-urls", type=int, default=300)
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--race-sample-size", type=int, default=10)
    args = parser.parse_args()

    sitemap_urls, sitemap_source = load_sitemap_urls(args.delay)
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

    for url in race_sample:
        status, body = fetch(url)
        if status != 200:
            seed_failures.append((status, url))
        else:
            extractor = LinkExtractor(url)
            extractor.feed(body)
            to_check |= extractor.urls
            cta_urls |= extractor.cta_urls
        time.sleep(args.delay)

    urls = sorted(to_check - cta_urls)
    if len(urls) > args.max_urls:
        print(f"NOTE: capping at {args.max_urls} of {len(urls)} discovered non-CTA URLs "
              f"(raise --max-urls to cover all)")
        urls = urls[:args.max_urls]

    dead = list(seed_failures)
    for url in sorted(cta_urls) + urls:
        status, _ = fetch(url)
        if status != 200:
            dead.append((status, url))
        time.sleep(args.delay)

    print(f"Sitemap source: {sitemap_source}")
    print(f"Checked {len(race_sample)} live race sample pages")
    print(f"Checked {len(cta_urls)} CTA URLs + {len(urls)} discovered URLs")
    if dead:
        print(f"\nDEAD LINKS ({len(dead)}):")
        for status, url in sorted(dead, key=lambda d: d[1]):
            print(f"  {status or 'ERR':>4}  {url}")
        return 1
    print("All links alive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
