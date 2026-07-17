#!/usr/bin/env python3
"""
XC Ski Labs guide cluster generator.

Builds the Wax Bench static guide pages:
  - output/guide/index.html
  - output/guide/{chapter-id}/index.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
GUIDE_JSON = PROJECT_ROOT / "guide" / "xc-guide-content.json"
OUTPUT_DIR = PROJECT_ROOT / "output" / "guide"
RACE_DATA_DIR = PROJECT_ROOT / "race-data"

sys.path.insert(0, str(SCRIPT_DIR))
from generate_race_pages import (  # noqa: E402
    _safe_json_for_script,
    build_cookie_consent,
    build_footer,
    build_ga4_snippet,
    build_interactions_js,
    build_nav_header,
    build_product_ladder,
    build_sticky_js,
    build_css as build_race_css,
    esc,
)


CITE_RE = re.compile(r"\[\^([A-Za-z0-9_.-]+)\]")


def load_content(path: Path = GUIDE_JSON) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _slug_set(data_dir: Path = RACE_DATA_DIR) -> set[str]:
    return {p.stem for p in data_dir.glob("*.json") if p.name != "_schema.json"}


def _plain(text: Any) -> str:
    out = "" if text is None else str(text)
    out = out.replace("honestly", "plainly").replace("Honestly", "Plainly")
    out = out.replace("honest review", "rated review").replace("Honest review", "Rated review")
    return out


def _md_inline(text: Any, source_map: dict[str, int] | None = None) -> str:
    out = esc(_plain(text))

    def repl(match: re.Match[str]) -> str:
        sid = match.group(1)
        num = source_map.get(sid) if source_map else None
        if num is None:
            # unknown source id — render nothing visible rather than a raw slug
            return f'<sup><a class="gl-cite gl-cite--missing" href="#sources">[?]</a></sup>'
        return f'<sup><a class="gl-cite" href="#source-{esc(sid)}" id="ref-{esc(sid)}">{num}</a></sup>'

    return CITE_RE.sub(repl, out)


def _paragraphs(text: Any, source_map: dict[str, int] | None = None) -> str:
    parts = [p.strip() for p in _plain(text).split("\n\n") if p.strip()]
    return "".join(f'<p class="gl-section-prose">{_md_inline(p, source_map)}</p>' for p in parts)


def _estimate_read_time(chapter: dict[str, Any]) -> int:
    chars = 0
    extra = 0
    for section in chapter.get("sections", []):
        for block in section.get("blocks", []):
            chars += len(json.dumps(block))
            if block.get("type") not in {"prose", "callout"}:
                extra += 1
    return max(4, round(chars / 1000) + extra)


def render_guide_plate(chapter: dict[str, Any]) -> str:
    num = int(chapter["number"])
    motifs = {
        1: '<path class="gl-plate-ridge" d="M154 74C190 42 224 88 262 58S318 70 342 40"/><path class="gl-plate-route" d="M64 160C110 118 154 184 204 132S284 96 326 126"/>',
        2: '<path class="gl-plate-ridge" d="M148 58H324"/><rect class="gl-plate-bar" x="154" y="86" width="126" height="16"/><rect class="gl-plate-bar gl-plate-bar--quiet" x="154" y="120" width="168" height="16"/><rect class="gl-plate-bar gl-plate-bar--quiet" x="154" y="154" width="84" height="16"/>',
        3: '<rect class="gl-plate-zone" x="154" y="78" width="36" height="86"/><rect class="gl-plate-zone gl-plate-zone--quiet" x="198" y="78" width="36" height="86"/><rect class="gl-plate-zone gl-plate-zone--quiet" x="242" y="78" width="36" height="86"/><rect class="gl-plate-zone gl-plate-zone--quiet" x="286" y="78" width="36" height="86"/>',
        4: '<path class="gl-plate-route" d="M156 162V76L214 116L272 76V162"/><path class="gl-plate-ridge" d="M146 182H328"/>',
        5: '<path class="gl-plate-ridge" d="M150 116H326"/><path class="gl-plate-ridge gl-plate-ridge--quiet" d="M178 76V156M238 76V156M298 76V156"/><rect class="gl-plate-square" x="174" y="110" width="10" height="10"/><rect class="gl-plate-square" x="234" y="110" width="10" height="10"/><rect class="gl-plate-square" x="294" y="110" width="10" height="10"/>',
        6: '<path class="gl-plate-route" d="M154 148C190 58 234 184 274 98S316 72 336 52"/><rect class="gl-plate-square" x="210" y="139" width="10" height="10"/><rect class="gl-plate-square" x="298" y="70" width="10" height="10"/>',
        7: '<path class="gl-plate-ridge" d="M154 118H326"/><path class="gl-plate-ridge gl-plate-ridge--quiet" d="M176 80V154M224 80V154M272 80V154M320 80V154"/>',
        8: '<path class="gl-plate-ridge gl-plate-ridge--quiet" d="M154 112C196 186 226 190 252 118S304 42 336 72"/><path class="gl-plate-route" d="M154 146H326"/>',
    }
    motif = motifs.get(num, motifs[1])
    return f"""
