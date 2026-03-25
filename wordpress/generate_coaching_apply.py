#!/usr/bin/env python3
"""
XC Ski Labs — Coaching Intake Form Generator

Generates a multi-section questionnaire for athletes applying for
1-on-1 XC ski coaching. Self-contained HTML with localStorage
save/resume, progress tracking, and conditional field visibility.

Usage:
    python wordpress/generate_coaching_apply.py
    python wordpress/generate_coaching_apply.py --output-dir output
"""

import html
import json
import os
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

TOTAL_SECTIONS = 12
FORM_ACTION = "https://formsubmit.co/coaching@xcskilabs.com"
FORM_SUBJECT = "New Coaching Application \u2014 XC Ski Labs"


# ── Helpers ────────────────────────────────────────────────────

def esc(text) -> str:
    """HTML-escape a string. Safe for None/empty."""
    if text is None or text == "":
        return ""
    return html.escape(str(text))


# ── CSS ────────────────────────────────────────────────────────

def build_css() -> str:
    """Build the complete CSS for the coaching intake form."""
    return """
:root {
  /* Primary */
  --gl-nordic-night: #1a2332;
  --gl-fjord-blue: #2b4c7e;
  --gl-deep-powder: #354f6e;
  --gl-slate-steel: #4a5568;

  /* Accents */
  --gl-aurora-green: #1b7260;
  --gl-aurora-green-hover: #15604f;
  --gl-aurora-violet: #7b5ea7;
  --gl-wax-orange: #b34a1a;
  --gl-glacier-teal: #357a88;

  /* Neutrals & Backgrounds */
  --gl-birch-bark: #d4cdc4;
  --gl-silver-mist: #9ca8b8;
  --gl-frost-white: #e8edf2;
  --gl-ice-paper: #f0f3f7;

  /* Typography */
  --gl-font-data: 'Sometype Mono', monospace;
  --gl-font-editorial: 'Source Serif 4', serif;

  /* Borders (neo-brutalist) */
  --gl-border-width: 2px;
  --gl-border-heavy: 3px;
  --gl-border-color: var(--gl-nordic-night);
}

*, *::before, *::after {
  box-sizing: border-box;
  border-radius: 0 !important;
  box-shadow: none !important;
}

body {
  margin: 0;
  padding: 0;
  background: var(--gl-ice-paper);
  color: var(--gl-nordic-night);
  font-family: var(--gl-font-editorial);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* ── Nav ──────────────────────────────────────── */

.gl-nav {
  background: var(--gl-nordic-night);
  border-bottom: var(--gl-border-heavy) solid var(--gl-fjord-blue);
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.gl-nav-brand {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-frost-white);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 2px;
}

.gl-nav-links {
  display: flex;
  gap: 20px;
  margin-left: auto;
}

.gl-nav-links a {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  color: var(--gl-silver-mist);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: color 0.15s;
}

.gl-nav-links a:hover {
  color: var(--gl-frost-white);
}

.gl-nav-links a.active {
  color: var(--gl-frost-white);
  border-bottom: 2px solid var(--gl-aurora-green);
  padding-bottom: 2px;
}

/* ── Page Layout ─────────────────────────────── */

.gl-page {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 20px 80px;
}

/* ── Page Header ─────────────────────────────── */

.gl-page-header {
  padding: 48px 0 32px;
  border-bottom: var(--gl-border-width) solid var(--gl-birch-bark);
  margin-bottom: 32px;
}

.gl-page-header h1 {
  font-family: var(--gl-font-editorial);
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 12px;
  line-height: 1.2;
}

.gl-page-header p {
  font-size: 1.05rem;
  color: var(--gl-slate-steel);
  margin: 0;
  max-width: 600px;
  line-height: 1.6;
}

/* ── Progress Bar ────────────────────────────── */

.gl-progress-wrap {
  position: sticky;
  top: 0;
  z-index: 100;
  background: var(--gl-frost-white);
  border-bottom: var(--gl-border-width) solid var(--gl-birch-bark);
  padding: 12px 20px;
}

.gl-progress-inner {
  max-width: 760px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.gl-progress-label {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--gl-slate-steel);
  white-space: nowrap;
  min-width: 90px;
}

.gl-progress-track {
  flex: 1;
  height: 8px;
  background: var(--gl-birch-bark);
  border: 1px solid var(--gl-silver-mist);
  overflow: hidden;
}

.gl-progress-fill {
  height: 100%;
  width: 0%;
  background: var(--gl-aurora-green);
  transition: width 0.3s ease;
}

.gl-progress-pct {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-slate-steel);
  min-width: 32px;
  text-align: right;
}

/* ── Form Sections ───────────────────────────── */

.gl-section {
  margin-bottom: 40px;
  border: var(--gl-border-width) solid var(--gl-border-color);
  background: white;
}

.gl-section-header {
  background: var(--gl-nordic-night);
  color: var(--gl-frost-white);
  padding: 14px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.gl-section-num {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  background: var(--gl-fjord-blue);
  color: white;
  padding: 3px 8px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.gl-section-title {
  font-family: var(--gl-font-editorial);
  font-size: 1.1rem;
  font-weight: 600;
}

.gl-section-body {
  padding: 24px 20px;
}

/* ── Form Fields ─────────────────────────────── */

.gl-field {
  margin-bottom: 20px;
}

.gl-field:last-child {
  margin-bottom: 0;
}

.gl-field label {
  display: block;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
  color: var(--gl-nordic-night);
}

.gl-field label .req {
  color: var(--gl-wax-orange);
  font-weight: 700;
}

.gl-field input[type="text"],
.gl-field input[type="email"],
.gl-field input[type="number"],
.gl-field input[type="date"],
.gl-field select,
.gl-field textarea {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  border: var(--gl-border-width) solid var(--gl-border-color);
  padding: 10px 12px;
  width: 100%;
  background: white;
  color: var(--gl-nordic-night);
  transition: outline 0.1s;
}

.gl-field input:focus,
.gl-field select:focus,
.gl-field textarea:focus {
  outline: var(--gl-border-heavy) solid var(--gl-fjord-blue);
  outline-offset: -1px;
}

.gl-field textarea {
  min-height: 100px;
  resize: vertical;
}

.gl-field .gl-hint {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-slate-steel);
  margin-top: 4px;
}

.gl-field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.gl-field-row-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 16px;
}

/* ── Radio & Checkbox Groups ─────────────────── */

.gl-radio-group,
.gl-checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}

.gl-radio-group label,
.gl-checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  cursor: pointer;
  padding: 8px 12px;
  border: 1px solid var(--gl-birch-bark);
  transition: background 0.1s, border-color 0.1s;
}

.gl-radio-group label:hover,
.gl-checkbox-group label:hover {
  background: var(--gl-frost-white);
  border-color: var(--gl-fjord-blue);
}

.gl-radio-group input[type="radio"],
.gl-checkbox-group input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--gl-aurora-green);
  flex-shrink: 0;
}

/* Horizontal checkbox layout for compact lists */
.gl-checkbox-group.gl-checkbox-horizontal {
  flex-direction: row;
  flex-wrap: wrap;
  gap: 8px;
}

.gl-checkbox-group.gl-checkbox-horizontal label {
  flex: 0 0 auto;
}

/* ── Scale Rating ────────────────────────────── */

.gl-scale-group {
  display: flex;
  gap: 0;
  margin-top: 4px;
}

.gl-scale-group label {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 4px;
  border: 1px solid var(--gl-birch-bark);
  border-right: none;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 400;
  text-transform: none;
  letter-spacing: 0;
  cursor: pointer;
  text-align: center;
  transition: background 0.1s;
}

.gl-scale-group label:last-child {
  border-right: 1px solid var(--gl-birch-bark);
}

.gl-scale-group label:hover {
  background: var(--gl-frost-white);
}

.gl-scale-group input[type="radio"] {
  accent-color: var(--gl-aurora-green);
}

.gl-scale-labels {
  display: flex;
  justify-content: space-between;
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  color: var(--gl-slate-steel);
  margin-top: 4px;
}

/* ── Conditional Fields ──────────────────────── */

.gl-conditional {
  display: none;
  margin-top: 12px;
  padding-left: 16px;
  border-left: 3px solid var(--gl-aurora-green);
}

.gl-conditional.visible {
  display: block;
}

/* ── Submit ───────────────────────────────────── */

.gl-submit-wrap {
  margin-top: 40px;
  padding: 32px 0;
  border-top: var(--gl-border-width) solid var(--gl-birch-bark);
  text-align: center;
}

.gl-submit-btn {
  font-family: var(--gl-font-data);
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 2px;
  background: var(--gl-aurora-green);
  color: white;
  border: var(--gl-border-heavy) solid var(--gl-nordic-night);
  padding: 16px 48px;
  cursor: pointer;
  transition: background 0.15s;
}

.gl-submit-btn:hover {
  background: var(--gl-aurora-green-hover);
}

.gl-submit-note {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-slate-steel);
  margin-top: 12px;
}

/* ── Save Indicator ──────────────────────────── */

.gl-save-indicator {
  position: fixed;
  bottom: 20px;
  right: 20px;
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  background: var(--gl-nordic-night);
  color: var(--gl-frost-white);
  padding: 8px 14px;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
  z-index: 200;
}

.gl-save-indicator.show {
  opacity: 1;
}

/* ── Footer ──────────────────────────────────── */

.gl-footer {
  background: var(--gl-nordic-night);
  color: var(--gl-silver-mist);
  padding: 32px 24px;
  margin-top: 60px;
  border-top: var(--gl-border-heavy) solid var(--gl-fjord-blue);
  text-align: center;
}

.gl-footer-brand {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gl-frost-white);
  text-transform: uppercase;
  letter-spacing: 2px;
}

.gl-footer-links {
  margin-top: 12px;
  display: flex;
  justify-content: center;
  gap: 20px;
}

.gl-footer-links a {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-silver-mist);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.gl-footer-links a:hover {
  color: var(--gl-frost-white);
}

.gl-footer-copy {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  color: var(--gl-slate-steel);
  margin-top: 16px;
}

/* ── Focus Visible (a11y) ────────────────────── */

a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {
  outline: 3px solid var(--gl-wax-orange);
  outline-offset: 2px;
}

/* ── Toast ───────────────────────────────────── */

.gl-toast {
  position: fixed;
  bottom: 60px;
  right: 20px;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  background: var(--gl-wax-orange);
  color: var(--gl-frost-white);
  padding: 10px 16px;
  z-index: 300;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

.gl-toast.show {
  opacity: 1;
}

/* ── Success Message ─────────────────────────── */

.gl-success-message {
  text-align: center;
  padding: 60px 20px;
}

.gl-success-message h2 {
  font-family: var(--gl-font-editorial);
  font-size: 1.8rem;
  margin: 0 0 16px;
}

.gl-success-message p {
  font-size: 1.05rem;
  color: var(--gl-slate-steel);
  max-width: 500px;
  margin: 0 auto 24px;
  line-height: 1.6;
}

.gl-success-message a {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  color: var(--gl-aurora-green);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 1px;
  border-bottom: 2px solid var(--gl-aurora-green);
  padding-bottom: 2px;
}

/* ── Cookie Consent ──────────────────────────── */

.gl-cookie-consent {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: var(--gl-nordic-night);
  border-top: 3px solid var(--gl-wax-orange);
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
  color: var(--gl-frost-white);
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
  border: var(--gl-border-width) solid var(--gl-frost-white);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 44px;
  min-height: 44px;
}
.gl-cookie-btn.accept {
  background: var(--gl-aurora-green);
  color: var(--gl-frost-white);
}
.gl-cookie-btn.decline {
  background: transparent;
  color: var(--gl-frost-white);
}

/* ── Privacy Notice ──────────────────────────── */

.gl-privacy-notice {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-slate-steel);
  margin-bottom: 16px;
  line-height: 1.5;
}

.gl-privacy-notice a {
  color: var(--gl-aurora-green);
  text-decoration: none;
  border-bottom: 1px solid var(--gl-aurora-green);
}

/* ── Responsive ──────────────────────────────── */

@media (max-width: 640px) {
  .gl-page-header h1 { font-size: 1.5rem; }
  .gl-field-row, .gl-field-row-3 { grid-template-columns: 1fr; }
  .gl-scale-group label { font-size: 0.65rem; padding: 8px 2px; }
  .gl-nav { padding: 12px 16px; gap: 12px; }
  .gl-nav-links { gap: 12px; }
  .gl-section-body { padding: 20px 16px; }
  .gl-submit-btn { width: 100%; padding: 16px 24px; }
  .gl-checkbox-group.gl-checkbox-horizontal { flex-direction: column; }
}

@media (max-width: 400px) {
  .gl-page { padding: 0 12px 60px; }
  .gl-page-header { padding: 32px 0 24px; }
  .gl-page-header h1 { font-size: 1.3rem; }
  .gl-section-header { padding: 12px 14px; flex-wrap: wrap; }
  .gl-section-body { padding: 16px 14px; }
  .gl-nav-links { gap: 8px; }
  .gl-nav-links a { font-size: 0.65rem; }
  .gl-scale-group { flex-wrap: wrap; }
  .gl-scale-group label { flex: 0 0 calc(20% - 0px); border-right: 1px solid var(--gl-birch-bark); }
}
"""


