#!/usr/bin/env python3
"""
recheck_official_sites.py — Re-read organizer pages and report what changed.

For each race whose dated edition has passed (or that has no dated edition),
fetch vitals.website, extract the next edition's date, status, distances,
entry fee and registration window with the cheap model, and report where the
page differs from the profile.

Report only. Nothing is written to race-data/. A finding is evidence for a
person or a gated fixer: profile edits still go through qc_new_profiles.py,
and a contested finding needs a second source (CLAUDE.md pitfalls 16 and 27).

Usage:
  python scripts/recheck_official_sites.py --dry-run            # list targets
  python scripts/recheck_official_sites.py --limit 40           # this week's 40; the window moves weekly
  python scripts/recheck_official_sites.py --slug vasaloppet --all
  python scripts/recheck_official_sites.py --limit 40 --out recheck

Output: <out>/recheck-report.json and <out>/recheck-report.md (default: data/recheck).

Requires: requests, OPENROUTER_API_KEY (not needed with --dry-run).
"""

import argparse
import json
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
# Not under output/: that directory is the deployed site.
DEFAULT_OUT_DIR = PROJECT_ROOT / "data" / "recheck"

MAX_HTML_CHARS = 100_000
FETCH_TIMEOUT_SECONDS = 20
USER_AGENT = "Mozilla/5.0 (compatible; race-date-recheck/1.0)"
DATE_FIELDS = ("next_edition_date", "registration_opens", "registration_closes")


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

_MONTH_NUMBERS = {name: i + 1 for i, name in enumerate([
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
])}


def edition_date(date_specific) -> tuple[int | None, int | None, int | None]:
    """(year, month, day) of a profile date such as "2027: March 7" or "2026-06-06".

    Any part that cannot be read is None. For a range ("June 26-27") the day is
    the first day.
    """
    text = str(date_specific or "")
    iso = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if iso:
        return int(iso.group(1)), int(iso.group(2)), int(iso.group(3))
    year_match = re.match(r"\s*(\d{4})\b", text) or re.search(r"\b(20\d{2})\b", text)
    year = int(year_match.group(1)) if year_match else None
    month = day = None
    month_match = re.search(r"\b(" + "|".join(_MONTH_NUMBERS) + r")\b\.?\s*(\d{1,2})?", text, re.IGNORECASE)
    if month_match:
        month = _MONTH_NUMBERS[month_match.group(1).lower()]
        day = int(month_match.group(2)) if month_match.group(2) else None
    return year, month, day


def is_stale_date(date_specific, today: date | None = None) -> bool:
    """True when the profile's dated edition has passed, or it names no year.

    A date with a year but no readable month counts as passed only once its
    year is over.
    """
    today = today or date.today()
    year, month, day = edition_date(date_specific)
    if year is None:
        return True
    if year != today.year:
        return year < today.year
    if month is None:
        return False
    return (month, day or 31) < (today.month, today.day)


# Month names as organizer sites write them (en, fr, it, es, de, nl, pt).
_MONTH_WORDS = {
    1: ["january", "jan", "janvier", "gennaio", "enero", "januar", "januari", "janeiro"],
    2: ["february", "feb", "février", "fevrier", "febbraio", "febrero", "februar", "februari", "fevereiro"],
    3: ["march", "mar", "mars", "marzo", "märz", "maerz", "maart", "março", "marco"],
    4: ["april", "apr", "avril", "aprile", "abril"],
    5: ["may", "mai", "maggio", "mayo", "mei", "maio"],
    6: ["june", "jun", "juin", "giugno", "junio", "juni", "junho"],
    7: ["july", "jul", "juillet", "luglio", "julio", "juli", "julho"],
    8: ["august", "aug", "août", "aout", "agosto", "augustus"],
    9: ["september", "sep", "sept", "septembre", "settembre", "septiembre", "setembro"],
    10: ["october", "oct", "octobre", "ottobre", "octubre", "oktober", "outubro"],
    11: ["november", "nov", "novembre", "noviembre", "novembro"],
    12: ["december", "dec", "décembre", "decembre", "dicembre", "diciembre", "dezember", "dezembro"],
}


