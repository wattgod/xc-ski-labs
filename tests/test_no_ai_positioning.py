"""Athlete-facing pages never position XC Ski Labs against AI.

Matti, 2026-11-14: "we never position ourselves against AI, never say we
don't use it, we just don't bring it up." Copy says what I do; it does not
compare me to AI, algorithms, software, apps or dashboards.

This test runs every page generator into its own temporary directory (some
generators treat --output-dir as the site root, others as their page's own
directory) and scans what it writes. The privacy policy generator is not run:
its processor disclosures are legal text and stay as written.
"""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Generators that accept --output-dir. generate_training_plans.py has no
# CLI flag and is run in-process below.
CLI_GENERATORS = [
    "scripts/generate_homepage.py",
    "scripts/generate_race_pages.py",
    "scripts/generate_prep_kit.py",
    "scripts/generate_guide.py",
    "scripts/generate_llms_txt.py",
    "scripts/generate_markdown_profiles.py",
    "wordpress/generate_about.py",
    "wordpress/generate_coaching.py",
    "wordpress/generate_coaching_apply.py",
    "wordpress/generate_consult_confirmed.py",
    "wordpress/generate_consult_intake.py",
    "wordpress/generate_consulting.py",
    "wordpress/generate_course.py",
    "wordpress/generate_exit_interview.py",
    "wordpress/generate_goals.py",
    "wordpress/generate_methodology.py",
    "wordpress/generate_questionnaire.py",
    "wordpress/generate_success.py",
    "wordpress/generate_terms.py",
]

BANNED = [
    ("standalone AI", re.compile(r"\bAI\b")),
    ("algorithm", re.compile(r"\balgorithm", re.IGNORECASE)),
    (
        "not-a-machine contrast",
        re.compile(
            r"\bnot (?:an? )?(?:AI|algorithm|bot|robot|app|software|dashboard|spreadsheet)\b",
            re.IGNORECASE,
        ),
    ),
    ("human-in-your-corner contrast", re.compile(r"\ba human (?:in your corner|who reads)", re.IGNORECASE)),
    ("read-by-a-person contrast", re.compile(r"\bread by a (?:person|human)\b", re.IGNORECASE)),
    ("software contrast", re.compile(r"\bsoftware flags\b", re.IGNORECASE)),
]


@pytest.fixture(scope="module")
def generated_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("no_ai_positioning")
    for rel in CLI_GENERATORS:
        gen_out = out / Path(rel).stem
        gen_out.mkdir()
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / rel), "--output-dir", str(gen_out)],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, f"{rel} failed: {result.stderr[-500:]}"

    wp_dir = str(PROJECT_ROOT / "wordpress")
    if wp_dir not in sys.path:
        sys.path.insert(0, wp_dir)
    spec = importlib.util.spec_from_file_location(
        "_tp_gen_for_ai_scan", PROJECT_ROOT / "wordpress" / "generate_training_plans.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.OUTPUT_DIR = out / "generate_training_plans"
    mod.generate_page()
    return out


def _scanned_files(root: Path):
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".html", ".txt", ".md", ".xml"}:
            continue
        yield path.relative_to(root).as_posix(), path


def test_generators_wrote_the_pages_this_test_guards(generated_dir):
    for rel in (
        "generate_homepage/index.html",
        "generate_coaching/coaching/index.html",
        "generate_coaching_apply/coaching/apply/index.html",
        "generate_consulting/consulting/index.html",
        "generate_training_plans/training-plans/index.html",
        "generate_llms_txt/llms.txt",
    ):
        assert (generated_dir / rel).is_file(), f"missing {rel}"


def test_no_ai_positioning_on_athlete_facing_pages(generated_dir):
    hits = []
    for rel, path in _scanned_files(generated_dir):
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in BANNED:
            for m in pattern.finditer(text):
                start = max(m.start() - 60, 0)
                hits.append(f"{rel}: {label}: ...{text[start:m.end() + 60]!r}")
    assert not hits, "AI positioning in athlete-facing copy:\n" + "\n".join(hits[:40])


@pytest.mark.parametrize(
    "line",
    [
        "Not an AI, not a dashboard.",
        "A human in your corner &mdash; not an AI.",
        "teach an algorithm what a person would see",
        "Every file, read by a person",
        "Software flags a number.",
    ],
)
def test_banned_patterns_catch_the_old_lines(line):
    assert any(p.search(line) for _, p in BANNED), line


def test_banned_patterns_allow_ordinary_words():
    for line in ("I read every file.", "Tail wind", "paid", "MAIN EVENT"):
        assert not any(p.search(line) for _, p in BANNED), line
