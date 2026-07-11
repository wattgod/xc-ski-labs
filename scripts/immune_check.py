#!/usr/bin/env python3
"""
XC Ski Labs — Immune System, Layer 1: deterministic verifier + lane classifier.

This is the "immune system's" senses. It does three things and NOTHING else:

  1. DETECT   — reuse preflight.py's static checks (score/tier math, schema,
                index & page parity, branding, security) plus a few extra
                immune-specific checks, and optionally the live 404 / money-path
                checker. Every problem becomes one structured Finding.
  2. CLASSIFY — sort each Finding into exactly one lane:
        GREEN  (auto-heal)  safe & mechanical — a regenerate/normalize fixes it
        YELLOW (needs you)  judgment — a fix is proposed, but a human approves
        RED    (issue only) unsafe to auto-fix — money path / security / systemic
  3. REPORT   — write immune/report.json, append a run record to
                immune/ledger.jsonl, and print a human digest.

IMPORTANT: this script never edits data, commits, or deploys. It is the *verifier*
the nightly repair loop checks its candidate fixes against — the Karpathy rule:
a candidate fix only ships if it makes this script go green WITHOUT turning
anything new red. Anything else becomes a PR (YELLOW) or an issue (RED).

Usage:
    python3 scripts/immune_check.py            # fast, offline: data + index checks
    python3 scripts/immune_check.py --regen     # regenerate output/ first, then also
                                                #   check pages / branding / homepage
    python3 scripts/immune_check.py --live       # also run the live money-path / 404 check
    python3 scripts/immune_check.py --json        # print machine JSON only (for the agent)

Exit code: 0 if no RED and no YELLOW findings, else 1 (so CI can gate on it).
"""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
IMMUNE_DIR = PROJECT_ROOT / "immune"
REPORT_FILE = IMMUNE_DIR / "report.json"      # latest snapshot (gitignored — churns every run)
SCANS_FILE = IMMUNE_DIR / "scans.jsonl"       # scan telemetry / streak (gitignored)
LEDGER_FILE = IMMUNE_DIR / "ledger.jsonl"     # permanent FIX log (tracked — the memory)

BRAND = "xc-ski-labs"
GREEN, YELLOW, RED = "green", "yellow", "red"

# Make preflight.py importable and reuse its logic (don't reinvent it).
sys.path.insert(0, str(SCRIPT_DIR))
import preflight  # noqa: E402


@dataclass
class Finding:
    code: str            # short stable slug, e.g. "index-drift"
    lane: str            # green | yellow | red
    severity: str        # critical | high | medium | low
    title: str           # one-line human summary
    detail: str          # the raw message / specifics
    remedy: str          # what a fix would do, in plain words
    auto_fix: str | None = None   # the exact safe command (GREEN only), else None
    source: str = "preflight"     # which detector raised it


# ── Classification table ──────────────────────────────────────────────────────
# Each rule: (regex on the raw message, code, lane, severity, remedy, auto_fix cmd)
# Ordered — first match wins. Unmatched errors default to YELLOW/high (a human
# decides), which is the safe direction: never auto-touch something we can't
# confidently classify.
REGEN_INDEX = "python3 scripts/generate_race_index.py"
REGEN_PAGES = "python3 scripts/generate_race_pages.py"
REGEN_HOME = "python3 scripts/generate_homepage.py"
NORMALIZE = "python3 scripts/normalize_profiles.py"

