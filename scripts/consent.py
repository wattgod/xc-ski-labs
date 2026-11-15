"""Shared consent head script and banner for every XC Ski Labs page.

Port of Gravel God's consent model (gravel-race-automation
wordpress/cookie_consent.py, Matti's ruling 2026-11-14), with XC's cookie
name ``xl_consent`` and XC's tokens.

Consent behaviour:
- EEA/UK/CH timezones default analytics to denied and show the banner.
- Other known timezones default analytics to granted and do not show it.
- A missing or unknown timezone fails closed to the stricter posture.
- An existing ``xl_consent=accepted`` / ``declined`` cookie overrides the
  geographic default.
- ad_storage, ad_user_data and ad_personalization are always denied.
- ``wait_for_update: 500`` gives the banner time to update before tags fire.
- The "Privacy choices" link opens the banner in every region.

Nothing goes to Google unless analytics is granted (Matti, 2026-11-15: the
code matches the privacy policy, "declining turns analytics off"):
- gtag.js is loaded and ``gtag('config')`` runs only from
  ``window.xlAnalyticsStart()``, which the head calls when the effective
  state is granted and the banner's Accept calls otherwise. A declined or
  not-yet-answered visitor never loads gtag.js, so no cookieless pings.
- ``gtag('event', ...)`` calls made before analytics starts are dropped,
  not queued, so pre-consent clicks are never replayed after Accept.
- Decline on a page where gtag.js already loaded sets Google's
  ``ga-disable-<id>`` flag and stops page events, so nothing more is sent.
- A checkout ``session_id`` is removed from the address bar before config
  (kept in ``window.xlCheckoutSessionId``) so it never reaches GA4 as
  page_location or as the next page's referrer.

The Consent Mode default runs in the same synchronous <script> block as
``gtag('config')`` and before it (CLAUDE.md pitfall 31). Every generator
uses ``get_ga4_head()`` in <head> and ``get_consent_banner_html()`` before
</body>; tests/test_consent.py enforces that on every generated page.
``web/nordic-lab-search.html`` is static: it carries the same two snippets
byte for byte (tests/test_consent.py checks parity).

Banner colours use the --gl-* tokens every page embeds (tokens/tokens.css).
"""
from __future__ import annotations

import json
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

GA4_MEASUREMENT_ID = "G-3JQLSQLPPM"
CONSENT_COOKIE = "xl_consent"

# Explicit IANA timezones for the EEA member states, United Kingdom, and
# Switzerland, copied from Gravel God's list. Cyprus has both Europe/* and
# Asia/* identifiers. Do not broaden this to all Europe/*: Istanbul, Moscow,
# Minsk, Belgrade, Kyiv and other non-EEA European zones stay outside the
# opt-in gate.
EEA_UK_CH_TIMEZONES = (
    "Africa/Ceuta",
    "Asia/Famagusta",
    "Asia/Nicosia",
    "Atlantic/Azores",
    "Atlantic/Canary",
    "America/Cayenne",
    "America/Guadeloupe",
    "America/Marigot",
    "America/Martinique",
    "Arctic/Longyearbyen",
    "Atlantic/Faeroe",
    "Indian/Mayotte",
    "Indian/Reunion",
    "Atlantic/Reykjavik",
    "Atlantic/Faroe",
    "Atlantic/Madeira",
    "Europe/Amsterdam",
    "Europe/Athens",
    "Europe/Belfast",
    "Europe/Berlin",
    "Europe/Bratislava",
    "Europe/Brussels",
    "Europe/Bucharest",
    "Europe/Budapest",
    "Europe/Busingen",
    "Europe/Copenhagen",
    "Europe/Dublin",
    "Europe/Helsinki",
    "Europe/Lisbon",
    "Europe/Ljubljana",
    "Europe/London",
    "Europe/Luxembourg",
    "Europe/Madrid",
    "Europe/Malta",
    "Europe/Mariehamn",
    "Europe/Nicosia",
    "Europe/Oslo",
    "Europe/Paris",
    "Europe/Prague",
    "Europe/Riga",
    "Europe/Rome",
    "Europe/Sofia",
    "Europe/Stockholm",
    "Europe/Tallinn",
    "Europe/Vaduz",
    "Europe/Vienna",
    "Europe/Vilnius",
    "Europe/Warsaw",
    "Europe/Zagreb",
    "Europe/Zurich",
)


