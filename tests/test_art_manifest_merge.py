"""A single-slug race page build must not truncate art/manifest.json.

`generate_race_pages.py --slug <one>` used to call write_art_manifest()
with only the selected race, silently rewriting the tracked manifest from
229 entries down to 1 and destroying every other race's tier, source and
licence record. These tests pin the merge behaviour that fixes it.
"""

import importlib.util
import json
import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_MANIFEST = REPO_ROOT / "art" / "manifest.json"


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "gen_race_pages", REPO_ROOT / "scripts" / "generate_race_pages.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


gen = _load_generator()


def _seed_manifest(tmp_path) -> tuple[Path, dict]:
    """Copy the real 229-entry manifest into a throwaway art dir."""
    art_dir = tmp_path / "art"
    art_dir.mkdir()
    shutil.copy(REAL_MANIFEST, art_dir / "manifest.json")
    return art_dir, json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))


def test_real_manifest_still_has_229_entries():
    """Guard the guard: if the real manifest changes size, the numbers below
    need rechecking rather than silently passing."""
    manifest = json.loads(REAL_MANIFEST.read_text(encoding="utf-8"))
    assert len(manifest) == 229


def test_single_slug_write_preserves_every_other_entry(tmp_path):
    art_dir, original = _seed_manifest(tmp_path)
    slug = "alley-loop"
    assert slug in original

    gen.write_art_manifest(
        {slug: {"tier": "B", "source": "spot-check", "license": "Profile data"}},
        art_dir,
        merge=True,
    )

    after = json.loads((art_dir / "manifest.json").read_text(encoding="utf-8"))
    assert len(after) == 229, f"manifest truncated to {len(after)} entries"
    assert after[slug]["source"] == "spot-check", "selected race was not refreshed"
    untouched = {k: v for k, v in after.items() if k != slug}
    assert untouched == {k: v for k, v in original.items() if k != slug}


def test_full_build_still_replaces_the_manifest_wholesale(tmp_path):
    """Merging must not become the default: a full build is the authority and
    has to be able to drop races that no longer exist."""
    art_dir, _ = _seed_manifest(tmp_path)
    gen.write_art_manifest({"only-race": {"tier": "A"}}, art_dir)
    after = json.loads((art_dir / "manifest.json").read_text(encoding="utf-8"))
    assert after == {"only-race": {"tier": "A"}}


def test_generate_all_merges_only_for_single_slug_runs(tmp_path, monkeypatch):
    """Prove the wiring, not just the helper: generate_all must pass
    merge=True when --slug is used and merge=False for a full build."""
    seen = {}

    def fake_write(records, art_dir=None, *, merge=False):
        seen["count"] = len(records)
        seen["merge"] = merge

    monkeypatch.setattr(gen, "write_art_manifest", fake_write)

    gen.generate_all(REPO_ROOT / "race-data", tmp_path / "one", "alley-loop")
    assert seen == {"count": 1, "merge": True}

    gen.generate_all(REPO_ROOT / "race-data", tmp_path / "all", None)
    assert seen["merge"] is False
    assert seen["count"] == 229