# ── Section Builders ───────────────────────────────────────────

def build_section(num: int, title: str, fields_html: str) -> str:
    """Wrap fields in a numbered section container."""
    return f"""
<div class="gl-section" data-section="{num}">
  <div class="gl-section-header">
    <span class="gl-section-num">{num:02d}</span>
    <span class="gl-section-title">{esc(title)}</span>
  </div>
  <div class="gl-section-body">
    {fields_html}
  </div>
</div>"""


def _text_field(name: str, label: str, required: bool = False,
                field_type: str = "text", hint: str = "",
                placeholder: str = "", extra_attrs: str = "") -> str:
    """Generate a text/email/number/date input field."""
    req_mark = ' <span class="req">*</span>' if required else ""
    req_attr = " required" if required else ""
    ph = f' placeholder="{esc(placeholder)}"' if placeholder else ""
    extra = f" {extra_attrs}" if extra_attrs else ""
    hint_html = f'\n    <div class="gl-hint">{esc(hint)}</div>' if hint else ""
    return f"""
    <div class="gl-field">
      <label for="{esc(name)}">{label}{req_mark}</label>
      <input type="{field_type}" id="{esc(name)}" name="{esc(name)}"{ph}{req_attr}{extra}>
      {hint_html}
    </div>"""


def _textarea_field(name: str, label: str, required: bool = False,
                    hint: str = "", placeholder: str = "",
                    rows: int = 4, maxlength: int = 2000) -> str:
    """Generate a textarea field."""
    req_mark = ' <span class="req">*</span>' if required else ""
    req_attr = " required" if required else ""
    ph = f' placeholder="{esc(placeholder)}"' if placeholder else ""
    hint_html = f'\n    <div class="gl-hint">{esc(hint)}</div>' if hint else ""
    return f"""
    <div class="gl-field">
      <label for="{esc(name)}">{label}{req_mark}</label>
      <textarea id="{esc(name)}" name="{esc(name)}" rows="{rows}" maxlength="{maxlength}"{ph}{req_attr}></textarea>
      {hint_html}
    </div>"""


