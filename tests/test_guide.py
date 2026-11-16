import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE_JSON = ROOT / "guide" / "xc-guide-content.json"
OUTPUT_GUIDE = ROOT / "output" / "guide"
TOKEN_CSS = ROOT / "tokens" / "tokens.css"

sys.path.insert(0, str(ROOT / "scripts"))
import generate_guide as gg  # noqa: E402
import xsl_loops  # noqa: E402


def setup_module():
    subprocess.run([sys.executable, "scripts/generate_guide.py"], cwd=ROOT, check=True)


def _content():
    return json.loads(GUIDE_JSON.read_text(encoding="utf-8"))


def _chapter_html(chapter):
    return (OUTPUT_GUIDE / chapter["id"] / "index.html").read_text(encoding="utf-8")


def _visible_text(html):
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", text)


def _guide_pages():
    content = _content()
    return [OUTPUT_GUIDE / "index.html"] + [OUTPUT_GUIDE / c["id"] / "index.html" for c in content["chapters"]]


def test_every_chapter_generates_and_is_open():
    content = _content()
    assert (OUTPUT_GUIDE / "index.html").exists()
    n = len(content["chapters"])
    assert [c["number"] for c in content["chapters"]] == list(range(1, n + 1))
    for chapter in content["chapters"]:
        html = _chapter_html(chapter)
        assert f"Chapter {chapter['number']}:" in html
        assert '<meta name="robots" content="index, follow">' in html
        assert "gl-guide-gate" not in html and "fueling-lead-intake" not in html  # free, no email gate
    assert f"{n} chapters" in (OUTPUT_GUIDE / "index.html").read_text(encoding="utf-8")


OLD_CHAPTERS = ("what-is-xc-ski-racing", "race-selection", "training-fundamentals", "technique-and-execution",
                "nutrition-fueling-cold", "tactics-and-the-mind", "race-week-protocol", "post-race-and-offseason")


def test_retired_chapter_urls_redirect_to_a_live_page():
    content = _content()
    live = {c["id"] for c in content["chapters"]}
    assert set(OLD_CHAPTERS) <= set(content["retired_chapters"])  # every URL the old guide published
    for old, new in content["retired_chapters"].items():
        html = (OUTPUT_GUIDE / old / "index.html").read_text(encoding="utf-8")
        target = f"/guide/{new}/" if new else "/guide/"
        assert not new or new in live
        assert f'url={target}"' in html and f'href="https://xcskilabs.com{target}"' in html


def test_no_stale_chapter_dirs_survive_a_rebuild():
    content = _content()
    keep = {c["id"] for c in content["chapters"]} | set(content["retired_chapters"])
    assert {p.name for p in OUTPUT_GUIDE.iterdir() if p.is_dir()} == keep


def test_cleanup_removes_only_pages_the_guide_wrote(tmp_path):
    out = tmp_path / "guide"
    stale = out / "dropped-chapter"
    stale.mkdir(parents=True)
    (stale / "index.html").write_text("<html>" + gg.GUIDE_MARKER + "</html>")
    other = out / "vasaloppet"  # e.g. a wrong --output-dir pointing at the site root
    other.mkdir()
    (other / "index.html").write_text("<html>race page</html>")
    gg.generate(out)
    assert not stale.exists()
    assert (other / "index.html").read_text() == "<html>race page</html>"
    assert (out / "the-gears" / "index.html").exists()


def test_retired_mapping_refuses_a_missing_target():
    bad = {"chapters": [{"id": "a"}], "retired_chapters": {"old": "nowhere"}}
    try:
        gg.retired_targets(bad)
    except ValueError:
        return
    raise AssertionError("a redirect to a missing chapter must refuse")


def test_unknown_block_type_refuses_instead_of_rendering_a_placeholder():
    try:
        gg.render_block({"type": "mystery"}, {"id": "x"}, {})
    except ValueError:
        return
    raise AssertionError("unsupported blocks must refuse")


def test_course_offer_is_hidden_until_the_course_is_live():
    content = _content()
    offer = content["course_offer"]
    if offer["live"]:
        last = _chapter_html(content["chapters"][-1])
        assert last.count("data-guide-offer") == 1 and f'href="{offer["href"]}"' in last
    else:
        for page in _guide_pages():
            html = page.read_text(encoding="utf-8")
            assert "data-guide-offer" not in html and 'href="/course/"' not in html, page


def test_course_offer_needs_live_to_be_exactly_true():
    content = _content()
    for value in ("false", "true", 1, None):
        content["course_offer"]["live"] = value
        assert gg.build_course_offer(content) == ""


def test_course_offer_renders_once_when_live():
    content = _content()
    content["course_offer"]["live"] = True
    html = gg.build_chapter_page(content["chapters"][-1], content)
    assert html.count("data-guide-offer") == 1 and 'href="/course/"' in html
    assert "data-guide-offer" not in gg.build_chapter_page(content["chapters"][0], content)
    assert gg.build_pillar(content).count("data-guide-offer") == 1


