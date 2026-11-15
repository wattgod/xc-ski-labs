# XC Ski Labs — Nordic Race Automation

## AI writing as Matti

Before drafting, rewriting, or approving copy presented as Matti Rowe or one of
his brands, read `docs/AI_WRITING_POLICY.md`. Its source-retrieval,
provenance, privacy, and anti-slop requirements are binding.
This includes the complete pinned `petergyang/no-ai-slop` skill and eval;
passing a phrase linter alone is not approval.

## Baseline editorial and citation rules

These rules apply to every agent and every public-facing race, rating, article,
email, and product surface:

- Write the finished judgment, never the research process. Do not say a source's
  "assessment rings true," "according to our research," "sources say," or name
  the person/site that supplied an ordinary fact unless the attribution itself
  materially matters.
- Do not use the brand as a synthetic narrator (for example, "XC Ski Labs
  scores..."). State the judgment directly in the brand's established voice.
- Lead every Course and Editorial/Experience rating with one sharp, standalone
  verdict sentence before discussing individual criteria.
- Put a numbered inline marker such as `[3]` on every factual or quoted claim.
  Every marker must resolve to that page's numbered source list; preserve stable
  source order, never invent a source number, and never use attribution prose as
  a substitute for the marker.
- Preserve a real person's exact words inside quotation marks and cite the quote.
  Clean up only the surrounding prose; do not flatten actual human language into
  house style.
- Cut AI filler: importance puffery, vague scene-setting, fake quotations,
  repetitive conclusions, canned transitions, generic superlatives, and words
  such as "delve," "testament," or "game-changing" when a concrete statement
  will do.
- Citation correctness and voice quality are separate gates. A sourced sentence
  can still be bad copy, and clean copy can still be unsupported. Verify both.

## Project Overview
XC ski race database at `xcskilabs.com`. 227 race profiles scored across 14 criteria.
Modeled after Gravel God (`gravel-race-automation`). Same deploy pattern (tar+ssh to SiteGround).

## Key Paths
- **Race profiles**: `race-data/*.json` (skip `_schema.json`)
- **Search UI**: `web/nordic-lab-search.html` + `web/nordic-lab-search.js`
- **Search index**: `web/race-index.json`
- **Output**: `output/` (generated, gitignored)
- **Scripts**: `scripts/generate_race_pages.py`, `scripts/generate_prep_kit.py`, `scripts/generate_race_index.py`, `scripts/generate_homepage.py`, `scripts/generate_sitemap.py`
- **Deploy**: `scripts/deploy.py`, `scripts/preflight.py`
- **Tests**: `tests/test_race_profiles.py` (parametrized per-profile), `tests/test_generators.py`, `tests/test_youtube.py`

## Scoring System
- 14 criteria, each 1-5: distance, elevation, altitude, field_size, prestige, international_draw, course_technicality, snow_reliability, grooming_quality, accessibility, community, scenery, organization, competitive_depth
- `overall_score = round((sum_of_14 / 70) * 100)` — denominator 70 is intentional (same as Gravel God)
- **Tiers**: T1 Elite (>=80), T2 Contender (>=60), T3 Solid (>=45), T4 Roster (<45). Names are Gravel God's; `scripts/tiers.py` is the only mapping (tests/test_tier_names.py)
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
- SSH key: `~/.ssh/xcskilabs_key` (RSA-4096, rebuilt 2026-08-03; imported in Site Tools as `xcskilabs-deploy`. SiteGround's key Import field REJECTS ed25519 — RSA only, error is just "Invalid field")
- Env vars in `.env` (gitignored): `GL_SSH_HOST=ssh.xcskilabs.com`, `GL_SSH_USER`, `GL_SSH_PORT=18765`; `GL_REMOTE_BASE` defaults to `~/www/xcskilabs.com/public_html` (GL_ prefix is legacy)
- xcskilabs.com is its OWN SiteGround site — gravel/road servers and keys don't reach it
- Cache purge is automated (`--purge-cache` / `--deploy-all` use `site-tools-client domain update id=1 flush_cache=1` over SSH)
- Pre-deploy: `python scripts/preflight.py` (or `--deploy` to chain)

## Brand
- Name: **XC Ski Labs** (not "Nordic Lab" — that's the internal project folder name only)
- Domain: `xcskilabs.com`
- **RATIFIED BRAND: `docs/brand/sledge-stores/README.md`** — Sledge Stores ·
  Splash on wool, locked by Matti on 2026-11-14. Wool, oat and fjord navy with
  one salmon object per page; Big Shoulders Stencil, Big Shoulders Text and
  Libre Franklin; the crossed-skis mark in `docs/brand/sledge-stores/logos/`.
  Read it before touching any visual. New visual work follows it.
- **The live site runs the book (ported 2026-11-15).** `tokens/tokens.css` is
  GENERATED by `scripts/build_brand_tokens.py` from the book's `tokens.json`
  and `components/bundle.css` (it also rewrites the token block inside
  `web/nordic-lab-search.html`). Never hand-edit it: edit the book, run the
  script, commit both; `tests/test_brand_port.py` fails on a stale file.
  Book variables use the book's names (`--ground`, `--ink`, `--font-label`,
  `--space-5` ...) and the `xc-*` component classes. The old `--gl-*` names
  still used by the templates are aliases pinned to Wool values (mapping in
  `LEGACY_COLOURS`); new work uses the book names.
- Navy is for straps (header, footer, sticky CTA) and action slabs only. Old
  templates that filled content bands with ink (`.gl-hero`, `.gl-ladder`,
  `.gl-transition`, `.gl-verdict`, `.gl-final-cta`, `.gl-coach-band--dark`,
  `.gl-consult-cta`) are flipped to oat panels in tokens.css by re-pointing
  the `--gl-*` names inside them. A filled button inside one of those bands
  must be listed in the "action pair" rule there, or its text vanishes.
- Fonts: `scripts/brand_head.py` holds the one Google Fonts URL and the
  favicon link (`/favicon.svg`, the book's small mark). `web/xc-logo.svg` is
  the wool mark for straps. Fjord (dark) exists only on `data-theme="dark"`;
  the live site stays Wool because the legacy templates can't follow a theme.
- `docs/brand/vintage-nordic-print.md` and `docs/BRAND_GUIDELINES.md` are
  retired/historical.
- Square corners and no elevation; the book allows only round eyelets
  (`border-radius: 50%`) and inset lines (button underline, eyelet rings).
- Copy rule: never self-describe as honest — "rated", not "honestly rated"

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
python scripts/generate_prep_kit.py             # output/{slug}/prep-kit/index.html (preflight requires one per profile)
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
- `test_race_profiles.py`: ~5,267 parametrized (227 profiles × ~23 tests each)
- `test_generators.py`: 23 tests
- `test_new_features.py`: 72 tests (GA4, consent, nav, CTA, training, coaching, security, Stripe, deploy, edge cases)
- `test_youtube.py`: 69 tests
- `test_data_quality.py`: additional data quality checks
- Total: ~7,970 passing

## Website Pages (generated)
- **Race pages**: 227 (`output/{slug}/index.html`) — with GA4, consent, nav, sticky CTA, training section
- **Prep kits**: 227 (`output/{slug}/prep-kit/index.html`) — linked from the race-page gate and day-0 kit emails
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
- **Consent**: Gravel God's region-aware model (Matti, 2026-11-14). `scripts/consent.py` is the only consent code: `get_ga4_head()` in `<head>`, `get_consent_banner_html()` before `</body>`. Analytics defaults to granted outside EEA/UK/CH (browser timezone) unless `xl_consent=declined`; EEA/UK/CH or an unreadable timezone defaults to denied and shows the banner; ad_storage/ad_user_data/ad_personalization always denied; `wait_for_update: 500`. "Privacy choices" link on every page reopens the banner. Nothing goes to Google unless analytics is granted (Matti, 2026-11-15): a declined or not-yet-answered visitor never loads gtag.js or runs `gtag('config')`; Accept loads and configures them without a reload (`window.xlAnalyticsStart`), Decline sets `ga-disable-<id>` and drops later events (`window.xlAnalyticsStop`). Events sent before Accept are dropped, not replayed. A checkout `?session_id=` is stripped from the URL before config (`window.xlCheckoutSessionId`).
- **Embedded in**: All generated pages (race, training, coaching) — NOT via mu-plugins. `tests/test_consent.py` fails if a page configures GA4 any other way. Exception: `wordpress/generate_questionnaire.py` still has its own snippet (pending its FormSubmit move).
- **No browser `purchase` events**: success pages are reachable with any `?session_id=`, so they fire only non-revenue views.

## Known Pitfalls (additions)
29. **Mu-plugins don't work on static sites** — xcskilabs.com has no WordPress. GA4, consent, nav must be embedded directly in HTML generators, not PHP mu-plugins. The `wordpress/mu-plugins/` directory is kept for reference only.
30. **Stripe price extraction needs regex** — `word.isdigit()` fails on "4-week". Use `re.search(r'(\d+)', nickname)`.
31. **Cookie consent must fire before GA4** — Set consent defaults in the same `<script>` block, before `gtag('config', ...)`. `scripts/consent.py` does this; never hand-write a GA4 snippet.
32. **Sticky CTA needs padding-bottom on body** — Without `padding-bottom: 80px`, the CTA overlaps the footer on short pages. Put it on `body`, not the page wrapper: the shared Privacy choices strip comes after the wrapper and must stay tappable.
33. **IntersectionObserver must guard entries** — Always check `entries.length > 0` before `entries[0]`. Wrap updates in `requestAnimationFrame`.
34. **Touch targets must be >= 44px** — WCAG 2.1 SC 2.5.5. Dismiss button needs `min-width: 44px; min-height: 44px`.
35. **`sync_search()` must fail on partial deploys** — Use `return success == len(files)`, not `return success > 0`.
36. **Post-deploy validation is mandatory** — Count `index.html` files on remote after tar+ssh upload. Partial deploys corrupt the site silently.
37. **FormSubmit.co needs `_next` redirect** — Without it, users see a generic third-party page after submit.
38. **Coaching form collects medical data** — Must have privacy policy notice before submit button.

## Agent skills

### Issue tracker

Issues live in GitHub Issues (`wattgod/xc-ski-labs`), via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: root `CONTEXT.md` + `docs/adr/` (created lazily by `/domain-modeling`). See `docs/agents/domain.md`.
