# XC Ski Labs brand book: Sledge Stores · Splash on wool

> **Locked by Matti on 2026-11-14.** This is the ratified XC Ski Labs brand. It was copied from the private design-system artifact (version 11).
> - Colour, type, spacing and line values live in `tokens.json`.
> - Component CSS is in `components/bundle.css`, with each component's rules and a preview in `components/<Name>/`. Each preview links `tokens/tokens.css`, which `scripts/build_brand_tokens.py` builds from `tokens.json` and `bundle.css`; the live site embeds the same file.
> - The live site runs this book since 2026-11-15: `tokens/tokens.css` is built from `tokens.json` and `bundle.css` by `scripts/build_brand_tokens.py`.
> - Background is in `rationale.md`. The competitor check is in `separation.md`.

XC Ski Labs looks like an expedition outfitter's stores: wool canvas, oat crates with timber slats, navy stencils, shipping tags, and one salmon thing per screen. The mood is early polar expeditions, when skiers packed every gram by hand and labelled every crate. The page reads like a packing manifest. Prices are stencilled big, stats hang off crates on luggage tags, lessons are a checklist, and the fine print is a tag tied to the box. Salmon is the splash. It is never the background. It marks the one crate worth opening first.

These rules apply to every XC Ski Labs surface:
- xcskilabs.com: homepage, race pages, search, questionnaire, training plans and coaching
- the course
- emails
- Open Graph images
- print

**Locked 2026-11-14 (Matti).** The name is XC Ski Labs. Changing anything below needs Matti's yes and a decision-log line.

**What this version ratifies.** Identity (mark, lockup, colour, type) and the course storefront (hero, crates, tags, checklist). Race pages, the questionnaire, emails and print are in scope, but stay blocked until their components and rules are specified. Web fonts don't load in most mail clients, so email needs its own type rules: **Not specified yet**.

Where this book and an older XC document disagree, this book wins. Anything marked **Not specified yet** has no rule. Don't invent one in a template; raise it, and the book gets a rule first.

The reference build is the "Sledge Stores · Splash on wool" mockup of /course/, chosen by Matti on 2026-11-14. It is in the salmon studies artifact.

## 1. Principles

1. **Stores, not a poster.** Every surface is built from outfitter objects: a canvas page, oat crates, stencilled heads, luggage tags, a packing checklist, shipping tags. If a block isn't one of those, it is plain body text on wool.
2. **Salmon is a splash.** One salmon object per page: one crate or one checklist row, never a band, hero, strap or page ground. The only other salmon is the 5px underline inside buttons and one ski in the mark. A second salmon object means the page is wrong. Documentation artwork, such as the cover of this book, is exempt.
3. **The splash means "start here".** The salmon crate is the current object if there is one: the lesson you're on, this week's training. On a sales page with nothing current, it is the recommended purchase, labelled with the word Recommended. Pages that only inform have no salmon object.
4. **Ink does the work.** Text, rules, stencils, the header and footer straps and buttons all use the ink colour: navy in Wool, wool in Fjord. Buttons are found by shape (a solid `action` slab), not by a colour of their own. The salmon underline is decoration and never the only cue.
5. **Big stencilled numbers.** Prices are stencilled at crate size: `$29`, `$49`. Counts hang on tags in words and digits: `3 lessons, 14 clips`.
6. **Real or nothing.** No AI-generated or stock photography, no invented data, no fake reviews.
   - A count states what it counts. The course has 31 unique filmed clips across all its lessons, the basics included; the Classic module has 14 and the Skate module 16. Those three numbers come from the course content and its tests (`xc-ski-labs/tests/test_course_page.py`); never add or subtract them by hand.
   - Missing optional images collapse.
   - A missing image the task needs shows an empty stitched slot with a label.
7. **Legible at 320.** Every surface reflows at 320 CSS px and is checked at 390, 768, 1024 and 1440. Nothing goes under 11px, and running text is never under 15px. Touch targets are 44px; buttons are 56px.
8. **Flat canvas.** No elevation shadows, glows or tonal gradients. Flat repeating patterns draw the weave and the slats, and an inset line draws the button underline. Depth comes from stacked panels, stitching and slats, never from elevation.