RULES: list[tuple[str, str, str, str, str, str | None]] = [
    # ── GREEN: safe, mechanical, deterministic regenerate/normalize ──
    (r"race-index\.json not found|Search index has \d+ races",
     "index-drift", GREEN, "high",
     "Search index is stale/missing — regenerate it from the profiles.", REGEN_INDEX),
    (r"Output has \d+ pages|output/ directory not found|Homepage missing",
     "pages-stale", GREEN, "high",
     "Generated pages are stale/missing — regenerate output/.", REGEN_PAGES),
    (r"Homepage shows \d+ (races|countries)",
     "homepage-stats-stale", GREEN, "low",
     "Homepage counters drifted from the data — regenerate the homepage.", REGEN_HOME),
    (r"video_id should be str",
     "video-id-type", GREEN, "low",
     "A YouTube video_id came back as a number — coerce to string.", NORMALIZE),
    # ── YELLOW: judgment — propose a fix, human approves (includes ALL ratings) ──
    (r"Score mismatch",
     "score-math", YELLOW, "high",
     "A race's overall_score doesn't equal its criteria sum. Proposed: recompute "
     "the score — but confirm the criteria are what you intended (a score IS a rating).",
     None),
    (r"Tier mismatch",
     "tier-math", YELLOW, "high",
     "A race's tier doesn't match its score/prestige rule. Proposed: recompute the "
     "tier — confirm the inputs.", None),
    (r"not in \[1,5\]|Missing criteria|Missing nordic_lab_rating",
     "rating-broken", YELLOW, "high",
     "A race's rating criteria are missing or out of range — needs a human rating call.",
     None),
    (r"Invalid JSON",
     "json-invalid", YELLOW, "critical",
     "A profile file is malformed JSON — needs a careful human fix (auto-repair could "
     "silently change data).", None),
    (r"slug .* != filename|Invalid slug format",
     "slug-mismatch", YELLOW, "high",
     "A profile's slug and filename disagree — renaming either affects live URLs, so "
     "a human decides.", None),
    (r"Missing '(name|display_name|tagline)'|Missing vitals\.",
     "missing-content", YELLOW, "high",
     "A race is missing required content (name/tagline/country/discipline) — a human "
     "fills it in.", None),
    (r"Invalid discipline",
     "bad-discipline", YELLOW, "medium",
     "A race has an invalid discipline value — a human sets classic/skate/both.", None),
    (r"Orphaned quote",
     "orphaned-quote", YELLOW, "medium",
     "A displayed quote points at a video that's no longer curated — a human removes "
     "or re-sources it (it's public copy).", None),
    (r"Duplicate slugs|Duplicate names",
     "duplicate-race", YELLOW, "high",
     "Two profiles look like the same event — a human picks the canonical one to keep.",
     None),
    # ── RED: unsafe to auto-fix, ever ──
    (r"\.env not in \.gitignore|hardcoded API key|Possible hardcoded API key",
     "security", RED, "critical",
     "Possible secret exposure — handle by hand, never auto-touch secrets.", None),
    (r"branded 'NORDIC LAB'|Title still says 'Nordic Lab'",
     "stale-branding", YELLOW, "medium",
     "Brand-name leak in a title (should be 'XC Ski Labs') — needs a generator edit.",
     None),
]


def classify(message: str, source: str = "preflight") -> Finding:
    for pattern, code, lane, severity, remedy, auto in RULES:
        if re.search(pattern, message):
            return Finding(code, lane, severity, code.replace("-", " ").title(),
                           message, remedy, auto, source)
    # Unknown error → safe default: a human looks at it.
    return Finding("unclassified", YELLOW, "high", "Unclassified issue",
                   message, "New kind of problem — a human should look and, once "
                   "understood, add a rule for it.", None, source)


# ── Detectors ─────────────────────────────────────────────────────────────────
def run_preflight(regen: bool) -> list[Finding]:
    """Run preflight's checks (swallowing its prints) and classify every error/warning."""
    result = preflight.PreflightResult()
    sink = io.StringIO()
    with redirect_stdout(sink):
        preflight.check_profiles(result)
        preflight.check_search_index(result)
        if regen or (PROJECT_ROOT / "output").exists():
            preflight.check_output_pages(result)
            preflight.check_branding(result)
            preflight.check_homepage_stats(result)
        preflight.check_security(result)
    findings = [classify(m) for m in result.errors]
    findings += [classify(m) for m in result.warnings]
    return findings


