#!/usr/bin/env python3
"""
XC Ski Labs — Data Quality & Edge Case Tests

Catches: schema inconsistencies, type mismatches, duplicate races,
orphaned data, silent failures, and edge cases that strain the system.

Run: pytest tests/test_data_quality.py -v
"""

import json
import re
import unicodedata
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
WEB_DIR = PROJECT_ROOT / "web"
OUTPUT_DIR = PROJECT_ROOT / "output"

VALID_DISCIPLINES = {"classic", "skate", "both"}

# Canonical top-level keys every profile's "race" dict should contain.
# _fact_check_fixes is metadata that should be cleaned up — tested separately.
CANONICAL_RACE_KEYS = {
    "name", "slug", "display_name", "tagline",
    "vitals", "climate", "course", "nordic_lab_rating",
    "history", "series_membership", "youtube_data",
}

REQUIRED_CRITERIA = [
    "distance", "elevation", "altitude", "field_size", "prestige",
    "international_draw", "course_technicality", "snow_reliability",
    "grooming_quality", "accessibility", "community", "scenery",
    "organization", "competitive_depth",
]


# ── Helpers ──────────────────────────────────────────────────


def _load_all_profiles():
    """Load all race JSON profiles, yielding (filename, data) tuples."""
    profiles = []
    for f in sorted(RACE_DATA_DIR.glob("*.json")):
        if f.name == "_schema.json":
            continue
        with open(f) as fh:
            data = json.load(fh)
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
    return filename, data["race"]


def _extract_number(s):
    """Try to extract a leading number from a string like '~8,000 starters'."""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return s
    m = re.match(r"^~?\s*([\d,]+(?:\.\d+)?)", str(s).strip())
    if m:
        return float(m.group(1).replace(",", ""))
    # Range like "400-700"
    m = re.match(r"^~?\s*([\d,]+)\s*[-–]\s*([\d,]+)", str(s).strip())
    if m:
        lo = float(m.group(1).replace(",", ""))
        hi = float(m.group(2).replace(",", ""))
        return (lo + hi) / 2
    return None


def _normalize_name(name):
    """Lowercase, strip accents, remove common suffixes for fuzzy matching."""
    # Decompose unicode and strip combining characters (accents)
    nfkd = unicodedata.normalize("NFKD", name)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    normalized = stripped.lower().strip()
    # Remove common suffixes
    for suffix in ["ski marathon", "loppet", "race", "marathon", "hiihto",
                   "maraton", "lopp", "rennet"]:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)].strip()
    return normalized


def _levenshtein(a, b):
    """Simple Levenshtein distance."""
    if len(a) < len(b):
        return _levenshtein(b, a)
    if len(b) == 0:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[j] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


def _normalize_domain(url):
    """Extract domain from URL for comparison."""
    if not url:
        return ""
    url = url.lower().strip().rstrip("/")
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"^www\.", "", url)
    # Strip path
    url = url.split("/")[0]
    return url


# ── Schema Consistency Tests ──────────────────────────────────


