#!/usr/bin/env python3
"""Regression tests for race-page recommendations, citations, and JSON-LD."""

import importlib.util
import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
GENERATOR_PATH = PROJECT_ROOT / "scripts" / "generate_race_pages.py"


def _generator():
    spec = importlib.util.spec_from_file_location("generate_race_pages", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _profiles():
    return [
        json.loads(path.read_text(encoding="utf-8"))["race"]
        for path in sorted(RACE_DATA_DIR.glob("*.json"))
        if path.name != "_schema.json"
    ]


def _jsonld(markup):
    payload = re.search(
        r'<script type="application/ld\+json">(.*?)</script>', markup, re.DOTALL
    ).group(1)
    return json.loads(payload.replace("<\\/", "</"))


def _event(graph):
    return next(node for node in graph["@graph"] if node["@type"] == "SportsEvent")


def test_similar_races_render_six_or_fewer_without_self_reference_and_are_deterministic():
    gen = _generator()
    profiles = _profiles()
    race = next(profile for profile in profiles if profile["slug"] == "vasaloppet")

    first = [profile["slug"] for profile in gen.similar_races(race, profiles)]
    second = [profile["slug"] for profile in gen.similar_races(race, profiles)]
    html = gen.generate_page(race, profiles)
    rendered = re.findall(r'data-similar-race="([^"]+)"', html)

    assert first == second
    assert rendered == first
    assert 1 <= len(rendered) <= 6
    assert race["slug"] not in rendered
    assert all(f'href="/race/{slug}/"' in html for slug in rendered)


def test_similar_races_prioritize_shared_series_and_use_stable_slug_ties():
    gen = _generator()
    race = {
        "slug": "target",
        "series_membership": ["shared-series"],
        "nordic_lab_rating": {"tier": 2},
        "vitals": {"lat": 60, "lng": 20},
    }
    candidates = [
        race,
        {
            "slug": "geo-only",
            "series_membership": [],
            "nordic_lab_rating": {"tier": 2},
            "vitals": {"lat": 60, "lng": 20},
        },
        {
            "slug": "shared-far",
            "series_membership": ["shared-series"],
            "nordic_lab_rating": {"tier": 2},
            "vitals": {"lat": 10, "lng": 10},
        },
        {
            "slug": "shared-zulu",
            "series_membership": ["shared-series"],
            "nordic_lab_rating": {"tier": 2},
            "vitals": {"lat": 61, "lng": 21},
        },
        {
            "slug": "shared-alpha",
            "series_membership": ["shared-series"],
            "nordic_lab_rating": {"tier": 2},
            "vitals": {"lat": 61, "lng": 21},
        },
    ]

    ordered = [entry["slug"] for entry in gen.similar_races(race, candidates)]
    shuffled = [entry["slug"] for entry in gen.similar_races(race, list(reversed(candidates)))]

    assert ordered == shuffled
    assert "target" not in ordered
    assert ordered.index("shared-far") < ordered.index("geo-only")
    assert ordered.index("shared-alpha") < ordered.index("shared-zulu")


def test_section_kickers_are_unique_and_sequential_with_or_without_videos():
    gen = _generator()
    profiles = _profiles()
    with_video = next(profile for profile in profiles if profile.get("youtube_data", {}).get("videos"))
    without_video = next(profile for profile in profiles if not profile.get("youtube_data", {}).get("videos"))

    for profile in (with_video, without_video):
        kickers = [int(value) for value in re.findall(
            r'<span class="gl-section-num">(\d+)</span>',
            gen.generate_page(profile, profiles),
        )]
        assert kickers == list(range(1, len(kickers) + 1))


def test_sources_only_link_to_urls_present_in_the_profile_data():
    gen = _generator()
    race = next(profile for profile in _profiles() if profile["slug"] == "vasaloppet")
    sources = gen.build_sources(race)
    urls = re.findall(r'<a href="([^"]+)"', sources)
    expected = {race["vitals"]["website"]}
    expected.update(video["url"] for video in race["youtube_data"]["videos"] if video.get("url"))

    assert 'id="sources"' in sources
    assert "Official race website" in sources
    assert urls
    assert set(urls) <= expected


def test_sources_omit_the_section_when_the_profile_has_no_citable_urls():
    gen = _generator()
    assert gen.build_sources({"vitals": {}, "youtube_data": {"videos": []}}) == ""


def test_jsonld_has_parseable_start_dates_linked_reviews_and_breadcrumbs():
    gen = _generator()
    profiles = _profiles()
    dated = 0
    for race in profiles:
        graph = _jsonld(gen.build_jsonld(race))
        event = _event(graph)
        expected_date = gen.parse_date_specific(race["vitals"].get("date_specific"))
        reviews = [node for node in graph["@graph"] if node["@type"] == "Review"]
        breadcrumbs = [node for node in graph["@graph"] if node["@type"] == "BreadcrumbList"]

        if expected_date:
            dated += 1
            assert event["startDate"] == expected_date
        else:
            assert "startDate" not in event
        assert len(reviews) == 1
        assert reviews[0]["itemReviewed"] == {"@id": event["@id"]}
        assert len(breadcrumbs) == 1
        assert [item["name"] for item in breadcrumbs[0]["itemListElement"][:2]] == ["Home", "Search"]
    assert dated > 0


def test_race_cookie_banner_links_to_privacy_policy():
    gen = _generator()
    assert 'href="/privacy/"' in gen.build_cookie_consent()
