#!/usr/bin/env python3
"""
XC Ski Labs — Tests for the /consulting/ landing page

Covers wordpress/generate_consulting.py: hero + checkout form (incl.
plan_addon checkbox), two futures, five-frame how-it-works strip, what
I actually look at, what we can cover, plan add-on, bio, fit check,
six-item FAQ, close, footer, CSS quality, and JS quality.

Port of gravel-race-automation/tests/test_consulting.py (Sultanic copy
v2) — same coverage, adapted to this repo's generator naming and to
skier-neutral vocabulary swaps (training not riding, sessions not
rides, skis not bike, ski files not ride files) plus the live race
count from web/race-index.json instead of a hardcoded "750+".

Run: pytest tests/test_consulting.py -v
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
OUTPUT_DIR = PROJECT_ROOT / "output"

sys.path.insert(0, str(WORDPRESS_DIR))

from generate_consulting import (  # noqa: E402
    CONSULTING_PRICE,
    CONSULTING_PRICE_INT,
    CONSULTING_DURATION,
    ADDON_PRICE,
    ADDON_PRICE_INT,
    GA4_ID,
    load_race_count,
    build_nav,
    build_hero,
    build_two_futures,
    build_how_it_works,
    build_what_i_look_at,
    build_what_we_cover,
    build_plan_addon,
    build_who,
    build_fit,
    build_faq,
    build_close,
    build_footer,
    build_css,
    build_page_js,
    build_jsonld,
    generate_page,
)

# Section builders whose output is human-readable copy — the Normie Test and
# other content guards should be checked against these, not the full page
# (which also embeds JS option names like IntersectionObserver's `threshold`).
COPY_SECTION_BUILDERS = [
    build_hero,
    build_two_futures,
    build_how_it_works,
    build_what_i_look_at,
    build_what_we_cover,
    build_plan_addon,
    build_who,
    build_fit,
    build_faq,
    build_close,
]


# ── Fixtures ─────────────────────────────────────────────────


@pytest.fixture(scope="module")
def consulting_html(tmp_path_factory):
    out_dir = tmp_path_factory.mktemp("consulting-out")
    path = generate_page(output_dir=out_dir)
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def consulting_css():
    return build_css()


@pytest.fixture(scope="module")
def consulting_js():
    return build_page_js()


@pytest.fixture(scope="module")
def all_copy():
    return "\n".join(fn() for fn in COPY_SECTION_BUILDERS)


def _visible_text(html_doc: str) -> str:
    no_script = re.sub(r"<script.*?</script>", "", html_doc, flags=re.DOTALL)
    no_style = re.sub(r"<style.*?</style>", "", no_script, flags=re.DOTALL)
    return re.sub(r"<[^>]+>", "", no_style)


# ── Page Generation ──────────────────────────────────────────


class TestPageGeneration:
    def test_generator_runs_clean(self):
        result = subprocess.run(
            [sys.executable, str(WORDPRESS_DIR / "generate_consulting.py"),
             "--output-dir", "/tmp/xl-consulting-test-out"],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, result.stderr

    def test_returns_html(self, consulting_html):
        assert isinstance(consulting_html, str)
        assert "<!DOCTYPE html>" in consulting_html

    def test_has_canonical(self, consulting_html):
        assert 'rel="canonical"' in consulting_html
        assert "/consulting/" in consulting_html

    def test_has_ga4(self, consulting_html):
        assert GA4_ID in consulting_html
        assert "googletagmanager.com" in consulting_html

    def test_has_jsonld(self, consulting_html):
        assert 'application/ld+json' in consulting_html
        assert '"@type":"Service"' in consulting_html

    def test_has_meta_robots(self, consulting_html):
        assert 'name="robots"' in consulting_html
        assert 'content="index, follow"' in consulting_html

    def test_has_meta_description(self, consulting_html):
        assert 'name="description"' in consulting_html

    def test_has_og_tags(self, consulting_html):
        assert 'og:title' in consulting_html
        assert 'og:description' in consulting_html

    def test_has_title(self, consulting_html):
        assert "<title>" in consulting_html
        assert "Consulting" in consulting_html

    def test_price_in_page(self, consulting_html):
        assert CONSULTING_PRICE in consulting_html

    def test_duration_in_page(self, consulting_html):
        assert "60 minutes" in consulting_html

    def test_addon_price_in_page(self, consulting_html):
        assert ADDON_PRICE in consulting_html


# ── Nav ──────────────────────────────────────────────────────


class TestNav:
    def test_nav_consulting_link_active(self):
        nav = build_nav()
        assert 'href="/consulting/"' in nav
        assert 'class="active"' in nav

    def test_footer_consulting_link(self):
        footer = build_footer()
        assert 'href="/consulting/"' in footer

    @pytest.mark.parametrize("relpath", [
        "index.html",
        "coaching/index.html",
        "coaching/apply/index.html",
    ])
    def test_nav_link_present_on_other_pages(self, relpath):
        """The canonical nav (scripts/generate_race_pages.py::build_nav_header)
        must carry the Consulting link on every generated page, not just
        /consulting/ itself."""
        path = OUTPUT_DIR / relpath
        if not path.exists():
            pytest.skip(f"Page not generated: {relpath}")
        html = path.read_text(encoding="utf-8")
        assert 'href="/consulting/"' in html


# ── Hero ─────────────────────────────────────────────────────


class TestHero:
    def test_headline(self):
        hero = build_hero()
        assert "read you can" in hero

    def test_price_displayed(self):
        hero = build_hero()
        assert CONSULTING_PRICE in hero

    def test_checkout_form_present(self):
        hero = build_hero()
        assert 'id="checkout"' in hero
        assert "<form" in hero

    def test_checkout_form_has_name_field(self):
        hero = build_hero()
        assert 'name="name"' in hero
        assert 'type="text"' in hero

    def test_checkout_form_has_email_field(self):
        hero = build_hero()
        assert 'type="email"' in hero
        assert 'name="email"' in hero

    def test_checkout_form_has_submit_button(self):
        hero = build_hero()
        assert CONSULTING_PRICE in hero
        assert 'type="submit"' in hero
        assert 'data-cta="hero_book"' in hero

    def test_checkout_form_has_honeypot(self):
        hero = build_hero()
        assert 'name="_honeypot"' in hero
        assert 'display:none' in hero

    def test_checkout_form_has_addon_checkbox(self):
        hero = build_hero()
        assert 'name="plan_addon"' in hero
        assert 'type="checkbox"' in hero
        assert "custom 12-week plan" in hero
        assert ADDON_PRICE in hero

    def test_button_copy(self):
        hero = build_hero()
        assert "Book the consult" in hero


# ── Two Futures ───────────────────────────────────────────────


class TestTwoFutures:
    def test_section_present(self):
        section = build_two_futures()
        assert 'id="two-futures"' in section
        assert "Two futures" in section

    def test_comparison_ignition(self):
        section = build_two_futures()
        assert "forum" in section.lower()
        assert "Same skis. Same hours." in section

    def test_skier_neutral_vocabulary(self):
        """Cycling-specific 'bike'/'ride' vocabulary must not survive the port."""
        section = build_two_futures()
        assert "bike" not in section.lower()
        assert "the long session you always do" in section


# ── How It Works ─────────────────────────────────────────────


class TestHowItWorks:
    def test_five_frames(self):
        section = build_how_it_works()
        assert section.count("gl-consult-strip-frame") >= 5

    def test_svg_present(self):
        section = build_how_it_works()
        assert "<svg" in section
        assert "gl-consult-strip-svg" in section

    def test_hairline_rail(self):
        section = build_how_it_works()
        assert "gl-consult-strip-rail" in section

    def test_frame_four_emphasised(self):
        section = build_how_it_works()
        assert "gl-consult-strip-frame--emphasis" in section

    def test_captions_present(self):
        section = build_how_it_works()
        assert "Book." in section
        assert "Connect your TrainingPeaks." in section
        assert "Answer twelve questions." in section
        assert "Your read arrives" in section
        assert "written plan of action within 48 hours" in section

    def test_no_var_in_svg_attrs(self):
        """SVG attributes can't resolve var() — must be styled via CSS classes only."""
        section = build_how_it_works()
        svg_match = re.search(r'<svg.*?</svg>', section, re.DOTALL)
        assert svg_match
        assert "var(--" not in svg_match.group(0)


