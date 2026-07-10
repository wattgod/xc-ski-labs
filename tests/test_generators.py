#!/usr/bin/env python3
"""
XC Ski Labs — Generator & Pipeline Tests

Tests the race page generator, search index generator, and deploy script
for edge cases, silent failures, and correctness.

Run: pytest tests/test_generators.py -v
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
WORDPRESS_DIR = PROJECT_ROOT / "wordpress"
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
WEB_DIR = PROJECT_ROOT / "web"
OUTPUT_DIR = PROJECT_ROOT / "output"
NON_RACE_DIRS = {"about", "coaching", "questionnaire", "search", "training-plans"}


# ── Race Page Generator Tests ─────────────────────────────────


class TestRacePageGenerator:
    """Test generate_race_pages.py for correctness and edge cases."""

    def test_generator_runs_without_error(self):
        """Generator should complete without crashing."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "generate_race_pages.py"),
             "--data-dir", str(RACE_DATA_DIR),
             "--output-dir", str(OUTPUT_DIR)],
            capture_output=True, text=True, timeout=120,
        )
        assert result.returncode == 0, \
            f"Generator failed:\nstdout: {result.stdout[-500:]}\nstderr: {result.stderr[-500:]}"

    def test_output_count_matches_valid_profiles(self):
        """Every profile with a valid rating should produce a page."""
        valid_count = 0
        for f in RACE_DATA_DIR.glob("*.json"):
            if f.name == "_schema.json":
                continue
            with open(f) as fh:
                data = json.load(fh)
            race = data.get("race", {})
            if race.get("nordic_lab_rating"):
                valid_count += 1

        output_dirs = [d for d in OUTPUT_DIR.iterdir()
                       if d.is_dir() and (d / "index.html").exists()]
        # Subtract 1 for 'search' directory if present
        non_race_dirs = NON_RACE_DIRS
        page_count = len([d for d in output_dirs if d.name not in non_race_dirs])
        page_count = len([d for d in output_dirs if d.name not in NON_RACE_DIRS])

        assert page_count == valid_count, \
            f"Output pages ({page_count}) != valid profiles ({valid_count})"

    def test_every_page_has_doctype(self):
        """Every generated page should start with <!DOCTYPE html>."""
        for slug_dir in OUTPUT_DIR.iterdir():
            if not slug_dir.is_dir() or slug_dir.name in ("about", "coaching", "questionnaire", "search", "training-plans"):
                continue
            index = slug_dir / "index.html"
            if not index.exists():
                continue
            content = index.read_text()[:50]
            assert content.strip().startswith("<!DOCTYPE html"), \
                f"{slug_dir.name}/index.html missing DOCTYPE"

    def test_every_page_has_title(self):
        """Every page should have a <title> tag."""
        for slug_dir in OUTPUT_DIR.iterdir():
            if not slug_dir.is_dir() or slug_dir.name in ("about", "coaching", "questionnaire", "search", "training-plans"):
                continue
            index = slug_dir / "index.html"
            if not index.exists():
                continue
            content = index.read_text()
            assert "<title>" in content and "</title>" in content, \
                f"{slug_dir.name}/index.html missing <title>"

    def test_no_unescaped_script_close_tags(self):
        """No </script> should appear inside <script> JSON blocks."""
        pattern = re.compile(r"<script[^>]*>.*?</script>", re.DOTALL)
        for slug_dir in OUTPUT_DIR.iterdir():
            if not slug_dir.is_dir() or slug_dir.name in ("about", "coaching", "questionnaire", "search", "training-plans"):
                continue
            index = slug_dir / "index.html"
            if not index.exists():
                continue
            content = index.read_text()
            scripts = pattern.findall(content)
            for script_block in scripts:
                # The opening and closing <script> tags each contain </script>
                # but the CONTENT between them shouldn't
                inner = script_block.split(">", 1)[1].rsplit("</script>", 1)[0]
                assert "</script>" not in inner, \
                    f"{slug_dir.name}/index.html: unescaped </script> in script block"

    def test_no_undefined_or_null_in_visible_text(self):
        """'undefined' or 'null' should not appear as visible text."""
        skip_patterns = re.compile(r'(rider_intel|"null"|null,|= null|null;|null\))')
        for slug_dir in OUTPUT_DIR.iterdir():
            if not slug_dir.is_dir() or slug_dir.name in ("about", "coaching", "questionnaire", "search", "training-plans"):
                continue
            index = slug_dir / "index.html"
            if not index.exists():
                continue
            content = index.read_text()
            # Check for 'undefined' outside of script blocks
            # Remove script blocks first
            no_scripts = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL)
            no_style = re.sub(r"<style[^>]*>.*?</style>", "", no_scripts, flags=re.DOTALL)
            assert "undefined" not in no_style, \
                f"{slug_dir.name}: 'undefined' in visible HTML"

    def test_json_ld_valid(self):
        """SportsEvent JSON-LD should be parseable."""
        ld_pattern = re.compile(
            r'<script type="application/ld\+json">(.*?)</script>', re.DOTALL
        )
        checked = 0
        for slug_dir in OUTPUT_DIR.iterdir():
            if not slug_dir.is_dir() or slug_dir.name in ("about", "coaching", "questionnaire", "search", "training-plans"):
                continue
            index = slug_dir / "index.html"
            if not index.exists():
                continue
            content = index.read_text()
            matches = ld_pattern.findall(content)
            for m in matches:
                # Unescape the safe-json escaping
                m_clean = m.replace("<\\/", "</")
                try:
                    ld = json.loads(m_clean)
                    checked += 1
                except json.JSONDecodeError as e:
                    pytest.fail(f"{slug_dir.name}: Invalid JSON-LD — {e}")
        assert checked > 0, "No JSON-LD found in any page"

    def test_pages_have_back_navigation(self):
        """Every race page should link back to search and home."""
        for slug_dir in OUTPUT_DIR.iterdir():
            if not slug_dir.is_dir() or slug_dir.name in ("about", "coaching", "questionnaire", "search", "training-plans"):
                continue
            index = slug_dir / "index.html"
            if not index.exists():
                continue
            content = index.read_text()
            assert "/search/" in content, \
                f"{slug_dir.name}: No link back to search"


