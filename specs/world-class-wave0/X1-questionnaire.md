# X1 — Build /questionnaire/ (the plan-purchase intake) — P0

## Why
Every race page's primary CTA ("BUILD MY {race} PLAN", scripts/generate_race_pages.py
lines ~1386 and ~1401) and all three buttons on /training-plans/ link to
/questionnaire/?race={slug} — which is a 404. The site's entire plan-purchase path is dead.

## Build
New generator `wordpress/generate_questionnaire.py` producing `output/questionnaire/index.html`.
Model the architecture on `wordpress/generate_coaching_apply.py` (self-contained HTML,
localStorage save/resume optional — this form is SHORT so progress UI is unnecessary),
but this is the PLAN funnel, not coaching: keep it to ONE page, ~7 fields:

1. Target race — text input, PRE-FILLED from `?race=` URL param by matching against
   web/race-index.json slugs (JS fetch of /race-index.json is NOT available at that path
   on prod; instead embed a compact slug→name map at generate time, same technique as
   the search page). If the param doesn't match, leave the field editable/empty.
2. Race date (date input) 3. Weekly training hours (select: 0-5/5-8/8-12/12+)
4. Years of structured training (select) 5. Classic / skate / both (select)
6. Anything the plan must work around (textarea, optional) 7. Email (required).

Form POSTs to FormSubmit like coaching-apply does — action
`https://formsubmit.co/coaching@xcskilabs.com`, subject "New Plan Questionnaire — XC Ski Labs",
include FormSubmit honeypot (_honey) + _next redirect back to /questionnaire/?submitted=1,
and render a calm success state when ?submitted=1.

Below the form, one quiet line: "You'll get your plan details and payment link by email,
usually within a day." (Plans are fulfilled manually via Stripe links in
data/stripe-products.json — do NOT build checkout.)

Page chrome: same nav header + GA4 + consent pattern as generate_race_pages.py output.
Kicker "TRAINING PLANS", H1 "Tell me about your race.", one-line sub in the understated
register. No testimonials, no pricing tables — the /training-plans/ page already sold them.

## Acceptance
- `python3 wordpress/generate_questionnaire.py` writes output/questionnaire/index.html.
- ?race=vasaloppet pre-fills "Vasaloppet" (test with a race-index fixture).
- Form has honeypot + POSTs to FormSubmit; success state renders on ?submitted=1.
- GA4 snippet + consent present; tests in tests/test_generators.py style pass;
  no --gl-* token invented; pytest green.
