"""Guards for the /course/ sales page (wordpress/generate_course.py)."""

import json
import os
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "wordpress"))

import generate_course as gc  # noqa: E402
import generate_terms  # noqa: E402

COURSE_JSON = Path(os.environ.get(
    "XC_COURSE_JSON",
    Path.home() / "glide-labs-platform" / "course" / "content" / "xc-ski-technique.json"))


def test_page_states_price_refund_and_seller():
    page = gc.generate_html()
    assert "Buy Classic, $29" in page and "Buy Skate, $29" in page and "Buy every module, $49" in page
    assert "within 14 days" in page
    assert "Gravel God Cycling LLC" in page
    assert 'href="/terms/"' in page and 'href="/privacy/"' in page


def test_checkout_goes_to_the_course_endpoint_only():
    page = gc.generate_html("http://localhost:5050/")
    assert "http://localhost:5050/api/create-course-checkout" in page
    for pid in ("xc-classic", "xc-skate", "xc-all"):
        assert f'value="{pid}"' in page
    assert "course_id:btn.value" in page
    assert "railway.app" not in page


def test_athlete_facing_copy_is_first_person():
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", gc.generate_html(), flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    for banned in (r"\bMatt\b", r"\bMatti\b", r"\bcoach\b", r"\bAI\b", r"Claude", r"GPT", r"Codex",
                   "—", "–", "&mdash;", "&ndash;"):
        assert not re.search(banned, text), banned


def test_terms_name_the_llc_and_course_refund():
    terms = generate_terms.generate_html()
    assert "operated by Gravel God Cycling LLC" in terms
    assert "within 14 days of that purchase" in terms and "added to the course after you buy it" in terms


@pytest.mark.skipif(not COURSE_JSON.exists(), reason="glide-labs-platform course JSON not checked out")
def test_lesson_list_matches_the_course():
    course = json.loads(COURSE_JSON.read_text())["course"]
    titles = [l["title"] for m in course["modules"] for l in m["lessons"]]
    by_access = {}
    for m in course["modules"]:
        by_access.setdefault(m["access"], []).extend(l["title"] for l in m["lessons"])
    assert sorted(by_access["basics"]) == sorted(gc.BASICS)
    prods = {p["id"]: p for p in gc.PRODUCTS}
    assert list(prods["xc-classic"]["lessons"]) == by_access["classic"]
    assert list(prods["xc-skate"]["lessons"]) == by_access["skate"]
    assert gc.LESSON_COUNT == len(titles)
    for pid, access in (("xc-classic", "classic"), ("xc-skate", "skate")):
        clips = {b["media"] for m in course["modules"] if m["access"] == access
                 for l in m["lessons"] for b in l["blocks"] if b.get("type") == "video"}
        assert prods[pid]["clips"] == len(clips)
    videos = {b["media"] for m in course["modules"] for l in m["lessons"]
              for b in l["blocks"] if b.get("type") == "video"}
    assert len(videos) == gc.VIDEO_COUNT
    quizzed = sum(1 for m in course["modules"] for l in m["lessons"]
                  if any(b.get("type") == "quiz" for b in l["blocks"]))
    assert quizzed == 12
