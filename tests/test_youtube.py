#!/usr/bin/env python3
"""
test_youtube.py — Tests for the YouTube enrichment pipeline.

Tests cover:
  - Search query building (classic/skate/both techniques)
  - Wrong-sport filtering (alpine, biathlon, ski jumping)
  - Duration parsing (MM:SS, H:MM:SS, edge cases)
  - Video ID coercion to string
  - Enrichment validation
  - Skier intel validation
  - Thumbnail URL format validation
"""

import sys
from pathlib import Path

import pytest

# Add scripts dir to path for imports
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from youtube_research import build_search_query, build_alt_queries, is_wrong_sport, WRONG_SPORT_TERMS
from youtube_enrich import (
    _parse_duration_seconds,
    validate_enrichment,
    extract_video_id,
    parse_json_response,
    VIDEO_ID_RE,
    QUOTE_CATEGORIES,
)
from youtube_validate import (
    validate_skier_intel,
    THUMBNAIL_URL_RE,
    WRONG_SPORT_RE,
    VIDEO_ID_RE as VALIDATE_VIDEO_ID_RE,
    DATE_RE,
    HTML_RE,
)


# ── Search Query Building ──────────────────────────────────────────────

class TestBuildSearchQuery:
    """Test technique-aware search query construction."""

    def _make_race(self, name: str, location: str = "", technique: str = "both") -> dict:
        return {
            "race": {
                "name": name,
                "display_name": name,
                "vitals": {"location": location},
                "nordic_rating": {"technique": technique},
            }
        }

    def test_classic_technique(self):
        race = self._make_race("Vasaloppet", "Mora, Sweden", "classic")
        query = build_search_query(race)
        assert "classic technique" in query
        assert "Vasaloppet" in query
        assert "Mora" in query

    def test_skate_technique(self):
        race = self._make_race("American Birkebeiner", "Hayward, Wisconsin", "skate")
        query = build_search_query(race)
        assert "skate technique" in query
        assert "American Birkebeiner" in query

    def test_both_techniques(self):
        race = self._make_race("Engadin Skimarathon", "St. Moritz, Switzerland", "both")
        query = build_search_query(race)
        assert "cross country ski race" in query
        assert "classic" not in query.lower().replace("cross country", "")
        assert "skate" not in query.lower()

    def test_default_technique(self):
        """Missing technique defaults to 'both' (generic XC ski race)."""
        race = {"race": {"name": "Some Race", "vitals": {}, "nordic_rating": {}}}
        query = build_search_query(race)
        assert "cross country ski race" in query

    def test_location_only_first_part(self):
        """Location uses only city/region before comma."""
        race = self._make_race("Test Race", "Lillehammer, Norway")
        query = build_search_query(race)
        assert "Lillehammer" in query
        assert "Norway" not in query

    def test_no_location(self):
        race = self._make_race("Marcialonga", "")
        query = build_search_query(race)
        assert "Marcialonga" in query
        assert "cross country ski race" in query


class TestBuildAltQueries:
    """Test alternative query generation."""

    def test_loppet_and_marathon_variants(self):
        race = {"race": {"name": "Vasaloppet", "display_name": "Vasaloppet"}}
        alts = build_alt_queries(race)
        assert any("loppet" in q for q in alts)
        assert any("ski marathon" in q for q in alts)

    def test_uses_race_name(self):
        race = {"race": {"name": "Birkebeinerrennet", "display_name": "Birkebeinerrennet"}}
        alts = build_alt_queries(race)
        assert all("Birkebeinerrennet" in q for q in alts)


# ── Wrong-Sport Filtering ──────────────────────────────────────────────

class TestWrongSportFiltering:
    """Test rejection of alpine, biathlon, ski jumping content."""

    def test_alpine_skiing_rejected(self):
        video = {"title": "Alpine Skiing World Cup Highlights", "description": "", "tags": []}
        assert is_wrong_sport(video) is True

    def test_downhill_skiing_rejected(self):
        video = {"title": "Best Downhill Skiing Runs 2025", "description": "", "tags": []}
        assert is_wrong_sport(video) is True

    def test_ski_jumping_rejected(self):
        video = {"title": "Ski Jumping World Championship", "description": "", "tags": []}
        assert is_wrong_sport(video) is True

    def test_biathlon_rejected(self):
        video = {"title": "Biathlon Sprint Race", "description": "", "tags": []}
        assert is_wrong_sport(video) is True

    def test_slalom_rejected(self):
        video = {"title": "Slalom Race in Kitzbuhel", "description": "", "tags": []}
        assert is_wrong_sport(video) is True

    def test_xc_skiing_accepted(self):
        video = {"title": "Vasaloppet 2025 Full Race Recap", "description": "Cross country skiing", "tags": []}
        assert is_wrong_sport(video) is False

    def test_wrong_sport_in_description(self):
        video = {"title": "Winter Race", "description": "This alpine skiing event was amazing", "tags": []}
        assert is_wrong_sport(video) is True

    def test_wrong_sport_in_tags(self):
        video = {"title": "Winter Race", "description": "", "tags": ["biathlon", "skiing"]}
        assert is_wrong_sport(video) is True

    def test_none_fields_handled(self):
        video = {"title": None, "description": None, "tags": None}
        assert is_wrong_sport(video) is False


