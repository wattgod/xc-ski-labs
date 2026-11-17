"""Race rows on /search/ in real browsers (#118).

Runs tests/browser/search_row_links.js with Node Playwright in Chromium,
WebKit and Firefox at 1440 and 390. Engines that are not installed are
skipped; at least one must run for the test to count.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tests" / "browser" / "search_row_links.js"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


@pytest.fixture(scope="module")
def results():
    proc = subprocess.run(
        ["node", str(SCRIPT), str(ROOT / "web")],
        capture_output=True, text=True, timeout=300, cwd=ROOT,
    )
    assert proc.returncode == 0, proc.stderr
    rows = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith("{")]
    errors = [r for r in rows if r["status"] == "error"]
    assert not errors, errors
    ran = [r for r in rows if r["status"] == "ran"]
    if not ran:
        pytest.skip("no Playwright browser engine installed: " + json.dumps(rows))
    return ran


def test_every_cell_opens_its_own_race(results):
    for r in results:
        assert r["hits"] == r["total"] > 0, (r["engine"], r["width"], r["misses"])
        assert set(r["linksPerRow"]) == {1}, (r["engine"], r["width"])
        assert not r["cueFocusable"], (r["engine"], r["width"])


def test_nothing_outside_the_rows_is_a_race_link(results):
    for r in results:
        assert not r["belowIsLink"], (r["engine"], r["width"])
        assert not r["hscroll"], (r["engine"], r["width"])


def test_keyboard_reaches_rows_and_rings_them(results):
    for r in results:
        assert r["reached"], (r["engine"], r["width"])
        assert r["ring"] == "solid", (r["engine"], r["width"])
        assert r["nextIsRow2"], (r["engine"], r["width"])


def test_one_click_one_event_and_navigation(results):
    for r in results:
        assert r["events"] == ["fixture-race-2"], (r["engine"], r["width"])
        assert r["navigated"], (r["engine"], r["width"])
        assert r["jsLoads"] == 1, (r["engine"], r["width"])
