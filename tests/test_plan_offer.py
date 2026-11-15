"""Tests for the custom ski plan billed every 4 weeks.

Covers wordpress/plan_offer.py (numbers and offer lines), the v2 skier
questionnaire and buy button (wordpress/generate_questionnaire.py), the offer
on /training-plans/, the plan's success page and the terms paragraph.

The last class cross-checks against the checkout server's own code in
athlete-custom-training-plan-pipeline when that checkout sits next to this
one (~/athlete-custom-training-plan-pipeline); it is skipped elsewhere.
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORDPRESS_DIR = PROJECT_ROOT / "wordpress"
CATALOG = PROJECT_ROOT / "data" / "ski-event-catalog.json"
PIPELINE = Path.home() / "athlete-custom-training-plan-pipeline"

sys.path.insert(0, str(WORDPRESS_DIR))
import plan_offer  # noqa: E402
import generate_questionnaire as gq  # noqa: E402


@pytest.fixture(scope="module")
def questionnaire_html(tmp_path_factory) -> str:
    out = tmp_path_factory.mktemp("q")
    index = out / "race-index.json"
    index.write_text(json.dumps({"races": [
        {"s": "american-birkebeiner", "n": "American Birkebeiner"},
        {"s": "vasaloppet", "n": "Vasaloppet"},
    ]}), encoding="utf-8")
    gq.generate_page(out, index, CATALOG)
    return (out / "questionnaire" / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def page_config(questionnaire_html) -> dict:
    m = re.search(r'<script type="application/json" id="xc-plan-config">(.*?)</script>',
                  questionnaire_html, re.S)
    assert m, "questionnaire config block missing"
    return json.loads(m.group(1).replace("<\\/", "</"))


@pytest.fixture(scope="module")
def training_plans_html(tmp_path_factory) -> str:
    spec = importlib.util.spec_from_file_location(
        "gen_tp", WORDPRESS_DIR / "generate_training_plans.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = tmp_path_factory.mktemp("tp")
    mod.OUTPUT_DIR = out
    mod.generate_page()
    return (out / "training-plans" / "index.html").read_text(encoding="utf-8")


# Words rider-facing copy never uses (CLAUDE.md: Matti speaks in first person,
# no AI or automation, "every 4 weeks" not "monthly").
BANNED = re.compile(
    r"\bMatt\b|\bMatti\b|\byour coach\b|\bthe coach\b|\bCoach Matti\b|\bClaude\b|\bCodex\b"
    r"|\bGPT\b|\bAI\b|\bautomat\w*|\bgenerat\w*|\balgorithm\w*|\bmonthly\b|/\s?mo\b"
    r"|\bper month\b|\bnext race\b|\bauto-?sync\w*|\bsyncs?\b",
    re.I,
)


def _rider_lines() -> list[str]:
    lines = list(plan_offer.OFFER_LINES) + list(plan_offer.FIT_LINES)
    lines += [plan_offer.PRICE_LINE, plan_offer.TERMS_SHORT]
    lines += list(gq.REFUSALS.values()) + list(gq.ERRORS.values())
    lines += [gq.FORM_SUMMARY_ERROR, gq.SAVED_NOTE]
    return lines


class TestPaymentPlan:
    @pytest.mark.parametrize("weeks,count,total,first,last", [
        (1, 1, 1250, 1250, 1250),
        (3, 1, 3750, 3750, 3750),
        (4, 1, 4999, 4999, 4999),
        (5, 2, 6249, 4999, 1250),
        (15, 4, 18747, 4999, 3750),
        (16, 4, 19996, 4999, 4999),
        (52, 13, 64987, 4999, 4999),
    ])
    def test_blocks_and_short_last_block(self, weeks, count, total, first, last):
        plan = plan_offer.payment_plan(weeks)
        assert plan["payment_count"] == count
        assert plan["total_cents"] == total
        assert plan["first_payment_cents"] == first
        assert plan["payments_cents"][-1] == last

    @pytest.mark.parametrize("bad", [0, -1, 2.5, "4"])
    def test_rejects_non_weeks(self, bad):
        with pytest.raises(ValueError):
            plan_offer.payment_plan(bad)

    def test_money(self):
        assert plan_offer.money(4999) == "$49.99"
        assert plan_offer.money(1250) == "$12.50"
        assert plan_offer.money(18747) == "$187.47"

    def test_example_line_matches_the_math(self):
        assert "4 payments: 3 at $49.99 and one at $37.50, $187.47 in all" in plan_offer.NO_CAP_LINE


class TestRiderCopy:
    def test_offer_says_every_4_weeks(self):
        assert plan_offer.PRICE_LINE == "$49.99 every 4 weeks"
        assert "$12.50 a week" in plan_offer.LAST_BLOCK_LINE
        assert "14 days" in plan_offer.REFUND_LINE and "plan page" in plan_offer.REFUND_LINE
        assert "plan page" in plan_offer.CANCEL_LINE
        assert "race week" in plan_offer.ENDS_LINE
        assert "no cap" in plan_offer.NO_CAP_LINE

    @pytest.mark.parametrize("line", _rider_lines())
    def test_no_banned_words(self, line):
        assert not BANNED.search(line), line

    def test_contact_is_mattis_address(self):
        assert plan_offer.CONTACT_EMAIL == "gravelgodcoaching@gmail.com"

    def test_stale_offer_guard_catches_the_old_offer(self):
        old = "<p>$249 cap. $15 a week. One-time payment, no subscription. $50/mo, monthly.</p>"
        assert set(plan_offer.stale_offer_phrases(old)) >= {
            "$249", "$15 a week", "One-time payment", "no subscription", "/mo", "monthly"}
        assert plan_offer.stale_offer_phrases("<script>var a='monthly';</script><p>ok</p>") == []


class TestRefusals:
    def test_every_message_says_nothing_was_charged(self):
        for code, message in gq.REFUSALS.items():
            assert "Nothing was charged." in message, code

    def test_contact_placeholder_only_where_meant(self):
        for code, message in gq.REFUSALS.items():
            assert "{" not in message.replace("{contact}", ""), code

    def test_known_codes_have_messages(self):
        for code in ("offer_disabled", "live_stripe_key_refused", "plan_start_out_of_range",
                     "race_name_required", "juniors_not_built", "first_season_not_built",
                     "event_unknown", "event_facts_stale", "event_technique_mismatch",
                     "season_not_built", "plan_too_short", "plan_too_long", "no_test_mode",
                     "no_hard_dryland_modality", "no_easy_dryland_modality", "rest_days",
                     "ski_gate_failed", "ski_intake_invalid", "email_invalid",
                     "name_required", "rate_limited", "network"):
            assert code in gq.REFUSALS, code

    def test_unknown_codes_fall_back_to_the_invalid_message(self, questionnaire_html):
        assert "if (reason && CFG.refusals[reason]) return reason;" in questionnaire_html
        assert "return 'ski_intake_invalid';" in questionnaire_html


class TestQuestionnairePage:
    def test_config(self, page_config):
        assert page_config["endpoint"] == (
            "https://athlete-custom-training-plan-pipeline-production.up.railway.app"
            "/api/create-checkout")
        assert page_config["product"] == "race_plan_4weekly"
        assert page_config["schemaVersion"] == "xc-skier-intake/v2"
        assert page_config["blockCents"] == 4999
        assert page_config["weekCents"] == 1250
        assert page_config["refusals"] == gq.REFUSALS
        assert page_config["races"]["american-birkebeiner"] == "American Birkebeiner"

    def test_catalog_races_offered(self, questionnaire_html):
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        assert catalog["events"], "vendored catalog is empty"
        for event in catalog["events"]:
            assert f'value="{event["event_id"]}"' in questionnaire_html, event["event_id"]

    def test_posts_only_what_the_server_takes(self, questionnaire_html):
        js = gq.QUESTIONNAIRE_JS
        for key in ("product:", "name:", "email:", "race_name:", "ski_intake:"):
            assert key in js, key
        assert "buy.stripe.com" not in questionnaire_html
        assert "formsubmit" not in questionnaire_html

    def test_offer_on_the_page(self, questionnaire_html):
        text = plan_offer.visible_text(questionnaire_html)
        assert plan_offer.PRICE_LINE in text
        assert plan_offer.REFUND_LINE in text
        assert plan_offer.stale_offer_phrases(questionnaire_html) == []

    def test_visible_text_has_no_banned_words(self, questionnaire_html):
        text = plan_offer.visible_text(questionnaire_html)
        hits = {m.group(0) for m in BANNED.finditer(text)}
        assert not hits, hits

    def test_athlete_id_is_random_not_personal(self):
        assert "'xc-' +" in gq.QUESTIONNAIRE_JS
        assert "crypto.getRandomValues" in gq.QUESTIONNAIRE_JS


class TestTrainingPlansPage:
    def test_headline_list_and_fine_print(self, training_plans_html):
        text = plan_offer.visible_text(training_plans_html)
        for line in (plan_offer.HEADLINE, plan_offer.FINE_PRINT) + plan_offer.INCLUDED:
            assert line in text, line
        assert 'id="price"' in training_plans_html and 'id="included"' in training_plans_html

    def test_sells_plainly(self, training_plans_html):
        # Matti, 2026-11-15: never against coaching, never per-day, no value or
        # refund pitch above the fine print.
        text = plan_offer.visible_text(training_plans_html)
        pitch = text.split(plan_offer.HEADLINE, 1)[1].split(plan_offer.FINE_PRINT)[0]
        for phrase in ("a day", "per day", "coaching", "value", "bargain", "deal",
                       "refund", "money back", "guarantee"):
            assert phrase not in pitch.lower(), phrase

    def test_pitch_lines_pass_the_banned_words(self):
        for line in (plan_offer.HEADLINE, plan_offer.FINE_PRINT) + plan_offer.INCLUDED:
            assert not BANNED.search(line), line

    def test_no_retired_offer(self, training_plans_html):
        assert plan_offer.stale_offer_phrases(training_plans_html) == []
        assert "buy.stripe.com" not in training_plans_html

    def test_jsonld_price(self, training_plans_html):
        m = re.search(r'<script type="application/ld\+json">(.*?)</script>',
                      training_plans_html, re.S)
        assert m
        offer = json.loads(m.group(1).replace("<\\/", "</"))["offers"]
        assert offer["price"] == "49.99"
        assert offer["priceSpecification"]["billingDuration"] == 4
        assert offer["priceSpecification"]["unitCode"] == "WEE"


class TestSuccessAndTerms:
    def test_plan_success_page(self):
        import generate_success
        html = generate_success.build_plan_success_page()
        text = plan_offer.visible_text(html)
        assert "https://xcskilabs.com/training-plans/success/" in html
        assert not BANNED.search(text), BANNED.search(text)

    def test_terms_name_the_plan_and_refund(self):
        import generate_terms
        terms = generate_terms.PLAN_TERMS
        assert "$49.99 every 4 weeks" in terms
        assert "14 days" in terms
        assert "Gravel God Cycling LLC" in terms
        assert not re.search(r"\bmonthly\b|/mo\b|per month", terms, re.I)


@pytest.mark.skipif(not PIPELINE.exists(), reason="pipeline checkout not next to this repo")
class TestAgainstCheckoutServer:
    """The page's copy of the server's rules must match the server."""

    @pytest.fixture
    def ski_intake(self):
        if sys.version_info < (3, 10):
            pytest.skip("pipeline code needs Python 3.10+")
        sys.path.insert(0, str(PIPELINE / "athletes" / "scripts"))
        try:
            import ski_intake
        except ImportError as exc:
            pytest.skip(f"pipeline import failed: {exc}")
        return ski_intake

    def test_schema_version(self, ski_intake):
        assert ski_intake.SCHEMA_VERSION == gq.SCHEMA_VERSION

    def test_every_schema_field_is_sent(self, ski_intake):
        for field in ski_intake.FIELDS:
            assert re.search(rf"\b{field}\b", gq.QUESTIONNAIRE_JS), field

    def test_vendored_catalog_matches(self):
        theirs = json.loads((PIPELINE / "athletes" / "config" / "ski" / "event_catalog.json")
                            .read_text(encoding="utf-8"))
        ours = json.loads(CATALOG.read_text(encoding="utf-8"))
        keys = ("event_id", "technique", "event_date", "distance_km", "verified_on")
        assert sorted(tuple(e[k] for k in keys) for e in ours["events"]) == \
            sorted(tuple(e[k] for k in keys) for e in theirs["events"].values())
        engine = (PIPELINE / "athletes" / "scripts" / "ski_engine.py").read_text(encoding="utf-8")
        assert f"EVENT_FACTS_MAX_AGE_DAYS = {ours['max_age_days']}" in engine

    def test_prices_match(self):
        src = (PIPELINE / "webhook" / "race_plan_subscription.py").read_text(encoding="utf-8")
        assert f"BLOCK_PRICE_CENTS = {plan_offer.BLOCK_PRICE_CENTS}" in src
        assert f"BLOCK_WEEKS = {plan_offer.BLOCK_WEEKS}" in src
        assert f"REFUND_WINDOW_DAYS = {plan_offer.REFUND_DAYS}" in src

    def test_every_refusal_code_has_a_message(self):
        sources = [PIPELINE / "athletes" / "scripts" / n
                   for n in ("ski_engine.py", "ski_intake.py")]
        sources.append(PIPELINE / "webhook" / "race_plan_subscription.py")
        codes = set()
        for path in sources:
            codes |= set(re.findall(r"f?[\"']([a-z]+(?:_[a-z]+)+): ",
                                    path.read_text(encoding="utf-8")))
        app = (PIPELINE / "webhook" / "app.py").read_text(encoding="utf-8")
        start = app.index("def _rp_ski_target")
        route = app[start:start + 20000]
        codes |= set(re.findall(r"'reason': '([a-z_]+)'", route))
        codes |= set(re.findall(r"ValueError\(f?'([a-z_]+):", route))
        # Schema field names in "field: detail" messages are not refusal
        # codes for the skier; the page never sends a retired value.
        codes.discard("available_modalities")
        missing = sorted(c for c in codes if c not in gq.REFUSALS)
        assert not missing, missing
