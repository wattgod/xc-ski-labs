"""Regression tests for the SiteGround WAF-challenge handling in the immune
link checker (Roadie Labs 2026-07-22 incident: 18 false dead/money-path
findings that were all HTTP 202 bot-challenge responses).

Covers: challenge classification, retry budget, checker exit semantics, and
immune_check's parsing of the checker's output (including crash handling).

Also (#12) connection-level failures under WAF pressure — timeout / reset /
SSL / URLError — which must be retried and reported as inconclusive, never as
dead links; and (#15) the bounded worker pool's shared retry budget.
"""

from __future__ import annotations

import http.client
import io
import re
import socket
import ssl
import sys
import threading
import time
import urllib.error
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_links
import immune_check


class FakeResponse:
    def __init__(self, status: int, headers: dict[str, str] | None = None,
                 body: bytes = b"", content_type: str = "text/html"):
        self.status = status
        hdrs = {"Content-Type": content_type}
        hdrs.update(headers or {})
        self.headers = hdrs
        self._body = body

    def read(self, n: int = -1) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


# ── Challenge classification ─────────────────────────────────────────────────
def test_202_is_challenged_not_dead(monkeypatch):
    monkeypatch.setattr(check_links.urllib.request, "urlopen",
                        lambda req, timeout=15: FakeResponse(202, {"sg-captcha": "challenge"}))
    status, _, challenged = check_links.fetch_once("https://xcskilabs.com/x/")
    assert status == 202 and challenged


def test_404_with_sg_captcha_header_is_dead_not_challenged(monkeypatch):
    err = urllib.error.HTTPError(
        "https://xcskilabs.com/x/", 404, "Not Found",
        {"sg-captcha": "challenge"}, io.BytesIO(b""))
    def raise_it(req, timeout=15):
        raise err
    monkeypatch.setattr(check_links.urllib.request, "urlopen", raise_it)
    status, _, challenged = check_links.fetch_once("https://xcskilabs.com/x/")
    assert status == 404 and not challenged


def test_200_is_clean(monkeypatch):
    monkeypatch.setattr(check_links.urllib.request, "urlopen",
                        lambda req, timeout=15: FakeResponse(200, body=b"<html></html>"))
    status, _, challenged = check_links.fetch_once("https://xcskilabs.com/")
    assert status == 200 and not challenged