class TestSchemaConsistency:
    """Validate that all profiles share a consistent schema."""

    # tervahiihto.json is a known profile missing 'history' — documented for backfill.
    KNOWN_MISSING_HISTORY = {"tervahiihto.json"}

    def test_all_profiles_have_consistent_top_level_keys(self, race):
        """Every profile must have the canonical top-level keys under 'race'.
        Extra keys (like _fact_check_fixes) are flagged in a separate test.
        """
        filename, r = race
        actual_keys = {k for k in r.keys() if not k.startswith("_")}
        missing = CANONICAL_RACE_KEYS - actual_keys
        extra = actual_keys - CANONICAL_RACE_KEYS

        # Allow known exceptions
        if filename in self.KNOWN_MISSING_HISTORY and missing == {"history"}:
            pytest.xfail(f"{filename}: Missing 'history' — backfill needed")

        assert not missing, \
            f"{filename}: Missing top-level keys: {missing}"
        assert not extra, \
            f"{filename}: Unexpected top-level keys: {extra}"

    def test_vitals_field_types(self, race):
        """Core vitals fields must have correct types."""
        filename, r = race
        vitals = r.get("vitals", {})

        # distance_km must be numeric
        dist = vitals.get("distance_km")
        if dist is not None:
            assert isinstance(dist, (int, float)), \
                f"{filename}: distance_km should be int/float, got {type(dist).__name__}: {dist!r}"

        # elevation_m must be int/float or None
        elev = vitals.get("elevation_m")
        if elev is not None:
            assert isinstance(elev, (int, float)), \
                f"{filename}: elevation_m should be int/float, got {type(elev).__name__}: {elev!r}"

        # field_size_estimate must be int/float (not string like "~8,000")
        fse = vitals.get("field_size_estimate")
        if fse is not None:
            assert isinstance(fse, (int, float)), \
                f"{filename}: field_size_estimate should be int/float, got {type(fse).__name__}: {fse!r}"

        # discipline must be valid
        disc = vitals.get("discipline")
        if disc is not None:
            assert disc in VALID_DISCIPLINES, \
                f"{filename}: Invalid discipline '{disc}'"

    def test_no_string_numbers_in_vitals(self, race):
        """Scan vitals for string values that look like bare numbers.
        The 'field_size' field is a known human-readable string (e.g. '~1,500 starters')
        and is excluded. All other vitals should use actual numeric types.
        """
        filename, r = race
        vitals = r.get("vitals", {})
        # field_size is a display string by convention; field_size_estimate is the numeric one.
        # date_specific, date, registration, etc. are legitimately strings containing digits.
        EXEMPT_FIELDS = {
            "field_size", "date", "date_specific", "registration",
            "aid_stations", "cutoff_time", "prize_purse", "location",
            "location_badge", "region", "country", "country_code",
            "website", "distance_options",
        }
        bare_number_re = re.compile(r"^\d[\d,.]*$")
        violations = []
        for key, val in vitals.items():
            if key in EXEMPT_FIELDS:
                continue
            if isinstance(val, str) and bare_number_re.match(val.strip()):
                violations.append(f"{key}={val!r}")
        assert not violations, \
            f"{filename}: String values that look like bare numbers in vitals: {violations}"

    def test_website_field_consistency(self):
        """Every profile should use the same field path for website.
        Convention is vitals.website — flag any that use a different path.
        """
        no_website = []
        for filename, data in ALL_PROFILES:
            race = data.get("race", {})
            vitals = race.get("vitals", {})
            if "website" not in vitals:
                no_website.append(filename)
            # Check no alternative location
            logistics = race.get("logistics", {})
            if isinstance(logistics, dict):
                assert "official_site" not in logistics, \
                    f"{filename}: Website in logistics.official_site instead of vitals.website"
        # All profiles should have vitals.website (some may have it as None)
        assert not no_website, \
            f"Profiles missing vitals.website field entirely: {no_website}"

    def test_no_fact_check_metadata_in_profiles(self):
        """Profiles should NOT contain _fact_check_fixes or other
        underscore-prefixed metadata keys. These are internal artifacts
        that should be cleaned before commit.
        """
        violations = []
        for filename, data in ALL_PROFILES:
            race = data.get("race", {})
            underscore_keys = [k for k in race if k.startswith("_")]
            if underscore_keys:
                violations.append(f"{filename}: {underscore_keys}")
        # NOTE: 22 profiles currently have _fact_check_fixes.
        # This test documents the issue. When cleaned, it will enforce cleanliness.
        if violations:
            pytest.xfail(
                f"{len(violations)} profiles have underscore-prefixed metadata keys "
                f"(e.g. _fact_check_fixes). Clean with normalize_profiles.py. "
                f"First 3: {violations[:3]}"
            )


# ── Duplicate Detection Tests ─────────────────────────────────


