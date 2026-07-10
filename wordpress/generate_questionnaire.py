#!/usr/bin/env python3
"""Generate the custom-plan intake form at /questionnaire/."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
RACE_INDEX = PROJECT_ROOT / "web" / "race-index.json"
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"

FORM_ACTION = "https://formsubmit.co/coaching@xcskilabs.com"
FORM_SUBJECT = "New Plan Questionnaire \u2014 XC Ski Labs"
TOTAL_SECTIONS = 8


def esc(text: Any) -> str:
    if text is None or text == "":
        return ""
    return html.escape(str(text), quote=True)


def _safe_json_for_script(obj: Any, **kwargs: Any) -> str:
    return json.dumps(obj, **kwargs).replace("</", "<\\/")


def load_tokens_css() -> str:
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


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


def load_race_details(slug_map: dict[str, str]) -> dict[str, dict[str, Any]]:
    """Load date and distance options for known race slugs when available."""
    details: dict[str, dict[str, Any]] = {}
    for slug, name in slug_map.items():
        details[slug] = {"name": name}
        path = RACE_DATA_DIR / f"{slug}.json"
        if not path.exists():
            continue
        try:
            race = json.loads(path.read_text(encoding="utf-8")).get("race", {})
        except json.JSONDecodeError:
            continue
        vitals = race.get("vitals") or {}
        details[slug] = {
            "name": race.get("display_name") or race.get("name") or name,
            "date": vitals.get("date_specific") or vitals.get("date") or "",
            "distance_options": vitals.get("distance_options") or [],
            "distance_km": vitals.get("distance_km") or "",
            "discipline": vitals.get("discipline") or "",
        }
    return details


def build_css() -> str:
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
a { color: var(--gl-swix-red); }
a:hover { color: var(--gl-carbon); }
a:focus-visible,
button:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible {
  outline: 3px solid var(--gl-swix-red);
  outline-offset: 2px;
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
.gl-skip-link:focus { left: 8px; }
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
  min-height: 52px;
}
.gl-nav-logo {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-white);
  text-decoration: none;
  letter-spacing: 0.1em;
}
.gl-nav-links {
  display: flex;
  gap: 18px;
  align-items: center;
}
.gl-nav-links a {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.gl-nav-links a:hover,
.gl-nav-links a.active { color: var(--gl-white); }
.gl-page {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 20px 80px;
}
.gl-page-header {
  padding: 48px 0 28px;
  border-bottom: 2px solid var(--gl-hairline);
  margin-bottom: 24px;
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
  font-family: var(--gl-font-display);
  font-size: clamp(2.2rem, 8vw, 4.4rem);
  font-style: italic;
  font-weight: 900;
  line-height: 0.96;
  text-transform: uppercase;
  margin: 0 0 14px;
}
.gl-page-header p {
  font-size: 1.08rem;
  color: var(--gl-muted);
  margin: 0;
  max-width: 62ch;
}
.gl-progress-wrap {
  position: sticky;
  top: 52px;
  z-index: 900;
  background: var(--gl-white);
  border: 2px solid var(--gl-carbon);
  margin-bottom: 28px;
  padding: 12px;
}
.gl-progress-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}
.gl-progress-label,
.gl-progress-pct,
.gl-save-indicator {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gl-muted);
  white-space: nowrap;
}
.gl-progress-track {
  flex: 1;
  height: 8px;
  background: var(--gl-hairline);
  border: 1px solid var(--gl-muted);
}
.gl-progress-fill {
  height: 100%;
  width: 0;
  background: var(--gl-swix-red);
  transition: width 0.2s ease;
}
.gl-save-indicator {
  opacity: 0;
  transition: opacity 0.15s ease;
}
.gl-save-indicator.show { opacity: 1; }
.gl-form { margin: 0; }
.gl-section {
  border: 2px solid var(--gl-carbon);
  background: var(--gl-white);
  margin-bottom: 28px;
}
.gl-section-header {
  background: var(--gl-carbon);
  color: var(--gl-white);
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.gl-section-num {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  font-weight: 700;
  background: var(--gl-swix-red);
  color: var(--gl-white);
  padding: 3px 8px;
  letter-spacing: 0.08em;
}
.gl-section-title {
  font-family: var(--gl-font-data);
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.gl-section-body { padding: 22px 18px; }
.gl-field { margin-bottom: 18px; }
.gl-field:last-child { margin-bottom: 0; }
.gl-field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.gl-field label,
.gl-label {
  display: block;
  font-family: var(--gl-font-data);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.req { color: var(--gl-swix-red); }
input[type="text"],
input[type="email"],
input[type="number"],
input[type="date"],
select,
textarea {
  width: 100%;
  min-height: 44px;
  border: 2px solid var(--gl-carbon);
  background: var(--gl-paper);
  color: var(--gl-carbon);
  font-family: var(--gl-font-data);
  font-size: 0.9rem;
  padding: 10px 12px;
}
textarea {
  min-height: 116px;
  resize: vertical;
}
.gl-hint {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  color: var(--gl-muted);
  margin-top: 4px;
}
.gl-radio-group,
.gl-checkbox-group,
.gl-scale-group {
  display: grid;
  gap: 8px;
}
.gl-radio-group,
.gl-checkbox-group {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.gl-scale-group {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}
.gl-choice {
  min-height: 44px;
  border: 1px solid var(--gl-hairline);
  padding: 9px 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--gl-font-data);
  font-size: 0.78rem;
  cursor: pointer;
}
.gl-choice:hover { border-color: var(--gl-swix-red); }
.gl-choice input { accent-color: var(--gl-swix-red); }
.gl-conditional {
  display: none;
  margin-top: 12px;
  padding-left: 14px;
  border-left: 3px solid var(--gl-swix-red);
}
.gl-conditional.visible { display: block; }
.gl-submit-wrap {
  border: 2px solid var(--gl-carbon);
  background: var(--gl-white);
  padding: 22px 18px;
}
.gl-submit-btn {
  min-height: 44px;
  border: 2px solid var(--gl-carbon);
  background: var(--gl-swix-red);
  color: var(--gl-white);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 12px 18px;
}
.gl-submit-btn:hover { background: var(--gl-carbon); }
.gl-submit-note {
  color: var(--gl-muted);
  font-size: 0.95rem;
  margin: 12px 0 0;
}
.gl-success-message {
  border: 3px solid var(--gl-carbon);
  background: var(--gl-white);
  padding: 28px;
  margin: 36px 0;
}
.gl-success-message h2 {
  font-family: var(--gl-font-display);
  font-style: italic;
  font-weight: 900;
  text-transform: uppercase;
  line-height: 0.98;
  margin: 0 0 12px;
}
.gl-footer {
  max-width: 760px;
  margin: 0 auto;
  padding: 34px 20px 60px;
  color: var(--gl-muted);
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.gl-cookie-consent {
  position: fixed;
  left: 20px;
  right: 20px;
  bottom: 20px;
  z-index: 2000;
  display: none;
  background: var(--gl-carbon);
  color: var(--gl-white);
  border: 2px solid var(--gl-swix-red);
  padding: 14px;
}
.gl-cookie-consent.visible { display: block; }
.gl-cookie-inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 16px;
  justify-content: space-between;
}
.gl-cookie-text {
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  color: var(--gl-hairline);
}
.gl-cookie-actions {
  display: flex;
  gap: 8px;
}
.gl-cookie-actions button {
  min-height: 40px;
  border: 2px solid var(--gl-white);
  background: transparent;
  color: var(--gl-white);
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 8px 12px;
  cursor: pointer;
}
.gl-cookie-actions button:first-child {
  background: var(--gl-white);
  color: var(--gl-carbon);
}
@media (max-width: 700px) {
  .gl-nav-inner { align-items: flex-start; flex-direction: column; padding: 12px 0; }
  .gl-nav-links { flex-wrap: wrap; gap: 12px; }
  .gl-progress-wrap { top: 86px; }
  .gl-field-row,
  .gl-radio-group,
  .gl-checkbox-group,
  .gl-scale-group {
    grid-template-columns: 1fr;
  }
  .gl-cookie-inner { align-items: flex-start; flex-direction: column; }
}
"""


