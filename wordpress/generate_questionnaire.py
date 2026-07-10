#!/usr/bin/env python3
"""
XC Ski Labs - Plan Questionnaire Generator

Generates the plan-purchase intake form at /questionnaire/.

Usage:
    python wordpress/generate_questionnaire.py
    python wordpress/generate_questionnaire.py --output-dir output
"""

import html
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
RACE_INDEX = PROJECT_ROOT / "web" / "race-index.json"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"

FORM_ACTION = "https://formsubmit.co/coaching@xcskilabs.com"
FORM_SUBJECT = "New Plan Questionnaire \u2014 XC Ski Labs"


def esc(text) -> str:
    """HTML-escape a string. Safe for None/empty."""
    if text is None or text == "":
        return ""
    return html.escape(str(text), quote=True)


def _safe_json_for_script(obj, **kwargs) -> str:
    """Serialize JSON safely for embedding inside a script element."""
    raw = json.dumps(obj, **kwargs)
    return raw.replace("</", "<\\/")


def load_race_slug_map(index_path: Path = RACE_INDEX) -> dict[str, str]:
    """Load a compact slug-to-name map from web/race-index.json."""
    if not index_path.exists():
        return {}

    data = json.loads(index_path.read_text(encoding="utf-8"))
    slug_map: dict[str, str] = {}
    for race in data.get("races", []):
        slug = race.get("s")
        name = race.get("dn") or race.get("n")
        if slug and name:
            slug_map[str(slug)] = str(name)
    return dict(sorted(slug_map.items()))


def load_tokens_css() -> str:
    """Read shared Wax Bench tokens for static embedding."""
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


def build_css() -> str:
    """Build the complete CSS for the questionnaire page."""
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
  font-family: 'Inter', sans-serif;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

a {
  color: var(--gl-swix-red);
}

a:hover {
  color: var(--gl-klister);
}

a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {
  outline: 3px solid var(--gl-swix-red);
  outline-offset: 2px;
}

.gl-page {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 20px;
  padding-bottom: 80px;
}

.gl-skip-link {
  position: absolute;
  left: -999px;
  top: 8px;
  background: var(--gl-white);
  color: var(--gl-carbon);
  padding: 8px 12px;
  z-index: 10000;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
}

.gl-skip-link:focus {
  left: 8px;
}

/* Nav Header */

.gl-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--gl-carbon);
  border-bottom: 3px solid var(--gl-swix-red);
  padding: 0 20px;
}
.gl-nav-inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
}
.gl-nav-logo {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-white);
  text-decoration: none;
  letter-spacing: 0.1em;
}
.gl-nav-logo:hover {
  color: var(--gl-hairline);
}
.gl-nav-links {
  display: flex;
  align-items: center;
  gap: 0;
  list-style: none;
  margin: 0;
  padding: 0;
}
.gl-nav-item {
  position: relative;
}
.gl-nav-item > a {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 16px 14px;
  display: block;
}
.gl-nav-item > a:hover,
.gl-nav-item > a.active {
  color: var(--gl-white);
}
.gl-nav-dropdown {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  background: var(--gl-carbon);
  border: 2px solid var(--gl-swix-red);
  min-width: 200px;
  z-index: 1001;
  padding: 8px 0;
}
.gl-nav-item:hover .gl-nav-dropdown {
  display: block;
}
.gl-nav-dropdown a {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 16px;
  display: block;
}
.gl-nav-dropdown a:hover {
  color: var(--gl-white);
  background: var(--gl-swix-red);
}
.gl-nav-hamburger {
  display: none;
  background: transparent;
  border: none;
  color: var(--gl-white);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 8px;
  min-width: 44px;
  min-height: 44px;
}

/* Header */

.gl-page-header {
  padding: 52px 0 28px;
  border-bottom: 2px solid var(--gl-hairline);
  margin-bottom: 28px;
}
.gl-kicker {
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--gl-swix-red);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 12px;
}
.gl-page-header h1 {
  font-family: var(--gl-font-editorial);
  font-size: 2.35rem;
  line-height: 1.1;
  font-weight: 700;
  margin: 0 0 12px;
}
.gl-page-header p {
  font-family: var(--gl-font-editorial);
  font-size: 1.08rem;
  color: var(--gl-muted);
  margin: 0;
}

/* Form */

