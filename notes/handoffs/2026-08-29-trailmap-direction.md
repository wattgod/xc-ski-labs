# Handoff — XC Ski Labs trail-map redesign

**Branch:** `claude/xcski-land-ui-redesign-aey5os` (wattgod/xc-ski-labs)
**Status:** direction exploration complete and data-bound. **Port not started.**
**Preview:** `docs/brand/trailmap-site.html` (generated — do not hand-edit)

## What this is

Matti rejected the shipped "Wax Bench" brand and asked for the site to be modeled
on a 1980s hand-drawn Devil's Thumb Ranch nordic trail map. This branch explores
that and stops at the gate before the port.

## Decisions made

- **The map's value is its legend, not its texture.** Its symbol vocabulary maps
  onto fields already stored: circle/square/diamond/double-diamond render
  `course.technical_rating`; the climb ladder renders any 1–5 criterion; the star
  is a real feed station; a dashed rule marks an unverified claim. Tier stays
  typographic (T1–T4) — course difficulty and race quality are different axes.
- **Three moves recommended, one held back.** Network (browse surface),
  Groomer's Note (race page), Someone's Copy (treatment). The Fold-Out was built
  but held: it puts a single-page app between Google and 229 pages.
- **Five dials** ship as a token layer: direction, colour, spacing, texture,
  rules. Direction changes *layout*, not just palette — Amundsen is a ruled field
  log, Ralph is a centred plate wall.
- **My recommendation, not yet signed off:** direction Paper, colour
  signage + alarm, spacing dense, texture subtle, rules heavy.

## Not decided — needs Matti

1. Which direction and dial settings become the defaults in `tokens/tokens.css`.
2. Whether `docs/BRAND_GUIDELINES.md` is rewritten. It currently documents Wax
   Bench as ratified 9 Jul 2026 and records warm-wool (= Amundsen) as
   *considered and declined*. Whatever is chosen, that doc must be rewritten in
   the same commit as the tokens or the spec lags the code.

## Traps

- **`trailmap-site.html` is generated.** Edit
  `docs/brand/trailmap-site.template.html` then run
  `python scripts/trailmap_preview.py`. `tests/test_trailmap.py::test_committed_build_is_current`
  fails on a stale build.
- **Provenance fields do not exist.** `surveyed_on`, `surveyed_how`,
  `fact_checked_on`, `source_count`, `note_written_on`, `note_method` are declared
  in `PROPOSED_SCHEMA` in `scripts/trailmap_preview.py`. The "Someone's Copy"
  treatment and the Amundsen field record **cannot ship** until a migration adds
  them. A test fails if that list grows.
- **~220 of 229 races have no note and no survey.** The unvisited state is
  first-class by design; do not fill it with generated prose.
- Google Fonts is blocked to the browser in this sandbox. To screenshot, inline
  the woff2 files; the published artifact loads them normally.
- Theme-scoped layout overrides must be wrapped in their breakpoint (lesson 63).

## Next session — the port, in this order

1. `tokens/tokens.css` → chosen direction's palette; rewrite `BRAND_GUIDELINES.md`
   in the same commit.
2. `wordpress/trailkey.py` — shared glyph defs, climb-ladder builder, legend,
   difficulty mapper, stamp/wear components. One source, fifteen consumers.
3. `scripts/trailmap_network.py` is already production-shaped — wire it into the
   search/database build.
4. `scripts/generate_race_pages.py` (229 pages, the hardest surface).
5. `generate_homepage.py` + `web/nordic-lab-search.html` → note that the deploy
   reads `output/search/`, not `web/`.
6. The eleven WordPress generators, then guide/legal/prep-kit, feeds, OG images.
7. Guards: token-only hex rule; a legend test that fails if a glyph renders with
   no backing field; a wear test that fails if a stamp renders with no
   verification date.

## Files

| Path | Role |
|---|---|
| `scripts/trailmap_network.py` | Trail-network SVG from `series_membership` |
| `scripts/trailmap_preview.py` | Builds the preview from `race-data`; holds `PROPOSED_SCHEMA` |
| `docs/brand/trailmap-site.template.html` | Template — edit this |
| `docs/brand/trailmap-site.html` | Generated output |
| `docs/brand/trailmap-preview-manifest.json` | Every rendered value + provenance |
| `docs/brand/trailmap-directions.html` | The four-readings review page |
| `tests/test_trailmap.py` | 25 tests: network, generator, contrast |
