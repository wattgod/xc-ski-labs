"""Race tier names match Gravel God's and appear the same on every surface.

Gravel God (gravel-race-automation scripts/generate_llms_txt.py TIER_LABELS):
Tier 1 (Elite), Tier 2 (Contender), Tier 3 (Solid), Tier 4 (Roster).
scripts/tiers.py is the one mapping; nothing else defines tier names.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from tiers import TIER_NAMES, tier_badge, tier_label, tier_name  # noqa: E402

GRAVEL_GOD_TIER_LABELS = {
    1: "Tier 1 (Elite)",
    2: "Tier 2 (Contender)",
    3: "Tier 3 (Solid)",
    4: "Tier 4 (Roster)",
}

OLD_NAMES = re.compile(
    r"Tier [1-4] \((?:Strong|Developing)\)|T[1-4]=(?:strong|developing)|"
    r"the monuments|Must-Do Races|must-do races|niche picks",
)


def test_labels_match_gravel_god():
    assert {t: tier_label(t) for t in TIER_NAMES} == GRAVEL_GOD_TIER_LABELS


def test_names_and_badges():
    assert [tier_name(t) for t in (1, 2, 3, 4)] == ["Elite", "Contender", "Solid", "Roster"]
    assert tier_badge(1) == "TIER 1 · ELITE"
    assert tier_badge("4") == "TIER 4 · ROSTER"


@pytest.mark.parametrize("bad", [0, 5, None, "x"])
def test_unknown_tier_raises(bad):
    with pytest.raises(ValueError):
        tier_label(bad)


def test_no_generator_defines_its_own_tier_names():
    offenders = []
    for path in list((PROJECT_ROOT / "scripts").glob("*.py")) + list((PROJECT_ROOT / "wordpress").glob("*.py")):
        if path.name == "tiers.py":
            continue
        text = path.read_text(encoding="utf-8")
        if OLD_NAMES.search(text) or re.search(r"\{\s*1:\s*[\"'](?:TIER 1|Tier 1|Elite)", text):
            offenders.append(path.name)
    assert not offenders, offenders


def test_search_filter_buttons_use_the_mapping():
    html = (PROJECT_ROOT / "web" / "nordic-lab-search.html").read_text(encoding="utf-8")
    for t, name in TIER_NAMES.items():
        assert f'data-filter="t{t}">Tier {t} · {name}</button>' in html


def test_llms_txt_uses_gravel_god_labels(tmp_path):
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_llms_txt.py"), "--output-dir", str(tmp_path)],
        cwd=PROJECT_ROOT, check=True, capture_output=True, text=True,
    )
    text = "".join(p.read_text(encoding="utf-8") for p in tmp_path.glob("*.txt"))
    for label in GRAVEL_GOD_TIER_LABELS.values():
        assert label in text
    assert not OLD_NAMES.search(text)


def test_homepage_and_race_page_use_the_mapping(tmp_path):
    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_homepage.py"), "--output-dir", str(tmp_path)],
        cwd=PROJECT_ROOT, check=True, capture_output=True, text=True,
    )
    home = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "Tier 1 — Elite" in home
    assert not OLD_NAMES.search(home)

    subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "generate_race_pages.py"),
         "--output-dir", str(tmp_path), "--slug", "vasaloppet"],
        cwd=PROJECT_ROOT, check=True, capture_output=True, text=True,
    )
    race = (tmp_path / "vasaloppet" / "index.html").read_text(encoding="utf-8")
    assert re.search(r'gl-scorebox-tier">TIER [1-4] · (?:ELITE|CONTENDER|SOLID|ROSTER)<', race)
    assert re.search(r"Rated \d+/100, Tier [1-4] \((?:Elite|Contender|Solid|Roster)\), in ", race)
