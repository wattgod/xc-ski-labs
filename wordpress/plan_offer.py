"""Copy and numbers for the custom ski plan billed every 4 weeks (2026-11-14).

XC Ski Labs sells one plan: $49.99 every 4 weeks, one 4-week block per
payment, until race week. Every page that offers it (/training-plans/,
/questionnaire/, /training-plans/success/, /terms/) builds its lines from
here, so the price and terms read the same everywhere.

Source of the numbers and terms: the checkout server's
``webhook/race_plan_subscription.py`` in athlete-custom-training-plan-pipeline
(``payment_plan`` and ``terms_text``, shown at Stripe checkout and approved by
Matti 2026-11-12) and its payment email (``race_plan_emails``). Nothing here
promises more than those say. Rules: the rate only, "$49.99 / four weeks",
never a total, a payment count or a per-race sum (Matti, 2026-11-17, every
brand); never "monthly", "/mo" or "per month"; adding a next race is not built
for ski plans, so never offer it.

``stale_offer_phrases`` is the guard: tests fail a page that shows the
retired one-off offer ($15 a week, $60-$249, "no subscription") next to
this plan, or a total or payment count for it.
"""
from __future__ import annotations

import html as _html
import re

# ── Numbers (the server's race_plan_subscription constants) ──
BLOCK_WEEKS = 4
BLOCK_PRICE_CENTS = 4999
WEEK_PRICE_CENTS = -(-BLOCK_PRICE_CENTS // BLOCK_WEEKS)  # 1250, the last short block
REFUND_DAYS = 14
PRODUCT = "race_plan_4weekly"
CHECKOUT_ENDPOINT = (
    "https://athlete-custom-training-plan-pipeline-production.up.railway.app"
    "/api/create-checkout"
)
CONTACT_EMAIL = "gravelgodcoaching@gmail.com"

# What the ski engine builds (athletes/scripts/ski_intake.py, ski_engine.py).
MIN_AGE = 18                 # juniors_not_built
MAX_DISTANCE_KM = 90         # own_event.distance_km
RACE_MONTHS = "December to April"  # season_not_built


def money(cents: int) -> str:
    return f"${cents // 100:,}.{cents % 100:02d}"


def payment_plan(weeks: int) -> dict:
    """Payments for ``weeks`` of plan, the server's ``payment_plan`` math."""
    if not isinstance(weeks, int) or weeks < 1:
        raise ValueError("A plan needs at least one week")
    full_blocks, leftover = divmod(weeks, BLOCK_WEEKS)
    payments = [BLOCK_PRICE_CENTS] * full_blocks
    if leftover:
        payments.append(WEEK_PRICE_CENTS * leftover)
    return {
        "weeks": weeks,
        "payment_count": len(payments),
        "payments_cents": payments,
        "total_cents": sum(payments),
        "first_payment_cents": payments[0],
    }


BLOCK_PRICE = money(BLOCK_PRICE_CENTS)   # "$49.99"
WEEK_PRICE = money(WEEK_PRICE_CENTS)     # "$12.50"
PRICE_UNIT = "four weeks"
PRICE_LINE = f"{BLOCK_PRICE} / {PRICE_UNIT}"   # "$49.99 / four weeks"
PRICE_TO_RACE = f"{PRICE_LINE} until race week"

# ── Rider-facing lines (Matti speaking). Every one is listed for approval. ──
BLOCK_LINE = f"Each payment covers one {BLOCK_WEEKS}-week block of your plan."
# The $12.50 week rate is a billing term for /terms/ only; offer copy
# carries one rate.
LAST_BLOCK_LINE = (f"If your race isn't a whole number of {BLOCK_WEEKS}-week blocks away, "
                   "the last block is shorter and costs less.")
ENDS_LINE = "It ends after race week. Nothing is charged after that."
REVIEW_LINE = ("I look over every block before it goes on your TrainingPeaks calendar, "
               "and each block comes with a guide by email.")
CANCEL_LINE = "Cancel any time from your plan page; you keep any block you've paid for."
REFUND_LINE = (f"Within {REFUND_DAYS} days of your first payment you can cancel from "
               "your plan page with a full refund.")
TERMS_SHORT = (f"{PRICE_TO_RACE}. Cancel any time from your plan page; full refund "
               f"within {REFUND_DAYS} days of your first payment.")

# Who the plan is built for: each line is a rule the checkout server refuses on.
FIT_LINES = (
    f"A classic, skate or skiathlon race from {RACE_MONTHS}, up to {MAX_DISTANCE_KM} km.",
    "At least one full winter on skis.",
    f"{MIN_AGE} or older.",
    "Week 1 starts this week or next week.",
)

OFFER_LINES = (BLOCK_LINE, LAST_BLOCK_LINE, ENDS_LINE, REVIEW_LINE,
               CANCEL_LINE, REFUND_LINE)

# ── The sales page (Matti, 2026-11-15): one plain headline, a fast list of
# what's in it, the terms as fine print. Never compared with coaching, never
# a per-day price, never a value or refund pitch (docs/AI_WRITING_POLICY.md).
# Every item is built: the course grant is pipeline #459, heat is #458.
HEADLINE = ("A custom ski plan built around your race and your life, adjusted every "
            f"{BLOCK_WEEKS} weeks, for less than a block of race wax.")
INCLUDED = (
    "Built for your race: classic, skate or skiathlon, up to 90 km",
    "Fits your week: your hours, your days, your long day",
    "Follows your snow: rollerski, run, SkiErg or bike until it falls",
    f"Checked by me every {BLOCK_WEEKS} weeks, with your changes built in",
    "The XC Ski Labs Course: every technique module, and every one I add",
    "Strength every week, for a gym, dumbbells or bodyweight",
    "Fueling targets for long sessions, carb-load before the race",
    "Heat training, if you have a sauna or a hot bath",
    "Effort targets on every session, heart rate where you know your ski max",
    "Test sessions that reset your ranges",
    "Taper into race week",
    "On your TrainingPeaks calendar, with a guide for every block",
)
FINE_PRINT = (
    f"Billed {PRICE_LINE} until race week, then it stops. {LAST_BLOCK_LINE} "
    f"{CANCEL_LINE} {REFUND_LINE} For skiers {MIN_AGE} or older with at least one full "
    f"winter on skis, racing classic, skate or skiathlon from {RACE_MONTHS}, up to "
    f"{MAX_DISTANCE_KM} km."
)


# ── Guard: the retired one-off offer must not reappear next to the plan ──

STALE_OFFER_PATTERNS: dict[str, re.Pattern] = {
    "$249": re.compile(r"\$249\b"),
    "$60": re.compile(r"\$60\b"),
    "$15 a week": re.compile(r"\$15\s*(?:/\s*(?:wk|week)\b|a week|per week)", re.I),
    "One-time payment": re.compile(r"\bone[- ]time payment", re.I),
    "One plan, one price": re.compile(r"\bone plan, one price\b", re.I),
    "no subscription": re.compile(r"\bno subscription\b", re.I),
    "No recurring charges": re.compile(r"\bno recurring charges?\b", re.I),
    "/mo": re.compile(r"/\s?mo\b", re.I),
    "monthly": re.compile(r"\bmonthly\b", re.I),
    "per month": re.compile(r"\bper month\b", re.I),
    "next race": re.compile(r"\bnext race\b", re.I),
    # Rate only (Matti, 2026-11-17): no total, payment count or per-race sum.
    "a total ('in all')": re.compile(r"\bin all\b", re.I),
    "a payment count": re.compile(r"\b\d+ payments?\b", re.I),
    "number of payments": re.compile(r"\bnumber of payments\b", re.I),
    "your total": re.compile(r"\b(?:your|the) total\b", re.I),
}


def visible_text(page_html: str) -> str:
    """Rough visible text: scripts, styles and comments dropped, tags
    removed, entities decoded, whitespace collapsed."""
    text = re.sub(r"<(script|style)\b[\s\S]*?</\1>", " ", page_html, flags=re.I)
    text = re.sub(r"<!--[\s\S]*?-->", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    return re.sub(r"\s+", " ", text)


def stale_offer_phrases(page_html: str) -> list[str]:
    """Retired-offer phrases anywhere in the page's visible text."""
    text = visible_text(page_html)
    return [label for label, pattern in STALE_OFFER_PATTERNS.items() if pattern.search(text)]
