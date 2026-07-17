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
DEFAULT_INDEX_PATH = SCRIPT_DIR.parent / "web" / "race-index.json"
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

RATING_GROUPS = [
    (
        "course",
        "Course & conditions",
        [
            "distance",
            "elevation",
            "altitude",
            "course_technicality",
            "snow_reliability",
            "grooming_quality",
            "scenery",
        ],
    ),
    (
        "experience",
        "Race experience",
        [
            "field_size",
            "prestige",
            "international_draw",
            "accessibility",
            "community",
            "organization",
            "competitive_depth",
        ],
    ),
]

RATING_LABELS = dict(RATING_CRITERIA)

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

.gl-breadcrumb {{
  max-width: var(--gl-measure);
  margin: 0 auto;
  padding: var(--gl-space-2) var(--gl-space-5);
  font-family: var(--gl-font-data);
  font-size: .64rem;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
}}
.gl-breadcrumb a {{ color: var(--gl-muted); text-decoration: none; }}
.gl-breadcrumb a:hover {{ color: var(--gl-swix-red); }}
.gl-breadcrumb-sep {{ margin: 0 var(--gl-space-2); color: var(--gl-hairline); }}
.gl-breadcrumb-current {{ color: var(--gl-carbon); }}

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

.gl-scorebox-tier {{
  display: block;
  margin-top: var(--gl-space-2);
  border-top: 1px solid var(--gl-white);
  padding-top: var(--gl-space-2);
  font-family: var(--gl-font-data);
  font-size: .62rem;
  font-weight: 700;
  letter-spacing: .16em;
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

.gl-verdict {{
  max-width: var(--gl-measure);
  margin: 0 auto;
  border-top: 6px solid var(--gl-klister);
  background: var(--gl-carbon);
  color: var(--gl-white);
  padding: var(--gl-space-5);
}}
.gl-verdict-kicker {{ margin: 0 0 var(--gl-space-2); color: var(--gl-klister); font-family: var(--gl-font-data); font-size: .66rem; font-weight: 700; letter-spacing: .2em; text-transform: uppercase; }}
.gl-verdict-copy {{ max-width: var(--gl-prose); margin: 0; font-family: var(--gl-font-editorial); font-size: 1.08rem; line-height: 1.65; }}

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

.gl-rating-intro {{ max-width: var(--gl-prose); margin: 0 0 var(--gl-space-5); font-size: 1.05rem; line-height: 1.65; }}
.gl-rating-tablist {{ display: grid; grid-template-columns: 1fr 1fr; border: 3px solid var(--gl-carbon); }}
.gl-rating-tablist button {{
  min-height: 48px;
  border: 0;
  border-right: 3px solid var(--gl-carbon);
  background: var(--gl-white);
  color: var(--gl-carbon);
  padding: var(--gl-space-3) var(--gl-space-4);
  font-family: var(--gl-font-data);
  font-size: .7rem;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
  cursor: pointer;
}}
.gl-rating-tablist button:last-child {{ border-right: 0; }}
.gl-rating-tablist button[aria-selected="true"] {{ background: var(--gl-carbon); color: var(--gl-white); }}
.gl-rating-tablist button span {{ color: var(--gl-klister); }}
.gl-rating-panel {{ display: grid; grid-template-columns: minmax(300px, 1.05fr) minmax(280px, .95fr); grid-template-areas: "radar tiles" "radar detail"; border: 3px solid var(--gl-carbon); border-top: 0; }}
.gl-rating-panel[hidden] {{ display: none; }}
.gl-radar-chart {{ grid-area: radar; display: flex; align-items: center; border-right: 1px solid var(--gl-hairline); background: var(--gl-white); padding: var(--gl-space-3); }}
.gl-radar-svg {{ display: block; width: 100%; height: auto; }}
.gl-radar-grid {{ fill: none; stroke: var(--gl-hairline); stroke-width: 1; }}
.gl-radar-spoke {{ stroke: var(--gl-hairline); stroke-width: 1; }}
.gl-radar-spoke.is-active {{ stroke: var(--gl-swix-red); stroke-width: 2; }}
.gl-radar-polygon {{ fill: var(--gl-swix-red); fill-opacity: .18; stroke: var(--gl-swix-red); stroke-width: 3; }}
.gl-radar-hit {{ fill: transparent; cursor: pointer; }}
.gl-radar-hit:focus {{ outline: none; }}
.gl-radar-dot {{ fill: var(--gl-klister); stroke: var(--gl-carbon); stroke-width: 2; }}
.gl-radar-axis-label,
.gl-radar-axis-score,
.gl-radar-total,
.gl-radar-total-max {{ font-family: var(--gl-font-data); font-weight: 700; }}
.gl-radar-axis-label {{ fill: var(--gl-carbon); font-size: 9px; letter-spacing: .04em; }}
.gl-radar-axis-score {{ fill: var(--gl-swix-red); font-size: 10px; }}
.gl-radar-total {{ fill: var(--gl-swix-red); font-size: 24px; }}
.gl-radar-total-max {{ fill: var(--gl-muted); font-size: 9px; letter-spacing: .1em; }}
.gl-rating-tiles {{ grid-area: tiles; display: grid; grid-template-columns: 1fr 1fr; align-content: start; }}
.gl-rating-tile {{
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gl-space-3);
  border: 0;
  border-bottom: 1px solid var(--gl-hairline);
  border-right: 1px solid var(--gl-hairline);
  background: var(--gl-white);
  color: var(--gl-carbon);
  padding: var(--gl-space-3);
  text-align: left;
  cursor: pointer;
}}
.gl-rating-tile[aria-pressed="true"] {{ background: var(--gl-paper); box-shadow: inset 5px 0 0 var(--gl-swix-red); }}
.gl-rating-tile-label {{ font-family: var(--gl-font-data); font-size: .62rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }}
.gl-rating-tile-score {{ font-family: var(--gl-font-display); font-size: 1.35rem; font-style: italic; font-weight: 900; }}
.gl-rating-tile-score small {{ font-family: var(--gl-font-data); font-size: .58rem; }}
.gl-rating-explanation {{ grid-area: detail; align-self: stretch; border-top: 3px solid var(--gl-carbon); padding: var(--gl-space-4); }}
.gl-rating-explanation-head {{ display: flex; align-items: baseline; justify-content: space-between; gap: var(--gl-space-3); font-family: var(--gl-font-data); text-transform: uppercase; }}
.gl-rating-explanation-head span {{ color: var(--gl-swix-red); font-weight: 700; }}
.gl-rating-explanation p {{ margin: var(--gl-space-3) 0 0; line-height: 1.55; }}
.gl-breakdown-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); border: 3px solid var(--gl-carbon); }}
.gl-breakdown-tile {{ min-height: 118px; display: flex; flex-direction: column; justify-content: space-between; gap: var(--gl-space-4); border-right: 1px solid var(--gl-hairline); border-bottom: 1px solid var(--gl-hairline); background: var(--gl-white); color: var(--gl-carbon); padding: var(--gl-space-4); text-decoration: none; }}
.gl-breakdown-tile strong {{ font-family: var(--gl-font-display); font-style: italic; text-transform: uppercase; }}
.gl-breakdown-tile span {{ color: var(--gl-muted); font-size: .88rem; line-height: 1.45; }}
.gl-breakdown-tile:hover {{ background: var(--gl-paper); box-shadow: inset 0 -5px 0 var(--gl-klister); }}

