# XC Ski Labs — Nordic Race Automation

## Project Overview
XC ski race database at `xcskilabs.com`. 229 race profiles scored across 14 criteria.
Modeled after Gravel God (`gravel-race-automation`). Same deploy pattern (tar+ssh to SiteGround).

## Key Paths
- **Race profiles**: `race-data/*.json` (skip `_schema.json`)
- **Search UI**: `web/nordic-lab-search.html` + `web/nordic-lab-search.js`
- **Search index**: `web/race-index.json`
- **Output**: `output/` (generated, gitignored)
- **Scripts**: `scripts/generate_race_pages.py`, `scripts/generate_race_index.py`, `scripts/generate_homepage.py`, `scripts/generate_sitemap.py`
- **Deploy**: `scripts/deploy.py`, `scripts/preflight.py`
- **Tests**: `tests/test_race_profiles.py` (parametrized per-profile), `tests/test_generators.py`, `tests/test_youtube.py`

## Scoring System
- 14 criteria, each 1-5: distance, elevation, altitude, field_size, prestige, international_draw, course_technicality, snow_reliability, grooming_quality, accessibility, community, scenery, organization, competitive_depth
- `overall_score = round((sum_of_14 / 70) * 100)` — denominator 70 is intentional (same as Gravel God)
- **Tiers**: T1 (>=80), T2 (>=60), T3 (>=45), T4 (<45)
- **Prestige overrides**: p5+score>=75 → T1, p5+score<75 → cap at T2, p4 → promote 1 tier (not into T1)

## Race JSON Structure
```
d["race"]["slug"]
d["race"]["name"]
d["race"]["display_name"]
d["race"]["tagline"]
d["race"]["vitals"]["country"]
d["race"]["vitals"]["distance_km"]
d["race"]["vitals"]["discipline"]  # "classic", "skate", or "both"
d["race"]["nordic_lab_rating"]["overall_score"]
d["race"]["nordic_lab_rating"]["tier"]
d["race"]["nordic_lab_rating"][CRITERION]  # each of the 14
d["race"]["youtube_data"]["videos"]  # list
d["race"]["history"]["founded"]
```

## Deploy
- SiteGround via tar+ssh (NOT GitHub Pages)
- SSH key: `~/.ssh/xcskilabs_key`
- Env vars: `GL_SSH_HOST`, `GL_SSH_USER`, `GL_SSH_PORT`, `GL_REMOTE_BASE` (GL_ prefix is legacy)
- Always purge SiteGround cache after deploy
- Pre-deploy: `python scripts/preflight.py` (or `--deploy` to chain)