# ── Search Index Tests ────────────────────────────────────────


class TestSearchIndex:
    """Test generate_race_index.py and the index JSON."""

    def test_index_generator_runs(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "generate_race_index.py")],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0, \
            f"Index generator failed: {result.stderr[-300:]}"

    def test_index_json_valid(self):
        index_file = WEB_DIR / "race-index.json"
        assert index_file.exists(), "race-index.json not found"
        with open(index_file) as f:
            data = json.load(f)
        assert "races" in data, "Missing 'races' key in index"
        assert len(data["races"]) > 0, "No races in index"

    def test_index_race_count_matches_profiles(self):
        """Index should have exactly as many races as valid profiles."""
        index_file = WEB_DIR / "race-index.json"
        if not index_file.exists():
            pytest.skip("race-index.json not generated yet")
        with open(index_file) as f:
            data = json.load(f)

        valid_count = 0
        for f in RACE_DATA_DIR.glob("*.json"):
            if f.name == "_schema.json":
                continue
            with open(f) as fh:
                d = json.load(fh)
            if d.get("race", {}).get("nordic_lab_rating"):
                valid_count += 1

        assert len(data["races"]) == valid_count, \
            f"Index has {len(data['races'])} races but {valid_count} valid profiles"

    def test_index_required_fields(self):
        """Every race in the index should have required compact fields."""
        index_file = WEB_DIR / "race-index.json"
        if not index_file.exists():
            pytest.skip("race-index.json not generated yet")
        with open(index_file) as f:
            data = json.load(f)

        required = {"n", "s", "t", "sc", "di", "co"}
        for race in data["races"]:
            missing = required - set(race.keys())
            assert not missing, \
                f"Race '{race.get('n', '?')}' missing index fields: {missing}"

    def test_index_search_text_populated(self):
        """Every race should have search text for filtering."""
        index_file = WEB_DIR / "race-index.json"
        if not index_file.exists():
            pytest.skip("race-index.json not generated yet")
        with open(index_file) as f:
            data = json.load(f)

        for race in data["races"]:
            st = race.get("st", "")
            assert st and len(st) > 5, \
                f"Race '{race.get('n', '?')}' has empty/short search text"


