# Nordic Lab

XC ski race database, scoring, and search. Classic & skate. 300+ races worldwide.

## Structure

```
race-data/          Race profile JSONs (one per race)
scripts/            Generators, scrapers, scoring
tokens/             Design system tokens (CSS)
web/                Search UI, race index, static assets
data/               Caches, snapshots (gitignored)
research/           Race research and source material
tests/              Test suite
output/             Generated race pages (gitignored)
```

## Scoring

14 criteria (1-5 scale), overall_score = round((sum/70)*100)

- **T1** (>=80): Iconic, bucket-list races
- **T2** (>=60): Major regional/national events
- **T3** (>=45): Solid citizen races
- **T4** (<45): Local/niche events

Prestige override: p5 + score>=75 → T1, p5 + score<75 → T2 cap, p4 = 1-tier promotion (not into T1)

## Disciplines

- `classic` — traditional technique
- `skate` — freestyle/skating technique

## Brand

Neo-brutalist design system. Wintry palette (deep slate, ice blue, frost).
Font stack: Sometype Mono (data) + Literata (editorial).
