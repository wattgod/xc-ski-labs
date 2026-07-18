#!/usr/bin/env python3
"""
XC Ski Labs — Tests for the /coaching/ landing page ("The Dossier")

Covers wordpress/generate_coaching.py: hero, five numbered terms, three
service tiers (monthly billing, no setup fee), fit check, seven-item
FAQ, dark application close, mobile sticky CTA, GA4 + consent, and the
nav retarget from /coaching/apply/ to /coaching/ across the site.

Modeled on gravel-race-automation/tests/test_coaching.py and this
repo's tests/test_new_features.py::TestCoachingForm conventions.

Run: pytest tests/test_coaching_page.py -v
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORDPRESS_DIR = PROJECT_ROOT / "wordpress"
OUTPUT_DIR = PROJECT_ROOT / "output"

sys.path.insert(0, str(WORDPRESS_DIR))

from generate_coaching import (  # noqa: E402
    APPLY_URL,
    GA4_ID,
    SITE_BASE_URL,
    build_nav,
    build_footer,
    build_hero,
    build_terms,
    build_tiers,
    build_fit,
    build_faq,
    build_close,
    build_mobile_sticky_cta,
    build_cookie_consent,
    build_page_js,
    build_jsonld,
    build_css,
    generate_page,
)


# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def coaching_html(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("coaching-out")
    path = generate_page(output_dir=out_dir)
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def coaching_css():
    return build_css()


def _visible_text(html_doc: str) -> str:
    """Strip <script>...</script> and <style>...</style> blocks, then
    strip remaining HTML tags — leaving only what a reader actually sees.
    """
    no_script = re.sub(r"<script.*?</script>", "", html_doc, flags=re.DOTALL)
    no_style = re.sub(r"<style.*?</style>", "", no_script, flags=re.DOTALL)
    return re.sub(r"<[^>]+>", "", no_style)


# ── Page generation ──────────────────────────────────────────────


class TestPageGeneration:
    def test_generator_runs_clean(self):
        result = subprocess.run(
            [sys.executable, str(WORDPRESS_DIR / "generate_coaching.py")],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"generate_coaching.py failed: {result.stderr[-500:]}"
        assert (OUTPUT_DIR / "coaching" / "index.html").exists()

    def test_returns_html(self, coaching_html):
        assert "<!DOCTYPE html>" in coaching_html

    def test_has_canonical(self, coaching_html):
        assert 'rel="canonical"' in coaching_html
        assert f"{SITE_BASE_URL}/coaching/" in coaching_html

    def test_has_robots_index_follow(self, coaching_html):
        assert 'name="robots"' in coaching_html
        assert 'content="index, follow"' in coaching_html

    def test_has_meta_description(self, coaching_html):
        assert 'name="description"' in coaching_html

    def test_has_title(self, coaching_html):
        assert "<title>" in coaching_html
        assert "Coaching" in coaching_html


# ── GA4 + consent ────────────────────────────────────────────────


class TestGA4AndConsent:
    def test_ga4_present(self, coaching_html):
        assert GA4_ID in coaching_html
        assert "googletagmanager.com" in coaching_html

    def test_ga4_in_head(self, coaching_html):
        head = coaching_html.split("</head>")[0]
        assert GA4_ID in head

    def test_consent_gated(self, coaching_html):
        assert "xl_consent" in coaching_html

    def test_consent_banner_accept_decline(self, coaching_html):
        assert "gl-coach-cookie-consent" in coaching_html
        assert "Accept" in coaching_html
        assert "Decline" in coaching_html

    def test_consent_sets_cookie(self, coaching_html):
        assert "xl_consent=accepted" in coaching_html
        assert "xl_consent=declined" in coaching_html


# ── JSON-LD ──────────────────────────────────────────────────────


class TestJSONLD:
    def test_has_jsonld(self, coaching_html):
        assert 'application/ld+json' in coaching_html
        assert '"@type":"WebPage"' in coaching_html
        assert '"@type":"Service"' in coaching_html

    def test_jsonld_references_coaching_url(self):
        ld = build_jsonld()
        assert f"{SITE_BASE_URL}/coaching/" in ld

    def test_uses_safe_json_for_script(self):
        """A '</script>' payload must never be able to break out of the
        <script> tag (repo pitfall #4)."""
        from generate_coaching import _safe_json_for_script
        payload = {"a": "</script><script>alert(1)</script>"}
        safe = _safe_json_for_script(payload)
        assert "</script>" not in safe


# ── Hero ─────────────────────────────────────────────────────────


class TestHero:
    def test_hero_id(self):
        assert 'id="hero"' in build_hero()

    def test_hero_h1(self):
        hero = build_hero()
        assert "You could be better than you think." in hero
        assert "That is not encouragement &mdash;" in hero
        assert "it&rsquo;s an observation about people who train alone." in hero

    def test_hero_sub(self):
        hero = build_hero()
        assert "The fix is a human in your corner." in hero
        assert "Not an AI, not a dashboard, not a coach who reads you like a spreadsheet." in hero
        assert "The terms are below." in hero

    def test_hero_cta(self):
        hero = build_hero()
        assert "GET ME IN YOUR CORNER &rarr;" in hero
        assert f'href="{APPLY_URL}"' in hero
        assert 'class="gl-coach-hero-cta"' in hero

    def test_hero_cta_visible_without_scrolling(self, coaching_html):
        """The hero CTA must render inside the hero band itself, not
        require scrolling past other content to reach."""
        hero_band = re.search(
            r'<section class="gl-coach-band gl-coach-hero" id="hero">.*?</section>',
            coaching_html, re.DOTALL,
        )
        assert hero_band is not None
        assert "gl-coach-hero-cta" in hero_band.group(0)

    def test_hero_cta_no_underline(self, coaching_css):
        assert ".gl-coach-hero-cta {" in coaching_css
        block = re.search(r"\.gl-coach-hero-cta\s*\{[^}]*\}", coaching_css)
        assert block is not None
        assert "text-decoration: none;" in block.group(0)

    def test_no_file_strip(self, coaching_html):
        assert "TERMS OF WORK" not in coaching_html
        assert "COURSES ON FILE" not in coaching_html


# ── Terms — five numbered clauses ───────────────────────────────


class TestTerms:
    def test_terms_id(self):
        assert 'id="terms"' in build_terms()

    def test_five_clauses(self):
        t = build_terms()
        assert t.count('class="gl-coach-term"') == 5

    def test_clause_numbers(self):
        t = build_terms()
        for n in ("01", "02", "03", "04", "05"):
            assert f'<div class="gl-coach-term-num">{n}</div>' in t

    def test_clause_titles(self):
        t = build_terms()
        for title in (
            "Every file, read by a person",
            "The patterns you can&rsquo;t see",
            "The plan moves when your life does",
            "The truth, on schedule",
            "Involvement is the only variable",
        ):
            assert title in t

    def test_blindspot_sentence(self):
        t = build_terms()
        assert (
            "Every athlete is their own worst blindspot: too fresh to rest, "
            "too stubborn to taper, too close to their own data to see the "
            "shape of it." in t
        )
        assert "Seeing it is the job." in t


# ── Tiers ────────────────────────────────────────────────────────


class TestTiers:
    def test_tiers_id(self):
        assert 'id="tiers"' in build_tiers()

    def test_three_tier_columns(self):
        tiers = build_tiers()
        assert tiers.count('class="gl-coach-tier-col"') == 3
        assert "Min" in tiers
        assert "Mid" in tiers
        assert "Max" in tiers

    def test_prices_and_monthly_interval(self):
        tiers = build_tiers()
        assert "$199" in tiers
        assert "$299" in tiers
        assert "$1,200" in tiers
        assert tiers.count("/ MONTH") == 3
        assert "/ 4 WEEKS" not in tiers

    def test_get_started_links(self):
        tiers = build_tiers()
        assert tiers.count("GET STARTED") == 3
        assert f"{APPLY_URL}?tier=min" in tiers
        assert f"{APPLY_URL}?tier=mid" in tiers
        assert f"{APPLY_URL}?tier=max" in tiers

    def test_no_setup_fee(self, coaching_html):
        assert "setup fee" not in coaching_html.lower()
        assert "$99" not in coaching_html

    def test_disclaimer(self):
        tiers = build_tiers()
        assert "skipped workouts" in tiers
        assert "24 hours" in tiers

    def test_min_tier_features(self):
        tiers = build_tiers()
        for item in (
            "Weekly training review", "File analysis", "Quarterly strategy calls",
            "Structured workouts for your watch or ski erg",
            "Race-day nutrition plan", "Custom training guide",
        ):
            assert item in tiers, f"Missing Min tier feature: {item}"
        assert "Structured workouts for your trainer or head unit" not in tiers

    def test_mid_tier_features(self):
        tiers = build_tiers()
        for item in (
            "Everything in Min", "Detailed training-file analysis",
            "Every-4-week strategy calls", "Weekly plan adjustments",
            "Direct message access", "Blindspot detection",
        ):
            assert item in tiers, f"Missing Mid tier feature: {item}"
        assert "Detailed power-file analysis" not in tiers

    def test_max_tier_features(self):
        tiers = build_tiers()
        for item in (
            "Everything in Mid", "Daily file review", "On-demand calls",
            "Race-week strategy", "Multi-race season planning", "Priority response",
        ):
            assert item in tiers, f"Missing Max tier feature: {item}"

    def test_no_animation_on_tiers(self):
        assert "data-animate" not in build_tiers()


# ── Fit ──────────────────────────────────────────────────────────


class TestFit:
    def test_fit_id(self):
        assert 'id="fit"' in build_fit()

    def test_yes_no_headings(self):
        f = build_fit()
        assert "Coaching is for you if:" in f
        assert "It isn&rsquo;t:" in f

    def test_yes_list(self):
        f = build_fit()
        for item in (
            "You&rsquo;ll do the training when the thinking is done right",
            "You have a race and a reason",
            "You&rsquo;re ready to be honest about your habits",
            "You want a plan smarter than the one you&rsquo;d build alone",
        ):
            assert item in f

    def test_no_list(self):
        f = build_fit()
        for item in (
            "Accountability texts when you skip a Tuesday",
            "Validation dressed up as feedback",
            "A rescue for a race that&rsquo;s next week",
            "A substitute for doing the work",
        ):
            assert item in f

    def test_eight_list_items(self):
        f = build_fit()
        assert f.count("<li>") == 8


# ── FAQ ──────────────────────────────────────────────────────────


class TestFAQ:
    def test_faq_id(self):
        assert 'id="faq"' in build_faq()

    def test_seven_questions(self):
        f = build_faq()
        assert f.count('class="gl-coach-faq-item"') == 7

    def test_power_meter_question_replaced(self):
        f = build_faq()
        assert "Do I need a power meter?" not in f
        assert "What data do I need?" in f
        assert "A watch with heart rate is plenty." in f
        assert "Every workout carries effort-based targets you can train by feel." in f

    def test_setup_fee_question_removed(self):
        f = build_faq()
        assert "$99 setup fee" not in f
        assert "setup fee" not in f.lower()

    def test_cancel_anytime_says_monthly_cycle(self):
        f = build_faq()
        assert "Can I cancel anytime?" in f
        assert "monthly cycle" in f
        assert "4-week cycle" not in f

    def test_accordion_aria(self):
        f = build_faq()
        assert 'aria-expanded' in f
        assert 'role="button"' in f
        assert 'aria-controls="gl-coach-faq-ans-' in f


# ── Application close ────────────────────────────────────────────


class TestClose:
    def test_final_cta_id(self):
        assert 'id="final-cta"' in build_close()

    def test_dark_band(self):
        assert "gl-coach-band--dark" in build_close()

    def test_kicker(self):
        assert "APPLICATION" in build_close()

    def test_close_line(self):
        c = build_close()
        assert "Ten minutes of honest answers. I read every one myself." in c
        assert (
            "You&rsquo;ll hear from me within 48 hours &mdash; including "
            "if I don&rsquo;t think coaching is what you need." in c
        )

    def test_cta(self):
        c = build_close()
        assert "GET ME IN YOUR CORNER &rarr;" in c
        assert f'href="{APPLY_URL}"' in c

    def test_no_contact_line(self, coaching_html):
        """No verified receiving mailbox on xcskilabs.com — the
        'Questions first?' close-line contact must be omitted entirely."""
        assert "Questions first?" not in coaching_html
        assert "coach@xcskilabs.com" not in coaching_html
        assert "mailto:coach@" not in coaching_html


# ── Mobile sticky CTA ────────────────────────────────────────────


class TestMobileStickyCTA:
    def test_sticky_cta_present(self, coaching_html):
        assert "gl-coach-sticky-cta" in coaching_html

    def test_sticky_cta_link(self):
        sticky = build_mobile_sticky_cta()
        assert "GET ME IN YOUR CORNER &rarr;" in sticky
        assert f'href="{APPLY_URL}"' in sticky

    def test_sticky_cta_page_bottom_padding(self, coaching_css):
        """Repo pitfall #32: without padding-bottom on the page, the
        sticky CTA overlaps the footer on short pages."""
        assert "gl-coach-page" in coaching_css
        assert "padding-bottom: 80px;" in coaching_css


# ── Nav / Footer / CTAs ──────────────────────────────────────────


class TestNavAndCTAs:
    def test_nav_coaching_link_and_active(self):
        nav = build_nav()
        assert f'href="/coaching/" class="active">Coaching</a>' in nav

    def test_footer_coaching_link(self):
        footer = build_footer()
        assert 'href="/coaching/">Coaching</a>' in footer

    def test_apply_url_constant(self):
        assert APPLY_URL == "/coaching/apply/"

    def test_all_ctas_point_to_apply(self, coaching_html):
        """Hero, all three tier CTAs, close, and sticky all point at
        /coaching/apply/ — never at /coaching/ (which would self-link)."""
        assert coaching_html.count(f'href="{APPLY_URL}"') >= 3  # hero, close, sticky
        assert f'{APPLY_URL}?tier=min' in coaching_html
        assert f'{APPLY_URL}?tier=mid' in coaching_html
        assert f'{APPLY_URL}?tier=max' in coaching_html


# ── Visual / brand compliance ────────────────────────────────────


class TestBrandCompliance:
    def test_no_border_radius(self, coaching_css):
        assert "border-radius: 0" in coaching_css
        # No non-zero border-radius declarations anywhere.
        for m in re.finditer(r"border-radius:\s*([^;!]+)", coaching_css):
            assert m.group(1).strip() == "0", f"Non-zero border-radius: {m.group(0)}"

    def test_no_box_shadow(self, coaching_css):
        for m in re.finditer(r"box-shadow:\s*([^;]+)", coaching_css):
            value = m.group(1).strip().replace(" !important", "")
            assert value == "none", f"Non-none box-shadow: {m.group(0)}"

    def test_no_images(self, coaching_html):
        body = coaching_html.split("<body>", 1)[1]
        assert "<img" not in body.lower()

    def test_uses_editorial_and_data_fonts(self, coaching_css):
        assert "var(--gl-font-editorial)" in coaching_css
        assert "var(--gl-font-data)" in coaching_css

    def test_strictly_monochrome_no_swix_red_usage(self, coaching_css):
        """The tokens.css file (embedded wholesale) declares
        --gl-swix-red as a custom property — that's unavoidable
        boilerplate. What must never happen is this page's own CSS
        actually *using* var(--gl-swix-red)."""
        assert "var(--gl-swix-red)" not in coaching_css

    def test_strictly_monochrome_no_klister_usage(self, coaching_css):
        assert "var(--gl-klister)" not in coaching_css

    def test_strictly_monochrome_no_wax_colors_usage(self, coaching_css):
        for token in ("--gl-wax-green", "--gl-wax-blue", "--gl-wax-violet"):
            assert f"var({token})" not in coaching_css

    def test_correct_class_prefix(self, coaching_css):
        """Every BASE class must carry the gl- prefix. Chained state
        modifiers (e.g. `.gl-coach-cookie-btn.accept`,
        `a.active`) are generic, reused site-wide unprefixed, and are
        exempt — only the leading class of each compound selector is
        checked."""
        exempt_modifiers = {"active", "accept", "visible", "open"}
        # Leading class of a compound selector: a dot not itself preceded
        # by a class-name character (word char or another class boundary).
        leading = re.findall(r"(?<![\w.-])\.([a-zA-Z][\w-]*)", coaching_css)
        for cls in set(leading):
            if cls in exempt_modifiers:
                continue
            assert cls.startswith("gl-"), f"Non gl- prefixed class in coaching CSS: .{cls}"


# ── No animations ────────────────────────────────────────────────


class TestNoAnimations:
    def test_no_data_animate(self, coaching_html):
        assert "data-animate" not in coaching_html

    def test_no_keyframes(self, coaching_css):
        assert "@keyframes" not in coaching_css

    def test_no_hidden_by_default_opacity(self, coaching_css):
        assert "opacity: 0" not in coaching_css


# ── No testimonials ──────────────────────────────────────────────


class TestNoTestimonials:
    def test_no_blockquote(self, coaching_html):
        assert "<blockquote" not in coaching_html.lower()

    def test_no_testimonial_markup(self, coaching_html):
        assert "testimonial" not in coaching_html.lower()


# ── Restraint / banned-word guard ────────────────────────────────


BANNED_VISIBLE_TEXT = [
    "unlock",
    "transform",
    "crush",
    "TERMS OF WORK",
    "COURSES ON FILE",
    "$14.95",
    "suffer smarter",
]


class TestRestraintGuard:
    @pytest.mark.parametrize("phrase", BANNED_VISIBLE_TEXT)
    def test_banned_phrase_absent_from_visible_text(self, coaching_html, phrase):
        visible = _visible_text(coaching_html)
        assert phrase.lower() not in visible.lower(), (
            f"Banned phrase found in visible coaching page text: {phrase!r}"
        )

    def test_no_defensive_messaging(self, coaching_html):
        lower = coaching_html.lower()
        assert "no sponsors" not in lower
        assert "not sponsored" not in lower
        assert "no affiliates" not in lower


# ── Site-wide nav retarget ───────────────────────────────────────
# Every generator's nav-menu "Coaching" link must point at /coaching/
# now that the landing page exists. Explicit apply/CTA buttons (e.g.
# "Apply", "Coaching application") and the intake form's own post-
# submit redirect are exempt and must keep pointing at /coaching/apply/.


class TestSiteWideNavRetarget:
    def _generated(self, relpath: str) -> str:
        path = OUTPUT_DIR / relpath
        if not path.exists():
            pytest.skip(f"Page not generated: {relpath}")
        return path.read_text(encoding="utf-8")

    @pytest.mark.parametrize("relpath", [
        "vasaloppet/index.html",
        "index.html",
        "about/index.html",
        "training-plans/index.html",
        "questionnaire/index.html",
        "coaching/apply/index.html",
        "search/index.html",
    ])
    def test_nav_coaching_link_is_landing_page(self, relpath):
        html = self._generated(relpath)
        assert 'href="/coaching/">Coaching</a>' in html or \
               'href="/coaching/" class="active">Coaching</a>' in html, (
            f"{relpath}: nav 'Coaching' link does not point at /coaching/"
        )

    def test_about_cta_still_points_to_apply(self):
        html = self._generated("about/index.html")
        assert 'href="/coaching/apply/">Coaching application</a>' in html

    def test_homepage_apply_button_still_points_to_apply(self):
        html = self._generated("index.html")
        assert 'class="gl-rung-btn apply" href="/coaching/apply/">Apply</a>' in html

    def test_apply_form_redirect_unchanged(self):
        html = self._generated("coaching/apply/index.html")
        assert 'value="https://xcskilabs.com/coaching/apply/?submitted=true"' in html
