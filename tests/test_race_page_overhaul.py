"""Regression coverage for the spine-first race-page overhaul."""

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "generate_race_pages.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("race_page_overhaul_generator", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _vasaloppet():
    return json.loads((ROOT / "race-data" / "vasaloppet.json").read_text(encoding="utf-8"))["race"]


def test_spine_first_page_order_and_custom_first_offer():
    page = _load_generator().generate_page(_vasaloppet())

    ordered_markers = [
        'id="hero"',
        'id="rating"',
        'id="breakdown"',
        'class="gl-transition"',
        'id="training"',
        'id="deep-dive"',
    ]
    positions = [page.index(marker) for marker in ordered_markers]
    assert positions == sorted(positions)
    assert page.index("Custom plan") < page.index("1:1 coaching")
    assert "Training plans" not in page
    assert "VIDEO ENRICHMENT COMING SOON" not in page


def test_rating_is_server_rendered_two_radar_and_click_explain():
    page = _load_generator().generate_page(_vasaloppet())

    assert page.count('class="gl-radar-polygon"') == 2
    assert 'id="gl-rating-panel-course"' in page
    assert 'id="gl-rating-panel-experience"' in page
    assert page.count('class="gl-rating-tile"') == 14
    assert 'role="tablist"' in page
    assert 'role="status" aria-live="polite"' in page
    assert "rating_criterion_click" in page
    assert ".gl-rating-panel[hidden] { display: none; }" in page


def test_rating_uses_nordic_schema_and_profile_evidence():
    page = _load_generator().generate_page(_vasaloppet())

    assert "Course &amp; conditions" in page
    assert "Race experience" in page
    assert "The primary distance is 90 km." in page
    assert "The listed field size is 16000 skiers." in page
    assert "gravel_god_rating" not in page
    assert "fondo_rating" not in page


def test_new_dynamic_copy_is_escaped():
    generator = _load_generator()
    race = _vasaloppet()
    race["display_name"] = '</h2><script>alert("x")</script>'
    race["course"]["grooming"] = '</span><script>alert("g")</script>'

    page = generator.generate_page(race)

    assert '</h2><script>alert("x")</script>' not in page
    assert '</span><script>alert("g")</script>' not in page
    assert "&lt;script&gt;alert" in page


def test_interactions_do_not_write_dynamic_html():
    source = GENERATOR_PATH.read_text(encoding="utf-8")
    assert ".innerHTML" not in source
    assert "onclick=" not in source