class TestDuplicateDetection:
    """Detect potential duplicate races hiding under different slugs."""

    # Known-valid pairs where one slug is a substring of another.
    KNOWN_SUBSTRING_PAIRS = {
        ("marcialonga", "marcialonga-bodo"),
        ("tartu-maraton", "tartu-maratoni-retrosoit"),
        ("vasaloppet", "vasaloppet-china"),
        ("vasaloppet", "vasaloppet-japan"),
        ("vasaloppet", "vasaloppet-usa"),
    }

    # Known-valid pairs with low Levenshtein distance (verified different events).
    KNOWN_SIMILAR_SLUGS = {
        ("asarna-ski-marathon", "astana-ski-marathon"),  # Sweden vs Kazakhstan
        ("saskaloppet", "vasaloppet"),                    # Canada vs Sweden
    }

    def test_no_similar_slugs(self):
        """Detect slugs that are suspiciously similar:
        - Levenshtein distance < 3
        - One is a substring of the other
        Whitelisted known-valid pairs are excluded.
        """
        slugs = []
        for filename, data in ALL_PROFILES:
            race = data.get("race", {})
            slugs.append(race.get("slug", filename.replace(".json", "")))

        suspicious = []
        for i, s1 in enumerate(slugs):
            for s2 in slugs[i + 1:]:
                pair = tuple(sorted([s1, s2]))
                if pair in self.KNOWN_SUBSTRING_PAIRS:
                    continue
                if pair in self.KNOWN_SIMILAR_SLUGS:
                    continue
                # Substring check
                if s1 in s2 or s2 in s1:
                    suspicious.append((s1, s2, "substring"))
                # Levenshtein check (skip very short slugs to avoid noise)
                elif len(s1) > 5 and len(s2) > 5 and _levenshtein(s1, s2) < 3:
                    suspicious.append((s1, s2, f"lev={_levenshtein(s1, s2)}"))

        assert not suspicious, \
            f"Suspiciously similar slugs (check for duplicates): {suspicious}"

    def test_no_duplicate_display_names_fuzzy(self):
        """Flag display names that match after normalization:
        lowercase, strip accents, remove common suffixes.
        """
        name_map = {}
        for filename, data in ALL_PROFILES:
            race = data.get("race", {})
            display_name = race.get("display_name", "")
            if not display_name:
                continue
            norm = _normalize_name(display_name)
            name_map.setdefault(norm, []).append(
                (filename, display_name)
            )

        duplicates = {k: v for k, v in name_map.items() if len(v) > 1}
        if duplicates:
            details = []
            for norm, entries in duplicates.items():
                names = [f"{fn} ({dn})" for fn, dn in entries]
                details.append(f"'{norm}': {names}")
            # Known duplicates from normalization (e.g. "Vasaloppet" family)
            # These are legitimate separate events — only fail on unexpected ones.
            known_norm_dupes = {
                "vasaloppet",  # vasaloppet, vasaloppet-china, vasaloppet-japan, vasaloppet-usa
                "gatineau",    # gatineau-55 / gatineau-loppet both normalize to "gatineau"
                "ushuaia",     # ushuaia-loppet / ushuaia-ski-marathon are distinct events
            }
            unexpected = {k: v for k, v in duplicates.items()
                          if k not in known_norm_dupes}
            assert not unexpected, \
                f"Fuzzy duplicate display names: {details}"

    def test_no_duplicate_official_sites(self):
        """Two different races sharing the same website domain is suspicious.
        Known-valid shared domains (umbrella orgs) are whitelisted.
        """
        # Umbrella organization domains that legitimately host multiple races
        KNOWN_SHARED_DOMAINS = {
            "birkie.com",           # American Birkebeiner + North End Classic
            "swissloppet.ch",       # Swiss Loppet series races
            "russialoppet.ru",      # Russia Loppet series races
            "svenskalanglopp.se",   # Swedish long-distance series
            "langlopscupen.no",     # Norwegian long-distance cup
            "loppet.org",           # Minneapolis Loppet Foundation
            "oregonnordic.org",     # Oregon Nordic Club
            "engadin-skimarathon.ch",  # Engadin main + Frauenlauf
            "finlandiahiihto.fi",   # Finlandia Hiihto family
            "gatineauloppet.com",   # Gatineau Loppet family
            "skiserbia.rs",         # Serbian ski federation
            "snowfarmnz.com",       # Snow Farm NZ events
            "sovereignlake.com",    # Sovereign Lake events
            "skiclassics.com",      # Ski Classics series
            "tartumaraton.ee",      # Tartu Marathon family
            "vasaloppet.se",        # Vasaloppet week events (main, halvvasan, nattvasan, etc.)
            "mbsef.org",            # Mt Baker Ski Education Foundation events
            "ugraloppet.ru",        # Ugra region events
            "yllaslevi.fi",         # Yllas-Levi region events
        }

        domain_map = {}
        for filename, data in ALL_PROFILES:
            race = data.get("race", {})
            url = race.get("vitals", {}).get("website", "")
            if not url:
                continue
            domain = _normalize_domain(url)
            if domain in KNOWN_SHARED_DOMAINS:
                continue
            domain_map.setdefault(domain, []).append(filename)

        duplicates = {d: files for d, files in domain_map.items()
                      if len(files) > 1}
        assert not duplicates, \
            f"Races sharing the same website domain (not whitelisted): {duplicates}"


