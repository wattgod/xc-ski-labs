# XC Ski Labs — Lessons Learned

Hard-won lessons from building the Nordic race database. Each one represents a real bug or silent failure.

## Security

1. **Never hardcode API keys in scripts.** `batch_enrich.sh` had the full Anthropic key on line 5. Fixed to load from `.env`. Always check: is this file committed? Is the key in git history?

2. **`.env` must be in `.gitignore` before the first commit.** Ours was — verify with `git log -p -- .env` to confirm it was never tracked.

3. **Preflight security scan can match itself.** A regex like `sk-ant-` will match the literal regex string in the scanner script. Skip the scanner file when checking for leaked keys.

## Data Integrity

4. **Slug must match filename exactly.** `foo-bar.json` must contain `"slug": "foo-bar"`. The parametrized test suite catches this for every profile.

5. **Duplicate profiles are silent killers.** `traversee-du-massacre.json` and `traverse-du-massacre.json` both existed with different scores. Only caught by slug uniqueness test. Always run `test_no_duplicate_slugs` and `test_no_duplicate_display_names`.

6. **Score math is non-negotiable.** `overall_score = round((sum_of_14_criteria / 70) * 100)`. The denominator is 70 (legacy from Gravel God). Every profile is validated by `test_score_math`.

7. **Tier assignment has prestige overrides.** Base tier from score thresholds (80/60/45), but prestige=5 forces T1 (if score>=75) or caps at T2, and prestige=4 promotes one tier (not into T1). Both preflight and tests validate this.

8. **Delete output when deleting profiles.** After removing `traversee-du-massacre.json`, its `output/traversee-du-massacre/` directory still existed, causing a count mismatch (218 pages vs 217 profiles).

9. **Estonian spelling: "maraton" not "marathon".** Homepage linked to `tartu-marathon` but the profile slug is `tartu-maraton`. Caught by `test_homepage_no_broken_race_links`.

## HTML Generation

10. **`</script>` in embedded JSON breaks the page.** If race data contains `</script>` (e.g., in a tagline or quote), the HTML parser closes the script block early. Always use `_safe_json_for_script()` to replace `</` with `<\/`.

11. **`undefined` and `null` in visible HTML = template bug.** `test_no_undefined_or_null_in_visible_text` strips script/style blocks and checks the remaining HTML. Catches template rendering failures.

12. **JSON-LD must be valid JSON.** `test_json_ld_valid` parses every `application/ld+json` block. After unescaping `<\/` back to `</`, the JSON must parse cleanly.

13. **Every page needs DOCTYPE.** `test_every_page_has_doctype` catches pages where the generator silently emitted partial HTML.

14. **Homepage stat IDs are a contract.** `preflight.py` uses regex `id="statRaces">(\d+)` to verify homepage stats match profile counts. Changing the ID format silently breaks preflight validation.

## Branding

15. **It's "XC Ski Labs", not "Nordic Lab".** The project folder is `nordic-race-automation` and CSS vars use `--nl-*`, but the user-facing brand is XC SKI LABS. `test_no_nordic_lab_in_race_pages` catches title tags that still say "Nordic Lab".

16. **Font stack must be consistent.** Race pages and homepage must both use Sometype Mono + Source Serif 4 + Inter. `test_consistent_font_stack` verifies this.

## Search Index

17. **Index field names are compact.** `n`=name, `s`=slug, `t`=tier, `sc`=score, `di`=discipline, `co`=country, `st`=search_text. Tests expected `sl` for slug — wrong. Always check `generate_race_index.py` for the actual field mapping.

18. **Index count must match profile count.** `test_index_race_count_matches_profiles` and `check_search_index()` in preflight both verify this. Stale index after adding/removing profiles is a common failure.

## YouTube Enrichment

19. **`video_id` can be int from the API.** Claude sometimes returns `12345` instead of `"12345"`. `validate_enrichment()` must coerce to str before regex validation.

20. **Search files must be copied to output/search/ after web/ changes.** The deploy script reads from `output/`, not `web/`. Forgetting this means the live search page is stale.

## Deploy

21. **SiteGround, not GitHub Pages.** This project deploys via tar+ssh to SiteGround, same as Gravel God. The user explicitly rejected GitHub Pages.

22. **Always purge SiteGround cache after deploy.** Pages look stale without it.

23. **Race page URLs use `/race/{slug}/` in production.** Output is flat (`output/{slug}/index.html`), but homepage links use `race/{slug}/` prefix because that's the production structure.