<div class="gl-hero-plate" aria-hidden="true">
  <svg class="gl-art-plate gl-guide-plate" viewBox="0 0 360 210" focusable="false">
    <path class="gl-plate-stripes" d="M0 0H360V210H0Z"/>
    <text class="gl-guide-plate-num" x="24" y="170">{num:02d}</text>
    {motif}
    <text class="gl-plate-title" x="154" y="192">CHAPTER {num:02d}</text>
  </svg>
</div>
"""


def build_css() -> str:
    return build_race_css() + """

.gl-guide-jump { background: var(--gl-white); border-bottom: 1px solid var(--gl-hairline); }
.gl-guide-jump-inner { max-width: var(--gl-measure); margin: 0 auto; padding: var(--gl-space-3) var(--gl-space-5); display: flex; flex-wrap: wrap; gap: var(--gl-space-2); }
.gl-guide-jump a { min-height: 44px; display: inline-flex; align-items: center; border: 1px solid var(--gl-hairline); padding: 0 var(--gl-space-3); font-family: var(--gl-font-data); font-size: .62rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; text-decoration: none; background: var(--gl-paper); }
.gl-guide-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: var(--gl-space-4); margin: var(--gl-space-6) 0; }
.gl-guide-card { display: grid; grid-template-columns: 144px 1fr; min-height: 180px; background: var(--gl-white); border: 3px solid var(--gl-carbon); color: inherit; text-decoration: none; }
.gl-guide-card-plate { background: var(--gl-carbon); display: flex; align-items: center; justify-content: center; padding: var(--gl-space-3); }
.gl-guide-card-plate .gl-art-plate { border-color: var(--gl-white); }
.gl-guide-card-body { padding: var(--gl-space-4); display: flex; flex-direction: column; gap: var(--gl-space-2); }
.gl-guide-card-kicker, .gl-guide-tag { color: var(--gl-muted); font-family: var(--gl-font-data); font-size: .62rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; }
.gl-guide-card h3 { margin: 0; font-family: var(--gl-font-display); font-size: 1.25rem; font-weight: 900; font-style: italic; line-height: 1; letter-spacing: 0; text-transform: uppercase; }
.gl-guide-card p { margin: 0; font-size: .94rem; line-height: 1.5; }
.gl-guide-card-meta { margin-top: auto; display: flex; gap: var(--gl-space-2); flex-wrap: wrap; }
.gl-guide-tag { border: 1px solid var(--gl-hairline); padding: var(--gl-space-1) var(--gl-space-2); }
.gl-guide-tag--free { color: var(--gl-swix-red); }
.gl-guide-gate { background: var(--gl-white); border: 3px solid var(--gl-carbon); border-top: 6px solid var(--gl-swix-red); padding: var(--gl-space-5); margin: var(--gl-space-5) 0 0; }
.gl-guide-gate h2 { margin: 0 0 var(--gl-space-2); font-family: var(--gl-font-display); font-size: 1.45rem; font-weight: 900; font-style: italic; letter-spacing: 0; text-transform: uppercase; }
.gl-guide-gate p { max-width: var(--gl-prose); margin: 0 0 var(--gl-space-4); }
.gl-guide-gate-label { font-family: var(--gl-font-data); font-size: .62rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; color: var(--gl-muted); display: block; margin: 0 0 var(--gl-space-2); }
.gl-guide-gate-row { display: flex; gap: var(--gl-space-2); flex-wrap: wrap; }
.gl-guide-gate-input { flex: 1 1 240px; min-height: 44px; border: 2px solid var(--gl-carbon); padding: 0 var(--gl-space-3); font-family: var(--gl-font-editorial); font-size: 1rem; background: var(--gl-paper); }
.gl-guide-gate-note { font-size: .82rem; color: var(--gl-muted); margin: var(--gl-space-3) 0 0; }
.gl-guide-gate-note a { color: var(--gl-swix-red); font-weight: 700; }
.gl-guide-locked[hidden] { display: none; }
.gl-guide-btn { min-height: 44px; display: inline-flex; align-items: center; background: var(--gl-carbon); color: var(--gl-white); padding: 0 var(--gl-space-4); font-family: var(--gl-font-data); font-size: .7rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; text-decoration: none; }
.gl-guide-plate-num { fill: var(--gl-muted); opacity: .34; font-family: var(--gl-font-display); font-size: 140px; font-weight: 900; font-style: italic; }
.gl-plate-bar, .gl-plate-zone { fill: var(--gl-klister); }
.gl-plate-bar--quiet, .gl-plate-zone--quiet { opacity: .45; }
.gl-guide-block { margin: var(--gl-space-5) 0; }
.gl-callout { max-width: var(--gl-prose); background: var(--gl-white); border: 3px solid var(--gl-carbon); border-left: 8px solid var(--gl-swix-red); padding: var(--gl-space-4); }
.gl-callout--note { border-left-color: var(--gl-carbon); }
.gl-callout--tip { border-left-color: var(--gl-klister); }
.gl-callout--warning { border-left-color: var(--gl-swix-red); }
.gl-callout h3, .gl-tabs h3, .gl-accordion summary, .gl-data-table-title, .gl-timeline-title, .gl-flashcard h3, .gl-calc h3, .gl-race-ref h3, .gl-personal h3 { margin: 0 0 var(--gl-space-2); font-family: var(--gl-font-display); font-size: 1.05rem; font-weight: 900; font-style: italic; line-height: 1; letter-spacing: 0; text-transform: uppercase; }
.gl-tabs, .gl-accordion, .gl-calc, .gl-personal { max-width: var(--gl-prose); }
.gl-tab-buttons, .gl-personal-buttons { display: flex; flex-wrap: wrap; gap: var(--gl-space-2); margin-bottom: var(--gl-space-3); }
.gl-tab-button, .gl-personal-button { min-height: 44px; border: 2px solid var(--gl-carbon); background: var(--gl-white); color: var(--gl-carbon); padding: 0 var(--gl-space-4); font-family: var(--gl-font-data); font-size: .68rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; cursor: pointer; }
.gl-tab-button.is-active, .gl-personal-button.is-active { background: var(--gl-carbon); color: var(--gl-white); }
.gl-tab-panel, .gl-personal-panel { display: none; background: var(--gl-white); border: 1px solid var(--gl-hairline); padding: var(--gl-space-4); }
.gl-tab-panel.is-active, .gl-personal-panel.is-active { display: block; }
.gl-accordion details { background: var(--gl-white); border: 1px solid var(--gl-hairline); padding: var(--gl-space-4); }
.gl-accordion details + details { border-top: 0; }
.gl-accordion summary { cursor: pointer; min-height: 44px; }
.gl-data-table-wrap { overflow-x: auto; border-top: 3px solid var(--gl-carbon); }
.gl-data-table { width: 100%; border-collapse: collapse; background: var(--gl-white); }
.gl-data-table th { color: var(--gl-muted); font-family: var(--gl-font-data); font-size: .62rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; text-align: left; }
.gl-data-table th, .gl-data-table td { border-bottom: 1px solid var(--gl-hairline); padding: var(--gl-space-3); vertical-align: top; }
.gl-timeline { max-width: var(--gl-prose); border-left: 4px solid var(--gl-carbon); padding-left: var(--gl-space-5); }
.gl-timeline-item { position: relative; padding: 0 0 var(--gl-space-4); }
.gl-timeline-item::before { content: ""; position: absolute; left: calc(-1 * var(--gl-space-5) - 7px); top: 4px; width: 10px; height: 10px; background: var(--gl-swix-red); border: 2px solid var(--gl-carbon); }
.gl-timeline-label { display: block; font-family: var(--gl-font-data); font-size: .66rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: var(--gl-muted); }
.gl-hero-stats { display: grid; grid-template-columns: repeat(4, 1fr); border-top: 3px solid var(--gl-carbon); }
.gl-hero-stat { background: var(--gl-white); border-right: 1px solid var(--gl-hairline); border-bottom: 1px solid var(--gl-hairline); padding: var(--gl-space-4); }
.gl-hero-stat-value { display: block; font-family: var(--gl-font-display); font-size: 2.1rem; font-weight: 900; font-style: italic; line-height: 1; color: var(--gl-swix-red); }
.gl-hero-stat-label { font-family: var(--gl-font-data); font-size: .62rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; }
.gl-zone-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--gl-space-3); }
.gl-zone-card { background: var(--gl-white); border: 3px solid var(--gl-carbon); padding: var(--gl-space-4); }
.gl-zone-share { display: block; color: var(--gl-swix-red); font-family: var(--gl-font-display); font-size: 2rem; font-weight: 900; font-style: italic; }
.gl-race-ref { max-width: var(--gl-prose); background: var(--gl-carbon); color: var(--gl-white); padding: var(--gl-space-5); border-left: 6px solid var(--gl-swix-red); }
.gl-race-ref a { color: var(--gl-klister); font-family: var(--gl-font-data); font-size: .68rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; text-decoration: none; }
.gl-calc-output { background: var(--gl-carbon); color: var(--gl-white); padding: var(--gl-space-4); margin-top: var(--gl-space-3); }
.gl-calc input { min-height: 44px; width: 120px; border: 2px solid var(--gl-carbon); background: var(--gl-white); padding: 0 var(--gl-space-3); font-family: var(--gl-font-data); }
.gl-sources { border-top: 4px solid var(--gl-carbon); }
.gl-source-list { padding-left: var(--gl-space-5); }
.gl-source-list li { margin: 0 0 var(--gl-space-3); max-width: var(--gl-prose); }
.gl-source-list a { color: var(--gl-swix-red); font-weight: 700; }
.gl-cite { color: var(--gl-swix-red); font-family: var(--gl-font-data); font-size: .68em; text-decoration: none; }
.gl-prev-next { display: grid; grid-template-columns: 1fr 1fr; gap: var(--gl-space-4); margin: var(--gl-space-7) 0; }
.gl-prev-next a { background: var(--gl-white); border: 3px solid var(--gl-carbon); padding: var(--gl-space-4); text-decoration: none; }
.gl-prev-next span { display: block; color: var(--gl-muted); font-family: var(--gl-font-data); font-size: .62rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; }
@media (max-width: 820px) { .gl-guide-grid, .gl-zone-grid, .gl-hero-stats, .gl-prev-next { grid-template-columns: 1fr; } .gl-guide-card { grid-template-columns: 1fr; } .gl-guide-card-plate { min-height: 180px; } }
"""


def build_guide_hero(title: str, subtitle: str, kicker: str, plate: str) -> str:
    return f"""
