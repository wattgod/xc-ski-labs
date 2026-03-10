"""
Nordic Lab — XC Ski Race Scoring System
14 criteria, 1-5 scale, overall_score = round((sum/70)*100)
Tiers: T1 (>=80), T2 (>=60), T3 (>=45), T4 (<45)
Prestige override: p5 + score>=75 → T1, p5 + score<75 → T2 cap, p4 = 1-tier promotion (not into T1)
"""

CRITERIA = [
    "distance",
    "elevation",
    "altitude",
    "field_size",
    "prestige",
    "international_draw",
    "course_technicality",
    "snow_reliability",
    "grooming_quality",
    "accessibility",
    "community",
    "scenery",
    "organization",
    "competitive_depth",
]

TIER_THRESHOLDS = {
    1: 80,
    2: 60,
    3: 45,
    4: 0,
}


def _parse_score(raw):
    """Safely parse a score value. Handles str, float, int, None."""
    if raw is None or raw == "":
        return None
    try:
        val = float(raw)
        return round(val)
    except (ValueError, TypeError):
        return None


def calculate_overall_score(ratings: dict) -> int:
    """Calculate overall score from individual criterion ratings (1-5 scale)."""
    total = 0
    for criterion in CRITERIA:
        val = _parse_score(ratings.get(criterion))
        if val is None:
            raise ValueError(f"Missing or invalid score for '{criterion}'")
        if not 1 <= val <= 5:
            raise ValueError(f"Score for '{criterion}' must be 1-5, got {val}")
        total += val
    return round((total / 70) * 100)


def determine_tier(overall_score: int, prestige: int = None) -> int:
    """Determine tier with optional prestige override."""
    # Base tier from score
    if overall_score >= TIER_THRESHOLDS[1]:
        base_tier = 1
    elif overall_score >= TIER_THRESHOLDS[2]:
        base_tier = 2
    elif overall_score >= TIER_THRESHOLDS[3]:
        base_tier = 3
    else:
        base_tier = 4

    # Prestige overrides
    if prestige == 5:
        if overall_score >= 75:
            return 1
        else:
            return min(base_tier, 2)  # Cap at T2
    elif prestige == 4:
        # 1-tier promotion, but not into T1
        promoted = max(base_tier - 1, 2)
        return min(promoted, base_tier)  # Don't worsen

    return base_tier


def tier_label(tier: int) -> str:
    return f"TIER {tier}"


def score_race(ratings: dict) -> dict:
    """Score a race and return full rating result."""
    overall = calculate_overall_score(ratings)
    prestige = _parse_score(ratings.get("prestige"))
    tier = determine_tier(overall, prestige)

    return {
        "overall_score": overall,
        "tier": tier,
        "tier_label": tier_label(tier),
        **{c: _parse_score(ratings[c]) for c in CRITERIA},
    }


if __name__ == "__main__":
    # Example: Vasaloppet
    example = {
        "distance": 5,       # 90km
        "elevation": 3,       # ~850m
        "altitude": 2,        # 350m start
        "field_size": 5,      # 16,000
        "prestige": 5,        # Founded 1922, THE race
        "international_draw": 5,
        "course_technicality": 3,
        "snow_reliability": 5,
        "grooming_quality": 5,
        "accessibility": 4,
        "community": 5,
        "scenery": 4,
        "organization": 5,
        "competitive_depth": 5,
    }
    result = score_race(example)
    print(f"Vasaloppet: {result['overall_score']}% — {result['tier_label']}")