def build_ga4() -> str:
    return """<script async src="https://www.googletagmanager.com/gtag/js?id=G-3JQLSQLPPM"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
(function(){
  var consent = (document.cookie.match(/xl_consent=([^;]+)/) || [])[1];
  gtag('consent','default',{
    'analytics_storage': consent === 'accepted' ? 'granted' : 'denied',
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'functionality_storage': 'granted',
    'security_storage': 'granted'
  });
})();
gtag('js', new Date());
gtag('config', 'G-3JQLSQLPPM');
</script>"""


def build_nav() -> str:
    return """<nav class="gl-nav" aria-label="Primary">
  <div class="gl-nav-inner">
    <a href="/" class="gl-nav-logo">XC SKI LABS</a>
    <div class="gl-nav-links">
      <a href="/search/">Search</a>
      <a href="/training-plans/" class="active">Plans</a>
      <a href="/coaching/apply/">Coaching</a>
    </div>
  </div>
</nav>"""


def radio_group(name: str, options: list[tuple[str, str]], required: bool = False) -> str:
    req = " required" if required else ""
    return '<div class="gl-radio-group">' + "".join(
        f'<label class="gl-choice"><input type="radio" name="{esc(name)}" value="{esc(value)}"{req}> {esc(label)}</label>'
        for value, label in options
    ) + "</div>"


