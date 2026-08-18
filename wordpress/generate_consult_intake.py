#!/usr/bin/env python3
"""
XC Ski Labs — Consulting Intake Form Generator (/consulting/intake/)

Fourteen questions, five minutes, save/resume via localStorage. Reads
the booking session ref and the athlete's private intake token from
the URL FRAGMENT (`#ref=...&t=...`) — never the query string, so
neither value is logged by servers or shows up in referrer headers.
The token itself is only ever emailed to the athlete in their welcome
email; if it's missing (e.g. someone lands here from the confirmed
page instead of the email), the page still works and tells them to
use the emailed link instead.

Submits `{ref, t, answers}` as JSON to the pipeline's
/api/consult-intake endpoint (token travels in the POST body, not a
header or query param, to keep the simple-CORS story intact).

Port of Gravel God's consult intake generator (gravel-race-automation/
wordpress/generate_consult_intake.py) — same 14 fields (incl. tp_email
key), same fragment-only token handling. Shares nav/footer/consent/
CSS-token loading with wordpress/generate_consulting.py.

Usage:
    python wordpress/generate_consult_intake.py
    python wordpress/generate_consult_intake.py --output-dir output
"""

import html
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_consulting import (
    SITE_BASE_URL,
    GA4_ID,
    PRIVACY_SENTENCE,
    load_tokens_css,
    build_nav,
    build_footer,
    build_cookie_consent,
)

CONSULT_INTAKE_API = "https://athlete-custom-training-plan-pipeline-production.up.railway.app/api/consult-intake"


def esc(text) -> str:
    """HTML-escape a string. Safe for None/empty."""
    if text is None or text == "":
        return ""
    return html.escape(str(text))


# ── Page sections ─────────────────────────────────────────────

def build_header() -> str:
    return '''<div class="gl-intake-header">
    <div class="gl-intake-badge">Consult Intake</div>
    <h1>Twelve Questions, Five Minutes</h1>
    <p>Answer what you can. Skip what you don&rsquo;t know &mdash; &ldquo;don&rsquo;t know&rdquo; is a fine answer for FTP and LTHR. Save and come back if you need to.</p>
  </div>
  <div class="gl-intake-token-banner" id="token-banner" style="display:none">
    Can&rsquo;t find your booking reference? Use the link in your welcome email instead &mdash; it connects your answers to your consult automatically. You can still fill this out; I&rsquo;ll match it up.
  </div>'''


