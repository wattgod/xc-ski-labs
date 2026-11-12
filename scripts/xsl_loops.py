"""Technique loops: Gravel God skiing each classic technique, printed like a 1970s Nordic race poster.

The motion is motion-captured from Matti's own XC Ski Labs course videos and rendered by
wattgod/gravel-god-character (`rig/print_loops.py`). The files live in web/media/loops/ and deploy to
/media/loops/ (scripts/deploy.py --sync-media). Each loop is a whole number of technique cycles, so it repeats
seamlessly.

  from xsl_loops import loop_figure, LOOP_CSS, LOOP_JS
  loop_figure('diagonal', 'square')          # <figure> with a lazy, muted, looping video + caption

Behaviour (LOOP_JS): nothing downloads until the figure scrolls near the viewport; it plays only while visible;
with prefers-reduced-motion the poster frame stays and the video never loads.
"""
from __future__ import annotations

import html
from pathlib import Path

MEDIA_URL = "/media/loops"
MEDIA_DIR = Path(__file__).resolve().parent.parent / "web" / "media" / "loops"
SIZES = {"wide": (1280, 720), "square": (900, 900)}

# technique -> (name, gear / role, cycle seconds). Names and gear labels match the guide's "Classic gears".
LOOPS = {
    "diagonal": ("Diagonal stride", "Climbing gear", 1.26),
    "kickdp": ("Kick double-pole", "Rolling gear", 1.38),
    "doublepole": ("Double-pole", "Speed gear", 2.04),
    "klaebo": ("Klaebo step", "Steep, short climbs", 1.50),
    "herringbone": ("Herringbone", "Too steep to stride", 3.75),
    "nopoles": ("No-poles drill", "Diagonal stride drill", 1.12),
    "singlestick": ("Single-stick drill", "Diagonal stride drill", 1.22),
    "frozendp": ("Frozen double-pole drill", "Double-pole drill", 1.09),
}

# race discipline -> the loop that fits it (skate has no captured technique yet)
DISCIPLINE_LOOP = {"classic": "diagonal", "both": "kickdp"}


def copy_media(output_dir: Path) -> int:
    """Copy the loop media into output/media/loops/ (for local preview; deploy uploads web/media/loops/)."""
    import shutil
    dest = Path(output_dir) / "media" / "loops"
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    for f in sorted(MEDIA_DIR.glob("*")):
        if f.suffix in (".mp4", ".jpg"):
            shutil.copy2(f, dest / f.name); n += 1
    return n


def media_files(tech: str, shape: str) -> tuple[Path, Path]:
    return MEDIA_DIR / f"{tech}_{shape}.mp4", MEDIA_DIR / f"{tech}_{shape}.jpg"


def loop_figure(tech: str, shape: str = "wide", caption: bool = True, extra_class: str = "") -> str:
    """One technique loop. The video is decorative (aria-hidden); the caption carries the technique name."""
    name, gear, cycle = LOOPS[tech]
    w, h = SIZES[shape]
    stem = f"{MEDIA_URL}/{tech}_{shape}"
    cap = (f'<figcaption class="xsl-loop-cap"><span class="xsl-loop-name">{html.escape(name)}</span>'
           f'<span class="xsl-loop-meta">{html.escape(gear)} &middot; {cycle:.2f} s cycle</span></figcaption>'
           if caption else "")
    cls = f"xsl-loop xsl-loop--{shape}" + (f" {extra_class}" if extra_class else "")
    return (f'<figure class="{cls}" data-xsl-loop>'
            f'<div class="xsl-loop-frame"><video class="xsl-loop-video" muted loop playsinline preload="none" '
            f'poster="{stem}.jpg" data-src="{stem}.mp4" width="{w}" height="{h}" aria-hidden="true"></video></div>'
            f'{cap}</figure>')


