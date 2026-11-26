# Couzens written-work mining vs the XC ski engine (2026-11-13)

Scope: Alan Couzens's **free** written work (alancouzens.com blog, archived
Endurance Corner articles, his 2007-2012 Blogger posts, and the free part of
his Substack posts). It adds to `docs/evidence/2026-08-23-couzens-corpus-mining.md`
(rules A1-J4), which came only from YouTube transcripts. Compared against
`docs/ALGORITHM_EVIDENCE.md` §20-§20.3 (AE-SKI-1.x, 2.1-2.27, 3.1-3.11),
`docs/plans/XC_SKI_LABS_PLAN.md` and `athletes/scripts/ski_engine.py`.

Method and limits:
- Pages were read with WebFetch, which returns a model-made digest of the page,
  not the raw HTML. Quotes below are the short verbatim phrases that digest
  returned. Spot-check a quote against the page before it is cited in a ruling.
- Paid content was not read and nothing behind a paywall or sign-in was
  attempted. Where a free page keeps its numbers in an image, those numbers
  are listed as not read.
- Most of these numbers are TSS/CTL (cycling/triathlon load units) or Ironman
  monthly hours. The ski engine works in hours and RPE. Where a comparison
  needs a unit conversion this doc says so and does not do it.
- Arithmetic marked "(my arithmetic)" is mine from his numbers, not his.

---

## 1. Sources

### Read (free, fully visible unless noted)

| # | Page | Date on page |
|---|------|--------------|
| S1 | https://www.alancouzens.com/blog/season_planning_4.html | Nov 17 2016 (reprint of 2010); phase tables and annual chart are images, not read |
| S2 | https://www.alancouzens.com/blog/periodization.html | Dec 15 2014 |
| S3 | https://www.alancouzens.com/blog/optimal_periodization.html | Aug 7 2017 |
| S4 | https://www.alancouzens.com/blog/off_season.html | Nov 17 2017 |
| S5 | https://www.alancouzens.com/blog/volume_vs_intensity2.html | Jun 1 2016 |
| S6 | https://www.alancouzens.com/blog/vol_int_responder.html | Aug 21 2018 |
| S7 | https://www.alancouzens.com/blog/volume-vs-intensity.html | Aug 19 2015 |
| S8 | https://www.alancouzens.com/blog/specificity.html | Feb 20 2019 |
| S9 | https://www.alancouzens.com/blog/responder2.html | Apr 17 2015 |
| S10 | https://www.alancouzens.com/blog/load-limits.html | Nov 18 2015 |
| S11 | https://www.alancouzens.com/blog/CTLramp.html | May 22 2015 |
| S12 | https://www.alancouzens.com/blog/maintain.html | Apr 25 2017 (no numbers) |
| S13 | https://www.alancouzens.com/blog/strength_week.html | Dec 14 2015 |
| S14 | https://www.alancouzens.com/blog/healthy_aging.html | Mar 17 2014; hours-per-day chart is an image, not read |
| S15 | https://www.alancouzens.com/blog/lean_muscle_aging.html | Jan 23 2018 |
| S16 | https://www.alancouzens.com/blog/kona_year.html | Oct 19 2017 |
| S17 | https://www.alancouzens.com/blog/big_push.html | Sep 19 2018 |
| S18 | https://www.alancouzens.com/endurance-corner/season-planning-part-iii-determining-load-structure/ | archive date Oct 3 2015 (likely written ~2010-11) |
| S19 | https://www.alancouzens.com/endurance-corner/season-planning-part-iv-determining-training-volume-and-intensity/ | archive Oct 3 2015; zone tables are images, not read |
| S20 | https://www.alancouzens.com/endurance-corner/periodization-simplified/ | archive Oct 4 2015 |
| S21 | https://www.alancouzens.com/endurance-corner/basic-limiters-strength/ | archive Oct 24 2015 |
| S22 | https://www.alancouzens.com/endurance-corner/improving-your-recover-ability/ | archive Oct 3 2015 |
| S23 | https://alancouzens.substack.com/p/physiological-periodization | Sep 24 2025, **free part only** (paid) |
| S24 | https://alancouzens.substack.com/p/building-your-season-like-a-rocket | Apr 5 2026, **free part only** (paid); no numbers in free text |
| S25 | https://alancouzens.substack.com/p/your-50-year-training-plan | Aug 4 2026, **free part only** (paid) |
| S26 | https://alancouzens.substack.com/p/sensibly-aggressive-long-term-planning | Jan 7 2026, **free part only**; the "what is realistic?" answer is paid |
| S27 | https://alancouzens.substack.com/p/why-too-much-intensity-breaks-athletes | Jun 2 2026, **free part only**; no numbers in free text |
| S28 | https://alancouzens.substack.com/p/why-your-training-isnt-making-you | Mar 19 2026, **free part only** |
| S29 | https://alancouzens.substack.com/p/strength-training-for-endurance-athletes | Dec 17 2025, **free part only**; no numbers in free text |
| S30 | https://www.alancouzens.com/ (home page, link list skimmed) | - |
| S31 | https://alancouzens.blogspot.com/2007/08/real-world-periodization-loading.html | Aug 1 2007; loading charts are images, not read |
| S32 | https://alancouzens.blogspot.com/2007/09/real-world-periodization-ii-phases.html | Sep 3 2007 |
| S33 | https://alancouzens.blogspot.com/2012/09/tapering-part-ii-taper-weeks-by-sport.html | Sep 10 2012; influence-curve figures not read |
| S34 | https://www.alancouzens.com/blog/Psycho_Taper.html | Apr 27 2015 (no numbers) |
| S35 | https://www.alancouzens.com/endurance-corner/season-planning-part-ii-setting-phases-objectives-and-checkpoints/ | archive Oct 3 2015 |
| S36 | https://alancouzens.blogspot.com/2008/12/structural-considerations-in-planning.html | Dec 10 2008 |

