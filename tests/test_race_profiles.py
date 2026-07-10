#!/usr/bin/env python3
"""
XC Ski Labs — Race Profile Validation Tests

These tests run against EVERY race JSON profile in race-data/.
They catch: score math errors, missing fields, schema violations,
tier mismatches, slug inconsistencies, and data integrity issues.

Run: pytest tests/test_race_profiles.py -v
"""

import json
import re
from pathlib import Path

import pytest

RACE_DATA_DIR = Path(__file__).resolve().parent.parent / "race-data"
SCHEMA_FILE = RACE_DATA_DIR / "_schema.json"

VALID_DISCIPLINES = {"classic", "skate", "both"}
VALID_TIERS = {1, 2, 3, 4}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

REQUIRED_CRITERIA = [
    "distance", "elevation", "altitude", "field_size", "prestige",
    "international_draw", "course_technicality", "snow_reliability",
    "grooming_quality", "accessibility", "community", "scenery",
    "organization", "competitive_depth",
]
CRITERIA_COUNT = 14
SCORE_DENOMINATOR = 70

REQUIRED_VITALS = ["country", "distance_km", "discipline"]
REQUIRED_ROOT = ["name", "slug", "display_name", "tagline"]
REQUIRED_RATING = ["overall_score", "tier"]


# ── Fixtures ──────────────────────────────────────────────────


def _load_all_profiles():
    """Load all race JSON profiles, yielding (filename, data) tuples."""
    profiles = []
    for f in sorted(RACE_DATA_DIR.glob("*.json")):
        if f.name == "_schema.json":
            continue
        with open(f) as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as e:
                pytest.fail(f"{f.name}: Invalid JSON — {e}")
            profiles.append((f.name, data))
    return profiles


ALL_PROFILES = _load_all_profiles()
PROFILE_IDS = [p[0] for p in ALL_PROFILES]


@pytest.fixture(params=ALL_PROFILES, ids=PROFILE_IDS)
def profile(request):
    """Yield (filename, data) for each race profile."""
    return request.param


@pytest.fixture
def race(profile):
    """Yield the race dict from a profile."""
    filename, data = profile
    assert "race" in data, f"{filename}: Missing top-level 'race' key"
    return filename, data["race"]


# ── Structure Tests ───────────────────────────────────────────


class TestProfileStructure:
    """Validate JSON structure and required fields."""

    def test_has_race_key(self, profile):
        filename, data = profile
        assert "race" in data, f"{filename}: Missing 'race' key"

    def test_required_root_fields(self, race):
        filename, r = race
        for field in REQUIRED_ROOT:
            val = r.get(field)
            assert val is not None and val != "", \
                f"{filename}: Missing or empty required field '{field}'"

    def test_has_vitals(self, race):
        filename, r = race
        assert "vitals" in r, f"{filename}: Missing 'vitals'"

    def test_required_vitals_fields(self, race):
        filename, r = race
        vitals = r.get("vitals", {})
        for field in REQUIRED_VITALS:
            val = vitals.get(field)
            assert val is not None and val != "", \
                f"{filename}: Missing or empty vitals.{field}"

    def test_has_nordic_lab_rating(self, race):
        filename, r = race
        assert "nordic_lab_rating" in r, f"{filename}: Missing 'nordic_lab_rating'"

    def test_required_rating_fields(self, race):
        filename, r = race
        rating = r.get("nordic_lab_rating", {})
        for field in REQUIRED_RATING:
            val = rating.get(field)
            assert val is not None, \
                f"{filename}: Missing nordic_lab_rating.{field}"

    def test_has_youtube_data(self, race):
        filename, r = race
        yt = r.get("youtube_data")
        assert yt is not None, f"{filename}: Missing 'youtube_data'"
        assert "videos" in yt, f"{filename}: youtube_data missing 'videos' key"

    def test_youtube_data_videos_is_list(self, race):
        filename, r = race
        yt = r.get("youtube_data", {})
        videos = yt.get("videos")
        assert isinstance(videos, list), \
            f"{filename}: youtube_data.videos should be a list, got {type(videos)}"


# ── Slug Tests ────────────────────────────────────────────────