def build_fields() -> str:
    return '''<div class="gl-intake-group">
      <label class="gl-intake-label" for="goal_event">Goal event</label>
      <input type="text" id="goal_event" name="goal_event" placeholder="Race or event name">
    </div>
    <div class="gl-intake-group">
      <label class="gl-intake-label" for="goal_date">Date</label>
      <input type="date" id="goal_date" name="goal_date">
    </div>
    <div class="gl-intake-inline">
      <div class="gl-intake-group">
        <label class="gl-intake-label" for="hours_typical">Typical weekly hours</label>
        <input type="text" id="hours_typical" name="hours_typical" placeholder="e.g. 8">
      </div>
      <div class="gl-intake-group">
        <label class="gl-intake-label" for="hours_max">Max weekly hours</label>
        <input type="text" id="hours_max" name="hours_max" placeholder="e.g. 12">
      </div>
    </div>
    <div class="gl-intake-group">
      <label class="gl-intake-label" for="years_training">Years training</label>
      <input type="text" id="years_training" name="years_training" placeholder="e.g. 3">
    </div>
    <div class="gl-intake-inline">
      <div class="gl-intake-group">
        <label class="gl-intake-label" for="ftp">Your threshold power (FTP), if you know it</label>
        <input type="text" id="ftp" name="ftp" placeholder="Watts, from a roller-ski erg or cycling, or &quot;don't know&quot;">
      </div>
      <div class="gl-intake-group">
        <label class="gl-intake-label" for="lthr">Your threshold heart rate (LTHR), if you know it</label>
        <input type="text" id="lthr" name="lthr" placeholder="BPM, or &quot;don't know&quot;">
      </div>
    </div>
    <div class="gl-intake-group">
      <label class="gl-intake-label" for="top_question">The one question you most want answered</label>
      <textarea id="top_question" name="top_question" rows="3"></textarea>
    </div>
    <div class="gl-intake-group">
      <label class="gl-intake-label" for="whats_gone_wrong">What&rsquo;s gone wrong this year</label>
      <textarea id="whats_gone_wrong" name="whats_gone_wrong" rows="3"></textarea>
    </div>
    <div class="gl-intake-group">
      <label class="gl-intake-label" for="injuries_limits">Injuries or limits</label>
      <textarea id="injuries_limits" name="injuries_limits" rows="2"></textarea>
    </div>
    <div class="gl-intake-group">
      <label class="gl-intake-label" for="tp_email">The email you sign in to TrainingPeaks with (or &quot;no TP&quot;)</label>
      <input type="text" id="tp_email" name="tp_email" placeholder="you@example.com, or &quot;no TP&quot;">
    </div>
    <div class="gl-intake-inline">
      <div class="gl-intake-group">
        <span class="gl-intake-label">Power meter?</span>
        <div class="gl-intake-radio-row">
          <label class="gl-intake-radio-option"><input type="radio" name="power_meter" value="yes"> Yes</label>
          <label class="gl-intake-radio-option"><input type="radio" name="power_meter" value="no"> No</label>
        </div>
      </div>
      <div class="gl-intake-group">
        <span class="gl-intake-label">HR strap?</span>
        <div class="gl-intake-radio-row">
          <label class="gl-intake-radio-option"><input type="radio" name="hr_strap" value="yes"> Yes</label>
          <label class="gl-intake-radio-option"><input type="radio" name="hr_strap" value="no"> No</label>
        </div>
      </div>
    </div>
    <div class="gl-intake-group">
      <label class="gl-intake-label" for="coaching_history">Coaching or plan history</label>
      <textarea id="coaching_history" name="coaching_history" rows="2"></textarea>
    </div>
    <div class="gl-intake-group">
      <label class="gl-intake-label" for="anything_else">Anything else</label>
      <textarea id="anything_else" name="anything_else" rows="2"></textarea>
    </div>'''


def build_submit_buttons() -> str:
    return '''<div class="gl-intake-buttons">
      <button type="button" id="save-btn" class="gl-intake-save-btn">Save Progress</button>
      <button type="submit" id="submit-btn" class="gl-intake-submit-btn">Submit</button>
    </div>'''


def build_success_state() -> str:
    return '''<div id="intake-success" class="gl-intake-success" style="display:none">
    <h2>Got it &mdash; I&rsquo;ll have your read done before we talk.</h2>
  </div>'''


def build_privacy() -> str:
    return f'''<p class="gl-intake-privacy">{PRIVACY_SENTENCE}</p>'''


def build_jsonld() -> str:
    return f'''<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "WebPage",
  "name": "Consulting Intake",
  "url": "{SITE_BASE_URL}/consulting/intake/"
}}
</script>'''


# ── CSS ────────────────────────────────────────────────────────

