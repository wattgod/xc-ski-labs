TASK: X13/X14 — race-page hero art plates + Rise-style interactive blocks.
This branch contains the full Wax Bench port (X10a/b). Study docs/BRAND_GUIDELINES.md,
docs/brand/reference-mock.html, and scripts/generate_race_pages.py before writing code.
Everything below goes into scripts/generate_race_pages.py (+ helpers) and tests.

## 1. Hero art plates (inline SVG, brand tokens via CSS classes — SVG attrs can't
   resolve var(), so use class-styled shapes; hex only inside tokens-derived CSS)

Two tiers, auto-selected per race:

**Tier A — course plate** (renders ONLY when a real route file exists at
`art/gpx/{slug}.gpx`): parse the GPX (stdlib xml.etree; tolerate trkpt/rtept), extract
elevation series + total distance; downsample to ≤80 points; render as the PoC's
"elevation massif" — filled dark-red mountain silhouette with a red stroke and
klister-dot overlay along the profile, mono-caps labels for START (name+elev), HIGH
POINT (elev), FINISH (name+elev), placed with collision-safe anchors. Start/finish
display names: derive from vitals.location or a "route" hint; if unknown, label
START/FINISH only. Record every plate in `art/manifest.json`:
{slug: {tier: "A", source: "art/gpx/{slug}.gpx", license: "<from art/gpx/{slug}.license
if present else 'UNVERIFIED — do not deploy'"}}. If the license file is missing, still
render locally but preflight-style test must WARN.

**Tier B — data plate** (all other races): abstract terrain line-art (decorative ridge
lines — do NOT claim real geography) + the race's REAL scalars as typographic art:
distance_km, elevation_m (gain), altitude_m when present, discipline, start/finish
squares connected by a red route stroke labeled "{distance} KM". Everything from
race-data vitals; omit any missing figure rather than inventing.

The plate replaces the diagonal-stripes filler on the hero's right side (stripes stay
as plate background texture if it helps). Text column keeps priority; plate is
aria-hidden decorative with the data duplicated in visible text elsewhere.

## 2. Interactive blocks (new section between COURSE OVERVIEW and the rating section)

Port the Rise-block feel (reference: /Users/mattirowe/Documents/NordicLab/
glide-labs-platform/course/templates/blocks/ for markup patterns — read, adapt to Wax
Bench, do NOT import Jinja2):

a) **Process stepper "RACE WEEK"** — 3 steps in the PoC style (carbon number cells,
   klister numerals): generic race-week protocol parameterized with the race's name,
   discipline (classic/skate/both wording), and date field. Educational template
   content — factual, no hype.
b) **Wax flip cards "WAX CALL"** — 3 tap-to-flip cards derived from the race's
   typical_temp_c range: pick the 3 wax bands overlapping/adjacent to the range, front
   = temp scenario, back = standard kick-wax guidance (hardwax blue/violet, klister at
   0°+; keep guidance generic-correct, no brand product claims). Cards use the wax
   band colors (sanctioned: this is temperature). Click via addEventListener — NO
   inline onclick anywhere (also fix the two existing inline onclick hamburger handlers
   in generate_race_pages.py and generate_homepage.py while you're there).
c) **Knowledge check** — ONE question generated from the race's real profile facts,
   preferring history.founded ("Founded in ___?" with 3 plausible-year options, correct
   from data) or falling back to distance. Correct/wrong states per PoC (wax-green/
   swix-red). Below the result: one quiet mono link "Build my {race} plan →
   /questionnaire/?race={slug}". If the needed fact is missing, omit the whole block.

## 3. Tests + validation
- Unit tests: GPX parser (fixture file), tier selection (A when gpx exists, B
  otherwise), manifest writing, wax-card band selection from temp range, quiz fact
  correctness (correct answer matches profile data), no inline onclick left in
  generators, blocks omitted when data missing.
- Regenerate all 229 pages; python3 scripts/preflight.py PASSES; python3 -m pytest
  tests/ -q fully green (update pinned tests as needed).
HARD RULES: no race-data/ modifications; no network calls at generate time; no deploy;
no new fonts; blocks JS must be dependency-free and tiny. Final message: files changed,
test tail, preflight result.
