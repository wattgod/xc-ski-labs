# XC ski plan storefront copy: DRAFT for Matti

Branch `claude/xc-ski-4weekly-storefront`, 2026-11-22. Launch checklist rows
8-10 (athlete-custom-training-plan-pipeline
`docs/plans/XC_SKI_4WEEKLY_LAUNCH.md`). Every line below is new or changed
customer copy. Nothing here is approved until Matti reads it.

Voice grounding: `writing-graph/self/voice-and-beliefs-profile.md` (Sales and
landing pages; Product surfaces), `docs/AI_WRITING_POLICY.md` "Selling a
product", `vendor/no-ai-slop/SKILL.md` and `eval.md`. Retrieval
(`scripts/retrieve_voice.py "selling a training plan plainly, price and terms,
XC ski"`) returned
`inbox/gravel-god/hacking-unbound-200-with-best-bike-split.md` and
`inbox/substack/shit-athletes-say-ill-just-train.md`; none of their lines fit
a one-line headline or legal terms, so no source language is reused.

## 1. Training plans headline (changed)

Renders: `/training-plans/` hero `<h1>`. Source: `wordpress/plan_offer.py`
`HEADLINE`.

Was:

> A custom ski plan built around your race and your life, adjusted every 4 weeks, for less than a block of race wax.

Proposed:

> A custom ski plan for your race, built around your week and checked by me one 4-week block at a time.

Why: "for less than a block of race wax" compares the price with something
else, which the 2026-11-15 ruling puts out of bounds ("never sell it as a
value"). The new line says what the product is and the two things that are
true of it today: it is built from the skier's race and week, and Matti
checks each 4-week block before it goes out (backend: per-block approve and
release). "Adjusted" was dropped: changing a skier's answers after payment is
done by hand, not built.

## 2. Terms page, custom ski training plan paragraph (changed)

Renders: `/terms/`, "Purchases, delivery, and refunds", bold lead "Custom ski
training plan." Source: `wordpress/generate_terms.py` `PLAN_TERMS`.

New sentence (new):

> The custom XC ski training plan is sold by Gravel God Cycling LLC and paid by card.

(was "... is sold by Gravel God Cycling LLC." The card sentence is new: the
checkout's payment method configuration is card only.)

Billing and refund sentences, now word for word the checkout's `terms_text`
(pipeline `webhook/race_plan_subscription.py`, TERMS_VERSION
`race_plan_4weekly_terms/2026-11-17.1`, shown above Stripe's pay button),
except that the checkout prints its plan page address where this says "your
plan page, xcskilabs.com/plan/manage":

> Billing. $49.99 every 4 weeks from the day you sign up, one payment per block. If your race isn't a whole number of 4-week blocks away, the last, shorter block costs $12.50 a week. Payments end after your race week. Cancel any time at your plan page, xcskilabs.com/plan/manage; you keep the block you've paid for. Refunds. Full refund within 14 days of your first payment; refunding it ends the plan. Adding another race to this plan later doesn't start a new 14-day window. Later payments aren't refunded, except where the law says otherwise.

These replaced (the old site wording, not word for word with checkout):

> It is billed $49.99 / four weeks from the day you sign up, one payment for each 4-week block of your plan, and it ends after your race week. If your race isn't a whole number of 4-week blocks away, the last, shorter block costs $12.50 a week. You can cancel any time from your plan page and keep the block you've paid for. Within 14 days of your first payment you can cancel from your plan page with a full refund of that payment, which ends the plan. Later payments aren't refunded, except where the law says otherwise.

Sentence by sentence:

| # | Sentence | Status |
|---|---|---|
| 1 | The custom XC ski training plan is sold by Gravel God Cycling LLC and paid by card. | changed (added "and paid by card") |
| 2 | Billing. $49.99 every 4 weeks from the day you sign up, one payment per block. | changed, checkout wording |
| 3 | If your race isn't a whole number of 4-week blocks away, the last, shorter block costs $12.50 a week. | unchanged in substance, checkout wording |
| 4 | Payments end after your race week. | changed, checkout wording |
| 5 | Cancel any time at your plan page, xcskilabs.com/plan/manage; you keep the block you've paid for. | changed, checkout wording with the address named |
| 6 | Refunds. Full refund within 14 days of your first payment; refunding it ends the plan. | changed, checkout wording |
| 7 | Adding another race to this plan later doesn't start a new 14-day window. | added, checkout wording (see question below) |
| 8 | Later payments aren't refunded, except where the law says otherwise. | unchanged |

Questions for Matti:

- Sentence 7 is in the checkout text every skier sees, but adding a race is
  not built for ski plans. Keep it (terms match checkout word for word), or
  ask for a ski-specific `terms_text` in the pipeline and drop it from both?
- "xcskilabs.com/plan/manage" redirects to the Railway manage page
  (`web/.htaccess`). The checkout prints whatever
  `RACE_PLAN_4WEEKLY_CANCEL_URL_XCSKILABS` says, or the Railway address when
  unset. Setting it to `https://xcskilabs.com/plan/manage` makes the two
  identical.

## 3. Questionnaire refusal for a test order (new)

Renders: `/questionnaire/` alert box when checkout answers 503
`test_coupon_unavailable` (only a listed test buyer can get it). Source: new,
`wordpress/generate_questionnaire.py` `REFUSALS`.

> The free test order isn't set up right now, so I couldn't take it. Nothing was charged. Email me at gravelgodcoaching@gmail.com.

## 4. Questionnaire honeypot label (new, not shown to people)

Renders: off-screen, `aria-hidden`, never seen or read aloud. Source: new.

> Leave this empty

## 5. Race-page prep-kit gate (PROPOSED ONLY, not in the code)

The gate promises nothing by email today. gravel-race-automation PR #707
(draft, not merged) adds an XC kit sequence: the kit link on day 0 and one
short check-in on day 2. Ship this line only with #707, never before, or the
gate promises an email nobody sends.

Where: `scripts/generate_race_pages.py`, `build_email_capture()`, the
`<p class="gl-capture-sub">` line, which today reads:

> Leave your email &mdash; the {name} prep kit is yours.

Proposed:

> Leave your email and the {name} prep kit opens now. I'll also email you the link, and one short note a couple of days later.

`tests/test_prep_kit.py` pins the current sentence and changes with it.

Separately, CLAUDE.md says prep kits are "linked from the race-page gate and
day-0 kit emails". The day-0 emails don't exist until #707 merges; the line
was left as is.

## Existing copy checked, not changed

- `plan_offer.INCLUDED` "Checked by me every 4 weeks, with your changes built
  in": the changes are made by hand (the backend has no self-serve change).
  True as a promise of Matti's own work; flagging in case he wants it plainer.
- Race-page offer ladder (`build_product_ladder`): "Start with a plan shaped
  around this race. Move up to coaching when you want ongoing judgment and
  adjustment." This sets the plan beside coaching, which the 2026-11-15
  ruling forbids on sales pages. It predates this branch and was left alone.
