"""Race rows open the race from anywhere on the row (#118).

The race name is each row's one real link; its ::after is stretched over the
positioned row. READ is a visual cue only: not a link, hidden from assistive
tech, so keyboard and screen-reader users meet one link per race.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

HAS_NODE = shutil.which("node") is not None


def _rule(css: str, selector: str) -> str:
    match = re.search(re.escape(selector) + r"\s*\{\{?([^}]*)\}", css)
    assert match, f"no rule for {selector}"
    return match.group(1)


# ── Search page ────────────────────────────────────────────


@pytest.fixture(scope="module")
def search_css():
    return (WEB_DIR / "nordic-lab-search.html").read_text(encoding="utf-8")


class TestSearchRowCss:
    def test_row_is_positioning_context(self, search_css):
        body = _rule(search_css, ".race-table .race-row")
        assert "position: relative" in body
        # WebKit only treats a row as the containing block when it is
        # transformed, and only clips the ::after to the row with clip-path.
        assert "transform: translate(0)" in body
        assert "clip-path: inset(0)" in body

    def test_name_after_covers_row(self, search_css):
        body = _rule(search_css, ".race-table .race-name::after")
        assert 'content: ""' in body
        assert "position: absolute" in body
        assert "inset: 0" in body

    def test_no_positioned_cell_traps_the_after(self, search_css):
        for selector in (".race-table td", ".race-table th"):
            assert "position" not in _rule(search_css, selector)

    def test_hover_and_focus_signifiers(self, search_css):
        assert "background: var(--panel)" in _rule(search_css, ".race-table .race-row:hover > td")
        assert "solid var(--focus)" in _rule(
            search_css, ".race-table .race-row:has(.race-name:focus-visible)"
        )
        assert "outline: none !important" in _rule(
            search_css, "html body .race-table .race-row:has(.race-name:focus-visible) .race-name:focus-visible"
        )
        assert re.search(r"\.race-row:hover \.race-name[^{]*\{[^}]*underline", search_css)


SEARCH_HARNESS = r"""
const fs = require("fs");
class El {
  constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.attrs = {};
    this.className = ""; this.textContent = ""; this.value = ""; this.dataset = {}; this.listeners = {};
    this.classList = { toggle() {}, add() {}, remove() {} }; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  getAttribute(k) { return k === "href" ? this.href : this.attrs[k]; }
  append(...c) { this.children.push(...c); }
  appendChild(c) { this.children.push(c); return c; }
  replaceChildren() { this.children = []; }
  addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); }
}
const ids = {};
const docListeners = [];
global.document = {
  createElement: (t) => new El(t),
  getElementById: (id) => (ids[id] = ids[id] || new El("div")),
  querySelectorAll: () => [],
  addEventListener: (t, f) => { if (t === "DOMContentLoaded") docListeners.push(f); },
};
global.document.currentScript = { getAttribute: (k) => (k === "data-index-version" ? "abc123def456" : null) };
global.window = { location: { search: "", pathname: "/search/" }, history: { replaceState() {} } };
global.fetch = async () => ({ ok: true, json: async () => ({ races: [
  { n: "Fixture Loppet", dn: "Fixture Loppet", s: "fixture-loppet", t: 1, sc: 88, co: "Norway", cc: "NO", d: 50, di: "classic", st: "fixture loppet" },
] }) });
const src = fs.readFileSync(process.argv[1], "utf8");
for (let i = 0; i < Number(process.argv[2]); i++) new Function(src)();
(async () => {
  for (const f of docListeners) await f();
  const rows = ids.raceGrid.children;
  const row = rows[0];
  const walk = (el, out) => { out.push(el); el.children.forEach((c) => walk(c, out)); return out; };
  const all = walk(row, []);
  console.log(JSON.stringify({
    rowCount: rows.length,
    rowClass: row.className,
    links: all.filter((e) => e.tagName === "A").map((e) => ({ cls: e.className, href: e.href, text: e.textContent })),
    cue: all.filter((e) => e.className === "rowlink").map((e) => ({ tag: e.tagName, hidden: e.attrs["aria-hidden"], text: e.textContent })),
    docListeners: docListeners.length,
    gridClickListeners: (ids.raceGrid.listeners.click || []).length,
  }));
})();
"""


def _run_search(times: int = 1) -> dict:
    result = subprocess.run(
        ["node", "-e", SEARCH_HARNESS, str(WEB_DIR / "nordic-lab-search.js"), str(times)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.skipif(not HAS_NODE, reason="node not installed")
class TestSearchRowMarkup:
    def test_race_name_is_the_rows_only_link(self):
        out = _run_search()
        assert out["rowCount"] == 1
        assert out["rowClass"] == "race-row"
        assert out["links"] == [
            {"cls": "race-name", "href": "/race/fixture-loppet/", "text": "Fixture Loppet"}
        ]

    def test_read_cue_is_decorative(self):
        out = _run_search()
        assert out["cue"] == [{"tag": "SPAN", "hidden": "true", "text": "READ →"}]

    def test_click_tracking_reads_the_name_link(self):
        js = (WEB_DIR / "nordic-lab-search.js").read_text(encoding="utf-8")
        assert 'closest("a.race-name")' in js
        assert "a.rowlink" not in js


# ── Homepage Tier 1 table ──────────────────────────────────


class TestHomepageRows:
    def test_tier_row_markup(self):
        import generate_homepage as gh

        row = gh.build_tier_row({
            "slug": "fixture-loppet",
            "display_name": "Fixture <Loppet>",
            "vitals": {"country": "Norway", "distance_km": 50, "discipline": "classic"},
            "nordic_lab_rating": {"overall_score": 88, "tier": 1},
        })
        assert '<tr class="race-row">' in row
        assert re.findall(r"<a\b[^>]*>", row) == ['<a class="race-name" href="/race/fixture-loppet/">']
        assert "Fixture &lt;Loppet&gt;</a>" in row
        assert '<span class="rowlink" aria-hidden="true">READ &rarr;</span>' in row

    def test_tier_table_css(self):
        src = (REPO_ROOT / "scripts" / "generate_homepage.py").read_text(encoding="utf-8")
        row = _rule(src, ".tier-table .race-row")
        assert "position: relative" in row and "transform: translate(0)" in row
        assert "clip-path: inset(0)" in row
        body = _rule(src, ".tier-table .race-name::after")
        assert "position: absolute" in body and "inset: 0" in body
        assert "position" not in _rule(src, ".tier-table td")
        assert "solid var(--focus)" in _rule(
            src, ".tier-table .race-row:has(.race-name:focus-visible)"
        )
        assert "background: var(--panel)" in _rule(src, ".tier-table .race-row:hover > td")
