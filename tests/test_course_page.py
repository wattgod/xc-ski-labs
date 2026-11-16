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


def test_page_states_price_and_refund_and_leaves_the_seller_to_the_terms():
    page = gc.generate_html()
    assert "Buy Classic, $29" in page and "Buy Skate, $29" in page and "Buy every module, $49" in page
    assert "within 14 days" in page
    assert "Gravel God" not in page  # the terms page names the seller (Matti, 2026-11-16)
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


def test_page_is_built_from_the_sledge_components():
    page = gc.generate_html()
    body = page.split("<main", 1)[1]
    # One splash crate, the bundle, first in the source and labelled Recommended.
    assert body.count("xc-crate--splash") == 1
    crates = re.findall(r'<li class="xc-crate[^"]*" id="([^"]+)"', body)
    assert crates == ["xc-all", "xc-classic", "xc-skate"]
    assert '<span class="xc-ribbon">Recommended</span>' in body
    assert body.count('class="xc-tag"') == 3
    assert 'class="xc-lists"' in body and body.count('class="xc-ship"') == 3
    # Sales checklists: every row planned, nothing salmon.
    assert "is-now" not in body and "is-done" not in body
    # Placeholders never ship; colours come from tokens only.
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    assert "[" not in re.sub(r"<[^>]+>", " ", text)
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", gc.PAGE_CSS)
    assert "gl-course-" not in body and "gl-course-" not in gc.PAGE_CSS


def test_hero_is_my_side_on_v2_clip_shipped_with_the_page(tmp_path):
    out = gc.generate_page(tmp_path)
    assert (out.parent / gc.HERO_VIDEO).stat().st_size > 1_000_000
    assert (out.parent / gc.HERO_POSTER).stat().st_size > 30_000
    page = out.read_text()
    assert f'src="{gc.HERO_VIDEO}"' in page and f'poster="{gc.HERO_POSTER}"' in page
    assert " autoplay" not in page  # started by script, so reduced-motion visitors keep the poster


def test_site_nav_links_the_course():
    from scripts.generate_race_pages import build_nav_header
    assert '<a href="/course/">Course</a>' in build_nav_header()
    assert '<a href="/course/" class="active">Course</a>' in gc.generate_html()



def test_book_decoration_survives_the_template_reset():
    css = gc.PAGE_CSS
    assert "var(--stroke-underline)) 0 var(--splash) !important" in css
    assert ".xc-tag::before { border-radius: 50% !important" in css
    assert ".xc-ship::before { border-radius: 50% !important" in css


def test_every_tag_counts_what_it_counts():
    for p in gc.PRODUCTS:
        assert re.match(r"\d+ lessons, \d+ clips", gc.stat_line(p))