def requires_explicit_consent(timezone: str | None) -> bool:
    """Return whether ``timezone`` uses the strict opt-in posture.

    A missing, empty or unknown timezone means detection failed, so it
    fails closed.
    """
    if not timezone:
        return True
    try:
        ZoneInfo(timezone)
    except (TypeError, ValueError, ZoneInfoNotFoundError):
        return True
    return timezone in EEA_UK_CH_TIMEZONES


def get_consent_head_script(ga_measurement_id: str = GA4_MEASUREMENT_ID) -> str:
    """Return the synchronous geo default and GA4 config in one script block."""
    timezone_json = json.dumps(EEA_UK_CH_TIMEZONES, separators=(",", ":"))
    return (
        "<script>window.dataLayer=window.dataLayer||[];"
        "function gtag(){if(arguments[0]==='event'&&!window.xlAnalyticsOn)return;"
        "dataLayer.push(arguments)}"
        f"var xlConsentStrictTimezones=new Set({timezone_json});"
        "var xlConsentTimezone='';var xlConsentTimezoneKnown=false;"
        "try{xlConsentTimezone=Intl.DateTimeFormat().resolvedOptions().timeZone||'';"
        "if(xlConsentTimezone){new Intl.DateTimeFormat('en-US',"
        "{timeZone:xlConsentTimezone});xlConsentTimezoneKnown=true}}"
        "catch(xlConsentTimezoneError){}"
        "var xlConsentRequiresOptIn=!xlConsentTimezoneKnown||"
        "xlConsentStrictTimezones.has(xlConsentTimezone);"
        "window.xlConsentRequiresOptIn=xlConsentRequiresOptIn;"
        "var xlConsentAccepted=/(^|; )xl_consent=accepted/.test(document.cookie);"
        "var xlConsentDeclined=/(^|; )xl_consent=declined/.test(document.cookie);"
        "var xlConsentAnalytics=xlConsentAccepted?'granted':"
        "xlConsentDeclined?'denied':xlConsentRequiresOptIn?'denied':'granted';"
        "gtag('consent','default',{'analytics_storage':xlConsentAnalytics,"
        "'ad_storage':'denied','ad_user_data':'denied',"
        "'ad_personalization':'denied','wait_for_update':500});"
        "try{var xlConsentUrl=new URL(location.href);"
        "var xlCheckoutSession=xlConsentUrl.searchParams.get('session_id');"
        "if(xlCheckoutSession!==null){window.xlCheckoutSessionId=xlCheckoutSession;"
        "xlConsentUrl.searchParams.delete('session_id');"
        "history.replaceState(history.state,'',"
        "xlConsentUrl.pathname+xlConsentUrl.search+xlConsentUrl.hash)}}"
        "catch(xlConsentUrlError){}"
        "window.xlAnalyticsOn=false;"
        "window.xlAnalyticsStart=function(){"
        f"window['ga-disable-{ga_measurement_id}']=false;"
        "window.xlAnalyticsOn=true;"
        "if(window.xlAnalyticsLoaded)return;window.xlAnalyticsLoaded=true;"
        "gtag('js',new Date());"
        f"gtag('config','{ga_measurement_id}');"
        "var s=document.createElement('script');s.async=true;"
        f"s.src='https://www.googletagmanager.com/gtag/js?id={ga_measurement_id}';"
        "document.head.appendChild(s)};"
        "window.xlAnalyticsStop=function(){window.xlAnalyticsOn=false;"
        f"window['ga-disable-{ga_measurement_id}']=true}};"
        "if(xlConsentAnalytics==='granted'){window.xlAnalyticsStart()}</script>"
    )


def get_ga4_head(ga_measurement_id: str = GA4_MEASUREMENT_ID) -> str:
    """Return the consent head block. It injects gtag.js itself, and only
    when analytics is granted (no static loader tag).

    Raw HTML with literal braces: concatenate it or pass it as an f-string
    value, never paste it inside an f-string template.
    """
    return get_consent_head_script(ga_measurement_id)


