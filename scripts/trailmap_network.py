#!/usr/bin/env python3
"""
XC Ski Labs -- trail-network drawing of the race database.

Draws the corpus the way the Devil's Thumb Ranch sheet draws a trail system:
each race series is a marked trail, each race is a node on it, a race in two
series is a junction, and races in no series are ungroomed snow.

Every coordinate is derived from race-data/*.json. Nothing here is decorative:
  node glyph  <- course.technical_rating   (circle / square / diamond / double)
  node fill   <- nordic_lab_rating.tier    (filled = tier one)
  trail       <- series_membership
  junction    <- a race carrying two memberships
  ungroomed   <- a race carrying none

Usage:
    python trailmap_network.py                    # SVG fragment to stdout
    python trailmap_network.py --out network.svg
"""

import argparse
import glob
import json
import math
import random
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR.parent / "race-data"

CANVAS_W, CANVAS_H = 1240, 730
UNGROOMED_SEED = 4

# Trail anchors are hand-set the way a trail system is: irregular lobes, no two
# alike. Regular geometry (a true circle, a clean sine) reads as a diagram and
# kills the whole conceit, so resist tidying these.
TRAILS: list[dict[str, Any]] = [
    dict(key="worldloppet", label="Worldloppet", hand=True, closed=True, major=True,
         pts=[(96, 318), (120, 230), (188, 164), (270, 126), (350, 148), (404, 198),
              (466, 166), (534, 194), (576, 266), (544, 336), (588, 404), (542, 472),
              (450, 510), (358, 484), (288, 518), (202, 492), (138, 430), (110, 370)]),
    dict(key="ski_classics_challengers", label="Ski Classics Challengers", hand=True, closed=False, major=True,
         pts=[(66, 648), (128, 700), (206, 614), (258, 670), (340, 588), (430, 662),
              (486, 612), (566, 684), (654, 604), (700, 650), (778, 590), (860, 670),
              (918, 612), (996, 678), (1074, 596), (1132, 648), (1188, 602)]),
    dict(key="euroloppet", label="Euroloppet", hand=True, closed=False, major=False,
         pts=[(650, 364), (694, 294), (762, 334), (838, 264), (882, 332), (948, 284),
              (988, 346), (1054, 298), (1102, 354), (1160, 310)]),
    dict(key="ski_classics_pro_tour", label="Ski Classics Pro Tour", hand=True, closed=False, major=False,
         pts=[(790, 198), (850, 132), (922, 162), (976, 104), (1036, 144)]),
    dict(key="russialoppet", label="Russialoppet", hand=False, closed=False, major=False,
         pts=[(1098, 262), (1152, 208), (1118, 152), (1170, 98), (1136, 44)]),
    dict(key="swiss_loppet", label="Swiss Loppet", hand=False, closed=True, major=False,
         pts=[(660, 452), (716, 422), (766, 456), (752, 510), (690, 522), (642, 492)]),
    dict(key="estoloppet", label="Estoloppet", hand=False, closed=True, major=False,
         pts=[(486, 56), (546, 32), (602, 62), (582, 110), (520, 116)]),
    dict(key="marathon_ski_tour", label="Marathon Ski Tour", hand=False, closed=False, major=False,
         pts=[(206, 500), (154, 532), (184, 572), (132, 606), (160, 644)]),
]

# Empty pockets of the sheet, where untracked snow goes.
POCKETS = [(936, 388, 272, 176), (74, 40, 246, 110), (210, 548, 200, 40), (624, 556, 236, 32)]
NOTE_BOX = (928, 572, 1214, 618)

GLYPH_FOR_TECH = {1: "circle", 2: "circle", 3: "square", 4: "diamond", 5: "dbldiamond"}


def esc(text: Any) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def load_races(data_dir: Path) -> dict[str, dict]:
    races: dict[str, dict] = {}
    for path in sorted(glob.glob(str(data_dir / "*.json"))):
        if "_schema" in path:
            continue
        race = json.loads(Path(path).read_text(encoding="utf-8"))["race"]
        vitals = race.get("vitals") or {}
        rating = race.get("nordic_lab_rating") or {}
        course = race.get("course") or {}
        series = race.get("series_membership") or []
        if isinstance(series, dict):
            series = [k for k, v in series.items() if v]
        races[race["slug"]] = dict(
            slug=race["slug"], name=race.get("display_name") or race["name"],
            country=vitals.get("country") or "", km=vitals.get("distance_km"),
            disc=vitals.get("discipline") or "", score=rating.get("overall_score") or 0,
            tier=rating.get("tier") or 4, tech=course.get("technical_rating"),
            series=series)
    return races