def build_intake_css() -> str:
    return load_tokens_css() + """

*, *::before, *::after {
  box-sizing: border-box;
  border-radius: 0 !important;
  box-shadow: none !important;
}

body {
  margin: 0;
  padding: 0;
  background: var(--gl-paper);
  color: var(--gl-carbon);
  font-family: var(--gl-font-editorial);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--gl-carbon); }

a:focus-visible, button:focus-visible, input:focus-visible, textarea:focus-visible {
  outline: 2px solid var(--gl-swix-red);
  outline-offset: 2px;
}

/* Shared site navigation (matches wordpress/generate_consulting.py) */
.gl-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--gl-carbon);
  border-bottom: 3px solid var(--gl-white);
  padding: 0 24px;
}
.gl-nav-inner {
  max-width: var(--gl-measure);
  min-height: 52px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.gl-nav-logo {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-white);
  text-decoration: none;
  letter-spacing: 0.1em;
}
.gl-nav-logo em { color: var(--gl-white); }
.gl-nav-links {
  display: flex;
  align-items: center;
  list-style: none;
  margin: 0;
  padding: 0;
}
.gl-nav-item { position: relative; }
.gl-nav-item > a {
  display: block;
  padding: 16px 14px;
  color: var(--gl-muted);
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-decoration: none;
  text-transform: uppercase;
}
.gl-nav-item > a:hover, .gl-nav-item > a.active { color: var(--gl-white); }
.gl-nav-dropdown {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 200px;
  padding: 8px 0;
  background: var(--gl-carbon);
  border: 2px solid var(--gl-white);
}
.gl-nav-item:hover .gl-nav-dropdown { display: block; }
.gl-nav-dropdown a {
  display: block;
  padding: 10px 16px;
  color: var(--gl-muted);
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-decoration: none;
  text-transform: uppercase;
}
.gl-nav-dropdown a:hover { background: var(--gl-white); color: var(--gl-carbon); }
.gl-nav-hamburger {
  display: none;
  min-width: 44px;
  min-height: 44px;
  padding: 8px;
  background: transparent;
  border: 0;
  color: var(--gl-white);
  cursor: pointer;
  font-size: 1.5rem;
}

/* ── Intake page ──────────────────────────────── */

.gl-intake-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 48px 24px 80px;
}
.gl-intake-header {
  text-align: center;
  margin-bottom: 24px;
}
.gl-intake-badge {
  display: inline-block;
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--gl-muted);
  margin-bottom: 12px;
}
.gl-intake-header h1 {
  font-family: var(--gl-font-editorial);
  font-size: clamp(24px, 4vw, 32px);
  font-weight: 700;
  color: var(--gl-carbon);
  margin: 0 0 12px;
}
.gl-intake-header p {
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--gl-muted);
  margin: 0;
}
.gl-intake-token-banner {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  line-height: 1.5;
  color: var(--gl-carbon);
  background: var(--gl-paper);
  border: 2px solid var(--gl-klister);
  padding: 16px;
  margin-bottom: 24px;
}
.gl-intake-form-card {
  background: var(--gl-white);
  border: 3px solid var(--gl-carbon);
  padding: 32px;
}
.gl-intake-inline {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.gl-intake-group {
  margin-bottom: 16px;
}
.gl-intake-label {
  display: block;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--gl-carbon);
  margin-bottom: 6px;
}
.gl-intake-group input[type="text"],
.gl-intake-group input[type="date"],
.gl-intake-group textarea {
  display: block;
  width: 100%;
  padding: 10px 12px;
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  color: var(--gl-carbon);
  background: var(--gl-white);
  border: 2px solid var(--gl-carbon);
  box-sizing: border-box;
  resize: vertical;
}
.gl-intake-group input:focus,
.gl-intake-group textarea:focus {
  outline: none;
  border-color: var(--gl-swix-red);
}
.gl-intake-radio-row {
  display: flex;
  gap: 16px;
}
.gl-intake-radio-option {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  color: var(--gl-muted);
  cursor: pointer;
}
.gl-intake-radio-option input[type="radio"] {
  accent-color: var(--gl-swix-red);
}
.gl-intake-honeypot {
  position: absolute;
  left: -9999px;
}
.gl-intake-buttons {
  display: flex;
  gap: 16px;
  margin-top: 24px;
}
.gl-intake-submit-btn,
.gl-intake-save-btn {
  flex: 1;
  padding: 12px 24px;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  cursor: pointer;
  border: 3px solid var(--gl-carbon);
  transition: background-color 0.15s, border-color 0.15s;
}
.gl-intake-submit-btn {
  color: var(--gl-white);
  background: var(--gl-swix-red);
}
.gl-intake-submit-btn:hover {
  background-color: var(--gl-red-deep);
}
.gl-intake-submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.gl-intake-save-btn {
  color: var(--gl-carbon);
  background: var(--gl-white);
}
.gl-intake-save-btn:hover {
  background-color: var(--gl-paper);
}
.gl-intake-message {
  margin-top: 16px;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  text-align: center;
}
.gl-intake-message.info {
  color: var(--gl-carbon);
}
.gl-intake-message.error {
  color: var(--gl-carbon);
  border: 2px solid var(--gl-swix-red);
  padding: 10px 12px;
  background: var(--gl-paper);
}
.gl-intake-message.hidden {
  display: none;
}
.gl-intake-success {
  text-align: center;
  padding: 64px 24px;
  background: var(--gl-white);
  border: 3px solid var(--gl-carbon);
}
.gl-intake-success h2 {
  font-family: var(--gl-font-editorial);
  font-size: clamp(22px, 4vw, 26px);
  font-weight: 700;
  color: var(--gl-carbon);
  margin: 0;
}
.gl-intake-privacy {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  color: var(--gl-muted);
  text-align: center;
  line-height: 1.5;
  margin-top: 32px;
}

/* ── Footer (matches wordpress/generate_consulting.py) ── */
.gl-consult-footer {
  background: var(--gl-carbon);
  color: var(--gl-muted);
  padding: 32px 24px;
  border-top: 1px solid var(--gl-hairline);
  text-align: center;
}
.gl-consult-footer-brand {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gl-white);
  text-transform: uppercase;
  letter-spacing: 2px;
}
.gl-consult-footer-links {
  margin-top: 12px;
  display: flex;
  justify-content: center;
  gap: 20px;
  flex-wrap: wrap;
}
.gl-consult-footer-links a {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.gl-consult-footer-links a:hover { color: var(--gl-white); }
.gl-consult-footer-copy {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  color: var(--gl-muted);
  margin-top: 16px;
}

/* ── Cookie Consent (matches wordpress/generate_consulting.py) ── */
.gl-consult-cookie-consent {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: var(--gl-carbon);
  border-top: 1px solid var(--gl-paper);
  padding: 20px;
  display: none;
}
.gl-consult-cookie-consent.visible { display: block; }
.gl-consult-cookie-inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.gl-consult-cookie-text {
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  color: var(--gl-white);
  flex: 1;
  min-width: 200px;
}
.gl-consult-cookie-buttons { display: flex; gap: 10px; }
.gl-consult-cookie-btn {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 10px 20px;
  border: 1px solid var(--gl-white);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 44px;
  min-height: 44px;
  background: transparent;
  color: var(--gl-white);
}
.gl-consult-cookie-btn.accept { background: var(--gl-white); color: var(--gl-carbon); }

/* ── Responsive ───────────────────────────────── */

@media (max-width: 640px) {
  .gl-intake-page { padding: 32px 16px 60px; }
  .gl-intake-form-card { padding: 20px; }
  .gl-intake-inline { grid-template-columns: 1fr; }
  .gl-intake-buttons { flex-direction: column; }
  .gl-nav { padding: 0 20px; }
  .gl-nav-hamburger { display: block; }
  .gl-nav-links {
    display: none;
    position: absolute;
    top: 52px;
    left: 0;
    right: 0;
    flex-direction: column;
    align-items: stretch;
    background: var(--gl-carbon);
    border-bottom: 3px solid var(--gl-white);
  }
  .gl-nav-links.open { display: flex; }
  .gl-nav-dropdown { display: block; position: static; border: 0; padding: 0 0 0 16px; }
  .gl-nav-item > a { padding: 12px 0; }
}
"""


