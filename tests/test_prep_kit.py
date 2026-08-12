"""Prep-kit generator, race-page gate, and sitemap parity tests."""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RACE_DATA_DIR = PROJECT_ROOT / "race-data"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


prep_kit = _load_module("generate_prep_kit", SCRIPTS_DIR / "generate_prep_kit.py")
race_pages = _load_module("generate_race_pages_prepkit", SCRIPTS_DIR / "generate_race_pages.py")
sitemap = _load_module("generate_sitemap_prepkit", SCRIPTS_DIR / "generate_sitemap.py")


@pytest.mark.parametrize(
    "slug",
    ["american-birkebeiner", "crescent-lake-challenge", "attraverso-campra"],
)
def test_prep_kit_renders_representative_profiles(slug, tmp_path):
    """Birkie and two thin profiles should each render a useful kit."""
    race = prep_kit.load_race(RACE_DATA_DIR / f"{slug}.json")
    assert race is not None
    target = prep_kit.generate_race(race, tmp_path)
    html = target.read_text(encoding="utf-8")

    assert target == tmp_path / slug / "prep-kit" / "index.html"
    assert html.startswith("<!DOCTYPE html>")
    assert "Race logistics" in html
    assert "Pacing and fueling" in html
    assert "Gear and wax day" in html
    assert f'href="/race/{slug}/"' in html
    assert "race-specific wax prescription" in html
    assert "weeks out" not in html.lower()
    assert "race is past" not in html.lower()


def test_prep_kit_cli_generates_birkie(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "generate_prep_kit.py"),
            "--slug",
            "american-birkebeiner",
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "american-birkebeiner" / "prep-kit" / "index.html").exists()


def test_2027_race_date_is_rendered_without_past_framing():
    race = prep_kit.load_race(RACE_DATA_DIR / "kananaskis-ski-marathon.json")
    assert race is not None
    html = prep_kit.build_page(race)
    assert "2027: January 30" in html
    assert "past" not in html.lower()


def test_race_page_contains_prep_kit_gate():
    data = json.loads((RACE_DATA_DIR / "american-birkebeiner.json").read_text())
    html = race_pages.generate_page(data["race"], [data["race"]])

    assert "Leave your email &mdash; the American Birkebeiner prep kit is yours." in html
    assert "GET PREP KIT" in html
    assert "prep_kit_gate" in html
    assert "brand: 'xcskilabs'" in html
    assert "window.location.assign(kitUrl)" in html
    assert 'name="website"' in html


def test_worker_payload_field_names_match_gravel_gate_plus_brand():
    """Keep Gravel's five gate fields byte-identical and add only brand."""
    source = race_pages.build_capture_js()
    match = re.search(r"body: JSON\.stringify\(\{(.*?)\}\)", source, re.DOTALL)
    assert match, "prep-kit worker payload not found"
    fields = re.findall(r"^\s*([a-z_]+):", match.group(1), re.MULTILINE)

    gravel_gate_fields = ["email", "race_slug", "race_name", "source", "website"]
    assert [field for field in fields if field != "brand"] == gravel_gate_fields
    assert fields == ["email", "race_slug", "race_name", "source", "brand", "website"]


def test_sitemap_includes_one_prep_kit_per_race():
    profiles = [
        {"slug": "alpha", "tier": 1, "overall_score": 90},
        {"slug": "beta", "tier": 4, "overall_score": 35},
    ]
    xml, _ = sitemap.generate_sitemap("https://xcskilabs.com", profiles)
    text = xml.decode("utf-8")
    assert text.count("/prep-kit/") == len(profiles)
    assert "https://xcskilabs.com/race/alpha/prep-kit/" in text