def date_is_on_page(html: str, iso_date) -> bool:
    """True when the page itself shows this day, month and year as one date.

    A model can project last year's date forward and return a plausible date
    the organizer never published. Only a date written on the page is kept.
    The year must belong to the date: "7 March 2026. See you in 2027!" does
    not show 7 March 2027.
    """
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(iso_date or "").strip())
    if not m or not html:
        return False
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        date(year, month, day)
    except ValueError:
        return False
    text = re.sub(r"<[^>]+>", " ", html).lower()
    text = re.sub(r"\s+", " ", text)

    sep = r"\s?[-/.]\s?"
    d, mo = rf"0?{day}", rf"0?{month}"
    numeric = [
        rf"(?<!\d){year}{sep}{mo}{sep}{d}(?!\d)",
        rf"(?<!\d){d}{sep}{mo}{sep}{year}(?!\d)",
        rf"(?<!\d){mo}{sep}{d}{sep}{year}(?!\d)",
    ]
    if any(re.search(p, text) for p in numeric):
        return True

    words = "|".join(re.escape(w) for w in _MONTH_WORDS[month])
    day_first = rf"(?<!\d){d}(?:st|nd|rd|th|er|\.|º)?(?:\s(?:and|et|e|y|und|en|[-–&])\s?\d{{1,2}})?\s(?:de\s|of\s)?(?:{words})\b"
    month_first = rf"\b(?:{words})\.?\s(?:\d{{1,2}}(?:st|nd|rd|th)?\s?(?:and|[-–&,])\s?)?{d}(?!\d)"
    for match in re.finditer(rf"{day_first}|{month_first}", text):
        # The first year written after the date (or the one right before it) is the date's year.
        after = re.search(r"(?<!\d)(\d{4})(?!\d)", text[match.end(): match.end() + 16])
        if after:
            if int(after.group(1)) == year:
                return True
            continue
        before = re.search(r"(?<!\d)(\d{4})\W{1,3}$", text[max(0, match.start() - 8): match.start()])
        if before and int(before.group(1)) == year:
            return True
    return False


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------

def load_targets(slug: str | None = None, include_fresh: bool = False,
                 today: date | None = None) -> list[dict]:
    """Races to re-check, most overdue first.

    A race is a target when it has an HTTPS website and its dated edition has
    passed or it has no dated edition. Passed editions come before races with
    no date, so the weekly cap goes to dates that are known to be wrong.
    """
    targets = []
    for path in sorted(RACE_DATA_DIR.glob("*.json")):
        if path.name == "_schema.json":
            continue
        try:
            race = json.loads(path.read_text(encoding="utf-8")).get("race", {})
        except (json.JSONDecodeError, OSError):
            continue
        race_slug = race.get("slug", path.stem)
        if slug and race_slug != slug:
            continue
        vitals = race.get("vitals", {})
        website = vitals.get("website") or ""
        if not website.startswith("https://"):
            continue
        date_specific = vitals.get("date_specific")
        stale = is_stale_date(date_specific, today)
        if not stale and not include_fresh:
            continue
        targets.append({
            "slug": race_slug,
            "name": race.get("display_name") or race.get("name", race_slug),
            "website": website,
            "date_specific": date_specific,
            "distance_km": vitals.get("distance_km"),
            "discipline": vitals.get("discipline"),
            "has_date": bool(date_specific),
        })
    # Passed dated editions first (oldest first), then undated, then fresh.
    def order(t):
        year, month, day = edition_date(t["date_specific"])
        return (0 if t["has_date"] else 1, year or 9999, month or 0, day or 0, t["slug"])
    return sorted(targets, key=order)


def weekly_batch(targets: list[dict], limit: int, today: date | None = None) -> list[dict]:
    """This week's slice of the targets.

    A fixed "first N" would re-check the same races every week and never reach
    the rest, because a page with nothing new keeps its place. The window moves
    by `limit` each ISO week and wraps, so every target is reached in turn.
    """
    if limit <= 0 or not targets:
        return []
    if limit >= len(targets):
        return list(targets)
    year, week, _ = (today or date.today()).isocalendar()
    start = ((year * 53 + week) * limit) % len(targets)
    return [targets[(start + i) % len(targets)] for i in range(limit)]


# ---------------------------------------------------------------------------
# Fetch and extract
# ---------------------------------------------------------------------------

def _is_public_https(url: str) -> bool:
    """HTTPS to a named public host: not an IP address, localhost or a bare name."""
    from urllib.parse import urlsplit

    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
    except ValueError:
        return False
    if parts.scheme != "https" or "." not in host or host.endswith((".local", ".internal", ".localhost")):
        return False
    return not re.fullmatch(r"[\d.]+", host) and ":" not in host


def fetch_page(url: str) -> tuple[str | None, str | None]:
    """(html, None) on success, (None, reason) when the page cannot be read."""
    import requests

    try:
        response = requests.get(url, timeout=FETCH_TIMEOUT_SECONDS,
                                headers={"User-Agent": USER_AGENT})
    except requests.exceptions.RequestException as e:
        return None, type(e).__name__
    if response.status_code != 200:
        return None, f"http_{response.status_code}"
    # The profile URL is HTTPS; a redirect must not lead anywhere else.
    if not _is_public_https(response.url):
        return None, "redirected_off_public_https"
    if len(response.text) < 500:
        return None, "page_too_short"
    return response.text, None


def page_text_for_model(html: str) -> str:
    """The page with scripts and styles removed, capped for cost."""
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned[:MAX_HTML_CHARS]


