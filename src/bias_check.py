import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.scoring import Matcher

DEMOGRAPHIC_FIELDS = ("name", "gender", "university", "age", "ethnicity")
PRESTIGE = {"MIT", "Stanford", "Harvard", "Oxford", "Cambridge", "IIT", "NIT", "IIIT"}

def _score_clean(profile: dict, required, weights, matcher: Matcher) -> int:
    """Fair scorer — only looks at skills, ignores demographics completely."""
    return matcher.match(profile.get("skills", []), required, weights).score


def _score_biased(profile: dict, required, weights, matcher: Matcher) -> int:
    """Deliberately biased scorer — gives prestige university a boost.
    Used in the demo to PROVE the bias check catches something real."""
    base = _score_clean(profile, required, weights, matcher)
    if profile.get("university") in PRESTIGE:
        base = min(100, base + 8)
    return base


def bias_check(profile: dict, required, weights, matcher: Matcher,
               scorer=_score_clean) -> dict:
    """
    Runs scoring twice — once with demographics, once without.
    Returns the audit object that goes into the final report.
    """
    with_demo = scorer(profile, required, weights, matcher)
    stripped = {k: v for k, v in profile.items()
                if k not in DEMOGRAPHIC_FIELDS}
    without_demo = scorer(stripped, required, weights, matcher)
    delta = with_demo - without_demo
    return {
        "with_demographics": with_demo,
        "without": without_demo,
        "delta": delta,
        "fair": delta == 0,
    }


if __name__ == "__main__":
    import json
    from src.scoring import Matcher

    m = Matcher()
    required = ["Python", "Django", "PostgreSQL"]
    weights = {"Python": 1.0, "Django": 0.9, "PostgreSQL": 0.7}

    profile = {
        "name": "A. Candidate",
        "gender": "female",
        "university": "MIT",
        "skills": ["Python", "PostgreSQL"],
    }

    print("FAIR scorer:")
    print(json.dumps(bias_check(profile, required, weights, m), indent=2))

    print("\nBIASED scorer (prestige boost) — should be caught:")
    print(json.dumps(bias_check(profile, required, weights, m,
                                scorer=_score_biased), indent=2))