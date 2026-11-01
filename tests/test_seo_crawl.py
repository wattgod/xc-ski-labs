"""Crawl-health guards from the Oct 31, 2026 SEO pass: internal links that
resolve, landing pages in the sitemap, a sitemap that is regenerated on every
deploy, and deploy staging that never ships non-race pages under /race/."""

import importlib.util
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


guide = _load_module("generate_guide_seo", SCRIPTS_DIR / "generate_guide.py")
sitemap = _load_module("generate_sitemap_seo", SCRIPTS_DIR / "generate_sitemap.py")
homepage = _load_module("generate_homepage_seo", SCRIPTS_DIR / "generate_homepage.py")
deploy = _load_module("deploy_seo", SCRIPTS_DIR / "deploy.py")


def test_guide_race_reference_links_into_race_section():
    block = {"type": "race_reference", "slug": "vasaloppet", "context": "The oldest loppet."}
    content = guide.load_content()
    chapter = content["chapters"][0]
    html = guide.render_block(block, chapter, content)
    assert 'href="/race/vasaloppet/"' in html
    assert 'href="/vasaloppet/"' not in html


def test_sitemap_lists_coaching_and_consulting_landing_pages():
    xml, _ = sitemap.generate_sitemap("https://xcskilabs.com", [{"slug": "alpha", "tier": 1, "overall_score": 90}])
    text = xml.decode("utf-8")
    assert "https://xcskilabs.com/coaching/</loc>" in text
    assert "https://xcskilabs.com/consulting/</loc>" in text
    # intake/confirmation steps stay out: they are noindex
    assert "/coaching/apply/" not in text and "/consulting/intake/" not in text


def test_sync_sitemap_regenerates_before_upload():
    src = (SCRIPTS_DIR / "deploy.py").read_text(encoding="utf-8")
    body = src[src.index("def sync_sitemap"):src.index("def sync_training")]
    call = 'SCRIPT_DIR / "generate_sitemap.py"'
    assert call in body
    assert body.index(call) < body.index("_scp_upload")


def test_pages_deploy_refreshes_sitemap():
    src = (SCRIPTS_DIR / "deploy.py").read_text(encoding="utf-8")
    body = src[src.index("def sync_pages"):src.index("def sync_homepage")]
    assert "sync_sitemap()" in body


def test_non_race_output_dirs_never_ship_under_race():
    for name in ("consulting", "media", "learn"):
        assert name in deploy.NON_RACE_OUTPUT_DIRS


def test_homepage_hides_course_link_until_course_exists():
    if (homepage.DEFAULT_OUTPUT_DIR / "learn" / "index.html").exists():
        return
    races = homepage.load_all_races(PROJECT_ROOT / "race-data")
    html = homepage.generate_homepage(races)
    assert 'href="/learn/"' not in html, "/learn/ 404s live until the course is built"
