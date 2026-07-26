"""Shared text cleanup helpers for generated public surfaces."""

from __future__ import annotations

import re
from typing import Any


# Covers the public-surface estate rule, including flag indicators, pictographs,
# symbol/dingbat emoji, variation selectors, and zero-width joiners.
EMOJI_PATTERN = re.compile(
    "["
    "\\U0001F1E6-\\U0001F1FF"
    "\\U0001F300-\\U0001FAFF"
    "\\u2600-\\u27BF"
    "\\u2B00-\\u2BFF"
    "\\uFE0F"
    "\\u200D"
    "]+"
)
WHITESPACE_PATTERN = re.compile(r"\s+")


def strip_emoji(text: Any) -> str:
    """Remove emoji code points and normalize whitespace left in their place."""
    if text is None:
        return ""
    return WHITESPACE_PATTERN.sub(" ", EMOJI_PATTERN.sub("", str(text))).strip()
