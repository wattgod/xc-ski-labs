#!/usr/bin/env python3
"""Version the race search script's URL by its contents.

SiteGround serves /search/nordic-lab-search.js with a one-year max-age, so a
returning visitor keeps whatever copy they first downloaded. The search page
(served uncached) therefore loads it as ``nordic-lab-search.js?v=<hash>``,
where <hash> is the first 12 hex digits of the file's SHA-256. Any change to
the script changes the URL and every browser fetches the new copy.

    python scripts/search_script_version.py           # stamp the page
    python scripts/search_script_version.py --check   # exit 1 if stale

tests/test_search_script_version.py, preflight.py and deploy.py's
sync_search() all refuse an unversioned or stale script tag.
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

SCRIPT_TAG_RE = re.compile(r'<script src="nordic-lab-search\.js(?:\?v=[^"]*)?"></script>')


def script_version(js_path: Path = SEARCH_JS) -> str:
    return hashlib.sha256(js_path.read_bytes()).hexdigest()[:12]


def script_tag(js_path: Path = SEARCH_JS) -> str:
    return f'<script src="nordic-lab-search.js?v={script_version(js_path)}"></script>'


class _ScriptSrcs(HTMLParser):
    """Collect the src of every real <script> element (comments are skipped)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.srcs = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            src = dict(attrs).get("src")
            if src is not None:
                self.srcs.append(src)


def search_script_srcs(html: str) -> list:
    """Every active <script src> that points at the search script, any quoting or case."""
    parser = _ScriptSrcs()
    parser.feed(html)
    parser.close()
    return [src for src in parser.srcs
            if urlsplit(src.strip()).path.rsplit("/", 1)[-1].lower() == SEARCH_JS.name.lower()]


def check(html_path: Path = SEARCH_HTML, js_path: Path = SEARCH_JS) -> str | None:
    """Return a problem description, or None when the page loads the current script."""
    srcs = search_script_srcs(html_path.read_text(encoding="utf-8"))
    if len(srcs) != 1:
        return f"{html_path.name}: expected one active {SEARCH_JS.name} script tag, found {len(srcs)}: {srcs}"
    want = script_version(js_path)
    got = parse_qs(urlsplit(srcs[0]).query).get("v", [])
    if got != [want]:
        return (f"{html_path.name}: search script {srcs[0]!r} is not versioned with the current hash "
                f"v={want}; run python scripts/search_script_version.py")
    return None


def stamp(html_path: Path = SEARCH_HTML, js_path: Path = SEARCH_JS) -> bool:
    """Rewrite the script tag with the current hash. Returns True if the file changed."""
    html = html_path.read_text(encoding="utf-8")
    if len(SCRIPT_TAG_RE.findall(html)) != 1:
        raise SystemExit(f"{html_path}: expected exactly one search script tag to stamp")
    new = SCRIPT_TAG_RE.sub(script_tag(js_path), html)
    if new == html:
        return False
    html_path.write_text(new, encoding="utf-8")
    problem = check(html_path, js_path)
    if problem:
        raise SystemExit(problem)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if the page's script URL is stale")
    args = parser.parse_args()
    if args.check:
        problem = check()
        if problem:
            print(problem)
            return 1
        print(f"search script versioned: v={script_version()}")
        return 0
    changed = stamp()
    print(f"{'stamped' if changed else 'already current'}: v={script_version()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
