"""Regression coverage for the spine-first race-page overhaul."""

import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts" / "generate_race_pages.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location("race_page_overhaul_generator", GENERATOR_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _vasaloppet():
    return json.loads((ROOT / "race-data" / "vasaloppet.json").read_text(encoding="utf-8"))["race"]


def _birkebeinerrennet():
    return json.loads((ROOT / "race-data" / "birkebeinerrennet.json").read_text(encoding="utf-8"))["race"]


def test_spine_first_page_order_and_custom_first_offer():
    page = _load_generator().generate_page(_vasaloppet(), [_birkebeinerrennet()])

    ordered_markers = [
        'class="gl-breadcrumb"',
        'id="hero"',
        'id="rating"',
        'id="breakdown"',
        'class="gl-transition"',
        'id="training"',
        'id="deep-dive"',
    ]
    positions = [page.index(marker) for marker in ordered_markers]
    assert positions == sorted(positions)
    assert 'id="verdict"' not in page
    assert page.index("Custom plan") < page.index("1:1 coaching")
    assert "Training plans" not in page
    assert "VIDEO ENRICHMENT COMING SOON" not in page
    assert 'data-page-format="spine-v2-approved"' in page
    assert '"@type":"BreadcrumbList"' in page
    assert 'id="similar-races"' in page
    assert 'data-related-race="birkebeinerrennet"' in page


def test_rating_is_server_rendered_two_radar_and_click_explain():
    page = _load_generator().generate_page(_vasaloppet())

    assert page.count('class="gl-radar-polygon"') == 2
    assert 'id="gl-rating-panel-course"' in page
    assert 'id="gl-rating-panel-experience"' in page
    assert page.count('class="gl-rating-tile"') == 14
    assert 'role="tablist"' in page
    assert 'role="status" aria-live="polite"' in page
    assert "rating_criterion_click" in page
    assert "race_section_view" in page
    assert "related_race_click" in page
    assert ".gl-deep-dive > section[id]" in page
    assert ".gl-rating-panel[hidden] { display: none; }" in page


def test_rating_leads_with_group_verdicts_not_first_criterion():
    page = _load_generator().generate_page(_vasaloppet())

    assert page.count('class="gl-rating-summary"') == 2
    assert "Course &amp; conditions verdict" in page
    assert "Race experience verdict" in page
    assert '<button type="button" class="gl-rating-tile"' in page
    assert not re.search(r'<button[^>]+class="gl-rating-tile"[^>]+aria-pressed="true"', page)
    assert page.count('role="status" aria-live="polite" hidden') == 2


def test_rating_bumper_keeps_short_opening_with_followup():
    generator = _load_generator()
    assert generator._rating_bumper(
        "Relentless. Not one killer climb, but 90 kilometers of attrition. Extra detail."
    ) == "Relentless. Not one killer climb, but 90 kilometers of attrition."


def test_catalog_rating_summaries_are_present_and_compact():
    generator = _load_generator()
    violations = []
    for path in (ROOT / "race-data").glob("*.json"):
        if path.name == "_schema.json":
            continue
        race = json.loads(path.read_text(encoding="utf-8"))["race"]
        rating = race["nordic_lab_rating"]
        for group_id, _label, keys in generator.RATING_GROUPS:
            total = sum(
                max(0, min(5, generator._parse_score(rating.get(key)) or 0))
                for key in keys
            )
            summary = generator._rating_group_summary(race, group_id, total)
            if not summary or len(summary) > 220:
                violations.append(f"{path.stem}.{group_id} length={len(summary)}")
            if not re.search(r"\[\d+\]$", summary):
                violations.append(f"{path.stem}.{group_id} lacks citation marker")
    assert not violations, "\n".join(violations[:30])


def test_catalog_rating_claims_resolve_to_numbered_sources():
    generator = _load_generator()
    violations = []
    slop = re.compile(
        r"according to|assessment rings true|Wax Bench scores|"
        r"experts agree|studies show|many argue|widely regarded as|"
        r"stands as a testament|marks a pivotal moment|plays a vital role|"
        r"solidifies its position|underscores its significance|"
        r"\bAs\s+[^,:]{1,100}\s+(?:puts it|notes?|reports?|describes?|captures?)[,:]",
        re.IGNORECASE,
    )
    for path in (ROOT / "race-data").glob("*.json"):
        if path.name == "_schema.json":
            continue
        race = json.loads(path.read_text(encoding="utf-8"))["race"]
        sources = generator._source_entries(race)
        if not sources:
            violations.append(f"{path.stem} has no source registry")
            continue
        for _group_id, _label, keys in generator.RATING_GROUPS:
            for key in keys:
                score = max(0, min(5, generator._parse_score(
                    race["nordic_lab_rating"].get(key)
                ) or 0))
                explanation = generator._criterion_explanation(race, key, score)
                if slop.search(explanation):
                    violations.append(f"{path.stem}.{key} uses source/slop scaffolding")
                refs = [int(value) for value in re.findall(r"\[(\d+)\]", explanation)]
                if not refs:
                    violations.append(f"{path.stem}.{key} lacks citation marker")
                elif any(ref < 1 or ref > len(sources) for ref in refs):
                    violations.append(f"{path.stem}.{key} has unresolved marker {refs}")
        source_html = generator.build_sources(race)
        if 'id="xc-citation-1"' not in source_html:
            violations.append(f"{path.stem} source list is not numbered")
    assert not violations, "\n".join(violations[:30])


def test_rating_uses_nordic_schema_and_profile_evidence():
    page = _load_generator().generate_page(_vasaloppet())

    assert "Course &amp; conditions" in page
    assert "Race experience" in page
    assert "The primary distance is 90 km." in page
    assert "The field is listed at 16000 skiers." in page
    assert "gravel_god_rating" not in page
    assert "fondo_rating" not in page


def test_new_dynamic_copy_is_escaped():
    generator = _load_generator()
    race = _vasaloppet()
    race["display_name"] = '</h2><script>alert("x")</script>'
    race["course"]["grooming"] = '</span><script>alert("g")</script>'

    page = generator.generate_page(race)

    assert '</h2><script>alert("x")</script>' not in page
    assert '</span><script>alert("g")</script>' not in page
    assert "&lt;script&gt;alert" in page


def test_interactions_do_not_write_dynamic_html():
    source = GENERATOR_PATH.read_text(encoding="utf-8")
    assert ".innerHTML" not in source
    assert "onclick=" not in source
