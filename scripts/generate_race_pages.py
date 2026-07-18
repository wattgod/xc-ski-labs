#!/usr/bin/env python3
"""
XC Ski Labs — Race Page Generator

Generates self-contained HTML race pages from JSON profiles.
Wax Bench design system, with tokens embedded from tokens/tokens.css.

Usage:
    python generate_race_pages.py              # all races
    python generate_race_pages.py --slug vasaloppet   # single race
    python generate_race_pages.py --data-dir ../race-data --output-dir ../output
"""

import argparse
import html
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Optional
import xml.etree.ElementTree as ET

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR.parent / "race-data"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parent / "output"
DEFAULT_ART_DIR = SCRIPT_DIR.parent / "art"
TOKENS_CSS = SCRIPT_DIR.parent / "tokens" / "tokens.css"

# ── Rating Criteria ────────────────────────────────────────────

RATING_CRITERIA = [
    ("distance", "Distance"),
    ("elevation", "Elevation"),
    ("altitude", "Altitude"),
    ("field_size", "Field Size"),
    ("prestige", "Prestige"),
    ("international_draw", "Int'l Draw"),
    ("course_technicality", "Technicality"),
    ("snow_reliability", "Snow Reliability"),
    ("grooming_quality", "Grooming"),
    ("accessibility", "Accessibility"),
    ("community", "Community"),
    ("scenery", "Scenery"),
    ("organization", "Organization"),
    ("competitive_depth", "Comp. Depth"),
]

# ── Series Labels ──────────────────────────────────────────────

SERIES_LABELS = {
    "worldloppet": "Worldloppet",
    "ski_classics_pro_tour": "Ski Classics Pro Tour",
    "ski_classics_grand_classic": "Ski Classics Grand Classic",
    "euroloppet": "Euroloppet",
    "china_loppet": "China Loppet",
    "australia_loppet": "Australia Loppet",
}

# ── Discipline Labels ──────────────────────────────────────────

DISCIPLINE_LABELS = {
    "classic": "Classic",
    "skate": "Skate",
    "both": "Classic & Skate",
}


# ── Helpers ────────────────────────────────────────────────────

def esc(text: Any) -> str:
    """HTML-escape a string. Safe for None/empty."""
    if text is None or text == "":
        return ""
    return html.escape(str(text))


def _safe_json_for_script(obj, **kwargs) -> str:
    """Serialize obj to JSON safe for embedding inside <script> tags.

    json.dumps does NOT escape '</' sequences, so a string containing
    '</script>' would prematurely close the <script> element.
    We replace '</' with '<\\/' which is valid JSON and safe in HTML.
    """
    raw = json.dumps(obj, **kwargs)
    return raw.replace("</", "<\\/")


def _parse_score(raw: Any) -> Optional[int]:
    """Safely parse a score value that might be int, float, string, or None."""
    if raw is None or raw == "":
        return None
    try:
        return int(float(str(raw)))
    except (ValueError, TypeError):
        return None


def format_distance(km: Any) -> str:
    """Format distance with km suffix."""
    if km is None:
        return "—"
    return f"{km} km"


def format_elevation(m: Any) -> str:
    """Format elevation with m suffix."""
    if m is None:
        return "—"
    return f"{m} m"


def format_altitude(m: Any) -> str:
    """Format altitude with m suffix."""
    if m is None:
        return "—"
    return f"{m} m"


def tier_class(tier: int) -> str:
    """Return CSS class for tier."""
    return f"t{tier}" if tier in (1, 2, 3, 4) else "t4"


def tier_label(tier: int) -> str:
    """Return display label for tier."""
    labels = {1: "TIER 1", 2: "TIER 2", 3: "TIER 3", 4: "TIER 4"}
    return labels.get(tier, "TIER 4")


def _display_caps(text: Any) -> str:
    """Format display text for the Wax Bench hero.

    Existing hyphens become non-breaking (the name breaks where WE say);
    known Nordic compound suffixes get a soft hyphen so very long single
    words (BIRKEBEINERRENNET) break with a real hyphen, per guidelines §3.
    """
    out = esc(text).replace("-", "&#8209;")
    words = out.split(" ")
    fixed = []
    for w in words:
        if len(w) > 14:
            for suffix in ("rennet", "loppet", "marsjen", "maraton", "marathon", "rittet"):
                idx = w.lower().rfind(suffix)
                if idx > 3:
                    w = w[:idx] + "&shy;" + w[idx:]
                    break
        fixed.append(w)
    return " ".join(fixed)


def _hero_name_class(name: str) -> str:
    longest = max((len(w) for w in str(name).split()), default=0)
    return "gl-hero-name gl-hero-name--long" if longest > 14 else "gl-hero-name"


def _series_label(race: dict) -> str:
    series = race.get("series_membership", [])
    if not series:
        return "Independent"
    return SERIES_LABELS.get(series[0], str(series[0]).replace("_", " ").title())


def parse_temperature_range(raw: Any) -> Optional[tuple[float, float]]:
    """Parse climate temperature strings like '-15 to 0'."""
    if raw is None:
        return None
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", str(raw))
    if len(nums) < 2:
        return None
    try:
        a, b = float(nums[0]), float(nums[1])
    except ValueError:
        return None
    return (min(a, b), max(a, b))


WAX_SEGMENTS = [
    ("green", "GREEN · -15° AND BELOW", float("-inf"), -15.0),
    ("blue", "BLUE · -15° TO -8°", -15.0, -8.0),
    ("violet", "VIOLET · -8° TO -2°", -8.0, -2.0),
    ("red", "RED · -2° AND ABOVE", -2.0, float("inf")),
]

WAX_CARD_BANDS = [
    {
        "key": "green",
        "label": "Deep cold",
        "range": "-15°C and below",
        "low": -30.0,
        "high": -15.0,
        "guidance": "Hardwax green or blue-green range. Keep layers thin and test grip before adding more.",
    },
    {
        "key": "blue",
        "label": "Cold snow",
        "range": "-15°C to -8°C",
        "low": -15.0,
        "high": -8.0,
        "guidance": "Hardwax blue range. Cork several thin layers and check kick on the first sustained climb.",
    },
    {
        "key": "violet",
        "label": "Mixed cold",
        "range": "-8°C to -2°C",
        "low": -8.0,
        "high": -2.0,
        "guidance": "Hardwax violet range. Watch glazed tracks and add a warmer cover only if grip drops.",
    },
    {
        "key": "red",
        "label": "Near zero",
        "range": "-2°C and above",
        "low": -2.0,
        "high": 5.0,
        "guidance": "Red hardwax can work below freezing. At 0°C and above, expect klister or covered klister.",
    },
]


def _ranges_overlap(low: float, high: float, seg_low: float, seg_high: float) -> bool:
    return high >= seg_low and low <= seg_high


def _format_number(raw: Any) -> str:
    if raw is None or raw == "":
        return ""
    try:
        val = float(str(raw))
    except (TypeError, ValueError):
        return str(raw)
    return f"{val:g}"


