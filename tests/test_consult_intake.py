#!/usr/bin/env python3
"""
XC Ski Labs — Tests for the /consulting/intake/ form

Covers wordpress/generate_consult_intake.py: 14 fields (incl. tp_email
exact key), header copy, honeypot/form structure, success state,
privacy sentence (shared with /consulting/), fragment-only ref/t
parsing (never the query string), the fetch-based submission to
/api/consult-intake, and save/resume via localStorage.

Port of gravel-race-automation/tests/test_consult_intake.py — same
coverage, adapted to this repo's generator naming.

Run: pytest tests/test_consult_intake.py -v
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORDPRESS_DIR = PROJECT_ROOT / "wordpress"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"

sys.path.insert(0, str(WORDPRESS_DIR))

from generate_consult_intake import (  # noqa: E402
    CONSULT_INTAKE_API,
    build_nav,
    build_header,
    build_fields,
    build_submit_buttons,
    build_success_state,
    build_privacy,
    build_footer,
    build_jsonld,
    build_intake_css,
    build_intake_js,
    generate_intake_page,
)
from generate_consulting import PRIVACY_SENTENCE  # noqa: E402


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture(scope="module")
def intake_html(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("intake-out")
    path = generate_intake_page(output_dir=out_dir)
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def intake_css():
    return build_intake_css()


@pytest.fixture(scope="module")
def intake_js():
    return build_intake_js()


# ── Page Generation ──────────────────────────────────────────


class TestPageGeneration:
    def test_generator_runs_clean(self):
        result = subprocess.run(
            [sys.executable, str(WORDPRESS_DIR / "generate_consult_intake.py"),
             "--output-dir", "/tmp/xl-consult-intake-test-out"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, result.stderr

    def test_returns_html(self, intake_html):
        assert isinstance(intake_html, str)
        assert "<!DOCTYPE html>" in intake_html

    def test_has_canonical(self, intake_html):
        assert 'rel="canonical"' in intake_html
        assert "/consulting/intake/" in intake_html

    def test_has_ga4(self, intake_html):
        assert "G-3JQLSQLPPM" in intake_html
        assert "googletagmanager.com" in intake_html

    def test_has_meta_robots_noindex(self, intake_html):
        assert 'name="robots"' in intake_html
        assert "noindex" in intake_html

    def test_has_meta_description(self, intake_html):
        assert 'name="description"' in intake_html

    def test_has_title(self, intake_html):
        assert "<title>" in intake_html
        assert "Consulting Intake" in intake_html

    def test_has_jsonld(self, intake_html):
        assert 'application/ld+json' in intake_html


# ── Nav ──────────────────────────────────────────────────────


class TestNav:
    def test_nav_present(self, intake_html):
        assert "gl-nav" in intake_html
        assert 'href="/consulting/"' in intake_html


# ── Fields (14 questions, exact keys) ────────────────────────


class TestFields:
    EXPECTED_FIELD_NAMES = [
        "goal_event",
        "goal_date",
        "hours_typical",
        "hours_max",
        "years_training",
        "ftp",
        "lthr",
        "top_question",
        "whats_gone_wrong",
        "injuries_limits",
        "tp_email",
        "power_meter",
        "hr_strap",
        "coaching_history",
        "anything_else",
    ]

    def test_all_field_names_present(self):
        fields = build_fields()
        for name in self.EXPECTED_FIELD_NAMES:
            assert f'name="{name}"' in fields, f"Missing field: {name}"

    def test_field_count_in_range(self):
        """Spec: 12-14 field GROUPS (goal event + date count as one group)."""
        fields = build_fields()
        names = set(re.findall(r'name="(\w+)"', fields))
        group_count = len(names) - 1
        assert 12 <= group_count <= 14, f"Expected 12-14 field groups, got {group_count}"

    def test_tp_email_field_key_exact(self):
        """The TrainingPeaks login email field key MUST be tp_email."""
        fields = build_fields()
        assert 'name="tp_email"' in fields

    def test_tp_email_allows_no_tp(self):
        fields = build_fields()
        assert "no TP" in fields

    def test_ftp_lthr_allow_dont_know(self):
        fields = build_fields()
        assert "don't know" in fields
        assert fields.count("don't know") >= 2

    def test_power_meter_and_hr_strap_are_yes_no(self):
        fields = build_fields()
        assert 'name="power_meter" value="yes"' in fields
        assert 'name="power_meter" value="no"' in fields
        assert 'name="hr_strap" value="yes"' in fields
        assert 'name="hr_strap" value="no"' in fields

    def test_top_question_field(self):
        fields = build_fields()
        assert 'name="top_question"' in fields
        assert "<textarea" in fields

    def test_fields_in_full_page(self, intake_html):
        for name in self.EXPECTED_FIELD_NAMES:
            assert f'name="{name}"' in intake_html


# ── Header / Copy ─────────────────────────────────────────────


class TestHeader:
    def test_header_present(self):
        header = build_header()
        assert "Twelve Questions" in header
        assert "five minutes" in header.lower() or "Five minutes" in header

    def test_missing_token_banner_present(self):
        header = build_header()
        assert "welcome email" in header.lower()
        assert 'id="token-banner"' in header


# ── Honeypot / Form Structure ─────────────────────────────────


class TestFormStructure:
    def test_honeypot(self, intake_html):
        assert "gl-intake-honeypot" in intake_html
        assert 'name="_honeypot"' in intake_html

    def test_form_element(self, intake_html):
        assert '<form id="intake-form"' in intake_html

    def test_submit_and_save_buttons(self):
        buttons = build_submit_buttons()
        assert 'id="submit-btn"' in buttons
        assert 'id="save-btn"' in buttons
        assert "Save Progress" in buttons


# ── Success State ─────────────────────────────────────────────


class TestSuccessState:
    def test_success_copy(self):
        success = build_success_state()
        assert "I&rsquo;ll have your read done before we talk" in success

    def test_success_hidden_by_default(self):
        success = build_success_state()
        assert 'style="display:none"' in success


# ── Privacy ────────────────────────────────────────────────────


class TestPrivacy:
    def test_privacy_sentence_present(self):
        privacy = build_privacy()
        assert "deleted on request" in privacy

    def test_privacy_matches_consulting_page(self):
        """Privacy language must match the /consulting/ page verbatim."""
        privacy = build_privacy()
        assert PRIVACY_SENTENCE in privacy

    def test_privacy_in_full_page(self, intake_html):
        assert "deleted on request" in intake_html


# ── Fragment Parsing (never query string) ─────────────────────


class TestFragmentParsing:
    def test_reads_hash_not_search(self, intake_js):
        assert "window.location.hash" in intake_js

    def test_does_not_read_query_string_for_token(self, intake_js):
        """The intake token must never be read from window.location.search —
        query strings get logged by servers and leak via referrer headers."""
        assert "location.search" not in intake_js

    def test_no_query_string_token_anywhere(self, intake_html):
        """No `?t=` pattern anywhere in the page — the token is fragment-only."""
        assert "?t=" not in intake_html

    def test_ref_and_t_parsed(self, intake_js):
        assert 'params.get("ref")' in intake_js
        assert 'params.get("t")' in intake_js


# ── Submission (POST, token in body) ──────────────────────────


class TestSubmission:
    def test_posts_to_consult_intake_api(self, intake_js):
        assert CONSULT_INTAKE_API in intake_js
        assert "/api/consult-intake" in intake_js

    def test_payload_shape(self, intake_js):
        assert "ref: frag.ref" in intake_js
        assert "t: frag.t" in intake_js
        assert "answers: answers" in intake_js

    def test_uses_post_method(self, intake_js):
        assert 'method: "POST"' in intake_js

    def test_token_in_body_not_header_or_query(self, intake_js):
        """CORS: token travels in the JSON body, not a custom header or
        query param."""
        assert "Authorization" not in intake_js
        assert "X-Token" not in intake_js


# ── Save / Resume ──────────────────────────────────────────────


class TestSaveResume:
    def test_localstorage_save(self, intake_js):
        assert "localStorage.setItem" in intake_js
        assert "consult_intake_progress" in intake_js

    def test_localstorage_restore(self, intake_js):
        assert "restoreProgress" in intake_js
        assert "localStorage.getItem" in intake_js

    def test_success_clears_draft(self, intake_js):
        assert "localStorage.removeItem" in intake_js

    def test_error_keeps_draft(self, intake_js):
        """On a failed submission, the draft must NOT be cleared."""
        catch_match = re.search(r'\.catch\(function\(err\)\{(.*?)\}\);', intake_js, re.DOTALL)
        assert catch_match, "Could not find .catch() error handler"
        assert "localStorage.removeItem" not in catch_match.group(1)
        assert "saved on this device" in catch_match.group(1)


# ── Brand Compliance ─────────────────────────────────────────


class TestBrandCompliance:
    def test_no_border_radius(self, intake_css):
        for m in re.finditer(r"border-radius:\s*([^;!]+)", intake_css):
            assert m.group(1).strip() == "0", f"Non-zero border-radius: {m.group(0)}"

    def test_no_box_shadow(self, intake_css):
        for m in re.finditer(r"box-shadow:\s*([^;]+)", intake_css):
            value = m.group(1).strip().replace(" !important", "")
            assert value == "none", f"Non-none box-shadow: {m.group(0)}"

    def test_no_bounce_easing(self, intake_css):
        assert "bounce" not in intake_css.lower()
        assert "spring" not in intake_css.lower()

    def test_no_entrance_animations(self, intake_css):
        assert "@keyframes" not in intake_css

    def test_no_opacity_transition(self, intake_css):
        assert "transition: opacity" not in intake_css
        assert "transition:opacity" not in intake_css

    def test_uses_brand_tokens(self, intake_css):
        assert "var(--gl-" in intake_css
        assert "var(--gl-font-" in intake_css

    def test_responsive_breakpoint(self, intake_css):
        assert "640px" in intake_css

    def test_correct_class_prefix(self, intake_css):
        """Every BASE class must carry the gl- prefix. Chained state
        modifiers are generic, reused site-wide unprefixed, and exempt."""
        exempt_modifiers = {"active", "accept", "visible", "open", "hidden", "info", "error"}
        leading = re.findall(r"(?<![\w.-])\.([a-zA-Z][\w-]*)", intake_css)
        for cls in set(leading):
            if cls in exempt_modifiers:
                continue
            assert cls.startswith("gl-"), f"Non gl- prefixed class in intake CSS: .{cls}"


# ── Tokens Are Real ────────────────────────────────────────────


class TestCssTokenValidation:
    def test_all_var_refs_defined(self, intake_css):
        tokens_css = TOKENS_CSS.read_text(encoding="utf-8")
        var_refs = set(re.findall(r'var\((--gl-[a-z0-9-]+)\)', intake_css))
        assert var_refs, "No var(--gl-*) references found — did the generator change?"
        for var_name in var_refs:
            assert var_name in tokens_css, f"Undefined token: {var_name}"


# ── JS Syntax ────────────────────────────────────────────────


class TestJSSyntax:
    def test_js_parses_via_node(self, intake_js):
        js = intake_js.replace("<script>", "").replace("</script>", "")
        result = subprocess.run(
            ["node", "-e", f"new Function({repr(js)})"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"JS syntax error: {result.stderr}"


# ── Footer ───────────────────────────────────────────────────


class TestFooter:
    def test_footer_present(self, intake_html):
        assert "gl-consult-footer" in intake_html