Already reviewed by the caller, not re-fetched: github.com/alan-couzens/Endurance-Code
(public book notebooks): HRV cost of load by TSS-CTL category (recovery < -30,
easy -30..30, loading 30..60, BIG > 60), readiness model, Banister fit,
nutrition (CHO g/day formula, protein), pacing fatigue curve, heat. Nothing
from it is used below beyond this mention.

### Not read

| Page | Why |
|------|-----|
| https://www.triathlete.com/training/what-does-it-mean-to-train-like-a-norwegian/ | The server redirected to an Outside account sign-in (accounts.outsideonline.com). Not followed. Content unknown. |
| Paid remainder of S23-S29 | Paywalled ("Keep reading with a 7-day free trial"). |
| https://alancouzens.substack.com/p/chapter-11-the-ultimate-guide-to and https://alancouzens.substack.com/p/weekly-planning-to-maximize-readiness | The Endurance Code book chapters are paid; not opened. |
| Image-only tables in S1, S14, S19, S31, S33, S35 | Numbers sit in images WebFetch cannot read. |
| https://www.fasttalklabs.com/pathways/polarized-training/ | Membership site; not opened. |

The ln(volume) regression the earlier doc (A2) says "lives on his blog" was
**not found** in any page read here. S7 gives no equation; S8 gives linear
monthly-hours equations (CW8). Do not cite an ln(volume) coefficient.

---

## 2. Rules

Scope tag: **G** = sport-general as written; **T** = written for triathlon,
Ironman or cycling (TSS/CTL units, swim/bike/run), transfer to skiing not shown.

### Annual volume and multi-year progression

**CW1 - Volume is undervalued; returns diminish.** Going from 40 to 60 h/month
gave about +0.5 W/kg; the next 20 h/month (60-80) only about +0.2 W/kg.
Intensity "takes a lot" to make up small volume cuts. Quote: "Most athletes
significantly underestimate the benefit of volume on performance" (S5). **T**
(W/kg on the bike). Confirms spoken A3.