<section class="gl-hero" id="hero">
  <div class="gl-hero-inner">
    <div class="gl-hero-copy">
      <p class="gl-hero-kicker">{esc(kicker)}</p>
      <h1 class="gl-hero-name gl-hero-name--long">{esc(title)}</h1>
      <p class="gl-hero-tagline">{esc(_plain(subtitle))}</p>
      <div class="gl-hero-chips"><span class="gl-chip">8 chapters</span><span class="gl-chip">Training guide</span><span class="gl-chip">XC ski racing</span></div>
    </div>
    {plate}
  </div>
</section>
"""


def build_jump_nav(chapters: list[dict[str, Any]]) -> str:
    links = [f'<a href="/guide/{esc(ch["id"])}/">Ch {int(ch["number"]):02d}</a>' for ch in chapters]
    return f'<nav class="gl-guide-jump" aria-label="Guide chapters"><div class="gl-guide-jump-inner"><a href="/guide/">Guide home</a>{"".join(links)}</div></nav>'


def render_block(block: dict[str, Any], chapter: dict[str, Any], content: dict[str, Any]) -> str:
    kind = block.get("type")
    source_map = {s["id"]: i + 1 for i, s in enumerate(chapter.get("sources", []))}
    if kind == "prose":
        return _paragraphs(block.get("content", ""), source_map)
    if kind == "callout":
        style = block.get("style", "note")
        return f'<aside class="gl-guide-block gl-callout gl-callout--{esc(style)}"><h3>{esc(block.get("title", style))}</h3>{_paragraphs(block.get("content", ""), source_map)}</aside>'
    if kind == "tabs":
        uid = f'tabs-{chapter["id"]}-{len(block.get("tabs", []))}'
        buttons = []
        panels = []
        for i, tab in enumerate(block.get("tabs", [])):
            active = " is-active" if i == 0 else ""
            buttons.append(f'<button class="gl-tab-button{active}" type="button" data-tab-target="{uid}-{i}">{esc(tab.get("label", ""))}</button>')
            panels.append(f'<div class="gl-tab-panel{active}" id="{uid}-{i}">{_paragraphs(tab.get("content", ""), source_map)}</div>')
        return f'<div class="gl-guide-block gl-tabs"><div class="gl-tab-buttons">{"".join(buttons)}</div>{"".join(panels)}</div>'
    if kind == "accordion":
        items = "".join(f'<details><summary>{esc(item.get("title", ""))}</summary>{_paragraphs(item.get("content", ""), source_map)}</details>' for item in block.get("items", []))
        return f'<div class="gl-guide-block gl-accordion">{items}</div>'
    if kind == "data_table":
        title = f'<h3 class="gl-data-table-title">{esc(block.get("title", ""))}</h3>' if block.get("title") else ""
        headers = "".join(f"<th>{esc(h)}</th>" for h in block.get("headers", []))
        rows = "".join("<tr>" + "".join(f"<td>{_md_inline(cell, source_map)}</td>" for cell in row) + "</tr>" for row in block.get("rows", []))
        return f'<div class="gl-guide-block">{title}<div class="gl-data-table-wrap"><table class="gl-data-table"><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table></div></div>'
    if kind == "process_list":
        steps = []
        for i, step in enumerate(block.get("steps", []), start=1):
            steps.append(f'<div class="gl-process-step"><span class="gl-process-num">{i}</span><h3>{esc(step.get("title", ""))}</h3>{_paragraphs(step.get("content", ""), source_map)}</div>')
        return f'<div class="gl-guide-block"><h3 class="gl-data-table-title">{esc(block.get("title", ""))}</h3><div class="gl-process">{"".join(steps)}</div></div>'
    if kind == "timeline":
        items = "".join(f'<div class="gl-timeline-item"><span class="gl-timeline-label">{esc(item.get("label", ""))}</span>{_paragraphs(item.get("content", ""), source_map)}</div>' for item in block.get("items", []))
        return f'<div class="gl-guide-block gl-timeline"><h3 class="gl-timeline-title">{esc(block.get("title", ""))}</h3>{items}</div>'
    if kind == "hero_stat":
        stats = "".join(f'<div class="gl-hero-stat"><span class="gl-hero-stat-value">{esc(s.get("value", ""))}</span><span class="gl-hero-stat-label">{esc(s.get("label", ""))}</span></div>' for s in block.get("stats", []))
        return f'<div class="gl-guide-block gl-hero-stats">{stats}</div>'
    if kind == "zone_visualizer":
        zones = "".join(f'<div class="gl-zone-card"><span class="gl-zone-share">{esc(z.get("share", ""))}</span><h3>{esc(z.get("name", ""))}</h3><p>{esc(z.get("cue", ""))}</p><p>{esc(z.get("use", ""))}</p></div>' for z in block.get("zones", []))
        return f'<div class="gl-guide-block gl-zone-grid">{zones}</div>'
    if kind == "flashcard":
        cards = []
        for card in block.get("cards", []):
            cards.append(f'<button class="gl-wax-card gl-wax-card-blue" type="button" aria-pressed="false"><span class="gl-wax-card-inner"><span class="gl-wax-card-face gl-wax-card-front"><span class="gl-wax-card-kicker">Flashcard</span><span><h3>{esc(card.get("front", ""))}</h3><p>Tap to reveal.</p></span></span><span class="gl-wax-card-face gl-wax-card-back"><span class="gl-wax-card-kicker">Answer</span><span><h3>Answer</h3>{_paragraphs(card.get("back", ""), source_map)}</span></span></span></button>')
        return f'<div class="gl-guide-block gl-flashcard"><div class="gl-wax-cards">{"".join(cards)}</div></div>'
    if kind == "calculator":
        return f'<div class="gl-guide-block gl-calc" data-guide-calculator><h3>{esc(block.get("title", ""))}</h3><p>{esc(_plain(block.get("description", "")))}</p><label class="gl-mono">Hours <input type="number" min="0" max="24" step="1" value="6" data-hours-input></label><div class="gl-calc-output" data-hours-output>6 hours: two easy sessions, one technique session, one longer ski.</div></div>'
    if kind == "knowledge_check":
        opts = []
        correct = ""
        feedback = ""
        for opt in block.get("options", []):
            if opt.get("correct"):
                correct = opt.get("label", "")
                feedback = opt.get("response", "")
            opts.append(f'<button class="gl-quiz-option" type="button" data-answer="{esc(opt.get("label", ""))}">{esc(opt.get("label", ""))}</button>')
        return f'<div class="gl-guide-block gl-knowledge" data-quiz-correct="{esc(correct)}" data-quiz-feedback="{esc(_plain(feedback))}"><h3>Knowledge check</h3><p class="gl-section-prose">{_md_inline(block.get("question", ""), source_map)}</p><div class="gl-quiz-options" role="group" aria-label="Knowledge check options">{"".join(opts)}</div><p class="gl-knowledge-result" aria-live="polite" data-empty="Choose one answer.">Choose one answer.</p></div>'
    if kind == "race_reference":
        slug = block.get("slug", "")
        return f'<aside class="gl-guide-block gl-race-ref" data-race-reference="{esc(slug)}"><h3>Race reference</h3><p>{_md_inline(block.get("context", ""), source_map)}</p><a href="/{esc(slug)}/">Open race profile</a></aside>'
    if kind == "personalized_content":
        riders = content.get("personalization", {}).get("rider_types", [])
        buttons = []
        panels = []
        variants = block.get("variants", {})
        for i, rider in enumerate(riders):
            rid = rider["id"]
            active = " is-active" if i == 0 else ""
            buttons.append(f'<button class="gl-personal-button{active}" type="button" data-rider-target="{esc(rid)}">{esc(rider["label"])}</button>')
            panels.append(f'<div class="gl-personal-panel{active}" data-rider-panel="{esc(rid)}"><span class="gl-guide-tag">{esc(rider.get("hours", ""))}</span>{_paragraphs(variants.get(rid, ""), source_map)}</div>')
        return f'<div class="gl-guide-block gl-personal"><h3>I am a:</h3><div class="gl-personal-buttons">{"".join(buttons)}</div>{"".join(panels)}</div>'
    return f'<div class="gl-guide-block gl-placeholder">Unsupported block: {esc(kind)}</div>'


def build_sources(chapter: dict[str, Any]) -> str:
    if not chapter.get("sources"):
        return ""
    items = []
    for src in chapter["sources"]:
        bits = [src.get("author"), src.get("title"), src.get("publisher"), src.get("year")]
        label = ". ".join(esc(x) for x in bits if x)
        url = esc(src.get("url", "#"))
        items.append(f'<li id="source-{esc(src["id"])}"><a href="{url}">{label}</a></li>')
    return f'<section class="gl-section gl-sources" id="sources">{build_section_header("S", "Sources")}<ol class="gl-source-list">{"".join(items)}</ol></section>'


def build_section_header(num: str, title: str) -> str:
    return f'<div class="gl-section-header"><span class="gl-section-num">{esc(num)}</span><h2 class="gl-section-title">{esc(title)}</h2></div>'


GATE_EMAIL = "coaching@xcskilabs.com"


def build_chapter_body(chapter: dict[str, Any], content: dict[str, Any]) -> str:
    parts = []
    gated = chapter.get("gated")
    if gated:
        cid = esc(chapter.get("id", ""))
        parts.append(f"""