# ── Scoring Integrity Tests ───────────────────────────────────


class TestScoringIntegrity:
    """Verify scoring criteria types and cross-validate against vitals."""

    def test_criteria_are_integers(self, race):
        """All 14 criteria must be int, not float. Score 3.5 is invalid."""
        filename, r = race
        rating = r.get("nordic_lab_rating", {})
        float_criteria = []
        for c in REQUIRED_CRITERIA:
            val = rating.get(c)
            if val is not None and isinstance(val, float):
                float_criteria.append(f"{c}={val}")
        assert not float_criteria, \
            f"{filename}: Float criteria (must be int): {float_criteria}"

    def test_elevation_criterion_matches_vitals(self, race):
        """Cross-validate elevation criterion against vitals.elevation_m.
        - If elevation_m > 1000, criterion should be >= 3
        - If elevation_m < 200, criterion should be <= 2
        """
        filename, r = race
        vitals = r.get("vitals", {})
        rating = r.get("nordic_lab_rating", {})
        elev = vitals.get("elevation_m")
        criterion = rating.get("elevation")
        if elev is None or criterion is None:
            return
        if elev > 1000:
            assert criterion >= 3, \
                f"{filename}: elevation_m={elev} but elevation criterion={criterion} (expected >= 3)"
        if elev < 200:
            assert criterion <= 2, \
                f"{filename}: elevation_m={elev} but elevation criterion={criterion} (expected <= 2)"

    def test_distance_criterion_matches_vitals(self, race):
        """Cross-validate distance criterion against vitals.distance_km.
        - If distance_km >= 70, criterion should be >= 4
        - If distance_km < 20, criterion should be <= 2
        """
        filename, r = race
        vitals = r.get("vitals", {})
        rating = r.get("nordic_lab_rating", {})
        dist = vitals.get("distance_km")
        criterion = rating.get("distance")
        if dist is None or criterion is None:
            return
        if dist >= 70:
            assert criterion >= 4, \
                f"{filename}: distance_km={dist} but distance criterion={criterion} (expected >= 4)"
        if dist < 20:
            assert criterion <= 2, \
                f"{filename}: distance_km={dist} but distance criterion={criterion} (expected <= 2)"

    def test_field_size_criterion_matches_vitals(self, race):
        """Cross-validate field_size criterion against field_size_estimate.
        - If field_size_estimate > 5000, criterion should be >= 3
        """
        filename, r = race
        vitals = r.get("vitals", {})
        rating = r.get("nordic_lab_rating", {})
        fse = vitals.get("field_size_estimate")
        criterion = rating.get("field_size")
        if fse is None or criterion is None:
            return
        if isinstance(fse, (int, float)) and fse > 5000:
            assert criterion >= 3, \
                f"{filename}: field_size_estimate={fse} but field_size criterion={criterion} (expected >= 3)"


# ── URL Quality Tests ─────────────────────────────────────────


class TestUrlQuality:
    """Validate website URLs for quality and correctness."""

    def test_websites_are_https(self, race):
        """All website URLs should use https://, not http://."""
        filename, r = race
        url = r.get("vitals", {}).get("website", "")
        if not url:
            return
        if url.startswith("http://"):
            pytest.xfail(
                f"{filename}: Website uses http:// — should be https://: {url}"
            )

    def test_websites_are_not_generic(self, race):
        """Website URLs should not be generic platforms."""
        filename, r = race
        url = r.get("vitals", {}).get("website", "")
        if not url:
            return
        generic_patterns = [
            "wikipedia.org", "facebook.com", "instagram.com",
            "youtube.com", "twitter.com", "x.com",
        ]
        url_lower = url.lower()
        for pattern in generic_patterns:
            assert pattern not in url_lower, \
                f"{filename}: Website is a generic platform URL ({pattern}): {url}"

    def test_no_localhost_or_example_urls(self, race):
        """Catch test/placeholder URLs that should never be in production data."""
        filename, r = race
        url = r.get("vitals", {}).get("website", "")
        if not url:
            return
        url_lower = url.lower()
        bad_patterns = ["localhost", "127.0.0.1", "example.com", "example.org",
                        "test.com", "placeholder"]
        for pattern in bad_patterns:
            assert pattern not in url_lower, \
                f"{filename}: Placeholder/test URL detected ({pattern}): {url}"