.gl-transition {{ max-width: var(--gl-measure); margin: 0 auto; padding: var(--gl-space-7) var(--gl-space-5); background: var(--gl-swix-red); color: var(--gl-white); }}
.gl-transition-kicker {{ margin: 0 0 var(--gl-space-3); color: var(--gl-klister); font-family: var(--gl-font-data); font-size: .66rem; font-weight: 700; letter-spacing: .2em; text-transform: uppercase; }}
.gl-transition h2 {{ max-width: 20ch; margin: 0 0 var(--gl-space-4); font-family: var(--gl-font-display); font-size: clamp(2rem, 5vw, 3.8rem); font-style: italic; font-weight: 900; line-height: .98; text-transform: uppercase; }}
.gl-transition > p:last-child {{ max-width: var(--gl-prose); margin: 0; line-height: 1.6; }}
.gl-deep-dive {{ padding-top: var(--gl-space-5); }}
.gl-deep-dive::before {{ content: 'DEEP DIVE'; display: block; margin-bottom: var(--gl-space-2); color: var(--gl-muted); font-family: var(--gl-font-data); font-size: .64rem; font-weight: 700; letter-spacing: .2em; }}
.gl-related-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); border: 3px solid var(--gl-carbon); }}
.gl-related-card {{ min-height: 150px; display: flex; flex-direction: column; justify-content: space-between; gap: var(--gl-space-4); border-right: 1px solid var(--gl-hairline); background: var(--gl-white); padding: var(--gl-space-4); text-decoration: none; }}
.gl-related-card:last-child {{ border-right: 0; }}
.gl-related-card:hover {{ background: var(--gl-paper); box-shadow: inset 0 -5px 0 var(--gl-klister); }}
.gl-related-card strong {{ font-family: var(--gl-font-display); font-style: italic; text-transform: uppercase; }}
.gl-related-meta {{ color: var(--gl-muted); font-family: var(--gl-font-data); font-size: .66rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }}

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
.gl-wax-call h3 {{
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
.gl-wax-card-face p {{
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

.gl-wax-card-kicker {{
  font-family: var(--gl-font-data);
  font-size: .62rem;
  font-weight: 700;
  letter-spacing: .18em;
  text-transform: uppercase;
}}

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
  .gl-wax-cards {{ grid-template-columns: 1fr; }}
  .gl-rating-panel {{ grid-template-columns: 1fr; grid-template-areas: "radar" "tiles" "detail"; }}
  .gl-radar-chart {{ border-right: 0; border-bottom: 1px solid var(--gl-hairline); }}
  .gl-breakdown-grid {{ grid-template-columns: 1fr 1fr; }}
  .gl-related-grid {{ grid-template-columns: 1fr; }}
  .gl-related-card {{ min-height: 110px; border-right: 0; border-bottom: 1px solid var(--gl-hairline); }}
  .gl-sticky-cta-name {{ display: none; }}
  .gl-footer-inner {{ align-items: flex-start; flex-direction: column; }}
}}

@media (max-width: 460px) {{
  .gl-rating-tablist,
  .gl-rating-tiles,
  .gl-breakdown-grid {{ grid-template-columns: 1fr; }}
  .gl-rating-tablist button {{ border-right: 0; border-bottom: 3px solid var(--gl-carbon); }}
  .gl-rating-tablist button:last-child {{ border-bottom: 0; }}
}}
"""


# ── HTML Builders ──────────────────────────────────────────────

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
      <li class="gl-nav-item"><a href="/coaching/apply/"{_active("coaching")}>Coaching</a></li>
      <li class="gl-nav-item"><a href="/about/"{_active("about")}>About</a></li>
    </ul>
  </div>
</nav>
"""


def build_breadcrumb(race: dict) -> str:
    """Visible, crawlable race hierarchy with a JS-enhanced return target."""
    name = race.get("display_name", race.get("name", "Race"))
    return f"""
<nav class="gl-breadcrumb" aria-label="Breadcrumb">
  <a href="/">Home</a><span class="gl-breadcrumb-sep">&rsaquo;</span>
  <a href="/search/" id="gl-races-crumb">Races</a><span class="gl-breadcrumb-sep">&rsaquo;</span>
  <span class="gl-breadcrumb-current" aria-current="page">{esc(name)}</span>
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
        <span class="gl-scorebox-tier">{esc(tier_label(tier))}</span>
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
    if not wax:
        return ""
    return f"""
<section class="gl-section" id="race-week">
  {build_section_header('03', 'Race week')}
  <div class="gl-rise-grid">
    {build_race_week_stepper(race)}
    {wax}
  </div>
</section>
"""


def _criterion_explanation(race: dict, key: str, score: int) -> str:
    """Explain a stored score using only facts already present in the profile."""
    v = race.get("vitals", {})
    course = race.get("course", {})
    climate = race.get("climate", {})
    history = race.get("history", {})
    label = RATING_LABELS.get(key, key.replace("_", " ").title())
    context = ""
    if key == "distance" and v.get("distance_km") is not None:
        context = f" The primary distance is {format_distance(v['distance_km'])}."
    elif key == "elevation" and v.get("elevation_m") is not None:
        context = f" The profile lists {format_elevation(v['elevation_m'])} of elevation."
    elif key == "altitude" and v.get("altitude_m") is not None:
        context = f" The listed altitude is {format_altitude(v['altitude_m'])}."
    elif key in {"field_size", "competitive_depth"} and v.get("field_size"):
        context = f" The listed field size is {v['field_size']} skiers."
    elif key == "course_technicality" and course.get("technical_rating") is not None:
        context = f" The course profile lists technical difficulty at {course['technical_rating']} out of 5."
    elif key == "snow_reliability" and climate.get("typical_temp_c"):
        context = f" The typical race-day range is {climate['typical_temp_c']}°C."
    elif key == "grooming_quality" and course.get("grooming"):
        context = f" Grooming note: {course['grooming']}"
    elif key == "accessibility" and v.get("location_badge", v.get("location")):
        context = f" The race is listed in {v.get('location_badge', v.get('location'))}."
    elif key == "prestige" and v.get("founded"):
        context = f" The event was founded in {v['founded']}."
    elif key == "community" and history.get("notable_facts"):
        context = f" Profile note: {history['notable_facts'][0]}"
    return f"Wax Bench scores {label} {score} out of 5.{context}"


def _radar_svg(race: dict, group_id: str, label: str, keys: list[str]) -> str:
    """Render a complete SVG radar before JavaScript runs."""
    rating = race["nordic_lab_rating"]
    width, height = 440, 390
    cx, cy, radius = 220, 182, 104
    label_radius = radius + 34
    offset = -math.pi / 2
    count = len(keys)

    def point(index: int, distance: float) -> tuple[float, float]:
        angle = offset + index * 2 * math.pi / count
        return cx + distance * math.cos(angle), cy + distance * math.sin(angle)

    rings = []
    for level in range(1, 6):
        points = " ".join(
            f"{point(i, radius * level / 5)[0]:.1f},{point(i, radius * level / 5)[1]:.1f}"
            for i in range(count)
        )
        rings.append(f'<polygon points="{points}" class="gl-radar-grid"/>')

    scores = [max(0, min(5, _parse_score(rating.get(key)) or 0)) for key in keys]
    polygon = " ".join(
        f"{point(i, radius * score / 5)[0]:.1f},{point(i, radius * score / 5)[1]:.1f}"
        for i, score in enumerate(scores)
    )
    spokes = []
    points_html = []
    labels = []
    for index, (key, score) in enumerate(zip(keys, scores)):
        outer_x, outer_y = point(index, radius)
        dot_x, dot_y = point(index, radius * score / 5)
        label_x, label_y = point(index, label_radius)
        criterion = RATING_LABELS.get(key, key.replace("_", " ").title())
        anchor = "middle"
        if label_x < cx - 15:
            anchor = "end"
        elif label_x > cx + 15:
            anchor = "start"
        spokes.append(
            f'<line x1="{cx}" y1="{cy}" x2="{outer_x:.1f}" y2="{outer_y:.1f}" '
            f'class="gl-radar-spoke" data-rating-key="{esc(key)}"/>'
        )
        points_html.append(
            f'<circle cx="{dot_x:.1f}" cy="{dot_y:.1f}" r="14" class="gl-radar-hit" '
            f'data-rating-group="{esc(group_id)}" data-rating-key="{esc(key)}" tabindex="0" role="button" '
            f'aria-label="Explain {esc(criterion)}, scored {score} out of 5"/>'
            f'<circle cx="{dot_x:.1f}" cy="{dot_y:.1f}" r="5" class="gl-radar-dot" pointer-events="none"/>'
        )
        labels.append(
            f'<text x="{label_x:.1f}" y="{label_y - 5:.1f}" text-anchor="{anchor}" class="gl-radar-axis-label">'
            f'{esc(criterion.upper())}</text>'
            f'<text x="{label_x:.1f}" y="{label_y + 9:.1f}" text-anchor="{anchor}" class="gl-radar-axis-score">'
            f'{score}/5</text>'
        )

    total = sum(scores)
    title_id = f"gl-radar-{group_id}-title"
    return f"""
<div class="gl-radar-chart" data-rating-group="{esc(group_id)}">
  <svg viewBox="0 0 {width} {height}" class="gl-radar-svg" role="img" aria-labelledby="{title_id}">
    <title id="{title_id}">{esc(label)} ratings. Select a score point for its explanation.</title>
    {''.join(rings)}
    {''.join(spokes)}
    <polygon points="{polygon}" class="gl-radar-polygon"/>
    {''.join(points_html)}
    {''.join(labels)}
    <text x="{cx}" y="{cy - 4}" text-anchor="middle" class="gl-radar-total">{total}</text>
    <text x="{cx}" y="{cy + 12}" text-anchor="middle" class="gl-radar-total-max">/35</text>
  </svg>
</div>"""


def _rating_tiles(race: dict, group_id: str, keys: list[str]) -> str:
    rating = race["nordic_lab_rating"]
    tiles = []
    first_label = ""
    first_score = 0
    first_explanation = ""
    for index, key in enumerate(keys):
        score = max(0, min(5, _parse_score(rating.get(key)) or 0))
        label = RATING_LABELS.get(key, key.replace("_", " ").title())
        explanation = _criterion_explanation(race, key, score)
        if index == 0:
            first_label, first_score, first_explanation = label, score, explanation
        tiles.append(f"""
<button type="button" class="gl-rating-tile" data-rating-group="{esc(group_id)}" data-rating-key="{esc(key)}" aria-pressed="{'true' if index == 0 else 'false'}">
  <span class="gl-rating-tile-label">{esc(label)}</span>
  <span class="gl-rating-tile-score">{score}<small>/5</small></span>
  <span class="gl-rating-source" hidden>{esc(explanation)}</span>
</button>""")
    return f"""
<div class="gl-rating-tiles">{''.join(tiles)}</div>
<div class="gl-rating-explanation" id="gl-rating-detail-{esc(group_id)}" role="status" aria-live="polite">
  <div class="gl-rating-explanation-head"><strong>{esc(first_label)}</strong><span>{first_score}/5</span></div>
  <p>{esc(first_explanation)}</p>
</div>"""


def build_rating_breakdown(race: dict) -> str:
    """Interactive, accessible two-radar decision tool."""
    panels = []
    tabs = []
    rating = race["nordic_lab_rating"]
    for index, (group_id, label, keys) in enumerate(RATING_GROUPS):
        selected = index == 0
        total = sum(max(0, min(5, _parse_score(rating.get(key)) or 0)) for key in keys)
        tabs.append(
            f'<button type="button" id="gl-rating-tab-{group_id}" role="tab" '
            f'aria-selected="{str(selected).lower()}" aria-controls="gl-rating-panel-{group_id}" '
            f'tabindex="{0 if selected else -1}">{esc(label)} <span>{total}/35</span></button>'
        )
        panels.append(f"""
<div id="gl-rating-panel-{group_id}" class="gl-rating-panel" role="tabpanel" aria-labelledby="gl-rating-tab-{group_id}" data-rating-group="{group_id}"{' hidden' if not selected else ''}>
  {_radar_svg(race, group_id, label, keys)}
  {_rating_tiles(race, group_id, keys)}
</div>""")

    return f"""
<section class="gl-section gl-rating-section" id="rating" data-measure-section="rating">
  {build_section_header('01', 'The Wax Bench rating')}
  <p class="gl-rating-intro">Two views of the same race: what the course demands, and what the event delivers. Select any criterion for the profile evidence.</p>
  <div class="gl-rating-tablist" role="tablist" aria-label="Rating categories">{''.join(tabs)}</div>
  {''.join(panels)}
</section>
"""


def build_breakdown_tiles(race: dict) -> str:
    """Compact map from the decision tool to the available deep-dive evidence."""
    candidates = [
        ("vitals", "Race vitals", "Distance, date, field, and format", bool(race.get("vitals"))),
        ("course", "Course", "Terrain, grooming, and technical demands", bool(race.get("course"))),
        (
            "race-week",
            "Race week",
            "Technique, wax, and start-line protocol",
            parse_temperature_range(race.get("climate", {}).get("typical_temp_c")) is not None,
        ),
        ("climate", "Conditions", "Temperature and snow variables", bool(race.get("climate"))),
        ("history", "Heritage", "Why this race matters", bool(race.get("history"))),
        ("series", "Series", "Championship and circuit context", bool(race.get("series_membership"))),
    ]
    tiles = "".join(
        f'<a class="gl-breakdown-tile" href="#{anchor}"><strong>{esc(title)}</strong><span>{esc(body)}</span></a>'
        for anchor, title, body, active in candidates if active
    )
    return f"""
<section class="gl-section" id="breakdown" data-measure-section="breakdown">
  {build_section_header('02', 'What the score means')}
  <div class="gl-breakdown-grid">{tiles}</div>
</section>"""


def build_transition_callout(race: dict) -> str:
    name = esc(race.get("display_name", race.get("name", "this race")))
    return f"""
<section class="gl-transition" aria-labelledby="gl-transition-title" data-measure-section="transition">
  <p class="gl-transition-kicker">Rating into action</p>
  <h2 id="gl-transition-title">A score tells you what {name} demands. A plan prepares you for it.</h2>
  <p>Use the profile below for the race facts. Use a custom plan when you want those demands translated into your available weeks, hours, and ski background.</p>
</section>"""


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


def build_verdict(race: dict) -> str:
    """Use the existing editor-authored score note as the compact verdict."""
    note = race.get("nordic_lab_rating", {}).get("score_note", "")
    if not note:
        return ""
    return f"""
<section class="gl-verdict" id="verdict" data-measure-section="verdict">
  <p class="gl-verdict-kicker">Lab verdict</p>
  <p class="gl-verdict-copy">{esc(note)}</p>
</section>
"""


def load_race_index() -> list[dict]:
    """Load the compact race index used by search and internal linking."""
    if not DEFAULT_INDEX_PATH.exists():
        return []
    try:
        payload = json.loads(DEFAULT_INDEX_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return payload.get("races", []) if isinstance(payload, dict) else []


def build_related_races(race: dict, race_index: list[dict]) -> str:
    """Three evidence-based next-race links, biased to country and technique."""
    slug = race.get("slug", "")
    vitals = race.get("vitals", {})
    rating = race.get("nordic_lab_rating", {})
    country = vitals.get("country_code", "")
    discipline = rating.get("discipline", vitals.get("discipline", ""))
    score = rating.get("overall_score", 0) or 0

    candidates = [entry for entry in race_index if entry.get("s") != slug]
    candidates.sort(key=lambda entry: (
        entry.get("cc") == country,
        entry.get("di") == discipline,
        -abs((entry.get("sc") or 0) - score),
    ), reverse=True)
    selected = candidates[:3]
    if not selected:
        return ""

    cards = []
    for entry in selected:
        name = entry.get("dn") or entry.get("n") or entry.get("s", "Race")
        meta = " · ".join(filter(None, [
            f"T{entry.get('t')}" if entry.get("t") else "",
            entry.get("co", ""),
            DISCIPLINE_LABELS.get(entry.get("di"), entry.get("di", "")),
        ]))
        cards.append(
            f'<a class="gl-related-card" href="/race/{esc(entry.get("s", ""))}/" '
            f'data-related-race="{esc(entry.get("s", ""))}">'
            f'<strong>{esc(name)}</strong><span class="gl-related-meta">{esc(meta)}</span></a>'
        )
    return f"""
<section class="gl-section" id="related">
  {build_section_header('08', 'Keep exploring')}
  <div class="gl-related-grid">{''.join(cards)}</div>
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
    """Custom-first offer, followed by the higher-touch coaching path."""
    slug = esc(race["slug"])
    rungs = [
        ("Built for your race", "Custom plan", "Your race, your weeks, your available hours, and your ski background — built from the intake.", "$60-$249", f"/questionnaire/?race={slug}", "Start the intake", True, False),
        ("Higher touch", "1:1 coaching", "A coach reads your training and adjusts the plan as conditions, recovery, and life change.", "$199-$1,200 / 4 WK", "/coaching/apply/", "Apply for coaching", False, False),
        ("Free reference", "Race prep guide", "Technique, pacing, fueling, and wax fundamentals to use while you evaluate your next step.", "FREE", "/guide/", "Read the guide", False, False),
    ]
    learn_path = DEFAULT_OUTPUT_DIR / "learn" / "index.html"
    if learn_path.exists():
        rungs.append(("Learn", "XC ski course", "Self-paced lessons from first glide to race preparation.", "SELF-PACED", "/learn/", "See the course", False, True))

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
      <a class="{btn_class}" href="{href}" data-cta="{'custom_plan' if primary else 'coaching' if title == '1:1 coaching' else 'guide'}"{rel}>{esc(label)}</a>
    </div>""")

    return f"""
<section class="gl-ladder" id="training" data-measure-section="offer">
  <div class="gl-ladder-inner">
    <h2>Built for your start line</h2>
    <p class="gl-ladder-lead">Start with a plan shaped around this race. Move up to coaching when you want ongoing judgment and adjustment.</p>
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
      <a href="/questionnaire/?race={slug}" class="gl-sticky-cta-btn" id="gl-sticky-cta-link" data-cta="custom_plan_sticky">
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
  var raceSlug = document.body.getAttribute('data-race-slug') || '';
  var pageFormat = document.body.getAttribute('data-page-format') || '';
  function track(eventName, params) {
    if (typeof gtag !== 'function') { return; }
    params = params || {};
    params.race_slug = raceSlug;
    params.page_format = pageFormat;
    gtag('event', eventName, params);
  }

  var racesCrumb = document.getElementById('gl-races-crumb');
  if (racesCrumb && document.referrer) {
    try {
      var referrer = new URL(document.referrer);
      if (referrer.origin === window.location.origin && referrer.pathname === '/search/') {
        racesCrumb.href = referrer.pathname + referrer.search;
        racesCrumb.textContent = 'Back to results';
      }
    } catch(e) {}
  }

  var navToggle = document.querySelector('[data-nav-toggle]');
  var navLinks = document.querySelector('.gl-nav-links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', function() {
      var open = navLinks.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }

  var ratingTabs = Array.prototype.slice.call(document.querySelectorAll('.gl-rating-tablist [role="tab"]'));
  function activateRatingTab(tab, focus) {
    ratingTabs.forEach(function(item) {
      var selected = item === tab;
      item.setAttribute('aria-selected', selected ? 'true' : 'false');
      item.setAttribute('tabindex', selected ? '0' : '-1');
      var panel = document.getElementById(item.getAttribute('aria-controls'));
      if (panel) { panel.hidden = !selected; }
    });
    if (focus) { tab.focus(); }
    track('rating_tab_click', {rating_group: tab.id.replace('gl-rating-tab-', '')});
  }
  ratingTabs.forEach(function(tab, index) {
    tab.addEventListener('click', function() { activateRatingTab(tab, false); });
    tab.addEventListener('keydown', function(event) {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') { return; }
      event.preventDefault();
      var step = event.key === 'ArrowRight' ? 1 : -1;
      activateRatingTab(ratingTabs[(index + step + ratingTabs.length) % ratingTabs.length], true);
    });
  });

  function activateCriterion(group, key, trackEvent) {
    var panel = document.querySelector('.gl-rating-panel[data-rating-group="' + group + '"]');
    if (!panel) { return; }
    var selected = panel.querySelector('.gl-rating-tile[data-rating-key="' + key + '"]');
    if (!selected) { return; }
    panel.querySelectorAll('.gl-rating-tile').forEach(function(tile) {
      tile.setAttribute('aria-pressed', tile === selected ? 'true' : 'false');
    });
    panel.querySelectorAll('.gl-radar-spoke').forEach(function(spoke) {
      spoke.classList.toggle('is-active', spoke.getAttribute('data-rating-key') === key);
    });
    var detail = document.getElementById('gl-rating-detail-' + group);
    if (detail) {
      var label = selected.querySelector('.gl-rating-tile-label');
      var score = selected.querySelector('.gl-rating-tile-score');
      var source = selected.querySelector('.gl-rating-source');
      var detailLabel = detail.querySelector('strong');
      var detailScore = detail.querySelector('.gl-rating-explanation-head span');
      var detailCopy = detail.querySelector('p');
      if (label && detailLabel) { detailLabel.textContent = label.textContent; }
      if (score && detailScore) { detailScore.textContent = score.textContent; }
      if (source && detailCopy) { detailCopy.textContent = source.textContent; }
    }
    if (trackEvent) { track('rating_criterion_click', {rating_group: group, rating_criterion: key}); }
  }
  document.querySelectorAll('.gl-rating-tile, .gl-radar-hit').forEach(function(control) {
    function select() {
      activateCriterion(control.getAttribute('data-rating-group'), control.getAttribute('data-rating-key'), true);
    }
    control.addEventListener('click', select);
    if (control.classList.contains('gl-radar-hit')) {
      control.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(); }
      });
    }
  });

  document.querySelectorAll('a[data-cta]').forEach(function(link) {
    link.addEventListener('click', function() {
      track('cta_click', {
        cta_type: link.getAttribute('data-cta') || 'other',
        cta_destination: link.getAttribute('href') || ''
      });
    });
  });

  document.querySelectorAll('a[data-related-race]').forEach(function(link) {
    link.addEventListener('click', function() {
      track('related_race_click', {related_race_slug: link.getAttribute('data-related-race') || ''});
    });
  });

  if ('IntersectionObserver' in window) {
    var seenSections = {};
    var sectionObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (!entry.isIntersecting) { return; }
        var section = entry.target.getAttribute('data-measure-section') || ('deep_' + (entry.target.id || 'section'));
        if (!section || seenSections[section]) { return; }
        seenSections[section] = true;
        track('race_section_view', {section_name: section});
        sectionObserver.unobserve(entry.target);
      });
    }, {threshold: 0.35});
    document.querySelectorAll('[data-measure-section], .gl-deep-dive > section[id]').forEach(function(section) {
      sectionObserver.observe(section);
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

    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://xcskilabs.com/"},
            {"@type": "ListItem", "position": 2, "name": "Races", "item": "https://xcskilabs.com/search/"},
            {"@type": "ListItem", "position": 3, "name": race["name"], "item": f"https://xcskilabs.com/race/{race['slug']}/"},
        ],
    }

    return (
        '<script type="application/ld+json">'
        + _safe_json_for_script(event, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
        + '<script type="application/ld+json">'
        + _safe_json_for_script(breadcrumb, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
    )


# ── Page Assembly ──────────────────────────────────────────────

def generate_page(race: dict, race_index: Optional[list[dict]] = None) -> str:
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
    breadcrumb = build_breadcrumb(race)
    hero = build_hero(race)
    verdict = build_verdict(race)
    vitals = build_at_a_glance(race)
    course = build_course(race)
    interactive = build_interactive_blocks(race)
    climate = build_climate(race)
    rating = build_rating_breakdown(race)
    breakdown = build_breakdown_tiles(race)
    transition = build_transition_callout(race)
    wax_bar = build_wax_bar(race)
    ladder = build_product_ladder(race)
    history = build_history(race)
    series = build_series(race)
    related = build_related_races(race, race_index if race_index is not None else load_race_index())
    sticky_cta = build_sticky_cta(race)
    interactions_js = build_interactions_js()
    sticky_js = build_sticky_js()
    cookie_consent = build_cookie_consent()
    footer = build_footer(race)

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
<body data-race-slug="{esc(slug)}" data-page-format="spine-v2">
<a href="#course" class="gl-skip-link">Skip to content</a>
{nav_header}
{breadcrumb}
<div class="gl-page">
{hero}
{wax_bar}
{verdict}
<div class="gl-wrap">
{rating}
{breakdown}
</div>
{transition}
</div>
{ladder}
<div class="gl-page">
<div class="gl-wrap gl-deep-dive" id="deep-dive" data-measure-section="deep-dive">
{vitals}
{course}
{interactive}
{climate}
{history}
{series}
{related}
</div>
{footer}
</div>
{sticky_cta}
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
    race_index = load_race_index()

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

        page_html = generate_page(race, race_index)

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