<aside class="gl-guide-gate" data-guide-gate>
  <p class="gl-guide-tag">Free — one email</p>
  <h2>Read the rest of the guide</h2>
  <p>Chapters four through eight — technique, fueling, tactics, race week, and the off-season — plus the whole guide, for your email. No spam; unsubscribe anytime.</p>
  <form class="gl-guide-gate-form" data-guide-gate-form action="https://formsubmit.co/{GATE_EMAIL}" method="POST">
    <input type="hidden" name="_subject" value="Guide unlock — {cid}">
    <input type="hidden" name="chapter" value="{cid}">
    <input type="text" name="_honey" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px" aria-hidden="true">
    <label class="gl-guide-gate-label" for="gate-email-{cid}">Email</label>
    <div class="gl-guide-gate-row">
      <input class="gl-guide-gate-input" id="gate-email-{cid}" type="email" name="email" required placeholder="you@example.com" autocomplete="email">
      <button class="gl-guide-btn" type="submit">Unlock the guide</button>
    </div>
    <p class="gl-guide-gate-note">Prefer a plan built for you? <a href="/questionnaire/">Start the intake</a> instead.</p>
  </form>
</aside>
""")
    body = []
    for idx, section in enumerate(chapter.get("sections", []), start=1):
        blocks = "\n".join(render_block(block, chapter, content) for block in section.get("blocks", []))
        title = section.get("title") or section.get("id", "").replace("-", " ")
        body.append(f'<section class="gl-section" id="{esc(section["id"])}">{build_section_header(f"{idx:02d}", title)}{blocks}</section>')
    body.append(build_sources(chapter))
    body_html = "\n".join(body)
    if gated:
        # Content hidden until unlocked (JS reveals on email submit or returning reader)
        parts.append(f'<div class="gl-guide-locked" data-guide-locked hidden>{body_html}</div>')
    else:
        parts.append(body_html)
    return "\n".join(parts)


def build_prev_next(chapter: dict[str, Any], chapters: list[dict[str, Any]]) -> str:
    prev_ch = next((c for c in chapters if c["number"] == chapter["number"] - 1), None)
    next_ch = next((c for c in chapters if c["number"] == chapter["number"] + 1), None)
    left = '<div></div>' if not prev_ch else f'<a href="/guide/{esc(prev_ch["id"])}/"><span>Previous</span>Ch {prev_ch["number"]}: {esc(prev_ch["title"])}</a>'
    right = '<div></div>' if not next_ch else f'<a href="/guide/{esc(next_ch["id"])}/"><span>Next</span>Ch {next_ch["number"]}: {esc(next_ch["title"])}</a>'
    return f'<nav class="gl-prev-next" aria-label="Chapter navigation">{left}{right}</nav>'


def build_jsonld(name: str, description: str, url: str, kind: str = "Article") -> str:
    obj = {
        "@context": "https://schema.org",
        "@type": kind,
        "name": name,
        "description": description,
        "url": url,
        "publisher": {"@type": "Organization", "name": "XC Ski Labs"},
    }
    return '<script type="application/ld+json">' + _safe_json_for_script(obj, ensure_ascii=False, separators=(",", ":")) + "</script>"


def build_script() -> str:
    return build_interactions_js() + """
