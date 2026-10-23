"""Numeric daily pace rules shared without sharing evidence or interpretations."""

PROFILE_ID = "rtpeval_daily_density_3"
LEGACY_PROFILE_ID = "rtpeval_daily_density_2"

PENALTIES = {
    "ordinary": [100, 40, 0, 10, 50, 80],
    "relaxed": [100, 20, 0, 40, 70, 90],
    "rich": [100, 60, 10, 0, 30, 70],
}
PENALTY_PROFILES = {
    PROFILE_ID: PENALTIES,
    LEGACY_PROFILE_ID: {**PENALTIES, "rich": [100, 60, 0, 0, 30, 70]},
}


def daily_penalty(count, profile, exact_count=None, *, rules_profile_id=PROFILE_ID):
    penalties = PENALTY_PROFILES[rules_profile_id]
    if exact_count is not None:
        return 0 if count == exact_count else 100
    if profile not in penalties:
        return None
    return penalties[profile][count] if count < 6 else 100


def zero_penalty_counts(profile, exact_count=None):
    if exact_count is not None:
        return (exact_count,)
    return tuple(n for n, p in enumerate(PENALTIES.get(profile, ())) if p == 0)