class TestSlugs:
    """Validate slug format and consistency."""

    def test_slug_matches_filename(self, race):
        filename, r = race
        expected_slug = filename.replace(".json", "")
        assert r.get("slug") == expected_slug, \
            f"{filename}: slug '{r.get('slug')}' doesn't match filename"

    def test_slug_format(self, race):
        filename, r = race
        slug = r.get("slug", "")
        assert SLUG_RE.match(slug), \
            f"{filename}: Invalid slug format '{slug}' — must be lowercase-hyphenated"

    def test_no_duplicate_slugs(self):
        slugs = [d["race"]["slug"] for _, d in ALL_PROFILES if "race" in d]
        dupes = [s for s in slugs if slugs.count(s) > 1]
        assert not dupes, f"Duplicate slugs: {set(dupes)}"

    def test_no_duplicate_display_names(self):
        names = [d["race"].get("display_name", "") for _, d in ALL_PROFILES if "race" in d]
        names = [n for n in names if n]
        dupes = [n for n in names if names.count(n) > 1]
        assert not dupes, f"Duplicate display names: {set(dupes)}"


# ── Scoring Tests ─────────────────────────────────────────────


class TestScoring:
    """Validate scoring math, tier assignments, and criteria bounds."""

    def test_all_14_criteria_present(self, race):
        filename, r = race
        rating = r.get("nordic_lab_rating", {})
        missing = [c for c in REQUIRED_CRITERIA if c not in rating]
        assert not missing, \
            f"{filename}: Missing criteria: {missing}"

    def test_criteria_in_range(self, race):
        filename, r = race
        rating = r.get("nordic_lab_rating", {})
        for criterion in REQUIRED_CRITERIA:
            val = rating.get(criterion)
            if val is None:
                continue  # Caught by test_all_14_criteria_present
            assert isinstance(val, (int, float)), \
                f"{filename}: {criterion} should be numeric, got {type(val).__name__}"
            assert 1 <= val <= 5, \
                f"{filename}: {criterion}={val} out of range [1,5]"

    def test_score_math(self, race):
        """Verify overall_score = round((sum_of_14_criteria / 70) * 100)."""
        filename, r = race
        rating = r.get("nordic_lab_rating", {})
        criteria_sum = sum(
            rating.get(c, 0) for c in REQUIRED_CRITERIA
        )
        expected = round((criteria_sum / SCORE_DENOMINATOR) * 100)
        actual = rating.get("overall_score")
        assert actual == expected, \
            f"{filename}: Score mismatch — criteria sum={criteria_sum}, " \
            f"expected score={expected}, actual={actual}"

    def test_tier_matches_score(self, race):
        """Verify tier assignment matches score thresholds."""
        filename, r = race
        rating = r.get("nordic_lab_rating", {})
        score = rating.get("overall_score", 0)
        tier = rating.get("tier")
        prestige = rating.get("prestige", 0)

        # Calculate expected tier (before prestige overrides)
        if score >= 80:
            base_tier = 1
        elif score >= 60:
            base_tier = 2
        elif score >= 45:
            base_tier = 3
        else:
            base_tier = 4

        # Prestige overrides
        expected_tier = base_tier
        if prestige == 5 and score >= 75:
            expected_tier = 1
        elif prestige == 5 and score < 75:
            expected_tier = min(base_tier, 2)
        elif prestige == 4:
            expected_tier = max(base_tier - 1, 2)  # promote 1 tier, not into T1

        assert tier == expected_tier, \
            f"{filename}: Tier mismatch — score={score}, prestige={prestige}, " \
            f"expected tier={expected_tier}, actual={tier}"

    def test_tier_is_valid(self, race):
        filename, r = race
        tier = r.get("nordic_lab_rating", {}).get("tier")
        assert tier in VALID_TIERS, \
            f"{filename}: Invalid tier {tier}"


# ── Discipline Tests ──────────────────────────────────────────


class TestDiscipline:
    """Validate discipline field values."""

    def test_valid_discipline(self, race):
        filename, r = race
        disc = r.get("vitals", {}).get("discipline")
        assert disc in VALID_DISCIPLINES, \
            f"{filename}: Invalid discipline '{disc}'"


# ── Data Quality Tests ────────────────────────────────────────