**CW2 - Hold fitness with age by adding about 12 h a year, every year.**
About 0.4 ml/kg/min VO2max lost per year; offset by adding about 1 h/month
(about 12 h/yr, about 15 min/week) to annual volume each year. Example: 30
h/month at 40 implies about 60 h/month at 70. Quote: "add approximately one
hour per month to our annual training volume" (S25, free part). **G**.
Confirms and quantifies spoken G6.

**CW3 - Training needed to offset aging rises with age.** No training: VO2max
falls about 5 ml/kg/min per decade. About 0.5 ml/kg/min gained per 100 h of
training. About 100 h/yr offsets the decline at 30-40; about 475 h/yr at 60.
Quote: "0.5ml/kg/min per 100 hours of training" (S14). **G**.

**CW4 - Multi-year, "sensibly aggressive" loading; reject fast ramps.** He
calls 10%/week and 5-10 CTL/week long-term ramps "ridiculous"; going from the
couch to elite load in under six months is fantasy; it takes multiple years
but "not a decade". Quote: "it is going to take multiple years of sensibly
aggressive loading" (S26). **G**. The realistic number is behind the paywall:
not read.

**CW5 - Kona qualifiers' basic year (descriptive, ~40 athletes).** About 2-3
h/day Dec-Oct; off-season Oct/Nov at almost 50% of the peak month; December
base about 60 h; April a mid-season recovery month; May-July about 80-90+ h;
August peak 90-100 h; September taper about 70 h; October race. Quote:
"August tends to be the biggest month (90-100hrs)" (S16). **T** (Ironman).
Consistent with spoken A1 (800 h/yr tier).

### Ramp rate and load pattern

**CW6 - About 10 CTL per month by default.** "1,2,3" rule: ramp about 10
CTL/month, TSB floor about -20 at the end of 3 loading weeks, daily load about
CTL + 30 in loading weeks, about CTL - 30 in the recovery week (back to TSB
about 0). Proven or high-constitution athletes: "2,4,6" (about 20 CTL/month,
TSB floor -40, CTL + 60). He also gives a conservative long-term 3-5 CTL/week.
Quote: "Target CTL ramp rate = ~10 per month" (S11). S10 repeats "a ramp rate of
~10 per 4 week block" and a TSB floor of -30 (-20 safer in base). **T** (TSS
units). Confirms spoken B1.

**CW7 - Recovery week at least one "TSB length" below CTL.** Worked block:
750/800/900/350 TSS weeks; the recovery week sits at least a TSB's length
below CTL (example 75 - 25 = 50 TSS/d). Quote: "at least a 'TSB's length' below
the CTL" (S18). Recovery week = 350 / mean(750, 800, 900) = 0.43 of the
loading-week mean in TSS (my arithmetic); with CW6's CTL ± 30 at CTL 100 it is
70/130 = 0.54 (my arithmetic). **T** (TSS). Loading weeks step up inside the
block in this case study.

**CW8 - Flat 2:1 or 3:1 early; no progressive loading early for most.** In the
early preparatory period he repeats a fixed "basic week" in a flat 2:1 or 3:1
pattern; progressive loading then is "a mistake" for all but the most elite,
consistent athletes. A harder "challenge session" goes into the last loading
week only once the basic week is dialled in. Quote: "a 2:1 or 3:1 flat loading
protocol with my athletes in the early season" (S31). **G**.

**CW9 - Hold one stimulus 4-8 weeks, then overload by no more than 10%.**
Repeat the basic week 4-8 times before reassessing; overload steps "generally
no more than 10%". Base blocks are 4-8 months, not weeks. Quote: "4-8 weeks of
one consistent training stimulus" (S32). **G**. This 10% is a per-step overload,
not a year-over-year hours cap.

**CW10 - Some athletes need 2 recovery weeks.** Recovery length varies: some
are ready after one week, "some that take two weeks to freshen"; return to
neutral TSB before the next block. Three-weeks-in-four vs three-in-five costs
about seven training weeks a year. Quote: "some that take two weeks to freshen"
(S22). **G**.