def test_the_guide_upsells_only_the_course():
    """Matti: the guide's one upsell is the course. No plan, coaching or product ladder."""
    for page in _guide_pages():
        html = page.read_text(encoding="utf-8")
        main = html[html.index('id="content"'):html.index("</main>")]
        for href in ("/questionnaire/", "/coaching/", "/training-plans/", "/consulting/"):
            assert f'href="{href}"' not in main, (page, href)
        assert "gl-ladder" not in html[html.index("</main>"):html.index("<footer")], page


def test_hero_and_block_loops_exist_and_captions_are_names_only():
    content = _content()
    techs = [content["hero_loop"]] + [c["hero_loop"] for c in content["chapters"]]
    techs += [t for c in content["chapters"] for s in c["sections"] for b in s["blocks"]
              if b["type"] == "technique_loops" for t in b["techniques"]]
    for t in techs:
        assert t in xsl_loops.LOOPS
    for page in _guide_pages():
        html = page.read_text(encoding="utf-8")
        caps = re.findall(r'<figcaption class="xsl-loop-cap">(.*?)</figcaption>', html)
        assert caps, page
        for cap in caps:
            assert re.fullmatch(r'<span class="xsl-loop-name">[^<]+</span>', cap), cap


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k not in ("id", "href", "url", "retired_chapters", "techniques", "hero_loop"):
                yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def test_every_string_in_the_content_is_in_my_voice():
    """All copy, including quiz feedback, titles, meta and the course offer, case-insensitively."""
    banned = (r"\bmatti?\b", r"\bcoach", r"\bAI\b", r"\bclaude\b", r"\bgpt\b", r"\bcodex\b",
              r"\bwe\b", r"\bour\b", r"\bus\b", "honestly", "\u2014", "\u2013")
    content = _content()
    texts = list(_strings({k: v for k, v in content.items() if k != "chapters"}))
    for ch in content["chapters"]:
        texts += [s for s in _strings({k: v for k, v in ch.items() if k != "sources"})]
    for text in texts:
        for pat in banned:
            flags = 0 if pat == r"\bAI\b" else re.I
            assert not re.search(pat, text, flags), (pat, text)


def test_every_loop_the_guide_uses_has_its_media():
    content = _content()
    techs = {content["hero_loop"]} | {c["hero_loop"] for c in content["chapters"]}
    techs |= {t for c in content["chapters"] for s in c["sections"] for b in s["blocks"]
              if b["type"] == "technique_loops" for t in b["techniques"]}
    for t in techs:
        shape = "square" if "square" in xsl_loops.shapes(t) else xsl_loops.shapes(t)[0]
        for f in xsl_loops.media_files(t, shape):
            assert f.exists() and f.stat().st_size > 0, f


def test_athlete_facing_copy_is_first_person_and_clean():
    banned = (r"\bMatt\b", r"\bMatti\b", r"\bcoach\b", r"\bAI\b", r"Claude", r"GPT", r"Codex",
              "honestly", "honest review", "—", "–", "&mdash;", "&ndash;")
    for page in _guide_pages():
        html = page.read_text(encoding="utf-8")
        main = _visible_text(html[html.index('id="content"'):html.index("</main>")])
        for pat in banned:
            assert not re.search(pat, main), (page, pat)
    raw = json.dumps(_content(), ensure_ascii=False)
    assert "—" not in raw and "–" not in raw


def test_every_inline_citation_resolves_to_rendered_source_link():
    marker_re = re.compile(r"\[\^([A-Za-z0-9_.-]+)\]")
    for chapter in _content()["chapters"]:
        html = _chapter_html(chapter)
        marker_ids = marker_re.findall(json.dumps(chapter))
        assert set(marker_ids) <= {s["id"] for s in chapter.get("sources", [])}
        for sid in marker_ids:
            assert f'href="#source-{sid}"' in html


def test_no_inline_onclick_in_guide_output():
    for path in OUTPUT_GUIDE.glob("**/index.html"):
        assert "onclick=" not in path.read_text(encoding="utf-8").lower(), path


def test_no_hex_outside_tokens_in_guide_output():
    color_re = re.compile(r"(?<!&)#[0-9a-fA-F]{3,6}")
    allowed = {m.group(0).lower() for m in color_re.finditer(TOKEN_CSS.read_text())}
    for path in OUTPUT_GUIDE.glob("**/index.html"):
        found = {m.group(0).lower() for m in color_re.finditer(path.read_text())}
        assert found <= allowed, (path, sorted(found - allowed))


def test_sitemap_lists_the_live_chapters_only():
    import generate_sitemap as gs
    xml, _ = gs.generate_sitemap("https://xcskilabs.com", [])
    xml = xml.decode()
    for ch in _content()["chapters"]:
        assert f"https://xcskilabs.com/guide/{ch['id']}/" in xml
    for old in OLD_CHAPTERS:
        assert f"/guide/{old}/" not in xml
        assert f"/guide/{old}/" not in (ROOT / "web" / "sitemap.xml").read_text(encoding="utf-8")


def test_guide_never_links_the_buyers_only_lessons():
    for path in OUTPUT_GUIDE.glob("**/index.html"):
        assert 'href="/learn/' not in path.read_text(encoding="utf-8"), path