def build_prompt(html: str, target: dict, today: date | None = None) -> str:
    today_iso = (today or date.today()).isoformat()
    return f"""Extract facts about the cross-country ski race "{target['name']}" from its official website HTML.
Today is {today_iso}.

OFFICIAL WEBSITE HTML:
{page_text_for_model(html)}

Return ONLY a JSON object with these fields (use null for anything the page does not state):
{{
  "next_edition_date": "YYYY-MM-DD of the next edition on or after today",
  "event_status": "scheduled|cancelled|postponed",
  "distances_km": [list of race distances in kilometres],
  "discipline": "classic|skate|both",
  "entry_fee": "price or price range with its currency",
  "registration_opens": "YYYY-MM-DD",
  "registration_closes": "YYYY-MM-DD",
  "registration_status": "open|closed|sold_out|lottery|coming_soon"
}}

Rules:
- Only state what the page shows. Do not guess, and do not project a past year's date forward.
- A date needs its year written on the page next to it. For a multi-day event use the first day.
- event_status is "cancelled" or "postponed" only when the page says so for the next edition.
- "skate" covers freestyle and free technique. Use "both" only when the event has classic and skate races.
- Return valid JSON only, no explanation."""


def parse_json_reply(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


_ENUMS = {
    "event_status": {"scheduled", "cancelled", "postponed"},
    "discipline": {"classic", "skate", "both"},
    "registration_status": {"open", "closed", "sold_out", "lottery", "coming_soon"},
}


def _clean_facts(raw: dict) -> dict:
    """Keep only fields of the expected shape; the reply is model output built from a web page.

    Dates must be real calendar dates in YYYY-MM-DD. Enumerated fields must be
    one of their values. Free text is cut to a short plain string. Anything
    else becomes None, so a malformed reply can never crash the batch or carry
    page text into a report.
    """
    facts = {}
    for field in DATE_FIELDS:
        value = str(raw.get(field) or "").strip()
        try:
            facts[field] = date.fromisoformat(value).isoformat() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) else None
        except ValueError:
            facts[field] = None
    for field, allowed in _ENUMS.items():
        value = str(raw.get(field) or "").strip().lower()
        facts[field] = value if value in allowed else None
    distances = raw.get("distances_km")
    if isinstance(distances, (int, float)) and not isinstance(distances, bool):
        distances = [distances]
    facts["distances_km"] = [d for d in distances if isinstance(d, (int, float))
                             and not isinstance(d, bool) and 0 < d < 1000] if isinstance(distances, list) else []
    fee = raw.get("entry_fee")
    facts["entry_fee"] = (re.sub(r"[^\w\s.,:/€$£+()-]", "", str(fee))[:60].strip() or None) if fee else None
    return facts


def extract_facts(html: str, target: dict, today: date | None = None) -> dict:
    """Facts from one page, or {"error": ...}.

    A date is kept only when the page shows it; anything else moves to
    "unverified_dates" so a projected date can never reach a report as fact.
    """
    from cheap_llm import call_cheap_llm_with_usage

    try:
        reply, usage = call_cheap_llm_with_usage(
            build_prompt(html, target, today), script="recheck_official_sites",
            max_tokens=8000, reasoning_effort="low")
        facts = parse_json_reply(reply)
    except Exception as e:
        return {"error": str(e)}
    if not isinstance(facts, dict) or not facts:
        return {"error": "extraction did not return a JSON object with fields"}

    facts = _clean_facts(facts)
    today = today or date.today()

    unverified = {}
    for field in DATE_FIELDS:
        claimed = facts.get(field)
        if not claimed:
            continue
        if not date_is_on_page(html, claimed):
            unverified[field] = claimed
            facts[field] = None
        elif field == "next_edition_date" and date.fromisoformat(claimed) < today:
            # A past edition on an archive page is on the page but is not the next edition.
            facts[field] = None
    if unverified:
        facts["unverified_dates"] = unverified
    facts["extraction_model"] = usage.get("model")
    facts["extraction_cost_usd"] = usage.get("cost_usd")
    return facts


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------