# ── Duration Parsing ───────────────────────────────────────────────────

class TestParseDuration:
    """Test YouTube duration string parsing."""

    def test_mm_ss(self):
        assert _parse_duration_seconds("12:34") == 754

    def test_h_mm_ss(self):
        assert _parse_duration_seconds("1:30:00") == 5400

    def test_seconds_only(self):
        assert _parse_duration_seconds("45") == 45

    def test_empty_string(self):
        assert _parse_duration_seconds("") == 0

    def test_none(self):
        assert _parse_duration_seconds(None) == 0

    def test_non_string(self):
        assert _parse_duration_seconds(123) == 0

    def test_invalid_format(self):
        assert _parse_duration_seconds("abc") == 0

    def test_three_minutes_boundary(self):
        assert _parse_duration_seconds("3:00") == 180

    def test_two_hours_boundary(self):
        assert _parse_duration_seconds("2:00:00") == 7200

    def test_short_video(self):
        """2:59 is under minimum threshold."""
        assert _parse_duration_seconds("2:59") == 179

    def test_long_video(self):
        """2:00:01 is over maximum threshold."""
        assert _parse_duration_seconds("2:00:01") == 7201


# ── Video ID Handling ──────────────────────────────────────────────────

class TestVideoIdCoercion:
    """Test that video_id is always coerced to string."""

    def test_string_id_stays_string(self):
        enriched = {
            "videos": [{"video_id": "dQw4w9WgXcQ", "curation_reason": "test", "duration_string": "5:00"}],
            "quotes": [],
        }
        errors = validate_enrichment("test", enriched)
        assert not errors
        assert enriched["videos"][0]["video_id"] == "dQw4w9WgXcQ"
        assert isinstance(enriched["videos"][0]["video_id"], str)

    def test_int_id_coerced_to_string(self):
        """Claude API sometimes returns int for video_id -- must be coerced."""
        enriched = {
            "videos": [{"video_id": 12345678901, "curation_reason": "test", "duration_string": "5:00"}],
            "quotes": [],
        }
        errors = validate_enrichment("test", enriched)
        # Will have errors because 11-digit int as string won't match VIDEO_ID_RE
        # but the coercion itself should work
        assert isinstance(enriched["videos"][0]["video_id"], str)

    def test_valid_video_id_regex(self):
        assert VIDEO_ID_RE.match("dQw4w9WgXcQ")
        assert VIDEO_ID_RE.match("abc-def_123")
        assert not VIDEO_ID_RE.match("short")
        assert not VIDEO_ID_RE.match("toolongvideoid12345")
        assert not VIDEO_ID_RE.match("")


# ── Enrichment Validation ──────────────────────────────────────────────

