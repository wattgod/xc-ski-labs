# Nordic Race Automation

> Brand name TBD

XC ski race database, search engine, and coaching funnel.

## Disciplines

- **Classic** -- traditional technique
- **Skate** -- freestyle/skating technique

## Architecture

Mirrors the `gravel-race-automation` pattern: individual race JSON profiles, scoring system, static page generator, search UI, and coaching pipeline integration.

## Structure

```
race-data/          Race profile JSONs (one per race)
research/           Race research and source material
scripts/            Generators, validators, enrichment scripts
web/                Search UI, race index, static assets
output/             Generated race pages (gitignored)
data/               Caches, snapshots (gitignored)
tests/              Test suite
tokens/             Design system tokens (CSS)
```

## Status

Research phase. 100 race profiles created. Search UI functional.