def check_money_path_wiring() -> list[Finding]:
    """Offline guard: the page generator must still emit the questionnaire CTA.
    If a future edit drops it, that's a money-path regression — RED, never auto."""
    gen = SCRIPT_DIR / "generate_race_pages.py"
    try:
        src = gen.read_text(encoding="utf-8")
    except OSError:
        return [Finding("money-path-generator-missing", RED, "critical",
                        "Money Path Generator Missing", str(gen),
                        "The race-page generator is unreadable — the money path can't "
                        "be verified.", None, "immune")]
    if "/questionnaire/" not in src:
        return [Finding("money-path-cta-dropped", RED, "critical",
                        "Money Path CTA Dropped",
                        "generate_race_pages.py no longer contains a /questionnaire/ CTA",
                        "The 'Build my plan' CTA vanished from the page generator — "
                        "restore it before deploying. Money path, so never auto-fixed.",
                        None, "immune")]
    return []


def check_fuzzy_duplicates() -> list[Finding]:
    """Catch near-duplicate events hiding under different slugs (e.g.
    traverse-du-massacre vs traversee-du-massacre).

    Primary signal is a HIGH fuzzy-similarity between event names — precise enough
    to avoid flagging a whole race series that merely shares one organizer website.
    Sharing a website only raises confidence; it never flags on its own."""
    from difflib import SequenceMatcher

    findings: list[Finding] = []
    profiles: list[tuple[str, dict]] = []
    for f in sorted(RACE_DATA_DIR.glob("*.json")):
        if f.name == "_schema.json":
            continue
        try:
            profiles.append((f.stem, json.loads(f.read_text(encoding="utf-8")).get("race", {})))
        except (OSError, json.JSONDecodeError):
            continue

    def canon(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (s or "").lower())

    def site_of(race: dict) -> str:
        return (race.get("vitals", {}).get("website") or "").strip().lower().rstrip("/")

    NAME_THRESHOLD = 0.88  # tuned: catches traverse/traversee (~0.96), skips series
    for i in range(len(profiles)):
        slug_a, race_a = profiles[i]
        name_a = canon(race_a.get("name") or slug_a)
        for j in range(i + 1, len(profiles)):
            slug_b, race_b = profiles[j]
            name_b = canon(race_b.get("name") or slug_b)
            ratio = SequenceMatcher(None, name_a, name_b).ratio()
            if ratio >= NAME_THRESHOLD:
                same_site = site_of(race_a) and site_of(race_a) == site_of(race_b)
                conf = "same website too" if same_site else "distinct websites"
                findings.append(Finding(
                    "duplicate-race", YELLOW, "high", "Near-Duplicate Name",
                    f"'{slug_a}' and '{slug_b}' names ~{int(ratio * 100)}% similar "
                    f"({conf})",
                    "Likely the same event under two slugs — a human merges/removes one.",
                    None, "immune"))
    return findings


def run_live_link_check() -> list[Finding]:
    """Run the existing live checker as a subprocess and parse its DEAD LINKS block.
    A dead link on the money path (/questionnaire/ or /coaching/) is a RED P0."""
    try:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "check_links.py"), "--max-urls", "300"],
            capture_output=True, text=True, timeout=900)
    except Exception as e:  # noqa: BLE001
        return [Finding("live-check-failed", YELLOW, "medium", "Live Check Failed",
                        str(e), "The live link checker couldn't run — check network/site.",
                        None, "check_links")]
    findings: list[Finding] = []
    in_dead = False
    for line in proc.stdout.splitlines():
        if line.startswith("DEAD LINKS"):
            in_dead = True
            continue
        if in_dead and line.strip():
            m = re.match(r"\s*(\d+|ERR)\s+(\S+)", line)
            if not m:
                continue
            status, url = m.group(1), m.group(2)
            money = "/questionnaire/" in url or "/coaching/" in url
            findings.append(Finding(
                "money-path-404" if money else "dead-link",
                RED if money else YELLOW,
                "critical" if money else "medium",
                "Money-Path 404" if money else "Dead Link",
                f"{status}  {url}",
                ("A conversion link a visitor clicks is dead — likely the questionnaire/"
                 "coaching dir isn't deployed or the cache wasn't purged. Money path, so "
                 "a human confirms the re-deploy.") if money else
                "A same-site link is dead — a human confirms the fix.",
                None, "check_links"))
    return findings