.gl-form {
  border: 2px solid var(--gl-carbon);
  background: var(--gl-white);
}
.gl-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
}
.gl-field {
  padding: 20px;
  border-right: 2px solid var(--gl-carbon);
  border-bottom: 2px solid var(--gl-carbon);
}
.gl-field:nth-child(2n) {
  border-right: none;
}
.gl-field-full {
  grid-column: 1 / -1;
  border-right: none;
}
.gl-label {
  display: block;
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--gl-muted);
  margin-bottom: 8px;
}
.gl-required {
  color: var(--gl-swix-red);
}
.gl-input,
.gl-select,
.gl-textarea {
  width: 100%;
  min-height: 44px;
  border: 2px solid var(--gl-carbon);
  background: var(--gl-paper);
  color: var(--gl-carbon);
  font-family: 'Inter', sans-serif;
  font-size: 1rem;
  padding: 10px 12px;
}
.gl-textarea {
  min-height: 116px;
  resize: vertical;
}
.gl-submit-wrap {
  padding: 22px 20px;
}
.gl-submit-btn {
  min-width: 44px;
  min-height: 44px;
  border: 2px solid var(--gl-carbon);
  background: var(--gl-swix-red);
  color: var(--gl-white);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--gl-font-data);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 12px 18px;
}
.gl-submit-btn:hover {
  background: var(--gl-klister);
}
.gl-submit-note,
.gl-plan-note {
  color: var(--gl-muted);
  font-family: var(--gl-font-editorial);
  font-size: 0.96rem;
  margin: 14px 0 0;
}
.gl-success-message {
  border: 2px solid var(--gl-carbon);
  background: var(--gl-white);
  padding: 28px 24px;
  margin-top: 34px;
  display: none;
}
.gl-success-message h2 {
  font-family: var(--gl-font-editorial);
  font-size: 1.55rem;
  line-height: 1.2;
  margin: 0 0 10px;
}
.gl-success-message p {
  color: var(--gl-muted);
  font-family: var(--gl-font-editorial);
  margin: 0 0 16px;
}
body.is-submitted .gl-page-header,
body.is-submitted .gl-form {
  display: none;
}
body.is-submitted .gl-success-message {
  display: block;
}

/* Footer */

.gl-footer {
  max-width: 760px;
  margin: 0 auto;
  padding: 28px 20px 44px;
  border-top: 2px solid var(--gl-hairline);
  color: var(--gl-muted);
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.gl-footer a {
  color: var(--gl-swix-red);
  text-decoration: none;
}

/* Cookie Consent */

.gl-cookie-consent {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: var(--gl-carbon);
  border-top: 3px solid var(--gl-swix-red);
  padding: 20px;
  display: none;
}
.gl-cookie-consent.visible {
  display: block;
}
.gl-cookie-inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.gl-cookie-text {
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  color: var(--gl-white);
  flex: 1;
  min-width: 200px;
}
.gl-cookie-buttons {
  display: flex;
  gap: 10px;
}
.gl-cookie-btn {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 10px 20px;
  border: 2px solid var(--gl-white);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 44px;
  min-height: 44px;
}
.gl-cookie-btn.accept {
  background: var(--gl-swix-red);
  color: var(--gl-white);
}
.gl-cookie-btn.decline {
  background: transparent;
  color: var(--gl-white);
}

@media (max-width: 640px) {
  .gl-nav-links {
    display: none;
    position: absolute;
    top: 52px;
    left: 0;
    right: 0;
    background: var(--gl-carbon);
    flex-direction: column;
    padding: 16px 20px;
    gap: 0;
    border-bottom: 3px solid var(--gl-swix-red);
  }
  .gl-nav-links.open {
    display: flex;
  }
  .gl-nav-hamburger {
    display: block;
  }
  .gl-nav-dropdown {
    position: static;
    border: none;
    padding: 0 0 0 16px;
    display: block;
  }
  .gl-nav-item > a {
    padding: 12px 0;
  }
  .gl-page-header h1 {
    font-size: 2rem;
  }
  .gl-form-grid {
    grid-template-columns: 1fr;
  }
  .gl-field {
    border-right: none;
  }
}
"""


def build_ga4_snippet() -> str:
    """GA4 tracking snippet with cookie consent gating."""
    return """<script async src="https://www.googletagmanager.com/gtag/js?id=G-3JQLSQLPPM"></script>
<script>
window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}
(function(){var c=(document.cookie.match(/xl_consent=([^;]+)/)||[])[1];
if(c==='declined')return;gtag('js',new Date());gtag('config','G-3JQLSQLPPM')})();
</script>"""


def build_cookie_consent() -> str:
    """Cookie consent banner with accept/decline buttons."""
    return """
