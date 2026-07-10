# X10a — Wax Bench port, part 1: tokens + race pages

READ FIRST, IN ORDER:
1. docs/BRAND_GUIDELINES.md — the ratified brand spec. It is law. §2 tokens, §3 type,
   §4 wax bar, §5 components, §8 enforcement.
2. docs/brand/reference-mock.html — the visual reference (race hero, wax bar, table,
   ladder band, scorebox). When guidelines and mock disagree, mock wins.
3. CLAUDE.md pitfalls (esp. #3 homepage stat IDs, #4 _safe_json_for_script, #8 regen
   after generator change, #32-34 CTA/observer/touch).

## Deliverables
1. **Rewrite `tokens/tokens.css`** with the §2 `--gl-*` token set exactly (delete every
   `--nl-*` token). Add the layout tokens you need (measure 1200px, spacing scale).
2. **Port `scripts/generate_race_pages.py`** to Wax Bench:
   - Import/inline tokens from tokens/tokens.css at generate time (read the file and
     embed — pages are static; NO inline hardcoded hex outside what tokens.css defines;
     a test must enforce generators contain no hex literals except via the tokens file).
   - Carbon race hero per mock: klister kicker (tier · series · country), display-caps
     name (system Helvetica/Arial 900 italic — NO new webfonts), italic serif tagline,
     white mono data chips, red scorebox rotated 2° with Lab Score.
   - **Wax bar** directly under the hero: 4 segments (green ≤−15 / blue −8..−15 /
     violet −2..−8 / red ≥−2, labels per mock). Parse the race's
     `race["climate"]["typical_temp_c"]` (string like "-15 to 0"); mark every segment
     overlapping that range with an "▲ RACE DAY" caret treatment (or highlight per mock).
     All 229 profiles have numeric typical_temp_c — but code defensively: if parsing
     fails, OMIT the bar entirely (never render unmarked/invented).
   - Reading sections: quiet — red numeral + display title section headers, serif prose
     ≤66ch on paper, hairline rules. Kill all Nordic Night blues.
   - Sticky CTA + GA4 + consent + nav: keep existing behavior, restyle to guidelines
     (carbon nav band, mono links, wordmark "XC SKI LABS" with LABS in red).
   - Product ladder band "GET RACE READY" before the footer, per mock §5: 4 rungs
     (Training plans /training-plans/, Custom plan /questionnaire/?race={slug},
     XC ski course — link /learn/ marked rel=nofollow ONLY IF the page exists, else
     omit the course rung for now, 1:1 coaching /coaching/apply/). Ghost buttons,
     red fill only on coaching APPLY.
   - Red footer strip per mock.
3. **Regenerate** all output (`python3 scripts/generate_race_pages.py`) and keep
   preflight + full pytest green. Update tests that pin Nordic Night colors/structure;
   ADD: no-hex-in-generator test, wax-bar-omitted-when-unparseable test, ≤1 red surface
   check if pinnable, banned-substring test ("honestly rated", "honest review",
   "unbiased", case-insensitive) over generated HTML.

## Hard constraints
- Do NOT touch race-data/, deploy.py, homepage/search/other generators (part 2).
- No new font files, no border-radius, no box-shadow, no entrance animations.
- Copy register unchanged — you are restyling chrome, not rewriting body copy. The only
  copy changes allowed: section header casing to match the new header style, and any
  literal "honestly" self-descriptions you find (say "rated").
- Final message: files changed, tests added/updated, pytest tail, how to preview one page.