def get_consent_banner_html() -> str:
    """Return the Privacy choices strip and the consent banner (CSS, HTML, JS).

    Place it right before </body>.
    """
    return '''<style>
.xl-privacy-choices-footer{padding:8px 16px;background:var(--gl-carbon);font-family:var(--gl-font-data);display:flex;justify-content:center;gap:12px;flex-wrap:wrap}
.xl-privacy-choices{color:var(--gl-paper);font-size:11px;letter-spacing:1px;text-transform:uppercase;text-decoration:underline;text-underline-offset:3px}
.xl-privacy-choices:hover{color:var(--gl-white)}
.xl-privacy-choices:focus-visible{outline:2px solid var(--gl-klister);outline-offset:2px}
.xl-consent-banner{position:fixed;bottom:0;left:0;right:0;z-index:9999;background:var(--gl-carbon);border-top:3px solid var(--gl-swix-red);padding:16px 24px;display:none;align-items:center;justify-content:center;gap:16px;flex-wrap:wrap;font-family:var(--gl-font-data)}
.xl-consent-banner.xl-consent-show{display:flex}
.xl-consent-text{color:var(--gl-paper);font-size:13px;line-height:1.5;max-width:640px;margin:0}
.xl-consent-text a{color:var(--gl-klister)}
.xl-consent-text a:hover{color:var(--gl-white)}
.xl-consent-btn{min-width:44px;min-height:44px;padding:8px 20px;font-family:var(--gl-font-data);font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;cursor:pointer;border:2px solid;transition:background-color .3s,color .3s,border-color .3s}
.xl-consent-btn:focus-visible{outline:2px solid var(--gl-klister);outline-offset:2px}
.xl-consent-accept{background:var(--gl-swix-red);color:var(--gl-white);border-color:var(--gl-swix-red)}
.xl-consent-accept:hover{background:var(--gl-carbon);color:var(--gl-white)}
.xl-consent-decline{background:transparent;color:var(--gl-white);border-color:var(--gl-white)}
.xl-consent-decline:hover{background:var(--gl-white);color:var(--gl-carbon)}
@media(max-width:600px){.xl-consent-banner{padding:10px 16px;gap:10px}.xl-consent-text{font-size:11px;text-align:center}.xl-consent-btn{padding:6px 14px;font-size:11px}}
@media(prefers-reduced-motion:reduce){.xl-consent-btn{transition:none}}
</style>
<footer class="xl-privacy-choices-footer" aria-label="Legal"><a class="xl-privacy-choices" id="xl-privacy-choices" href="/privacy/#cookies">Privacy choices</a><a class="xl-privacy-choices" href="/privacy/">Privacy</a><a class="xl-privacy-choices" href="/terms/">Terms</a></footer>
<div class="xl-consent-banner" id="xl-consent-banner" role="dialog" aria-label="Cookie consent" aria-describedby="xl-consent-desc">
  <p class="xl-consent-text" id="xl-consent-desc">I use analytics cookies to see which pages get read. No ad cookies. <a href="/privacy/#cookies">Privacy policy</a>.</p>
  <button type="button" class="xl-consent-btn xl-consent-accept" id="xl-consent-accept">Accept</button>
  <button type="button" class="xl-consent-btn xl-consent-decline" id="xl-consent-decline">Decline</button>
</div>
<script>
(function(){
  var b=document.getElementById('xl-consent-banner');
  var p=document.getElementById('xl-privacy-choices');
  if(!b)return;
  var tid;var autoPending=false;
  function cancelAutoShow(){
    if(!autoPending)return;autoPending=false;
    clearTimeout(tid);
    window.removeEventListener('scroll',showBanner);
  }
  function showBanner(){
    cancelAutoShow();
    b.classList.add('xl-consent-show');
  }
  if(p){p.addEventListener('click',function(e){e.preventDefault();showBanner()})}
  if(!/(^|; )xl_consent=/.test(document.cookie)&&window.xlConsentRequiresOptIn!==false){
    autoPending=true;
    window.addEventListener('scroll',showBanner,{passive:true,once:true});
    tid=setTimeout(showBanner,3000);
  }
  document.getElementById('xl-consent-accept').addEventListener('click',function(){
    document.cookie='xl_consent=accepted;path=/;max-age=31536000;SameSite=Lax;Secure';
    if(typeof gtag==='function'){gtag('consent','update',{'analytics_storage':'granted'})}
    if(typeof window.xlAnalyticsStart==='function'){window.xlAnalyticsStart()}
    b.classList.remove('xl-consent-show');
  });
  document.getElementById('xl-consent-decline').addEventListener('click',function(){
    document.cookie='xl_consent=declined;path=/;max-age=31536000;SameSite=Lax;Secure';
    if(typeof window.xlAnalyticsStop==='function'){window.xlAnalyticsStop()}
    if(typeof gtag==='function'){gtag('consent','update',{'analytics_storage':'denied'})}
    b.classList.remove('xl-consent-show');
  });
})();
</script>'''
