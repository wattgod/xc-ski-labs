"""Region-aware consent: scripts/consent.py and every page that uses it.

Ported from Gravel God's tests/test_cookie_consent.py (Matti's ruling
2026-11-14: XC adopts Gravel God's consent model, cookie ``xl_consent``),
plus XC checks that every generated page carries the one shared head and
banner and nothing else configures GA4.

The questionnaire (the $49.99 storefront) uses the same head and banner.
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

    def test_no_static_loader_tag(self):
        """gtag.js is injected by xlAnalyticsStart only, never by a static tag."""
        assert "<script async" not in get_ga4_head()
        assert get_ga4_head().count("googletagmanager.com/gtag/js") == 1

    def test_config_and_loader_live_only_in_start(self, head):
        start = head.index("window.xlAnalyticsStart=function(){")
        end = head.index("window.xlAnalyticsStop=")
        for needle in ("gtag('config'", "gtag('js'", "googletagmanager.com/gtag/js", "createElement('script')"):
            assert head.count(needle) == 1, needle
            assert start < head.index(needle) < end, needle
        assert head.endswith("if(xlConsentAnalytics==='granted'){window.xlAnalyticsStart()}</script>")

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
        out = _run_page(timezone, cookie, "")
        assert out["default"] == expected
        # Granted loads gtag.js and configures GA4 once; denied (declined or
        # not yet answered) loads nothing and configures nothing.
        if expected == "granted":
            assert out["scripts"] == [f"https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"]
            assert out["commands"].count("config") == 1
        else:
            assert out["scripts"] == []
            assert "config" not in out["commands"] and "js" not in out["commands"]


# ── Behaviour in a fake browser (node) ─────────────────────

_FAKE_BROWSER = r"""
var scripts=[];var replaced=[];var timers=[];
function El(){this.h={};this.cls={};var self=this;
  this.addEventListener=function(t,f){self.h[t]=f};
  this.classList={add:function(c){self.cls[c]=true},remove:function(c){delete self.cls[c]}};
  this.click=function(){self.h.click&&self.h.click({preventDefault:function(){}})}}
var els={'xl-consent-banner':new El(),'xl-privacy-choices':new El(),
  'xl-consent-accept':new El(),'xl-consent-decline':new El()};
var dataLayer=[];var window={dataLayer:dataLayer,addEventListener:function(){},removeEventListener:function(){}};
var document={cookie:COOKIE,getElementById:function(i){return els[i]||null},
  createElement:function(){return {}},
  head:{appendChild:function(s){scripts.push(s.src)}}};
var location={href:HREF};
var history={state:null,replaceState:function(s,t,u){replaced.push(u)}};
function setTimeout(f){timers.push(f);return 1}function clearTimeout(){}
var Intl={DateTimeFormat:function(l,o){
  if(o&&o.timeZone&&o.timeZone!==TZ)throw new RangeError('bad');
  return {resolvedOptions:function(){return {timeZone:TZ}}}}};
