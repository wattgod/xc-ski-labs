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