## 2. Colour

Every hex lives in `tokens.json`. A hex literal anywhere else is a bug. The exceptions are the logo SVGs and print files.

### Light (Wool) and dark (Fjord)

| Token | Wool (light) | Fjord (dark) | Job | Never |
|---|---|---|---|---|
| `ground` | `#f1e9dc` wool | `#1e2b3c` navy | The page, with the canvas weave | A crate |
| `panel` | `#ddd0bc` oat | `#263649` | Hero, crates, photo pocket, banded sections | Text colour |
| `paper` | `#f1e9dc` | `#263649` | Lists and the fine-print strip on a panel | — |
| `tag-paper` | `#f1e9dc` | `#ddd0bc` | Shipping and luggage tags, light in both themes | — |
| `on-tag` | `#1e2b3c` | `#1e2b3c` | Text and eyelet rings on tags | — |
| `strap` | `#1e2b3c` | `#141d29` | Header and footer straps | Content sections |
| `on-strap` | `#f1e9dc` | `#f1e9dc` | Text and links on a strap | — |
| `ink` | `#1e2b3c` | `#f1e9dc` | Text, stencils, rules, outlines | — |
| `ink-2` | `#4a5566` | `#c9c0b0` | Secondary text | Headings |
| `rule` | `#6e4b36` tobacco | `#9a8b76` | Dashed list rules, dotted planned outlines | Text |
| `action` | `#1e2b3c` | `#f1e9dc` | Button fill | Decoration |
| `on-action` | `#f1e9dc` | `#1e2b3c` | Button text | — |
| `splash` | `#e3876d` salmon | `#e3876d` | The one start-here crate or checklist row, the button underline, one ski in the mark | Bands, heroes, straps, grounds, text on light grounds, a second object |
| `on-splash` | `#1e2b3c` | `#1e2b3c` | Text, stitch and the button slab on salmon | — |
| `on-splash-action` | `#f1e9dc` | `#f1e9dc` | Button text on the salmon crate's navy slab, both themes | — |
| `splash-deep` | `#b85c47` | `#b85c47` | Slats on the salmon crate | Anything else |
| `splash-ink` | `#9a4a39` | `#e3876d` | Salmon as text, on wool or navy only | Oat (4.1:1) |
| `done` | `#3d5a45` moss | `#8fb39a` | Finished lessons, owned modules, confirmed payments | Decoration |
| `on-done` | `#f1e9dc` | `#1e2b3c` | Text on done | — |
| `danger` | `#a8321f` | `#ff9a85` | Errors, with a word and an icon | Oat, prices |
| `focus` | `#1e2b3c` | `#f1e9dc` | 3px focus ring, 3px offset | — |

**Contrast** (WCAG 2, calculated from the hexes):

| Pair | Ratio |
|---|---|
| navy on wool | 11.9:1 |
| navy on oat | 9.4:1 |
| navy on salmon | 5.4:1 |
| wool on navy | 11.9:1 |
| wool on `#263649` | 10.2:1 |
| `ink-2` (weakest pair) | 5.0:1 |
| `splash-ink` on wool | 5.1:1 |
| salmon on navy | 5.4:1 |
| `rule` dotted marks on panel | 5.1:1 light, 3.7:1 dark |
| `on-done` on `done` | 6.4:1 light, 6.2:1 dark |
| `danger` on wool | 5.6:1 |
| `danger` on navy | 7.0:1 |

Salmon on wool is 2.2:1, so salmon is never text or a meaning-carrying line on a light ground.

**The canvas weave.** The page ground carries a 4px woven grid of 1px lines in the `weave` token: tobacco at 6% on wool, wool at 3.5% on navy. The decorative stitches use `stitch-soft` (hero) and `stitch-tag` (shipping tags); no colour is written as a literal. It is the only texture. It never sits on a crate, a tag or a button, and it is never drawn in email.

**Retired:** the poster palette (ultramarine, sun, sky, snow, dawn), the wax quartet and the Glyph surface material. The temperature bar on race pages needs its own colours: **Not specified yet**.