def checkbox_group(name: str, options: list[tuple[str, str]]) -> str:
    return '<div class="gl-checkbox-group">' + "".join(
        f'<label class="gl-choice"><input type="checkbox" name="{esc(name)}" value="{esc(value)}"> {esc(label)}</label>'
        for value, label in options
    ) + "</div>"


def scale_group(name: str, required: bool = False) -> str:
    req = " required" if required else ""
    return '<div class="gl-scale-group">' + "".join(
        f'<label class="gl-choice"><input type="radio" name="{esc(name)}" value="{i}"{req}> {i}</label>'
        for i in range(1, 6)
    ) + "</div>"


def section(num: int, title: str, body: str) -> str:
    return f"""<section class="gl-section" data-section="{num}">
  <div class="gl-section-header">
    <div class="gl-section-num">{num:02d}</div>
    <div class="gl-section-title">{esc(title)}</div>
  </div>
  <div class="gl-section-body">{body}</div>
</section>"""


def build_form() -> str:
    return f"""<form id="planIntake" class="gl-form" action="{esc(FORM_ACTION)}" method="POST">
  <input type="hidden" name="_subject" value="{esc(FORM_SUBJECT)}">
  <input type="hidden" name="_next" value="https://xcskilabs.com/questionnaire/?submitted=1">
  <input type="text" name="_honey" tabindex="-1" autocomplete="off" style="display:none">
  <input type="hidden" name="_captcha" value="false">
  <input type="hidden" name="race_slug" id="raceSlug">

  {section(1, "Your race", '''
    <div class="gl-field">
      <label for="targetRace">Target race <span class="req">*</span></label>
      <input id="targetRace" name="target_race" type="text" required autocomplete="off">
      <div class="gl-hint">Tell me about your race.</div>
    </div>
    <div class="gl-field-row">
      <div class="gl-field">
        <label for="raceDate">Race date <span class="req">*</span></label>
        <input id="raceDate" name="race_date" type="text" required placeholder="March 1, 2027">
      </div>
      <div class="gl-field">
        <label for="raceDistance">Distance</label>
        <select id="raceDistance" name="race_distance">
          <option value="">Select if known</option>
        </select>
      </div>
    </div>
  ''')}

  {section(2, "Technique", f'''
    <div class="gl-field">
      <div class="gl-label">What do you ski most?</div>
      {radio_group("technique_background", [("classic", "Classic"), ("skate", "Skate"), ("both", "Both")])}
    </div>
    <div class="gl-field">
      <div class="gl-label">Technique for this race <span class="req">*</span></div>
      {radio_group("technique", [("classic", "Classic"), ("skate", "Skate"), ("both", "Both")], required=True)}
    </div>
    <div class="gl-field">
      <div class="gl-label">Technique confidence</div>
      {scale_group("technique_confidence")}
      <div class="gl-hint">1 means shaky. 5 means confident.</div>
    </div>
  ''')}

  {section(3, "Experience", '''
    <div class="gl-field-row">
      <div class="gl-field">
        <label for="yearsSnow">Years on snow</label>
        <input id="yearsSnow" name="years_on_snow" type="number" min="0" step="1">
      </div>
      <div class="gl-field">
        <label for="structuredYears">Years structured training</label>
        <input id="structuredYears" name="structured_training_years" type="number" min="0" step="1">
      </div>
    </div>
    <div class="gl-field">
      <label for="recentHours">Typical weekly hours last 3 months</label>
      <input id="recentHours" name="recent_weekly_hours" type="number" min="0" step="0.5">
    </div>
  ''')}

  {section(4, "Schedule", '''
    <div class="gl-field-row">
      <div class="gl-field">
        <label for="weeklyHours">Hours/week available <span class="req">*</span></label>
        <input id="weeklyHours" name="weekly_hours" type="number" min="1" step="0.5" required>
      </div>
      <div class="gl-field">
        <label for="daysWeek">Days/week available</label>
        <input id="daysWeek" name="days_per_week" type="number" min="1" max="7" step="1">
      </div>
    </div>
    <div class="gl-field">
      <label for="longDay">Best day for the long session</label>
      <select id="longDay" name="long_session_day">
        <option value="">Select one</option>
        <option>Monday</option><option>Tuesday</option><option>Wednesday</option>
        <option>Thursday</option><option>Friday</option><option>Saturday</option><option>Sunday</option>
      </select>
    </div>
  ''')}

  {section(5, "Dry-land reality", f'''
    <div class="gl-field">
      <div class="gl-label">Rollerski access</div>
      {radio_group("rollerski_access", [("yes", "Yes"), ("no", "No")])}
    </div>
    <div class="gl-field">
      <div class="gl-label">SkiErg access</div>
      {radio_group("ski_erg_access", [("yes", "Yes"), ("no", "No")])}
    </div>
    <div class="gl-field">
      <div class="gl-label">Gym or strength access</div>
      {radio_group("strength_access", [("yes", "Yes"), ("no", "No")])}
    </div>
    <div class="gl-field">
      <div class="gl-label">Running tolerance</div>
      {radio_group("running_tolerance", [("none", "None"), ("some", "Some"), ("lots", "Lots")])}
    </div>
  ''')}

  {section(6, "Recent form", '''
    <div class="gl-field">
      <label for="recentResult">Recent race result or time trial</label>
      <textarea id="recentResult" name="recent_result" maxlength="900"></textarea>
    </div>
    <div class="gl-field">
      <label for="restingHr">Resting HR if known</label>
      <input id="restingHr" name="resting_hr" type="number" min="25" max="120" step="1">
    </div>
  ''')}

  {section(7, "Constraints", '''
    <div class="gl-field">
      <label for="injuries">Injuries or movements to avoid</label>
      <textarea id="injuries" name="injuries" maxlength="900"></textarea>
    </div>
    <div class="gl-field">
      <label for="constraints">Work/family constraints</label>
      <textarea id="constraints" name="constraints" maxlength="900"></textarea>
    </div>
    <div class="gl-field-row">
      <div class="gl-field">
        <label for="homeAltitude">Altitude where you live</label>
        <input id="homeAltitude" name="home_altitude" type="text">
      </div>
      <div class="gl-field">
        <label for="raceAltitude">Altitude where you race</label>
        <input id="raceAltitude" name="race_altitude" type="text">
      </div>
    </div>
  ''')}

  {section(8, "Email and notes", '''
    <div class="gl-field">
      <label for="email">Email <span class="req">*</span></label>
      <input id="email" name="email" type="email" required autocomplete="email">
    </div>
    <div class="gl-field">
      <label for="planNotes">Anything the plan must work around</label>
      <textarea id="planNotes" name="plan_workarounds" maxlength="1200"></textarea>
    </div>
  ''')}

  <div class="gl-submit-wrap">
    <button type="submit" class="gl-submit-btn" id="submitBtn">Send questionnaire</button>
    <p class="gl-submit-note">You'll get your plan details and payment link by email, usually within a day.</p>
  </div>
</form>"""


