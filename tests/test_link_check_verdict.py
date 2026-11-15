"""XC-10: an inconclusive link check must not read as a pass forever."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from link_check_verdict import previous_outcome, verdict  # noqa: E402

WORKFLOW = (PROJECT_ROOT / ".github" / "workflows" / "link-check.yml").read_text(encoding="utf-8")


def test_checked_passes():
    assert verdict(0, None)[0] == 0
    assert verdict(0, "inconclusive")[0] == 0


def test_dead_links_fail():
    assert verdict(1, None)[0] == 1


def test_one_inconclusive_run_warns_and_says_not_checked():
    code, summary = verdict(2, "checked")
    assert code == 0 and "NOT CHECKED" in summary


def test_second_inconclusive_run_in_a_row_fails():
    code, summary = verdict(2, "inconclusive")
    assert code == 1 and "two runs in a row" in summary


def test_missing_history_is_named_not_assumed():
    code, summary = verdict(2, None)
    assert code == 0 and "no record of the previous run" in summary


def test_unknown_exit_code_fails():
    assert verdict(3, None)[0] == 1


def test_previous_outcome_ignores_junk(tmp_path):
    p = tmp_path / "status.txt"
    assert previous_outcome(p) is None
    p.write_text("inconclusive\n")
    assert previous_outcome(p) == "inconclusive"
    p.write_text("garbage")
    assert previous_outcome(p) is None


def test_cli_writes_outcome_and_exit_code(tmp_path):
    prev = tmp_path / "prev.txt"
    prev.write_text("inconclusive\n")
    out = tmp_path / "out" / "status.txt"
    r = subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "link_check_verdict.py"),
                        "--rc", "2", "--previous", str(prev), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 1
    assert out.read_text().strip() == "inconclusive"
    assert "::error::" in r.stdout


def test_workflow_no_longer_swallows_exit_2():
    assert 'exit 0' not in WORKFLOW
    assert "link_check_verdict.py" in WORKFLOW
    assert "upload-artifact" in WORKFLOW and "link-check-status" in WORKFLOW
    assert "actions: read" in WORKFLOW