<div class="gl-cookie-consent" id="gl-cookie-consent">
  <div class="gl-cookie-inner">
    <p class="gl-cookie-text">We use cookies for analytics to improve your experience. You can accept or decline.</p>
    <div class="gl-cookie-buttons">
      <button class="gl-cookie-btn accept" id="gl-cookie-accept">Accept</button>
      <button class="gl-cookie-btn decline" id="gl-cookie-decline">Decline</button>
    </div>
  </div>
</div>
<script>
(function(){
  var banner=document.getElementById('gl-cookie-consent');
  if(!banner)return;
  if(document.cookie.match(/xl_consent=/)){return;}
  banner.classList.add('visible');
  document.getElementById('gl-cookie-accept').addEventListener('click',function(){
    document.cookie='xl_consent=accepted;path=/;max-age=31536000;SameSite=Lax';
    banner.classList.remove('visible');
    if(typeof gtag==='function'){gtag('consent','update',{'analytics_storage':'granted'});gtag('js',new Date());gtag('config','G-3JQLSQLPPM');}
  });
  document.getElementById('gl-cookie-decline').addEventListener('click',function(){
    document.cookie='xl_consent=declined;path=/;max-age=31536000;SameSite=Lax';
    banner.classList.remove('visible');
    if(typeof gtag==='function'){gtag('consent','update',{'analytics_storage':'denied'});}
  });
})();
</script>
"""


def build_nav_header(active: str = "") -> str:
    """Sticky top nav bar with logo and links."""
    def _active(page: str) -> str:
        return ' class="active"' if active == page else ""

    return f"""
<nav class="gl-nav">
  <div class="gl-nav-inner">
    <a href="/" class="gl-nav-logo">XC SKI LABS</a>
    <button class="gl-nav-hamburger" aria-label="Toggle navigation" onclick="document.querySelector('.gl-nav-links').classList.toggle('open')">&#9776;</button>
    <ul class="gl-nav-links">
      <li class="gl-nav-item">
        <a href="/search/"{_active("races")}>Races</a>
        <div class="gl-nav-dropdown">
          <a href="/search/">All XC Ski Races</a>
        </div>
      </li>
      <li class="gl-nav-item">
        <a href="/training-plans/"{_active("products")}>Products</a>
        <div class="gl-nav-dropdown">
          <a href="/training-plans/">Training Plans</a>
        </div>
      </li>
      <li class="gl-nav-item">
        <a href="/coaching/apply/"{_active("services")}>Services</a>
        <div class="gl-nav-dropdown">
          <a href="/coaching/apply/">Coaching</a>
        </div>
      </li>
      <li class="gl-nav-item">
        <a href="/about/"{_active("about")}>About</a>
      </li>
    </ul>
  </div>
</nav>
"""


def build_form() -> str:
    """Build the plan questionnaire form."""
    return f"""
<form class="gl-form" id="planQuestionnaire" action="{esc(FORM_ACTION)}" method="POST">
  <input type="hidden" name="_subject" value="{esc(FORM_SUBJECT)}">
  <input type="hidden" name="_captcha" value="false">
  <input type="hidden" name="_template" value="table">
  <input type="hidden" name="_next" value="https://xcskilabs.com/questionnaire/?submitted=1">
  <input type="text" name="_honey" tabindex="-1" autocomplete="off" style="display:none">

  <div class="gl-form-grid">
    <div class="gl-field gl-field-full">
      <label class="gl-label" for="target_race">Target race <span class="gl-required">*</span></label>
      <input class="gl-input" id="target_race" name="target_race" type="text" autocomplete="off" required>
    </div>

    <div class="gl-field">
      <label class="gl-label" for="race_date">Race date <span class="gl-required">*</span></label>
      <input class="gl-input" id="race_date" name="race_date" type="date" required>
    </div>

    <div class="gl-field">
      <label class="gl-label" for="weekly_hours">Weekly training hours <span class="gl-required">*</span></label>
      <select class="gl-select" id="weekly_hours" name="weekly_hours" required>
        <option value="">Select</option>
        <option value="0-5">0-5</option>
        <option value="5-8">5-8</option>
        <option value="8-12">8-12</option>
        <option value="12+">12+</option>
      </select>
    </div>

    <div class="gl-field">
      <label class="gl-label" for="structured_training_years">Years of structured training <span class="gl-required">*</span></label>
      <select class="gl-select" id="structured_training_years" name="structured_training_years" required>
        <option value="">Select</option>
        <option value="0">0</option>
        <option value="1-2">1-2</option>
        <option value="3-5">3-5</option>
        <option value="6+">6+</option>
      </select>
    </div>

    <div class="gl-field">
      <label class="gl-label" for="technique">Classic / skate / both <span class="gl-required">*</span></label>
      <select class="gl-select" id="technique" name="technique" required>
        <option value="">Select</option>
        <option value="classic">Classic</option>
        <option value="skate">Skate</option>
        <option value="both">Both</option>
      </select>
    </div>

    <div class="gl-field gl-field-full">
      <label class="gl-label" for="constraints">Anything the plan must work around</label>
      <textarea class="gl-textarea" id="constraints" name="constraints" maxlength="1200"></textarea>
    </div>

    <div class="gl-field gl-field-full">
      <label class="gl-label" for="email">Email <span class="gl-required">*</span></label>
      <input class="gl-input" id="email" name="email" type="email" autocomplete="email" required>
    </div>
  </div>

  <div class="gl-submit-wrap">
    <button type="submit" class="gl-submit-btn" id="submitBtn">Send questionnaire</button>
    <p class="gl-plan-note">You'll get your plan details and payment link by email, usually within a day.</p>
  </div>
