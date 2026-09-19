from types import SimpleNamespace

from scripts import jev_client, jev_existence_triage


def test_existence_verdict_bands(monkeypatch):
    values = iter((0.9, 0.3, 0.5))
    monkeypatch.setattr(jev_client, "ask", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(jev_client, "noul", lambda *_args: SimpleNamespace(noul=next(values)))
    data = {"race": {"name": "Synthetic", "vitals": {}, "history": {}}}
    result = {"status": "SUSPICIOUS", "evidence_summary": "Synthetic evidence"}
    assert jev_existence_triage._row("a", data, result)["verdict"] == "reinforce_real"
    assert jev_existence_triage._row("a", data, result)["verdict"] == "reinforce_doubt"
    assert jev_existence_triage._row("a", data, result)["verdict"] == "unclear"


def test_unavailable_is_unclear(monkeypatch):
    monkeypatch.setattr(jev_client, "get_client", lambda: None)
    row = jev_existence_triage._row("a", {"race": {}}, {"status": "LIKELY"})
    assert row["real_probability"] is None
    assert row["verdict"] == "unclear"


def test_missing_results_dir_is_skipped(monkeypatch, tmp_path):
    monkeypatch.setattr(jev_existence_triage, "RESULTS", tmp_path / "missing")
    report = jev_existence_triage.run(SimpleNamespace(slug=None, limit=None))
    assert report["jev_available"] is False
    assert report["summary"]["skipped"] is True
