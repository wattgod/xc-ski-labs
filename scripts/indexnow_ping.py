#!/usr/bin/env python3
"""Ping IndexNow (Bing/Yandex/Seznam/etc.) when race URLs change.

IndexNow lets a site push updated-URL notifications instead of waiting for a
crawler to rediscover them. The key below is a static, non-secret token —
its matching web/{key}.txt file (served at the site root) is what proves
ownership of the host, per the IndexNow protocol.

Modeled on the road repo's scripts/indexnow_ping.py. This key is new and
distinct from both the road and gravel repos' IndexNow keys.

Usage:
    python scripts/indexnow_ping.py                     # ping every URL in race-index.json
    python scripts/indexnow_ping.py --urls URL [URL...]  # ping specific URLs
    python scripts/indexnow_ping.py --dry-run            # preview payload, no network call
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
INDEX_FILE = PROJECT_ROOT / "web" / "race-index.json"
SITE_URL = "https://xcskilabs.com"
SITE_HOST = "xcskilabs.com"

# Static IndexNow key — not a secret, just proves host ownership via
# web/{INDEXNOW_KEY}.txt served at the site root. Generated once with
# secrets.token_hex(32); do not rotate casually, the key file on the
# server must match this constant. Distinct from the road and gravel
# repos' keys.
INDEXNOW_KEY = "be7599e0840353b98c18be58d6bce205be449a0e6863fa70bb5e80b0e72d0f3c"

INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
MAX_URLS_PER_BATCH = 10000


def build_payload(url_list: list[str], host: str = SITE_HOST, key: str = INDEXNOW_KEY) -> dict:
    """Build the IndexNow JSON payload for a batch of URLs (<= 10,000)."""
    return {
        "host": host,
        "key": key,
        "keyLocation": f"{SITE_URL}/{key}.txt",
        "urlList": url_list,
    }


def urls_from_index(index_path: Path = INDEX_FILE) -> list[str]:
    """Build the full list of canonical race-page URLs from race-index.json.

    race-index.json here is {"generated": ..., "count": ..., "races": [...]}
    with compact keys per CLAUDE.md pitfall #6 — slug lives at "s".
    """
    if not index_path.exists():
        return []
    index = json.loads(index_path.read_text(encoding="utf-8"))
    races = index.get("races", []) if isinstance(index, dict) else index
    return [f"{SITE_URL}/race/{r['s']}/" for r in races if r.get("s")]


def ping(url_list: list[str], dry_run: bool = False) -> list[int | None]:
    """POST url_list to IndexNow in batches of <= MAX_URLS_PER_BATCH.

    Returns the list of response status codes (None for a failed/dry-run batch).
    Never raises — callers (e.g. the deploy script) should be able to treat
    a ping failure as non-fatal.
    """
    codes: list[int | None] = []
    for i in range(0, len(url_list), MAX_URLS_PER_BATCH):
        batch = url_list[i:i + MAX_URLS_PER_BATCH]
        payload = build_payload(batch)
        if dry_run:
            print(f"[dry-run] would POST {len(batch)} URLs to {INDEXNOW_ENDPOINT}")
            codes.append(None)
            continue
        try:
            resp = requests.post(INDEXNOW_ENDPOINT, json=payload, timeout=30)
            print(f"IndexNow: {resp.status_code} for {len(batch)} URLs")
            codes.append(resp.status_code)
        except Exception as e:
            print(f"IndexNow ping failed: {e}")
            codes.append(None)
    return codes


def main() -> int:
    parser = argparse.ArgumentParser(description="Ping IndexNow for updated race URLs")
    parser.add_argument("--urls", nargs="+", help="Explicit URL list to ping (default: all URLs in race-index.json)")
    parser.add_argument("--dry-run", action="store_true", help="Preview the payload without POSTing")
    args = parser.parse_args()

    url_list = args.urls if args.urls else urls_from_index()
    if not url_list:
        print("No URLs to ping")
        return 1

    print(f"Pinging IndexNow for {len(url_list)} URL(s)...")
    ping(url_list, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
