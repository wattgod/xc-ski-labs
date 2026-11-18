"""The search page loads its script and race index by content hash (#118, #123).

SiteGround caches /search/nordic-lab-search.js for a year and
/search/race-index.json for 180 days, so a returning visitor only gets a new
copy when its URL changes. These tests fail if the page ever loads either
without ``?v=<current hash>`` again.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import search_script_version as ssv  # noqa: E402

HTML = ROOT / "web" / "nordic-lab-search.html"
JS = ROOT / "web" / "nordic-lab-search.js"
INDEX = ROOT / "web" / "race-index.json"


def _fixture(tmp_path):
    js = tmp_path / "nordic-lab-search.js"
    js.write_text("console.log(1);\n", encoding="utf-8")
    index = tmp_path / "race-index.json"
    index.write_text('{"races":[]}', encoding="utf-8")
    return js, index, tmp_path / "nordic-lab-search.html"


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
    # A correctly stamped tag inside a comment does not count; the active loader is unversioned.
    "<!-- {good} --><script src='nordic-lab-search.js'></script>",
    '<SCRIPT SRC="/search/Nordic-Lab-Search.js"></SCRIPT>',
    '{good}{good}',
    '{good}<script src="nordic-lab-search.js"></script>',
])
def test_checker_rejects_unversioned_or_stale_tag(tmp_path, tag):
    js, index, html = _fixture(tmp_path)
    html.write_text("<body>" + tag.replace("{good}", ssv.script_tag(js, index)) + "</body>", encoding="utf-8")
    assert ssv.check(html, js, index)


@pytest.mark.parametrize("tag", [
    # Script current, index unversioned or stale.
    '<script src="nordic-lab-search.js?v={v}"></script>',
    '<script src="nordic-lab-search.js?v={v}" data-index-version=""></script>',
    '<script src="nordic-lab-search.js?v={v}" data-index-version="000000000000"></script>',
    # The index hash on some other element does not count.
    '<main data-index-version="{i}"></main><script src="nordic-lab-search.js?v={v}"></script>',
])
def test_checker_rejects_unversioned_or_stale_index(tmp_path, tag):
    js, index, html = _fixture(tmp_path)
    tag = tag.replace("{v}", ssv.script_version(js)).replace("{i}", ssv.index_version(index))
    html.write_text("<body>" + tag + "</body>", encoding="utf-8")
    assert ssv.check(html, js, index)


@pytest.mark.parametrize("tag", [
    '<script src="nordic-lab-search.js?v={v}" data-index-version="{i}"></script>',
    "<script src='nordic-lab-search.js?v={v}' data-index-version='{i}' defer></script>",
    '<!-- <script src="nordic-lab-search.js"></script> -->'
    '<script src="nordic-lab-search.js?v={v}" data-index-version="{i}"></script>',
])
def test_checker_accepts_one_active_current_loader(tmp_path, tag):
    js, index, html = _fixture(tmp_path)
    tag = tag.replace("{v}", ssv.script_version(js)).replace("{i}", ssv.index_version(index))
    html.write_text("<body>" + tag + "</body>", encoding="utf-8")
    assert ssv.check(html, js, index) is None


def test_stamp_follows_a_script_change(tmp_path):
    js, index, html = _fixture(tmp_path)
    html.write_text('<body><script src="nordic-lab-search.js"></script></body>', encoding="utf-8")
    assert ssv.stamp(html, js, index)
    first = _script_srcs(html.read_text(encoding="utf-8"))
    assert ssv.check(html, js, index) is None

    js.write_text("console.log(2);\n", encoding="utf-8")
    assert ssv.check(html, js, index), "a changed script must make the old stamp stale"
    assert ssv.stamp(html, js, index)
    second = _script_srcs(html.read_text(encoding="utf-8"))
    assert first != second and ssv.check(html, js, index) is None


def test_index_change_moves_only_the_index_hash(tmp_path):
    js, index, html = _fixture(tmp_path)
    html.write_text('<body><script src="nordic-lab-search.js?v=old"></script></body>', encoding="utf-8")
    assert ssv.stamp(html, js, index)
    first = html.read_text(encoding="utf-8")

    index.write_text('{"races":[{"s":"new-race"}]}', encoding="utf-8")
    assert ssv.check(html, js, index), "a changed index must make the old stamp stale"
    assert ssv.stamp(html, js, index)
    second = html.read_text(encoding="utf-8")
    assert _script_srcs(first) == _script_srcs(second), "a data change must not move the script URL"
    assert f'data-index-version="{ssv.index_version(index)}"' in second
    assert ssv.check(html, js, index) is None


def test_page_names_the_committed_index_by_hash():
    want = hashlib.sha256(INDEX.read_bytes()).hexdigest()[:12]
    assert ssv.search_scripts(HTML.read_text(encoding="utf-8"))[0].get("data-index-version") == want, (
        "run: python scripts/search_script_version.py"
    )


FETCH_HARNESS = r"""
const fetched = [];
const grid = { textContent: "" };
global.document = {
  currentScript: process.argv[2] === "-" ? null
    : { getAttribute: (k) => (k === "data-index-version" ? process.argv[2] : null) },
  getElementById: () => grid,
  querySelectorAll: () => [],
  addEventListener: (t, f) => { if (t === "DOMContentLoaded") global.__ready = f; },
};
global.window = { location: { search: "", pathname: "/search/" }, history: { replaceState() {} } };
global.fetch = async (url) => { fetched.push(String(url)); throw new Error("stop after recording the URL"); };
new Function(require("fs").readFileSync(process.argv[1], "utf8"))();
(async () => {
  if (global.__ready) await global.__ready();
  console.log(JSON.stringify({ fetched, grid: grid.textContent }));
})();
"""


def _fetched(version: str) -> dict:
    proc = subprocess.run(["node", "-e", FETCH_HARNESS, str(JS), version],
                          capture_output=True, text=True, timeout=10)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_script_fetches_the_index_by_the_page_hash():
    out = _fetched("abc123def456")
    assert out["fetched"] == ["race-index.json?v=abc123def456"], out


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_script_never_fetches_the_index_unversioned():
    out = _fetched("-")
    assert out["fetched"] == [], "without data-index-version the script must not fetch the bare URL"
    assert out["grid"] == "Failed to load race data."


def test_script_has_no_bare_index_fetch():
    js = JS.read_text(encoding="utf-8")
    assert not re.search(r"""fetch\(\s*["'`][^"'`]*race-index\.json["'`]\s*\)""", js)


def test_no_other_page_loads_the_script_unversioned():
    for path in [*ROOT.glob("web/*.html"), *ROOT.glob("scripts/*.py"), *ROOT.glob("wordpress/*.py")]:
        if path.name in {"search_script_version.py"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for src in [*_script_srcs(text), *ssv.search_script_srcs(text)]:
            assert "?v=" in src, f"{path.relative_to(ROOT)} loads {src} without a version"


@pytest.mark.parametrize("module, call", [
    ("scripts.deploy", "m._search_script_version_problem()"),
    ("scripts.preflight", "m.check_output_pages(m.PreflightResult())"),
])
def test_checks_work_when_imported_as_a_package_module(module, call):
    """deploy/preflight must find search_script_version without scripts/ on sys.path."""
    code = f"import importlib; m = importlib.import_module({module!r}); {call}"
    proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr[-2000:]


def _deploy_module(monkeypatch):
    import deploy
    monkeypatch.setattr(deploy, "get_ssh_credentials", lambda: ("host", "user", "1"))
    return deploy


def test_deploy_uploads_script_before_page(monkeypatch):
    deploy = _deploy_module(monkeypatch)
    uploads, commands = [], []
    monkeypatch.setattr(deploy, "_scp_upload", lambda h, u, p, local, remote, **k: uploads.append(Path(local).name) or True)
    monkeypatch.setattr(deploy, "_ssh_run", lambda h, u, p, cmd, **k: commands.append(cmd) or (True, "", ""))
    assert deploy.sync_search() is True
    assert uploads == ["nordic-lab-search.js", "race-index.json", "nordic-lab-search.html"]
    renames = [c for c in commands if " mv -f " in c]
    assert [c.rsplit("/", 1)[-1] for c in renames] == ["nordic-lab-search.js", "race-index.json", "index.html"]


def test_deploy_never_publishes_page_when_script_upload_fails(monkeypatch):
    deploy = _deploy_module(monkeypatch)
    uploads = []

    def scp(h, u, p, local, remote, **k):
        uploads.append(Path(local).name)
        return Path(local).name != "nordic-lab-search.js"

    monkeypatch.setattr(deploy, "_scp_upload", scp)
    monkeypatch.setattr(deploy, "_ssh_run", lambda *a, **k: (True, "", ""))
    assert deploy.sync_search() is False
    assert uploads == ["nordic-lab-search.js"]


def test_sync_index_uploads_index_then_page(monkeypatch):
    deploy = _deploy_module(monkeypatch)
    uploads, commands = [], []
    monkeypatch.setattr(deploy, "_scp_upload", lambda h, u, p, local, remote, **k: uploads.append(Path(local).name) or True)
    monkeypatch.setattr(deploy, "_ssh_run", lambda h, u, p, cmd, **k: commands.append(cmd) or (True, "", ""))
    assert deploy.sync_index() is True
    assert uploads == ["race-index.json", "nordic-lab-search.html"]
    renames = [c for c in commands if " mv -f " in c]
    assert [c.rsplit("/", 1)[-1] for c in renames] == ["race-index.json", "index.html"]


def test_sync_index_never_publishes_page_when_index_upload_fails(monkeypatch):
    deploy = _deploy_module(monkeypatch)
    uploads = []

    def scp(h, u, p, local, remote, **k):
        uploads.append(Path(local).name)
        return Path(local).name != "race-index.json"

    monkeypatch.setattr(deploy, "_scp_upload", scp)
    monkeypatch.setattr(deploy, "_ssh_run", lambda *a, **k: (True, "", ""))
    assert deploy.sync_index() is False
    assert uploads == ["race-index.json"]


@pytest.mark.parametrize("sync", ["sync_search", "sync_index"])
def test_deploy_refuses_a_stale_page_for_either_sync(monkeypatch, sync):
    deploy = _deploy_module(monkeypatch)
    monkeypatch.setattr(deploy, "_search_script_version_problem", lambda: "stale")
    monkeypatch.setattr(deploy, "_scp_upload", lambda *a, **k: pytest.fail("uploaded a stale page"))
    monkeypatch.setattr(deploy, "_ssh_run", lambda *a, **k: pytest.fail("touched the server"))
    assert getattr(deploy, sync)() is False


def test_deploy_refuses_a_stale_search_page(monkeypatch, tmp_path):
    deploy = _deploy_module(monkeypatch)
    monkeypatch.setattr(deploy, "_search_script_version_problem", lambda: "stale")
    monkeypatch.setattr(deploy, "_scp_upload", lambda *a, **k: pytest.fail("uploaded a stale page"))
    monkeypatch.setattr(deploy, "_ssh_run", lambda *a, **k: pytest.fail("touched the server"))
    assert deploy.sync_search() is False
