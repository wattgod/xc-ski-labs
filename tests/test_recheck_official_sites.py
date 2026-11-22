"""Tests for cheap_llm.py and recheck_official_sites.py. No network."""
from __future__ import annotations

import io
import json
import sys
import urllib.error
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
import cheap_llm  # noqa: E402
import recheck_official_sites as recheck  # noqa: E402
from cheap_llm import (  # noqa: E402
    CheapLLMError,
    build_request_body,
    call_cheap_llm,
    call_cheap_llm_with_usage,
    estimate_cost_usd,
)

WORKFLOW = (PROJECT_ROOT / ".github" / "workflows" / "weekly-date-recheck.yml").read_text(encoding="utf-8")
TODAY = date(2026, 11, 22)


def _reply(text='{"distance_mi": 100}', usage=None, finish="stop", model="thinkingmachines/inkling-2-mini"):
    return {
        "model": model,
        "choices": [{"message": {"content": text}, "finish_reason": finish}],
        "usage": usage if usage is not None else {"prompt_tokens": 10_000, "completion_tokens": 1_000},
    }


def _http_error(code):
    return urllib.error.HTTPError(cheap_llm.OPENROUTER_URL, code, "err", {}, io.BytesIO(b""))


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    for name in ("CHEAP_LLM_MODEL", "CHEAP_LLM_PROVIDERS", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"):
        monkeypatch.delenv(name, raising=False)


class TestRequestBody:
    def test_excludes_hosts_that_keep_prompts(self):
        body = build_request_body("hi", "m", 100, True)
        assert body["provider"] == {"data_collection": "deny"}
        assert body["response_format"] == {"type": "json_object"}
        assert body["usage"] == {"include": True}

    def test_pinned_providers_disable_fallback(self, monkeypatch):
        monkeypatch.setenv("CHEAP_LLM_PROVIDERS", "Alpha, Beta ,")
        provider = build_request_body("hi", "m", 100, False)["provider"]
        assert provider["order"] == ["Alpha", "Beta"]
        assert provider["allow_fallbacks"] is False

    def test_json_mode_off_omits_response_format(self):
        assert "response_format" not in build_request_body("hi", "m", 100, False)

    def test_reasoning_effort_is_sent_only_when_asked(self):
        assert "reasoning" not in build_request_body("hi", "m", 100, True)
        assert build_request_body("hi", "m", 100, True, "low")["reasoning"] == {"effort": "low"}

    def test_model_env_override(self, monkeypatch):
        assert cheap_llm.model_id() == cheap_llm.DEFAULT_MODEL
        monkeypatch.setenv("CHEAP_LLM_MODEL", "other/model")
        assert cheap_llm.model_id() == "other/model"


class TestCost:
    def test_price_table_matches_listed_rate(self):
        cost = estimate_cost_usd("thinkingmachines/inkling-2-mini",
                                 {"prompt_tokens": 10_000, "completion_tokens": 1_000})
        assert cost == pytest.approx(0.00105)

    def test_reported_cost_wins(self):
        assert estimate_cost_usd("thinkingmachines/inkling-2-mini", {"cost": 0.5, "prompt_tokens": 1}) == 0.5

    def test_unknown_model_without_reported_cost_is_unknown(self):
        assert estimate_cost_usd("nobody/unknown", {"prompt_tokens": 5}) is None


class TestCall:
    def test_missing_key_fails_loudly(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY")
        with pytest.raises(CheapLLMError, match="OPENROUTER_API_KEY"):
            call_cheap_llm("hi", script="t")

    def test_returns_text_and_usage(self):
        with patch.object(cheap_llm, "_post", return_value=_reply()) as post:
            text, usage = call_cheap_llm_with_usage("hi", script="t")
        assert text == '{"distance_mi": 100}'
        assert usage["model"] == "thinkingmachines/inkling-2-mini"
        assert usage["cost_usd"] == pytest.approx(0.00105)
        assert post.call_args[0][1] == "test-key"

    def test_retries_then_succeeds(self):
        with patch.object(cheap_llm, "_post", side_effect=[_http_error(429), _reply()]) as post, \
             patch.object(cheap_llm.time, "sleep") as sleep:
            assert call_cheap_llm("hi", script="t") == '{"distance_mi": 100}'
        assert post.call_count == 2
        sleep.assert_called_once()

    def test_auth_error_is_not_retried(self):
        with patch.object(cheap_llm, "_post", side_effect=_http_error(401)) as post, \
             patch.object(cheap_llm.time, "sleep"):
            with pytest.raises(CheapLLMError, match="401"):
                call_cheap_llm("hi", script="t")
        assert post.call_count == 1

    def test_gives_up_after_max_retries(self):
        with patch.object(cheap_llm, "_post", side_effect=_http_error(503)) as post, \
             patch.object(cheap_llm.time, "sleep"):
            with pytest.raises(CheapLLMError, match="after 3 attempts"):
                call_cheap_llm("hi", script="t")
        assert post.call_count == 3

    def test_error_object_in_200_is_retried(self):
        with patch.object(cheap_llm, "_post", side_effect=[{"error": {"message": "upstream down"}}, _reply()]), \
             patch.object(cheap_llm.time, "sleep"):
            assert call_cheap_llm("hi", script="t")

    def test_truncated_reply_is_an_error(self):
        with patch.object(cheap_llm, "_post", return_value=_reply(finish="length")):
            with pytest.raises(CheapLLMError, match="cut off"):
                call_cheap_llm("hi", script="t")

    def test_empty_reply_is_an_error(self):
        with patch.object(cheap_llm, "_post", return_value=_reply(text="  ")):
            with pytest.raises(CheapLLMError, match="empty"):
                call_cheap_llm("hi", script="t")

    def test_no_cost_log_without_supabase(self):
        with patch.object(cheap_llm, "_post", return_value=_reply()), \
             patch.object(cheap_llm.urllib.request, "urlopen") as urlopen:
            call_cheap_llm("hi", script="t")
        urlopen.assert_not_called()

    def test_cost_log_row(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://db.example")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc")
        with patch.object(cheap_llm, "_post", return_value=_reply()), \
             patch.object(cheap_llm.urllib.request, "urlopen") as urlopen:
            call_cheap_llm("hi", script="scrape_official_sites")
        request = urlopen.call_args[0][0]
        row = json.loads(request.data)
        assert request.full_url == "https://db.example/rest/v1/gg_api_usage"
        assert row == {"provider": "openrouter", "model": "thinkingmachines/inkling-2-mini",
                       "tokens_in": 10_000, "tokens_out": 1_000, "cost_usd": 0.00105,
                       "script": "scrape_official_sites"}

    def test_cost_log_failure_does_not_break_the_call(self, monkeypatch):
        monkeypatch.setenv("SUPABASE_URL", "https://db.example")
        monkeypatch.setenv("SUPABASE_SERVICE_KEY", "svc")
        with patch.object(cheap_llm, "_post", return_value=_reply()), \
             patch.object(cheap_llm.urllib.request, "urlopen", side_effect=OSError("down")):
            assert call_cheap_llm("hi", script="t")


# ---------------------------------------------------------------------------
# recheck_official_sites.py
# ---------------------------------------------------------------------------

def _target(**over):
    base = {"slug": "test-loppet", "name": "Test Loppet", "website": "https://example.org",
            "date_specific": "2026: February 7", "distance_km": 50, "discipline": "classic",
            "has_date": True}
    return {**base, **over}


class TestStaleness:
    def test_passed_edition_is_stale(self):
        assert recheck.is_stale_date("2026: February 7", TODAY)

    def test_upcoming_edition_is_fresh(self):
        assert not recheck.is_stale_date("2027: March 7", TODAY)
        assert not recheck.is_stale_date("2026: December 14", TODAY)

    def test_no_date_is_stale(self):
        assert recheck.is_stale_date(None, TODAY)

    def test_range_reads_first_day(self):
        assert recheck.edition_date("2027: January 9-10") == (2027, 1, 9)


class TestTargets:
    def test_every_target_is_https_and_stale(self):
        targets = recheck.load_targets(today=TODAY)
        assert targets, "no targets found in race-data/"
        for t in targets:
            assert t["website"].startswith("https://")
            assert recheck.is_stale_date(t["date_specific"], TODAY)

    def test_passed_dates_come_before_undated(self):
        flags = [t["has_date"] for t in recheck.load_targets(today=TODAY)]
        assert flags == sorted(flags, reverse=True)

    def test_slug_filter(self):
        targets = recheck.load_targets(slug="vasaloppet", include_fresh=True, today=TODAY)
        assert [t["slug"] for t in targets] == ["vasaloppet"]


class TestDateIsOnPage:
    def test_formats(self):
        assert recheck.date_is_on_page("<b>07.03.2027</b>", "2027-03-07")
        assert recheck.date_is_on_page("Sunday, March 7, 2027", "2027-03-07")
        assert recheck.date_is_on_page("den 7. März 2027", "2027-03-07")

    def test_projected_date_is_rejected(self):
        assert not recheck.date_is_on_page("Race day was 1 March 2026. See you in 2027!", "2027-03-07")

    def test_wrong_year_is_rejected(self):
        assert not recheck.date_is_on_page("March 7, 2026", "2027-03-07")


class TestExtractFacts:
    PAGE = "<main>Vasaloppet 2027 takes place on March 7, 2027. 90 km classic.</main>" + " " * 600

    def _run(self, reply_json, page=None):
        with patch.object(cheap_llm, "_post", return_value=_reply(json.dumps(reply_json))) as post:
            facts = recheck.extract_facts(page or self.PAGE, _target(), TODAY)
        return facts, post

    def test_date_on_page_is_kept(self):
        facts, post = self._run({"next_edition_date": "2027-03-07", "distances_km": [90]})
        assert facts["next_edition_date"] == "2027-03-07"
        assert "unverified_dates" not in facts
        assert facts["extraction_model"] == "thinkingmachines/inkling-2-mini"
        body = post.call_args[0][0]
        assert body["max_tokens"] == 8000 and body["reasoning"] == {"effort": "low"}

    def test_invented_dates_are_parked(self):
        facts, _ = self._run({"next_edition_date": "2027-03-06", "registration_opens": "2026-12-01"})
        assert facts["next_edition_date"] is None and facts["registration_opens"] is None
        assert facts["unverified_dates"] == {"next_edition_date": "2027-03-06",
                                             "registration_opens": "2026-12-01"}

    def test_empty_object_is_an_error(self):
        facts, _ = self._run({})
        assert set(facts) == {"error"}

    def test_model_failure_is_an_error(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY")
        facts = recheck.extract_facts(self.PAGE, _target(), TODAY)
        assert set(facts) == {"error"}

    def test_prompt_states_today_and_forbids_projection(self):
        prompt = recheck.build_prompt(self.PAGE, _target(), TODAY)
        assert "Today is 2026-11-22." in prompt
        assert "do not project a past year's date forward" in prompt
        assert "<script" not in recheck.page_text_for_model("<script>x</script><p>ok</p>")


class TestCompare:
    def _kinds(self, facts, **target):
        return [f["kind"] for f in recheck.compare(_target(**target), facts)]

    def test_later_edition_is_stale_date(self):
        assert self._kinds({"next_edition_date": "2027-02-06"}) == ["STALE_DATE"]

    def test_profile_without_date_gets_new_date(self):
        assert self._kinds({"next_edition_date": "2027-02-06"}, date_specific=None, has_date=False) == ["NEW_DATE"]

    def test_same_year_same_month_is_no_finding(self):
        assert self._kinds({"next_edition_date": "2026-02-08"}) == []

    def test_same_year_month_shift_is_mismatch(self):
        assert self._kinds({"next_edition_date": "2026-11-28"}) == ["DATE_MISMATCH"]

    def test_older_site_date_is_no_finding(self):
        assert self._kinds({"next_edition_date": "2025-02-08"}) == []

    def test_cancelled_is_reported(self):
        assert self._kinds({"event_status": "cancelled"}) == ["CANCELLED"]

    def test_discipline_mismatch(self):
        assert self._kinds({"discipline": "skate"}) == ["DISCIPLINE_MISMATCH"]
        assert self._kinds({"discipline": "classic"}) == []
        assert self._kinds({"discipline": "nordic"}) == []

    def test_distance_matches_any_offered_distance(self):
        assert self._kinds({"distances_km": [25, 50.5]}) == []
        assert self._kinds({"distances_km": [25, 42]}) == ["DISTANCE_MISMATCH"]
        assert self._kinds({"distances_km": []}) == []

    def test_no_facts_no_findings(self):
        assert self._kinds({}) == []


class TestRecheckAndReport:
    def test_fetch_failure_is_an_error_row(self):
        with patch.object(recheck, "fetch_page", return_value=(None, "http_404")):
            result = recheck.recheck(_target(), TODAY)
        assert result["error"] == "fetch: http_404" and "findings" not in result

    def test_report_lists_findings_unverified_and_failures(self):
        results = [
            {"slug": "a", "facts": {"extraction_cost_usd": 0.002},
             "findings": [{"slug": "a", "kind": "STALE_DATE", "field": "date_specific",
                           "profile": "2026: February 7", "site": "2027-02-06"}]},
            {"slug": "b", "facts": {"unverified_dates": {"next_edition_date": "2027-03-06"},
                                    "extraction_cost_usd": 0.001}, "findings": []},
            {"slug": "c", "error": "fetch: http_404"},
        ]
        report = recheck.build_markdown(results)
        assert "3 checked, 1 finding(s), 1 could not be read" in report
        assert "| a | STALE_DATE | 2026: February 7 | 2027-02-06 |" in report
        assert "- b: {'next_edition_date': '2027-03-06'}" in report
        assert "- c: fetch: http_404" in report
        assert "$0.003" in report
        assert "Nothing was changed in `race-data/`" in report

    def test_missing_key_calls_nothing(self, monkeypatch, capsys):
        monkeypatch.delenv("OPENROUTER_API_KEY")
        monkeypatch.setattr("sys.argv", ["recheck_official_sites.py", "--limit", "1"])
        with patch.object(recheck, "recheck") as run:
            assert recheck.main() == 2
        run.assert_not_called()

    def test_dry_run_calls_nothing(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["recheck_official_sites.py", "--dry-run", "--limit", "2"])
        with patch.object(recheck, "recheck") as run:
            assert recheck.main() == 0
        run.assert_not_called()

    def test_every_page_failing_is_a_failed_run(self, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.argv", ["recheck_official_sites.py", "--limit", "2", "--delay", "0",
                                         "--out", str(tmp_path)])
        with patch.object(recheck, "fetch_page", return_value=(None, "ConnectionError")):
            assert recheck.main() == 1
        assert (tmp_path / "recheck-report.md").exists()


class TestWorkflow:
    def test_report_only(self):
        assert "contents: read" in WORKFLOW
        assert "git push" not in WORKFLOW and "git commit" not in WORKFLOW

    def test_fails_loudly_without_the_key(self):
        assert "OPENROUTER_API_KEY secret is not set" in WORKFLOW

    def test_runs_the_recheck_and_opens_an_issue(self):
        assert "scripts/recheck_official_sites.py" in WORKFLOW
        assert "gh issue create" in WORKFLOW