# ── What I Actually Look At ──────────────────────────────────


class TestWhatILookAt:
    def test_section_present(self):
        section = build_what_i_look_at()
        assert 'id="look"' in section
        assert "What I actually look at" in section

    def test_five_bullets(self):
        section = build_what_i_look_at()
        assert section.count("<li>") == 5

    def test_key_points(self):
        section = build_what_i_look_at()
        assert "hard training was actually hard" in section
        assert "climbing, flat, or quietly sliding" in section
        assert "long sessions are getting easier deep in" in section
        assert "zones are built on are still true" in section


# ── What We Can Cover ────────────────────────────────────────


class TestWhatWeCover:
    def test_section_present(self):
        section = build_what_we_cover()
        assert 'id="cover"' in section
        assert "What we can cover" in section

    def test_topics(self):
        section = build_what_we_cover()
        for topic in ["Race selection", "Season planning", "Fuelling", "Race-day execution"]:
            assert topic in section

    def test_gear_topic_is_skis_not_bike(self):
        section = build_what_we_cover()
        assert "Skis and gear choices" in section
        assert "Bike and gear" not in section

    def test_open_invite(self):
        section = build_what_we_cover()
        assert "It probably does" in section


# ── Plan Add-on ───────────────────────────────────────────────


class TestPlanAddon:
    def test_section_present(self):
        section = build_plan_addon()
        assert 'id="plan"' in section
        assert ADDON_PRICE in section

    def test_honest_limits(self):
        section = build_plan_addon()
        assert "one goal event" in section
        assert "twelve weeks" in section
        assert "seven days after the call" in section

    def test_no_jargon(self):
        section = build_plan_addon()
        for bad in ["TSS", "FTP", "CTL", "VO2", "periodization"]:
            assert bad not in section


