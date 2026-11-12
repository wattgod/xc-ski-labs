"""Technique loops: Gravel God skiing each classic technique (scripts/xsl_loops.py)."""

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import xsl_loops  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("tech", sorted(xsl_loops.LOOPS))
@pytest.mark.parametrize("shape", sorted(xsl_loops.SIZES))
def test_every_loop_has_web_sized_video_and_poster(tech, shape):
    mp4, jpg = xsl_loops.media_files(tech, shape)
    assert mp4.exists() and jpg.exists(), f"missing media for {tech}/{shape}"
    assert mp4.stat().st_size < 600_000, f"{mp4.name} is too heavy for an autoplaying loop"
    assert jpg.stat().st_size < 400_000


def test_figure_is_lazy_muted_inline_and_decorative():
    html = xsl_loops.loop_figure("diagonal", "square")
    video = re.search(r"<video[^>]*>", html).group(0)
    for attr in ("muted", "loop", "playsinline", 'preload="none"', 'aria-hidden="true"', 'data-src="/media/loops/diagonal_square.mp4"',
                 'poster="/media/loops/diagonal_square.jpg"'):
        assert attr in video
    assert " src=" not in video, "the video must not download before it scrolls into view"
    assert "Diagonal stride" in html and "Climbing gear" in html


def test_loop_script_respects_reduced_motion_and_guards_entries():
    js = xsl_loops.LOOP_JS
    assert "prefers-reduced-motion: reduce" in js
    assert js.index("if (mq && mq.matches) return;") < js.index("IntersectionObserver(")
    assert "addEventListener('change'" in js and "v.pause()" in js     # turned on mid-visit: loops stop
    assert "!entries.length" in js                      # pitfall #33
    assert "requestAnimationFrame" in js


def test_loop_css_has_no_radius_or_shadow():
    css = xsl_loops.LOOP_CSS + xsl_loops.BAND_CSS
    assert "border-radius" not in css and "box-shadow" not in css


def test_race_pages_show_a_loop_for_classic_and_both_only():
    gen = _load("generate_race_pages", SCRIPTS_DIR / "generate_race_pages.py")
    seen = {}
    for path in sorted((PROJECT_ROOT / "race-data").glob("*.json")):
        if path.name == "_schema.json":
            continue
        race = json.loads(path.read_text(encoding="utf-8"))["race"]
        disc = str(race.get("vitals", {}).get("discipline", "")).lower()
        if disc in seen:
            continue
        seen[disc] = gen.build_technique_motion(race)
    assert "data-xsl-loop" in seen["classic"] and "/media/loops/diagonal_square.mp4" in seen["classic"]
    assert "data-xsl-loop" in seen["both"] and "/media/loops/kickdp_square.mp4" in seen["both"]
    assert seen.get("skate", "") == ""


def test_homepage_band_links_to_the_technique_chapter():
    gen = _load("generate_homepage", SCRIPTS_DIR / "generate_homepage.py")
    races = gen.load_all_races(PROJECT_ROOT / "race-data")
    html = gen.generate_homepage(races)
    band = html[html.index('id="motion"'):]
    band = band[:band.index("</section>")]
    assert band.count("data-xsl-loop") == 3
    assert 'href="/guide/technique-and-execution/"' in band
    assert "prefers-reduced-motion: reduce" in html


def test_guide_classic_gears_block_lists_known_techniques():
    content = json.loads((PROJECT_ROOT / "guide" / "xc-guide-content.json").read_text(encoding="utf-8"))
    blocks = [b for ch in content["chapters"] for sec in ch.get("sections", []) for b in sec.get("blocks", [])
              if b.get("type") == "technique_loops"]
    assert blocks, "classic gears should carry the technique loops"
    for b in blocks:
        assert b["techniques"] and all(t in xsl_loops.LOOPS for t in b["techniques"])


# ---------------------------------------------------------------- deploy fails closed (sol review, 2026-10-18)
def _deploy():
    return _load("deploy", SCRIPTS_DIR / "deploy.py")


def test_media_check_needs_every_file_by_name_and_size(tmp_path):
    deploy = _deploy()
    a, b = tmp_path / "a.mp4", tmp_path / "b.jpg"
    a.write_bytes(b"x" * 10); b.write_bytes(b"y" * 5)
    for listing, want in (("a.mp4 10\nb.jpg 5\nold.jpg 9\n", True),     # extra stale files are fine
                          ("a.mp4 10\nold.jpg 5\nzz.jpg 1\n", False),   # a stale file can't stand in for b.jpg
                          ("a.mp4 11\nb.jpg 5\n", False)):              # a truncated upload fails
        deploy._ssh_run = lambda h, u, p, c, timeout=30, out=listing: (True, out, "")
        assert deploy.media_on_server("h", "u", "1", [a, b], "/x") is want


def test_deploy_all_stops_before_pages_when_media_upload_fails():
    deploy = _deploy()
    calls = []
    deploy.sync_media = lambda: calls.append("media") or False
    for fn in ("sync_homepage", "sync_search", "sync_pages", "sync_training", "sync_guide", "purge_cache"):
        setattr(deploy, fn, lambda fn=fn: calls.append(fn) or True)
    assert deploy.deploy_all() is False
    assert calls == ["media"]


def test_page_uploads_that_show_loops_wait_for_the_media():
    deploy = _deploy()
    deploy.sync_media = lambda: False
    deploy.get_ssh_credentials = lambda: (_ for _ in ()).throw(AssertionError("page upload must not start"))
    assert deploy.sync_homepage() is False
    assert deploy.sync_pages() is False
    assert deploy.sync_training() is False
    assert deploy.sync_guide() is False