## Brand
- Name: **XC Ski Labs** (not "Nordic Lab" — that's the internal project folder name only)
- Domain: `xcskilabs.com`
- Neo-brutalist: no border-radius, no box-shadow, 2-3px solid borders
- Colors: Nordic Night `#1a2332`, Fjord Blue `#2b4c7e`, `#357a88`, `#b34a1a`, Cream `#d4cdc4`, Paper `#f0f3f7`
- Fonts: Sometype Mono (data), Source Serif 4 (editorial), Inter (UI)
- CSS variables use `--nl-*` prefix (legacy from Nordic Lab name)

## Known Pitfalls
1. **Never hardcode API keys in scripts** — use `.env` loading. `batch_enrich.sh` had a leaked key.
2. **Slug must match filename** — `race-data/foo-bar.json` must have `"slug": "foo-bar"` inside.
3. **Homepage stat IDs must be parseable** — preflight.py looks for `id="statRaces">(\d+)`. Don't change the format.
4. **`</script>` in JSON breaks HTML** — always use `_safe_json_for_script()` (replace `</` with `<\/`).
5. **Duplicate profiles cause silent count mismatches** — tests catch this via slug uniqueness + output count parity.
6. **Search index field names are compact** — `n`=name, `s`=slug, `t`=tier, `sc`=score, `di`=discipline, `co`=country, `st`=search_text. Don't assume full names.
7. **Tagline validation: exact match, not substring** — "America's largest cross-country ski race" is specific; "a cross-country ski race" is generic.
8. **Output dir must be regenerated after any generator change** — stale output pages cause test failures.
9. **After deleting a profile, also delete its output dir** — `rm -rf output/{slug}`.
10. **Estonian spelling matters** — it's `tartu-maraton` not `tartu-marathon`.
11. **Preflight regex can match its own source** — skip self when scanning for API key patterns.
12. **Copy search files to output/search/ after any web/ changes** — the deploy reads from output/.
13. **YouTube `video_id` can be int from API** — always coerce to str.
14. **Race page nav links**: `/search/` not `/nordic-lab-search.html` (production URL structure).
15. **Git history**: check if secrets were committed before assuming removal is sufficient.
16. **AI-checking-AI is circular** — fact_check_profiles.py uses Claude to verify Claude-generated data. Many results are "UNCERTAIN". Use web-grounded search (Perplexity) for real verification.
17. **AI-generated races may be fictional** — profiles created from training knowledge can hallucinate events. Always verify T1/T2 races have a real web presence. `validate_urls.py` catches dead URLs; no website = suspect.
18. **`field_size_estimate` must be numeric** — never store as string like `"~8,000 starters"`. Run `normalize_profiles.py` to fix.
19. **Schema must be consistent across all profiles** — different agent batches create profiles with different schemas. Run `normalize_profiles.py` after bulk creation.
20. **Auto-fix changes vitals but not scoring criteria** — if elevation goes from 500→1200, the `elevation` criterion (1-5) may need updating too. Criteria-to-vitals consistency tests catch drift.
21. **Duplicate races can hide under different slugs** — `holmenkollen-skimaraton` and `holmenkollmarsjen` are the same event. Test for similar slugs and shared websites.
22. **YouTube enrichment "success" ≠ quality** — exit code 0 doesn't mean relevant videos. Wrong-sport, indoor trainer, slideshow content can slip through.
23. **`_fact_check_fixes` and other metadata keys pollute profiles** — auto-fix tools must not leave internal metadata in the JSON. Tests enforce no underscore-prefixed keys.
24. **All website URLs must be HTTPS** — http:// URLs should be upgraded or flagged.
25. **Search files in output/search/ must match web/** — no test previously enforced this. `test_data_quality.py` now does.
26. **39% of AI-generated profiles were fictional** — Mar 2026 existence check via Perplexity sonar-pro found 149/378 races had zero web evidence. Always verify new profiles with `scripts/verify_race_existence.py` before adding to database.
27. **Perplexity false positives need Exa cross-check** — Perplexity got Birkebeinerrennet discipline wrong. Always use Exa MCP for contested findings. 12 "fictional" races were actually duplicates under hallucinated names (e.g., halvvasan→vasaloppet-45, keskinada-loppet→gatineau-loppet).
28. **Fact-check scripts**: `fact_check_profiles.py` (Perplexity sonar-pro), `apply_fact_check_fixes.py` (with false-positive blacklist), `cleanup_fact_check.py` (junk field removal), `verify_race_existence.py` (existence verification), `remove_fictional_races.py` (batch deletion).

## QC Gate (mandatory for new profiles)
```bash
# Before adding any new race profile:
python scripts/qc_new_profiles.py --slug my-new-race     # full pipeline (existence + fact-check)
python scripts/qc_new_profiles.py --new                   # auto-detect unchecked profiles
python scripts/qc_new_profiles.py --slug my-race --dry-run # schema only, no API calls

# 4 stages: schema → existence (Perplexity) → fact-check (Perplexity) → normalize
# Profile BLOCKED if: schema errors, FICTIONAL/SUSPICIOUS existence, or WRONG facts
# Requires PERPLEXITY_API_KEY in .env
```

## Regeneration Commands
```bash
# Full regeneration pipeline
python scripts/generate_race_index.py          # web/race-index.json
python scripts/generate_race_pages.py           # output/{slug}/index.html
python scripts/generate_homepage.py             # output/index.html
python scripts/generate_sitemap.py              # output/sitemap.xml
cp web/nordic-lab-search.html output/search/index.html
cp web/nordic-lab-search.js output/search/
cp web/race-index.json output/search/

# Validation
python scripts/preflight.py
pytest tests/ -v
```

## Test Counts
- `test_race_profiles.py`: ~5,267 parametrized (229 profiles × ~23 tests each)
- `test_generators.py`: 23 tests
- `test_new_features.py`: 72 tests (GA4, consent, nav, CTA, training, coaching, security, Stripe, deploy, edge cases)
- `test_youtube.py`: 69 tests
- `test_data_quality.py`: additional data quality checks
- Total: ~7,970 passing

## Website Pages (generated)
- **Race pages**: 229 (`output/{slug}/index.html`) — with GA4, consent, nav, sticky CTA, training section
- **Training plans**: `output/training-plans/index.html` — pricing from `data/stripe-products.json`
- **Coaching form**: `output/coaching/apply/index.html` — 12-section intake, FormSubmit.co
- **Homepage**: `output/index.html`
- **Search**: `web/nordic-lab-search.html` + `web/nordic-lab-search.js`
- **Sitemap**: `output/sitemap.xml` (231 URLs)

## Stripe
- **Account**: xcskilabs (Endurance Labs org)
- **Products**: 5 (Custom Training Plan, Coaching Min/Mid/Max, Consulting)
- **Prices**: 18 (14 plan durations + 3 coaching tiers + 1 consulting)
- **Data**: `data/stripe-products.json` (source of truth for pricing)

## GA4
- **Measurement ID**: `G-3JQLSQLPPM` (XC Ski Labs property)
- **Consent-gated**: Only fires if `xl_consent` cookie is not `declined`
- **Embedded in**: All generated pages (race, training, coaching) — NOT via mu-plugins

## Known Pitfalls (additions)
29. **Mu-plugins don't work on static sites** — xcskilabs.com has no WordPress. GA4, consent, nav must be embedded directly in HTML generators, not PHP mu-plugins. The `wordpress/mu-plugins/` directory is kept for reference only.
30. **Stripe price extraction needs regex** — `word.isdigit()` fails on "4-week". Use `re.search(r'(\d+)', nickname)`.
31. **Cookie consent must fire before GA4** — Set consent defaults in the same `<script>` block, before `gtag('config', ...)`.
32. **Sticky CTA needs padding-bottom on page** — Without `padding-bottom: 80px` on `.gl-page`, the CTA overlaps the footer on short pages.
33. **IntersectionObserver must guard entries** — Always check `entries.length > 0` before `entries[0]`. Wrap updates in `requestAnimationFrame`.
34. **Touch targets must be >= 44px** — WCAG 2.1 SC 2.5.5. Dismiss button needs `min-width: 44px; min-height: 44px`.
35. **`sync_search()` must fail on partial deploys** — Use `return success == len(files)`, not `return success > 0`.
36. **Post-deploy validation is mandatory** — Count `index.html` files on remote after tar+ssh upload. Partial deploys corrupt the site silently.
37. **FormSubmit.co needs `_next` redirect** — Without it, users see a generic third-party page after submit.
38. **Coaching form collects medical data** — Must have privacy policy notice before submit button.
