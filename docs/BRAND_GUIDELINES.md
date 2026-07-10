# XC Ski Labs — Brand Guidelines ("Wax Bench")

**Status:** Ratified by Matti 2026-07-09 ("ngl I like B a lot more" → "build a brand
guidelines comprehensive spec around this").
**Reference implementation:** `docs/brand/reference-mock.html` (+ `.png`) — when these
guidelines and the mock disagree, the mock wins until this doc is updated.
**Supersedes:** the "Nordic Night" cold-blue palette (inline `:root` blocks in
`scripts/generate_race_pages.py` / `generate_homepage.py`) and the orphaned `--nl-*`
`tokens/tokens.css`. Both are dead the day the port ships.
**Scope:** every xcskilabs.com surface — race pages, homepage, search, questionnaire,
about, training-plans, coaching, the course at `/learn/` (X12), emails, OG images.

---

## 1. The idea

The 90s wax bench: Swix-red boxes in a battered toolkit, color-coded kick wax, black
permanent marker on white tape, start-list typography. It's loud, technical, and
unmistakably *ski racing* — nostalgia the 45-year-old Birken skier feels in his hands.

The discipline that keeps it prestigious instead of cheesy:

> **Loud where the sport is loud. Quiet where you're actually reading.**

The shouting (900-italic caps, Swix red, diagonal stripes) is reserved for **chrome**:
heroes, section headers, CTAs, the score box. The **reading layer** — race intel, course
prose, tables — stays serif-on-paper, exactly as calm as the other Labs sites. The wax
colors are **data, not decoration**: they encode temperature (and only temperature).

This is the XC skin of the shared Labs Editorial skeleton (see
`gravel-god-cycling/docs/world-class-sites-spec.md` §2): full-bleed bands, 1200px
measure, prose capped at ~66ch, body painted, no border-radius, no box-shadow.

## 2. Palette — `--gl-*` tokens

Single source of truth: `tokens/tokens.css` (to be rewritten in the X10 port; generators
import it — **no inline `:root` palettes anywhere**).

| Token | Hex | Job | Never |
|---|---|---|---|
| `--gl-paper` | `#f2f0eb` | body background, reading bands | — |
| `--gl-carbon` | `#141414` | ink, dark bands, hard rules, nav | as a tint/opacity |
| `--gl-swix-red` | `#d3222a` | THE brand color: hero blocks, primary CTA, score box, active row | body text below 15px bold; more than one red block per viewport |
| `--gl-red-deep` | `#a8161d` | stripe partner, red hover | standalone |
| `--gl-klister` | `#ffd200` | kickers on dark, prices, nav-active | on paper (fails contrast); backgrounds |
| `--gl-wax-green` | `#0a7d4f` | temp band ≤ −15° | anything non-temperature |
| `--gl-wax-blue` | `#1266b3` | temp band −8…−15°; course-lesson header | anything non-temperature except lesson chrome |
| `--gl-wax-violet` | `#7a3f9d` | temp band −2…−8° | anything non-temperature |
| `--gl-white` | `#ffffff` | chips, scorebox text, cards on dark | — |
| `--gl-hairline` | `#d8d4c8` | table row rules, quiet borders | — |
| `--gl-muted` | `#8b877c` | table headers, captions, footnotes | body prose |

**Contrast floor (WCAG AA):** white on swix-red 4.9:1 ✓ (bold/large only — mono-caps
≥10px bold or text ≥18px); klister on carbon 11:1 ✓; white on wax-blue 4.6:1, wax-green
5.4:1, wax-violet 6.7:1 ✓ (bold mono-caps only); swix-red text on paper ≈4.6:1 — bold,
≥15px only. Never klister-on-red, red-on-carbon text, or violet-on-blue adjacency without
a white/carbon separator.

**Rationing rule (the anti-cheese law):** per viewport, at most ONE red surface (a hero,
a CTA, or the scorebox — not several), and the wax quartet appears only as the temperature
bar or a lesson header. Diagonal stripes appear only inside red or carbon hero blocks,
never on paper.

## 3. Typography — three fonts, three jobs (unchanged fonts, new display treatment)

| Layer | Face | Treatment |
|---|---|---|
| **Display** (H1/H2, section headers, ladder titles, CTAs-as-headlines) | Helvetica Neue / Arial (system stack) | **900 weight, italic, ALL-CAPS**, letter-spacing −0.01em, line-height 0.92–1.0. Zero webfont cost, period-correct. |
| **Data** (kickers, chips, tables, prices, nav, buttons) | Sometype Mono | 700 for emphasis, letter-spacing .1–.3em, uppercase |
| **Reading** (prose, taglines, FAQ answers, lesson body) | Source Serif 4 / Georgia | sentence case, 15.5–17px, line-height 1.55–1.7, max 66ch; italic for taglines/pull-quotes |

Rules:
- Display italic caps NEVER appears in running prose, table cells, or below 14px.
- Section headers: red numeral + display title (`01 COURSE OVERVIEW`) over a 3–4px carbon
  rule or on its own — never boxed, never bordered chrome around headers.
- The logo is set in display: `XC SKI LABS` with LABS in red on carbon (klister in the
  red footer). No drawn logo mark yet; the wordmark IS the mark.
- Hyphenate long race names in heroes with a real hyphen break (`BIRKEBEINER-RENNET`),
  don't shrink the type.

## 4. The wax bar — the house data language

The signature component. A full-width 4-segment strip in the wax quartet
(green/blue/violet/red with mono-caps temperature labels), used for exactly one thing:
**temperature**.

- **Race pages:** encodes the race's historical race-day temperature range from
  `race-data/{slug}.json` climate fields; the matching segment gets the `▲ RACE DAY`
  caret beneath. If climate data is missing, the bar is omitted entirely — never shown
  unmarked or invented (veracity rule).
- **Course:** lesson-header blue is the one sanctioned off-label use (waxing lessons may
  use the full bar pedagogically).
- Segments are labeled in mono caps with real ranges. The bar never becomes a generic
  progress bar, tier indicator, or decoration. Tier encoding stays typographic (T1–T4
  chips, carbon on white / white on carbon).

## 5. Layout & components

**Skeleton:** full-bleed bands; inner content `max-width: 1200px` (1160 + 24px padding is
the mock's compromise — pick 1200 in tokens); `body { background: var(--gl-paper) }`;
prose ≤66ch; `border-radius: 0` everywhere; no box-shadow; borders 1px hairline, 3px
frames, 4–6px statement rules only.

- **Nav:** carbon band, display wordmark left, mono links right, active link klister.
  Mobile: hamburger (ship it this time — Roadie's known gap), sticky, 44px targets.
- **Homepage hero:** red block, klister kicker, display headline ≤13ch/line, serif deck
  on pale red (`#ffecec`-equivalent via white at 88%… use solid `#ffecec` token if needed),
  white + carbon button pair, klister stat line. Stripes right, behind nothing readable.
- **Race hero:** carbon block variant, klister kicker, display name, italic serif tagline,
  white data chips (54 KM · CLASSIC · MARCH · ROUTE), red **scorebox** rotated 2°, wax bar
  immediately beneath the hero.
- **Scorebox:** red, white 900 display number, mono label. The 2° rotation is the ONLY
  rotated element on the site (marker-on-tape gesture). Rider Score, when present, sits
  beside it as a white box with carbon text (critic vs audience, RT mechanic).
- **Tables (database/search):** 3px carbon header rule, mono-caps muted headers, serif
  cells, hairline rows, T1–T4 chips, score in red only for tier-1/featured, `READ →`
  mono link.
- **Buttons:** mono caps 700. Primary = red fill/white. On dark: ghost white 2px border;
  the ONE conversion button per dark band may be red fill. On paper: carbon fill or
  carbon-border ghost. Never klister buttons, never red ghost on red.
- **Product ladder band ("GET RACE READY"):** carbon band, 4 rungs (`Plans / Custom /
  Course / Coaching`), each `#1d1d1d` card with 6px red top rule, klister rung-kicker +
  price, ghost buttons — red fill reserved for coaching APPLY. This band ships on every
  high-intent page (race pages, hubs, course index) — church/state: it is its own band,
  never interleaved with intel.
- **Course lesson card:** 3px carbon frame, wax-blue header (display title + mono label),
  serif body, red-on-hairline progress bar.
- **Footer:** red strip, wordmark + mono motto (`BUILT FOR SKIERS WHO CHASE START LINES`),
  above a carbon mega-footer (links, legal) if/when needed.
- **Pull quotes:** 6px red left rule, serif italic. **Email capture:** paper band, carbon
  frame, mono button — one per page max (X3).

## 6. Imagery & graphics

- **No AI-generated photography. No stock.** Until real race/athlete photography exists,
  the site is type + color + drawn data.
- Sanctioned graphics: the wax bar; diagonal stripe fields (hero blocks only); survey-plate
  style SVG data drawings (elevation ticks, tier distributions) in carbon/red hairline on
  paper — the WS-B plate language wearing Wax Bench colors; race-course line art.
- OG images: red or carbon plate, display race name, scorebox, wax bar strip. Generated,
  consistent, no photos.

## 7. Voice

Copy register is unchanged from the estate rule (Claude register — understated, brief,
concrete; Sultanic structure; Normie Test; no defensive messaging; no fabricated claims):
**the design shouts so the words don't have to.** Display-caps headlines are short
factual statements ("EVERY LOPPET, RATED." / "GET RACE READY"), never hype
("UNLEASH YOUR POTENTIAL" is a firing offense — slop_rules applies). Body copy would read
correctly on the Amundsen design; only the chrome knows about Swix.

**Never self-describe as honest** (Matti, Jul 9 2026: "I don't want copy on the website
to say Honestly Rated; just say rated"). "Honestly rated", "honest reviews", "unbiased",
"trustworthy" — same family as "no sponsors": claiming the virtue plants the doubt. Say
"rated", "scored", "reviewed"; let the T4s on famous races do the proving.
(RestraintGuard enforces: banned substrings `honestly rated`, `honest review`, `unbiased`.)

## 8. Enforcement (ships with the port)

- `tokens/tokens.css` is the only place hex values live; a test greps generators for
  hex literals and inline `:root` blocks (port of gravel's token guard).
- RestraintGuard (E1): ≤1 red surface per template section; wax colors only in
  `gl-waxbar`/lesson-header classes; no display-italic class on prose elements; no
  banned phrases; no "no sponsors" framing.
- Wax bar only renders when climate data exists (test with a climate-less fixture).
- Contrast: automated check that klister never sits on paper/red, red text ≥15px bold.
- Existing suites (7,987 tests) must stay green through the port; visual before/after
  screenshots on: homepage, Birkebeinerrennet, a T4 race, search, questionnaire, about,
  training-plans — Matti reviews before deploy (A2-style gate).

## 9. Migration map (X10 execution order)

1. Rewrite `tokens/tokens.css` with §2 tokens; delete the `--nl-*` corpse.
2. Extract shared band/nav/footer/button CSS builders (consume the gravel `shared_bands`
   pattern when A1 lands; until then, a local `wordpress/brand_css.py`).
3. Port order: race pages (`scripts/generate_race_pages.py`, incl. wax bar from climate
   data) → homepage → search UI (`web/nordic-lab-search.html`) → questionnaire/about →
   training-plans/coaching (add ladder band + X11 Stripe checkout) → course `/learn/`
   (X12, lesson cards per §5).
4. Emails and OG images last.
5. Deploy per `scripts/deploy.py --deploy-all` + post-deploy count validation + crawler run.

---
*Related: `gravel-god-cycling/docs/world-class-sites-spec.md` (X10–X12), Amundsen and
Lillehammer exploration mocks in session scratchpad (kept for the record: warm-wool and
cobalt directions were considered and declined Jul 9 2026).*
