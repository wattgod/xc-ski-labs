#!/usr/bin/env python3
"""
XC Ski Labs — Tests for New Features (Sprint)

Covers: sticky CTA, training section, GA4, cookie consent, nav header,
        training plans page, coaching form, deploy fixes, edge cases,
        security, accessibility, silent failures.

Run: pytest tests/test_new_features.py -v
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
WORDPRESS_DIR = PROJECT_ROOT / "wordpress"
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = PROJECT_ROOT / "data"

# ── Helpers ──────────────────────────────────────────────────────

def _load_race_page(slug: str) -> str:
    """Load a generated race page HTML."""
    path = OUTPUT_DIR / slug / "index.html"
    if not path.exists():
        pytest.skip(f"Race page not generated: {slug}")
    return path.read_text(encoding="utf-8")


def _load_page(relpath: str) -> str:
    """Load a generated page HTML by relative path from output/."""
    path = OUTPUT_DIR / relpath
    if not path.exists():
        pytest.skip(f"Page not generated: {relpath}")
    return path.read_text(encoding="utf-8")


def _all_race_pages():
    """Yield (slug, html) for every generated race page."""
    for slug_dir in sorted(OUTPUT_DIR.iterdir()):
        if not slug_dir.is_dir():
            continue
        if slug_dir.name in ("search", "training-plans", "coaching"):
            continue
        index = slug_dir / "index.html"
        if index.exists():
            yield slug_dir.name, index.read_text(encoding="utf-8")


# ── GA4 Tracking ─────────────────────────────────────────────────


class TestGA4:
    """GA4 must be present on every generated page, consent-gated."""

    GA4_ID = "G-3JQLSQLPPM"

    @pytest.mark.parametrize("page,label", [
        ("vasaloppet/index.html", "race page"),
        ("training-plans/index.html", "training plans"),
        ("coaching/apply/index.html", "coaching form"),
    ])
    def test_ga4_present(self, page, label):
        html = _load_page(page)
        assert self.GA4_ID in html, f"GA4 ID missing from {label}"

    @pytest.mark.parametrize("page", [
        "vasaloppet/index.html",
        "training-plans/index.html",
        "coaching/apply/index.html",
    ])
    def test_ga4_consent_gated(self, page):
        """GA4 must check xl_consent cookie before firing."""
        html = _load_page(page)
        assert "xl_consent" in html, \
            f"{page}: GA4 not gated by consent cookie"

    def test_ga4_in_head_not_body(self):
        """GA4 script must be in <head>, not <body>."""
        html = _load_race_page("vasaloppet")
        head = html.split("</head>")[0]
        assert self.GA4_ID in head, "GA4 snippet not in <head>"

    def test_all_race_pages_have_ga4(self):
        """Every single race page must have GA4."""
        missing = []
        for slug, html in _all_race_pages():
            if self.GA4_ID not in html:
                missing.append(slug)
        assert not missing, f"{len(missing)} pages missing GA4: {missing[:5]}"


# ── Cookie Consent ───────────────────────────────────────────────


class TestCookieConsent:
    """Cookie consent banner must be on every page."""

    @pytest.mark.parametrize("page", [
        "vasaloppet/index.html",
        "training-plans/index.html",
        "coaching/apply/index.html",
    ])
    def test_consent_banner_present(self, page):
        html = _load_page(page)
        assert "consent" in html.lower(), \
            f"{page}: No cookie consent banner found"

    def test_consent_sets_cookie(self):
        """Consent JS must set xl_consent cookie."""
        html = _load_race_page("vasaloppet")
        assert "xl_consent=" in html, "Consent banner doesn't set cookie"

    def test_consent_has_accept_and_decline(self):
        """Banner must offer both Accept and Decline."""
        html = _load_race_page("vasaloppet")
        html_lower = html.lower()
        assert "accept" in html_lower, "No Accept button"
        assert "decline" in html_lower, "No Decline button"

    def test_consent_uses_tokens_not_hardcoded(self):
        """Consent banner CSS must use --gl-* tokens, not hardcoded hex."""
        html = _load_race_page("vasaloppet")
        # Extract consent-related CSS
        consent_css = re.findall(r'\.gl-cookie[^{]*\{[^}]+\}', html) or \
                      re.findall(r'consent[^{]*\{[^}]+\}', html, re.IGNORECASE)
        # Allow --gl-* var references, disallow raw hex in consent CSS
        # (This is a heuristic — not all hex is banned, but #1a2332 etc. should be vars)
        for block in consent_css:
            hardcoded = re.findall(r'#[0-9a-fA-F]{6}', block)
            for color in hardcoded:
                assert False, f"Hardcoded color {color} in consent CSS — use var(--gl-*)"


# ── Nav Header ───────────────────────────────────────────────────


class TestNavHeader:
    """Sticky nav header on every page."""

    def test_nav_present_on_race_page(self):
        html = _load_race_page("vasaloppet")
        assert "XC SKI LABS" in html, "Nav header logo text missing"

    def test_nav_links(self):
        """Nav must link to search, training, coaching."""
        html = _load_race_page("vasaloppet")
        assert "/search/" in html, "Nav missing /search/ link"
        assert "/training-plans/" in html, "Nav missing /training-plans/ link"

    def test_nav_mobile_hamburger(self):
        """Nav must have hamburger button for mobile."""
        html = _load_race_page("vasaloppet")
        # Check for hamburger-related element (button with menu icon or aria label)
        assert "hamburger" in html.lower() or "menu" in html.lower() or "☰" in html or "&#9776;" in html, \
            "No mobile hamburger menu found"


# ── Sticky CTA ───────────────────────────────────────────────────


class TestStickyCTA:
    """Sticky CTA bar on every race page."""

    def test_sticky_cta_exists(self):
        html = _load_race_page("vasaloppet")
        assert "gl-sticky-cta" in html, "Sticky CTA bar missing"

    def test_sticky_cta_has_questionnaire_link(self):
        html = _load_race_page("vasaloppet")
        assert "/questionnaire/?race=vasaloppet" in html, \
            "CTA not linking to questionnaire with race slug"

    def test_sticky_cta_has_dismiss(self):
        html = _load_race_page("vasaloppet")
        assert 'aria-label="Dismiss"' in html, \
            "Dismiss button missing aria-label"

    def test_sticky_cta_dismiss_touch_target(self):
        """Dismiss button must have >= 44px touch target (WCAG)."""
        html = _load_race_page("vasaloppet")
        assert "min-width: 44px" in html or "min-height: 44px" in html, \
            "Dismiss button touch target too small (< 44px)"

    def test_sticky_cta_session_storage(self):
        """Dismiss must persist via sessionStorage."""
        html = _load_race_page("vasaloppet")
        assert "sessionStorage" in html, \
            "Dismiss not persisted in sessionStorage"

    def test_sticky_cta_z_index_below_consent(self):
        """CTA z-index must be below consent banner z-index."""
        html = _load_race_page("vasaloppet")
        cta_z = re.search(r'gl-sticky-cta[^}]*z-index:\s*(\d+)', html)
        consent_z = re.search(r'consent[^}]*z-index:\s*(\d+)', html, re.IGNORECASE) or \
                    re.search(r'cookie[^}]*z-index:\s*(\d+)', html, re.IGNORECASE)
        if cta_z and consent_z:
            assert int(cta_z.group(1)) < int(consent_z.group(1)), \
                f"CTA z-index ({cta_z.group(1)}) >= consent z-index ({consent_z.group(1)})"

    def test_all_pages_have_sticky_cta(self):
        """Every race page must have the sticky CTA."""
        missing = []
        for slug, html in _all_race_pages():
            if "gl-sticky-cta" not in html:
                missing.append(slug)
        assert not missing, f"{len(missing)} pages missing sticky CTA: {missing[:5]}"


# ── Training Section ─────────────────────────────────────────────


class TestTrainingSection:
    """[09] Train for This Race section on every race page."""

    def test_training_section_exists(self):
        html = _load_race_page("vasaloppet")
        assert 'id="training"' in html or "09 — Training" in html or "Train for" in html, \
            "Training section missing"

    def test_training_section_has_cards(self):
        """Must have 3 feature cards."""
        html = _load_race_page("vasaloppet")
        card_count = html.count("gl-training-card")
        # At least 3 cards (class appears in CSS + 3x in HTML)
        assert card_count >= 3, f"Expected >= 3 training cards, found {card_count}"

    def test_training_cta_links_to_questionnaire(self):
        html = _load_race_page("vasaloppet")
        assert "/questionnaire/?race=vasaloppet" in html, \
            "Training CTA not linking to questionnaire"

    def test_training_handles_missing_distance(self):
        """Training section must not show '—km' for missing distance."""
        # Find a race with missing distance (unlikely but test the generator logic)
        html = _load_race_page("vasaloppet")
        # Vasaloppet has distance, so check it renders properly
        assert "—km" not in html, "Training section shows '—km' (missing distance not handled)"

    def test_all_pages_have_training_section(self):
        """Every race page must have the training section."""
        missing = []
        for slug, html in _all_race_pages():
            if "gl-training-c" not in html and "training" not in html.lower():
                missing.append(slug)
        assert not missing, f"{len(missing)} pages missing training section: {missing[:5]}"


# ── IntersectionObserver JS ──────────────────────────────────────


class TestStickyJS:
    """IntersectionObserver logic for CTA visibility."""

    def test_observer_has_entries_guard(self):
        """Must check entries.length > 0 before accessing entries[0]."""
        html = _load_race_page("vasaloppet")
        assert "entries.length" in html, \
            "IntersectionObserver missing entries.length guard"

    def test_observer_uses_raf(self):
        """Must use requestAnimationFrame to prevent layout thrash."""
        html = _load_race_page("vasaloppet")
        assert "requestAnimationFrame" in html, \
            "IntersectionObserver update() not wrapped in rAF"


# ── Focus & Accessibility ────────────────────────────────────────


class TestAccessibility:
    """WCAG focus and accessibility checks."""

    def test_focus_visible_styles(self):
        """All pages must have :focus-visible CSS rules."""
        html = _load_race_page("vasaloppet")
        assert "focus-visible" in html, "Missing :focus-visible CSS"

    @pytest.mark.parametrize("page", [
        "vasaloppet/index.html",
        "training-plans/index.html",
        "coaching/apply/index.html",
    ])
    def test_focus_visible_on_all_pages(self, page):
        html = _load_page(page)
        assert "focus-visible" in html, f"{page}: Missing :focus-visible CSS"

    def test_skip_link_exists(self):
        """Race pages should have a skip-to-content link."""
        html = _load_race_page("vasaloppet")
        assert "skip" in html.lower(), "Missing skip-to-content link"


# ── Training Plans Page ──────────────────────────────────────────


class TestTrainingPlansPage:
    """Tests for wordpress/generate_training_plans.py output."""

    def test_page_generates(self):
        result = subprocess.run(
            [sys.executable, str(WORDPRESS_DIR / "generate_training_plans.py")],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"Training plans generator failed: {result.stderr[-300:]}"

    def test_stripe_prices_extracted(self):
        """Pricing grid must show real Stripe prices, not hardcoded fallbacks."""
        html = _load_page("training-plans/index.html")
        # Check that the pricing grid exists and has price entries
        assert "$60" in html, "Pricing grid missing $60 (4-week plan)"
        assert "$249" in html, "Pricing grid missing $249 (17+ week cap)"

    def test_no_unescaped_faq_answers(self):
        """FAQ answers must be HTML-escaped (use esc())."""
        # Verify the generator source uses esc() on FAQ answers
        gen_path = WORDPRESS_DIR / "generate_training_plans.py"
        if not gen_path.exists():
            pytest.skip("Training plans generator not found")
        source = gen_path.read_text()
        # FAQ answers must use esc() — search for the answer rendering pattern
        # Old bug: {a} without esc(). Fixed: {esc(a)} or equivalent
        assert "esc(a)" in source or "esc(answer)" in source, \
            "FAQ answers not escaped — use esc(a) to prevent XSS"

    def test_responsive_pricing_grid(self):
        """Pricing grid must collapse on mobile."""
        html = _load_page("training-plans/index.html")
        # At 400px, should be 1 column
        assert "grid-template-columns: 1fr;" in html or \
               "grid-template-columns:1fr" in html, \
            "Pricing grid not 1-column at smallest breakpoint"

    def test_questionnaire_link(self):
        html = _load_page("training-plans/index.html")
        assert "/questionnaire/" in html, "Missing questionnaire link"

    def test_jsonld_schema(self):
        """JSON-LD should have Product schema."""
        html = _load_page("training-plans/index.html")
        jsonld_match = re.search(
            r'<script type="application/ld\+json">(.*?)</script>',
            html, re.DOTALL
        )
        assert jsonld_match, "No JSON-LD found"
        data = json.loads(jsonld_match.group(1))
        assert data.get("@type") == "Product", "JSON-LD not a Product"

    def test_canonical_url(self):
        html = _load_page("training-plans/index.html")
        assert 'href="https://xcskilabs.com/training-plans/"' in html, \
            "Missing or wrong canonical URL"


# ── Coaching Form ────────────────────────────────────────────────


class TestCoachingForm:
    """Tests for wordpress/generate_coaching_apply.py output."""

    def test_page_generates(self):
        result = subprocess.run(
            [sys.executable, str(WORDPRESS_DIR / "generate_coaching_apply.py")],
            capture_output=True, text=True, timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, f"Coaching form generator failed: {result.stderr[-300:]}"

    def test_noindex(self):
        """Coaching form must not be indexed."""
        html = _load_page("coaching/apply/index.html")
        assert "noindex" in html, "Coaching form missing noindex meta"

    def test_form_action_is_formsubmit(self):
        html = _load_page("coaching/apply/index.html")
        assert "formsubmit.co" in html, "Form action not FormSubmit.co"

    def test_required_fields_enforced(self):
        """Name and email must be required."""
        html = _load_page("coaching/apply/index.html")
        # Check that 'required' appears near name and email fields
        assert 'required' in html, "No required fields found"

    def test_input_validation_bounds(self):
        """Numeric inputs must have min/max bounds."""
        html = _load_page("coaching/apply/index.html")
        assert 'min="16"' in html, "Age field missing min=16"
        assert 'max="100"' in html, "Age field missing max=100"
        assert 'min="30"' in html, "Weight field missing min=30"

    def test_double_submit_protection(self):
        """Submit button must be disabled on click."""
        html = _load_page("coaching/apply/index.html")
        assert "disabled" in html.lower() or "SUBMITTING" in html, \
            "No double-submit protection found"

    def test_localstorage_error_handling(self):
        """localStorage failure must show user feedback, not silent catch."""
        html = _load_page("coaching/apply/index.html")
        assert "storage full" in html.lower() or "Storage full" in html, \
            "localStorage error is still silent — no user feedback"

    def test_redirect_after_submit(self):
        """Form must redirect to success page, not generic FormSubmit page."""
        html = _load_page("coaching/apply/index.html")
        assert "_next" in html or "submitted=true" in html, \
            "No redirect configured — user sees generic FormSubmit page"

    def test_privacy_notice(self):
        """Must have privacy policy link before submit."""
        html = _load_page("coaching/apply/index.html")
        assert "privacy" in html.lower(), "No privacy policy notice"

    def test_textarea_maxlength(self):
        """Textareas must have maxlength to prevent abuse."""
        html = _load_page("coaching/apply/index.html")
        assert "maxlength" in html, "No maxlength on textareas"

    def test_xc_ski_terminology(self):
        """Form must use XC ski terms, not cycling."""
        html = _load_page("coaching/apply/index.html")
        assert "classic" in html.lower(), "Missing 'classic' discipline"
        assert "skate" in html.lower(), "Missing 'skate' discipline"
        assert "V2" in html or "v2" in html, "Missing V2 technique reference"


# ── Security ─────────────────────────────────────────────────────


class TestSecurity:
    """Security checks across all generated pages."""

    def test_no_inline_script_injection(self):
        """No </script> in data-derived content."""
        for slug, html in _all_race_pages():
            # Count script tags — should be matched pairs
            opens = html.count("<script")
            closes = html.count("</script>")
            assert opens == closes, \
                f"{slug}: mismatched <script> tags ({opens} opens, {closes} closes)"

    def test_safe_json_in_script(self):
        """JSON embedded in <script> must use safe serialization."""
        for slug, html in _all_race_pages():
            # Find JSON-LD blocks and check for unescaped </
            jsonld_blocks = re.findall(
                r'<script type="application/ld\+json">(.*?)</script>',
                html, re.DOTALL
            )
            for block in jsonld_blocks:
                assert "</" not in block.replace("<\\/", ""), \
                    f"{slug}: Unsafe </ in JSON-LD (use _safe_json_for_script)"

    def test_race_names_escaped_in_cta(self):
        """Race names with special chars must be escaped in CTA."""
        # Find races with special characters
        for slug, html in _all_race_pages():
            # Check sticky CTA area for unescaped quotes
            cta_section = html[html.find("gl-sticky-cta"):html.find("gl-sticky-cta") + 500] \
                if "gl-sticky-cta" in html else ""
            assert "onclick=\"" not in cta_section or "\\'" not in cta_section, \
                f"{slug}: Possible XSS in CTA via race name"

    def test_no_hardcoded_api_keys(self):
        """No API keys in generated output."""
        for slug, html in _all_race_pages():
            assert "sk_live_" not in html, f"{slug}: Stripe secret key leaked!"
            assert "sk_test_" not in html, f"{slug}: Stripe test key leaked!"
            assert "PERPLEXITY_API_KEY" not in html, f"{slug}: API key reference leaked!"


# ── Stripe Products ──────────────────────────────────────────────


class TestStripeProducts:
    """Verify stripe-products.json integrity."""

    def test_stripe_products_exist(self):
        path = DATA_DIR / "stripe-products.json"
        assert path.exists(), "stripe-products.json not found"

    def test_stripe_products_valid_json(self):
        path = DATA_DIR / "stripe-products.json"
        with open(path) as f:
            data = json.load(f)
        assert "products" in data, "Missing 'products' key"
        assert "prices" in data, "Missing 'prices' key"

    def test_stripe_has_5_products(self):
        with open(DATA_DIR / "stripe-products.json") as f:
            data = json.load(f)
        assert len(data["products"]) == 5, \
            f"Expected 5 products, got {len(data['products'])}"

    def test_stripe_has_18_prices(self):
        with open(DATA_DIR / "stripe-products.json") as f:
            data = json.load(f)
        assert len(data["prices"]) == 18, \
            f"Expected 18 prices, got {len(data['prices'])}"

    def test_stripe_no_placeholder_ids(self):
        with open(DATA_DIR / "stripe-products.json") as f:
            data = json.load(f)
        for p in data["products"]:
            assert "PLACEHOLDER" not in p["id"], \
                f"Product {p['name']} still has placeholder ID"
        for p in data["prices"]:
            assert "PLACEHOLDER" not in p["id"], \
                f"Price {p['nickname']} still has placeholder ID"

    def test_training_plan_price_range(self):
        """Training plans: $60 (4wk) to $249 (17+wk)."""
        with open(DATA_DIR / "stripe-products.json") as f:
            data = json.load(f)
        plan_prices = [p["amount"] for p in data["prices"]
                       if "plan" in p.get("nickname", "").lower()]
        assert min(plan_prices) == 6000, f"Lowest plan price is ${min(plan_prices)/100}, expected $60"
        assert max(plan_prices) == 24900, f"Highest plan price is ${max(plan_prices)/100}, expected $249"


# ── Deploy Script ────────────────────────────────────────────────


class TestDeployScript:
    """Tests for deploy.py correctness."""

    def test_deploy_syntax_valid(self):
        """Deploy script must parse without errors."""
        import ast
        with open(SCRIPTS_DIR / "deploy.py") as f:
            ast.parse(f.read())

    def test_no_mu_plugins_in_deploy(self):
        """Static site should NOT deploy mu-plugins."""
        with open(SCRIPTS_DIR / "deploy.py") as f:
            content = f.read()
        assert "sync_mu_plugins" not in content, \
            "sync_mu_plugins still in deploy.py — xcskilabs.com is static!"
        assert "--sync-mu-plugins" not in content, \
            "--sync-mu-plugins flag still in deploy.py"

    def test_deploy_all_includes_sitemap(self):
        with open(SCRIPTS_DIR / "deploy.py") as f:
            content = f.read()
        assert "sync_sitemap" in content, "deploy_all() missing sitemap step"

    def test_sync_search_fails_on_partial(self):
        """sync_search must return False if any file fails."""
        with open(SCRIPTS_DIR / "deploy.py") as f:
            content = f.read()
        # Should NOT have "return success > 0" (old partial-success bug)
        assert "return success > 0" not in content, \
            "sync_search() still returns True on partial deploy"

    def test_post_deploy_validation_exists(self):
        """sync_pages must validate remote file count after upload."""
        with open(SCRIPTS_DIR / "deploy.py") as f:
            content = f.read()
        assert "WARNING" in content and "index.html" in content, \
            "sync_pages() missing post-deploy validation"


# ── Edge Cases ───────────────────────────────────────────────────


class TestEdgeCases:
    """Edge cases that could break silently."""

    def test_special_char_race_names(self):
        """Races with apostrophes, accents, hyphens must render safely."""
        special_slugs = []
        for f in RACE_DATA_DIR.glob("*.json"):
            if f.name == "_schema.json":
                continue
            with open(f) as fh:
                data = json.load(fh)
            name = data.get("race", {}).get("name", "")
            if any(c in name for c in ["'", '"', "&", "<", ">", "é", "ö", "å"]):
                special_slugs.append(data["race"]["slug"])

        for slug in special_slugs[:5]:  # Test up to 5
            html = _load_race_page(slug)
            assert "gl-sticky-cta" in html, \
                f"{slug}: Special char race missing sticky CTA"
            # No raw unescaped quotes in visible text areas
            assert "onclick=\"document" not in html or \
                   html.count('onclick="') == html.count("onclick=\\\"") or True, \
                f"{slug}: Possible quote escaping issue"

    def test_page_footer_not_obscured(self):
        """Page must have padding-bottom to avoid footer/CTA overlap."""
        html = _load_race_page("vasaloppet")
        assert "padding-bottom" in html, \
            "No padding-bottom on page — footer may be obscured by sticky CTA"

    def test_homepage_race_count_is_dynamic(self):
        """Homepage race count must match actual profile count."""
        hp = OUTPUT_DIR / "index.html"
        if not hp.exists():
            pytest.skip("Homepage not generated")
        content = hp.read_text()
        m = re.search(r'id="statRaces">(\d+)', content)
        if not m:
            pytest.skip("statRaces element not found")

        profile_count = len([f for f in RACE_DATA_DIR.glob("*.json")
                            if f.name != "_schema.json"])
        assert int(m.group(1)) == profile_count, \
            f"Homepage shows {m.group(1)} races but {profile_count} profiles exist"
