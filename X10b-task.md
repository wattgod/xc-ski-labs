TASK: X10b — Wax Bench port, part 2 (this branch already contains X10a: new
tokens/tokens.css + ported race pages — study scripts/generate_race_pages.py as the
in-repo reference implementation alongside docs/BRAND_GUIDELINES.md + docs/brand/
reference-mock.html).

Port these surfaces to Wax Bench, matching X10a's CSS patterns exactly (same tokens,
same nav/footer markup, same display/mono/serif roles):
1. scripts/generate_homepage.py — red hero block w/ stripes per mock ("EVERY LOPPET,
   RATED." headline — never "honestly rated"), klister kicker + stat line, white+carbon
   buttons, tier-1 table band, carbon "GET RACE READY" ladder band (4 rungs per race-page
   implementation), red footer strip. KEEP the parseable stat IDs (preflight pitfall #3:
   id="statRaces">NNN< format) and GA4/consent.
2. web/nordic-lab-search.html + web/nordic-lab-search.js — restyle to Wax Bench (carbon
   nav, paper background, table per mock, tier chips carbon/white, red READ links).
   Search behavior/index format unchanged. Copy results to output/search/ (pitfall #12).
3. wordpress/generate_questionnaire.py + wordpress/generate_about.py +
   wordpress/generate_training_plans.py + wordpress/generate_coaching_apply.py — restyle
   chrome to Wax Bench tokens (these currently carry Nordic Night inline :root blocks —
   replace with the token set; keep all form behavior, FormSubmit actions, GA4, consent,
   honeypots EXACTLY as-is).
4. Regenerate everything (race index untouched); run scripts/preflight.py and
   python3 -m pytest tests/ -q — update any tests pinning Nordic Night styling; keep the
   full suite green.
HARD RULES: no race-data/ changes, no deploy, no new fonts, no border-radius/box-shadow,
copy changes limited to chrome casing + the "honestly"→plain "rated" rule. Final message:
files changed, pytest tail, preflight result.