**CW11 - Response falls through a season; consider two builds a year.** Average
response coefficient about 0.35 at season start, falling each month; a gain
costing 10 CTL in month 1 costs 20 CTL by month 12. A full unload loses about
50% of CTL. Two 5-month builds with a mid-year unload can match an 11-month
build with less load; he says this is a starting point, not a rule. Quote:
"2x5month builds, with a mid year unload vs a full 11 month build" (S9). **T**
(CTL). Extends spoken H6.

**CW12 - Season length by level.** Banister-model optimum macrocycle about 5
months for an intermediate; novices 3-4 months; elites 5-7 months. The first
month back is "typically the most tiring". Quote: "the return month to training
is typically the most tiring" (S36). **G** (model-based).

**CW13 - Never raise volume and intensity together.** Quote: "Never increase
volume and intensity at the same time" (S28, free part). **G**. Confirms spoken B2.

**CW14 - Volume pyramid plus intensity ramp models best.** On 100+ Ironman
builds, with equal 50 h/month load, a volume pyramid (low early, mid-season
peak, decline into taper) plus intensity built from very low in winter
predicted 9:02 vs 9:59 for flat load. Quote: "built their intensity through
the year from very low levels in the winter" (S3). **T** (Ironman model).

### Peak timing, race season and taper

**CW15 - Load matters most 28-60 days out.** Load's impact on performance
peaks about 28-35 days before the event; week 5 out "should be a big week"
(S33). The ~30-60 day window before the event is the most impactful; Mark
Allen-style block = four hard weeks then a 4-week taper; competitive
age-grouper averaging ~18 h/wk goes to ~27 h/wk for that block (S17). Quote:
"the 5th week out should be a big week" (S33). **T**. In tension with spoken H2
(peak CTL 2-3 months before the race); S16 (peak month August, race October)
sits between them.

**CW16 - When each intensity pays off.** Sharpening (VO2max) work has most
effect about 16-70 days (2-10 weeks) out; threshold work about 4-16 weeks out
(S2). Training more than 5 months before the event has "very little
performance impact" (S4). Free S24 lists "Too much intensity too early" as a
classic error. Quote: "Threshold training tends to have the greatest positive
impact 4-16 weeks before" (S2). **G** (stated generally). Extends spoken H7.

**CW17 - Taper size.** About 50% average volume reduction over the 30 days
before competition; common tapers give 5-7% (S36). Studies he cites: volume
drops of 60-90% gave the biggest gains; 10-40% of in-season volume is the best
short-term trade-off (S4). Quote: "50% average volume reduction in the 30 days
prior to competition" (S36). **G**.

**CW18 - Taper length modifiers.** "Fitter athletes need shorter tapers."
"Shorter events need longer tapers." "Bigger athletes need longer tapers."
Race week: run and bike load generally hurts. No week counts given (S33). **T**
for the by-sport detail, **G** for the three modifiers.

**CW19 - Keep easy aerobic work in the taper.** Quote: "Not ditching the low
intensity exercise during taper" (S34). No numbers. **G**.

**CW20 - Key races at positive TSB 0-10; key-workout weeks near zero.** (S10)
**T** (TSB).

### Off-season

**CW21 - About 60 days off-season; better-trained athletes need longer.**
First half (2-4 weeks) pure recovery at about 7 h/week, under 60% VO2max; then
ramp back. A 3-4 week recovery cycle is the basis of the mesocycle. Quote: "for
a full ~60 day 'off-season'" (S4). S36: a 4-6 week end-of-season period. **G**.
Consistent with spoken H1 (4-6 week shutdown) and adds the ramp-back half.

**CW22 - A recovery month mid-season.** April "gather the mojo" recovery month
in the Kona year (S16). **T**.

### Intensity distribution

**CW23 - Base phases are mostly easy, IF about 0.69-0.70.** Prep weeks IF
0.69, General IF 0.70 (49 TSS/h); a higher % easy in General and Prep. Hours
= weekly TSS / TSS-per-hour. Quote: "all Prep weeks will have a standard IF of
0.69" (S1, S19). **T** (IF units). Zone percentages are in images: not read.