LOOP_CSS = """
/* Technique loops: a printed frame with the rust plate set off register behind it, like the loops themselves */
.xsl-loop { margin: 0; display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.xsl-loop-frame { position: relative; border: 3px solid var(--gl-ink); background: var(--gl-paper); isolation: isolate; }
.xsl-loop-frame::before { content: ""; position: absolute; inset: 0; transform: translate(7px, 7px); background: var(--gl-rust); z-index: -1; }
.xsl-loop-video { display: block; width: 100%; height: auto; background: var(--gl-paper); }
.xsl-loop--wide .xsl-loop-video { aspect-ratio: 16 / 9; }
.xsl-loop--square .xsl-loop-video { aspect-ratio: 1 / 1; }
.xsl-loop-cap { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 2px 12px; padding-top: 4px;
  font-family: var(--gl-font-data); font-size: 12px; letter-spacing: .08em; text-transform: uppercase; }
.xsl-loop-name { font-weight: 700; color: var(--gl-ink); }
.xsl-loop-meta { color: var(--gl-caption); font-variant-numeric: tabular-nums; }
.xsl-loop-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr)); gap: 28px 24px; }
@media (prefers-reduced-motion: reduce) { .xsl-loop-frame::before { transform: translate(5px, 5px); } }
"""

LOOP_JS = """
<script>
(function () {
  var figs = document.querySelectorAll('[data-xsl-loop] video[data-src]');
  if (!figs.length) return;
  var mq = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  if (mq && mq.matches) return;             // keep the poster frame; never download or play
  if (mq && mq.addEventListener) {          // turned on mid-visit: stop every loop where it is
    mq.addEventListener('change', function (e) {
      if (e.matches) { figs.forEach(function (v) { v.pause(); v.removeAttribute('autoplay'); }); if (io) io.disconnect(); }
    });
  }
  var io = null;
  function start(v) {
    if (!v.getAttribute('src')) { v.setAttribute('src', v.getAttribute('data-src')); }
    var p = v.play(); if (p && p.catch) { p.catch(function () {}); }
  }
  if (!('IntersectionObserver' in window)) { figs.forEach(start); return; }
  io = new IntersectionObserver(function (entries) {
    if (!entries || !entries.length) return;
    entries.forEach(function (e) {
      var v = e.target;
      window.requestAnimationFrame(function () {
        if (mq && mq.matches) { v.pause(); return; }
        if (e.isIntersecting) { start(v); } else if (v.getAttribute('src')) { v.pause(); }
      });
    });
  }, { rootMargin: '200px 0px', threshold: 0.15 });
  figs.forEach(function (v) { io.observe(v); });
})();
</script>
"""


def loops_band(heading: str, lead: str, techs: list[str], link_href: str, link_label: str, band_id: str = "motion") -> str:
    """A full-width band of square loops under a heading, with one link onward."""
    figs = "".join(loop_figure(t, "square") for t in techs)
    return f"""
<section class="xsl-motion" id="{band_id}" aria-labelledby="{band_id}-title">
  <div class="xsl-motion-inner">
    <h2 class="xsl-motion-title" id="{band_id}-title">{html.escape(heading)}</h2>
    <p class="xsl-motion-lead">{html.escape(lead)}</p>
    <div class="xsl-loop-grid">{figs}</div>
    <a class="xsl-motion-link" href="{link_href}">{html.escape(link_label)} &rarr;</a>
  </div>
</section>
"""


BAND_CSS = """
.xsl-motion { background: var(--gl-paper); border-top: 3px solid var(--gl-ink); border-bottom: 3px solid var(--gl-ink); }
.xsl-motion-inner { max-width: var(--gl-measure); margin: 0 auto; padding: 56px 20px 60px; display: flex; flex-direction: column; gap: 18px; }
.xsl-motion-title { margin: 0; font-family: var(--gl-font-display); font-weight: 900; font-stretch: condensed;
  font-size: clamp(30px, 5vw, 48px); line-height: 1; letter-spacing: -.02em; text-transform: uppercase; color: var(--gl-ink); text-wrap: balance; }
.xsl-motion-lead { margin: 0 0 8px; max-width: 60ch; font-family: var(--gl-font-editorial); font-size: 18px; color: var(--gl-ink); }
.xsl-motion-link { align-self: flex-start; margin-top: 8px; font-family: var(--gl-font-data); font-size: 13px; font-weight: 700;
  letter-spacing: .08em; text-transform: uppercase; color: var(--gl-ink); text-decoration: none; border-bottom: 3px solid var(--gl-rust); padding-bottom: 2px; }
.xsl-motion-link:hover, .xsl-motion-link:focus-visible { color: var(--gl-rust); }
"""
