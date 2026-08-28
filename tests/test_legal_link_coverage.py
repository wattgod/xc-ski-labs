"""Trust and crawlability guards for public XC Ski Labs page families."""

import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_guide import build_chapter_page, build_pillar, load_content  # noqa: E402
from scripts.generate_race_pages import generate_page  # noqa: E402

FOOTER_OWNERS = (
    "scripts/generate_homepage.py",
    "scripts/generate_prep_kit.py",
    "scripts/generate_race_pages.py",
    "web/nordic-lab-search.html",
    "wordpress/generate_about.py",
    "wordpress/generate_coaching.py",
    "wordpress/generate_coaching_apply.py",
    "wordpress/generate_consulting.py",
    "wordpress/generate_methodology.py",
    "wordpress/generate_privacy.py",
    "wordpress/generate_questionnaire.py",
    "wordpress/generate_terms.py",
    "wordpress/generate_training_plans.py",
)


def test_every_public_footer_owner_links_both_legal_pages() -> None:
    for relative_path in FOOTER_OWNERS:
        source = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        footers = re.findall(r"<footer\b[^>]*>.*?</footer>", source, re.DOTALL)
        assert footers, f"{relative_path}: no page footer found"
        assert any('href="/privacy/"' in footer for footer in footers), (
            f"{relative_path}: page footer is missing Privacy"
        )
        assert any('href="/terms/"' in footer for footer in footers), (
            f"{relative_path}: page footer is missing Terms"
        )


def test_search_page_is_explicitly_indexable_and_canonical() -> None:
    html = (PROJECT_ROOT / "web/nordic-lab-search.html").read_text(encoding="utf-8")
    assert '<meta name="robots" content="index, follow">' in html
    assert '<link rel="canonical" href="https://xcskilabs.com/search/">' in html


def test_race_page_emits_a_self_canonical() -> None:
    profile = next(
        path for path in sorted((PROJECT_ROOT / "race-data").glob("*.json"))
        if path.name != "_schema.json"
    )
    import json

    race = json.loads(profile.read_text(encoding="utf-8"))["race"]
    html = generate_page(race, [race])
    assert f'<link rel="canonical" href="https://xcskilabs.com/race/{race["slug"]}/">' in html


def test_guide_pages_emit_self_canonicals() -> None:
    content = load_content()
    assert '<link rel="canonical" href="https://xcskilabs.com/guide/">' in build_pillar(content)
    chapter = content["chapters"][0]
    assert (
        f'<link rel="canonical" href="https://xcskilabs.com/guide/{chapter["id"]}/">'
        in build_chapter_page(chapter, content)
    )