**CW24 - Volume vs intensity responders.** In his 40-athlete sample, 20% were
"intensity responders" (volume coefficient < 0.1, intensity > 0.2) and 25%
"volume responders" (volume > 0.1, intensity < 0.25), fit per athlete on
28-day blocks. Quote: "8/40 athletes (20%) are 'intensity responders'" (S6).
**G** method, **T** data.

**CW25 - Intensity has a short shelf life.** Low-intensity volume is tolerable
in large amounts for long periods; "only a few weeks of highly intensive
training" can leave athletes stale (S27, free part). **G**. Consistent with
spoken H1 (6-8-10 week intensity shelf life).

### Specificity and cross-training

**CW26 - Cross-training transfers about two-thirds.** "3hrs of cycling is
worth 2hrs of running" to run fitness. Monthly-hours regressions (triathletes):
Bike VO2max = 0.32 x bike h/mo + 0.23 x run h/mo + 38; Run VO2max = 0.21 x
bike h/mo + 0.36 x run h/mo + 41 (S8). Rowers took >50% of winter training
from cross-training such as skiing and cycling (S2). **T** (bike-run).

**CW27 - Aerobic endurance should reach race duration (Ironman base).** Base
2 extends aerobic-threshold endurance to "equal or exceed your predicted race
duration" (S32). **T** (Ironman, 9-17 h).

### Strength and masters

**CW28 - Most strength work "aerobic", below 60% 1RM; one max session.** Keep
"a large portion" of strength below 60% RM; he avoids the 70-80% RM
hypertrophy range (3 x 8-12 off moderate rest). Weekly template: two
aerobic-strength days, one easy strength/core day, one max strength/power
day, mobility between; hard endurance main sets go on the easy-strength days,
and on max/aerobic strength days the lift is the day's main set. 20-minute
focused sessions over 90-minute ones. Up to 2-3 max strength/power sessions
in a run-economy block. Quote: "keep a large portion of our strength work
below 60%RM" (S13). **G**. No sets/reps given.

**CW29 - Strength benchmark.** About 1.2 x bodyweight squat for 12 reps "as a
bare minimum", reached in the early season; check body composition at season
start; accept a little early-season weight gain (S21). **G**.

**CW30 - Endurance athletes lose muscle; strength train every year, more after
30.** About 5% lean mass per decade (meta-analysis he cites); 3-6% per decade
in the general population after the 30s, near 10% by the 70s. "One month of
strength emphasis per year is not enough." Quote: "Chronic endurance exercise
is not sufficient to maintain skeletal muscle mass" (S15, citing Hawkins
2003). **G**. Free S29 adds a yearly anabolic phase and not cutting calories
while raising gym intensity (no numbers). Extends spoken G5.

### Monitoring and testing

**CW31 - Session energy rating.** Rate each session 1-10; a 7-day rolling
average of 4-6 is the green zone for serious athletes; drifting toward 2
means load is compromised and injury/illness risk is up (S10). **G**.

**CW32 - Benchmarks per block; repeat a failed one, then the phase.** One
benchmark per block; make the first ones the easiest to hit; failed: repeat
it within the block; failed twice: consider repeating the phase. Blocks need
not be equal length (S35, S1). **G**.

**CW33 - Recovery takes three speeds.** About 70% of recovery in minutes to
hours, about 20% over days, the last 10% over weeks (S23 free part; S4 gives
the same split). **G**.

---

## 3. Comparison with the XC ski rules

Verdicts: **Agrees**, **Adds** (Couzens covers something no AE-SKI rule
rules), **CONTRADICTS** (Couzens's written rule and ours point different
ways). A contradiction is listed, not resolved. "Engine" = `ski_engine.py`
behaviour that no AE-SKI rule fixes.