def _select_field(name: str, label: str, options: list[tuple[str, str]],
                  required: bool = False, hint: str = "") -> str:
    """Generate a select dropdown. Options: list of (value, display) tuples."""
    req_mark = ' <span class="req">*</span>' if required else ""
    req_attr = " required" if required else ""
    opts = '<option value="">-- Select --</option>\n'
    for val, display in options:
        opts += f'      <option value="{esc(val)}">{esc(display)}</option>\n'
    hint_html = f'\n    <div class="gl-hint">{esc(hint)}</div>' if hint else ""
    return f"""
    <div class="gl-field">
      <label for="{esc(name)}">{label}{req_mark}</label>
      <select id="{esc(name)}" name="{esc(name)}"{req_attr}>
      {opts}
      </select>
      {hint_html}
    </div>"""


def _radio_group(name: str, label: str, options: list[tuple[str, str]],
                 required: bool = False, hint: str = "") -> str:
    """Generate a radio button group."""
    req_mark = ' <span class="req">*</span>' if required else ""
    radios = ""
    for val, display in options:
        req_attr = " required" if required else ""
        radios += f"""
        <label><input type="radio" name="{esc(name)}" value="{esc(val)}"{req_attr}> {esc(display)}</label>"""
    hint_html = f'\n    <div class="gl-hint">{esc(hint)}</div>' if hint else ""
    return f"""
    <div class="gl-field">
      <label>{label}{req_mark}</label>
      <div class="gl-radio-group">{radios}
      </div>
      {hint_html}
    </div>"""


