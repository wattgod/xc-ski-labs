"""XC Ski Labs goals funnel: /goals/ questionnaire+poster page and the
race-page goal card (ski version of Gravel God PR #397 / the GOAL_2027
season-review funnel). See wordpress/generate_goals.py and the
build_goal_card addition in scripts/generate_race_pages.py.
"""

import importlib.util
import json
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
WORDPRESS_DIR = PROJECT_ROOT / "wordpress"
RACE_DATA_DIR = PROJECT_ROOT / "race-data"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


goals = _load_module("generate_goals", WORDPRESS_DIR / "generate_goals.py")
race_pages = _load_module("generate_race_pages_goalcard", SCRIPTS_DIR / "generate_race_pages.py")


def _load_race(slug: str) -> dict:
    data = json.loads((RACE_DATA_DIR / f"{slug}.json").read_text(encoding="utf-8"))
    return data["race"]


# ── /goals/ page ────────────────────────────────────────────────────


class TestGoalsPage:
    def test_page_renders(self):
        html = goals.generate_page()
        assert "<!DOCTYPE html>" in html
        assert html.count("</html>") == 1

    def test_lives_at_its_own_url_and_is_findable(self):
        html = goals.generate_page()
        assert 'href="https://xcskilabs.com/goals/"' in html
        assert '<meta name="robots" content="index, follow">' in html

    def test_has_the_shared_ga4_property(self):
        html = goals.generate_page()
        assert "G-3JQLSQLPPM" in html

    def test_posts_to_the_shared_worker_with_the_xc_brand(self):
        html = goals.generate_page()
        assert "fueling-lead-intake.gravelgodcoaching.workers.dev" in html
        assert 'var BRAND = "xcskilabs"' in html
        assert 'var LEAD_SOURCE = "goal_2027"' in html

    def test_season_framing_is_a_ski_season_not_a_calendar_year(self):
        html = goals.generate_page()
        assert "So. 2025-26." in html
        assert "2026-27" in html
        # No bare "2027" goal-year framing carried over from the cycling copy.
        assert "your 2027 goal" not in html.lower()

    def test_no_ftp_or_training_numbers_are_asked(self):
        html = goals.generate_page()
        assert "ftp" not in html.lower()

    def test_no_exclamation_marks_in_visible_copy(self):
        html = goals.generate_page()
        # Strip <script> and <style> blocks: JS operators (!==, !=, !important)
        # and CSS are not "copy". What is left should be exclamation-free —
        # flat, deadpan register per the brand voice rule.
        stripped = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.S)
        stripped = re.sub(r"<style\b[^>]*>.*?</style>", "", stripped, flags=re.S)
        stripped = re.sub(r"<!--.*?-->", "", stripped, flags=re.S)
        stripped = re.sub(r"<!DOCTYPE[^>]*>", "", stripped, flags=re.I)
        assert "!" not in stripped

    def test_all_six_sections_present(self):
        html = goals.generate_page()
        assert html.count('class="gl-section"') == len(goals.SECTIONS)

    def test_results_screen_has_the_poster_canvas(self):
        html = goals.generate_page()
        assert 'id="poster-canvas"' in html
        assert 'id="results"' in html

    def test_offer_never_precedes_the_poster(self):
        html = goals.generate_page()
        poster_idx = html.index('id="poster-canvas"')
        offer_idx = html.index('class="gl-offer"')
        assert poster_idx < offer_idx

    def test_three_offer_variants_to_test(self):
        html = goals.generate_page()
        assert html.count('class="gl-offer" data-offer-variant="') == len(goals.OFFER["variants"]) == 3

    def test_offer_points_to_the_real_working_intake_not_a_dead_checkout(self):
        """XC Ski Labs has no live self-serve checkout (verified against
        data/stripe-products.json and the current /training-plans/ page:
        every CTA there also routes to this same manual, coach-mediated
        intake). The offer must point at a real destination, never a
        payment link that doesn't exist."""
        html = goals.generate_page()
        assert "/questionnaire/" in html
        assert "buy.stripe.com" not in html
        assert "checkout.stripe.com" not in html

    def test_honeypot_field_present(self):
        html = goals.generate_page()
        assert 'name="website"' in html
        assert 'class="gl-honeypot"' in html

    def test_privacy_link_present_in_footer(self):
        html = goals.generate_page()
        assert 'href="/privacy/"' in html

    def test_cookie_banner_is_wired_up_not_inert(self):
        html = goals.generate_page()
        assert 'getElementById("gl-cookie-accept")' in html
        assert 'getElementById("gl-cookie-decline")' in html
        assert "xl_consent=accepted" in html
        assert "xl_consent=declined" in html

    def test_cookie_buttons_meet_the_44px_touch_target_rule(self):
        html = goals.generate_page()
        assert "min-height: 44px" in re.search(
            r"\.gl-cookie-actions button \{[^}]*\}", html
        ).group(0)

    def test_reduced_motion_is_honored(self):
        html = goals.generate_page()
        assert "prefers-reduced-motion: reduce" in html
        assert "REDUCED_MOTION" in html