def build_cookie_banner() -> str:
    return """<div class="gl-cookie-consent" id="gl-cookie-consent">
  <div class="gl-cookie-inner">
    <div class="gl-cookie-text">We use analytics cookies to improve XC Ski Labs.</div>
    <div class="gl-cookie-actions">
      <button type="button" id="gl-cookie-accept">Accept</button>
      <button type="button" id="gl-cookie-decline">Decline</button>
    </div>
  </div>
</div>"""


def build_questionnaire_js(slug_map: dict[str, str], race_details: dict[str, dict[str, Any]]) -> str:
    return f"""<script>
(function() {{
  'use strict';
  var STORAGE_KEY = 'xcskilabs_plan_intake_v2';
  var TOTAL_SECTIONS = {TOTAL_SECTIONS};
  var races = {_safe_json_for_script(slug_map, separators=(',', ':'))};
  var raceDetails = {_safe_json_for_script(race_details, separators=(',', ':'))};
  var params = new URLSearchParams(window.location.search);
  var submitted = params.get('submitted');
  var form = document.getElementById('planIntake');
  var raceInput = document.getElementById('targetRace');
  var raceSlugInput = document.getElementById('raceSlug');
  var dateInput = document.getElementById('raceDate');
  var distanceSelect = document.getElementById('raceDistance');
  var progressFill = document.getElementById('progressFill');
  var progressPct = document.getElementById('progressPct');
  var saveIndicator = document.getElementById('saveIndicator');

  function setDistanceOptions(detail) {{
    if (!distanceSelect) return;
    var current = distanceSelect.value;
    distanceSelect.innerHTML = '<option value="">Select if known</option>';
    var options = [];
    if (detail && Array.isArray(detail.distance_options)) options = detail.distance_options;
    if (!options.length && detail && detail.distance_km) options = [String(detail.distance_km) + 'km'];
    options.forEach(function(option) {{
      var opt = document.createElement('option');
      opt.value = String(option);
      opt.textContent = String(option);
      distanceSelect.appendChild(opt);
    }});
    if (current) distanceSelect.value = current;
  }}

  function applyRacePrefill() {{
    var raceSlug = params.get('race');
    if (!raceSlug || !races[raceSlug]) return;
    raceInput.value = races[raceSlug];
    raceSlugInput.value = raceSlug;
    var detail = raceDetails[raceSlug] || {{}};
    if (detail.date && !dateInput.value) dateInput.value = detail.date;
    setDistanceOptions(detail);
    if (detail.discipline) {{
      var tech = form.querySelector('input[name="technique"][value="' + detail.discipline + '"]');
      if (tech) tech.checked = true;
    }}
  }}

  function getFormData() {{
    var data = {{}};
    Array.prototype.forEach.call(form.elements, function(el) {{
      if (!el.name || el.name.charAt(0) === '_') return;
      if (el.type === 'checkbox') {{
        if (!data[el.name]) data[el.name] = [];
        if (el.checked) data[el.name].push(el.value);
      }} else if (el.type === 'radio') {{
        if (el.checked) data[el.name] = el.value;
      }} else {{
        data[el.name] = el.value;
      }}
    }});
    return data;
  }}

  function restoreFormData() {{
    var raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    var data;
    try {{ data = JSON.parse(raw); }} catch(e) {{ return; }}
    Array.prototype.forEach.call(form.elements, function(el) {{
      if (!el.name || el.name.charAt(0) === '_') return;
      if (el.type === 'checkbox') {{
        el.checked = Array.isArray(data[el.name]) && data[el.name].indexOf(el.value) !== -1;
      }} else if (el.type === 'radio') {{
        el.checked = data[el.name] === el.value;
      }} else if (data[el.name] !== undefined) {{
        el.value = data[el.name];
      }}
    }});
  }}

  function saveFormData() {{
    try {{ localStorage.setItem(STORAGE_KEY, JSON.stringify(getFormData())); }} catch(e) {{}}
    if (saveIndicator) {{
      saveIndicator.classList.add('show');
      clearTimeout(saveIndicator._timeout);
      saveIndicator._timeout = setTimeout(function() {{ saveIndicator.classList.remove('show'); }}, 1000);
    }}
  }}

  function fieldHasValue(inp) {{
    if (inp.type === 'hidden') return false;
    if (inp.type === 'checkbox' || inp.type === 'radio') return inp.checked;
    return inp.value && inp.value.trim() !== '';
  }}

  function updateProgress() {{
    var sections = document.querySelectorAll('.gl-section');
    var filled = 0;
    Array.prototype.forEach.call(sections, function(section) {{
      var inputs = section.querySelectorAll('input, select, textarea');
      var hasContent = Array.prototype.some.call(inputs, fieldHasValue);
      if (hasContent) filled += 1;
    }});
    var pct = Math.round((filled / TOTAL_SECTIONS) * 100);
    if (progressFill) progressFill.style.width = pct + '%';
    if (progressPct) progressPct.textContent = pct + '%';
  }}

  function updateConditionals() {{
    var slug = raceSlugInput.value;
    setDistanceOptions(raceDetails[slug] || null);
  }}

  if (submitted === '1') {{
    var page = document.querySelector('.gl-page');
    if (page) {{
      page.innerHTML = '<div class="gl-success-message"><h2>Questionnaire received.</h2><p>Payment received or not, we read the intake before building the plan. Check your email for the next step.</p><a href="/training-plans/">Back to training plans</a></div>';
    }}
    return;
  }}

  restoreFormData();
  applyRacePrefill();
  updateProgress();
  updateConditionals();

  form.addEventListener('input', function() {{
    saveFormData();
    updateProgress();
  }});
  form.addEventListener('change', function() {{
    saveFormData();
    updateProgress();
    updateConditionals();
  }});
  form.addEventListener('submit', function() {{
    localStorage.removeItem(STORAGE_KEY);
    if (typeof gtag === 'function') gtag('event', 'generate_lead', {{ form_name: 'custom_plan_intake' }});
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

  var banner = document.getElementById('gl-cookie-consent');
  if (banner && !/xl_consent=/.test(document.cookie)) banner.classList.add('visible');
  var accept = document.getElementById('gl-cookie-accept');
  var decline = document.getElementById('gl-cookie-decline');
  if (accept) accept.addEventListener('click', function() {{
    document.cookie='xl_consent=accepted;path=/;max-age=31536000;SameSite=Lax';
    banner.classList.remove('visible');
    if(typeof gtag==='function') gtag('consent','update',{{'analytics_storage':'granted'}});
  }});
  if (decline) decline.addEventListener('click', function() {{
    document.cookie='xl_consent=declined;path=/;max-age=31536000;SameSite=Lax';
    banner.classList.remove('visible');
    if(typeof gtag==='function') gtag('consent','update',{{'analytics_storage':'denied'}});
  }});
}})();
</script>"""


