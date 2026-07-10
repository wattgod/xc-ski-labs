# X2 — Build /about/ (dead nav link on all 229 pages) — P0

## Why
The global nav on every race page links /about/ → 404.

## Build
New generator `wordpress/generate_about.py` producing `output/about/index.html`.
Short page, four sections, understated register (assert, don't perform):
1. Hero: kicker "ABOUT", H1 "Honest reviews for a sport that deserves them.",
   two-sentence sub: the database exists because XC ski race info is scattered and
   organizer marketing isn't a review.
2. "What this is" — 229 races scored on 14 criteria, ranked into four tiers, by hand.
   READ THE COUNT from race-data/*.json at generate time (len of dir glob, minus
   _schema.json) — never hardcode 229.
3. "How it's scored" — one short paragraph + link to /search/ and the tier system.
   Do NOT invent methodology claims; only what CLAUDE.md/scoring.py support.
4. "Who's behind it" — Matti: 12 years at TrainingPeaks, National-level racer,
   coaches endurance athletes across gravel/road/ski (same person as
   gravelgodcycling.com — one quiet cross-link, no logos wall). NO stock/AI imagery;
   the page is type-only.
Footer CTA band: one link to /training-plans/, one to /coaching/apply/.
Same chrome/GA4/consent pattern as race pages. Update nothing else — the nav already
points at /about/.

## Acceptance
- Generator runs; page has GA4+consent; count is computed not hardcoded; zero images;
  pytest green with a new test asserting /about/ generation + no hardcoded "229".