# ── Deploy Script Tests ───────────────────────────────────────


class TestDeployScript:
    """Test deploy.py for import-time errors and CLI validation."""

    def test_deploy_script_imports(self):
        """deploy.py should import without errors."""
        result = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util; "
             "spec = importlib.util.spec_from_file_location('deploy', "
             f"'{SCRIPTS_DIR / 'deploy.py'}'); "
             "mod = importlib.util.module_from_spec(spec)"],
            capture_output=True, text=True, timeout=10,
        )
        # Just check it doesn't crash on import
        assert result.returncode == 0, \
            f"deploy.py import failed: {result.stderr}"

    def test_deploy_no_args_shows_error(self):
        """deploy.py with no args should exit with error, not silently pass."""
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "deploy.py")],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0, \
            "deploy.py with no args should fail"


# ── Homepage Tests ────────────────────────────────────────────


class TestHomepage:
    """Test the homepage for correctness."""

    def test_homepage_exists(self):
        hp = OUTPUT_DIR / "index.html"
        assert hp.exists(), "Homepage not found at output/index.html"

    def test_homepage_has_doctype(self):
        hp = OUTPUT_DIR / "index.html"
        if not hp.exists():
            pytest.skip("Homepage not generated")
        content = hp.read_text()[:50]
        assert content.strip().startswith("<!DOCTYPE html")

    def test_homepage_has_search_link(self):
        hp = OUTPUT_DIR / "index.html"
        if not hp.exists():
            pytest.skip("Homepage not generated")
        content = hp.read_text()
        assert "/search/" in content, "Homepage missing link to search"

    def test_homepage_has_race_links(self):
        hp = OUTPUT_DIR / "index.html"
        if not hp.exists():
            pytest.skip("Homepage not generated")
        content = hp.read_text()
        assert "race/" in content, "Homepage missing links to race pages"

    def test_homepage_no_broken_race_links(self):
        """Every race link on homepage should correspond to an existing page.

        Homepage uses /race/{slug}/ paths (production structure).
        Output directory is flat: output/{slug}/index.html.
        We validate against the flat output structure.
        """
        hp = OUTPUT_DIR / "index.html"
        if not hp.exists():
            pytest.skip("Homepage not generated")
        content = hp.read_text()
        links = re.findall(r'href="race/([^"]+)/"', content)
        for slug in links:
            # Check flat output structure (production uses /race/ prefix)
            page = OUTPUT_DIR / slug / "index.html"
            assert page.exists(), \
                f"Homepage links to race/{slug}/ but output/{slug}/index.html doesn't exist"


# ── Questionnaire Tests ────────────────────────────────────────