# ── Who You'll Talk To ───────────────────────────────────────


class TestWho:
    def test_bio_section_present(self):
        bio = build_who()
        assert 'id="who"' in bio

    def test_bio_has_name(self):
        bio = build_who()
        assert "Matti" in bio

    def test_bio_has_credentials(self):
        bio = build_who()
        assert "TrainingPeaks" in bio
        assert "100+" in bio

    def test_bio_has_live_race_count(self):
        """The race count must be read live from web/race-index.json, not
        hardcoded — this is the same stale-count trap the Roadie Labs port
        of this page guards against."""
        bio = build_who()
        assert str(load_race_count()) in bio
        assert "cross-country ski races" in bio

    def test_bio_drops_mile_80_anecdote(self):
        """The cycling-specific 'blown up at mile 80' anecdote must be
        replaced with a skier-neutral sentence about racing endurance
        events, per the port spec."""
        bio = build_who()
        assert "mile 80" not in bio
        assert "endurance events" in bio

    def test_bio_section_title(self):
        bio = build_who()
        assert "Who you" in bio
        assert "talk to" in bio

    def test_bio_in_full_page(self, consulting_html):
        assert 'id="who"' in consulting_html
        assert "Matti" in consulting_html


# ── Is This For You ──────────────────────────────────────────


class TestFit:
    def test_section_present(self):
        section = build_fit()
        assert 'id="fit"' in section
        assert "Is this for you?" in section

    def test_for_and_not_for(self):
        section = build_fit()
        assert "For you if" in section
        assert "Not for you if" in section
        assert "goal event and real questions" in section
        assert "pep talk" in section


# ── FAQ ──────────────────────────────────────────────────────