## 3. Typography

Three families, all from Google Fonts with `display=swap`:

| Family token | Face | Weights | Job |
|---|---|---|---|
| `font-stencil` | Big Shoulders Stencil Display | 700, 900 | Page titles, section heads, prices. Uppercase. |
| `font-label` | Big Shoulders Text | 600, 800 | Crate titles, kickers, buttons, nav, list heads, tags, pull quotes |
| `font-body` | Libre Franklin | 400, 600, italic 400 | Everything people read |

Styles, by name in `tokens.json`:

- **Stencil:**
  - `stencil-xl`: page title, fluid 56–168px, line-height .84. One per page. The last word can sit in an ink block with ground-coloured text (`XC SKI LABS [COURSE]`).
  - `stencil-l`: section heads, 36–72px, set on a 4px ink rule.
  - `price`: 84–128px, for numbers on crates only.
- **Label:**
  - `crate-title` 26–32/800 uppercase
  - `kicker` 16/800 tracked .4em, in an ink block
  - `button` 19/800 uppercase
  - `nav` 16/600 uppercase
  - `list-head` 18/800 uppercase
  - `tag` 16/600 sentence case
  - `pull` 24–32/800 uppercase: one per page, under a 4px rule
- **Body:**
  - `lede` 18–21/600, max 38 characters per line
  - `body` 17/1.6, max 58 characters per line
  - `reading` 18/1.6, for the course
  - `fine` 15
  - Italic only for the one-line note under a list ("A short quiz follows twelve of the lessons.").
- **Stencil limits:**
  - At least 36px; the stencil breaks up below that.
  - At most 4 words per line and 3 lines.
  - Never in body text or buttons.
  - Race names with diacritics (å, ä, ö, ø, š): glyph coverage in both Big Shoulders faces is **not yet checked**. Until it is, set them in Libre Franklin 600.
- **Number formats:**
  - Prices are whole dollars: `$29`.
  - Recurring prices are `$199` followed by `every 4 weeks`, never `/mo`, `monthly` or `per month`.
  - Durations are `h:mm`. Distances are `54 km`. Counts are digits.

## 4. Objects

The system is a set of physical objects. Each one has one job.

| Object | Built from | Job |
|---|---|---|
| **Strap** | `strap` band, full width | Header and footer. Holds the lockup and nav. |
| **Band** | A full-width `panel` or `ground` section, with a 6px ink edge where two bands meet | Page sections |
| **Crate** | `panel`, a 14px inset, a 2px dashed stitch, 14px slats top and bottom (navy 22px, gap 4px) | One product or one lesson group |
| **Splash crate** | A crate in `splash`, slats in `splash-deep`, stitch in ink, a `Recommended` or `Now` ribbon in `tag-paper` | The one start-here object |
| **Luggage tag** | `tag-paper`, arrow-cut left end, an eyelet in the panel colour with an `on-tag` ring | One stat line on a crate |
| **Checklist** | `paper` with a 2px ink outline, ink header bar, rows on 1px dashed `rule`, an 18px checkbox | Lessons and what's included |
| **Shipping tag** | `tag-paper`, cut top corners, an eyelet, a dashed inner stitch at 35% | One note: after-you-pay, refunds, access |
| **Pocket** | `panel` with a dashed fold line | Holds one photo slot |
| **Stitch** | 2px dashed ink, inset 12–14px inside a filled object | Edges of filled objects |
| **Empty slot** | 2px dashed ink on an empty or translucent field, with an uppercase label | A photo that doesn't exist yet |

A stitch sits *inside* a filled object. An empty slot is a dashed box *with nothing in it but its label*. They never get confused, because a slot always says what belongs there.

## 5. Shape and line

- **Corners:** square everywhere (`radius-none`). The mark's tile is the only rounded thing (`radius-mark`).
- **Cut shapes:** clip paths are allowed only for the luggage tag's arrow end and the shipping tag's cut corners. Nothing else is cut or angled.
- **Lines:**