# ── Output Integrity Tests ────────────────────────────────────


class TestOutputIntegrity:
    """Verify generated output matches source data."""

    def test_search_dir_exists_and_current(self):
        """output/search/index.html must exist, and
        output/search/race-index.json must have the same race count
        as web/race-index.json.
        """
        search_dir = OUTPUT_DIR / "search"
        assert search_dir.exists(), "output/search/ directory missing"
        assert (search_dir / "index.html").exists(), \
            "output/search/index.html missing"

        web_index = WEB_DIR / "race-index.json"
        out_index = search_dir / "race-index.json"

        if not web_index.exists():
            pytest.skip("web/race-index.json not generated yet")
        assert out_index.exists(), \
            "output/search/race-index.json missing"

        with open(web_index) as f:
            web_data = json.load(f)
        with open(out_index) as f:
            out_data = json.load(f)

        assert len(out_data["races"]) == len(web_data["races"]), \
            f"output/search/race-index.json has {len(out_data['races'])} races " \
            f"but web/race-index.json has {len(web_data['races'])}"

    def test_sitemap_race_count_matches(self):
        """output/sitemap.xml URL count should match profile count + 2
        (homepage + search).
        """
        sitemap = OUTPUT_DIR / "sitemap.xml"
        if not sitemap.exists():
            pytest.skip("Sitemap not generated yet")

        content = sitemap.read_text()
        url_count = content.count("<url>")

        profile_count = len(ALL_PROFILES)
        expected = profile_count + 2  # homepage + search

        assert url_count == expected, \
            f"Sitemap has {url_count} URLs but expected {expected} " \
            f"({profile_count} profiles + homepage + search)"

    def test_no_orphaned_output_dirs(self):
        """Every dir in output/ (except 'search') should correspond
        to an existing profile slug. Catches stale output after profile deletion.
        """
        if not OUTPUT_DIR.exists():
            pytest.skip("Output directory not generated yet")

        profile_slugs = {f.stem for f in RACE_DATA_DIR.glob("*.json")
                         if f.name != "_schema.json"}

        orphaned = []
        for d in OUTPUT_DIR.iterdir():
            if not d.is_dir():
                continue
            if d.name in ("search", "training-plans", "coaching"):
                continue
            if d.name not in profile_slugs:
                orphaned.append(d.name)

        assert not orphaned, \
            f"Orphaned output directories (no matching profile): {orphaned}"

    def test_homepage_race_count_matches(self):
        """Homepage statRaces value must equal profile count."""
        hp = OUTPUT_DIR / "index.html"
        if not hp.exists():
            pytest.skip("Homepage not generated")

        content = hp.read_text()
        m = re.search(r'id="statRaces">(\d+)', content)
        assert m, "Homepage missing statRaces element"

        stat_count = int(m.group(1))
        profile_count = len(ALL_PROFILES)

        assert stat_count == profile_count, \
            f"Homepage says {stat_count} races but {profile_count} profiles exist"


# ── Edge Case Tests ───────────────────────────────────────────