def _checkbox_group(name: str, label: str, options: list[tuple[str, str]],
                    horizontal: bool = False, hint: str = "") -> str:
    """Generate a checkbox group."""
    h_class = " gl-checkbox-horizontal" if horizontal else ""
    checks = ""
    for val, display in options:
        checks += f"""
        <label><input type="checkbox" name="{esc(name)}" value="{esc(val)}"> {esc(display)}</label>"""
    hint_html = f'\n    <div class="gl-hint">{esc(hint)}</div>' if hint else ""
    return f"""
    <div class="gl-field">
      <label>{label}</label>
      <div class="gl-checkbox-group{h_class}">{checks}
      </div>
      {hint_html}
    </div>"""


def _scale_field(name: str, label: str, low_label: str = "Beginner",
                 high_label: str = "Expert", hint: str = "") -> str:
    """Generate a 1-5 scale rating field."""
    radios = ""
    for i in range(1, 6):
        radios += f"""
        <label><input type="radio" name="{esc(name)}" value="{i}"> {i}</label>"""
    hint_html = f'\n    <div class="gl-hint">{esc(hint)}</div>' if hint else ""
    return f"""
    <div class="gl-field">
      <label>{label}</label>
      <div class="gl-scale-group">{radios}
      </div>
      <div class="gl-scale-labels">
        <span>{esc(low_label)}</span>
        <span>{esc(high_label)}</span>
      </div>
      {hint_html}
    </div>"""


# ── Individual Sections ────────────────────────────────────────

def build_section_basic_info() -> str:
    """Section 1: Basic Info."""
    fields = f"""
    <div class="gl-field-row">
      {_text_field("name", "Full Name", required=True, placeholder="First Last")}
      {_text_field("email", "Email Address", required=True, field_type="email", placeholder="you@example.com")}
    </div>
    <div class="gl-field-row-3">
      {_text_field("age", "Age", field_type="number", placeholder="e.g. 35", extra_attrs='min="16" max="100"')}
      {_select_field("sex", "Sex", [("M", "Male"), ("F", "Female"), ("Other", "Other / Prefer not to say")])}
      {_text_field("weight", "Weight (kg)", field_type="number", placeholder="e.g. 72", hint="Used for power-to-weight calculations", extra_attrs='min="30" max="200"')}
    </div>
    {_text_field("height", "Height (cm)", field_type="number", placeholder="e.g. 178", hint="Helps with equipment and pole-length recommendations", extra_attrs='min="100" max="230"')}
"""
    return build_section(1, "Basic Info", fields)


def build_section_goals() -> str:
    """Section 2: Goals."""
    fields = f"""
    {_radio_group("primary_goal", "Primary Goal", [
        ("specific_race", "Prepare for a specific race"),
        ("general_fitness", "Improve general XC ski fitness"),
        ("technique", "Technique improvement"),
        ("return_from_injury", "Return from injury"),
    ], required=True)}

    <div class="gl-conditional" id="cond-race-name">
      {_text_field("target_race", "Target Race Name", placeholder="e.g. Vasaloppet, Birkebeinerrennet", hint="The race you are training for")}
    </div>

    {_text_field("target_date", "Target Date or Race Date", field_type="date", hint="When do you need to be in peak form?")}

    {_textarea_field("goal_details", "Describe Your Goal",
                     placeholder="What does success look like for you this season? Time target, finish goal, technique milestone, or something else entirely.",
                     rows=3)}
"""
    return build_section(2, "Goals", fields)


