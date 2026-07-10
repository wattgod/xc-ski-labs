#!/usr/bin/env python3
"""X13/X14 race page art plates and interactive block tests."""

import importlib.util
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def _generator():
    path = SCRIPTS_DIR / "generate_race_pages.py"
    spec = importlib.util.spec_from_file_location("generate_race_pages", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _race(**overrides):
    race = {
        "name": "Fixture Race",
        "slug": "fixture-race",
        "display_name": "Fixture Race",
        "tagline": "A fixture race.",
        "vitals": {
            "country": "Norway",
            "distance_km": 42,
            "elevation_m": 850,
            "altitude_m": 900,
            "location": "Startbyen to Finishvik",
            "date": "March",
            "discipline": "classic",
            "founded": 1978,
        },
        "climate": {"typical_temp_c": "-10 to -2", "description": "Variable."},
        "course": {"primary": "Rolling course.", "format": "point-to-point"},
        "history": {"founded": 1968, "summary": "Founded in 1968."},
        "nordic_lab_rating": {
            "overall_score": 62,
            "tier": 2,
            "discipline": "classic",
        },
    }
    gen = _generator()
    race["nordic_lab_rating"].update({key: 3 for key, _ in gen.RATING_CRITERIA})
    for key, value in overrides.items():
        race[key] = value
    return race


def test_gpx_parser_reads_fixture_profile():
    gen = _generator()
    profile = gen.parse_gpx_profile(FIXTURES_DIR / "sample-course.gpx")
    assert profile["distance_km"] > 0
    assert len(profile["points"]) == 5
    assert profile["start_elevation_m"] == 1000
    assert profile["high_point_m"] == 1125
    assert profile["finish_elevation_m"] == 1015


def test_art_tier_selection_uses_gpx_presence(tmp_path):
    gen = _generator()
    art_dir = tmp_path / "art"
    gpx_dir = art_dir / "gpx"
    gpx_dir.mkdir(parents=True)
    assert gen.select_art_plate_tier("fixture-race", art_dir) == "B"
    (gpx_dir / "fixture-race.gpx").write_text((FIXTURES_DIR / "sample-course.gpx").read_text(), encoding="utf-8")
    assert gen.select_art_plate_tier("fixture-race", art_dir) == "A"


def test_manifest_writing_records_course_plate_license(tmp_path):
    gen = _generator()
    art_dir = tmp_path / "art"
    gpx_dir = art_dir / "gpx"
    gpx_dir.mkdir(parents=True)
    (gpx_dir / "fixture-race.gpx").write_text((FIXTURES_DIR / "sample-course.gpx").read_text(), encoding="utf-8")
    (gpx_dir / "fixture-race.license").write_text("Test GPX license", encoding="utf-8")
    _, record = gen.build_hero_plate(_race(), art_dir)
    gen.write_art_manifest({"fixture-race": record}, art_dir)
    manifest = json.loads((art_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["fixture-race"] == {
        "tier": "A",
        "source": "art/gpx/fixture-race.gpx",
        "license": "Test GPX license",
    }


def test_missing_gpx_license_is_marked_unverified(tmp_path):
    gen = _generator()
    art_dir = tmp_path / "art"
    gpx_dir = art_dir / "gpx"
    gpx_dir.mkdir(parents=True)
    (gpx_dir / "fixture-race.gpx").write_text((FIXTURES_DIR / "sample-course.gpx").read_text(), encoding="utf-8")
    _, record = gen.build_hero_plate(_race(), art_dir)
    assert record["license"].startswith("UNVERIFIED")


def test_wax_card_band_selection_from_temperature_range():
    gen = _generator()
    bands = gen.select_wax_card_bands((-10, -2))
    assert [band["key"] for band in bands] == ["blue", "violet", "red"]


def test_quiz_fact_correct_answer_matches_profile_history():
    gen = _generator()
    fact = gen.build_quiz_fact(_race())
    assert fact["correct"] == 1968
    assert 1968 in fact["options"]


def test_generators_have_no_inline_onclick_handlers():
    scripts = [
        SCRIPTS_DIR / "generate_race_pages.py",
        SCRIPTS_DIR / "generate_homepage.py",
        PROJECT_ROOT / "wordpress" / "generate_about.py",
        PROJECT_ROOT / "wordpress" / "generate_questionnaire.py",
        PROJECT_ROOT / "wordpress" / "generate_training_plans.py",
    ]
    for script in scripts:
        source = script.read_text(encoding="utf-8")
        assert "onclick=" not in source


def test_interactive_blocks_omitted_when_required_data_missing():
    gen = _generator()
    race = _race(climate={}, history={}, vitals={"country": "Norway", "discipline": "classic"})
    assert gen.build_wax_call_cards(race) == ""
    assert gen.build_knowledge_check(race) == ""
    assert gen.build_interactive_blocks(race) == ""
