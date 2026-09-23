# XC Ski Labs: 1970s Nordic print direction

**Status:** September 2026 site direction. Source of truth for current CSS values:
`tokens/tokens.css`.

## Reference

The [Vintage XC Ads archive](https://crust.outlookalaska.com/VintageXCAds/)
suggests the visual language of old Nordic race advertising: assertive condensed
headlines, warm printed stock, practical product imagery, and a few strong ink
colors. Draw from the print pieces, not the archive website's own chrome. Use
original XC Ski Labs artwork and photography with permission; do not copy the ads.

## System

| Role | Token | Use |
| --- | --- | --- |
| Stock | `--gl-paper` | Reading surfaces and open space |
| Ink | `--gl-ink` | Type, rules, and dark fields |
| Primary spot | `--gl-rust` | Section emphasis and one primary action |
| Second spot | `--gl-ochre` | Small labels and ski-track detail on dark fields |
| Support inks | `--gl-slate`, `--gl-pine` | Data categories and rare editorial accents |
| Reading contrast | `--gl-caption`, `--gl-caption-on-dark` | Secondary text on the corresponding surface |

Keep hard rules and rectangular blocks. Use a narrow, upright, heavy display face
for headlines; a serif for long reading; a mono face for labels and data. Avoid
decorative gradients, orbs, glows, rounded cards, and arbitrary color coding.
Motion should explain a state change or guide attention. Honor reduced-motion
preferences and never animate the logo continuously.

## Marks

`web/xc-logo.svg` is the compact mark: four paired ski tracks cross as an X on a
dark square. Pair it with the `XC SKI LABS` wordmark in site navigation. The
wordmark carries the accessible name; the adjacent image is decorative there.
The standalone SVG contains its own accessible title and description.

## Rollout

The static site generators embed `tokens/tokens.css`; the search page currently
maintains a matching inline token block. Legacy `--gl-*` aliases remain while
existing page templates migrate to the semantic roles. The earlier Wax Bench
guidelines remain below as historical context, not current color instruction.