</form>
"""


def build_questionnaire_js(slug_map: dict[str, str]) -> str:
    """Build JS for race prefill, success state, and double-submit protection."""
    race_map_json = _safe_json_for_script(slug_map, ensure_ascii=False, separators=(",", ":"))
    return f"""
<script>
(function(){{
  'use strict';
  var races = {race_map_json};
  var params = new URLSearchParams(window.location.search);
  var submitted = params.get('submitted');
  if (submitted === '1' || submitted === 'true') {{
    document.body.classList.add('is-submitted');
  }}

  var raceSlug = params.get('race');
  var raceInput = document.getElementById('target_race');
  if (raceInput && raceSlug && Object.prototype.hasOwnProperty.call(races, raceSlug)) {{
    raceInput.value = races[raceSlug];
  }}

  var form = document.getElementById('planQuestionnaire');
  if (!form) return;
  form.addEventListener('submit', function() {{
    var btn = document.getElementById('submitBtn');
    if (btn) {{
      btn.disabled = true;
      btn.textContent = 'Sending...';
      setTimeout(function() {{
        btn.disabled = false;
        btn.textContent = 'Send questionnaire';
      }}, 5000);
    }}
  }});
}})();
</script>
"""


def build_footer() -> str:
    """Build footer links."""
    return """
<footer class="gl-footer">
  <a href="/">Home</a> &middot;
  <a href="/search/">Search</a> &middot;
  <a href="/training-plans/">Training Plans</a>
</footer>
"""


def generate_page(output_dir: Path | None = None, race_index_path: Path = RACE_INDEX) -> Path:
    """Generate the questionnaire page."""
    if output_dir is None:
        output_dir = OUTPUT_DIR

    out_path = output_dir / "questionnaire" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    slug_map = load_race_slug_map(race_index_path)
    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Plan Questionnaire | XC Ski Labs</title>
  <meta name="description" content="Tell XC Ski Labs about your target race and training history so we can prepare your custom XC ski training plan.">
  <meta name="robots" content="noindex, nofollow">
  <link rel="canonical" href="https://xcskilabs.com/questionnaire/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sometype+Mono:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap" rel="stylesheet">
  {build_ga4_snippet()}
  <style>{build_css()}</style>
</head>
<body>

<a href="#questionnaire" class="gl-skip-link">Skip to questionnaire</a>

{build_nav_header(active="products")}

<main class="gl-page" id="questionnaire">
  <header class="gl-page-header">
    <div class="gl-kicker">Training plans</div>
    <h1>Tell me about your race.</h1>
    <p>A short intake so the plan fits the start line, the calendar, and the training hours you actually have.</p>
  </header>

  {build_form()}

  <section class="gl-success-message" aria-live="polite">
    <h2>Questionnaire received.</h2>
    <p>You'll get your plan details and payment link by email, usually within a day.</p>
    <a href="/training-plans/">Back to training plans</a>
  </section>
</main>

{build_footer()}

{build_cookie_consent()}

{build_questionnaire_js(slug_map)}

</body>
</html>"""

    out_path.write_text(page_html, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate XC Ski Labs plan questionnaire")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--race-index", type=Path, default=RACE_INDEX)
    args = parser.parse_args()

    path = generate_page(args.output_dir, args.race_index)
    print(f"Generated {path}")
