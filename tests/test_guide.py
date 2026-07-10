import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE_JSON = ROOT / "guide" / "xc-guide-content.json"
OUTPUT_GUIDE = ROOT / "output" / "guide"
TOKEN_CSS = ROOT / "tokens" / "tokens.css"


def setup_module():
    subprocess.run(["python3", "scripts/generate_guide.py"], cwd=ROOT, check=True)


def _content():
    return json.loads(GUIDE_JSON.read_text(encoding="utf-8"))


def _chapter_html(chapter):
    return (OUTPUT_GUIDE / chapter["id"] / "index.html").read_text(encoding="utf-8")


def test_all_8_chapters_generate():
    content = _content()
    assert (OUTPUT_GUIDE / "index.html").exists()
    assert len(content["chapters"]) == 8
    for chapter in content["chapters"]:
        path = OUTPUT_GUIDE / chapter["id"] / "index.html"
        assert path.exists(), chapter["id"]
        html = path.read_text(encoding="utf-8")
        assert f"Chapter {chapter['number']}:" in html


def test_gate_meta_correct_per_chapter():
    for chapter in _content()["chapters"]:
        html = _chapter_html(chapter)
        if chapter["number"] <= 3:
            assert '<meta name="robots" content="index, follow">' in html
            assert "Email gate coming next" not in html
        else:
            assert '<meta name="robots" content="noindex">' in html
            assert "Email gate coming next" in html
            assert '<a class="gl-guide-btn" href="/questionnaire/">' in html


def test_every_inline_citation_resolves_to_rendered_source_link():
    marker_re = re.compile(r"\[\^([A-Za-z0-9_.-]+)\]")
    for chapter in _content()["chapters"]:
        html = _chapter_html(chapter)
        raw = json.dumps(chapter)
        marker_ids = marker_re.findall(raw)
        source_ids = {s["id"] for s in chapter.get("sources", [])}
        assert set(marker_ids) <= source_ids
        for sid in marker_ids:
            assert f'href="#source-{sid}"' in html
            assert f'id="source-{sid}"' in html


def test_race_references_point_to_existing_slugs():
    race_slugs = {p.stem for p in (ROOT / "race-data").glob("*.json") if p.name != "_schema.json"}
    for chapter in _content()["chapters"]:
        for section in chapter["sections"]:
            for block in section["blocks"]:
                if block.get("type") == "race_reference":
                    assert block["slug"] in race_slugs


def test_no_inline_onclick_in_guide_output():
    for path in OUTPUT_GUIDE.glob("**/index.html"):
        assert "onclick=" not in path.read_text(encoding="utf-8").lower(), path


def test_no_hex_outside_tokens_in_guide_output():
    color_re = re.compile(r"(?<!&)#[0-9a-fA-F]{3,6}")
    allowed = {m.group(0).lower() for m in color_re.finditer(TOKEN_CSS.read_text())}
    for path in OUTPUT_GUIDE.glob("**/index.html"):
        found = {m.group(0).lower() for m in color_re.finditer(path.read_text())}
        assert found <= allowed, (path, sorted(found - allowed))


def test_no_banned_register_phrases_in_guide_output():
    banned = ("honestly", "honest review")
    for path in OUTPUT_GUIDE.glob("**/index.html"):
        html = path.read_text(encoding="utf-8").lower()
        for phrase in banned:
            assert phrase not in html, (path, phrase)
