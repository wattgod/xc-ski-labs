#!/usr/bin/env python3
"""Version the search page's script and race index URLs by their contents.

SiteGround serves /search/nordic-lab-search.js with a one-year max-age and
/search/race-index.json with a 180-day max-age, so a returning visitor keeps
whatever copy they first downloaded. The search page (served uncached)
therefore names both by content hash on its one script tag:

    <script src="nordic-lab-search.js?v=<js hash>" data-index-version="<index hash>"></script>

where each hash is the first 12 hex digits of the file's SHA-256. The script
fetches ``race-index.json?v=<index hash>``. Any change to either file changes
its URL and every browser fetches the new copy; a data-only change leaves the
script's URL (and its cached copy) alone.

    python scripts/search_script_version.py           # stamp the page
    python scripts/search_script_version.py --check   # exit 1 if stale

generate_race_index.py stamps the page after every run. The tests in
tests/test_search_script_version.py, preflight.py and deploy.py's
sync_search() / sync_index() all refuse an unversioned or stale page.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
SEARCH_HTML = WEB_DIR / "nordic-lab-search.html"
SEARCH_JS = WEB_DIR / "nordic-lab-search.js"
SEARCH_INDEX = WEB_DIR / "race-index.json"

INDEX_ATTR = "data-index-version"
SCRIPT_TAG_RE = re.compile(
    r'<script src="nordic-lab-search\.js(?:\?v=[^"]*)?"(?: data-index-version="[^"]*")?></script>'
)


def file_version(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def script_version(js_path: Path = SEARCH_JS) -> str:
    return file_version(js_path)


def index_version(index_path: Path = SEARCH_INDEX) -> str:
    return file_version(index_path)


def script_tag(js_path: Path = SEARCH_JS, index_path: Path = SEARCH_INDEX) -> str:
    return (f'<script src="nordic-lab-search.js?v={script_version(js_path)}" '
            f'{INDEX_ATTR}="{index_version(index_path)}"></script>')


class _Scripts(HTMLParser):
    """Collect the attributes of every real <script src> element (comments are skipped)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attrs = dict(attrs)
            if attrs.get("src") is not None:
                self.scripts.append(attrs)


def search_scripts(html: str) -> list:
    """Attributes of every active <script> that loads the search script, any quoting or case."""
    parser = _Scripts()
    parser.feed(html)
    parser.close()
    return [a for a in parser.scripts
            if urlsplit(a["src"].strip()).path.rsplit("/", 1)[-1].lower() == SEARCH_JS.name.lower()]


def search_script_srcs(html: str) -> list:
    return [a["src"] for a in search_scripts(html)]


def check(html_path: Path = SEARCH_HTML, js_path: Path = SEARCH_JS,
          index_path: Path = SEARCH_INDEX) -> str | None:
    """Return a problem description, or None when the page names the current script and index."""
    scripts = search_scripts(html_path.read_text(encoding="utf-8"))
    if len(scripts) != 1:
        return (f"{html_path.name}: expected one active {SEARCH_JS.name} script tag, "
                f"found {len(scripts)}: {[a['src'] for a in scripts]}")
    src = scripts[0]["src"]
    want = script_version(js_path)
    if parse_qs(urlsplit(src).query).get("v", []) != [want]:
        return (f"{html_path.name}: search script {src!r} is not versioned with the current hash "
                f"v={want}; run python scripts/search_script_version.py")
    want_index = index_version(index_path)
    got_index = scripts[0].get(INDEX_ATTR)
    if got_index != want_index:
        return (f"{html_path.name}: {INDEX_ATTR}={got_index!r} does not match {index_path.name} "
                f"({want_index}); run python scripts/search_script_version.py")
    return None


def stamp(html_path: Path = SEARCH_HTML, js_path: Path = SEARCH_JS,
          index_path: Path = SEARCH_INDEX) -> bool:
    """Rewrite the script tag with the current hashes. Returns True if the file changed."""
    html = html_path.read_text(encoding="utf-8")
    if len(SCRIPT_TAG_RE.findall(html)) != 1:
        raise SystemExit(f"{html_path}: expected exactly one search script tag to stamp")
    new = SCRIPT_TAG_RE.sub(script_tag(js_path, index_path), html)
    changed = new != html
    if changed:
        html_path.write_text(new, encoding="utf-8")
    problem = check(html_path, js_path, index_path)
    if problem:
        raise SystemExit(problem)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the page's script or index URL is stale")
    args = parser.parse_args()
    versions = f"script v={script_version()}, index v={index_version()}"
    if args.check:
        problem = check()
        if problem:
            print(problem)
            return 1
        print(f"search page versioned: {versions}")
        return 0
    changed = stamp()
    print(f"{'stamped' if changed else 'already current'}: {versions}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