class TestEnrichmentValidation:
    """Test the enrichment validation function."""

    def _valid_enrichment(self) -> dict:
        return {
            "videos": [
                {
                    "video_id": "dQw4w9WgXcQ",
                    "curation_reason": "Great race recap from skier POV",
                    "display_order": 1,
                    "duration_string": "15:30",
                }
            ],
            "quotes": [
                {
                    "text": "The snow was perfect today.",
                    "source_video_id": "dQw4w9WgXcQ",
                    "category": "race_atmosphere",
                }
            ],
        }

    def test_valid_enrichment_no_errors(self):
        errors = validate_enrichment("test", self._valid_enrichment())
        assert not errors

    def test_invalid_video_id(self):
        enriched = self._valid_enrichment()
        enriched["videos"][0]["video_id"] = "bad"
        errors = validate_enrichment("test", enriched)
        assert any("Invalid video_id" in e for e in errors)

    def test_missing_curation_reason(self):
        enriched = self._valid_enrichment()
        enriched["videos"][0]["curation_reason"] = ""
        errors = validate_enrichment("test", enriched)
        assert any("missing curation_reason" in e for e in errors)

    def test_too_short_video(self):
        enriched = self._valid_enrichment()
        enriched["videos"][0]["duration_string"] = "2:30"
        errors = validate_enrichment("test", enriched)
        assert any("too short" in e for e in errors)

    def test_too_long_video(self):
        enriched = self._valid_enrichment()
        enriched["videos"][0]["duration_string"] = "2:30:00"
        errors = validate_enrichment("test", enriched)
        assert any("too long" in e for e in errors)

    def test_orphaned_quote(self):
        enriched = self._valid_enrichment()
        enriched["quotes"][0]["source_video_id"] = "xyzABCDEF12"
        errors = validate_enrichment("test", enriched)
        assert any("unknown video_id" in e for e in errors)

    def test_invalid_quote_category(self):
        enriched = self._valid_enrichment()
        enriched["quotes"][0]["category"] = "nonexistent"
        errors = validate_enrichment("test", enriched)
        assert any("invalid category" in e for e in errors)

    def test_duplicate_display_order(self):
        enriched = self._valid_enrichment()
        enriched["videos"].append({
            "video_id": "abc-def_1234",
            "curation_reason": "Another vid",
            "display_order": 1,
            "duration_string": "10:00",
        })
        errors = validate_enrichment("test", enriched)
        assert any("Duplicate display_order" in e for e in errors)

    def test_too_many_videos(self):
        enriched = self._valid_enrichment()
        for i in range(5):
            enriched["videos"].append({
                "video_id": f"vid{i:07d}abcd",
                "curation_reason": f"Video {i}",
                "display_order": i + 2,
                "duration_string": "10:00",
            })
        errors = validate_enrichment("test", enriched)
        assert any("Too many curated videos" in e for e in errors)

    def test_xc_specific_categories_valid(self):
        """Waxing and technique are valid XC-specific categories."""
        enriched = self._valid_enrichment()
        enriched["quotes"][0]["category"] = "waxing"
        errors = validate_enrichment("test", enriched)
        assert not errors

        enriched["quotes"][0]["category"] = "technique"
        errors = validate_enrichment("test", enriched)
        assert not errors


# ── Skier Intel Validation ─────────────────────────────────────────────

class TestSkierIntelValidation:
    """Test validation of the skier_intel block."""

    def _valid_intel(self) -> dict:
        return {
            "key_challenges": [
                {
                    "name": "Oxberg Hill",
                    "km_marker": "55",
                    "description": "Steep climb that breaks the pack.",
                    "source_video_ids": ["dQw4w9WgXcQ"],
                }
            ],
            "terrain_notes": [
                {"text": "Machine-groomed double track, icy in shadows.", "source_video_ids": ["dQw4w9WgXcQ"]}
            ],
            "wax_mentions": [
                {"text": "Klister needed for the warm section near Mora.", "source_video_ids": ["dQw4w9WgXcQ"]}
            ],
            "race_day_tips": [
                {"text": "Start easy, the first 20km are deceptively flat.", "source_video_ids": ["dQw4w9WgXcQ"]}
            ],
            "additional_quotes": [
                {
                    "text": "The blueberry soup station saved my race.",
                    "source_video_id": "dQw4w9WgXcQ",
                    "source_channel": "Nordic Skiing Channel",
                    "source_view_count": 15000,
                    "category": "logistics",
                    "curated": True,
                }
            ],
            "search_text": " ".join(["word"] * 100),  # 100 words
        }

    def test_valid_intel_no_errors(self):
        video_ids = {"dQw4w9WgXcQ"}
        errors = validate_skier_intel("test.json", self._valid_intel(), video_ids)
        assert not errors

    def test_missing_challenge_name(self):
        intel = self._valid_intel()
        intel["key_challenges"][0]["name"] = ""
        errors = validate_skier_intel("test.json", intel, {"dQw4w9WgXcQ"})
        assert any("missing 'name'" in e for e in errors)

    def test_html_in_text(self):
        intel = self._valid_intel()
        intel["terrain_notes"][0]["text"] = "The snow was <b>icy</b> today."
        errors = validate_skier_intel("test.json", intel, {"dQw4w9WgXcQ"})
        assert any("contains HTML" in e for e in errors)

    def test_unknown_video_reference(self):
        intel = self._valid_intel()
        intel["wax_mentions"][0]["source_video_ids"] = ["unknownVidId"]
        errors = validate_skier_intel("test.json", intel, {"dQw4w9WgXcQ"})
        assert any("unknown video_id" in e for e in errors)

    def test_search_text_too_short(self):
        intel = self._valid_intel()
        intel["search_text"] = "Too short."
        errors = validate_skier_intel("test.json", intel, {"dQw4w9WgXcQ"})
        assert any("too short" in e for e in errors)

    def test_search_text_too_long(self):
        intel = self._valid_intel()
        intel["search_text"] = " ".join(["word"] * 501)
        errors = validate_skier_intel("test.json", intel, {"dQw4w9WgXcQ"})
        assert any("too long" in e for e in errors)

    def test_missing_quote_attribution(self):
        intel = self._valid_intel()
        intel["additional_quotes"][0]["source_channel"] = ""
        errors = validate_skier_intel("test.json", intel, {"dQw4w9WgXcQ"})
        assert any("missing 'source_channel'" in e for e in errors)

    def test_too_many_challenges(self):
        intel = self._valid_intel()
        for i in range(6):
            intel["key_challenges"].append({
                "name": f"Hill {i}",
                "description": "A hill.",
                "source_video_ids": ["dQw4w9WgXcQ"],
            })
        errors = validate_skier_intel("test.json", intel, {"dQw4w9WgXcQ"})
        assert any("too many key_challenges" in e for e in errors)


