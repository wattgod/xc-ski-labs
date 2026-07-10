#!/usr/bin/env python3
"""Create Stripe Payment Links for XC Ski Labs prices.

Reads data/stripe-products.json and writes data/stripe-payment-links.json as:
  {price_id: {"url": "...", "nickname": "..."}}

The script is idempotent: existing price IDs in the output file are skipped.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
PRODUCTS_FILE = DATA_DIR / "stripe-products.json"
LINKS_FILE = DATA_DIR / "stripe-payment-links.json"
ENV_FILE = PROJECT_ROOT / ".env"
SUCCESS_URL = "https://xcskilabs.com/thanks/"


def load_dotenv() -> None:
    """Small .env loader so the script does not require python-dotenv."""
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def stripe_key() -> str:
    load_dotenv()
    key = os.environ.get("STRIPE_SECRET_KEY") or os.environ.get("XC_STRIPE_SECRET_KEY")
    if not key:
        raise SystemExit("Missing STRIPE_SECRET_KEY or XC_STRIPE_SECRET_KEY in environment/.env")
    return key


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def create_with_stripe_lib(price_id: str, nickname: str) -> str | None:
    try:
        import stripe  # type: ignore
    except Exception:
        return None

    stripe.api_key = stripe_key()
    link = stripe.PaymentLink.create(
        line_items=[{"price": price_id, "quantity": 1}],
        after_completion={
            "type": "redirect",
            "redirect": {"url": SUCCESS_URL},
        },
        metadata={
            "source": "xcskilabs",
            "price_id": price_id,
            "nickname": nickname,
        },
    )
    return str(link["url"])


def create_with_rest(price_id: str, nickname: str) -> str:
    payload = urllib.parse.urlencode(
        {
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "after_completion[type]": "redirect",
            "after_completion[redirect][url]": SUCCESS_URL,
            "metadata[source]": "xcskilabs",
            "metadata[price_id]": price_id,
            "metadata[nickname]": nickname,
        }
    ).encode("utf-8")
    token = base64.b64encode((stripe_key() + ":").encode("utf-8")).decode("ascii")
    req = urllib.request.Request(
        "https://api.stripe.com/v1/payment_links",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return str(data["url"])


def create_payment_link(price_id: str, nickname: str) -> str:
    url = create_with_stripe_lib(price_id, nickname)
    if url:
        return url
    return create_with_rest(price_id, nickname)


def main() -> None:
    products = load_json(PRODUCTS_FILE, {})
    existing: dict[str, dict[str, str]] = load_json(LINKS_FILE, {})
    created = 0
    skipped = 0

    for price in products.get("prices", []):
        price_id = str(price.get("id", "")).strip()
        nickname = str(price.get("nickname", "")).strip()
        if not price_id:
            continue
        if price_id in existing and existing[price_id].get("url"):
            skipped += 1
            print(f"skip {price_id} {nickname}")
            continue
        url = create_payment_link(price_id, nickname)
        existing[price_id] = {"url": url, "nickname": nickname}
        LINKS_FILE.write_text(json.dumps(existing, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        created += 1
        print(f"created {price_id} {nickname}")

    print(f"done: {created} created, {skipped} skipped, {len(existing)} recorded")


if __name__ == "__main__":
    main()