# ── Report + ledger ───────────────────────────────────────────────────────────
def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_outputs(findings: list[Finding], mode: dict) -> dict:
    IMMUNE_DIR.mkdir(exist_ok=True)
    lanes = {GREEN: 0, YELLOW: 0, RED: 0}
    for f in findings:
        lanes[f.lane] += 1
    report = {
        "brand": BRAND,
        "generated_at": now_iso(),
        "mode": mode,
        "counts": {"total": len(findings), **lanes},
        "findings": [asdict(f) for f in findings],
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    # Append a compact run record to the scan telemetry (gitignored; feeds the streak).
    # The permanent ledger.jsonl is reserved for type:"fix" records (the memory) so it
    # only changes when something is actually healed — no git noise from routine scans.
    run_record = {
        "ts": report["generated_at"], "type": "scan", "brand": BRAND,
        "mode": mode, "counts": report["counts"],
        "codes": sorted({f.code for f in findings}),
    }
    with SCANS_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(run_record) + "\n")
    return report


def print_digest(report: dict) -> None:
    findings = [Finding(**f) for f in report["findings"]]
    c = report["counts"]
    print("=" * 60)
    print(f"🩺 XC Ski Labs — Immune scan  ({report['generated_at']})")
    print(f"   mode: {report['mode']}")
    print("=" * 60)

    def block(lane, emoji, label):
        items = [f for f in findings if f.lane == lane]
        if not items:
            return
        print(f"\n{emoji} {label} ({len(items)})")
        for f in items:
            print(f"   • [{f.severity}] {f.title}: {f.detail}")
            print(f"       → {f.remedy}")
            if f.auto_fix:
                print(f"       ⤷ safe auto-fix: {f.auto_fix}")

    block(GREEN, "🟢", "AUTO-HEALABLE (the loop would fix these itself)")
    block(YELLOW, "🟡", "NEEDS YOU (a fix is proposed → PR for your approval)")
    block(RED, "🔴", "ISSUE ONLY (unsafe to auto-fix — money path / security / systemic)")

    print("\n" + "-" * 60)
    print(f"total {c['total']}  |  🟢 {c['green']}  🟡 {c['yellow']}  🔴 {c['red']}")
    if c["total"] == 0:
        print("🧬 All clear. Streak intact.")
    print("-" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="XC Ski Labs immune system — Layer 1 verifier")
    parser.add_argument("--regen", action="store_true",
                        help="regenerate output/ first (enables page/branding/homepage checks)")
    parser.add_argument("--live", action="store_true",
                        help="also run the live money-path / 404 check (network)")
    parser.add_argument("--json", action="store_true", help="print machine JSON only")
    parser.add_argument("--fail-on", choices=["red", "any"], default="any",
                        help="exit non-zero on RED only, or on any RED/YELLOW (default: any)")
    args = parser.parse_args()

    if args.regen:
        for cmd in (REGEN_INDEX, REGEN_PAGES, REGEN_HOME):
            subprocess.run(cmd.split(), cwd=PROJECT_ROOT, check=False,
                           stdout=subprocess.DEVNULL)

    findings: list[Finding] = []
    findings += run_preflight(args.regen)
    findings += check_money_path_wiring()
    findings += check_fuzzy_duplicates()
    if args.live:
        findings += run_live_link_check()

    mode = {"regen": args.regen, "live": args.live}
    report = write_outputs(findings, mode)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_digest(report)

    # Non-zero if anything needs attention, so CI / the agent can gate on it.
    if args.fail_on == "red":
        return 1 if report["counts"]["red"] else 0
    return 0 if report["counts"]["yellow"] == 0 and report["counts"]["red"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