# ── Thumbnail URL Validation ───────────────────────────────────────────

class TestThumbnailUrl:
    """Test thumbnail URL format validation."""

    def test_valid_maxres_url(self):
        url = "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        assert THUMBNAIL_URL_RE.match(url)

    def test_valid_hqdefault_url(self):
        url = "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"
        assert THUMBNAIL_URL_RE.match(url)

    def test_invalid_url_wrong_domain(self):
        url = "https://example.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        assert not THUMBNAIL_URL_RE.match(url)

    def test_invalid_url_wrong_format(self):
        url = "https://i.ytimg.com/vi/dQw4w9WgXcQ/sddefault.jpg"
        assert not THUMBNAIL_URL_RE.match(url)

    def test_invalid_url_bad_video_id(self):
        url = "https://i.ytimg.com/vi/short/maxresdefault.jpg"
        assert not THUMBNAIL_URL_RE.match(url)


# ── Video ID Extraction ────────────────────────────────────────────────

class TestExtractVideoId:
    """Test extraction of video IDs from various URL formats."""

    def test_standard_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_empty_url(self):
        assert extract_video_id("") == ""

    def test_none_url(self):
        assert extract_video_id(None) == ""

    def test_invalid_url(self):
        assert extract_video_id("https://example.com/page") == ""


# ── JSON Response Parsing ──────────────────────────────────────────────

class TestParseJsonResponse:
    """Test parsing of Claude API JSON responses."""

    def test_plain_json(self):
        result = parse_json_response('{"videos": [], "quotes": []}')
        assert result == {"videos": [], "quotes": []}

    def test_code_block_json(self):
        result = parse_json_response('```json\n{"videos": []}\n```')
        assert result == {"videos": []}

    def test_code_block_no_lang(self):
        result = parse_json_response('```\n{"videos": []}\n```')
        assert result == {"videos": []}

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            parse_json_response("not json at all")


# ── Regex Pattern Validation ───────────────────────────────────────────

class TestRegexPatterns:
    """Test that shared regex patterns work correctly."""

    def test_date_re(self):
        assert DATE_RE.match("2026-03-10")
        assert not DATE_RE.match("March 10, 2026")
        assert not DATE_RE.match("2026/03/10")

    def test_html_re(self):
        assert HTML_RE.search("<b>bold</b>")
        assert HTML_RE.search("<script>alert(1)</script>")
        assert not HTML_RE.search("no html here")
        assert not HTML_RE.search("5 < 10 and 10 > 5")  # not HTML tags

    def test_wrong_sport_re(self):
        assert WRONG_SPORT_RE.search("This is alpine skiing content")
        assert WRONG_SPORT_RE.search("Biathlon World Cup 2026")
        assert not WRONG_SPORT_RE.search("Vasaloppet cross country ski race")


# ── Quote Categories ───────────────────────────────────────────────────

class TestQuoteCategories:
    """Test XC-specific quote categories."""

    def test_standard_categories_present(self):
        assert "race_atmosphere" in QUOTE_CATEGORIES
        assert "course_difficulty" in QUOTE_CATEGORIES
        assert "community" in QUOTE_CATEGORIES
        assert "logistics" in QUOTE_CATEGORIES
        assert "training" in QUOTE_CATEGORIES
        assert "generic" in QUOTE_CATEGORIES

    def test_xc_specific_categories_present(self):
        assert "waxing" in QUOTE_CATEGORIES
        assert "technique" in QUOTE_CATEGORIES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