class TestDataQuality:
    """Catch subtle data quality issues."""

    def test_tagline_not_generic(self, race):
        """Taglines should be specific, not placeholder text."""
        filename, r = race
        tagline = r.get("tagline", "")
        # Only flag taglines that ARE the generic phrase, not ones containing it
        # "America's largest cross-country ski race" is specific
        # "A cross-country ski race" is generic
        generic_exact = [
            "a great race",
            "a ski race",
            "a cross-country ski race",
            "cross-country ski race",
            "tbd",
            "todo",
            "placeholder",
        ]
        normalized = tagline.strip().lower().rstrip(".")
        assert normalized not in generic_exact, \
            f"{filename}: Generic tagline: '{tagline}'"
        assert len(tagline) >= 20, \
            f"{filename}: Tagline too short ({len(tagline)} chars): '{tagline}'"

    def test_country_not_empty(self, race):
        filename, r = race
        country = r.get("vitals", {}).get("country", "")
        assert country and len(country) >= 2, \
            f"{filename}: Missing or invalid country"

    def test_distance_is_positive(self, race):
        filename, r = race
        dist = r.get("vitals", {}).get("distance_km")
        if dist is not None:
            assert isinstance(dist, (int, float)), \
                f"{filename}: distance_km should be numeric"
            assert dist > 0, \
                f"{filename}: distance_km={dist} must be positive"

    def test_display_name_not_empty(self, race):
        filename, r = race
        dn = r.get("display_name", "")
        assert dn and len(dn) >= 3, \
            f"{filename}: display_name too short or empty: '{dn}'"

    def test_founded_year_reasonable(self, race):
        """If founded year exists, it should be between 1800 and 2027."""
        filename, r = race
        hist = r.get("history", {})
        founded = hist.get("founded")
        if founded is not None:
            assert isinstance(founded, int), \
                f"{filename}: founded should be int, got {type(founded).__name__}"
            assert 1800 <= founded <= 2027, \
                f"{filename}: Unreasonable founded year: {founded}"

    def test_elevation_not_negative(self, race):
        filename, r = race
        elev = r.get("vitals", {}).get("elevation_gain_m")
        if elev is not None:
            assert elev >= 0, \
                f"{filename}: Negative elevation gain: {elev}"

    def test_field_size_estimate_reasonable(self, race):
        """If field_size_estimate exists, should be 1-100000."""
        filename, r = race
        fs = r.get("vitals", {}).get("field_size_estimate")
        if fs is not None:
            assert 1 <= fs <= 100000, \
                f"{filename}: Unreasonable field_size_estimate: {fs}"


# ── Cross-Profile Tests ──────────────────────────────────────


class TestCrossProfile:
    """Tests that span multiple profiles."""

    def test_minimum_profile_count(self):
        """Database should have a meaningful number of races."""
        assert len(ALL_PROFILES) >= 100, \
            f"Only {len(ALL_PROFILES)} profiles — expected 100+"

    def test_all_tiers_represented(self):
        """Every tier should have at least one race."""
        tiers = set()
        for _, data in ALL_PROFILES:
            race = data.get("race", {})
            tier = race.get("nordic_lab_rating", {}).get("tier")
            if tier:
                tiers.add(tier)
        for t in [1, 2, 3, 4]:
            assert t in tiers, f"No races in Tier {t}"

    def test_multiple_countries(self):
        """Database should cover multiple countries."""
        countries = set()
        for _, data in ALL_PROFILES:
            country = data.get("race", {}).get("vitals", {}).get("country")
            if country:
                countries.add(country)
        assert len(countries) >= 10, \
            f"Only {len(countries)} countries — expected 10+"

    def test_all_disciplines_represented(self):
        """All three disciplines should have races."""
        discs = set()
        for _, data in ALL_PROFILES:
            disc = data.get("race", {}).get("vitals", {}).get("discipline")
            if disc:
                discs.add(disc)
        for d in VALID_DISCIPLINES:
            assert d in discs, f"No races with discipline '{d}'"

    def test_score_distribution_not_degenerate(self):
        """Scores shouldn't all cluster at one value."""
        scores = []
        for _, data in ALL_PROFILES:
            score = data.get("race", {}).get("nordic_lab_rating", {}).get("overall_score")
            if score is not None:
                scores.append(score)
        assert len(set(scores)) >= 20, \
            f"Only {len(set(scores))} distinct scores — scoring may be degenerate"
        assert min(scores) < 50, "No low scores — tier calibration suspect"
        assert max(scores) >= 80, "No high scores — tier calibration suspect"