def generate_page(output_dir: Path = OUTPUT_DIR, race_index: Path = RACE_INDEX) -> Path:
    slug_map = load_race_slug_map(race_index)
    race_details = load_race_details(slug_map)
    out_path = output_dir / "questionnaire" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Custom Plan Intake | XC Ski Labs</title>
  <meta name="description" content="Tell XC Ski Labs about your target race, technique, schedule, training access, and constraints for a custom ski training plan.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/questionnaire/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
  {build_ga4()}
  <style>{build_css()}</style>
</head>
<body>
<a href="#questionnaire" class="gl-skip-link">Skip to questionnaire</a>
{build_nav()}
<main class="gl-page" id="questionnaire">
  <header class="gl-page-header">
    <div class="gl-kicker">Custom plan intake</div>
    <h1>Tell me about your race.</h1>
    <p>Race, technique, schedule, dry-land tools, and the constraints the plan needs to respect.</p>
  </header>
  <div class="gl-progress-wrap" aria-live="polite">
    <div class="gl-progress-inner">
      <div class="gl-progress-label">Progress</div>
      <div class="gl-progress-track"><div class="gl-progress-fill" id="progressFill"></div></div>
      <div class="gl-progress-pct" id="progressPct">0%</div>
      <div class="gl-save-indicator" id="saveIndicator">Saved</div>
    </div>
  </div>
  {build_form()}
</main>
<footer class="gl-footer">
  <a href="/training-plans/">Back to training plans</a>
</footer>
{build_cookie_banner()}
{build_questionnaire_js(slug_map, race_details)}
</body>
</html>
"""
    out_path.write_text(page, encoding="utf-8")
    print(f"Generated: {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate XC Ski Labs plan questionnaire")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--race-index", default=str(RACE_INDEX))
    args = parser.parse_args()
    generate_page(Path(args.output_dir), Path(args.race_index))


if __name__ == "__main__":
    main()
