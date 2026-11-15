"""XC-07 / ALL-10: the homepage says who runs XC Ski Labs, with no invented facts."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _graph(tmp_path):
    subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "generate_homepage.py"),
                    "--output-dir", str(tmp_path)], check=True, cwd=PROJECT_ROOT, capture_output=True)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    return [n for b in blocks for n in json.loads(b.replace("<\\/", "</")).get("@graph", [])]


def test_organization_with_parent_and_contact(tmp_path):
    org = next(n for n in _graph(tmp_path) if n.get("@type") == "Organization")
    assert org["name"] == "XC Ski Labs"
    assert org["parentOrganization"]["name"] == "Gravel God Cycling LLC"
    assert org["email"] == "gravelgodcoaching@gmail.com"
    # Nothing guessed: no social profiles exist, and Google wants a raster logo.
    assert "sameAs" not in org and "logo" not in org


def test_website_names_its_publisher(tmp_path):
    graph = _graph(tmp_path)
    site = next(n for n in graph if n.get("@type") == "WebSite")
    org = next(n for n in graph if n.get("@type") == "Organization")
    assert site["publisher"] == {"@id": org["@id"]}
    assert site["potentialAction"]["@type"] == "SearchAction"