class TestFAQ:
    def test_six_questions(self):
        faq = build_faq()
        assert faq.count("gl-consult-faq-item") == 6

    def test_accordion_buttons(self):
        faq = build_faq()
        assert faq.count('aria-expanded="false"') == 6

    def test_key_questions(self):
        faq = build_faq()
        assert "What happens after I pay?" in faq
        assert "I don" in faq and "TrainingPeaks" in faq
        assert "Do I have to share data?" in faq
        assert "Can I add the plan later?" in faq

    def test_no_tp_question_uses_ski_files(self):
        faq = build_faq()
        assert "ski files" in faq
        assert "ride files" not in faq

    def test_privacy_sentence(self):
        faq = build_faq()
        assert "What happens to my data?" in faq
        assert "deleted on request" in faq
        assert "aren" in faq and "shared or sold" in faq


# ── Close ────────────────────────────────────────────────────


class TestClose:
    def test_cta_present(self):
        cta = build_close()
        assert "Less than a race entry" in cta
        assert 'data-cta="final_book"' in cta

    def test_close_line_verbatim(self):
        cta = build_close()
        assert "Less than a race entry. More useful than the forum." in cta

    def test_final_cta_scrolls_to_form(self):
        cta = build_close()
        assert 'href="#checkout"' in cta

    def test_price_summary(self):
        cta = build_close()
        assert CONSULTING_PRICE in cta

    def test_no_dns_reference(self):
        cta = build_close()
        assert "DNS" not in cta

    def test_no_coffee_cliche(self):
        cta = build_close()
        lower = cta.lower()
        assert "coffee" not in lower
        assert "latte" not in lower

    def test_quiet_clause(self):
        cta = build_close()
        assert "every week" in cta
        assert 'href="https://xcskilabs.com/coaching/"' in cta

    def test_quiet_clause_no_credit_claim(self):
        cta = build_close()
        assert "credit" not in cta.lower()


# ── Footer ───────────────────────────────────────────────────


class TestFooter:
    def test_footer_present(self):
        footer = build_footer()
        assert "gl-consult-footer" in footer
        assert "XC Ski Labs" in footer


# ── No Testimonials ────────────────────────────────────────────


class TestNoTestimonials:
    def test_no_blockquote(self, consulting_html):
        assert "<blockquote" not in consulting_html.lower()

    def test_no_testimonial_section(self, consulting_html):
        assert "testimonial" not in consulting_html.lower()
        assert "What Athletes Say" not in consulting_html

    def test_no_removed_names(self, consulting_html):
        for name in ["Andrew T.", "Jen H.", "Katie B."]:
            assert name not in consulting_html


# ── CSS Quality ──────────────────────────────────────────────


class TestCSSQuality:
    def test_no_border_radius(self, consulting_css):
        for m in re.finditer(r"border-radius:\s*([^;!]+)", consulting_css):
            assert m.group(1).strip() == "0", f"Non-zero border-radius: {m.group(0)}"

    def test_no_box_shadow(self, consulting_css):
        for m in re.finditer(r"box-shadow:\s*([^;]+)", consulting_css):
            value = m.group(1).strip().replace(" !important", "")
            assert value == "none", f"Non-none box-shadow: {m.group(0)}"

    def test_uses_brand_tokens(self, consulting_css):
        assert "var(--gl-" in consulting_css
        assert "var(--gl-font-" in consulting_css

    def test_css_prefix(self, consulting_css):
        """Every BASE class must carry the gl- prefix. Chained state
        modifiers are generic, reused site-wide unprefixed, and exempt."""
        exempt_modifiers = {"active", "accept", "visible", "open"}
        leading = re.findall(r"(?<![\w.-])\.([a-zA-Z][\w-]*)", consulting_css)
        for cls in set(leading):
            if cls in exempt_modifiers:
                continue
            assert cls.startswith("gl-"), f"Non gl- prefixed class in consulting CSS: .{cls}"

    def test_responsive_breakpoint(self, consulting_css):
        assert "768px" in consulting_css

    def test_no_opacity_transition(self, consulting_css):
        assert "transition: opacity" not in consulting_css
        assert "transition:opacity" not in consulting_css

    def test_no_bounce_easing(self, consulting_css):
        assert "bounce" not in consulting_css.lower()
        assert "spring" not in consulting_css.lower()

    def test_no_entrance_animations(self, consulting_css):
        assert "@keyframes" not in consulting_css