class TestGoalCardDeploySurfacing:
    """The page must actually be reachable through this repo's release path
    (deploy.py / preflight.py / the sitemap), not just render correctly."""

    def test_deploy_excludes_goals_from_race_page_sync(self):
        import sys
        deploy = _load_module("deploy_for_goals_test", SCRIPTS_DIR / "deploy.py")
        assert "goals" in deploy.NON_RACE_OUTPUT_DIRS

    def test_deploy_has_a_sync_goals_step(self):
        deploy = _load_module("deploy_for_goals_test2", SCRIPTS_DIR / "deploy.py")
        assert hasattr(deploy, "sync_goals")

    def test_preflight_excludes_goals_from_race_page_count(self):
        preflight_src = (SCRIPTS_DIR / "preflight.py").read_text(encoding="utf-8")
        assert '"goals"' in preflight_src

    def test_sitemap_includes_goals(self):
        sitemap_src = (SCRIPTS_DIR / "generate_sitemap.py").read_text(encoding="utf-8")
        assert "/goals/" in sitemap_src


class TestGoalsSectionFields:
    def test_every_field_kind_is_renderable(self):
        # render_sections()/render_modules() must not raise for any kind
        # used across the real question set.
        html = goals.render_sections() + goals.render_modules()
        assert "unknown field kind" not in html

    def test_five_whys_all_present(self):
        html = goals.render_sections()
        for name in goals.WHY_NAMES:
            assert f'name="{name}"' in html

    def test_habit_direction_swap_data_attrs_present(self):
        html = goals.render_sections()
        assert "data-lbl-reduce=" in html
        assert "data-ph-reduce=" in html

    def test_last_goal_result_lift_wired(self):
        html = goals.render_sections()
        assert 'data-lift-when="none"' in html
        assert 'data-lift="last_goal,last_goal_why"' in html


# ── Race-page goal card ─────────────────────────────────────────────


