"""The search page loads its script by content hash (#118 follow-up).

SiteGround caches /search/nordic-lab-search.js for a year, so a returning
visitor only gets a new script when its URL changes. These tests fail if the
page ever loads the script without ``?v=<current hash>`` again.
"""

import hashlib
import re
import subprocess
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
    # A correctly stamped tag inside a comment does not count; the active loader is unversioned.
    "<!-- {good} --><script src='nordic-lab-search.js'></script>",
    '<SCRIPT SRC="/search/Nordic-Lab-Search.js"></SCRIPT>',
    '{good}{good}',
    '{good}<script src="nordic-lab-search.js"></script>',
])
def test_checker_rejects_unversioned_or_stale_tag(tmp_path, tag):
    js = tmp_path / "nordic-lab-search.js"
    js.write_text("console.log(1);\n", encoding="utf-8")
    html = tmp_path / "nordic-lab-search.html"
    good = f'<script src="nordic-lab-search.js?v={ssv.script_version(js)}"></script>'
    html.write_text("<body>" + tag.replace("{good}", good) + "</body>", encoding="utf-8")
    assert ssv.check(html, js)


@pytest.mark.parametrize("tag", [
    '<script src="nordic-lab-search.js?v={v}"></script>',
    "<script src='nordic-lab-search.js?v={v}' defer></script>",
    '<!-- <script src="nordic-lab-search.js"></script> --><script src="nordic-lab-search.js?v={v}"></script>',
])
def test_checker_accepts_one_active_current_loader(tmp_path, tag):
    js = tmp_path / "nordic-lab-search.js"
    js.write_text("console.log(1);\n", encoding="utf-8")
    html = tmp_path / "nordic-lab-search.html"
    html.write_text("<body>" + tag.replace("{v}", ssv.script_version(js)) + "</body>", encoding="utf-8")
    assert ssv.check(html, js) is None


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


def test_deploy_refuses_a_stale_search_page(monkeypatch, tmp_path):
    deploy = _deploy_module(monkeypatch)
    monkeypatch.setattr(deploy, "_search_script_version_problem", lambda: "stale")
    monkeypatch.setattr(deploy, "_scp_upload", lambda *a, **k: pytest.fail("uploaded a stale page"))
    monkeypatch.setattr(deploy, "_ssh_run", lambda *a, **k: pytest.fail("touched the server"))
    assert deploy.sync_search() is False
