# XC Ski Labs free guide: architecture

**Status:** Rebuilt 2026-11-15 on Matti's direction: the old 8-chapter racing guide was
"bizarre and lacks my character/content". The guide now gives away the general material of
the XC ski course, in Matti's first person, and ends on one upsell: the course.

**Content:** `guide/xc-guide-content.json`. **Generator:** `scripts/generate_guide.py`.
**Tests:** `tests/test_guide.py`. **Deploy:** `scripts/deploy.py --sync-guide` (in `--deploy-all`).

## What the guide gives away, and what stays in the course
Give away the "why and what": what XC skiing is, classic vs skate, finding trails, gear and
clothing, the first hour on snow, safety, the three fundamentals (stance, weight transfer,
hips), the practice loop, what every classic and skate technique is and when to shift, how
snow and wax work, and trail etiquette. Sources: the course's basics lessons
(`~/glide-labs-platform/output/learn/`: getting-started, finding-trails, athletic-foundation,
how-snow-works, technique-selection, trail-etiquette) and the technique lessons' overviews.

Keep in the course: body position, timing, power, error and drill detail for each technique,
the lesson-by-lesson progressions, and the filmed demos.

## Chapters (all open, indexable, no email gate)
1. What XC Skiing Is  2. Your First Day  3. The Foundation  4. The Gears
5. How Snow Works  6. Trail Etiquette

Each chapter's header art is a technique loop of Gravel God (`hero_loop`, from
`scripts/xsl_loops.py`); chapter 4 carries the classic loops and the V2 loop. Captions are
names only.

## The upsell
`course_offer` renders once at the end of the last chapter and once on the pillar, linking
`/course/`, and only when `course_offer.live` is true. While the course can't be bought
(as of 2026-11-15 `/course/` and `/learn/` are 404 and deploy.py doesn't publish `/course/`),
nothing renders in its place: no plan, coaching or product-ladder stand-in. Flip `live` in the
same change that puts `/course/` live.

## Retired URLs
`retired_chapters` maps each old chapter id to its replacement (or "" for the guide home).
The generator writes a noindex redirect page at each old URL, so links and search results
from the racing guide keep working, and removes any other stale chapter directory.

## Voice
Athlete-facing: Matti speaks as "I"; never "Matti", "the coach", AI, or em dashes (tests
enforce). Follow `athlete-custom-training-plan-pipeline/docs/AI_WRITING_POLICY.md`, run
`writing-graph/scripts/check_ai_writing.py --strict` on the copy. Personal lines must come
from Matti's authored writing (e.g. the roller-skiing line is from his Red Granite Grinder
newsletter; the Minnesota friend from "You Don't Need To Bike To Bike Fast").