| Token | Width | Used for |
|---|---|---|
| `stroke-weave` | 1px | Dashed `rule` rows in lists |
| `stroke-stitch` | 2px | Dashed stitching, list outlines, empty slots, checkboxes |
| `stroke-button` | 3px | Button borders and the focus ring |
| `stroke-rule` | 4px | Under section heads, above the pull quote |
| `stroke-underline` | 5px | The salmon underline inside buttons |
| `stroke-band` | 6px | Ink edges between bands |

- **Rotation:** shipping tags in a row may tilt ±1.2°. They sit straight below 860px. Nothing else rotates.
- **Checkboxes:** a dotted outline is planned, a solid outline is current, and filled with a check is done.
- **Elsewhere:** dashed is a stitch (inside a filled object), a list rule, or an empty slot (with its label).

## 6. Layout

- **Measure:** 1200px, with side padding `clamp(16px, 4vw, 48px)`. Running text is at most 58 characters per line.
- **Bands:** the page is a stack of full-width bands: strap, hero (panel), sections on ground, banded sections on panel, strap. Each band's top padding is 56px on phones and up to 104px on wide screens.
- **Section heads:** `stencil-l` on a 4px ink rule, with 32px below it.
- **Crate grid:**
  - The splash crate comes first in the source, so it is first in focus order and first on screen below 980px.
  - At 980px and wider: three columns at 1 : 1 : 1.25, with the splash crate placed in the wide right column.
  - From 640 to 979px: the splash crate spans the top row, and the other two sit below it.
  - Under 640px: one column, with the splash crate first.
- **Lists:** three columns at 1.3 : 1 : 1, one column under 900px.
- **Shipping tags:** three across, one column under 860px.
- **Header:** a strap with the lockup left and the nav right. Under 520px the wordmark drops to 19px and the nav wraps below. Nav hover and the current page are a 2px underline; the colour never changes. It is not sticky. **Not specified yet:** a phone menu for more than four links.

## 7. Components

Each component has a card with rules and a live preview. On xcskilabs.com the colours, type, lockup, favicon, straps, hero panels and buttons are ported (2026-11-15). The /course/ sales page (`wordpress/generate_course.py`) is built from the crates, tags and checklists, and the /learn/ course reads the same tokens and components from `tokens/course-brand.css`.

| Component | Built here | Not specified yet |
|---|---|---|
| Lockup | On a strap, on wool | Single-colour and reversed lockups |
| Button | Primary, on salmon, quiet link; hover, focus, disabled | Loading state |
| Crate | Product crate, splash crate, tag, button | Owned state; lesson crates inside the course |
| LuggageTag | Stat line | — |
| Checklist | Planned, current, done rows | Long lists |
| ShippingTag | Note tags in a row | — |
| Hero | Kicker, stencil title, lede, photo slot | — |
| Race rating, comparison row, video player, temperature bar, form fields, table | — | **All not specified yet.** Needed before race pages are reskinned. |

**States:**

| State | Treatment |
|---|---|
| Hover (button) | Ground fill, ink text, ink border (150ms) |
| Focus | 3px `focus` ring, 3px offset. On a strap the ring is `on-strap`; on the salmon crate and the current row it is `on-splash`; on tags it is `on-tag`. |
| Disabled | 45% opacity |
| Current | The splash crate, or a splash row in a checklist with the word Now |
| Done | A `done` checkbox with a solid border and a ✓, plus the word Done in the row |
| Planned | Dotted `rule` checkbox |
| Error | `danger`, with a word and an icon |

## 8. Logo

- **The mark** is the crossed skis, in the 2026-11-14 redraw Matti chose (its provenance is internal and never published): two long skis with swept tips, crossed on a rounded tile, with small bindings. It is drawn on a 300-unit tile with a 28-unit corner radius.
- **Colourways.** Only these two are used:

| Colourway | Tile | Skis | Bindings | Where |
|---|---|---|---|---|
| Wool | wool | one navy, one salmon | wool | On straps and on navy grounds |
| Fjord | navy | one wool, one salmon | navy | On wool and oat grounds, social avatars |

  The salmon ski is always the one running from the lower left to the upper right.