# ── Retry budget ─────────────────────────────────────────────────────────────
def test_retry_backoff_consumes_budget(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(check_links.time, "sleep", sleeps.append)
    monkeypatch.setattr(check_links, "fetch_once",
                        lambda url, timeout=15: (202, "", True))
    monkeypatch.setattr(check_links, "_challenge_budget",
                        check_links.CHALLENGE_RETRY_BUDGET)
    status, _, challenged = check_links.fetch("https://xcskilabs.com/x/")
    assert challenged
    assert sleeps == list(check_links.CHALLENGE_BACKOFF)
    assert check_links._challenge_budget == \
        check_links.CHALLENGE_RETRY_BUDGET - sum(check_links.CHALLENGE_BACKOFF)


def test_exhausted_budget_skips_sleeping(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(check_links.time, "sleep", sleeps.append)
    monkeypatch.setattr(check_links, "fetch_once",
                        lambda url, timeout=15: (202, "", True))
    monkeypatch.setattr(check_links, "_challenge_budget", 5)
    status, _, challenged = check_links.fetch("https://xcskilabs.com/x/")
    assert challenged and sleeps == []


def test_incident_pattern_fits_subprocess_timeout():
    """18 persistently challenged URLs (the Jul 22 pattern) must not be able
    to sleep past immune_check's 900s subprocess timeout."""
    assert check_links.CHALLENGE_RETRY_BUDGET + 300 < 900


# ── Connection-level failures are inconclusive, not dead (#12) ───────────────
# 2026-08-31: `ERR https://xcskilabs.com/race/stafettvasan/` was reported as a
# dead-link while 242 sibling URLs were WAF-challenged in the same run; the
# URL curled 202 three times. fetch_once's bare `except Exception` had turned a
# socket timeout into status 0 / not-challenged, skipping the retry budget.
@pytest.mark.parametrize("exc", [
    socket.timeout("timed out"),
    TimeoutError("timed out"),
    ConnectionResetError(54, "Connection reset by peer"),
    ssl.SSLError(1, "SSL handshake failed"),
    urllib.error.URLError("[Errno 8] nodename nor servname provided"),
    http.client.RemoteDisconnected("Remote end closed connection without response"),
    http.client.IncompleteRead(b""),
], ids=lambda e: type(e).__name__)
def test_transport_failure_is_inconclusive_not_dead(monkeypatch, exc):
    def raise_it(req, timeout=15):
        raise exc
    monkeypatch.setattr(check_links.urllib.request, "urlopen", raise_it)
    status, _, inconclusive = check_links.fetch_once("https://xcskilabs.com/race/stafettvasan/")
    assert status == 0 and inconclusive


def test_non_transport_exception_is_still_dead(monkeypatch):
    """A failure that is NOT the network (e.g. a malformed URL) stays a real
    ERR/dead result — only transport noise was reclassified."""
    def raise_it(req, timeout=15):
        raise ValueError("unknown url type")
    monkeypatch.setattr(check_links.urllib.request, "urlopen", raise_it)
    status, _, inconclusive = check_links.fetch_once("https://xcskilabs.com/x/")
    assert status == 0 and not inconclusive


def test_socket_timeout_is_retried_then_recovers(monkeypatch):
    """A socket.timeout on the first attempt draws from CHALLENGE_BACKOFF and the
    retry's clean 200 is the final answer."""
    sleeps: list[float] = []
    monkeypatch.setattr(check_links.time, "sleep", sleeps.append)
    monkeypatch.setattr(check_links, "_challenge_budget", check_links.CHALLENGE_RETRY_BUDGET)
    attempts = iter([socket.timeout("timed out"), FakeResponse(200, body=b"<html></html>")])

    def urlopen(req, timeout=15):
        result = next(attempts)
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr(check_links.urllib.request, "urlopen", urlopen)
    status, _, inconclusive = check_links.fetch("https://xcskilabs.com/race/stafettvasan/")
    assert status == 200 and not inconclusive
    assert sleeps == [check_links.CHALLENGE_BACKOFF[0]]


def _run_main(monkeypatch, urlopen, seeded: set[str]):
    """Drive check_links.main() offline: no sitemap/generator/race-data reads,
    a fake urlopen, no real sleeping, a fresh retry budget, default workers."""
    monkeypatch.setattr(check_links, "load_sitemap_urls", lambda delay: (seeded, "local", None))
    monkeypatch.setattr(check_links, "extract_generator_hrefs", lambda: set())
    monkeypatch.setattr(check_links, "race_sample_from_sitemap", lambda urls, n: [])
    monkeypatch.setattr(check_links.time, "sleep", lambda s: None)
    monkeypatch.setattr(check_links, "_challenge_budget", check_links.CHALLENGE_RETRY_BUDGET)
    monkeypatch.setattr(check_links.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(sys, "argv", ["check_links.py", "--race-sample-size", "0", "--delay", "0"])
    return check_links.main()


def test_persistent_timeout_lands_in_waf_block_not_dead(monkeypatch, capsys):
    """End to end: a URL that times out on every attempt is printed as ERR in
    the WAF-CHALLENGED block (rc 2), never under DEAD LINKS (rc 1), and
    immune_check reads it as live-check-challenged, not dead-link."""
    flaky = "https://xcskilabs.com/race/stafettvasan/"

    def urlopen(req, timeout=15):
        if req.full_url == flaky:
            raise socket.timeout("timed out")
        return FakeResponse(200, body=b"<html></html>")
    rc = _run_main(monkeypatch, urlopen, {flaky})
    out = capsys.readouterr().out
    assert rc == 2
    assert "DEAD LINKS" not in out
    assert re.search(r"^\s+ERR\s+" + re.escape(flaky) + r"$", out, re.M), out
    findings = parse(monkeypatch, out, rc)
    assert [f.code for f in findings] == ["live-check-challenged"]
    assert flaky in findings[0].detail


def test_real_404_is_still_dead_with_worker_pool(monkeypatch, capsys):
    """The pool must not change classification: an HTTPError 404 is a dead link."""
    gone = "https://xcskilabs.com/race/gone/"

    def urlopen(req, timeout=15):
        if req.full_url == gone:
            raise urllib.error.HTTPError(gone, 404, "Not Found", {}, io.BytesIO(b""))
        return FakeResponse(200, body=b"<html></html>")
    rc = _run_main(monkeypatch, urlopen, {gone})
    out = capsys.readouterr().out
    assert rc == 1
    assert re.search(r"^\s+404\s+" + re.escape(gone) + r"$", out, re.M), out
    findings = parse(monkeypatch, out, rc)
    assert [f.code for f in findings] == ["dead-link"]


# ── Concurrent budget accounting (#15) ───────────────────────────────────────
def test_concurrent_budget_never_goes_negative(monkeypatch):
    """Workers hitting persistent challenges simultaneously share ONE retry
    budget. The locked check-and-decrement must refuse most of them once the
    budget is short, and the sum of reserved sleeps must equal what left the
    budget — never overspend, never go negative."""
    n_workers = 16
    start_budget = 100          # < 16 * 20: most first retries must be refused
    real_sleep = time.sleep     # captured BEFORE patching (check_links.time is the time module)
    reserved: list[int] = []
    reserved_lock = threading.Lock()

    def fake_sleep(pause):
        with reserved_lock:
            reserved.append(pause)
        real_sleep(0.005)       # yield so the workers actually interleave
    monkeypatch.setattr(check_links.time, "sleep", fake_sleep)
    monkeypatch.setattr(check_links, "fetch_once", lambda url, timeout=15: (202, "", True))
    monkeypatch.setattr(check_links, "_challenge_budget", start_budget)

    barrier = threading.Barrier(n_workers)

    def worker(i: int):
        barrier.wait()
        check_links.fetch(f"https://xcskilabs.com/{i}/")
    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert check_links._challenge_budget >= 0
    assert sum(reserved) <= start_budget
    assert sum(reserved) == start_budget - check_links._challenge_budget
    assert all(p in check_links.CHALLENGE_BACKOFF for p in reserved)


def test_worst_case_wall_clock_fits_subprocess_timeout():
    """Even if EVERY request burned its full socket timeout (site totally
    unresponsive), the bounded pool + shared sleep budget keep a default scan
    under immune_check's 900s subprocess budget. Serial worst-case terms:
    sitemap fetch + its retries, the seed sample (one pool round), the main
    loop rounds, the whole sleep budget spent serially, every budgeted retry
    fetch timing out, and the per-request jitter."""
    t = check_links.DEFAULT_TIMEOUT
    rounds = -(-check_links.DEFAULT_MAX_URLS // check_links.DEFAULT_WORKERS)
    retries = check_links.CHALLENGE_RETRY_BUDGET // min(check_links.CHALLENGE_BACKOFF)
    jitter = check_links.DEFAULT_MAX_URLS * 1.5 * check_links.DEFAULT_DELAY / check_links.DEFAULT_WORKERS
    worst = (t * (1 + len(check_links.CHALLENGE_BACKOFF))   # live sitemap + retries
             + t                                           # seed sample round
             + rounds * t                                  # main loop
             + check_links.CHALLENGE_RETRY_BUDGET           # all backoff sleeps, serial
             + retries * t                                 # every budgeted retry fetch
             + jitter)
    assert worst < 900, worst


# ── immune_check parsing of checker output ───────────────────────────────────
def parse(monkeypatch, stdout, returncode, stderr=""):
    fake = SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)
    monkeypatch.setattr(immune_check.subprocess, "run", lambda *a, **k: fake)
    return immune_check.run_live_link_check()


def test_mixed_waf_and_dead(monkeypatch):
    stdout = (
        "  WAF challenge on https://xcskilabs.com/a/ — retrying in 20s\n"
        "Sitemap source: https://xcskilabs.com/sitemap.xml\n"
        "Checked 9 of 10 live race sample pages\n"
        "\nWAF-CHALLENGED (2): still behind SiteGround's bot challenge after retries\n"
        "   202  https://xcskilabs.com/a/\n"
        "   202  https://xcskilabs.com/a/\n"
        "\nDEAD LINKS (2):\n"
        "   404  https://xcskilabs.com/questionnaire/\n"
        "   500  https://xcskilabs.com/some-page/\n")
    findings = parse(monkeypatch, stdout, 1)
    codes = [f.code for f in findings]
    assert codes.count("live-check-challenged") == 1
    assert "money-path-404" in codes and "dead-link" in codes
    assert "live-check-failed" not in codes
    challenged = next(f for f in findings if f.code == "live-check-challenged")
    assert "https://xcskilabs.com/a/" in challenged.detail
    assert challenged.lane == immune_check.YELLOW
    money = next(f for f in findings if f.code == "money-path-404")
    assert money.lane == immune_check.RED


def test_challenged_only_rc2(monkeypatch):
    stdout = (
        "\nWAF-CHALLENGED (1): still behind SiteGround's bot challenge after retries\n"
        "   202  https://xcskilabs.com/questionnaire/\n"
        "No dead links found, but the scan is INCONCLUSIVE (WAF challenges).\n")
    findings = parse(monkeypatch, stdout, 2)
    assert [f.code for f in findings] == ["live-check-challenged"]
    assert "questionnaire" in findings[0].detail


def test_crash_is_a_finding_not_silence(monkeypatch):
    findings = parse(monkeypatch, "", 3, stderr="Traceback (most recent call last): ...")
    assert [f.code for f in findings] == ["live-check-failed"]
    assert "Traceback" in findings[0].detail


def test_rc1_without_parsable_dead_lines_flags_drift(monkeypatch):
    findings = parse(monkeypatch, "SOMETHING UNEXPECTED\n", 1)
    assert [f.code for f in findings] == ["live-check-failed"]


def test_clean_run_yields_nothing(monkeypatch):
    findings = parse(monkeypatch, "All links alive.\n", 0)
    assert findings == []


# ── Fingerprint stability for volatile-detail findings ──────────────────────
def test_volatile_code_fingerprints_on_code_alone():
    """Findings with inherently volatile details (e.g. live-check-challenged with
    shifting WAF-challenged URL lists) must fingerprint on code alone, not detail,
    so they can stabilize against baseline.json even when the specific URLs change.
    """
    f1 = immune_check.Finding(
        "live-check-challenged", immune_check.YELLOW, "low",
        "Live Check Challenged by WAF",
        "12 URLs unverifiable: https://xcskilabs.com/a/ https://xcskilabs.com/b/",
        "WAF variance", None, "check_links")
    f2 = immune_check.Finding(
        "live-check-challenged", immune_check.YELLOW, "low",
        "Live Check Challenged by WAF", 
        "8 URLs unverifiable: https://xcskilabs.com/c/ https://xcskilabs.com/d/",
        "WAF variance", None, "check_links")
    assert immune_check.fingerprint(f1) == immune_check.fingerprint(f2) == "live-check-challenged"


def test_prep_kit_blocked_fingerprints_stable():
    """prep-kit-check-blocked (transport noise, no stable URL list) should also
    fingerprint on code alone."""
    f1 = immune_check.Finding(
        "prep-kit-check-blocked", immune_check.YELLOW, "low",
        "Prep-Kit Coverage Partially Blocked",
        "some kit URLs returned non-404 errors (WAF challenge / timeout) — coverage unverified for those",
        "Transport noise", None, "prep_kit_coverage")
    f2 = immune_check.Finding(
        "prep-kit-check-blocked", immune_check.YELLOW, "low",
        "Prep-Kit Coverage Partially Blocked",
        "different detail text here for variation",
        "Transport noise", None, "prep_kit_coverage")
    assert immune_check.fingerprint(f1) == immune_check.fingerprint(f2) == "prep-kit-check-blocked"


def test_normal_findings_still_fingerprint_with_detail():
    """Findings that don't have volatile details should continue using code::detail."""
    f1 = immune_check.Finding(
        "prep-kit-missing", immune_check.YELLOW, "high",
        "Prep kit missing: holmenkollen-skimaraton",
        "https://xcskilabs.com/race/holmenkollen-skimaraton/prep-kit/",
        "Generate the kit", None, "prep_kit_coverage")
    f2 = immune_check.Finding(
        "prep-kit-missing", immune_check.YELLOW, "high",
        "Prep kit missing: vasaloppet",
        "https://xcskilabs.com/race/vasaloppet/prep-kit/",
        "Generate the kit", None, "prep_kit_coverage")
    fp1 = immune_check.fingerprint(f1)
    fp2 = immune_check.fingerprint(f2)
    # Different races should have different fingerprints
    assert fp1 != fp2
    assert fp1 == "prep-kit-missing::https://xcskilabs.com/race/holmenkollen-skimaraton/prep-kit/"
    assert fp2 == "prep-kit-missing::https://xcskilabs.com/race/vasaloppet/prep-kit/"


def test_second_scan_with_different_challenged_urls_is_not_new(monkeypatch):
    """End-to-end: two scans with different WAF-challenged URLs should produce the
    same fingerprint, so the second run marks new:false (the core bug being fixed)."""
    # First scan: 2 challenged URLs
    stdout1 = (
        "\nWAF-CHALLENGED (2): still behind SiteGround's bot challenge after retries\n"
        "   202  https://xcskilabs.com/a/\n"
        "   202  https://xcskilabs.com/b/\n")
    findings1 = parse(monkeypatch, stdout1, 2)
    assert len(findings1) == 1
    fp1 = immune_check.fingerprint(findings1[0])
    
    # Second scan: different 2 challenged URLs
    stdout2 = (
        "\nWAF-CHALLENGED (2): still behind SiteGround's bot challenge after retries\n"
        "   202  https://xcskilabs.com/c/\n"
        "   202  https://xcskilabs.com/d/\n")
    findings2 = parse(monkeypatch, stdout2, 2)
    assert len(findings2) == 1
    fp2 = immune_check.fingerprint(findings2[0])
    
    # Same fingerprint despite different URLs
    assert fp1 == fp2 == "live-check-challenged"
    
    # Simulate baseline acceptance: if first run's fingerprint is in baseline,
    # second run should be marked new:false
    baseline = {fp1}
    immune_check.mark_new(findings2, baseline)
    assert not findings2[0].new