def build_section_experience() -> str:
    """Section 3: Experience."""
    fields = f"""
    {_text_field("years_skiing", "Years of XC Skiing", field_type="number", placeholder="e.g. 5", extra_attrs='min="0" max="60"')}

    {_radio_group("discipline_pref", "Discipline Preference", [
        ("classic", "Classic"),
        ("skate", "Skate / Freestyle"),
        ("both", "Both"),
    ])}

    {_radio_group("racing_experience", "Racing Experience", [
        ("none", "None \u2014 I ski recreationally"),
        ("citizen", "Citizen racer \u2014 I enter events but don't train specifically for them"),
        ("competitive", "Competitive \u2014 I train with race goals and track results"),
        ("elite", "Elite / Former elite \u2014 national or international level"),
    ])}

    {_text_field("longest_race", "Longest Race Completed",
                 placeholder="e.g. Vasaloppet 90km, Birkebeinerrennet 54km",
                 hint="Distance and name, if applicable")}
"""
    return build_section(3, "Experience", fields)


def build_section_fitness() -> str:
    """Section 4: Current Fitness."""
    fields = f"""
    <div class="gl-field-row">
      {_text_field("weekly_hours", "Weekly Training Hours", field_type="number",
                   placeholder="e.g. 8", hint="Average hours per week, all sports", extra_attrs='min="1" max="40"')}
      {_text_field("weekly_km", "Weekly Skiing Distance (km)", field_type="number",
                   placeholder="e.g. 60", hint="During snow season, approximate", extra_attrs='min="0" max="500"')}
    </div>

    <div class="gl-field-row">
      {_text_field("vo2max", "VO2max (if known)", field_type="number",
                   placeholder="e.g. 55", hint="From a lab test or wearable estimate", extra_attrs='min="20" max="90"')}
      {_text_field("ftp", "FTP / Threshold Power (W)", field_type="number",
                   placeholder="e.g. 220", hint="From roller-ski erg or cycling, if known", extra_attrs='min="50" max="500"')}
    </div>

    {_checkbox_group("other_sports", "Other Sports You Train Regularly", [
        ("running", "Running"),
        ("cycling", "Cycling"),
        ("swimming", "Swimming"),
        ("strength", "Strength / Gym"),
        ("rowing", "Rowing / Paddling"),
        ("mountaineering", "Mountaineering / Hiking"),
        ("other", "Other"),
    ], horizontal=True)}

    {_textarea_field("fitness_notes", "Anything Else About Your Current Fitness",
                     placeholder="Recent improvements, setbacks, how you feel day-to-day, etc.",
                     rows=3)}
"""
    return build_section(4, "Current Fitness", fields)


def build_section_technique() -> str:
    """Section 5: Technique."""
    fields = f"""
    {_scale_field("classic_technique", "Classic Technique Self-Assessment",
                  low_label="Beginner", high_label="Expert",
                  hint="1 = learning the basics, 5 = biomechanically efficient at race pace")}

    {_scale_field("skate_technique", "Skate Technique Self-Assessment",
                  low_label="Beginner", high_label="Expert",
                  hint="1 = can barely V2, 5 = smooth and powerful across all gears")}

    {_radio_group("double_pole_strength", "Double Pole Strength", [
        ("weak", "Weak \u2014 I fatigue quickly and avoid flat sections"),
        ("moderate", "Moderate \u2014 I can sustain it but it is not a strength"),
        ("strong", "Strong \u2014 double pole is one of my best techniques"),
    ])}

    {_checkbox_group("technique_improve", "Areas You Want to Improve", [
        ("v1", "V1 (skate uphill)"),
        ("v2", "V2 (skate primary)"),
        ("v2a", "V2 Alternate"),
        ("diagonal", "Diagonal Stride"),
        ("double_pole", "Double Pole"),
        ("kick_dp", "Kick Double Pole"),
        ("downhill", "Downhill Technique / Tucking"),
        ("transitions", "Technique Transitions"),
    ], horizontal=True)}
"""
    return build_section(5, "Technique", fields)


def build_section_equipment() -> str:
    """Section 6: Equipment."""
    fields = f"""
    {_checkbox_group("skis_owned", "Skis You Own", [
        ("classic_race", "Classic Race"),
        ("classic_training", "Classic Training"),
        ("skate_race", "Skate Race"),
        ("skate_training", "Skate Training"),
        ("roller_skis_classic", "Roller Skis (Classic)"),
        ("roller_skis_skate", "Roller Skis (Skate)"),
    ], horizontal=True)}

    <div class="gl-field-row">
      {_radio_group("hr_monitor", "Heart Rate Monitor", [
          ("yes", "Yes"),
          ("no", "No"),
      ])}
      {_radio_group("power_meter", "Power Meter (ski or erg)", [
          ("yes", "Yes"),
          ("no", "No"),
      ])}
    </div>

    {_text_field("gps_watch", "GPS Watch Brand / Model",
                 placeholder="e.g. Garmin Fenix 7, COROS PACE 3, Polar Vantage",
                 hint="We can tailor workout exports to your device")}
"""
    return build_section(6, "Equipment", fields)