def _distance_label(raw: Any) -> str:
    val = _format_number(raw)
    return f"{val} KM" if val else ""


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = math.radians(a[0]), math.radians(a[1])
    lat2, lon2 = math.radians(b[0]), math.radians(b[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def _downsample_points(points: list[dict[str, float]], limit: int = 80) -> list[dict[str, float]]:
    if len(points) <= limit:
        return points
    step = (len(points) - 1) / (limit - 1)
    out = []
    for i in range(limit):
        out.append(points[round(i * step)])
    return out


def parse_gpx_profile(gpx_path: Path) -> dict[str, Any]:
    """Parse a GPX profile into distance/elevation points using stdlib XML."""
    root = ET.parse(gpx_path).getroot()
    raw_points: list[tuple[float, float, float]] = []
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag not in {"trkpt", "rtept"}:
            continue
        lat = el.get("lat")
        lon = el.get("lon")
        if lat is None or lon is None:
            continue
        ele = None
        for child in el:
            if child.tag.rsplit("}", 1)[-1] == "ele" and child.text:
                ele = child.text
                break
        try:
            raw_points.append((float(lat), float(lon), float(ele) if ele is not None else 0.0))
        except ValueError:
            continue

    if not raw_points:
        raise ValueError(f"No trkpt/rtept points found in {gpx_path}")

    series = []
    total_km = 0.0
    prev = None
    for lat, lon, ele in raw_points:
        if prev is not None:
            total_km += _haversine_km((prev[0], prev[1]), (lat, lon))
        series.append({"distance_km": total_km, "elevation_m": ele})
        prev = (lat, lon)

    return {
        "distance_km": total_km,
        "points": _downsample_points(series),
        "start_elevation_m": series[0]["elevation_m"],
        "finish_elevation_m": series[-1]["elevation_m"],
        "high_point_m": max(p["elevation_m"] for p in series),
    }


def _split_route_names(race: dict) -> tuple[str, str]:
    v = race.get("vitals", {})
    for raw in (v.get("location"), v.get("location_badge"), race.get("course", {}).get("route")):
        if not raw:
            continue
        text = str(raw)
        for sep in (" to ", " – ", " — ", "->", "→"):
            if sep in text:
                a, b = text.split(sep, 1)
                return a.strip() or "START", b.strip() or "FINISH"
    return "START", "FINISH"


def _profile_path(points: list[dict[str, float]], width: int = 330, height: int = 150) -> tuple[str, list[tuple[float, float, dict[str, float]]]]:
    if not points:
        return "", []
    min_ele = min(p["elevation_m"] for p in points)
    max_ele = max(p["elevation_m"] for p in points)
    total = max(points[-1]["distance_km"], 1.0)
    span = max(max_ele - min_ele, 1.0)
    mapped = []
    for p in points:
        x = (p["distance_km"] / total) * width
        y = height - ((p["elevation_m"] - min_ele) / span) * (height - 18) - 8
        mapped.append((x, y, p))
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in mapped)
    massif = f"M0,{height} L{line} L{width},{height} Z"
    return massif, mapped


def render_course_plate(race: dict, profile: dict[str, Any]) -> str:
    """Tier A plate: real route elevation massif."""
    start_name, finish_name = _split_route_names(race)
    points = profile["points"]
    massif, mapped = _profile_path(points)
    high_idx = max(range(len(mapped)), key=lambda i: mapped[i][2]["elevation_m"])
    sx, sy, sp = mapped[0]
    hx, hy, hp = mapped[high_idx]
    fx, fy, fp = mapped[-1]
    dots = []
    for i, (x, y, _) in enumerate(mapped):
        if i % 7 == 0 or i == len(mapped) - 1:
            dots.append(f'<circle class="gl-plate-dot" cx="{x:.1f}" cy="{y:.1f}" r="2.5"/>')
    labels = [
        (max(4, sx), max(18, sy - 16), "start", start_name, sp["elevation_m"], "start"),
        (min(270, hx + 8), max(18, hy - 18), "high point", None, hp["elevation_m"], "middle"),
        (min(318, fx), max(18, fy - 16), "finish", finish_name, fp["elevation_m"], "end"),
    ]
    label_html = ""
    for x, y, key, name, ele, anchor in labels:
        detail = f"{esc(str(name).upper())} · {ele:.0f} M" if name else f"{ele:.0f} M"
        label_html += (
            f'<text class="gl-plate-label" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}">'
            f'<tspan>{esc(key.upper())}</tspan>'
            f'<tspan x="{x:.1f}" dy="12">{detail}</tspan>'
            f'</text>'
        )
    distance = f"{profile['distance_km']:.1f} KM"
    return f"""
<div class="gl-hero-plate" aria-hidden="true">
  <svg class="gl-art-plate gl-art-plate--course" viewBox="0 0 360 210" focusable="false">
    <path class="gl-plate-stripes" d="M0 0H360V210H0Z"/>
    <path class="gl-plate-massif" d="{massif}" transform="translate(15 38)"/>
    <polyline class="gl-plate-profile" points="{' '.join(f'{x + 15:.1f},{y + 38:.1f}' for x, y, _ in mapped)}"/>
    <g transform="translate(15 38)">{''.join(dots)}</g>
    <g transform="translate(15 38)">{label_html}</g>
    <text class="gl-plate-title" x="18" y="26">{esc(_distance_label(distance.replace(" KM", "")))}</text>
  </svg>
</div>
"""


def render_data_plate(race: dict) -> str:
    """Tier B plate: abstract terrain with real profile scalars."""
    v = race.get("vitals", {})
    r = race.get("nordic_lab_rating", {})
    discipline = r.get("discipline", v.get("discipline", ""))
    distance = _distance_label(v.get("distance_km"))
    figures = []
    if distance:
        figures.append(("distance", distance))
    if v.get("elevation_m") is not None:
        figures.append(("gain", f"{_format_number(v.get('elevation_m'))} M"))
    if v.get("altitude_m") is not None:
        figures.append(("altitude", f"{_format_number(v.get('altitude_m'))} M"))
    if discipline:
        figures.append(("technique", DISCIPLINE_LABELS.get(discipline, discipline).upper()))
    figure_html = ""
    y = 50
    for label, value in figures[:4]:
        figure_html += f'<text class="gl-plate-stat" x="24" y="{y}"><tspan>{esc(label.upper())}</tspan><tspan x="24" dy="21">{esc(value)}</tspan></text>'
        y += 46
    route_label = distance or "ROUTE"
    return f"""
<div class="gl-hero-plate" aria-hidden="true">
  <svg class="gl-art-plate gl-art-plate--data" viewBox="0 0 360 210" focusable="false">
    <path class="gl-plate-stripes" d="M0 0H360V210H0Z"/>
    <path class="gl-plate-ridge" d="M146 56C182 28 205 76 236 48S291 63 334 34"/>
    <path class="gl-plate-ridge gl-plate-ridge--quiet" d="M146 102C178 82 205 117 237 91S292 112 337 82"/>
    <path class="gl-plate-ridge gl-plate-ridge--quiet" d="M146 150C184 128 206 168 238 139S294 164 337 132"/>
    <rect class="gl-plate-square" x="154" y="170" width="12" height="12"/>
    <rect class="gl-plate-square" x="324" y="88" width="12" height="12"/>
    <path class="gl-plate-route" d="M166 176C206 158 220 118 250 112S295 101 324 94"/>
    <text class="gl-plate-route-label" x="238" y="143">{esc(route_label)}</text>
    {figure_html}
  </svg>
</div>
"""


def select_art_plate_tier(slug: str, art_dir: Path = DEFAULT_ART_DIR) -> str:
    return "A" if (art_dir / "gpx" / f"{slug}.gpx").exists() else "B"


def build_hero_plate(race: dict, art_dir: Path = DEFAULT_ART_DIR) -> tuple[str, dict[str, str]]:
    slug = race["slug"]
    gpx_path = art_dir / "gpx" / f"{slug}.gpx"
    if gpx_path.exists():
        profile = parse_gpx_profile(gpx_path)
        license_path = art_dir / "gpx" / f"{slug}.license"
        license_text = license_path.read_text(encoding="utf-8").strip() if license_path.exists() else "UNVERIFIED — do not deploy"
        source = f"art/gpx/{slug}.gpx"
        return render_course_plate(race, profile), {"tier": "A", "source": source, "license": license_text}
    return render_data_plate(race), {"tier": "B", "source": f"race-data/{slug}.json", "license": "Profile data"}


def write_art_manifest(records: dict[str, dict[str, str]], art_dir: Path = DEFAULT_ART_DIR) -> None:
    art_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = art_dir / "manifest.json"
    manifest_path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def select_wax_card_bands(temp_range: tuple[float, float]) -> list[dict[str, Any]]:
    low, high = temp_range
    scored = []
    for idx, band in enumerate(WAX_CARD_BANDS):
        overlap = max(0.0, min(high, band["high"]) - max(low, band["low"]))
        if overlap > 0:
            distance = 0.0
        elif high < band["low"]:
            distance = band["low"] - high
        else:
            distance = low - band["high"]
        scored.append((0 if overlap > 0 else 1, -overlap, distance, idx, band))
    selected = sorted(scored)[:3]
    return [item[-1] for item in sorted(selected, key=lambda item: item[3])]


def build_quiz_fact(race: dict) -> Optional[dict[str, Any]]:
    history = race.get("history", {})
    founded = history.get("founded")
    if founded is None:
        founded = race.get("vitals", {}).get("founded")
    try:
        year = int(founded)
    except (TypeError, ValueError):
        year = None
    if year:
        options = sorted({year, year - 10, year + 10})
        return {
            "question": f"Founded in ___?",
            "options": options,
            "correct": year,
            "feedback": f"{race.get('display_name', race.get('name', 'The race'))} was founded in {year}.",
        }
    distance = race.get("vitals", {}).get("distance_km")
    if distance is None:
        return None
    try:
        dist = int(float(str(distance)))
    except (TypeError, ValueError):
        return None
    offsets = [dist - 10, dist, dist + 10] if dist > 15 else [dist, dist + 5, dist + 10]
    options = sorted({max(1, o) for o in offsets})
    return {
        "question": "Main distance?",
        "options": options,
        "correct": dist,
        "feedback": f"The main profile distance is {dist} km.",
    }


# ── CSS ────────────────────────────────────────────────────────

def load_tokens_css() -> str:
    """Read the shared Wax Bench token file for static embedding."""
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


def build_css() -> str:
    """Build the complete CSS for race pages."""
    tokens = load_tokens_css()
    return f"""
{tokens}

*, *::before, *::after {{
  box-sizing: border-box;
}}

html {{
  scroll-behavior: smooth;
}}

body {{
  margin: 0;
  background: var(--gl-paper);
  color: var(--gl-carbon);
  font-family: var(--gl-font-editorial);
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}}

.gl-page {{
  background: var(--gl-paper);
  padding-bottom: 80px;
}}

.gl-wrap {{
  max-width: var(--gl-measure);
  margin: 0 auto;
  padding: 0 var(--gl-space-5);
}}

.gl-display {{
  font-family: var(--gl-font-display);
  font-weight: 900;
  font-style: italic;
  text-transform: uppercase;
  letter-spacing: 0;
  line-height: .96;
}}

.gl-mono {{
  font-family: var(--gl-font-data);
  font-weight: 700;
  letter-spacing: .16em;
  text-transform: uppercase;
}}

a {{ color: inherit; }}

.gl-skip-link {{
  position: absolute;
  left: -9999px;
  top: 0;
  z-index: 9999;
  background: var(--gl-swix-red);
  color: var(--gl-white);
  padding: var(--gl-space-3) var(--gl-space-4);
  font-family: var(--gl-font-data);
  font-weight: 700;
  text-decoration: none;
}}

.gl-skip-link:focus {{ left: 0; }}

.gl-nav {{
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--gl-carbon);
  color: var(--gl-white);
  border-bottom: 3px solid var(--gl-carbon);
}}

.gl-nav-inner {{
  max-width: var(--gl-measure);
  min-height: 56px;
  margin: 0 auto;
  padding: 0 var(--gl-space-5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gl-space-5);
}}

.gl-nav-logo,
.gl-footer-logo {{
  font-family: var(--gl-font-display);
  font-weight: 900;
  font-style: italic;
  text-transform: uppercase;
  text-decoration: none;
  letter-spacing: 0;
  white-space: nowrap;
}}

.gl-nav-logo em {{ color: var(--gl-swix-red); font-style: italic; }}
.gl-footer-logo em {{ color: var(--gl-klister); font-style: italic; }}

.gl-nav-links {{
  display: flex;
  align-items: center;
  gap: var(--gl-space-2);
  list-style: none;
  margin: 0;
  padding: 0;
}}

.gl-nav-item > a,
.gl-nav-dropdown a {{
  min-height: 44px;
  display: flex;
  align-items: center;
  padding: 0 var(--gl-space-4);
  font-family: var(--gl-font-data);
  font-size: .68rem;
  font-weight: 700;
  letter-spacing: .18em;
  text-transform: uppercase;
  text-decoration: none;
  color: var(--gl-white);
}}

.gl-nav-item > a:hover,
.gl-nav-item > a.active,
.gl-nav-dropdown a:hover {{
  color: var(--gl-klister);
}}

.gl-nav-item {{ position: relative; }}

.gl-nav-dropdown {{
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 220px;
  background: var(--gl-carbon);
  border: 1px solid var(--gl-hairline);
  padding: var(--gl-space-2) 0;
}}

.gl-nav-item:hover .gl-nav-dropdown {{ display: block; }}

.gl-nav-hamburger {{
  display: none;
  min-width: 44px;
  min-height: 44px;
  border: 0;
  background: transparent;
  color: var(--gl-white);
  font-size: 1.45rem;
  cursor: pointer;
}}

.gl-hero {{
  position: relative;
  overflow: hidden;
  background: var(--gl-carbon);
  color: var(--gl-white);
}}

.gl-hero::after {{
  content: "";
  position: absolute;
  top: 0;
  right: -72px;
  bottom: 0;
  width: 340px;
  background: repeating-linear-gradient(115deg, var(--gl-carbon) 0 26px, var(--gl-muted) 26px 27px, var(--gl-carbon) 27px 52px);
  opacity: .35;
}}

.gl-hero-inner {{
  position: relative;
  z-index: 1;
  max-width: var(--gl-measure);
  margin: 0 auto;
  padding: 52px var(--gl-space-5) 42px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  align-items: end;
  gap: var(--gl-space-6);
}}

.gl-hero-copy {{ min-width: 0; position: static; }}

.gl-hero-plate {{
  position: relative;
  z-index: 1;
  align-self: end;
  margin-top: 56px;
  min-height: 250px;
  display: flex;
  align-items: center;
}}

.gl-hero-kicker {{
  margin: 0 0 var(--gl-space-3);
  color: var(--gl-klister);
  font-family: var(--gl-font-data);
  font-size: .68rem;
  font-weight: 700;
  letter-spacing: .28em;
  text-transform: uppercase;
}}

.gl-hero-name {{
  max-width: 14ch;
  margin: 0 0 var(--gl-space-4);
  font-family: var(--gl-font-display);
  font-size: clamp(3rem, 8vw, 5.9rem);
  font-weight: 900;
  font-style: italic;
  line-height: .92;
  text-transform: uppercase;
  letter-spacing: 0;
  overflow-wrap: normal;
  hyphens: manual;
}}
.gl-hero-name--long {{ font-size: clamp(2.4rem, 6vw, 4.4rem); }}

.gl-hero-tagline {{
  max-width: 54ch;
  margin: 0 0 var(--gl-space-5);
  color: var(--gl-hairline);
  font-family: var(--gl-font-editorial);
  font-size: 1.08rem;
  font-style: italic;
  line-height: 1.55;
}}

.gl-hero-chips {{ display: flex; flex-wrap: wrap; gap: var(--gl-space-2); }}

.gl-chip {{
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  background: var(--gl-white);
  color: var(--gl-carbon);
  padding: var(--gl-space-2) var(--gl-space-3);
  font-family: var(--gl-font-data);
  font-size: .68rem;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
}}

.gl-scorebox {{
  position: absolute;
  right: var(--gl-space-4);
  top: 34px;
  z-index: 3;
  width: 136px;
  background: var(--gl-swix-red);
  color: var(--gl-white);
  padding: var(--gl-space-4) var(--gl-space-3) var(--gl-space-3);
  text-align: center;
  transform: rotate(2deg);
}}

.gl-scorebox-number {{
  display: block;
  font-family: var(--gl-font-display);
  font-size: 3.3rem;
  font-weight: 900;
  font-style: italic;
  line-height: .9;
}}

.gl-scorebox-label {{
  display: block;
  margin-top: var(--gl-space-2);
  font-family: var(--gl-font-data);
  font-size: .56rem;
  font-weight: 700;
  letter-spacing: .18em;
  text-transform: uppercase;
}}

.gl-art-plate {{
  width: 100%;
  height: auto;
  display: block;
  border: 3px solid var(--gl-white);
  background: var(--gl-carbon);
}}

.gl-plate-stripes {{ fill: var(--gl-carbon); }}
.gl-art-plate .gl-plate-stripes {{
  opacity: .9;
}}
.gl-art-plate--course .gl-plate-massif {{ fill: var(--gl-red-deep); }}
.gl-plate-profile,
.gl-plate-route {{
  fill: none;
  stroke: var(--gl-swix-red);
  stroke-width: 4;
  stroke-linecap: square;
  stroke-linejoin: round;
}}
.gl-plate-dot,
.gl-plate-square {{
  fill: var(--gl-klister);
}}
.gl-plate-label,
.gl-plate-title,
.gl-plate-stat,
.gl-plate-route-label {{
  fill: var(--gl-white);
  font-family: var(--gl-font-data);
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
}}
.gl-plate-label {{ font-size: 7px; }}
.gl-plate-title,
.gl-plate-route-label {{ font-size: 11px; }}
.gl-plate-stat {{ font-size: 8px; }}
.gl-plate-stat tspan:first-child {{ fill: var(--gl-klister); }}
.gl-plate-ridge {{
  fill: none;
  stroke: var(--gl-white);
  stroke-width: 2;
  opacity: .9;
}}
.gl-plate-ridge--quiet {{ opacity: .36; }}

.gl-waxbar {{ display: grid; grid-template-columns: repeat(4, 1fr); }}
.gl-wax {{
  position: relative;
  min-height: 44px;
  padding: var(--gl-space-3) var(--gl-space-4) calc(var(--gl-space-3) + 14px);
  color: var(--gl-white);
  font-family: var(--gl-font-data);
  font-size: .62rem;
  font-weight: 700;
  letter-spacing: .14em;
  text-transform: uppercase;
}}
.gl-wax-green {{ background: var(--gl-wax-green); }}
.gl-wax-blue {{ background: var(--gl-wax-blue); }}
.gl-wax-violet {{ background: var(--gl-wax-violet); }}
.gl-wax-red {{ background: var(--gl-swix-red); }}
.gl-wax {{ opacity: .45; }}
.gl-wax.active {{ opacity: 1; box-shadow: none; outline: 3px solid var(--gl-white); outline-offset: -3px; }}
.gl-waxbar-caption {{
  font-family: var(--gl-font-data);
  font-size: .58rem;
  font-weight: 700;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: var(--gl-carbon);
  padding: var(--gl-space-2) var(--gl-space-4);
  background: var(--gl-paper);
}}

.gl-section {{
  border-bottom: 1px solid var(--gl-hairline);
  padding: var(--gl-space-7) 0;
}}

.gl-section:last-of-type {{ border-bottom: 0; }}

.gl-section-header {{
  display: flex;
  align-items: baseline;
  gap: var(--gl-space-3);
  margin: 0 0 var(--gl-space-5);
  border-bottom: 4px solid var(--gl-carbon);
  padding-bottom: var(--gl-space-3);
}}

.gl-section-num {{
  color: var(--gl-swix-red);
  font-family: var(--gl-font-display);
  font-size: 1.15rem;
  font-weight: 900;
  font-style: italic;
}}

.gl-section-title {{
  margin: 0;
  font-family: var(--gl-font-display);
  font-size: clamp(1.45rem, 3vw, 2rem);
  font-weight: 900;
  font-style: italic;
  line-height: 1;
  letter-spacing: 0;
  text-transform: uppercase;
}}

.gl-section-prose,
.gl-feature-list li,
.gl-challenge-list li,
.gl-facts-list li {{
  max-width: var(--gl-prose);
  font-family: var(--gl-font-editorial);
  font-size: 1rem;
  line-height: 1.7;
}}

.gl-section-prose {{ margin: 0 0 var(--gl-space-4); }}

.gl-vitals-grid,
.gl-course-meta {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  border-top: 3px solid var(--gl-carbon);
}}

.gl-vital-cell,
.gl-course-meta-item {{
  background: var(--gl-white);
  border-right: 1px solid var(--gl-hairline);
  border-bottom: 1px solid var(--gl-hairline);
  padding: var(--gl-space-4);
}}

.gl-vital-label,
.gl-course-meta-label,
.gl-rating-label {{
  margin-bottom: var(--gl-space-1);
  color: var(--gl-muted);
  font-family: var(--gl-font-data);
  font-size: .64rem;
  font-weight: 700;
  letter-spacing: .16em;
  text-transform: uppercase;
}}

.gl-vital-value,
.gl-course-meta-value {{
  font-family: var(--gl-font-data);
  font-size: .86rem;
  font-weight: 700;
  color: var(--gl-carbon);
}}

.gl-feature-list,
.gl-challenge-list,
.gl-facts-list {{
  list-style: none;
  padding: 0;
  margin: var(--gl-space-5) 0 0;
}}

.gl-feature-list li,
.gl-challenge-list li,
.gl-facts-list li {{
  border-bottom: 1px solid var(--gl-hairline);
  padding: var(--gl-space-3) 0;
}}

.gl-climate-temp {{
  display: inline-block;
  margin-bottom: var(--gl-space-4);
  background: var(--gl-white);
  border: 3px solid var(--gl-carbon);
  padding: var(--gl-space-2) var(--gl-space-4);
  font-family: var(--gl-font-data);
  font-size: .78rem;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
}}

.gl-rating-bars {{ display: grid; gap: var(--gl-space-2); max-width: 760px; }}
.gl-rating-row {{ display: grid; grid-template-columns: 150px 1fr 36px; align-items: center; gap: var(--gl-space-3); }}
.gl-rating-label {{ text-align: right; margin: 0; }}
.gl-rating-track {{ height: 20px; background: var(--gl-white); border: 1px solid var(--gl-hairline); }}
.gl-rating-fill {{ height: 100%; background: var(--gl-carbon); }}
.gl-rating-value {{ font-family: var(--gl-font-data); font-weight: 700; text-align: center; }}
.gl-score-note {{
  max-width: var(--gl-prose);
  margin-top: var(--gl-space-5);
  border-left: 6px solid var(--gl-swix-red);
  padding: var(--gl-space-3) 0 var(--gl-space-3) var(--gl-space-5);
  font-style: italic;
}}

.gl-rise-grid {{
  display: grid;
  gap: var(--gl-space-5);
}}

.gl-process {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  border-top: 3px solid var(--gl-carbon);
}}

.gl-process-step {{
  background: var(--gl-white);
  border-right: 1px solid var(--gl-hairline);
  border-bottom: 1px solid var(--gl-hairline);
  padding: var(--gl-space-5);
}}

.gl-process-num {{
  display: inline-grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin-bottom: var(--gl-space-4);
  background: var(--gl-carbon);
  color: var(--gl-klister);
  font-family: var(--gl-font-display);
  font-size: 1.4rem;
  font-weight: 900;
  font-style: italic;
}}

.gl-process-step h3,
.gl-wax-call h3,
.gl-knowledge h3 {{
  margin: 0 0 var(--gl-space-2);
  font-family: var(--gl-font-display);
  font-size: 1.05rem;
  font-weight: 900;
  font-style: italic;
  letter-spacing: 0;
  line-height: 1;
  text-transform: uppercase;
}}

.gl-process-step p,
.gl-wax-card-face p,
.gl-knowledge-result {{
  margin: 0;
  font-size: .96rem;
  line-height: 1.55;
}}

.gl-wax-cards {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--gl-space-4);
}}

.gl-wax-card {{
  min-height: 184px;
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--gl-white);
  cursor: pointer;
  perspective: 900px;
  text-align: left;
}}

.gl-wax-card-inner {{
  display: block;
  position: relative;
  min-height: 184px;
  transform-style: preserve-3d;
  transition: transform .35s;
}}
@media (prefers-reduced-motion: reduce) {{
  .gl-wax-card-inner {{ transition: none; }}
}}

.gl-wax-card.is-flipped .gl-wax-card-inner {{ transform: rotateY(180deg); }}

.gl-wax-card-face {{
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: var(--gl-space-5);
  backface-visibility: hidden;
}}

.gl-wax-card-back {{
  background: var(--gl-carbon);
  transform: rotateY(180deg);
}}

.gl-wax-card-green .gl-wax-card-front {{ background: var(--gl-wax-green); }}
.gl-wax-card-blue .gl-wax-card-front {{ background: var(--gl-wax-blue); }}
.gl-wax-card-violet .gl-wax-card-front {{ background: var(--gl-wax-violet); }}
.gl-wax-card-red .gl-wax-card-front {{ background: var(--gl-swix-red); }}

.gl-wax-card-kicker,
.gl-knowledge-link {{
  font-family: var(--gl-font-data);
  font-size: .62rem;
  font-weight: 700;
  letter-spacing: .18em;
  text-transform: uppercase;
}}

.gl-knowledge {{
  background: var(--gl-white);
  border: 3px solid var(--gl-carbon);
  padding: var(--gl-space-5);
}}

.gl-quiz-options {{
  display: flex;
  flex-wrap: wrap;
  gap: var(--gl-space-3);
  margin: var(--gl-space-4) 0;
}}

.gl-quiz-option {{
  min-height: 44px;
  border: 2px solid var(--gl-carbon);
  background: var(--gl-white);
  color: var(--gl-carbon);
  padding: 0 var(--gl-space-4);
  font-family: var(--gl-font-data);
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
  cursor: pointer;
}}

.gl-quiz-option.is-correct {{ background: var(--gl-wax-green); color: var(--gl-white); border-color: var(--gl-wax-green); }}
.gl-quiz-option.is-wrong {{ background: var(--gl-swix-red); color: var(--gl-white); border-color: var(--gl-swix-red); }}
.gl-knowledge-result {{ min-height: 28px; font-style: italic; }}
.gl-knowledge-link {{ display: inline-block; margin-top: var(--gl-space-4); color: var(--gl-carbon); text-decoration: none; }}

.gl-series-badges {{ display: flex; flex-wrap: wrap; gap: var(--gl-space-2); }}
.gl-series-badge,
.gl-placeholder {{
  background: var(--gl-white);
  border: 1px solid var(--gl-hairline);
  padding: var(--gl-space-3) var(--gl-space-4);
  font-family: var(--gl-font-data);
  font-size: .72rem;
  font-weight: 700;
  letter-spacing: .14em;
  text-transform: uppercase;
}}

.gl-ladder {{ background: var(--gl-carbon); color: var(--gl-white); }}
.gl-ladder-inner {{ max-width: var(--gl-measure); margin: 0 auto; padding: 52px var(--gl-space-5) 56px; }}
.gl-ladder h2 {{
  margin: 0 0 var(--gl-space-2);
  font-family: var(--gl-font-display);
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 900;
  font-style: italic;
  letter-spacing: 0;
  line-height: .95;
  text-transform: uppercase;
}}
.gl-ladder-lead {{ margin: 0 0 var(--gl-space-6); color: var(--gl-hairline); font-style: italic; }}
.gl-rungs {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--gl-space-4); }}
.gl-rung {{ background: var(--gl-carbon); border: 1px solid var(--gl-muted); border-top: 6px solid var(--gl-swix-red); padding: var(--gl-space-5); }}
.gl-rung-kicker,
.gl-rung-price {{ color: var(--gl-klister); font-family: var(--gl-font-data); font-size: .62rem; font-weight: 700; letter-spacing: .2em; text-transform: uppercase; }}
.gl-rung h3 {{ margin: var(--gl-space-2) 0; font-family: var(--gl-font-display); font-size: 1.05rem; font-weight: 900; font-style: italic; text-transform: uppercase; letter-spacing: 0; }}
.gl-rung p {{ margin: 0 0 var(--gl-space-4); color: var(--gl-hairline); font-size: .9rem; line-height: 1.55; }}
.gl-rung-btn {{
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  margin-top: var(--gl-space-3);
  border: 2px solid var(--gl-white);
  color: var(--gl-white);
  padding: 0 var(--gl-space-4);
  font-family: var(--gl-font-data);
  font-size: .68rem;
  font-weight: 700;
  letter-spacing: .14em;
  text-decoration: none;
  text-transform: uppercase;
}}
.gl-rung-btn.apply {{ border-color: var(--gl-swix-red); background: var(--gl-swix-red); }}

.gl-capture {{ background: var(--gl-carbon); border-top: 3px solid var(--gl-klister); padding: var(--gl-space-6, 32px) var(--gl-space-5, 24px); }}
.gl-capture-inner {{ max-width: var(--gl-measure); margin: 0 auto; }}
.gl-capture-head {{ font-family: var(--gl-font-data); font-weight: 700; font-size: 1rem; letter-spacing: .12em; color: var(--gl-klister); margin: 0 0 4px; }}
.gl-capture-sub {{ font-family: var(--gl-font-data); font-size: .8rem; color: var(--gl-white); margin: 0 0 14px; }}
.gl-capture-row {{ display: flex; gap: 8px; }}
.gl-capture-input {{ flex: 1; padding: 12px; font-family: var(--gl-font-data); font-size: .85rem; border: 2px solid var(--gl-white); background: var(--gl-white); color: var(--gl-carbon); }}
.gl-capture-btn {{ padding: 12px 22px; font-family: var(--gl-font-data); font-weight: 700; letter-spacing: .1em; border: 2px solid var(--gl-paper); background: var(--gl-paper); color: var(--gl-carbon); cursor: pointer; }}
.gl-capture-btn:disabled {{ opacity: .6; cursor: wait; }}
.gl-capture-honey {{ position: absolute; left: -9999px; }}
.gl-capture-ok, .gl-capture-err {{ font-family: var(--gl-font-data); font-size: .85rem; color: var(--gl-klister); margin: 8px 0 0; }}
.gl-capture-err {{ color: var(--gl-white); }}
@media (max-width: 560px) {{ .gl-capture-row {{ flex-direction: column; }} }}
.gl-footer {{ background: var(--gl-swix-red); color: var(--gl-white); }}
.gl-footer-inner {{ max-width: var(--gl-measure); min-height: 72px; margin: 0 auto; padding: var(--gl-space-4) var(--gl-space-5); display: flex; align-items: center; justify-content: space-between; gap: var(--gl-space-5); }}
.gl-footer-links {{ display: flex; gap: var(--gl-space-4); flex-wrap: wrap; }}
.gl-footer-links a,
.gl-footer-motto {{ font-family: var(--gl-font-data); font-size: .64rem; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; text-decoration: none; }}
.gl-footer-motto {{ color: var(--gl-klister); }}

.gl-sticky-cta {{
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 200;
  background: var(--gl-carbon);
  border-top: 4px solid var(--gl-swix-red);
  transform: translateY(100%);
  padding: var(--gl-space-3) var(--gl-space-5);
}}
.gl-sticky-cta.visible {{ transform: translateY(0); }}
.gl-sticky-cta-inner {{ max-width: var(--gl-measure); margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: var(--gl-space-4); }}
.gl-sticky-cta-name {{ color: var(--gl-white); font-style: italic; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.gl-sticky-cta-actions {{ display: flex; align-items: center; gap: var(--gl-space-3); }}
.gl-sticky-cta-btn {{ min-height: 44px; display: inline-flex; align-items: center; background: var(--gl-swix-red); color: var(--gl-white); padding: 0 var(--gl-space-4); font-family: var(--gl-font-data); font-size: .7rem; font-weight: 700; letter-spacing: .14em; text-decoration: none; text-transform: uppercase; white-space: nowrap; }}
.gl-sticky-cta-dismiss {{ min-width: 44px; min-height: 44px; border: 0; background: transparent; color: var(--gl-white); font-size: 1.4rem; cursor: pointer; }}

.gl-cookie-consent {{
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  display: none;
  background: var(--gl-carbon);
  border-top: 4px solid var(--gl-swix-red);
  padding: var(--gl-space-5);
}}
.gl-cookie-consent.visible {{ display: block; }}
.gl-cookie-inner {{ max-width: var(--gl-measure); margin: 0 auto; display: flex; align-items: center; justify-content: space-between; gap: var(--gl-space-4); flex-wrap: wrap; }}
.gl-cookie-text {{ margin: 0; color: var(--gl-white); max-width: 62ch; }}
.gl-cookie-buttons {{ display: flex; gap: var(--gl-space-2); }}
.gl-cookie-btn {{ min-width: 44px; min-height: 44px; border: 2px solid var(--gl-white); padding: 0 var(--gl-space-4); font-family: var(--gl-font-data); font-size: .72rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; cursor: pointer; }}
.gl-cookie-btn.accept {{ background: var(--gl-swix-red); color: var(--gl-white); border-color: var(--gl-swix-red); }}
.gl-cookie-btn.decline {{ background: transparent; color: var(--gl-white); }}

a:focus-visible, button:focus-visible {{ outline: 3px solid var(--gl-klister); outline-offset: 2px; }}

@media (max-width: 820px) {{
  .gl-hero-name,
  .gl-hero-tagline {{ margin-right: 0; }}
  .gl-hero-inner {{ grid-template-columns: 1fr; }}
  .gl-hero-copy {{ padding-right: 0; }}
  .gl-hero-plate {{ min-height: 0; max-width: 440px; }}
  .gl-scorebox {{ position: static; margin: var(--gl-space-5) 0 0; }}
  .gl-waxbar,
  .gl-rungs,
  .gl-process,
  .gl-wax-cards {{ grid-template-columns: 1fr 1fr; }}
}}

@media (max-width: 640px) {{
  .gl-nav-links {{ display: none; position: absolute; top: 56px; left: 0; right: 0; background: var(--gl-carbon); flex-direction: column; align-items: stretch; padding: var(--gl-space-3) var(--gl-space-5); border-bottom: 3px solid var(--gl-carbon); }}
  .gl-nav-links.open {{ display: flex; }}
  .gl-nav-hamburger {{ display: block; }}
  .gl-nav-dropdown {{ position: static; display: block; border: 0; padding: 0 0 0 var(--gl-space-4); }}
  .gl-nav-item > a {{ padding: 0; }}
  .gl-hero-inner {{ padding-top: 40px; }}
  .gl-waxbar,
  .gl-rungs,
  .gl-process,
  .gl-wax-cards,
  .gl-rating-row {{ grid-template-columns: 1fr; }}
  .gl-rating-label {{ text-align: left; }}
  .gl-sticky-cta-name {{ display: none; }}
  .gl-footer-inner {{ align-items: flex-start; flex-direction: column; }}
}}
"""


# ── HTML Builders ──────────────────────────────────────────────

def build_email_capture(race: dict) -> str:
    """Friend-register email capture — posts to the multi-brand lead worker
    (brand: xcskilabs). Deadpan register: about them, one field, no promises."""
    r = race.get("race", race)
    name = esc(r.get("display_name") or r.get("name", ""))
    slug = esc(r.get("slug", ""))
    return f"""
<section class="gl-capture" id="gl-capture">
  <div class="gl-capture-inner">
    <p class="gl-capture-head">GETTING READY FOR {name}?</p>
    <p class="gl-capture-sub">Leave your email. I'll help.</p>
    <form class="gl-capture-form" id="gl-capture-form" autocomplete="off">
      <input type="hidden" name="race_name" value="{name}">
      <input type="hidden" name="race_slug" value="{slug}">
      <input type="text" name="website" value="" tabindex="-1" autocomplete="off" aria-hidden="true" class="gl-capture-honey">
      <div class="gl-capture-row">
        <input class="gl-capture-input" type="email" name="email" required placeholder="you@example.com" aria-label="Email address">
        <button class="gl-capture-btn" type="submit">SEND</button>
      </div>
    </form>
    <p class="gl-capture-ok" id="gl-capture-ok" hidden>&#10003; Got it &mdash; reply when my email lands.</p>
    <p class="gl-capture-err" id="gl-capture-err" hidden>That didn't send. Try once more.</p>
  </div>
</section>"""


def build_capture_js() -> str:
    """Trail capture (localStorage xc_viewed_races) + capture form submit."""
    return """<script>
(function() {
  // trail: remember the last 5 race pages viewed (first-party, local only)
  try {
    var f0 = document.getElementById('gl-capture-form');
    var slug = f0 && f0.elements.race_slug ? f0.elements.race_slug.value : '';
    var name = f0 && f0.elements.race_name ? f0.elements.race_name.value : '';
    if (slug && name) {
      var races = [];
      try { races = JSON.parse(localStorage.getItem('xc_viewed_races') || '[]'); } catch (e) {}
      if (!Array.isArray(races)) races = [];
      races = races.filter(function(r) { return r && r.slug !== slug; });
      races.unshift({ slug: slug, name: name });
      localStorage.setItem('xc_viewed_races', JSON.stringify(races.slice(0, 5)));
    }
  } catch (e) {}

  var form = document.getElementById('gl-capture-form');
  if (!form) return;
  form.addEventListener('submit', function(ev) {
    ev.preventDefault();
    var ok = document.getElementById('gl-capture-ok');
    var err = document.getElementById('gl-capture-err');
    var btn = form.querySelector('.gl-capture-btn');
    // honeypot: bots get a fake success, no network call
    if (form.elements.website && form.elements.website.value) {
      form.hidden = true; if (ok) ok.hidden = false; return;
    }
    var viewed = [];
    try {
      viewed = (JSON.parse(localStorage.getItem('xc_viewed_races') || '[]') || [])
        .map(function(r) { return r && typeof r.name === 'string' ? r.name : null; }).filter(Boolean).slice(0, 5);
    } catch (e) {}
    if (btn) btn.disabled = true;
    if (err) err.hidden = true;
    fetch('https://fueling-lead-intake.gravelgodcoaching.workers.dev', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source: 'race_profile',
        brand: 'xcskilabs',
        email: form.elements.email.value,
        race_name: form.elements.race_name.value,
        race_slug: form.elements.race_slug.value,
        viewed_races: viewed,
        website: ''
      })
    }).then(function(resp) { return resp.ok ? resp.json() : Promise.reject(); })
      .then(function(data) {
        if (data && data.success === true) { form.hidden = true; if (ok) ok.hidden = false; }
        else { return Promise.reject(); }
      })
      .catch(function() { if (btn) btn.disabled = false; if (err) err.hidden = false; });
  });
})();
</script>"""


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
    <a href="/" class="gl-nav-logo" aria-label="XC SKI LABS">XC SKI <em>LABS</em></a>
    <button class="gl-nav-hamburger" aria-label="Toggle navigation" aria-expanded="false" data-nav-toggle>&#9776;</button>
    <ul class="gl-nav-links">
      <li class="gl-nav-item">
        <a href="/search/"{_active("races")}>Races</a>
        <div class="gl-nav-dropdown"><a href="/search/">All races</a></div>
      </li>
      <li class="gl-nav-item"><a href="/guide/"{_active("guide")}>Guide</a></li>
      <li class="gl-nav-item"><a href="/training-plans/"{_active("plans")}>Plans</a></li>
      <li class="gl-nav-item"><a href="/coaching/"{_active("coaching")}>Coaching</a></li>
      <li class="gl-nav-item"><a href="/about/"{_active("about")}>About</a></li>
    </ul>
  </div>
</nav>
"""


def build_hero(race: dict) -> str:
    """Carbon race hero with scorebox and data chips."""
    v = race["vitals"]
    r = race["nordic_lab_rating"]
    tier = r["tier"]
    score = r["overall_score"]
    discipline = r.get("discipline", v.get("discipline", "classic"))

    chips = []
    if v.get("distance_km"):
        chips.append(format_distance(v["distance_km"]).upper())
    if discipline:
        chips.append(DISCIPLINE_LABELS.get(discipline, discipline).upper())
    if v.get("date"):
        chips.append(str(v["date"]).upper())
    if v.get("location_badge") or v.get("location"):
        chips.append(str(v.get("location_badge", v.get("location"))).upper())

    chips_html = "".join(f'<span class="gl-chip">{esc(chip)}</span>' for chip in chips)
    kicker = f'{tier_label(tier)} · {_series_label(race)} · {v.get("country", "")}'
    plate_html, _ = build_hero_plate(race)

    return f"""
<section class="gl-hero" id="hero">
  <div class="gl-hero-inner">
    <div class="gl-hero-copy">
      <p class="gl-hero-kicker">{esc(kicker)}</p>
      <h1 class="{_hero_name_class(race.get("display_name", race["name"]))}">{_display_caps(race.get("display_name", race["name"]))}</h1>
      <p class="gl-hero-tagline">{esc(race.get("tagline", ""))}</p>
      <div class="gl-hero-chips">{chips_html}</div>
      <div class="gl-scorebox" aria-label="Lab Score {score} out of 100">
        <span class="gl-scorebox-number">{score}</span>
        <span class="gl-scorebox-label">Lab Score</span>
      </div>
    </div>
    {plate_html}
  </div>
</section>
"""


def build_wax_bar(race: dict) -> str:
    """Temperature wax bar, omitted if the profile range cannot be parsed."""
    parsed = parse_temperature_range(race.get("climate", {}).get("typical_temp_c"))
    if parsed is None:
        return ""
    low, high = parsed
    segments = []
    active_count = 0
    for key, label, seg_low, seg_high in WAX_SEGMENTS:
        active = _ranges_overlap(low, high, seg_low, seg_high)
        if active:
            active_count += 1
        classes = f"gl-wax gl-wax-{key}" + (" active" if active else "")
        segments.append(f'<div class="{classes}">{esc(label)}</div>')
    if active_count == 0:
        return ""
    # One caption for the whole range — a caret per segment reads as three alarms
    caption = (
        f'<div class="gl-waxbar-caption">&#9650; RACE DAY &middot; '
        f'{esc(f"{low:g}")}&deg; TO {esc(f"{high:g}")}&deg;C TYPICAL</div>'
    )
    return (
        '<div class="gl-waxbar" aria-label="Race day wax temperature range">'
        + "".join(segments) + "</div>" + caption
    )


def build_section_header(num: str, title: str) -> str:
    return f'<div class="gl-section-header"><span class="gl-section-num">{esc(num)}</span><h2 class="gl-section-title">{esc(title)}</h2></div>'


def build_at_a_glance(race: dict) -> str:
    """[02] At a Glance vitals grid."""
    v = race["vitals"]
    r = race["nordic_lab_rating"]
    discipline = r.get("discipline", v.get("discipline", ""))

    cells = [
        ("Distance", format_distance(v.get("distance_km"))),
        ("Elevation", format_elevation(v.get("elevation_m"))),
        ("Altitude", format_altitude(v.get("altitude_m"))),
        ("Field Size", v.get("field_size", "—")),
        ("Founded", str(v.get("founded", "—")) if v.get("founded") else "—"),
        ("Technique", DISCIPLINE_LABELS.get(discipline, discipline or "—")),
        ("Format", (race.get("course", {}).get("format", "—") or "—").replace("-", " ").title()),
        ("Date", v.get("date", "—")),
    ]

    # Add distance options if present
    dist_opts = v.get("distance_options", [])
    if dist_opts:
        cells.append(("Distances", " | ".join(dist_opts)))

    # Add location
    loc_badge = v.get("location_badge", v.get("location", ""))
    if loc_badge:
        cells.append(("Location", loc_badge))

    cells_html = ""
    for label, value in cells:
        cells_html += (
            f'<div class="gl-vital-cell">'
            f'<div class="gl-vital-label">{esc(label)}</div>'
            f'<div class="gl-vital-value">{esc(value)}</div>'
            f'</div>'
        )

    return f"""
<section class="gl-section" id="vitals">
  {build_section_header('01', 'Race vitals')}
  <div class="gl-vitals-grid">
    {cells_html}
  </div>
</section>
"""


def build_course(race: dict) -> str:
    """[03] Course section."""
    course = race.get("course", {})
    if not course:
        return ""

    primary = course.get("primary", "")
    fmt = (course.get("format") or "").replace("-", " ").title()
    surface = course.get("surface", "")
    tech = _parse_score(course.get("technical_rating"))
    grooming = course.get("grooming", "")
    features = course.get("features", [])

    meta_items = []
    if fmt:
        meta_items.append(("Format", fmt))
    if surface:
        meta_items.append(("Surface", surface))
    if tech is not None:
        meta_items.append(("Technical Rating", f"{tech} / 5"))
    if grooming:
        meta_items.append(("Grooming", grooming))

    meta_html = ""
    for label, value in meta_items:
        meta_html += (
            f'<div class="gl-course-meta-item">'
            f'<div class="gl-course-meta-label">{esc(label)}</div>'
            f'<div class="gl-course-meta-value">{esc(value)}</div>'
            f'</div>'
        )

    features_html = ""
    if features:
        items = "".join(f"<li>{esc(f)}</li>" for f in features)
        features_html = f'<ul class="gl-feature-list">{items}</ul>'

    return f"""
<section class="gl-section" id="course">
  {build_section_header('02', 'Course overview')}
  <div class="gl-course-meta">{meta_html}</div>
  <p class="gl-section-prose">{esc(primary)}</p>
  {features_html}
</section>
"""


def build_climate(race: dict) -> str:
    """[04] Climate section."""
    climate = race.get("climate", {})
    if not climate:
        return ""

    desc = climate.get("description", "")
    temp = climate.get("typical_temp_c", "")
    challenges = climate.get("challenges", [])

    temp_html = ""
    if temp:
        temp_html = f'<div class="gl-climate-temp">Typical: {esc(temp)}</div>'

    challenges_html = ""
    if challenges:
        items = "".join(f"<li>{esc(c)}</li>" for c in challenges)
        challenges_html = f'<ul class="gl-challenge-list">{items}</ul>'

    return f"""
<section class="gl-section" id="climate">
  {build_section_header('04', 'Weather and conditions')}
  {temp_html}
  <p class="gl-section-prose">{esc(desc)}</p>
  {challenges_html}
</section>
"""


def _discipline_phrase(race: dict) -> str:
    v = race.get("vitals", {})
    raw = race.get("nordic_lab_rating", {}).get("discipline", v.get("discipline", ""))
    if raw == "classic":
        return "classic kick and glide"
    if raw == "skate":
        return "skate pacing"
    if raw == "both":
        return "classic and skate options"
    return str(raw).replace("_", " ") if raw else "race technique"


def build_race_week_stepper(race: dict) -> str:
    name = race.get("display_name", race.get("name", "the race"))
    date = race.get("vitals", {}).get("date_specific") or race.get("vitals", {}).get("date") or "race day"
    discipline = _discipline_phrase(race)
    steps = [
        ("Check the week", f"Use the {esc(date)} timing as the anchor. Confirm travel, bib pickup, and the latest organizer notices before you adjust training."),
        ("Tune the sessions", f"Keep the final intensity short and specific to {esc(discipline)}. The goal is readiness, not added fitness."),
        ("Set race morning", f"Pack layers, food, and wax options for {esc(name)} before the last evening. Leave only weather checks for the morning."),
    ]
    cards = []
    for idx, (title, body) in enumerate(steps, start=1):
        cards.append(f"""
    <div class="gl-process-step">
      <span class="gl-process-num">{idx}</span>
      <h3>{esc(title)}</h3>
      <p>{body}</p>
    </div>""")
    return f"""
  <div class="gl-process" aria-label="Race week protocol">
    {''.join(cards)}
  </div>
"""


def build_wax_call_cards(race: dict) -> str:
    parsed = parse_temperature_range(race.get("climate", {}).get("typical_temp_c"))
    if parsed is None:
        return ""
    cards = []
    for band in select_wax_card_bands(parsed):
        cards.append(f"""
    <button class="gl-wax-card gl-wax-card-{esc(band['key'])}" type="button" aria-pressed="false">
      <span class="gl-wax-card-inner">
        <span class="gl-wax-card-face gl-wax-card-front">
          <span class="gl-wax-card-kicker">{esc(band['range'])}</span>
          <span><h3>{esc(band['label'])}</h3><p>Scenario for this race's typical temperature window.</p></span>
        </span>
        <span class="gl-wax-card-face gl-wax-card-back">
          <span class="gl-wax-card-kicker">Standard kick wax</span>
          <span><h3>Wax call</h3><p>{esc(band['guidance'])}</p></span>
        </span>
      </span>
    </button>""")
    return f"""
  <div class="gl-wax-call">
    <h3>Wax call</h3>
    <div class="gl-wax-cards">{''.join(cards)}</div>
  </div>
"""


def build_knowledge_check(race: dict) -> str:
    fact = build_quiz_fact(race)
    if fact is None:
        return ""
    slug = esc(race["slug"])
    options = "".join(
        f'<button class="gl-quiz-option" type="button" data-answer="{esc(opt)}">{esc(opt)}{(" KM" if fact["question"] == "Main distance?" else "")}</button>'
        for opt in fact["options"]
    )
    correct_display = f'{fact["correct"]} KM' if fact["question"] == "Main distance?" else str(fact["correct"])
    return f"""
  <div class="gl-knowledge" data-quiz-correct="{esc(fact['correct'])}" data-quiz-feedback="{esc(fact['feedback'])}">
    <h3>Knowledge check</h3>
    <p class="gl-section-prose">{esc(fact['question'])}</p>
    <div class="gl-quiz-options" role="group" aria-label="Knowledge check options">{options}</div>
    <p class="gl-knowledge-result" aria-live="polite" data-empty="Choose one answer.">Choose one answer.</p>
    <a class="gl-knowledge-link" href="/questionnaire/?race={slug}">Build my {esc(race.get('display_name', race.get('name', 'race')))} plan &rarr;</a>
    <span class="gl-placeholder" hidden>{esc(correct_display)}</span>
  </div>
"""


def build_interactive_blocks(race: dict) -> str:
    wax = build_wax_call_cards(race)
    quiz = build_knowledge_check(race)
    if not wax and not quiz:
        return ""
    return f"""
<section class="gl-section" id="race-week">
  {build_section_header('03', 'Race week')}
  <div class="gl-rise-grid">
    {build_race_week_stepper(race)}
    {wax}
    {quiz}
  </div>
</section>
"""


def build_rating_breakdown(race: dict) -> str:
    """[05] Rating Breakdown with horizontal bars."""
    r = race["nordic_lab_rating"]

    rows_html = ""
    for key, label in RATING_CRITERIA:
        score = _parse_score(r.get(key))
        if score is None:
            continue
        pct = (score / 5) * 100
        score_class = f"score-{score}" if 1 <= score <= 5 else "score-3"
        rows_html += (
            f'<div class="gl-rating-row">'
            f'<div class="gl-rating-label">{esc(label)}</div>'
            f'<div class="gl-rating-track">'
            f'<div class="gl-rating-fill {score_class}" style="width:{pct}%"></div>'
            f'</div>'
            f'<div class="gl-rating-value">{score}</div>'
            f'</div>'
        )

    # Score note
    note_html = ""
    score_note = r.get("score_note", "")
    if score_note:
        note_html = f'<div class="gl-score-note">{esc(score_note)}</div>'

    return f"""
<section class="gl-section" id="rating">
  {build_section_header('05', '14-criteria analysis')}
  <div class="gl-rating-bars">
    {rows_html}
  </div>
  {note_html}
</section>
"""


def build_history(race: dict) -> str:
    """[06] History section."""
    history = race.get("history", {})
    if not history:
        return ""

    summary = history.get("summary", "")
    facts = history.get("notable_facts", [])

    facts_html = ""
    if facts:
        items = "".join(f"<li>{esc(f)}</li>" for f in facts)
        facts_html = f'<ul class="gl-facts-list">{items}</ul>'

    return f"""
<section class="gl-section" id="history">
  {build_section_header('06', 'History and heritage')}
  <p class="gl-section-prose">{esc(summary)}</p>
  {facts_html}
</section>
"""


def build_series(race: dict) -> str:
    """[07] Series Membership badges."""
    series = race.get("series_membership", [])
    if not series:
        return ""

    badges_html = ""
    for s in series:
        label = SERIES_LABELS.get(s, s.replace("_", " ").title())
        css_class = "worldloppet" if "worldloppet" in s else (
            "ski-classics" if "ski_classics" in s else (
                "euroloppet" if "euroloppet" in s else ""
            )
        )
        badges_html += f'<span class="gl-series-badge {css_class}">{esc(label)}</span>'

    return f"""
<section class="gl-section" id="series">
  {build_section_header('07', 'Race series')}
  <div class="gl-series-badges">
    {badges_html}
  </div>
</section>
"""


def build_youtube_placeholder(race: dict) -> str:
    """[08] YouTube placeholder section."""
    videos = race.get("youtube_data", {}).get("videos", [])
    if videos:
        # Future: render actual videos here
        return ""

    return f"""
<section class="gl-section" id="videos">
  {build_section_header('08', 'Race videos')}
  <div class="gl-placeholder">VIDEO ENRICHMENT COMING SOON</div>
</section>
"""


def build_product_ladder(race: dict) -> str:
    """Product ladder band for high-intent race pages."""
    slug = esc(race["slug"])
    rungs = [
        ("Plans", "Training plans", "Structured blocks for classic ski-marathon preparation.", "FROM $60", "/training-plans/", "Browse", False, False),
        ("Custom", "Custom plan", "Your race, your hours, your history. Built from the intake.", "$60-$249", f"/questionnaire/?race={slug}", "Start the intake", False, False),
        ("Coaching", "1:1 coaching", "A person reads your training and adjusts the plan as life changes.", "$199-$1,200 / 4 WK", "/coaching/apply/", "Apply", True, False),
    ]
    learn_path = DEFAULT_OUTPUT_DIR / "learn" / "index.html"
    if learn_path.exists():
        rungs.insert(2, ("Course", "XC ski course", "Self-paced lessons from first glide to race preparation.", "SELF-PACED", "/learn/", "See the course", False, True))

    cards = []
    for kicker, title, desc, price, href, label, primary, nofollow in rungs:
        rel = ' rel="nofollow"' if nofollow else ""
        btn_class = "gl-rung-btn apply" if primary else "gl-rung-btn"
        cards.append(f"""
    <div class="gl-rung gl-training-card">
      <span class="gl-rung-kicker">{esc(kicker)}</span>
      <h3>{esc(title)}</h3>
      <p>{esc(desc)}</p>
      <span class="gl-rung-price">{esc(price)}</span><br>
      <a class="{btn_class}" href="{href}"{rel}>{esc(label)}</a>
    </div>""")

    return f"""
<section class="gl-ladder" id="training">
  <div class="gl-ladder-inner">
    <h2>Get race ready</h2>
    <p class="gl-ladder-lead">Choose the amount of structure you want around the start line.</p>
    <div class="gl-rungs">{''.join(cards)}</div>
  </div>
</section>
"""


def build_sticky_cta(race: dict) -> str:
    """Sticky CTA bar fixed to bottom of page."""
    name = esc(race.get("display_name", race["name"]))
    slug = esc(race["slug"])

    return f"""
<div class="gl-sticky-cta" id="gl-sticky-cta">
  <div class="gl-sticky-cta-inner">
    <span class="gl-sticky-cta-name">{name}</span>
    <div class="gl-sticky-cta-actions">
      <a href="/questionnaire/?race={slug}" class="gl-sticky-cta-btn" id="gl-sticky-cta-link">
        <span id="gl-sticky-cta-text">Build my plan</span>
      </a>
      <button class="gl-sticky-cta-dismiss" data-sticky-dismiss aria-label="Dismiss">&times;</button>
    </div>
  </div>
</div>
"""


def build_interactions_js() -> str:
    """Small dependency-free handlers for page controls."""
    return """
<script>
(function() {
  var navToggle = document.querySelector('[data-nav-toggle]');
  var navLinks = document.querySelector('.gl-nav-links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function() {
      var open = navLinks.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  var dismiss = document.querySelector('[data-sticky-dismiss]');
  if (dismiss) {
    dismiss.addEventListener('click', function() {
      var cta = document.getElementById('gl-sticky-cta');
      if (cta) { cta.style.display = 'none'; }
      try { sessionStorage.setItem('xl-cta-dismissed', '1'); } catch(e) {}
    });
  }

  document.querySelectorAll('.gl-wax-card').forEach(function(card) {
    card.addEventListener('click', function() {
      var flipped = card.classList.toggle('is-flipped');
      card.setAttribute('aria-pressed', flipped ? 'true' : 'false');
    });
  });

  document.querySelectorAll('.gl-knowledge').forEach(function(quiz) {
    var correct = quiz.getAttribute('data-quiz-correct');
    var feedback = quiz.getAttribute('data-quiz-feedback') || '';
    var result = quiz.querySelector('.gl-knowledge-result');
    quiz.querySelectorAll('.gl-quiz-option').forEach(function(button) {
      button.addEventListener('click', function() {
        quiz.querySelectorAll('.gl-quiz-option').forEach(function(option) {
          option.classList.remove('is-correct', 'is-wrong');
          option.disabled = true;
        });
        if (button.getAttribute('data-answer') === correct) {
          button.classList.add('is-correct');
          if (result) { result.textContent = feedback; }
        } else {
          button.classList.add('is-wrong');
          var correctButton = quiz.querySelector('[data-answer="' + correct + '"]');
          if (correctButton) { correctButton.classList.add('is-correct'); }
          if (result) { result.textContent = 'Not quite. ' + feedback; }
        }
      });
    });
  });
})();
</script>
"""


def build_sticky_js() -> str:
    """JavaScript for sticky CTA bar visibility logic."""
    return """
<script>
(function() {
  var cta = document.getElementById('gl-sticky-cta');
  if (!cta) return;
  try { if (sessionStorage.getItem('xl-cta-dismissed')) { cta.style.display = 'none'; return; } } catch(e) {}
  var hero = document.getElementById('hero') || document.querySelector('.gl-hero');
  var training = document.getElementById('training');
  if (!hero) return;
  var heroVisible = true;
  var trainingVisible = false;
  function update() {
    requestAnimationFrame(function() {
      if (heroVisible || trainingVisible) {
        cta.classList.remove('visible');
      } else {
        cta.classList.add('visible');
      }
    });
  }
  var heroObs = new IntersectionObserver(function(entries) {
    if (entries.length > 0) { heroVisible = entries[0].isIntersecting; }
    update();
  }, { threshold: 0 });
  heroObs.observe(hero);
  if (training) {
    var trainObs = new IntersectionObserver(function(entries) {
      if (entries.length > 0) { trainingVisible = entries[0].isIntersecting; }
      update();
    }, { threshold: 0 });
    trainObs.observe(training);
  }
})();
</script>
"""


def build_footer(race: dict) -> str:
    """Red footer strip."""
    return """
<footer class="gl-footer">
  <div class="gl-footer-inner">
    <span class="gl-footer-logo">XC SKI <em>LABS</em></span>
    <span class="gl-footer-motto">BUILT FOR SKIERS WHO CHASE START LINES</span>
    <span class="gl-footer-links"><a href="/search/">Back to search</a><a href="/">Home</a></span>
  </div>
</footer>
"""


def build_jsonld(race: dict) -> str:
    """Build SportsEvent JSON-LD structured data."""
    v = race["vitals"]
    r = race["nordic_lab_rating"]

    event = {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": race["name"],
        "sport": "Cross-Country Skiing",
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {
            "@type": "Place",
            "name": v.get("location", ""),
            "address": {
                "@type": "PostalAddress",
                "addressCountry": v.get("country_code", ""),
            },
        },
    }

    if v.get("lat") and v.get("lng"):
        event["location"]["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": v["lat"],
            "longitude": v["lng"],
        }

    if v.get("website"):
        event["url"] = v["website"]

    event["review"] = {
        "@type": "Review",
        "author": {
            "@type": "Organization",
            "name": "XC Ski Labs",
        },
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": str(r["overall_score"]),
            "bestRating": "100",
            "worstRating": "0",
        },
    }

    return (
        '<script type="application/ld+json">'
        + _safe_json_for_script(event, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
    )


# ── Page Assembly ──────────────────────────────────────────────

def generate_page(race: dict) -> str:
    """Generate a complete HTML page for a race."""
    name = race.get("display_name", race["name"])
    slug = race["slug"]
    r = race["nordic_lab_rating"]
    tier = r["tier"]
    score = r["overall_score"]
    v = race["vitals"]
    country = v.get("country", "")

    title = f"{esc(name)} | XC Ski Labs XC Ski Race Review"
    description = (
        f"{esc(race.get('tagline', name))} "
        f"Rated {score}/100 (Tier {tier}) in {esc(country)}. "
        f"Course, climate, ratings &amp; full breakdown."
    )

    css = build_css()
    jsonld = build_jsonld(race)
    ga4_snippet = build_ga4_snippet()

    nav_header = build_nav_header()
    hero = build_hero(race)
    vitals = build_at_a_glance(race)
    course = build_course(race)
    interactive = build_interactive_blocks(race)
    climate = build_climate(race)
    rating = build_rating_breakdown(race)
    wax_bar = build_wax_bar(race)
    ladder = build_product_ladder(race)
    history = build_history(race)
    series = build_series(race)
    youtube = build_youtube_placeholder(race)
    sticky_cta = build_sticky_cta(race)
    interactions_js = build_interactions_js()
    sticky_js = build_sticky_js()
    cookie_consent = build_cookie_consent()
    footer = build_footer(race)
    capture = build_email_capture(race)
    capture_js = build_capture_js()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="index, follow">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="article">
  {jsonld}
  {ga4_snippet}
  <style>{css}</style>
</head>
<body>
<a href="#course" class="gl-skip-link">Skip to content</a>
{nav_header}
<div class="gl-page">
{hero}
{wax_bar}
<div class="gl-wrap">
{vitals}
{course}
{interactive}
{climate}
{rating}
{history}
{series}
{youtube}
</div>
</div>
{ladder}
{capture}
<div class="gl-page">
{footer}
</div>
{sticky_cta}
{capture_js}
{interactions_js}
{sticky_js}
{cookie_consent}
</body>
</html>"""


# ── File I/O ───────────────────────────────────────────────────

def load_race(filepath: Path) -> Optional[dict]:
    """Load and validate a race JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        race = data.get("race")
        if not race:
            print(f"  SKIP {filepath.name}: no 'race' key")
            return None
        if not race.get("slug"):
            print(f"  SKIP {filepath.name}: no 'slug'")
            return None
        if not race.get("nordic_lab_rating"):
            print(f"  SKIP {filepath.name}: no 'nordic_lab_rating'")
            return None
        return race
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ERROR {filepath.name}: {e}")
        return None


def generate_all(data_dir: Path, output_dir: Path, slug_filter: Optional[str] = None):
    """Generate HTML pages for all races (or a single slug)."""
    files = sorted(data_dir.glob("*.json"))
    files = [f for f in files if f.name != "_schema.json"]

    if slug_filter:
        target = data_dir / f"{slug_filter}.json"
        if not target.exists():
            print(f"ERROR: No race file found for slug '{slug_filter}'")
            print(f"  Expected: {target}")
            sys.exit(1)
        files = [target]

    output_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    errors = 0
    tiers = {1: 0, 2: 0, 3: 0, 4: 0}
    art_records: dict[str, dict[str, str]] = {}

    for filepath in files:
        race = load_race(filepath)
        if not race:
            errors += 1
            continue

        slug = race["slug"]
        tier = race["nordic_lab_rating"]["tier"]
        _, art_record = build_hero_plate(race)
        art_records[slug] = art_record
        if art_record["tier"] == "A" and art_record["license"].startswith("UNVERIFIED"):
            print(f"  WARN {slug}: missing GPX license file for {art_record['source']}")

        page_html = generate_page(race)

        # Write to output/{slug}/index.html
        page_dir = output_dir / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        out_path = page_dir / "index.html"
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(page_html)

        total += 1
        tiers[tier] = tiers.get(tier, 0) + 1

    write_art_manifest(art_records)
    print(f"\nGenerated {total} race pages → {output_dir}/")
    if errors:
        print(f"  Skipped/errors: {errors}")
    print(f"  T1: {tiers.get(1, 0)} | T2: {tiers.get(2, 0)} | T3: {tiers.get(3, 0)} | T4: {tiers.get(4, 0)}")


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate XC Ski Labs race pages from JSON profiles."
    )
    parser.add_argument(
        "--slug",
        type=str,
        default=None,
        help="Generate a single race by slug (e.g., vasaloppet)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(DEFAULT_DATA_DIR),
        help=f"Race data directory (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        sys.exit(1)

    print(f"XC Ski Labs Race Page Generator")
    print(f"  Data: {data_dir}")
    print(f"  Output: {output_dir}")
    if args.slug:
        print(f"  Slug: {args.slug}")
    print()

    generate_all(data_dir, output_dir, args.slug)


if __name__ == "__main__":
    main()
