"""The search page loads its script by content hash (#118 follow-up).

SiteGround caches /search/nordic-lab-search.js for a year, so a returning
visitor only gets a new script when its URL changes. These tests fail if the
page ever loads the script without ``?v=<current hash>`` again.
"""

import hashlib
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import search_script_version as ssv  # noqa: E402

HTML = ROOT / "web" / "nordic-lab-search.html"
JS = ROOT / "web" / "nordic-lab-search.js"


def _script_srcs(html: str) -> list[str]:
    return re.findall(r'<script[^>]*\bsrc="([^"]*nordic-lab-search\.js[^"]*)"', html)


def test_page_loads_script_by_current_content_hash():
    want = hashlib.sha256(JS.read_bytes()).hexdigest()[:12]
    assert _script_srcs(HTML.read_text(encoding="utf-8")) == [f"nordic-lab-search.js?v={want}"], (
        "run: python scripts/search_script_version.py"
    )


def test_checker_passes_on_the_committed_page():
    assert ssv.check() is None


@pytest.mark.parametrize("tag", [
    '<script src="nordic-lab-search.js"></script>',
    '<script src="nordic-lab-search.js?v=000000000000"></script>',
])
def test_checker_rejects_unversioned_or_stale_tag(tmp_path, tag):
    js = tmp_path / "nordic-lab-search.js"
    js.write_text("console.log(1);\n", encoding="utf-8")
    html = tmp_path / "nordic-lab-search.html"
    html.write_text(f"<body>{tag}</body>", encoding="utf-8")
    assert ssv.check(html, js)


def test_stamp_follows_a_script_change(tmp_path):
    js = tmp_path / "nordic-lab-search.js"
    html = tmp_path / "nordic-lab-search.html"
    js.write_text("console.log(1);\n", encoding="utf-8")
    html.write_text('<body><script src="nordic-lab-search.js"></script></body>', encoding="utf-8")
    assert ssv.stamp(html, js)
    first = _script_srcs(html.read_text(encoding="utf-8"))
    assert ssv.check(html, js) is None

    js.write_text("console.log(2);\n", encoding="utf-8")
    assert ssv.check(html, js), "a changed script must make the old stamp stale"
    assert ssv.stamp(html, js)
    second = _script_srcs(html.read_text(encoding="utf-8"))
    assert first != second and ssv.check(html, js) is None


def test_no_other_page_loads_the_script_unversioned():
    for path in [*ROOT.glob("web/*.html"), *ROOT.glob("scripts/*.py"), *ROOT.glob("wordpress/*.py")]:
        if path.name in {"search_script_version.py"}:
            continue
        for src in _script_srcs(path.read_text(encoding="utf-8", errors="replace")):
            assert "?v=" in src, f"{path.relative_to(ROOT)} loads {src} without a version"


def test_deploy_refuses_a_stale_search_page():
    deploy_src = (ROOT / "scripts" / "deploy.py").read_text(encoding="utf-8")
    body = deploy_src.split("def sync_search():", 1)[1].split("\ndef ", 1)[0]
    assert "check_search_script_version()" in body
    assert body.index("check_search_script_version()") < body.index("_scp_upload")