def build_section_training_access() -> str:
    """Section 7: Training Access."""
    fields = f"""
    {_text_field("snow_months", "Snow Access (months per year)", field_type="number",
                 placeholder="e.g. 5", hint="How many months can you ski on natural or artificial snow?", extra_attrs='min="0" max="12"')}

    <div class="gl-field-row-3">
      {_radio_group("roller_ski_access", "Roller Ski Access", [
          ("yes", "Yes \u2014 safe roads or paths available"),
          ("no", "No \u2014 no safe roller skiing options"),
      ])}
      {_radio_group("gym_access", "Gym Access", [
          ("yes", "Yes"),
          ("no", "No"),
      ])}
      {_radio_group("ski_tunnel", "Ski Tunnel Access", [
          ("yes", "Yes"),
          ("no", "No"),
      ])}
    </div>

    {_radio_group("terrain", "Typical Training Terrain", [
        ("flat", "Flat \u2014 mostly level skiing"),
        ("hilly", "Hilly \u2014 moderate climbs and descents"),
        ("mountainous", "Mountainous \u2014 significant elevation changes"),
    ])}
"""
    return build_section(7, "Training Access", fields)


def build_section_schedule() -> str:
    """Section 8: Schedule."""
    fields = f"""
    {_checkbox_group("preferred_days", "Preferred Training Days", [
        ("mon", "Monday"),
        ("tue", "Tuesday"),
        ("wed", "Wednesday"),
        ("thu", "Thursday"),
        ("fri", "Friday"),
        ("sat", "Saturday"),
        ("sun", "Sunday"),
    ], horizontal=True)}

    {_radio_group("time_preference", "Time of Day Preference", [
        ("morning", "Morning (before work)"),
        ("midday", "Midday"),
        ("evening", "Evening (after work)"),
        ("flexible", "Flexible / No preference"),
    ])}

    {_text_field("max_hours", "Maximum Hours Per Week", field_type="number",
                 placeholder="e.g. 10", hint="The most you can realistically commit", extra_attrs='min="1" max="40"')}

    {_textarea_field("schedule_constraints", "Travel or Work Constraints",
                     placeholder="Frequent travel, shift work, childcare windows, seasonal availability, etc.",
                     rows=3)}
"""
    return build_section(8, "Schedule", fields)


def build_section_health() -> str:
    """Section 9: Health."""
    fields = f"""
    {_textarea_field("injuries", "Current or Past Injuries",
                     placeholder="Describe any injuries, surgeries, or chronic conditions that affect training. Include timeframes if relevant.",
                     rows=3, hint="This stays confidential and helps us design safe progressions")}

    {_textarea_field("allergies", "Allergies",
                     placeholder="Food, environmental, or medication allergies",
                     rows=2)}

    {_textarea_field("medications", "Medications That Affect Training",
                     placeholder="Beta blockers, asthma inhalers, thyroid medication, etc. \u2014 anything that could affect heart rate or performance",
                     rows=2, hint="Optional but important for accurate HR zone prescription")}
"""
    return build_section(9, "Health", fields)


def build_section_nutrition() -> str:
    """Section 10: Nutrition."""
    fields = f"""
    {_radio_group("nutrition_approach", "Current Nutrition Approach", [
        ("none", "No particular approach \u2014 I eat what I want"),
        ("casual", "Casual attention \u2014 I try to eat well around training"),
        ("structured", "Structured \u2014 I track macros or follow a plan"),
    ])}

    {_textarea_field("race_fueling", "Race Fueling Experience",
                     placeholder="What do you eat/drink before and during long races or training? Any issues with bonking, stomach problems, etc.?",
                     rows=3)}

    {_radio_group("hydration", "Hydration Habits During Training", [
        ("minimal", "Minimal \u2014 I often forget or skip it"),
        ("moderate", "Moderate \u2014 I drink when thirsty"),
        ("diligent", "Diligent \u2014 I plan hydration with electrolytes"),
    ])}
"""
    return build_section(10, "Nutrition", fields)


def build_section_coaching_prefs() -> str:
    """Section 11: Coaching Preferences."""
    fields = f"""
    {_checkbox_group("comm_preference", "Communication Preference", [
        ("email", "Email"),
        ("app", "Training app (TrainingPeaks, Intervals.icu, etc.)"),
        ("video", "Video calls"),
        ("chat", "Chat / Messaging"),
    ], hint="Select all that work for you")}

    {_radio_group("feedback_freq", "Preferred Feedback Frequency", [
        ("daily", "Daily check-ins"),
        ("weekly", "Weekly review and adjustment"),
        ("biweekly", "Every two weeks"),
    ])}

    {_textarea_field("prev_coaching", "Previous Coaching Experience",
                     placeholder="Have you worked with a coach before? What worked, what didn't? What are you looking for this time?",
                     rows=3)}
"""
    return build_section(11, "Coaching Preferences", fields)


def build_section_anything_else() -> str:
    """Section 12: Anything Else."""
    fields = f"""
    {_textarea_field("anything_else", "Anything Else We Should Know",
                     placeholder="Motivation, fears, past experiences, what you love about skiing, what frustrates you, specific questions \u2014 anything that helps us understand you as an athlete.",
                     rows=6)}
"""
    return build_section(12, "Anything Else", fields)