- **Files:** `logos/xc-mark-wool.svg` and `logos/xc-mark-fjord.svg`. Favicons and app icons up to 32px use `logos/xc-mark-small.svg` (approved by Matti, 2026-11-14). The previous drawing, `xc-crossed-skis.svg` (cream skis on dark green), retired on 2026-11-15 when the small mark became the live favicon.
- **Sizes and spacing:** at least 24px on screen and 10mm in print. Favicons and app icons up to 32px use the small mark (see the Small mark component). Clear space is one ski's width on every side.
- **Lockup:** the mark (44px on a strap, 36px in the footer) plus `XC SKI LABS` in Big Shoulders Text 800, 22px, tracked .2em, with a 12px gap.
  - The wordmark is the accessible name; the mark is decorative.
  - The wordmark is redrawn as outlined lettering before launch.
- **Don't:**
  - add colourways beyond wool and fjord
  - swap which ski is salmon
  - put the mark on salmon
  - outline, rotate or stretch it
  - put a shadow or bevel on it
  - single-colour and embossed versions are **not specified yet**

## 9. Imagery

- **Photography** is real and permissioned only: Matti's own footage and photos, or licensed photos with written permission. Natural colour, no filters, no duotones, no sepia "expedition" ageing.
- **Empty slots** are 2px dashed ink boxes with an uppercase label naming the photo that belongs there.
- **Illustration** is limited to the objects in §4. There are no drawn skiers, maps, compasses or polar scenes. The mood comes from the objects, not from pictures of the era.
  - **Exception, inside the course only (Matti, 2026-11-15):** the XC Ski Labs character, drawn from Matti's own filmed motion, stays in the /learn/ lessons: lesson heroes, technique strips and annotated figures. It does not appear on the sales page, race pages, emails or any other surface.
- **Open Graph images** (1200×630) follow the course mockup:
  - a wool ground with the weave
  - the stencil title
  - the fjord mark
  - one salmon crate or slat band
  - no photo unless it is real

  The exact layout is **not specified yet**.

## 10. Motion

| Motion | Value |
|---|---|
| Hover | 150ms |
| Other changes | 200ms maximum |
| Easing | `ease-out` |

Nothing loops, swings or bounces. Tags don't sway. Under `prefers-reduced-motion: reduce`, transitions are off.

## 11. Voice and copy

**Voice.** Every word an athlete or customer reads is Matti speaking, in the first person: "I add new modules to the course", "I'll refund that purchase in full".
- Never "the coach", "your coach", "ask the coach", "Coach Matti", "Matti will", "our team" or "Matt".
- Never mention AI, Claude, Codex, GPT, automation, drafts or generators.
- "Coaching" is allowed as a product name. "Coach" as a person is not.

**Before saving or sending.** Search the copy for Matt, Matti, coach, Claude, Codex, GPT and AI, and rewrite every hit in the first person or remove it. Follow `docs/AI_WRITING_POLICY.md`, including the full no-ai-slop pass.

**The look stays in the design.** The expedition mood never leaks into the words. No "gear up", "expedition", "provisions", "basecamp", "summit" or explorer puns in customer copy. The stores look is visual; the copy stays plain.

**State words.** The state words are Recommended, Now and Done. Other bracketed labels in mockups, such as `[Modules]`, are placeholders until Matti writes the words. Square brackets never ship.

**Real examples,** quoted from the live course page:
- "Learning a new technique as an adult is humbling. You go from embarrassing to bad, bad to OK, and OK to good."
- "One payment each. Full refund within 14 days if it isn't for you."

**Contact address.** Athletes and buyers write to gravelgodcoaching@gmail.com, Matti's address. Show it as plain selectable text. Never point anyone to Summit Endurance Academy emails, coaches, sites or social accounts.

**Billing.** Coaching bills every 4 weeks.

## 12. Accessibility

- Text pairs meet the ratios in §2 in both themes.
- Focus is a 3px solid ring with a 3px offset, visible on every surface, including straps and the salmon crate.
- State never depends on colour alone. Done has a check and a word, current has a label, and planned is dotted.
- Buttons are 56px tall; links and nav items are at least 44px.
- Focus is visible on every surface: ground, panel, strap, tags, the salmon crate and the current row each set their own ring colour. Tags keep a transparent 2px border, so forced colours show their edge.
- Before shipping a surface, test:
  - reflow at 320
  - 200% zoom
  - keyboard only
  - `forced-colors: active` (stitches and slats may drop; borders and labels must remain)
  - reduced motion
