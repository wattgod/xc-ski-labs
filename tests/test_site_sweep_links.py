"""Site sweep 2026-11-14: no links to the unshipped course, service pages in
the sitemap.

/learn/ and /course/ return 404 on xcskilabs.com, so no generated page may
link them while COURSE_LIVE is False, even when a stale local build left
output/learn/index.html behind. /coaching/ and /consulting/ are live,
indexable pages and belong in the sitemap; apply/intake/confirmation pages
do not.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _race(slug: str) -> dict:
    return json.loads((ROOT / "race-data" / f"{slug}.json").read_text(encoding="utf-8"))["race"]


def _fake_course_build(tmp_path: Path) -> Path:
    out = tmp_path / "output"
    (out / "learn").mkdir(parents=True)
    (out / "learn" / "index.html").write_text("<html></html>", encoding="utf-8")
    return out


class TestNoCourseLinkUntilLive:
    def test_homepage_flag_is_off(self):
        assert _load("hp_sweep", "scripts/generate_homepage.py").COURSE_LIVE is False

    def test_race_pages_flag_is_off(self):
        assert _load("rp_sweep", "scripts/generate_race_pages.py").COURSE_LIVE is False

    def test_homepage_has_no_course_link_even_with_local_build(self, tmp_path):
        hp = _load("hp_sweep2", "scripts/generate_homepage.py")
        hp.DEFAULT_OUTPUT_DIR = _fake_course_build(tmp_path)
        page = hp.generate_homepage([_race("vasaloppet"), _race("birkebeinerrennet")])
        assert 'href="/learn/' not in page
        assert 'href="/course/' not in page
        assert "See the course" not in page

    def test_race_page_ladder_has_no_course_link_even_with_local_build(self, tmp_path):
        rp = _load("rp_sweep2", "scripts/generate_race_pages.py")
        rp.DEFAULT_OUTPUT_DIR = _fake_course_build(tmp_path)
        ladder = rp.build_product_ladder(_race("vasaloppet"))
        assert 'href="/learn/' not in ladder
        assert "See the course" not in ladder


class TestSitemapServicePages:
    def _xml(self):
        sm = _load("sm_sweep", "scripts/generate_sitemap.py")
        xml, _ = sm.generate_sitemap("https://xcskilabs.com", [])
        return xml.decode("utf-8") if isinstance(xml, bytes) else xml

    def test_coaching_and_consulting_listed(self):
        xml = self._xml()
        assert "<loc>https://xcskilabs.com/coaching/</loc>" in xml
        assert "<loc>https://xcskilabs.com/consulting/</loc>" in xml

    def test_no_apply_intake_or_confirmation_pages(self):
        xml = self._xml()
        for path in ("/coaching/apply/", "/coaching/welcome/", "/consulting/intake/",
                     "/consulting/confirmed/", "/learn/", "/course/"):
            assert f"<loc>https://xcskilabs.com{path}</loc>" not in xml