# ── Progress Bar ───────────────────────────────────────────────

def build_progress_bar() -> str:
    """Build the sticky progress bar."""
    return """
<div class="gl-progress-wrap">
  <div class="gl-progress-inner">
    <span class="gl-progress-label">Progress</span>
    <div class="gl-progress-track">
      <div class="gl-progress-fill" id="progressFill"></div>
    </div>
    <span class="gl-progress-pct" id="progressPct">0%</span>
  </div>
</div>"""


# ── Navigation ─────────────────────────────────────────────────

def build_nav() -> str:
    """Build the site navigation bar."""
    return """
<nav class="gl-nav">
  <a href="/" class="gl-nav-brand">XC Ski Labs</a>
  <div class="gl-nav-links">
    <a href="/">Home</a>
    <a href="/search/">Search</a>
    <a href="/training/">Training Plans</a>
    <a href="/coaching/apply/" class="active">Coaching</a>
  </div>
</nav>"""


# ── Footer ─────────────────────────────────────────────────────

def build_footer() -> str:
    """Build the page footer."""
    return """
<footer class="gl-footer">
  <div class="gl-footer-brand">XC Ski Labs</div>
  <div class="gl-footer-links">
    <a href="/">Home</a>
    <a href="/search/">Search</a>
    <a href="/training/">Training Plans</a>
    <a href="/coaching/apply/">Coaching</a>
  </div>
  <div class="gl-footer-copy">&copy; 2026 XC Ski Labs. All rights reserved.</div>
</footer>"""


# ── Cookie Consent ─────────────────────────────────────────────

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


# ── JavaScript ─────────────────────────────────────────────────

def build_form_js() -> str:
    """Build the JavaScript for localStorage persistence, progress, and conditional fields."""
    return """
<script>
(function() {
  'use strict';

  var STORAGE_KEY = 'xcskilabs_coaching_form';
  var TOTAL_SECTIONS = """ + str(TOTAL_SECTIONS) + """;
  var form = document.getElementById('coachingForm');
  var progressFill = document.getElementById('progressFill');
  var progressPct = document.getElementById('progressPct');
  var saveIndicator = document.getElementById('saveIndicator');

  // ── localStorage Save / Restore ─────────────────────────

  function getFormData() {
    var data = {};
    var elements = form.elements;
    for (var i = 0; i < elements.length; i++) {
      var el = elements[i];
      if (!el.name || el.name.startsWith('_')) continue;

      if (el.type === 'checkbox') {
        if (!data[el.name]) data[el.name] = [];
        if (el.checked) data[el.name].push(el.value);
      } else if (el.type === 'radio') {
        if (el.checked) data[el.name] = el.value;
      } else {
        data[el.name] = el.value;
      }
    }
    return data;
  }

  function restoreFormData() {
    var raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    try {
      var data = JSON.parse(raw);
    } catch(e) { return; }

    var elements = form.elements;
    for (var i = 0; i < elements.length; i++) {
      var el = elements[i];
      if (!el.name || el.name.startsWith('_')) continue;

      if (el.type === 'checkbox') {
        var vals = data[el.name];
        if (Array.isArray(vals)) {
          el.checked = vals.indexOf(el.value) !== -1;
        }
      } else if (el.type === 'radio') {
        el.checked = (data[el.name] === el.value);
      } else if (data[el.name] !== undefined) {
        el.value = data[el.name];
      }
    }
  }

  function saveFormData() {
    var data = getFormData();
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch(e) {
      showToast('Storage full \u2014 please submit now');
    }
    showSaveIndicator();
  }

  function showSaveIndicator() {
    saveIndicator.classList.add('show');
    clearTimeout(saveIndicator._timeout);
    saveIndicator._timeout = setTimeout(function() {
      saveIndicator.classList.remove('show');
    }, 1200);
  }

  // ── Progress Tracking ───────────────────────────────────

  function updateProgress() {
    var sections = document.querySelectorAll('.gl-section');
    var filled = 0;

    for (var s = 0; s < sections.length; s++) {
      var section = sections[s];
      var inputs = section.querySelectorAll('input, select, textarea');
      var hasContent = false;

      for (var j = 0; j < inputs.length; j++) {
        var inp = inputs[j];
        if (inp.type === 'hidden') continue;
        if (inp.type === 'checkbox' || inp.type === 'radio') {
          if (inp.checked) { hasContent = true; break; }
        } else {
          if (inp.value && inp.value.trim() !== '') { hasContent = true; break; }
        }
      }

      if (hasContent) filled++;
    }

    var pct = Math.round((filled / TOTAL_SECTIONS) * 100);
    progressFill.style.width = pct + '%';
    progressPct.textContent = pct + '%';
  }

  // ── Conditional Visibility ──────────────────────────────

  function updateConditionals() {
    // Show race name field only when goal is "specific_race"
    var goalRadios = form.querySelectorAll('input[name="primary_goal"]');
    var raceNameCond = document.getElementById('cond-race-name');
    var showRaceName = false;

    for (var i = 0; i < goalRadios.length; i++) {
      if (goalRadios[i].checked && goalRadios[i].value === 'specific_race') {
        showRaceName = true;
        break;
      }
    }

    if (raceNameCond) {
      if (showRaceName) {
        raceNameCond.classList.add('visible');
      } else {
        raceNameCond.classList.remove('visible');
      }
    }
  }

  // ── Event Listeners ─────────────────────────────────────

  form.addEventListener('input', function() {
    saveFormData();
    updateProgress();
    updateConditionals();
  });

  form.addEventListener('change', function() {
    saveFormData();
    updateProgress();
    updateConditionals();
  });

  // Double-submit protection and clear localStorage on submit
  form.addEventListener('submit', function() {
    localStorage.removeItem(STORAGE_KEY);
    var btn = document.getElementById('submitBtn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'SUBMITTING...';
      setTimeout(function() {
        btn.disabled = false;
        btn.textContent = 'Submit Application';
      }, 5000);
    }
  });

  // ── Toast ───────────────────────────────────────────────

  function showToast(message) {
    var toast = document.getElementById('glToast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.add('show');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(function() {
      toast.classList.remove('show');
    }, 4000);
  }

  // ── Submitted Check ────────────────────────────────────

  if (window.location.search.indexOf('submitted=true') !== -1) {
    var formEl = document.getElementById('coachingForm');
    var headerEl = document.querySelector('.gl-page-header');
    var progressEl = document.querySelector('.gl-progress-wrap');
    if (formEl) formEl.style.display = 'none';
    if (headerEl) headerEl.style.display = 'none';
    if (progressEl) progressEl.style.display = 'none';

    var successDiv = document.createElement('div');
    successDiv.className = 'gl-success-message';
    successDiv.innerHTML = '<h2>Application Received</h2><p>Thank you for applying. We review applications within 48 hours and will reply by email.</p><a href="/">Back to Home</a>';
    var page = document.querySelector('.gl-page');
    if (page) page.appendChild(successDiv);
    return;
  }

  // ── Init ────────────────────────────────────────────────

  restoreFormData();
  updateProgress();
  updateConditionals();

})();
</script>"""


