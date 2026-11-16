"""XC Ski Labs Weekly sign-up: the form, the /weekly/ page and the homepage band.

A sign-up posts to the shared lead-intake Worker with
source=newsletter_subscribe and brand=xcskilabs. Success shows only after a
2xx; data never goes through innerHTML.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import newsletter_signup as ns  # noqa: E402
from wordpress import generate_weekly  # noqa: E402


@pytest.fixture(scope="module")
def form():
    return ns.newsletter_form_html("homepage")


@pytest.fixture(scope="module")
def page():
    return generate_weekly.generate_html()


def test_posts_xc_brand_and_newsletter_source_to_the_worker(form):
    assert "https://fueling-lead-intake.gravelgodcycling.workers.dev" in form
    assert "brand:'xcskilabs'" in form
    assert "source:'newsletter_subscribe'" in form
    assert "brand:'gravelgod'" not in form


def test_success_only_after_a_2xx(form):
    then = form.index(".then(function(r){")
    assert form.index("if(!r.ok) throw", then) < form.index("ok.textContent", then)
    assert ".catch(function(){" in form


def test_messages_use_textcontent_never_innerhtml(form):
    assert "innerHTML" not in form
    assert "textContent" in form


def test_honeypot_and_accessible_label(form):
    assert 'name="website"' in form and 'tabindex="-1"' in form
    assert 'for="xc-newsletter-email-homepage"' in form
    assert 'id="xc-newsletter-email-homepage"' in form


@pytest.mark.parametrize("bad", ["Home Page", "", "x" * 40, "a<b"])
def test_placement_is_validated(bad):
    with pytest.raises(ValueError):
        ns.newsletter_form_html(bad)


def test_js_strings_are_escaped():
    assert ns._js_str("it's <b>") == "it\\'s \\x3cb\\x3e"


def test_weekly_page_is_canonical_with_consent_and_form(page):
    assert '<link rel="canonical" href="https://xcskilabs.com/weekly/">' in page
    assert "xl_consent" in page or "xlAnalyticsStart" in page
    assert 'data-placement="weekly_page"' in page
    assert "<h1>XC Ski Labs Weekly</h1>" in page


def test_weekly_page_copy_is_first_person_and_never_mentions_ai(page):
    visible = re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", page, flags=re.S)
    for banned in (r"\bAI\b", r"\bMatti\b", r"\bMatt\b", r"\bcoach\b", r"\bClaude\b", r"\bGPT\b",
                   r"automat", r"generat", r"algorithm"):
        assert not re.search(banned, visible), banned
    assert "my take" in visible.lower() or "what I make of it" in visible


def test_touch_targets_and_phone_layout():
    css = ns.newsletter_css()
    assert "min-height: 56px" in css
    assert "@media (max-width: 600px)" in css and "flex-direction: column" in css


def test_homepage_carries_the_band_and_footer_link():
    src = (ROOT / "scripts" / "generate_homepage.py").read_text()
    assert 'newsletter_form_html("homepage")' in src
    assert '<a href="/weekly/" class="footer-link">Weekly</a>' in src
    assert "newsletter_css()" in src


def test_weekly_ships_with_sitemap_deploy_and_preflight():
    assert '{domain}/weekly/' in (ROOT / "scripts" / "generate_sitemap.py").read_text()
    deploy = (ROOT / "scripts" / "deploy.py").read_text()
    assert '("Weekly", sync_weekly)' in deploy and '"--sync-weekly"' in deploy
    assert '"weekly"' in (ROOT / "scripts" / "preflight.py").read_text()
