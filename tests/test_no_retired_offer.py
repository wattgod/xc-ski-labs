"""No generated page quotes the retired plan offer (sweep finding XC-05).

The custom ski plan is sold at wordpress/plan_offer.py's price. Home, race
pages, the guide and /goals/ used to quote "$60-$249" and "FROM $60" for
plans that no longer exist; plan_offer.STALE_OFFER_PATTERNS lists the
retired phrases.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "wordpress"))
import plan_offer  # noqa: E402

OUTPUT = PROJECT_ROOT / "output"
PAGES = sorted(OUTPUT.rglob("index.html")) if OUTPUT.exists() else []


@pytest.mark.skipif(not PAGES, reason="output/ not generated")
def test_no_page_quotes_a_retired_offer():
    hits = {}
    for page in PAGES:
        found = plan_offer.stale_offer_phrases(page.read_text(encoding="utf-8"))
        if found:
            hits[page.relative_to(OUTPUT).as_posix()] = found
    assert not hits, f"{len(hits)} pages quote a retired offer, e.g. {list(hits.items())[:5]}"


@pytest.mark.skipif(not PAGES, reason="output/ not generated")
# The guide is not an offer surface: its one upsell is the course (Matti, 2026-11-15).
@pytest.mark.parametrize("rel", ["index.html", "vasaloppet/index.html", "goals/index.html"])
def test_offer_surfaces_show_the_current_price(rel):
    text = plan_offer.visible_text((OUTPUT / rel).read_text(encoding="utf-8"))
    assert plan_offer.BLOCK_PRICE in text
    assert "FROM $60" not in text.upper()


@pytest.mark.parametrize("rel", ["scripts/generate_race_pages.py", "scripts/generate_homepage.py",
                                 "wordpress/generate_goals.py"])
def test_offer_copy_is_first_person(rel):
    src = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
    for phrase in ("A coach reads your training", "coach-built", "Built from the intake",
                   "built from the intake"):
        assert phrase not in src, f"{rel}: {phrase}"