- Dark mode (Fjord) follows `prefers-color-scheme`; a toggle sets `data-theme`.

## 13. Brand boundaries

- **No real brand is imitated.** The polar-expedition mood is borrowed from history, not from any company. In particular, nothing comes from Amundsen Sports: not its logo, type, product names, photos or layouts.

### Separation check (2026-11-14)

Colours and fonts were sampled from the live home pages of Amundsen Sports, Fjällräven, Bergans, Norrøna, Dale of Norway, Swix, Madshus, Filson, Best Made Co. and Topo Designs. Astra scored the same field independently from memory. The full numbers are in `separation.md`.

**What the check found**
- **Cream is shared ground, not ours.** Our wool is ΔE00 2.0 from Amundsen's cream, and our oat is 1.5 from Filson's. Both differences are too small to see. Bergans and Topo Designs use near-identical creams too. Cream gives no separation either way, so the identity cannot rest on it.
- **Navy is ours against this field.** Amundsen's ink is near-black navy (ΔE00 8.7 from ours). No sampled brand uses a mid fjord navy for bands.
- **Salmon is the most distinctive colour.** It is at least ΔE00 18 from every red and orange sampled (Filson, Madshus, Swix, Best Made). Salmon is the colour that carries the identity.
- **Stencil type is distinctive.** No sampled brand sets display type in a stencil. Amundsen uses a serif wordmark with mono headings. Filson uses an extra-condensed grotesk. Big Shoulders Stencil is a separator, so it stays.
- **Category overlap is real.** Amundsen sells a Cross-Country Skiing range and Norwegian wool. XC sells instruction, not clothing, but a buyer can only tell that from the words.
- **The closest logo is Best Made's red X.** Two crossed bars in red sit between the words BEST and MADE. Our skis are two colours with swept tips, which reads as skis at 24px and up. At favicon size, the tips can blur into an X.