## Process

24. **Regenerate output after editing generators.** Changing `generate_race_pages.py` doesn't update `output/`. You must re-run the generator.

25. **Preflight before every deploy.** `python scripts/preflight.py` catches score mismatches, missing fields, stale stats, branding drift, index drift, and security issues. Use `--deploy` flag to chain validation → deploy.

26. **Tests are the safety net, not manual review.** 5,090 parametrized tests caught the Tartu Maraton typo, the Massacre duplicate, and the search index field name — all things a human reviewer would miss at scale.

27. **Tagline validation: match exactly, not by substring.** "America's largest cross-country ski race" is specific. "A cross-country ski race" is generic. The test uses an exact-match list of truly generic phrases plus a minimum length check.

28. **Token limits on batch operations.** Creating 54 profiles in one agent hit the 32K output limit. Split into 3 parallel batches of ~18 each.

## Data Integrity (Round 2)

29. **AI fact-checking AI is circular.** We used Claude to generate profiles, then Claude to verify them. 101/122 elevation values came back "UNCERTAIN". Use Perplexity (web-grounded) for real fact-checking. Claude-on-Claude is sanity checking at best.

30. **AI-generated races can be fictional.** 9 T2 races had zero web presence — no website, no search results. `besseggen-pa-langs`, `lavaredo-ski-marathon`, `peer-gynt-skimaraton` may be hallucinated events. Always verify race existence for T1/T2.

31. **Different agent batches create different schemas.** Batch 1 profiles have `vitals.website`, batch 4 has `logistics.official_site`. Some have `climate`, `course.primary` — others don't. Run `normalize_profiles.py` after every bulk creation.

32. **`field_size_estimate` type must be enforced.** Found `"~8,000 starters"` (string) instead of `8000` (int). One bad type cascades — templates, search index, and sort all break silently.

33. **Auto-fix changes vitals without updating criteria.** Elevation went 500→1200m but `elevation` criterion stayed at 3. The criteria-to-vitals consistency test now catches this drift.

34. **Semantic duplicates hide under different slugs.** `holmenkollen-skimaraton` and `holmenkollmarsjen` are the same race. Slug uniqueness tests don't catch this. Need fuzzy name matching + shared-website detection.

35. **YouTube enrichment "success" is just exit code 0.** The batch script doesn't validate content quality. Wrong-sport videos, indoor trainers, and slideshows can pass through as "enriched."

36. **132/386 official URLs were dead.** Most were AI-hallucinated domains (e.g., `beitomaraton.no`, `besseggenpalangs.no`). URL validation must run before any deploy.

37. **Vasaloppet sub-event URLs all had stale paths.** Nattvasan, Öppet Spår, Stafettvasan, Kortvasan — all linked to old URL patterns. The main site restructured and broke all deep links.

38. **Search files require manual copy to output/search/.** No automated step, no test. Easy to forget. Added `test_search_dir_exists_and_current` to catch this.

39. **`_fact_check_fixes` metadata pollutes profiles.** Auto-fix tools wrote internal arrays into race JSON. Generators and tests don't expect these keys. Must clean up after auto-fix.

40. **http:// URLs should be https://.** Some profiles had `http://` official sites. Modern browsers show warnings. Normalize to https:// everywhere.

## Website & Monetization (Sprint — Mar 2026)

41. **WordPress mu-plugins are dead code on a static site.** xcskilabs.com deploys static HTML via tar+ssh. PHP mu-plugins (`xl-ga4.php`, `xl-header.php`, `xl-cookie-consent.php`) require WordPress hooks to execute. They were deployed to `wp-content/mu-plugins/` but never ran. Solution: embed GA4, cookie consent, and nav directly in the Python HTML generators. The mu-plugins directory is kept for reference only.

42. **GA4 must be consent-gated.** The GA4 snippet must check the `xl_consent` cookie before calling `gtag('config', ...)`. If consent is `declined`, GA4 must not fire. Set Consent Mode v2 defaults in the same `<script>` block, *before* the `gtag('config')` call, not in a separate file with race conditions.

43. **Cookie consent banner must appear on every generated page.** Static sites don't have a global template injector (no `wp_footer` hook). Every generator (`generate_race_pages.py`, `generate_training_plans.py`, `generate_coaching_apply.py`) must independently emit the consent banner HTML+JS+CSS. A shared function helps, but the output must be self-contained.

