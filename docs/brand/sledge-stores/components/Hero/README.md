# Hero

The top of a page: a stitched oat panel.

- **Build:** a `panel` band with a 6px ink bottom edge and a dashed stitch inset 12px.
- **Contents:**
  - a `kicker` block (ink fill, ground text, tracked .4em)
  - the `stencil-xl` title, whose last word may sit in an ink block
  - a `lede` sentence
  - on the right, one real photo or an empty labelled slot
- **Columns:** 1.5 : 1, stacking to one column under 900px. The content is padded at least 28px from the edge, so it clears the stitch. Padding is 56–104px top and bottom.
- **Slot:** an empty slot is plain text in a dashed box, not an image. Don't give it `role="img"`.
- **No salmon in the hero.** The splash belongs to the crate below it.
- **Copy:** the title and lede from the live page.
