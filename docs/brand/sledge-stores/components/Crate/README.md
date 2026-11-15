# Crate

A product or a group of lessons, packed as an oat crate.

- **Build:** a `panel` fill, a 14px inset, a 2px dashed ink stitch, and 14px navy slats top and bottom (22px slat, 4px gap).
- **Contents, in order:**
  1. `crate-title`
  2. a stencilled `price`
  3. the description in `body`
  4. one luggage tag with the stat line
  5. a full-width button at the bottom
- **Splash crate:** at most one per page. It is the current item or, on a sales page, the recommended purchase. It has a `splash` fill, `splash-deep` slats, an ink stitch, and a `Recommended` (or `Now`) ribbon in `tag-paper`. Its button is a navy slab with `on-splash-action` (wool) text in both themes, and no underline.
- **Grid:**
  - **Source order:** the splash crate comes first, so it is first in focus order and first on screen below 980px.
  - 980px and wider: three columns at 1 : 1 : 1.25. The splash crate is placed in the wide right column.
  - 640 to 979px: the splash crate spans the top row, with the other two below it.
  - Under 640px: one column, with the splash crate first.
- **Copy:** the live product copy, verbatim.
- Not specified yet: the owned state, which will use `done` and the word "Owned".