# ── JS ─────────────────────────────────────────────────────────

def build_intake_js() -> str:
    return f'''<script>
(function(){{
  var API_URL = "{CONSULT_INTAKE_API}";
  var STORAGE_KEY = "xcskilabs_consult_intake_progress";

  /* ── Parse ref/t from the URL FRAGMENT only — never the query string ── */
  function parseFragment(){{
    var hash = window.location.hash || "";
    if (hash.indexOf("#") === 0) {{ hash = hash.slice(1); }}
    var params = new URLSearchParams(hash);
    return {{ ref: params.get("ref") || "", t: params.get("t") || "" }};
  }}
  var frag = parseFragment();

  if (!frag.t) {{
    var banner = document.getElementById("token-banner");
    if (banner) {{ banner.style.display = "block"; }}
  }}

  var form = document.getElementById("intake-form");
  var msgEl = document.getElementById("intake-message");
  var submitBtn = document.getElementById("submit-btn");
  var successEl = document.getElementById("intake-success");

  function showMessage(type, text){{
    if (!msgEl) return;
    msgEl.className = "gl-intake-message " + type;
    msgEl.textContent = text;
  }}

  /* ── Save progress ── */
  var saveBtn = document.getElementById("save-btn");
  if (saveBtn) {{
    saveBtn.addEventListener("click", function(){{
      var data = {{}};
      new FormData(form).forEach(function(value, key){{
        if (key === "_honeypot") return;
        data[key] = value;
      }});
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      showMessage("info", "Progress saved. Come back anytime.");
      if (typeof gtag === "function") {{ gtag("event", "consult_intake_progress_saved", {{}}); }}
    }});
  }}

  /* ── Restore progress ── */
  function restoreProgress(){{
    var saved = localStorage.getItem(STORAGE_KEY);
    if (!saved) return;
    try {{
      var data = JSON.parse(saved);
      Object.keys(data).forEach(function(key){{
        var elements = form.querySelectorAll('[name="' + key + '"]');
        elements.forEach(function(el){{
          if (el.type === "radio") {{ el.checked = (el.value === data[key]); }}
          else {{ el.value = data[key]; }}
        }});
      }});
    }} catch (e) {{ /* ignore corrupt localStorage */ }}
  }}

  /* ── Submit ── */
  if (form) {{
    form.addEventListener("submit", function(e){{
      e.preventDefault();
      var honeypot = form.querySelector('input[name="_honeypot"]').value;
      if (honeypot) return;

      submitBtn.disabled = true;
      submitBtn.textContent = "Submitting...";
      showMessage("info", "");

      var answers = {{}};
      new FormData(form).forEach(function(value, key){{
        if (key === "_honeypot") return;
        answers[key] = value;
      }});

      var payload = {{ ref: frag.ref, t: frag.t, answers: answers }};

      fetch(API_URL, {{
        method: "POST",
        headers: {{ "Content-Type": "application/json" }},
        body: JSON.stringify(payload)
      }}).then(function(r){{
        if (!r.ok) throw new Error("Server error (" + r.status + ")");
        return r.json();
      }}).then(function(){{
        localStorage.removeItem(STORAGE_KEY);
        if (typeof gtag === "function") {{ gtag("event", "consult_intake_submitted", {{}}); }}
        form.style.display = "none";
        if (successEl) {{ successEl.style.display = "block"; successEl.scrollIntoView({{ behavior: "smooth", block: "center" }}); }}
      }}).catch(function(err){{
        /* Keep the draft in localStorage — do NOT clear it on error */
        showMessage("error", "Something went wrong. Your answers are saved on this device — try again, or reply to your welcome email.");
        submitBtn.disabled = false;
        submitBtn.textContent = "Submit";
        if (typeof gtag === "function") {{ gtag("event", "consult_intake_error", {{ error: err.message || "unknown" }}); }}
      }});
    }});
  }}

  if (typeof gtag === "function") {{ gtag("event", "consult_intake_page_view", {{}}); }}

  restoreProgress();
}})();
</script>'''