<script>
(function(){
  document.querySelectorAll('[data-tab-target]').forEach(function(button) {
    button.addEventListener('click', function() {
      var wrap = button.closest('.gl-tabs');
      if (!wrap) return;
      wrap.querySelectorAll('.gl-tab-button,.gl-tab-panel').forEach(function(el) { el.classList.remove('is-active'); });
      button.classList.add('is-active');
      var panel = document.getElementById(button.getAttribute('data-tab-target'));
      if (panel) panel.classList.add('is-active');
    });
  });
  document.querySelectorAll('[data-rider-target]').forEach(function(button) {
    button.addEventListener('click', function() {
      var wrap = button.closest('.gl-personal');
      if (!wrap) return;
      var target = button.getAttribute('data-rider-target');
      wrap.querySelectorAll('.gl-personal-button,.gl-personal-panel').forEach(function(el) { el.classList.remove('is-active'); });
      button.classList.add('is-active');
      var panel = wrap.querySelector('[data-rider-panel="' + target + '"]');
      if (panel) panel.classList.add('is-active');
    });
  });
  document.querySelectorAll('[data-guide-calculator]').forEach(function(calc) {
    var input = calc.querySelector('[data-hours-input]');
    var output = calc.querySelector('[data-hours-output]');
    if (!input || !output) return;
    function update() {
      var hours = parseFloat(input.value || '0');
      var label = hours < 4 ? 'two short easy sessions and one technique touch' : hours < 8 ? 'two easy sessions, one technique session, one longer ski' : hours < 12 ? 'three aerobic sessions, one interval session, one technique block, one long ski' : 'a planned week with volume, intensity, strength, and recovery protected';
      output.textContent = hours + ' hours: ' + label + '.';
    }
    input.addEventListener('input', update);
    update();
  });

  // Guide email gate: reveal gated content on submit (or for returning readers)
  var UNLOCK_KEY = 'xl_guide_unlocked';
  function unlock() {
    document.querySelectorAll('[data-guide-locked]').forEach(function(el) { el.hidden = false; });
    document.querySelectorAll('[data-guide-gate]').forEach(function(el) { el.hidden = true; });
  }
  try { if (localStorage.getItem(UNLOCK_KEY) === '1') unlock(); } catch (e) {}
  document.querySelectorAll('[data-guide-gate-form]').forEach(function(form) {
    form.addEventListener('submit', function(e) {
      e.preventDefault();
      var honey = form.querySelector('[name="_honey"]');
      if (honey && honey.value) return; // bot
      // Fire-and-forget to the lead worker: record the email + chapter,
      // never block the reader on the network (unlock happens regardless).
      var viewed = [];
      try {
        viewed = (JSON.parse(localStorage.getItem('xc_viewed_races') || '[]') || [])
          .map(function(r) { return r && r.name; }).filter(Boolean).slice(0, 5);
      } catch (e2) {}
      fetch('https://fueling-lead-intake.gravelgodcoaching.workers.dev', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'training_guide',
          brand: 'xcskilabs',
          email: (form.querySelector('[name="email"]') || {}).value || '',
          guide_chapter: (form.querySelector('[name="chapter"]') || {}).value || '',
          viewed_races: viewed,
          website: ''
        })
      }).catch(function(){});
      try { localStorage.setItem(UNLOCK_KEY, '1'); } catch (e) {}
      if (typeof gtag === 'function') gtag('event', 'guide_unlock', { chapter: (form.querySelector('[name="chapter"]') || {}).value || '' });
      unlock();
      var target = document.querySelector('[data-guide-locked]');
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
})();
</script>
"""


def assemble_page(title: str, description: str, robots: str, body: str, jsonld: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="{esc(robots)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
  {jsonld}
  {build_ga4_snippet()}
  <style>{build_css()}</style>
</head>
<body>
<a href="#content" class="gl-skip-link">Skip to content</a>
{build_nav_header("guide")}
{body}
{build_script()}
{build_sticky_js()}
{build_cookie_consent()}
</body>
</html>"""


def build_pillar(content: dict[str, Any]) -> str:
    chapters = content["chapters"]
    card_html = []
    for ch in chapters:
        tags = f'<span class="gl-guide-tag gl-guide-tag--free">Open</span>' if not ch.get("gated") else '<span class="gl-guide-tag">Noindex</span>'
        card_html.append(f"""
<a class="gl-guide-card" href="/guide/{esc(ch["id"])}/">
  <div class="gl-guide-card-plate">{render_guide_plate(ch)}</div>
  <div class="gl-guide-card-body">
    <span class="gl-guide-card-kicker">Chapter {int(ch["number"]):02d}</span>
    <h3>{esc(ch["title"])}</h3>
    <p>{esc(_plain(ch.get("subtitle", "")))}</p>
    <div class="gl-guide-card-meta">{tags}<span class="gl-guide-tag">{_estimate_read_time(ch)} min</span></div>
  </div>
</a>""")
    plate = render_guide_plate({"number": 1})
    body = f"""
<div class="gl-page">
{build_guide_hero(content["title"], content["subtitle"], "Free guide", plate)}
{build_jump_nav(chapters)}
<main class="gl-wrap" id="content">
  <section class="gl-section">
    {build_section_header("01", "Guide chapters")}
    <div class="gl-guide-grid">{"".join(card_html)}</div>
  </section>
</main>
</div>
{build_product_ladder({"slug": "guide"})}
<div class="gl-page">{build_footer({})}</div>
"""
    return assemble_page(
        f'{content["title"]} | XC Ski Labs',
        content.get("meta_description", ""),
        "index, follow",
        body,
        build_jsonld(content["title"], content.get("meta_description", ""), "https://xcskilabs.com/guide/", "Course"),
    )


def build_chapter_page(chapter: dict[str, Any], content: dict[str, Any]) -> str:
    title = f'Chapter {chapter["number"]}: {chapter["title"]} | XC Ski Labs'
    description = chapter.get("subtitle") or content.get("meta_description", "")
    robots = "noindex" if chapter.get("gated") else "index, follow"
    body = f"""
<div class="gl-page">
{build_guide_hero(chapter["title"], chapter.get("subtitle", ""), f'Chapter {int(chapter["number"]):02d}', render_guide_plate(chapter))}
{build_jump_nav(content["chapters"])}
<main class="gl-wrap" id="content">
{build_chapter_body(chapter, content)}
{build_prev_next(chapter, content["chapters"])}
</main>
</div>
<div class="gl-page">{build_footer({})}</div>
"""
    return assemble_page(
        title,
        description,
        robots,
        body,
        build_jsonld(title, description, f'https://xcskilabs.com/guide/{chapter["id"]}/'),
    )


def generate(output_dir: Path = OUTPUT_DIR) -> None:
    content = load_content()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(build_pillar(content), encoding="utf-8")
    for chapter in content["chapters"]:
        ch_dir = output_dir / chapter["id"]
        ch_dir.mkdir(parents=True, exist_ok=True)
        (ch_dir / "index.html").write_text(build_chapter_page(chapter, content), encoding="utf-8")
    print(f"Generated guide pillar and {len(content['chapters'])} chapters in {output_dir}")


def validate_references(content: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    slugs = _slug_set()
    for chapter in content.get("chapters", []):
        source_map = {s["id"]: i + 1 for i, s in enumerate(chapter.get("sources", []))}
        for section in chapter.get("sections", []):
            for block in section.get("blocks", []):
                raw = json.dumps(block)
                for sid in CITE_RE.findall(raw):
                    if sid not in source_map:
                        errors.append(f"{chapter['id']}: missing source {sid}")
                if block.get("type") == "race_reference" and block.get("slug") not in slugs:
                    errors.append(f"{chapter['id']}: missing race slug {block.get('slug')}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    content = load_content()
    errors = validate_references(content)
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1
    if not args.check:
        generate(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
