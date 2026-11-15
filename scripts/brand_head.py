"""Shared <head> pieces for the Sledge Stores brand (docs/brand/sledge-stores).

Page generators that build their own <head> use these strings so every page
loads the same three families and the approved small mark as its favicon.
"""

# README §3: Big Shoulders Stencil Display 700/900, Big Shoulders Text 600/800,
# Libre Franklin 400, 600 and italic 400, all with display=swap.
BRAND_FONT_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Big+Shoulders+Stencil+Display:wght@700;900"
    "&family=Big+Shoulders+Text:wght@600;800"
    "&family=Libre+Franklin:ital,wght@0,400;0,600;1,400"
    "&display=swap"
)

BRAND_FONT_LINKS = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
    f'<link href="{BRAND_FONT_URL}" rel="stylesheet">'
)

# README §8: favicons and app icons up to 32px use the small mark.
FAVICON_LINK = '<link rel="icon" type="image/svg+xml" href="/favicon.svg">'