"""


def _run_page(timezone: str, cookie: str, steps: str, href: str = "https://xcskilabs.com/") -> dict:
    """Run the shared head, then the banner script, then ``steps`` in node.

    Returns the default analytics state, every gtag command name in order
    ('event:<name>' for events), the injected script srcs, URLs passed to
    history.replaceState and the captured checkout session id.
    """
    head_js = get_consent_head_script().replace("<script>", "").replace("</script>", "")
    banner_js = _extract_js(get_consent_banner_html())
    harness = (
        _FAKE_BROWSER.replace("COOKIE", json.dumps(cookie))
        .replace("HREF", json.dumps(href))
        .replace("TZ", json.dumps(timezone))
        + head_js + "\n" + banner_js + "\n" + steps + "\n"
        + "var d=dataLayer.filter(function(a){return a[0]==='consent'&&a[1]==='default'})[0][2];"
        + "process.stdout.write(JSON.stringify({default:d.analytics_storage,"
        + "commands:dataLayer.map(function(a){return a[0]==='event'?'event:'+a[1]:a[0]}),"
        + "scripts:scripts,replaced:replaced,session:window.xlCheckoutSessionId||null,"
        + "disabled:window['ga-disable-" + GA4_MEASUREMENT_ID + "']===true}));"
    )
    result = subprocess.run(["node", "-e", harness], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.skipif(not HAS_NODE, reason="node not installed")
class TestNothingSentWithoutConsent:
    @pytest.mark.parametrize("timezone", ["America/Denver", "Europe/Oslo", ""])
    def test_declined_visitor_loads_nothing(self, timezone):
        out = _run_page(timezone, "xl_consent=declined", "gtag('event','cta_click',{});")
        assert out["scripts"] == []
        assert out["commands"] == ["consent"]

    def test_eea_visitor_without_choice_loads_nothing(self):
        out = _run_page("Europe/Oslo", "", "gtag('event','cta_click',{});")
        assert out["scripts"] == []
        assert out["commands"] == ["consent"]

    def test_eea_accept_loads_and_configures_without_reload(self):
        out = _run_page(
            "Europe/Oslo", "",
            "gtag('event','before_accept',{});"
            "els['xl-consent-accept'].click();"
            "gtag('event','after_accept',{});",
        )
        assert out["scripts"] == [f"https://www.googletagmanager.com/gtag/js?id={GA4_MEASUREMENT_ID}"]
        # Pre-consent event dropped; update precedes js/config.
        assert out["commands"] == ["consent", "consent", "js", "config", "event:after_accept"]

    def test_accept_after_decline_works_without_reload(self):
        out = _run_page(
            "America/Denver", "xl_consent=declined",
            "els['xl-privacy-choices'].click();els['xl-consent-accept'].click();"
            "gtag('event','after_accept',{});",
        )
        assert len(out["scripts"]) == 1
        assert out["commands"].count("config") == 1
        assert out["commands"][-1] == "event:after_accept"
        assert out["disabled"] is False

    def test_accept_twice_configures_once(self):
        out = _run_page("Europe/Oslo", "", "els['xl-consent-accept'].click();els['xl-consent-accept'].click();")
        assert len(out["scripts"]) == 1
        assert out["commands"].count("config") == 1

    def test_decline_after_load_stops_collection(self):
        out = _run_page(
            "America/Denver", "",
            "els['xl-privacy-choices'].click();els['xl-consent-decline'].click();"
            "gtag('event','after_decline',{});",
        )
        assert out["disabled"] is True
        assert "event:after_decline" not in out["commands"]


@pytest.mark.skipif(not HAS_NODE, reason="node not installed")
class TestCheckoutSessionIdNeverReachesGa4:
    def test_session_id_stripped_before_config(self):
        out = _run_page(
            "America/Denver", "", "",
            href="https://xcskilabs.com/consulting/confirmed/?session_id=cs_test_abc&x=1#top",
        )
        assert out["session"] == "cs_test_abc"
        assert out["replaced"] == ["/consulting/confirmed/?x=1#top"]
        assert "cs_test" not in json.dumps(out["commands"])

    def test_no_session_id_leaves_url_alone(self):
        out = _run_page("America/Denver", "", "", href="https://xcskilabs.com/coaching/?a=1")
        assert out["replaced"] == []
        assert out["session"] is None


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

    def test_banner_never_configures_directly(self, js):
        """Accept starts analytics through the head's xlAnalyticsStart (once)."""
        assert "gtag('config'" not in js
        assert "gtag('js'" not in js
        assert "window.xlAnalyticsStart()" in js
        assert "window.xlAnalyticsStop()" in js

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
    "wordpress/generate_questionnaire.py",
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


@pytest.mark.skipif(not HAS_NODE, reason="node not installed")
def test_coaching_tier_regex_matches_every_tier(generated_pages):
    """The tier regex once lost its \\b to a Python backspace and matched nothing."""
    html = next(v for k, v in generated_pages.items() if k.startswith("generate_coaching/coaching/"))
    assert "\x08" not in html
    regex = re.search(r"match\((/\[\?&\]tier=.*?/)\)", html).group(1)
    js = (
        "var r=%s;process.stdout.write(JSON.stringify(['min','mid','max','maxi'].map("
        "function(t){var m=('/coaching/apply/?tier='+t).match(r);return m?m[1]:null})))" % regex
    )
    result = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == ["min", "mid", "max", None]


def test_coaching_privacy_choices_clears_sticky_cta(generated_pages):
    """The bottom padding sits on body, so the strip after .gl-coach-page clears the fixed CTA."""
    html = next(v for k, v in generated_pages.items() if k.startswith("generate_coaching/coaching/"))
    mobile = html[html.index("@media (max-width: 768px) {\n  .gl-coach-sticky-cta"):]
    mobile = mobile[: mobile.index("\n}\n")]
    assert "body { padding-bottom: 80px; }" in mobile