# ── Page Generator ─────────────────────────────────────────────

def generate_page(output_dir: Path = None) -> Path:
    """Generate the coaching intake form page."""
    if output_dir is None:
        output_dir = OUTPUT_DIR

    out_path = output_dir / "coaching" / "apply" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    sections = [
        build_section_basic_info(),
        build_section_goals(),
        build_section_experience(),
        build_section_fitness(),
        build_section_technique(),
        build_section_equipment(),
        build_section_training_access(),
        build_section_schedule(),
        build_section_health(),
        build_section_nutrition(),
        build_section_coaching_prefs(),
        build_section_anything_else(),
    ]

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Coaching Application | XC Ski Labs</title>
  <meta name="description" content="Apply for 1-on-1 XC ski coaching with XC Ski Labs. Detailed intake form covering goals, experience, technique, and training access.">
  <meta name="robots" content="noindex, nofollow">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap" rel="stylesheet">
  <style>{build_css()}</style>
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-3JQLSQLPPM"></script>
  <script>
  window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
  (function(){{var c=(document.cookie.match(/xl_consent=([^;]+)/)||[])[1];
  if(c==='declined')return;gtag('js',new Date());gtag('config','G-3JQLSQLPPM')}})();
  </script>
</head>
<body>

{build_nav()}

{build_progress_bar()}

<main class="gl-page">

  <div class="gl-page-header">
    <h1>Coaching Application</h1>
    <p>Tell us about yourself, your skiing, and your goals. The more detail you provide, the better we can tailor your coaching experience. Your responses are saved automatically and will be here if you need to come back.</p>
  </div>

  <form id="coachingForm" action="{esc(FORM_ACTION)}" method="POST">
    <input type="hidden" name="_subject" value="{esc(FORM_SUBJECT)}">
    <input type="hidden" name="_captcha" value="false">
    <input type="hidden" name="_template" value="table">
    <input type="hidden" name="_next" value="https://xcskilabs.com/coaching/apply/?submitted=true">

    {"".join(sections)}

    <div class="gl-submit-wrap">
      <p class="gl-privacy-notice">By submitting this form, you agree to our <a href="/privacy/">Privacy Policy</a>. Your data is used solely for coaching purposes.</p>
      <button type="submit" class="gl-submit-btn" id="submitBtn">Submit Application</button>
      <div class="gl-submit-note">We review applications within 48 hours and will reply by email.</div>
    </div>
  </form>

</main>

<div class="gl-save-indicator" id="saveIndicator">Draft saved</div>
<div class="gl-toast" id="glToast"></div>

{build_footer()}

{build_cookie_consent()}

{build_form_js()}

</body>
</html>"""

    out_path.write_text(page_html, encoding="utf-8")
    return out_path


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate XC Ski Labs coaching intake form")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Output directory (default: project output/)")
    args = parser.parse_args()

    out = generate_page(output_dir=args.output_dir)
    print(f"Generated: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")
