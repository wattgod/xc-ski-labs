# XC Ski Labs Race Data Audit Report

**Date**: 2026-03-10
**Total profiles checked**: 218

## Summary

| Category | Count |
|----------|-------|
| Score math mismatch | 0 |
| Tier incorrectness | 0 |
| Missing required fields | 0 |
| Missing criteria (14 required) | 0 |
| Criteria out of range (1-5) | 0 |
| Criteria type errors | 0 |
| Slug/filename mismatch | 0 |
| Invalid discipline value | 0 |
| Duplicate slugs | 0 |
| Duplicate names | 1 |
| YouTube data structure issues | 0 |
| YouTube data missing entirely | 0 |
| Empty taglines | 0 |
| Suspiciously short taglines | 0 |
| JSON parse errors | 0 |
| Missing race key | 0 |

**Total issues**: 1

## Duplicate names (1)

- name="Traversee du Massacre": appears in TWO files with different slugs and scores:
  - `traverse-du-massacre.json` (slug: `traverse-du-massacre`, score: 69, tier: 2)
  - `traversee-du-massacre.json` (slug: `traversee-du-massacre`, score: 57, tier: 3)
  - **Action needed**: Determine which is the canonical profile and remove or merge the other.

## Checks Passed (no issues)

- Score math: All 218 profiles have `round((sum_of_14_criteria / 70) * 100) == overall_score`
- Tier correctness: All tiers match score thresholds (T1>=80, T2>=60, T3>=45, T4<45)
- Required fields: All profiles have name, slug, display_name, tagline, vitals.country, vitals.distance_km, vitals.discipline, vitals.date, overall_score, tier
- All 14 criteria present in every profile, all values in 1-5 range
- Every slug matches its filename
- All discipline values are valid ("classic", "skate", or "both")
- No duplicate slugs
- All profiles have youtube_data with videos array and rider_intel (object or null)
- No empty or suspiciously short taglines
- No JSON parse errors