class TestGoalCard:
    def test_renders_for_a_race_with_a_parseable_date(self):
        race = _load_race("american-birkebeiner")
        html = race_pages.build_goal_card(race)
        assert 'id="goal-card"' in html
        assert "glGoalCardCompute" in html

    def test_hidden_by_default(self):
        race = _load_race("american-birkebeiner")
        html = race_pages.build_goal_card(race)
        assert '<section class="gl-goal-card" id="goal-card" data-measure-section="goal-card" hidden>' in html

    def test_links_into_the_goals_page_with_race_attribution(self):
        race = _load_race("american-birkebeiner")
        html = race_pages.build_goal_card(race)
        assert "/goals/?src=race&amp;race=american-birkebeiner" in html or \
               "/goals/?src=race&race=american-birkebeiner" in html

    def test_prep_kit_link_matches_the_sites_real_url_pattern(self):
        race = _load_race("american-birkebeiner")
        html = race_pages.build_goal_card(race)
        assert 'href="/race/american-birkebeiner/prep-kit/"' in html

    def test_ski_specific_copy_not_cycling_copy(self):
        assert "ski" in race_pages.GOAL_CARD_COPY["goal_lines"]["same"].lower() or \
               "Ski" in race_pages.GOAL_CARD_COPY["goal_lines"]["same"]
        assert "ride" not in json.dumps(race_pages.GOAL_CARD_COPY).lower()

    def test_five_goal_types_match_the_shared_workers_validation(self):
        # fueling-lead-intake/worker.js validates goal_type against
        # ^(finish|beat_time|race_it|same|bigger)$ for every brand — the
        # card's buttons must use exactly this set.
        allowed = {"finish", "beat_time", "race_it", "same", "bigger"}
        assert set(race_pages.GOAL_CARD_COPY["buttons"].keys()) == allowed
        assert set(race_pages.GOAL_CARD_COPY["goal_lines"].keys()) == allowed

    def test_multiday_event_end_date_is_the_last_day_not_the_first(self):
        # "2026: March 7-8" must give the card an end date of March 8, or
        # day two of the event would already read as "post" instead of
        # staying in "week" for the whole span.
        race = _load_race("american-birkebeiner")
        race = dict(race)
        race["vitals"] = dict(race["vitals"])
        race["vitals"]["date_specific"] = "2026: March 7-8"
        static_json = re.search(r"var D = (\{.*?\});", race_pages.build_goal_card(race)).group(1)
        static_data = json.loads(static_json)
        assert static_data["startISO"] == "2026-03-07"
        assert static_data["endISO"] == "2026-03-08"

    def test_no_date_returns_empty_string(self):
        race = _load_race("american-birkebeiner")
        race = dict(race)
        race["vitals"] = dict(race["vitals"])
        race["vitals"]["date_specific"] = "Cancelled"
        assert race_pages.build_goal_card(race) == ""

    def test_wired_into_the_full_page(self):
        race = _load_race("american-birkebeiner")
        html = race_pages.generate_page(race, [])
        assert 'id="goal-card"' in html


class TestParseDateSpecificEnd:
    def test_same_month_range(self):
        assert race_pages.parse_date_specific_end("2026: March 7-8") == "2026-03-08"

    def test_cross_month_range(self):
        assert race_pages.parse_date_specific_end("2026: January 31 - February 1") == "2026-02-01"

    def test_single_day_has_no_range(self):
        assert race_pages.parse_date_specific_end("2026: March 1") is None

    def test_unparseable_is_none(self):
        assert race_pages.parse_date_specific_end("Cancelled") is None


class TestGoalCardStateMath:
    """Pin the JS date arithmetic (glGoalCardCompute) by running the exact
    source through Node — same discipline as the ported Gravel God version,
    since this is date math, not brand copy, and was copied verbatim."""

    def _run(self, start, end, today):
        import subprocess
        script = race_pages.GOAL_CARD_STATE_JS + (
            f'\nconsole.log(JSON.stringify(glGoalCardCompute("{start}", "{end}", "{today}")));'
        )
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout.strip())

    def test_far(self):
        assert self._run("2027-03-01", "2027-03-01", "2026-09-27")["state"] == "far"

    def test_near(self):
        assert self._run("2026-10-17", "2026-10-17", "2026-09-27")["state"] == "near"

    def test_week_inside_multiday_event(self):
        computed = self._run("2026-10-01", "2026-10-05", "2026-10-03")
        assert computed["state"] == "week"

    def test_post(self):
        assert self._run("2026-09-01", "2026-09-01", "2026-09-27")["state"] == "post"

    def test_hidden_far_past(self):
        assert self._run("2026-01-01", "2026-01-01", "2026-09-27")["state"] == "hidden"

    def test_hidden_on_unparseable_dates(self):
        assert self._run("not-a-date", "not-a-date", "2026-09-27")["state"] == "hidden"
