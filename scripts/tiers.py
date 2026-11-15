"""Race tier names: the one mapping every XC Ski Labs generator uses.

The names are Gravel God's (gravel-race-automation scripts/generate_llms_txt.py
TIER_LABELS): Tier 1 Elite, Tier 2 Contender, Tier 3 Solid, Tier 4 Roster.
The thresholds live in scripts/scoring.py; this module only names tiers.

An unknown tier raises: a page never shows a guessed tier name.
"""

from __future__ import annotations

TIER_NAMES: dict[int, str] = {1: "Elite", 2: "Contender", 3: "Solid", 4: "Roster"}


def _tier(tier) -> int:
    try:
        n = int(tier)
    except (TypeError, ValueError):
        raise ValueError(f"unknown race tier: {tier!r}") from None
    if n not in TIER_NAMES:
        raise ValueError(f"unknown race tier: {tier!r}")
    return n


def tier_name(tier) -> str:
    """'Elite' for 1, 'Contender' for 2, 'Solid' for 3, 'Roster' for 4."""
    return TIER_NAMES[_tier(tier)]


def tier_label(tier) -> str:
    """'Tier 1 (Elite)': the Gravel God llms.txt label."""
    n = _tier(tier)
    return f"Tier {n} ({TIER_NAMES[n]})"


def tier_badge(tier) -> str:
    """'TIER 1 · ELITE': the display-caps badge on race pages."""
    n = _tier(tier)
    return f"TIER {n} · {TIER_NAMES[n].upper()}"