44. **Stripe price extraction: `word.isdigit()` fails on "4-week".** The nickname format from Stripe is `"4-week plan ($60)"`. Splitting on spaces and checking `.isdigit()` on each word returns nothing. Use `re.search(r'(\d+)', nickname)` to extract the week number. The bug was silent — it fell back to hardcoded pricing, so users saw correct-looking but disconnected-from-Stripe prices.

45. **Sticky CTA overlaps footer without padding.** `position: fixed; bottom: 0` on the CTA bar means it covers the last ~60px of content. Add `padding-bottom: 80px` to `.gl-page` so footer text is never obscured.

46. **IntersectionObserver: always guard `entries[0]`.** The callback can theoretically receive empty entries. Always check `if (entries.length > 0)` before accessing `entries[0].isIntersecting`. Wrap the DOM update in `requestAnimationFrame` to prevent layout thrash during rapid scroll.

47. **Touch targets must be >= 44×44px.** WCAG 2.1 SC 2.5.5. The sticky CTA dismiss button (×) originally had `padding: 4px 8px` — too small for mobile. Increased to `12px 16px` with `min-width: 44px; min-height: 44px`.

48. **`sync_search()` returned True on partial deploys.** `return success > 0` meant deploying 1 of 3 search files was considered "success". Changed to `return success == len(files)`. Any partial deploy is a failure.

49. **Post-deploy validation catches partial tar+ssh uploads.** If SSH drops mid-transfer, some race pages are updated and others are stale — silently corrupting the site. After upload, SSH into remote and count `index.html` files. Compare to expected count. Print WARNING on mismatch.

50. **`.htaccess` touch does NOT purge SiteGround's static cache.** This was cargo-cult code that gave a false "Cache invalidated" success message. SiteGround's dynamic cache must be flushed via Site Tools UI (Speed → Caching → Flush Cache). The deploy script now prints actionable instructions instead of pretending it worked.

51. **FormSubmit.co needs `_next` redirect.** Without a `<input type="hidden" name="_next" value="...">`, users see FormSubmit's generic third-party thank-you page after submitting the coaching form. Add `_next` pointing to `?submitted=true` on the same page, then show a branded success message via JS.

52. **Coaching form collects medical data — privacy notice is mandatory.** The intake form asks about injuries, allergies, and medications. A "By submitting, you agree to our Privacy Policy" notice must appear before the submit button. This isn't optional.

53. **Double-submit protection on forms.** Disable the submit button and change text to "SUBMITTING..." on click. Re-enable after 5 seconds as a safety valve. Without this, users click multiple times and the coaching inbox gets duplicates.

54. **localStorage can silently fail.** Private browsing, quota exhaustion, or disabled storage all cause `localStorage.setItem()` to throw. The original code had an empty `catch(e) {}`. Now shows a "Storage full — please submit now" toast so users know their draft isn't being saved.

55. **Input validation bounds prevent garbage data.** Without `min`/`max` on numeric fields, the coaching form accepted age=-5, VO2max=9999, weight=0. Added: age 16-100, weight 30-200kg, height 100-230cm, VO2max 20-90, FTP 50-500W. Textareas capped at 2000 chars.

56. **Hardcoded hover colors bypass the token system.** `.gl-cta-btn:hover { background: #9a3e15; }` won't update when the brand palette changes. Define hover variants as tokens: `--gl-wax-orange-hover: #9a3e15` and reference via `var()`.

57. **Focus-visible styles are required on every interactive element.** Without `:focus-visible` CSS, keyboard-only users can't see which element has focus. Added `outline: 3px solid var(--gl-wax-orange); outline-offset: 2px` to all `a` and `button` elements across all generators.

58. **72 new tests prevent regression on all of the above.** `test_new_features.py` covers: GA4 presence + consent gating, cookie banner on all pages, nav header, sticky CTA (existence, questionnaire link, dismiss, touch target, z-index, session storage), training section (existence, cards, CTA URL, missing data handling), IntersectionObserver (entries guard, rAF), accessibility (focus-visible, skip link), training plans page (Stripe prices, FAQ escaping, responsive grid, JSON-LD, canonical), coaching form (noindex, validation bounds, double-submit, localStorage errors, redirect, privacy, maxlength, XC terminology), security (script injection, JSON safety, name escaping, no API keys), Stripe products (count, IDs, price range), deploy (no mu-plugins, sitemap, partial deploy, post-validation), and edge cases (special chars, footer overlap, dynamic race count).
