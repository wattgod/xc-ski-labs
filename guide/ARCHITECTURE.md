# The Complete XC Ski Racing Training Guide — Architecture

**Status:** Ratified direction (Matti, Jul 10 2026: "produce a phenomenal analogue" of the
gravel guide). Content authored by Fable; generator is a port of gravel's
`generate_guide_cluster.py` in Wax Bench style with survey plates (NO AI imagery).
**Content file:** `guide/xc-guide-content.json` — same schema as gravel's
(`title/subtitle/meta_description/personalization/glossary/chapters[8]`, sections of
typed blocks, gate after ch3, chapter heroes = drawn plates keyed by chapter number).
**URL plan:** `/guide/` pillar + 8 chapter pages, jump nav, email gate at ch4+
(BLOCKED until X3 email-capture worker exists — gate can ship pointing at the worker
the day it lands; until then chapters 4-8 ship `noindex` + soft-gated).

## What carries over from gravel (same physiology, re-derived honestly)
Aerobic base as the engine; zone logic and the 80/20 shape; supercompensation and why
rest weeks exist; periodization phases; fueling math (carbs/hr, bonk mechanics — with
cold-weather caveats); taper logic; mental skills; post-race recovery windows.
Carry the CONCEPTS, never the prose — every sentence rewritten for skiing, and every
gravel-specific claim re-checked before reuse (e.g. fueling rates differ in the cold;
pack-riding tactics don't map).

## What is XC-native (the chapters earn their keep here)
- **Technique is a second engine.** Unlike gravel, economy differences between skiers
  dwarf fitness differences at citizen level. Classic vs skate as different sports;
  technique selection by terrain and speed; "technique dies when the heart rate rises."
- **The upper body is load-bearing.** Double-pole power, ski-erg/rollerski dry-land
  reality, strength that transfers (and the gym work that doesn't).
- **Snow literacy.** Wax/kick basics (the wax bar IS our brand language), glide vs kick
  trade-offs, cold-weather physiology (airway, layering, frostbite windows, the -20°C
  race-cancellation reality), altitude plateaus of European classics.
- **Seasonality is brutal.** 5-7 dry-land months: rollerski periodization, running,
  bounding, the October volume trap; "your season is built in July."
- **Mass-start seeding + track tactics**: wave qualification (Birken/Vasaloppet seeding),
  double-pole trains, feed-station technique with poles on, drafting reality on flats.

## Chapter map (mirrors gravel's proven arc; XC content)
1. **What Is XC Ski Racing?** (open) — loppet culture, classic/skate/both, the four rider
   types, tier system intro, race anatomy (waves, tracks, feeds). Plate: terrain trace.
2. **Race Selection** (open) — using the 229-race database: tiers, criteria that matter
   per rider type, monuments vs local loppets, travel math, entry/seeding requirements.
   Plate: REAL tier distribution (7/85/106/31).
3. **Training Fundamentals** (open) — engine physiology carried from gravel + the
   technique-economy engine; zones by feel/HR (power optional: erg only); 80/20 on snow
   and dry land; the year wheel (May-Nov dry, Dec-Apr snow). Plate: zone spectrum.
4. **Technique & Workout Execution** (gated) — classic gears (diagonal, double-pole,
   kick-double-pole) and skate gears (V1/V2/V2-alt) as shift points; drills; executing
   intervals when technique degrades; rollerski safety. Plate: gear shift-points diagram.
5. **Nutrition, Fueling & Cold** (gated) — carbs/hr adjusted for cold; warm feeds; the
   frozen-bottle problem; pre-race in a heated cabin economy; layering/airway basics.
   Plate: fueling timeline ticks.
6. **Mental Training & Race Tactics** (gated) — pacing a mass start you can't win in
   the first km but can lose; wave dynamics, track choice, when to double-pole through
   feeds; the long-grind psychology of 50-90 km. Plate: psych phase curve.
7. **Race Week Protocol** (gated) — taper, travel to snow/altitude, kit and wax
   decisions by forecast (wax bar pedagogy), morning-of protocol, drop-bag/clothing at
   start. Plate: countdown ticks.
8. **Post-Race & The Off-Season** (gated) — recovery windows, the April gap, building
   the dry-land year, choosing next season's monument; ladder hand-off (plans/custom/
   course/coaching). Plate: supercompensation curve.

## Personalization (rider types — XC analogues, hours honest for skiing)
- **Lantern Rouge** (0-4 hrs/wk) — finish the loppet upright, enjoy it.
- **Finisher** (4-8) — finish strong, negative-split the back half.
- **Wave Chaser** (8-12) — seeding waves, PBs on monuments.
- **Elite Wave** (12+) — front-wave qualification, age-group results.
(IDs: lantern_rouge / finisher / wave_chaser / elite_wave. No FTP defaults — XC
personalization keys on hours + technique confidence, not watts.)

## Citations doctrine (Matti, Jul 10: "abundant citations")
Every chapter carries a `sources` array: {id, title, author?, publisher, year?, url,
supports}. Inline markers `[^id]` in prose where a claim leans on a source; rendered as
superscript links to a per-chapter SOURCES section. Two source pools:
(1) **fasterskier.com** — 20+ years of coach interviews, training series, wax science;
    the never-synthesized archive this guide mines on purpose (ongoing: every new chapter
    starts with a FasterSkier sweep).
(2) **Primary literature** — the physiology anchors are conveniently native to this
    sport (Seiler's seminal intensity-distribution work was done ON elite XC skiers;
    Sandbakk & Holmberg's world-class-skier physiology reviews; Holmberg's double-pole
    biomechanics). Verified-before-shipped: a citation enters the JSON only after the
    page/abstract was fetched and read. No text-fragment URLs; stable DOIs preferred;
    paywalled is fine, fabricated is never. Port gravel's validate_citations.py rules
    to a guide-citations checker in the generator tests.

## Voice & gates
Claude register per estate rule ("rated," never "honestly rated"; no hype; Normie Test —
no raw VO2max/lactate jargon without plain English). slop_rules port applies. Every
physiological claim either textbook-consensus or hedged honestly; zero invented studies,
zero fake testimonials, race references only to races in our database via race_reference
blocks (slugs must exist in race-data/).

## Block budget per chapter (gravel parity)
~6 sections, ~11 prose blocks (~5K chars), 2-4 callouts, 1-2 data_tables, 1 process_list
or timeline, 1 knowledge_check, 1-2 accordions/tabs, race_reference blocks where a real
race illustrates the point, personalized_content forks at decision moments.

## Build order
1. This architecture (done).
2. `xc-guide-content.json`: pillar + ch1-3 (open chapters first — they're the SEO/traffic
   surface). ← Fable writes.
3. Codex ports generate_guide_cluster.py -> nordic (Wax Bench chrome, plate heroes via
   the existing race-page plate CSS language, knowledge_check styled like the race-page
   quiz), consuming whatever chapters exist (ships with 3, grows to 8).
4. Fable writes ch4-8; gate wiring lands with X3.
