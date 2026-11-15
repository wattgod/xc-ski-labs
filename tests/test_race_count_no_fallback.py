"""The training plans page never prints a guessed race count (no-fallbacks rule)."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("generate_training_plans", ROOT / "wordpress" / "generate_training_plans.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def test_counts_real_profiles():
    expected = len([p for p in (ROOT / "race-data").glob("*.json") if p.name != "_schema.json"])
    assert gen.count_race_profiles() == expected


def test_missing_race_data_refuses(tmp_path):
    with pytest.raises(SystemExit, match="race-data/ not found"):
        gen.count_race_profiles(tmp_path / "race-data")


def test_empty_race_data_refuses(tmp_path):
    (tmp_path / "_schema.json").write_text("{}")
    with pytest.raises(SystemExit, match="no race profiles"):
        gen.count_race_profiles(tmp_path)


def test_no_hardcoded_count_in_source():
    src = (ROOT / "wordpress" / "generate_training_plans.py").read_text(encoding="utf-8")
    assert "return 229" not in src and "return 227" not in src