| CW | Touches | Verdict | Note |
|----|---------|---------|------|
| CW2, CW3, CW4 | AE-SKI-2.22 (+10% over last season), AE-SKI-3.9 layoff low-year | **Agrees** | Endurance Code ch. 11 free preview (https://alancouzens.substack.com/p/chapter-11-the-ultimate-guide-to, read 2026-11-13): "adding ~10% per year to the training load over many years" is the long-term goal, and the annual plan must not sacrifice it. This directly supports AE-SKI-2.22. Earlier note, from free blog pages only: no free page gives a year-over-year hours cap. His free numbers are a floor (about +12 h/yr just to hold fitness with age), not a ceiling; the realistic multi-year ramp is paid. +12 h is under +10% for anyone above 120 h/yr (my arithmetic), so the cap only binds below that. Spoken examples (A5 700 -> 1,200 h over years; H1 600 -> 700 -> 800 h) grew faster than 10%/yr. |
| CW9 | AE-SKI-2.22 | Adds | His "no more than 10%" is an overload step after 4-8 weeks of one basic week, not an annual cap. Do not cite it as support for AE-SKI-2.22. |
| CW6, CW12 | Engine week budgets; AE-SKI-2.7 (structured training from spring week 4) | **CONTRADICTS (engine, not a ruling)** | Engine: spring weeks 2-3 at 0.5 x load budget, week 4 straight to 1.0 x (a doubling in one week). Every loading week is the same flat budget (`_load_budget`). Couzens: about 10 CTL/month, and the first month back is the most tiring. No AE-SKI rule sets the size of the step back in. |
| CW8 | AE-SKI-2.6 (3:1 for every level), engine flat loading weeks | Agrees | He runs flat 2:1 or 3:1 early season with a repeated basic week. Matches the engine's flat loading weeks. The approved Birkie programs' recovery weeks (4, 7, 11) mix 3:1 and 2:1, which he also allows. |
| CW7, CW6 | Engine RECOVERY_RATIO 0.62 (hours) | Adds (units differ) | His recovery weeks are deeper in TSS (0.43 in his worked block; 0.54 at CTL 100 by CTL ± 30). Ours is hours, measured from the approved programs, and recreational recovery weeks drop all hard days, so TSS falls further than hours. Cannot be compared without an IF per week. Not a contradiction on this evidence. |
| CW10 | AE-SKI-2.6 | Adds | Some athletes need 2 recovery weeks. Not ruled; the engine always gives 1. |
| CW11, CW22 | AE-SKI-2.6, AE-SKI-2.7 | Adds | Mid-season unload / two builds a year. Ours: one season, spring break only, optional top-amateur capacity week not scheduled. |
| CW14, CW13 | AE-SKI-2.23 + AE-SKI-2.5 | **CONTRADICTS (rule text)** | AE-SKI-2.23 puts the biggest volume mid-Oct to early Nov; AE-SKI-2.5 starts full VO2 blocks in August and peaks them in autumn. Read together, volume and intensity both rise Aug-Nov. CW13 (and spoken B2) says never raise both at once. The engine itself keeps loading weeks flat, so the engine does not raise volume then; the rule text does. |
| CW15, CW5 | AE-SKI-2.23 (race-season months at 60-70%), engine RACE_SEASON_SHARE 0.65 (unruled point inside the range) | **CONTRADICTS** | Couzens (Ironman): load matters most 28-60 days out, week 5 out is a big week, race months near peak (Kona year: May-Jul 80-90+ h vs Aug peak 90-100 h; taper month about 70 h). Ours: every January-on loading week at 65% of autumn, so for a late-February A race weeks 5-8 out are at 65%. His evidence is single-peak Ironman; ski race seasons hold several races. |
| CW16 | AE-SKI-2.5 (full VO2 from August, peak in autumn), AE-SKI-2.23 (intensity kept in race season) | **CONTRADICTS (partly)** | He puts sharpening at 2-10 weeks out and threshold at 4-16 weeks out, and calls early intensity a classic error. For a late-February race, August is about 28 weeks out (my arithmetic). AE-SKI-2.23 keeps intensity through race season, so the 2-10 week window is still covered; the conflict is the autumn VO2 peak. |
| CW17 | AE-SKI-1.5 / AE-SKI-2.10 (approved 2-week cut), engine TAPER 0.65 / RACE WEEK 0.375 | Agrees (roughly) | Last 30 days vs the last loading week: (1 + 1 + 0.65 + 0.375) / 4 = 0.76, a 24% cut; vs the autumn peak (x 0.65 race season) about 0.49, a 51% cut (my arithmetic, assumes weeks -4 and -3 are loading weeks). His 50% matches the second reading. |
| CW18 | AE-SKI-2.10 (same taper for every level and race length) | **CONTRADICTS** | He says taper length depends on fitness (fitter = shorter), event length (shorter event = longer) and body size (bigger = longer). He gives no week counts, so no sized alternative exists. |
| CW19 | AE-SKI-1.5, AE-SKI-2.10 | Agrees | Approved taper keeps easy sessions and short pickups. |
| CW21 | AE-SKI-2.7 (3-week spring break: 1 mostly off, 2 at half summer hours) | **CONTRADICTS** | He gives about 60 days (2-4 weeks pure recovery at about 7 h/wk under 60% VO2max, then ramp back), longer for better-trained athletes; S36 and spoken H1 give 4-6 weeks. Ours is 3 weeks, then a full loading week. |
| CW23, CW25 | AE-SKI-2.4, AE-SKI-2.5 | Agrees | Mostly easy in base, limited hard days, intensity used in short blocks. |
| CW24 | AE-SKI-2.4 (level sets hard days) | Adds | Individual volume/intensity response; needs per-athlete data the questionnaire does not collect. |
| CW26 | AE-SKI-2.14 (bike counts 75% toward ski hours) | Adds | His bike-to-run transfer is about 67%. Different sports; not evidence for or against 0.75. |
| CW27 | AE-SKI-2.11 (marathon long session builds toward race duration, max 3.5 h) | Adds (Ironman-only) | He wants aerobic endurance to reach or pass race duration for Ironman. Our 3.5 h cap sits below many recreational 50 km classic finish times. His rule is Ironman-specific; flagged, not counted as a contradiction. |
| (none) | Engine LONG_SHARE_MAX 0.5 | Gap | No free written rule on long-session share of the week. |
| CW28 | AE-SKI-1.2 (A/B lifts, prep 2x8 RPE 6-7, build 3x5 RPE 7-8), AE-SKI-2.8 | Adds / tension | He wants most strength below 60% RM plus one max session. Our build dose (3 x 5 at RPE 7-8) is max-strength work; his aerobic-strength (<60% RM) sessions have no equivalent here. He gives no sets/reps, so there is nothing sized to add. |
| CW28 | Engine `_strength` placement | **CONTRADICTS (engine, not a ruling)** | The engine puts strength on hard days first. Couzens puts hard endurance main sets on the easy-strength days and makes max/aerobic strength the main set of its own day; spoken G5 keeps masters strength away from VO2 days. The approved Birkie programs mostly keep strength off hard days too (classic 5 of 20 strength days on a hard day, skate 0 of 15, counted from `approved_programs.json`). Placement is not in `ENGINE_DECISIONS`. |
| CW29 | AE-SKI-2.8 | Adds | Squat benchmark (1.2 x BW x 12). Not ruled. |
| CW30, CW2 | AE-SKI-2.9 (weekly race-season strength), AE-SKI-3.3 (masters from 40), AE-SKI-2.15 | Agrees / Adds | Strength all year agrees ("one month a year is not enough"). He says muscle loss starts after 30; our masters line is 40. Masters need more training each year, not less; nothing in our rules cuts masters volume. |
| CW31, CW33 | AE-SKI-1.1 (advance only after controlled completion) | Adds | Session energy rating with a 7-day average; not collected. |
| CW32 | AE-SKI-2.19 (test every 8 weeks, results to coach) | Adds | Repeat a failed benchmark, then the phase. Ours sends results to Matti without a rule for a failed test. |

Spoken-rule cross-check:
- Confirmed by written work: A3 (CW1), B1 (CW6), B2 (CW13), G6 (CW2, CW3),
  H1 (CW21, in length), H6 (CW11), H7 (CW16), G5 (CW30, in direction).
- In tension: H2 (peak CTL 2-3 months out) vs CW15 (biggest week 5 out).
- A2 still stands: no ln(volume) equation found in the free pages read.

---

## 4. Questions for Matti

Each is a real contradiction or gap. The recommended answer is a
suggestion; nothing changes until you rule.

1. **How much do race-season weeks drop?** Couzens's Ironman data keeps the
   months before the A race close to peak volume and puts the biggest single
   week about 5 weeks out. Our rule drops every January-on loading week to
   60-70% of the autumn peak (the engine uses 65%, a number no ruling picked).
   For a late-February Birkie that means weeks 5-8 out are at 65%.
   *Recommended:* keep AE-SKI-2.23 for skiers, because Aukland and CXC are
   ski sources and the ski season has several races; but pick the exact
   number yourself (65% or another inside 60-70%) so it stops being an engine
   guess.

2. **Do volume and intensity rise together in autumn?** AE-SKI-2.23 puts the
   biggest volume mid-October to early November, and AE-SKI-2.5 peaks VO2
   work in autumn. Couzens (and his spoken B2) says never raise both at once.
   *Recommended:* say which leads in autumn: keep volume flat while VO2 builds
   (what the engine does now), or build volume first and add VO2 after.

3. **When should VO2 work peak for a February race?** Couzens says VO2 work
   pays off 2-10 weeks out and threshold 4-16 weeks out, and calls early
   intensity a classic mistake. Ours starts full VO2 blocks in August and
   peaks them in autumn, then keeps intensity through race season.
   *Recommended:* keep AE-SKI-2.5 (it settled conflict C5 between ski
   sources); Couzens is not a ski source, and race-season intensity already
   covers his window.

4. **How long is the spring break?** Couzens gives about 60 days (2-4 weeks
   pure recovery, then a ramp back), or 4-6 weeks, longer for better-trained
   athletes. Ours is 3 weeks.
   *Recommended:* keep 3 weeks off for now, and answer question 5 so the
   weeks after it ramp instead of jumping.

5. **How big is the first step back after the spring break?** The engine goes
   from half the summer hours in spring week 3 to full loading hours in week
   4. Couzens says the first month back is the most tiring and ramps about 10
   CTL a month. No rule of ours sets this step.
   *Recommended:* rule a ramp for the first loading block after the break
   (the size is yours; Couzens's numbers are in TSS, not hours).

6. **Should strength go on hard days or easy days?** The engine puts strength
   on hard days first. Couzens keeps heavy strength and hard endurance work on
   separate days, and the approved Birkie programs mostly do too (skate never,
   classic 5 of 20 times).
   *Recommended:* follow the approved programs: strength on non-hard days
   unless the week has no room, and say so in the review.

7. **Should taper length change with the skier or the race?** Couzens says
   fitter athletes need shorter tapers, shorter races need longer ones, and
   bigger athletes need longer ones. AE-SKI-2.10 gives every skier the same
   2-week cut. He gives no week counts.
   *Recommended:* keep one taper for everyone (there are no sized numbers to
   build from), and note it in the coach review for sprint racers.

8. **How long can a marathon long session get?** Couzens (Ironman) wants
   aerobic endurance to reach race duration. Our cap is 3.5 h, below many
   recreational Birkie classic finish times.
   *Recommended:* keep 3.5 h; his rule is written for Ironman and nothing in
   the ski sources asks for more.

Not raised as questions (additions with no contradiction, open for later):
two recovery weeks for some skiers (CW10), a mid-season unload (CW11/CW22), a
session energy rating (CW31), a failed-test rule (CW32), aerobic strength
below 60% RM and a squat benchmark (CW28/CW29), masters line at 30 vs 40
(CW30).
