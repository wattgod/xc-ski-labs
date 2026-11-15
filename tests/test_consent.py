"""Region-aware consent: scripts/consent.py and every page that uses it.

Ported from Gravel God's tests/test_cookie_consent.py (Matti's ruling
2026-11-14: XC adopts Gravel God's consent model, cookie ``xl_consent``),
plus XC checks that every generated page carries the one shared head and
banner and nothing else configures GA4.

wordpress/generate_questionnaire.py is excluded: it is being moved off
FormSubmit in a separate PR and still carries its own consent snippet.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from consent import (  # noqa: E402
    EEA_UK_CH_TIMEZONES,
    GA4_MEASUREMENT_ID,
    get_consent_banner_html,
    get_consent_head_script,
    get_ga4_head,
    requires_explicit_consent,
)

HAS_NODE = shutil.which("node") is not None


def _extract_css(html: str) -> str:
    m = re.search(r"<style>(.*?)</style>", html, re.DOTALL)
    return m.group(1) if m else ""


def _extract_js(html: str) -> str:
    scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    return scripts[-1] if scripts else ""


@pytest.fixture
def banner():
    return get_consent_banner_html()


@pytest.fixture
def css(banner):
    return _extract_css(banner)


@pytest.fixture
def js(banner):
    return _extract_js(banner)


@pytest.fixture
def head():
    return get_consent_head_script()


# ── Head script ────────────────────────────────────────────


class TestHeadScript:
    def test_default_before_config_in_one_block(self, head):
        assert head.count("<script>") == 1
        assert head.index("gtag('consent','default'") < head.index("gtag('config'")

    def test_ad_signals_always_denied(self, head):
        assert "'ad_storage':'denied'" in head
        assert "'ad_user_data':'denied'" in head
        assert "'ad_personalization':'denied'" in head

    def test_wait_for_update(self, head):
        assert "'wait_for_update':500" in head

    def test_cookie_overrides_geo_default(self, head):
        assert "/(^|; )xl_consent=accepted/.test(document.cookie)" in head
        assert "/(^|; )xl_consent=declined/.test(document.cookie)" in head
        assert (
            "xlConsentAccepted?'granted':xlConsentDeclined?'denied':"
            "xlConsentRequiresOptIn?'denied':'granted'"
        ) in head

    def test_unknown_timezone_requires_opt_in(self, head):
        assert "xlConsentRequiresOptIn=!xlConsentTimezoneKnown||" in head

    def test_timezone_list_is_embedded(self, head):
        assert json.dumps(EEA_UK_CH_TIMEZONES, separators=(",", ":")) in head

    def test_measurement_id(self, head):
        assert f"gtag('config','{GA4_MEASUREMENT_ID}')" in head

    def test_ga4_head_loads_gtag_after_defaults(self):
        snippet = get_ga4_head()
        assert snippet.index("gtag('consent','default'") < snippet.index("googletagmanager.com/gtag/js")

    @pytest.mark.skipif(not HAS_NODE, reason="node not installed")
    @pytest.mark.parametrize(
        "timezone, cookie, expected",
        [
            ("America/Denver", "", "granted"),
            ("Europe/Oslo", "", "denied"),
            ("Europe/London", "", "denied"),
            ("Europe/Zurich", "", "denied"),
            ("", "", "denied"),
            ("Europe/Oslo", "xl_consent=accepted", "granted"),
            ("America/Denver", "xl_consent=declined", "denied"),
            ("America/Denver", "other=1; xl_consent=declined", "denied"),
            ("America/Denver", "notxl_consent=declined", "granted"),
        ],
    )
    def test_head_script_behaviour(self, head, timezone, cookie, expected):
        body = head.replace("<script>", "").replace("</script>", "")
        harness = (
            "var calls=[];var window={};var document={cookie:%s};"
            "var dataLayer=[];"
            "var Intl={DateTimeFormat:function(l,o){"
            "if(o&&o.timeZone&&o.timeZone!==%s)throw new RangeError('bad');"
            "return {resolvedOptions:function(){return {timeZone:%s}}}}};"
            "%s\n"
            "var d=dataLayer.filter(function(a){return a[0]==='consent'&&a[1]==='default'})[0][2];"
            "process.stdout.write(d.analytics_storage+'|'+String(window.xlConsentRequiresOptIn));"
        ) % (json.dumps(cookie), json.dumps(timezone), json.dumps(timezone), body)
        result = subprocess.run(["node", "-e", harness], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        assert result.stdout.split("|")[0] == expected


# ── Banner structure ───────────────────────────────────────


class TestBannerStructure:
    def test_dialog_semantics(self, banner):
        assert 'role="dialog"' in banner
        assert 'aria-label="Cookie consent"' in banner
        assert 'aria-describedby="xl-consent-desc"' in banner
        assert 'id="xl-consent-desc"' in banner

    def test_accept_and_decline(self, banner):
        assert 'id="xl-consent-accept"' in banner and ">Accept<" in banner
        assert 'id="xl-consent-decline"' in banner and ">Decline<" in banner
        assert len(re.findall(r"<button[^>]*>", banner)) == 2

    def test_privacy_choices_and_legal_links(self, banner):
        assert 'id="xl-privacy-choices"' in banner
        assert ">Privacy choices<" in banner
        assert 'href="/privacy/"' in banner
        assert 'href="/terms/"' in banner

    def test_banner_copy_is_first_person_and_plain(self, banner):
        text = re.search(r'id="xl-consent-desc">(.*?)</p>', banner).group(1)
        assert text.startswith("I use analytics cookies")
        for banned in ("Matt ", "We ", "AI", "monthly"):
            assert banned not in text

    def test_no_border_radius_or_shadow(self, css):
        assert "border-radius" not in css
        assert "box-shadow" not in css

    def test_colours_are_tokens(self, css):
        assert not re.findall(r"#[0-9a-fA-F]{3,8}\b", css)
        for var in set(re.findall(r"var\((--gl-[\w-]+)\)", css)):
            tokens = (PROJECT_ROOT / "tokens" / "tokens.css").read_text()
            assert f"{var}:" in tokens, var


class TestAccessibility:
    def test_focus_visible(self, css):
        assert "focus-visible" in css

    def test_reduced_motion(self, css):
        idx = css.find("prefers-reduced-motion")
        assert idx >= 0 and "transition:none" in css[idx:]

    def test_touch_targets(self, css):
        assert "min-width:44px;min-height:44px" in css


# ── Banner JS ──────────────────────────────────────────────


class TestBannerJs:
    @pytest.mark.skipif(not HAS_NODE, reason="node not installed")
    def test_js_syntax_valid(self, js):
        result = subprocess.run(
            ["node", "-e", f"new Function({json.dumps(js)})"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0, result.stderr

    def test_cookie_check_uses_prefix_safe_regex(self, js):
        assert "/(^|; )xl_consent=/.test" in js
        assert "indexOf" not in js

    def test_accept_and_decline_update_consent(self, js):
        assert "xl_consent=accepted" in js
        assert "xl_consent=declined" in js
        assert "'analytics_storage':'granted'" in js
        assert "'analytics_storage':'denied'" in js
        assert "typeof gtag==='function'" in js

    def test_accept_does_not_reconfigure(self, js):
        assert "gtag('config'" not in js
        assert "gtag('js'" not in js

    def test_auto_show_only_for_strict_geo_without_cookie(self, js):
        assert "window.xlConsentRequiresOptIn!==false" in js

    def test_privacy_choices_opens_banner(self, js):
        assert "e.preventDefault();showBanner()" in js

    def test_cookie_flags(self, js):
        sets = re.findall(r"document\.cookie='[^']*'", js)
        assert len(sets) == 2
        for cookie_set in sets:
            assert "Secure" in cookie_set
            assert "SameSite=Lax" in cookie_set
            assert "max-age=31536000" in cookie_set

    def test_both_buttons_hide_banner(self, js):
        assert js.count("classList.remove('xl-consent-show')") == 2


# ── Timezone classifier ────────────────────────────────────


class TestTimezoneClassifier:
    @pytest.mark.parametrize("tz", ["Europe/Paris", "Europe/Oslo", "Atlantic/Canary", "Asia/Nicosia"])
    def test_eea_is_strict(self, tz):
        assert requires_explicit_consent(tz)

    @pytest.mark.parametrize("tz", ["Europe/London", "Europe/Belfast", "Europe/Zurich"])
    def test_uk_and_switzerland_are_strict(self, tz):
        assert requires_explicit_consent(tz)

    @pytest.mark.parametrize("tz", ["Europe/Istanbul", "Europe/Moscow", "Europe/Minsk", "Europe/Belgrade", "Europe/Kyiv"])
    def test_non_eea_european_zones_excluded(self, tz):
        assert tz not in EEA_UK_CH_TIMEZONES
        assert not requires_explicit_consent(tz)

    @pytest.mark.parametrize("tz", ["America/Denver", "America/Toronto", "Asia/Tokyo"])
    def test_rest_of_world_is_not_strict(self, tz):
        assert not requires_explicit_consent(tz)

    @pytest.mark.parametrize("tz", [None, "", "Unknown/Timezone"])
    def test_unknown_or_missing_fails_closed(self, tz):
        assert requires_explicit_consent(tz)


# ── Every page uses the shared snippets ────────────────────

CLI_GENERATORS = [
    "scripts/generate_homepage.py",
    "scripts/generate_race_pages.py",
    "scripts/generate_prep_kit.py",
    "scripts/generate_guide.py",
    "wordpress/generate_about.py",
    "wordpress/generate_coaching.py",
    "wordpress/generate_coaching_apply.py",
    "wordpress/generate_consult_confirmed.py",
    "wordpress/generate_consult_intake.py",
    "wordpress/generate_consulting.py",
    "wordpress/generate_course.py",
    "wordpress/generate_exit_interview.py",
    "wordpress/generate_goals.py",
    "wordpress/generate_methodology.py",
    "wordpress/generate_privacy.py",
    "wordpress/generate_terms.py",
]


@pytest.fixture(scope="module")
def generated_pages(tmp_path_factory):
    out = tmp_path_factory.mktemp("consent_pages")
    for rel in CLI_GENERATORS:
        gen_out = out / Path(rel).stem
        gen_out.mkdir()
        cmd = [sys.executable, str(PROJECT_ROOT / rel), "--output-dir", str(gen_out)]
        if rel.endswith("generate_race_pages.py") or rel.endswith("generate_prep_kit.py"):
            cmd += ["--slug", "vasaloppet"]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=300)
        assert result.returncode == 0, f"{rel} failed: {result.stderr[-500:]}"

    wp_dir = str(PROJECT_ROOT / "wordpress")
    if wp_dir not in sys.path:
        sys.path.insert(0, wp_dir)
    spec = importlib.util.spec_from_file_location(
        "_tp_gen_for_consent", PROJECT_ROOT / "wordpress" / "generate_training_plans.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.OUTPUT_DIR = out / "generate_training_plans"
    mod.generate_page()

    pages = {p.relative_to(out).as_posix(): p.read_text(encoding="utf-8") for p in out.rglob("*.html")}
    pages["web/nordic-lab-search.html"] = (PROJECT_ROOT / "web" / "nordic-lab-search.html").read_text(encoding="utf-8")
    return pages


def test_every_generator_produced_pages(generated_pages):
    stems = {rel.split("/")[0] for rel in generated_pages}
    expected = {Path(r).stem for r in CLI_GENERATORS} | {"generate_training_plans", "web"}
    assert expected <= stems, expected - stems


def test_every_page_carries_the_shared_head_and_banner(generated_pages):
    head = get_ga4_head()
    banner = get_consent_banner_html()
    problems = []
    for rel, html in generated_pages.items():
        if "googletagmanager.com" not in html:
            problems.append(f"{rel}: no GA4")
            continue
        if html.count(head) != 1:
            problems.append(f"{rel}: shared consent head appears {html.count(head)} times")
        elif html.index(head) > html.index("</head>"):
            problems.append(f"{rel}: consent head is not in <head>")
        if html.count(banner) != 1:
            problems.append(f"{rel}: shared banner appears {html.count(banner)} times")
        # Nothing else configures GA4 or sets a consent default.
        rest = html.replace(head, "").replace(banner, "")
        for needle in ("gtag('config'", "gtag(\"config\"", "'consent','default'", "'consent', 'default'",
                       "googletagmanager.com/gtag/js", "gl-cookie-accept", "xlConsent("):
            if needle in rest:
                problems.append(f"{rel}: stray {needle}")
    assert not problems, "\n".join(problems)


def test_no_browser_purchase_events(generated_pages):
    hits = [rel for rel, html in generated_pages.items()
            if re.search(r"gtag\(\s*['\"]event['\"]\s*,\s*['\"]purchase['\"]", html)]
    assert not hits, hits


def test_coaching_ctas_send_cta_click(generated_pages):
    html = next(v for k, v in generated_pages.items() if k.startswith("generate_coaching/coaching/"))
    assert "gtag('event', 'cta_click', { source: 'coaching', cta_name: name })" in html
    for name in ("hero_apply", "final_fill_intake", "sticky_cta"):
        assert f"'{name}'" in html
    assert "'tier_' + m[1]" in html
    for tier in ("min", "mid", "max"):
        assert f"?tier={tier}" in html