# ── Page Generator ─────────────────────────────────────────────

def generate_intake_page(output_dir: Path = None) -> Path:
    """Generate the consulting intake form page."""
    if output_dir is None:
        output_dir = OUTPUT_DIR

    out_path = output_dir / "consulting" / "intake" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    canonical_url = f"{SITE_BASE_URL}/consulting/intake/"
    title = "Consulting Intake | XC Ski Labs"
    description = "Twelve questions before your consult call — five minutes, save and come back."

    nav = build_nav()
    header = build_header()
    fields = build_fields()
    buttons = build_submit_buttons()
    success = build_success_state()
    privacy = build_privacy()
    footer = build_footer()
    jsonld = build_jsonld()
    intake_css = build_intake_css()
    intake_js = build_intake_js()
    consent = build_cookie_consent()

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="{esc(canonical_url)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap" rel="stylesheet">
  {jsonld}
  <style>{intake_css}</style>
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
  <script>
  window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
  (function(){{var c=(document.cookie.match(/xl_consent=([^;]+)/)||[])[1];
  if(c==='declined')return;gtag('js',new Date());gtag('config','{GA4_ID}')}})();
  </script>
</head>
<body>

{nav}

<div class="gl-intake-page">
  {header}
  <form id="intake-form" class="gl-intake-form-card" novalidate>
    <input type="text" name="_honeypot" class="gl-intake-honeypot" tabindex="-1" autocomplete="off">
    {fields}
    {buttons}
    <div id="intake-message" class="gl-intake-message hidden"></div>
  </form>
  {success}
  {privacy}
</div>

{footer}

{consent}

{intake_js}

</body>
</html>"""

    out_path.write_text(page_html, encoding="utf-8")
    return out_path


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate XC Ski Labs consulting intake form")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Output directory (default: project output/)")
    args = parser.parse_args()

    out = generate_intake_page(output_dir=args.output_dir)
    print(f"Generated: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")