# ── Brand Tokens Are Real ──────────────────────────────────────


class TestCssTokenValidation:
    def test_all_var_refs_defined(self, consulting_css):
        """Every var(--gl-*) used in the consulting CSS must exist in
        tokens/tokens.css."""
        tokens_css = TOKENS_CSS.read_text(encoding="utf-8")
        var_refs = set(re.findall(r'var\((--gl-[a-z0-9-]+)\)', consulting_css))
        assert var_refs, "No var(--gl-*) references found — did the generator change?"
        for var_name in var_refs:
            assert var_name in tokens_css, f"Undefined token: {var_name}"


# ── JS Quality ───────────────────────────────────────────────


class TestJSQuality:
    def test_faq_accordion(self, consulting_js):
        assert "gl-consult-faq-q" in consulting_js
        assert "classList" in consulting_js

    def test_cta_tracking(self, consulting_js):
        assert "'cta_click'" in consulting_js
        assert "source:'consulting'" in consulting_js
        assert "data-cta" in consulting_js

    def test_scroll_depth(self, consulting_js):
        assert "consulting_scroll_depth" in consulting_js
        assert "IntersectionObserver" in consulting_js
        assert "'who'" in consulting_js
        assert "'faq'" in consulting_js

    def test_intersection_observer_guards_empty_entries(self, consulting_js):
        """Repo pitfall: always check entries.length before entries[0]."""
        assert "if(!entries.length)return;" in consulting_js

    def test_page_view_event(self, consulting_js):
        assert "consulting_page_view" in consulting_js

    def test_checkout_js_has_api_url(self, consulting_js):
        assert "create-consulting-checkout" in consulting_js

    def test_checkout_js_sends_plan_addon(self, consulting_js):
        assert "plan_addon" in consulting_js
        assert "planAddon" in consulting_js

    def test_checkout_js_has_begin_checkout_event(self, consulting_js):
        assert "begin_checkout" in consulting_js
        assert "Consulting Session" in consulting_js

    def test_checkout_js_has_error_handling(self, consulting_js):
        assert "consulting_checkout_error" in consulting_js
        assert "gl-consult-form-message" in consulting_js

    def test_checkout_js_has_smooth_scroll(self, consulting_js):
        assert 'href="#checkout"' in consulting_js
        assert "scrollIntoView" in consulting_js

    def test_js_syntax_valid(self, consulting_js):
        """Validate JS syntax via Node.js."""
        js = consulting_js.replace("<script>", "").replace("</script>", "")
        result = subprocess.run(
            ["node", "-e", f"new Function({repr(js)})"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"JS syntax error: {result.stderr}"


# ── No Product Comparisons ───────────────────────────────────


class TestNoComparisons:
    """The consulting page body content should NOT compare itself to other
    products. Nav/footer links to other products are fine — we only check
    the page sections."""

    def test_no_coaching_price_comparison(self, all_copy):
        assert "$199" not in all_copy
        assert "$299" not in all_copy
        assert "$1,200" not in all_copy

    def test_no_training_plan_price_comparison(self, all_copy):
        """No '/mo' or '/ month'-style training-plan pricing mentioned."""
        assert "/mo" not in all_copy


# ── Normie Test (banned jargon guard) ────────────────────────


class TestNormieTest:
    """No TSS/FTP/CTL/VO2max/threshold/periodization anywhere in the copy.
    Checked against section-builder output, not the full page — the full
    page also contains legitimate non-copy uses like the
    IntersectionObserver `threshold` option in inline JS."""

    BANNED_TERMS = ["TSS", "FTP", "CTL", "VO2max", "VO2", "periodization", "power curve"]

    def test_no_banned_jargon(self, all_copy):
        for term in self.BANNED_TERMS:
            assert term not in all_copy, f"Banned jargon '{term}' found in copy"

    def test_no_bare_threshold_word(self, all_copy):
        assert "threshold" not in all_copy.lower()