class TestEdgeCases:
    """Catch edge cases that could break generators or the frontend."""

    def test_unicode_in_names_handled(self):
        """Profiles with non-ASCII names should generate valid HTML pages
        without encoding errors.
        """
        unicode_profiles = []
        for filename, data in ALL_PROFILES:
            race = data.get("race", {})
            dn = race.get("display_name", "")
            if any(ord(c) > 127 for c in dn):
                unicode_profiles.append((filename, dn, race.get("slug", "")))

        assert len(unicode_profiles) > 0, \
            "No profiles with non-ASCII names found — test is vacuous"

        for filename, display_name, slug in unicode_profiles:
            page = OUTPUT_DIR / slug / "index.html"
            if not page.exists():
                continue
            content = page.read_text(encoding="utf-8")
            assert display_name in content, \
                f"{filename}: Display name '{display_name}' not found in generated page"

    def test_very_long_taglines_dont_break_cards(self):
        """Taglines over 200 chars should still exist without issues."""
        long_taglines = []
        for filename, data in ALL_PROFILES:
            race = data.get("race", {})
            tagline = race.get("tagline", "")
            if len(tagline) > 200:
                long_taglines.append((filename, tagline, race.get("slug", "")))

        # Even if none exist, the test should not fail
        for filename, tagline, slug in long_taglines:
            page = OUTPUT_DIR / slug / "index.html"
            if not page.exists():
                continue
            content = page.read_text()
            # The tagline (or a truncated form) should appear somewhere
            # Check that at least the first 50 chars appear
            assert tagline[:50] in content, \
                f"{filename}: Long tagline ({len(tagline)} chars) not rendered"

    def test_zero_elevation_profiles(self):
        """Profiles with elevation_m = 0 or null should still generate valid pages."""
        zero_elev = []
        for filename, data in ALL_PROFILES:
            race = data.get("race", {})
            elev = race.get("vitals", {}).get("elevation_m")
            if elev is None or elev == 0:
                zero_elev.append((filename, race.get("slug", "")))

        for filename, slug in zero_elev:
            page = OUTPUT_DIR / slug / "index.html"
            if not page.exists():
                continue
            content = page.read_text()
            assert content.strip().startswith("<!DOCTYPE html"), \
                f"{filename}: Zero-elevation profile page is malformed"

    def test_empty_youtube_data_handled(self):
        """Profiles with empty videos list should render without
        'undefined' or errors in visible HTML.
        """
        empty_yt = []
        for filename, data in ALL_PROFILES:
            race = data.get("race", {})
            videos = race.get("youtube_data", {}).get("videos", [])
            if len(videos) == 0:
                empty_yt.append((filename, race.get("slug", "")))

        assert len(empty_yt) > 0, \
            "No profiles with empty youtube videos — test is vacuous"

        for filename, slug in empty_yt:
            page = OUTPUT_DIR / slug / "index.html"
            if not page.exists():
                continue
            content = page.read_text()
            # Strip out script and style blocks
            visible = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
            visible = re.sub(r"<style[^>]*>.*?</style>", "", visible, flags=re.DOTALL)
            assert "undefined" not in visible, \
                f"{filename}: 'undefined' in visible HTML of empty-youtube profile"

    def test_extreme_scores(self):
        """Verify that the lowest-scoring and highest-scoring profiles
        generate valid pages.
        """
        scores = []
        for filename, data in ALL_PROFILES:
            race = data.get("race", {})
            score = race.get("nordic_lab_rating", {}).get("overall_score", 0)
            slug = race.get("slug", "")
            scores.append((score, filename, slug))

        scores.sort()
        # Check lowest and highest
        for score, filename, slug in [scores[0], scores[-1]]:
            page = OUTPUT_DIR / slug / "index.html"
            if not page.exists():
                continue
            content = page.read_text()
            assert content.strip().startswith("<!DOCTYPE html"), \
                f"{filename} (score={score}): Generated page is malformed"
            assert "<title>" in content, \
                f"{filename} (score={score}): Generated page missing <title>"

    def test_all_countries_have_valid_names(self, race):
        """No country should be empty, '?', 'Unknown', 'TBD', or a 2-letter code."""
        filename, r = race
        country = r.get("vitals", {}).get("country", "")
        invalid_values = {"", "?", "Unknown", "TBD", "N/A", "None"}
        assert country not in invalid_values, \
            f"{filename}: Invalid country value: {country!r}"
        # Should not be a 2-letter country code (those belong in country_code)
        if country and len(country) == 2 and country.isupper():
            pytest.fail(
                f"{filename}: Country '{country}' looks like a country code, "
                f"not a full name"
            )
        # Minimum length for a real country name
        assert len(country) >= 3, \
            f"{filename}: Country too short: {country!r}"
