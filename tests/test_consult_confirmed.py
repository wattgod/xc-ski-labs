#!/usr/bin/env python3
"""
XC Ski Labs — Tests for the /consulting/confirmed/ page

Covers wordpress/generate_consult_confirmed.py: three post-checkout
steps (booking link, intake link with session_id passed as a URL
fragment, TrainingPeaks attach link), the plan add-on reminder, and
the quiet coaching clause.

Port of the confirmation-page content from gravel-race-automation/
wordpress/generate_success_pages.py::build_consulting_success +
build_success_js (Sultanic copy v2) — this repo has no existing
multi-product success-page framework, so this is a dedicated
single-purpose generator rather than a port of the whole PAGES-dict
architecture.

Run: pytest tests/test_consult_confirmed.py -v
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORDPRESS_DIR = PROJECT_ROOT / "wordpress"

sys.path.insert(0, str(WORDPRESS_DIR))

from generate_consult_confirmed import (  # noqa: E402
    TRAININGPEAKS_ATTACH_URL,
    build_hero,
    build_steps,
    build_crosssell,
    build_page_js,
    generate_page,
)
from generate_consulting import BOOKING_URL, ADDON_PRICE  # noqa: E402


@pytest.fixture(scope="module")
def confirmed_html(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("confirmed-out")
    path = generate_page(output_dir=out_dir)
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def confirmed_js():
    return build_page_js()


class TestPageGeneration:
    def test_generator_runs_clean(self):
        result = subprocess.run(
            [sys.executable, str(WORDPRESS_DIR / "generate_consult_confirmed.py"),
             "--output-dir", "/tmp/xl-consult-confirmed-test-out"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, result.stderr

    def test_returns_html(self, confirmed_html):
        assert "<!DOCTYPE html>" in confirmed_html

    def test_noindex(self, confirmed_html):
        assert 'name="robots"' in confirmed_html
        assert "noindex" in confirmed_html

    def test_has_ga4(self, confirmed_html):
        assert "G-3JQLSQLPPM" in confirmed_html


class TestHero:
    def test_headline_and_sub(self):
        hero = build_hero()
        assert "Booked. Three things, then I get to work." in hero
        assert "your read will be done before we talk" in hero


class TestSteps:
    def test_three_steps(self):
        steps = build_steps()
        assert steps.count("gl-confirmed-step-num") == 3

    def test_booking_link(self):
        steps = build_steps()
        assert BOOKING_URL in steps
        assert 'data-cta="schedule_session"' in steps

    def test_intake_link_defaults_to_intake_page(self):
        """The href defaults to /consulting/intake/ and is rewritten by
        JS to include #ref=<session_id> once session_id is known."""
        steps = build_steps()
        assert 'id="consult-intake-link"' in steps
        assert 'href="/consulting/intake/"' in steps
        assert 'data-cta="start_intake"' in steps

    def test_trainingpeaks_attach_link(self):
        steps = build_steps()
        assert TRAININGPEAKS_ATTACH_URL in steps
        assert 'data-cta="connect_trainingpeaks"' in steps


class TestCrosssell:
    def test_addon_reminder(self):
        crosssell = build_crosssell()
        assert ADDON_PRICE in crosssell
        assert "seven days after we speak" in crosssell

    def test_quiet_coaching_clause(self):
        crosssell = build_crosssell()
        assert "every week" in crosssell
        assert 'href="https://xcskilabs.com/coaching/"' in crosssell


class TestJS:
    def test_sets_intake_link_from_session_id(self, confirmed_js):
        assert "consult-intake-link" in confirmed_js
        assert "/consulting/intake/#ref=" in confirmed_js
        assert "session_id" in confirmed_js

    def test_fires_purchase_event(self, confirmed_js):
        assert "'purchase'" in confirmed_js
        assert "transaction_id: sessionId" in confirmed_js

    def test_js_syntax_valid(self, confirmed_js):
        js = confirmed_js.replace("<script>", "").replace("</script>", "")
        result = subprocess.run(
            ["node", "-e", f"new Function({repr(js)})"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"JS syntax error: {result.stderr}"


class TestFooter:
    def test_footer_present(self, confirmed_html):
        assert "gl-consult-footer" in confirmed_html