def compare(target: dict, facts: dict) -> list[dict]:
    """Findings where the page differs from the profile. Empty when nothing does."""
    findings = []

    def add(kind, field, profile, site):
        findings.append({"slug": target["slug"], "kind": kind, "field": field,
                         "profile": profile, "site": site})

    status = str(facts.get("event_status") or "").lower()
    if status in ("cancelled", "postponed"):
        add(status.upper(), "event_status", None, status)

    site_date = facts.get("next_edition_date")
    if site_date:
        site_year, site_month, _ = edition_date(site_date)
        year, month, _ = edition_date(target["date_specific"])
        if not target["date_specific"]:
            add("NEW_DATE", "date_specific", None, site_date)
        elif year is None or site_year > year:
            add("STALE_DATE", "date_specific", target["date_specific"], site_date)
        elif site_year == year and month and site_month:
            shift = abs(month - site_month)
            if min(shift, 12 - shift) > 1:
                add("DATE_MISMATCH", "date_specific", target["date_specific"], site_date)

    profile_discipline = target.get("discipline")
    site_discipline = facts.get("discipline")
    if site_discipline in ("classic", "skate", "both") and profile_discipline \
            and site_discipline != profile_discipline:
        add("DISCIPLINE_MISMATCH", "discipline", profile_discipline, site_discipline)

    profile_km = target.get("distance_km")
    site_km = [d for d in (facts.get("distances_km") or []) if isinstance(d, (int, float)) and not isinstance(d, bool)]
    if site_km and isinstance(profile_km, (int, float)) and not isinstance(profile_km, bool):
        if not any(abs(d - profile_km) <= max(1.0, 0.05 * profile_km) for d in site_km):
            add("DISTANCE_MISMATCH", "distance_km", profile_km, sorted(site_km))

    return findings


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def build_markdown(results: list[dict]) -> str:
    findings = [f for r in results for f in r.get("findings", [])]
    unverified = [(r["slug"], r["facts"]["unverified_dates"]) for r in results
                  if r.get("facts", {}).get("unverified_dates")]
    failed = [r for r in results if r.get("error")]
    cost = sum(r.get("facts", {}).get("extraction_cost_usd") or 0 for r in results)

    lines = [f"Weekly re-check of official race sites: {len(results)} checked, "
             f"{len(findings)} finding(s), {len(failed)} could not be read. "
             f"Model cost ${cost:.3f}. Nothing was changed in `race-data/`.", ""]
    if findings:
        lines += ["| Race | Finding | Profile | Site |", "|---|---|---|---|"]
        lines += [f"| {f['slug']} | {f['kind']} | {f['profile']} | {f['site']} |" for f in findings]
        lines += ["", "Check the site, then edit the profile and run `scripts/qc_new_profiles.py --slug <slug>`.", ""]
    if unverified:
        lines += ["Dates the model returned that the page does not show (ignored):"]
        lines += [f"- {slug}: {dates}" for slug, dates in unverified]
        lines += [""]
    if failed:
        lines += ["Could not be read:"]
        lines += [f"- {r['slug']}: {r['error']}" for r in failed]
        lines += [""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def recheck(target: dict, today: date | None = None) -> dict:
    result = {"slug": target["slug"], "website": target["website"]}
    html, reason = fetch_page(target["website"])
    if html is None:
        result["error"] = f"fetch: {reason}"
        return result
    try:
        facts = extract_facts(html, target, today)
        if "error" in facts:
            result["error"] = f"extract: {facts['error']}"
            return result
        findings = compare(target, facts)
    except Exception as e:  # one bad page must not lose the rest of the batch
        result["error"] = f"recheck: {type(e).__name__}"
        return result
    result["facts"] = facts
    result["findings"] = findings
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Re-read organizer pages and report what changed")
    parser.add_argument("--dry-run", action="store_true", help="List targets; fetch and call nothing")
    parser.add_argument("--slug", help="Re-check a single race")
    parser.add_argument("--all", action="store_true", help="Include races whose date is still ahead")
    parser.add_argument("--limit", type=int, default=40, help="Maximum races to re-check (default: 40)")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between races (default: 1.0)")
    parser.add_argument("--out", default=str(DEFAULT_OUT_DIR), help="Directory for the report")
    args = parser.parse_args()

    targets = load_targets(slug=args.slug, include_fresh=args.all)
    dated = sum(1 for t in targets if t["has_date"])
    print(f"{len(targets)} target(s): {dated} with a passed date, {len(targets) - dated} with no dated edition")
    targets = weekly_batch(targets, args.limit)

    if args.dry_run:
        for t in targets:
            print(f"  {t['slug']}: {t['date_specific'] or 'no date'}  {t['website']}")
        return 0

    from cheap_llm import is_configured
    if not is_configured():
        print("OPENROUTER_API_KEY is not set; nothing was fetched or called.")
        return 2

    results = []
    for i, target in enumerate(targets):
        result = recheck(target)
        results.append(result)
        summary = result.get("error") or ", ".join(f["kind"] for f in result["findings"]) or "no change"
        print(f"[{i + 1}/{len(targets)}] {target['slug']}: {summary}")
        if i < len(targets) - 1:
            time.sleep(args.delay)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "recheck-report.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown = build_markdown(results)
    (out_dir / "recheck-report.md").write_text(markdown + "\n", encoding="utf-8")
    print()
    print(markdown)

    # A run where every page failed found nothing out; say so with the exit code.
    if results and all(r.get("error") for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