**Rules from the check**
- The first screen of every page says in words what XC sells: cross-country ski technique courses and training plans. The look alone never carries that.
- Both skis are never the same colour, and never red or salmon together. The mark never sits between two words of a wordmark. Favicons and app icons up to 32px use the small mark, `logos/xc-mark-small.svg`, approved by Matti on 2026-11-14. Its skis cross low in a herringbone V with hooked tips, so it reads as skis, not an X, at 16px.
- No knit or Selbu patterns, no woven-label badges, no "since 18xx" or "Norwegian heritage" claims, and no clothing-led lifestyle photos. Photos lead with technique: skiers moving, frames from the lessons.
- Product names stay plain course and plan names. No collection names, and no explorer or place names as product names.
- Crates, tags and stitches belong to commerce: course and plan cards, the lessons list and the refund tag. Editorial pages, emails and race pages don't use them.
- `splash-deep` (#b85c47) is ΔE00 5.5 from Filson's red. It stays what §2 allows: thin slats on the salmon crate, broken by salmon gaps. It is never a fill, a band or text.

### Name search (2026-11-14, preliminary)

This was a quick search of the USPTO database and the open web. It is not a clearance search and not legal advice. A trademark attorney has to judge it.

**Matti's decision (2026-11-14):** the name stays XC Ski Labs, without waiting on an attorney review. Nordie Labs and Glide Labs were rejected. Nordie Labs was too close to "Nordic … Lab". Klister Labs is noted only as a fallback name if a trademark problem ever comes up. Nothing is built for it.

- **NORDIC SKI LAB, US Reg. 6296989, live.** It is owned by XCSN Nordic Skiing Inc. (Canada) and registered 2021-03-16 in class 41. It covers a website with cross-country skiing instruction and training information, and non-downloadable cross-country ski instruction and training videos. It runs at nordicskilab.com, which sells technique videos, training plans and online coaching. Those are the same services as XC Ski Labs, under a name that differs by "XC" against "Nordic" and a plural. **This is the most serious finding in the whole check.** Its site looks nothing like ours: bright blue and orange-red with Source Sans. The risk is the name, not the look.
- **XC, US Serial 99633124, published for opposition on 2026-11-10.** It is owned by Sports Content Creation LLC. Its class 41 services include online non-downloadable videos in the field of sports. It looks like a sports media brand, not ski instruction. US opposition windows open for 30 days from publication and can be extended.
- **SKI LAB INDOOR CENTER, US Serial 99489470, pending.** It is owned by SKI LAB LLC (Texas) in class 41 for sports instruction. Indoor ski simulation, US only.
- **"XC SKI LABS" itself:** no US filing found. No business by that name surfaced on the web.
- **Not searched:** Canada (CIPO), EU (EUIPO), UK, Norway, state registrations, common-law use beyond a web search, and design marks for the crossed skis.

**Kept (Matti, 2026-11-14):** the leather-brown rule, the eyelets, the tag tilt and the stitched borders. Astra suggested a grey rule (#b9b7b2) and dropping the rest as costume risks. Matti kept them as part of the Sledge Stores look. The commerce-only rule above is what keeps them from spreading.
- **Endure Labs** keeps its own Glyph look. XC no longer shares Glyph's surface material. Endure's app shows XC plans in Endure's design, not this one.
- **Gravel God:** no brown-and-gold palette. Tobacco is used only for thin rules and the weave.
- **Roadie Labs:** its palette was not found, so separation is **not yet checked**.

## 14. Don'ts

- No salmon band, hero, strap or ground, and no second salmon object on a page.
- No elevation shadows, glows, bevels or tonal gradients. No rounded corners except the mark's tile and the round eyelets.
- No drawn explorers, ships, sledges, maps or compasses.
- No expedition puns in copy.
- No stencil type under 36px or in body text.
- No stock, AI or "aged" photos.
- No hex values outside `tokens.json`, the logo SVGs and print files.

## 15. Reversals

| Was | Now | Why |
|---|---|---|
| P1 Poster rim (2026-11-13): ultramarine, sun, spruce, Bowlby One SC | Wool, oat, navy, salmon splash; Big Shoulders and Libre Franklin | Matti chose Sledge Stores · Splash on wool, 2026-11-14 |
| Endure Glyph anatomy and surface material: 6/7px radius, elevation, bevel, rim, grain | Square, flat canvas, stitched and slatted objects | The stores look is physical and flat |
| The rim marks the one start-here object | The salmon crate marks it | Same rule (Matti, 2026-11-14), new material |
| Poster art as the illustration system | No illustration beyond the objects | The objects carry the mood |
| Sun-and-tracks mark (proposed), then crossed skis in the old drawing | Astra's crossed skis in wool and fjord | Matti kept the skis and liked Astra's drawing |
| Four type families | Three | Stencil, label and body cover every job |
| Glyph's 2px stroke ladder | A six-step line ladder (1 to 6px) | Stitches, rules and bands need their own weights |

Kept:
- one job per colour
- state shown by shape and words as well as colour
- real or nothing
- an 11px floor
- a 44px touch floor
- every-4-weeks billing
- no self-described honesty
- first-person voice

**Decision log.**
- 2026-11-13: P1 Poster rim chosen, drafted and reviewed.
- 2026-11-14: P1 lift kept.
- 2026-11-14: crossed skis kept.
- 2026-11-14: Astra's drawing liked; salmon studies made.
- 2026-11-14: Sledge Stores · Splash on wool chosen as the base. This book is rewritten from it.
- 2026-11-14: separation check against ten outdoor brands run; rules added to §13.
- 2026-11-14: small-mark candidate drawn; preliminary name search found NORDIC SKI LAB (US Reg. 6296989) in the same services.
- 2026-11-14: small mark approved for favicons and app icons (Matti).
- 2026-11-14: name kept as XC Ski Labs; book locked (Matti).
- 2026-11-14: leather rule, eyelets, tag tilt and stitches kept (Matti).
- 2026-11-15: the character stays inside the course; §9 exception added (Matti).