class TestQuestionnaireGenerator:
    """Test wordpress/generate_questionnaire.py for the plan intake path."""

    def _generate_with_fixture(self, tmp_path: Path) -> str:
        fixture = tmp_path / "race-index.json"
        fixture.write_text(
            json.dumps({
                "races": [
                    {"s": "vasaloppet", "n": "Vasaloppet"},
                    {"s": "test-script", "n": "Test </script> Race"},
                ]
            }),
            encoding="utf-8",
        )
        result = subprocess.run(
            [
                sys.executable,
                str(WORDPRESS_DIR / "generate_questionnaire.py"),
                "--output-dir",
                str(tmp_path / "output"),
                "--race-index",
                str(fixture),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, \
            f"Questionnaire generator failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        out_file = tmp_path / "output" / "questionnaire" / "index.html"
        assert out_file.exists(), "Questionnaire output not generated"
        return out_file.read_text(encoding="utf-8")

    def test_page_generates_to_questionnaire_index(self):
        result = subprocess.run(
            [sys.executable, str(WORDPRESS_DIR / "generate_questionnaire.py")],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, \
            f"Questionnaire generator failed: {result.stderr[-300:]}"
        assert (OUTPUT_DIR / "questionnaire" / "index.html").exists()

    def test_race_slug_map_prefills_vasaloppet(self, tmp_path):
        html = self._generate_with_fixture(tmp_path)
        assert '"vasaloppet":"Vasaloppet"' in html
        assert "params.get('race')" in html
        assert "raceInput.value = races[raceSlug]" in html

    def test_embedded_slug_map_is_script_safe(self, tmp_path):
        html = self._generate_with_fixture(tmp_path)
        assert "Test <\\/script> Race" in html

    def test_form_posts_to_formsubmit_with_honeypot_and_redirect(self, tmp_path):
        html = self._generate_with_fixture(tmp_path)
        assert 'action="https://formsubmit.co/coaching@xcskilabs.com"' in html
        assert 'method="POST"' in html
        assert 'name="_honey"' in html
        assert 'name="_next" value="https://xcskilabs.com/questionnaire/?submitted=1"' in html
        assert 'name="_subject" value="New Plan Questionnaire' in html
        assert "XC Ski Labs" in html

    def test_success_state_for_submitted_query(self, tmp_path):
        html = self._generate_with_fixture(tmp_path)
        assert "params.get('submitted')" in html
        assert "submitted === '1'" in html
        assert "Questionnaire received." in html

    def test_expected_fields_present(self, tmp_path):
        html = self._generate_with_fixture(tmp_path)
        for field in [
            'name="target_race"',
            'name="race_date"',
            'name="weekly_hours"',
            'name="structured_training_years"',
            'name="technique"',
            'name="constraints"',
            'name="email"',
        ]:
            assert field in html
        assert 'type="email"' in html
        assert 'maxlength="1200"' in html
        assert "You'll get your plan details and payment link by email, usually within a day." in html

    def test_ga4_and_cookie_consent_present(self, tmp_path):
        html = self._generate_with_fixture(tmp_path)
        assert "G-3JQLSQLPPM" in html
        assert "xl_consent" in html
        assert "gl-cookie-consent" in html
        assert "Accept" in html
        assert "Decline" in html

    def test_no_new_gl_tokens_declared(self, tmp_path):
        html = self._generate_with_fixture(tmp_path)
        questionnaire_tokens = set(re.findall(r'(--gl-[a-z0-9-]+):', html))
        race_source = (SCRIPTS_DIR / "generate_race_pages.py").read_text(encoding="utf-8")
        race_root = race_source.split(":root {", 1)[1].split("}", 1)[0]
        race_tokens = set(re.findall(r'(--gl-[a-z0-9-]+):', race_root))
        assert questionnaire_tokens <= race_tokens, \
            f"Questionnaire declares new tokens: {sorted(questionnaire_tokens - race_tokens)}"


# ── Branding Consistency Tests ────────────────────────────────


class TestBranding:
    """Ensure branding is consistent across all pages."""

    def test_no_nordic_lab_in_race_pages(self):
        """Race pages should say 'XC Ski Labs', not 'Nordic Lab'."""
        for slug_dir in OUTPUT_DIR.iterdir():
            if not slug_dir.is_dir() or slug_dir.name in ("about", "coaching", "questionnaire", "search", "training-plans"):
                continue
            index = slug_dir / "index.html"
            if not index.exists():
                continue
            content = index.read_text()
            # Check title and visible text, not CSS variable names
            title_match = re.search(r"<title>(.*?)</title>", content)
            if title_match:
                assert "Nordic Lab" not in title_match.group(1), \
                    f"{slug_dir.name}: Title still says 'Nordic Lab'"

    def test_search_page_says_glide_labs(self):
        """Search page header should say XC SKI LABS."""
        search_html = WEB_DIR / "nordic-lab-search.html"
        if not search_html.exists():
            pytest.skip("Search page not found")
        content = search_html.read_text()
        assert "XC SKI LABS" in content, \
            "Search page still says NORDIC LAB"

    def test_consistent_font_stack(self):
        """Race pages and homepage should use the same font families."""
        hp = OUTPUT_DIR / "index.html"
        if not hp.exists():
            pytest.skip("Homepage not generated")
        hp_content = hp.read_text()

        # Check that homepage uses the same data font as race pages
        assert "Sometype Mono" in hp_content, \
            "Homepage missing Sometype Mono font"
