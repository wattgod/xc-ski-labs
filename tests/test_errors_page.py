"""XC-08: one hostname and a branded 404 (web/.htaccess, wordpress/generate_404.py)."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HTACCESS = (PROJECT_ROOT / "web" / ".htaccess").read_text(encoding="utf-8")


def _page(tmp_path: Path) -> str:
    subprocess.run([sys.executable, str(PROJECT_ROOT / "wordpress" / "generate_404.py"),
                    "--output-dir", str(tmp_path)], check=True, cwd=PROJECT_ROOT, capture_output=True)
    return (tmp_path / "404.html").read_text(encoding="utf-8")


def test_www_redirects_to_apex_with_path():
    assert re.search(r"RewriteCond %\{HTTP_HOST\} \^www\\\.xcskilabs\\\.com\$ \[NC\]", HTACCESS)
    assert "RewriteRule ^ https://xcskilabs.com%{REQUEST_URI} [R=301,L]" in HTACCESS


def test_no_https_rule_that_could_loop_behind_the_proxy():
    assert "%{HTTPS}" not in HTACCESS


def test_error_document_points_at_the_generated_page():
    assert "ErrorDocument 404 /404.html" in HTACCESS


def test_404_page_is_noindex_and_branded(tmp_path):
    html = _page(tmp_path)
    assert '<meta name="robots" content="noindex">' in html
    assert "XC Ski Labs" in html and 'href="/search/"' in html
    assert 'id="xl-consent-banner"' in html


def test_404_page_uses_only_absolute_paths(tmp_path):
    """It is served for missing URLs at any depth, so relative paths would break."""
    html = _page(tmp_path)
    for attr in re.findall(r'(?:href|src)="([^"]+)"', html):
        assert attr.startswith(("/", "https://", "mailto:", "#")), attr


def test_deploy_uploads_the_page_before_the_htaccess():
    src = (PROJECT_ROOT / "scripts" / "deploy.py").read_text(encoding="utf-8")
    body = src[src.index("def sync_errors"):src.index("def sync_feeds")]
    assert body.index('"404.html"') < body.index('".htaccess"')
    assert ".htaccess.bak-" in body


REMOVED_DUPLICATES = {  # removed slug -> surviving race (#87)
    "gatineau-55": "gatineau-loppet",
    "ushuaia-ski-marathon": "ushuaia-loppet",
}


def test_removed_duplicates_redirect_page_and_markdown():
    """A removed profile is gone from the data and both its URLs 301 to the survivor."""
    import re as _re
    from pathlib import Path as _Path
    root = _Path(__file__).resolve().parent.parent
    htaccess = (root / "web" / ".htaccess").read_text(encoding="utf-8")
    for old, new in REMOVED_DUPLICATES.items():
        assert not (root / "race-data" / f"{old}.json").exists(), old
        assert (root / "race-data" / f"{new}.json").exists(), new
        md = _re.search(rf"^RewriteRule \^race/{_re.escape(old)}\\\.md\$ https://xcskilabs\.com/race/{new}\.md \[R=301,L\]$", htaccess, _re.M)
        page = _re.search(rf"^RewriteRule \^race/{_re.escape(old)}\(\?:/\(\.\*\)\)\?\$ https://xcskilabs\.com/race/{new}/\$1 \[R=301,L\]$", htaccess, _re.M)
        assert md and page, old


def test_plan_manage_redirects_to_the_pipeline_page():
    """xcskilabs.com/plan/manage sends riders to the plan manage page (Railway).

    Only exact /plan/manage and /plan/manage/ move; the fragment token rides along
    in the browser, so the rule must not add a query string or a trailing path.
    """
    target = "https://athlete-custom-training-plan-pipeline-production.up.railway.app/plan/manage"
    rules = re.findall(r"^RewriteRule (\S+) (\S+) \[([^\]]+)\]$", HTACCESS, re.M)
    hits = [(p, t, f) for p, t, f in rules if t == target]
    assert hits == [(r"^plan/manage/?$", target, "R=302,L")]
    pattern = hits[0][0]
    for path in ("plan/manage", "plan/manage/"):
        assert re.search(pattern, path)
    for path in ("plan/manage/x", "plan/", "plan/managed", "xplan/manage"):
        assert not re.search(pattern, path)
