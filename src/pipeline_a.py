import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
from src.contracts import asdict
from src.scoring import Matcher
from src.bias_check import bias_check, _score_biased
from src.mock_data import (
    MOCK_GITHUB,
    MOCK_JD,
    MOCK_ASSESSMENT,
    MOCK_CANDIDATE_PROFILE,
    MOCK_EMPLOYEES,
)


def rank_internal(employees, required, weights, matcher):
    """Same matcher, run over a list of employees. Area 03 stretch."""
    ranked = []
    for emp in employees:
        result = matcher.match(emp.get("skills", []), required, weights)
        ranked.append({
            "employee": emp.get("id", "?"),
            "score": result.score,
            "gap": result.missing,
            "upskilling": (
                f"Learn: {', '.join(result.missing[:2])}"
                if result.missing else "role-ready"
            ),
        })
    return sorted(ranked, key=lambda r: r["score"], reverse=True)


def run():
    matcher = Matcher()

    print("=== 1. GitHub signals ===")
    print(json.dumps(asdict(MOCK_GITHUB), indent=2))

    print("\n=== 2. Required skills from JD ===")
    print(json.dumps(asdict(MOCK_JD), indent=2))

    print("\n=== 3. Baseline match (no assessment yet) ===")
    baseline = matcher.match(
        MOCK_GITHUB.inferred_skills,
        MOCK_JD.required,
        MOCK_JD.weights
    )
    print(json.dumps(asdict(baseline), indent=2))

    print("\n=== 4. Match with live assessment (Jason's output, mocked) ===")
    verified = matcher.match(
        MOCK_GITHUB.inferred_skills,
        MOCK_JD.required,
        MOCK_JD.weights,
        assessment=MOCK_ASSESSMENT
    )
    print(json.dumps(asdict(verified), indent=2))

    print("\n=== 5. Bias check ===")
    profile = dict(MOCK_CANDIDATE_PROFILE)
    profile["skills"] = MOCK_GITHUB.inferred_skills
    print("Fair scorer:")
    print(json.dumps(bias_check(profile, MOCK_JD.required,
                                MOCK_JD.weights, matcher), indent=2))
    print("Biased scorer (caught):")
    print(json.dumps(bias_check(profile, MOCK_JD.required,
                                MOCK_JD.weights, matcher,
                                scorer=_score_biased), indent=2))

    print("\n=== 6. Internal mobility (Area 03 stretch) ===")
    print(json.dumps(
        rank_internal(MOCK_EMPLOYEES, MOCK_JD.required,
                      MOCK_JD.weights, matcher),
        indent=2
    ))


if __name__ == "__main__":
    run()