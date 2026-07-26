"""Regression coverage for the no-emoji public-surface estate rule."""

import importlib.util
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
sys.path.insert(0, str(SCRIPTS_DIR))

import generate_markdown_profiles
from text_utils import EMOJI_PATTERN, strip_emoji


def _race_page_generator():
    path = SCRIPTS_DIR / "generate_race_pages.py"
    spec = importlib.util.spec_from_file_location("generate_race_pages", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _profiles():
    return [
        json.loads(path.read_text(encoding="utf-8"))["race"]
        for path in sorted(RACE_DATA_DIR.glob("*.json"))
        if path.name != "_schema.json"
    ]


def test_strip_emoji_removes_covered_sequences_and_normalizes_whitespace():
    assert strip_emoji("Title  🇺🇸 ☀️ joined 👩\u200d🚀") == "Title joined"


def test_generated_markdown_mirrors_and_race_pages_contain_no_emoji():
    """Source data may contain emoji, but generated public text may not."""
    profiles = _profiles()
    page_generator = _race_page_generator()
    violations = []

    for race in profiles:
        slug = race["slug"]
        markdown = generate_markdown_profiles.generate_profile(
            slug, RACE_DATA_DIR, race_count=len(profiles)
        )
        page = page_generator.generate_page(race, profiles)
        for surface, content in (("markdown", markdown), ("race page", page)):
            match = EMOJI_PATTERN.search(content or "")
            if match:
                violations.append(f"{slug} {surface}: {match.group()!r}")

    assert not violations, "Emoji leaked onto generated public surfaces:\n" + "\n".join(violations)