def catmull(pts, closed=False, samples=340):
    """Catmull-Rom spline through pts -> (path d, evenly sampled points)."""
    p = [pts[-1], *pts, pts[0], pts[1]] if closed else [pts[0], *pts, pts[-1]]
    d = f"M{p[1][0]:.1f} {p[1][1]:.1f}"
    out = []
    segments = len(p) - 3
    for i in range(segments):
        p0, p1, p2, p3 = p[i], p[i + 1], p[i + 2], p[i + 3]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
        steps = max(3, samples // segments)
        for s in range(steps):
            t = s / steps
            mt = 1 - t
            out.append((mt ** 3 * p1[0] + 3 * mt * mt * t * c1[0] + 3 * mt * t * t * c2[0] + t ** 3 * p2[0],
                        mt ** 3 * p1[1] + 3 * mt * mt * t * c1[1] + 3 * mt * t * t * c2[1] + t ** 3 * p2[1]))
    out.append(p[-2])
    return d + (" Z" if closed else ""), out


def build_network_svg(races: dict[str, dict], href: str = "/{slug}/") -> str:
    placed: dict[str, tuple[float, float]] = {}
    paths: list[str] = []
    nodes: list[str] = []
    labels: list[str] = []
    leaders: list[str] = []
    boxes: list[tuple[float, float, float, float]] = []
    all_points: list[tuple[float, float]] = []
    geo: dict[str, tuple[str, list]] = {}

    for trail in TRAILS:
        d, samples = catmull(trail["pts"], trail["closed"])
        geo[trail["key"]] = (d, samples)
        all_points += samples[::3]

    def collides(box) -> bool:
        x0, y0, x1, y1 = box
        for c in boxes:
            if x0 < c[2] + 4 and c[0] < x1 + 4 and y0 < c[3] + 4 and c[1] < y1 + 4:
                return True
        return any(x0 - 4 < px < x1 + 4 and y0 - 4 < py < y1 + 4 for px, py in all_points)

    for trail in TRAILS:
        d, samples = geo[trail["key"]]
        cx = sum(p[0] for p in trail["pts"]) / len(trail["pts"])
        cy = sum(p[1] for p in trail["pts"]) / len(trail["pts"])
        members = sorted((r for r in races.values() if trail["key"] in r["series"]),
                         key=lambda r: -r["score"])
        paths.append(f'<path class="nw-path{" nw-path--major" if trail["major"] else ""}" d="{d}"/>')
        label_index = 0

        for i, race in enumerate(members):
            t = 0.03 + 0.94 * (i / (len(members) - 1) if len(members) > 1 else 0.5)
            x, y = samples[min(len(samples) - 1, int(t * (len(samples) - 1)))]

            if race["slug"] in placed:
                px, py = placed[race["slug"]]
                paths.append(f'<path class="nw-junction" d="M{px:.1f} {py:.1f} L{x:.1f} {y:.1f}"/>')
                nodes.append(f'<circle class="nw-junction-ring" cx="{px:.1f}" cy="{py:.1f}" r="11.5"/>')
                continue

            placed[race["slug"]] = (x, y)
            # An unrated course gets the dashed "unverified" node, never a guessed glyph.
            glyph = GLYPH_FOR_TECH.get(race["tech"] or 0)
            width = 20 if glyph == "dbldiamond" else 13
            view = 30 if glyph == "dbldiamond" else 20
            mark = (f'<svg class="nw-g" x="{-width / 2:.1f}" y="-6.5" width="{width}" height="13" '
                    f'viewBox="0 0 {view} 20"><use href="#g-{glyph}"/></svg>'
                    if glyph else '<circle class="nw-unrated" r="6"/>')
            nodes.append(
                f'<a class="nw-node nw-t{race["tier"]}" href="{esc(href.format(slug=race["slug"]))}" '
                f'data-n="{esc(race["name"])}" data-c="{esc(race["country"])}" data-k="{race["km"]}" '
                f'data-s="{race["score"]}" data-t="{race["tier"]}" data-x="{race["tech"] or 0}" '
                f'data-d="{esc(race["disc"])}" data-sr="{esc(trail["label"])}" '
                f'transform="translate({x:.1f} {y:.1f})">'
                f'<title>{esc(race["name"])} &#8212; {race["score"]}</title>'
                f'<circle class="nw-hit" r="15"/>{mark}</a>')

            if race["tier"] == 1:
                vx, vy = x - cx, y - cy
                mag = math.hypot(vx, vy) or 1
                vx, vy = vx / mag, vy / mag
                # Fan consecutive labels off the outward normal so neighbours can't stack.
                angle = (label_index % 3 - 1) * 0.46
                ca, sa = math.cos(angle), math.sin(angle)
                nx, ny = vx * ca - vy * sa, vx * sa + vy * ca
                reach = 30 + (label_index % 2) * 26
                label_index += 1
                lx, ly = x + nx * reach, y + ny * reach
                anchor = "end" if nx < -0.25 else ("start" if nx > 0.25 else "middle")
                tw = len(race["name"]) * 6.4
                if anchor == "end" and lx - tw < 10:
                    anchor, lx = "start", max(lx, 10)
                if anchor == "start" and lx + tw > CANVAS_W - 10:
                    anchor, lx = "end", min(lx, CANVAS_W - 10)
                if anchor == "middle":
                    lx = min(max(lx, tw / 2 + 8), CANVAS_W - tw / 2 - 8)
                ly = min(max(ly, 16), CANVAS_H - 10)
                leaders.append(f'<path class="nw-leader" d="M{x + nx * 10:.1f} {y + ny * 10:.1f} '
                               f'L{x + nx * (reach - 4):.1f} {y + ny * (reach - 4):.1f}"/>')
                dx = 5 if anchor == "start" else (-5 if anchor == "end" else 0)
                labels.append(f'<text class="nw-name" x="{lx + dx:.1f}" y="{ly + 3:.1f}" '
                              f'text-anchor="{anchor}">{esc(race["name"])}</text>')
                x0 = lx - tw if anchor == "end" else (lx if anchor == "start" else lx - tw / 2)
                boxes.append((x0 - 6, ly - 11, x0 + tw + 6, ly + 7))

    grand = sorted((r for r in races.values()
                    if "ski_classics_grand_classic" in r["series"] and r["slug"] in placed),
                   key=lambda r: -r["score"])
    if len(grand) > 1:
        d, _ = catmull([placed[r["slug"]] for r in grand])
        paths.append(f'<path class="nw-grand" d="{d}"/>')

    # Trail names sit off the line, on the side away from the trail's own centre,
    # at the first sampled point where the label box is genuinely clear.
    for trail in TRAILS:
        _, samples = geo[trail["key"]]
        cx = sum(p[0] for p in trail["pts"]) / len(trail["pts"])
        cy = sum(p[1] for p in trail["pts"]) / len(trail["pts"])
        tw = len(trail["label"]) * (8.6 if trail["hand"] else 7.6)
        best = None
        for step in range(2, 39):
            idx = int(len(samples) * step / 40)
            x, y = samples[idx]
            j, k = min(len(samples) - 1, idx + 6), max(0, idx - 6)
            tx, ty = samples[j][0] - samples[k][0], samples[j][1] - samples[k][1]
            mag = math.hypot(tx, ty) or 1
            nx, ny = -ty / mag, tx / mag
            if nx * (x - cx) + ny * (y - cy) < 0:
                nx, ny = -nx, -ny
            for offset in (24, 34, 46):
                lx = min(max(x + nx * offset, tw / 2 + 10), CANVAS_W - tw / 2 - 10)
                ly = min(max(y + ny * offset, 20), CANVAS_H - 14)
                box = (lx - tw / 2 - 6, ly - 13, lx + tw / 2 + 6, ly + 7)
                if not collides(box):
                    best = (lx, ly, box)
                    break
            if best:
                break
        if not best:
            x, y = samples[len(samples) // 2]
            lx = min(max(x, tw / 2 + 10), CANVAS_W - tw / 2 - 10)
            ly = max(y - 30, 20)
            best = (lx, ly, (lx - tw / 2 - 6, ly - 13, lx + tw / 2 + 6, ly + 7))
        lx, ly, box = best
        boxes.append(box)
        cls = "nw-trailname" + (" nw-trailname--hand" if trail["hand"] else "")
        labels.append(f'<text class="{cls}" x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle">'
                      f'{esc(trail["label"])}</text>')

    boxes.append(NOTE_BOX)
    ungroomed = [r for r in races.values() if not r["series"]]
    rng = random.Random(UNGROOMED_SEED)

    def is_clear(px, py) -> bool:
        if any(x0 - 3 < px < x1 + 3 and y0 - 3 < py < y1 + 3 for x0, y0, x1, y1 in boxes):
            return False
        return not any(abs(qx - px) < 7 and abs(qy - py) < 7 for qx, qy in all_points)

    ticks: list[str] = []
    pocket_i = guard = 0
    while len(ticks) < len(ungroomed) and guard < 40000:
        guard += 1
        zx, zy, zw, zh = POCKETS[pocket_i % len(POCKETS)]
        px, py = zx + rng.random() * zw, zy + rng.random() * zh
        if not is_clear(px, py):
            continue
        a = rng.uniform(-0.55, 0.55)
        ticks.append(f'<path class="nw-un" d="M{px:.1f} {py:.1f} '
                     f'l{4.4 * math.cos(a):.1f} {4.4 * math.sin(a):.1f}"/>')
        pocket_i += 1

    return "\n".join([
        '<g class="nw-trails">' + "".join(paths) + "</g>",
        '<g class="nw-ungroomed">' + "".join(ticks) + "</g>",
        f'<text class="nw-note" x="1071" y="590">{len(ungroomed)} races off the marked trails</text>',
        '<text class="nw-note nw-note--sub" x="1071" y="608">'
        'ungroomed &#183; no series, still scored</text>',
        '<g class="nw-leaders">' + "".join(leaders) + "</g>",
        '<g class="nw-nodes">' + "".join(nodes) + "</g>",
        '<g class="nw-labels">' + "".join(labels) + "</g>",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--href", default="/{slug}/", help="node link template")
    args = parser.parse_args()

    svg = build_network_svg(load_races(args.data_dir), href=args.href)
    if args.out:
        args.out.write_text(svg, encoding="utf-8")
        print(f"wrote {args.out} ({len(svg):,} bytes)")
    else:
        print(svg)


if __name__ == "__main__":
    main()
