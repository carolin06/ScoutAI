import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import json
from src.contracts import asdict
from src.assessment import run_multi_skill_assessment
from src.glassbox import build_report
from src.scoring import Matcher
from src.bias_check import bias_check
from src.mock_data import MOCK_GITHUB, MOCK_JD, MOCK_CANDIDATE_PROFILE


def run():
    print("=== ScoutAI — Full Pipeline B ===\n")

    # use Carolin's real scoring engine
    matcher = Matcher()

    # candidate skills from GitHub signals
    candidate_skills = MOCK_GITHUB.inferred_skills
    print(f"Candidate skills from GitHub: {candidate_skills}")

    # baseline match against JD
    print("\n=== 1. Baseline match ===")
    baseline = matcher.match(
        candidate_skills,
        MOCK_JD.required,
        MOCK_JD.weights
    )
    print(json.dumps(asdict(baseline), indent=2))

    # run multi-skill adaptive assessment
    print("\n=== 2. Live adaptive assessment ===")
    assessment_results = run_multi_skill_assessment(
        required=MOCK_JD.required,
        weights=MOCK_JD.weights,
        max_skills=2,
        questions_per_skill=2
    )

    # use first assessment result for scoring
    primary_assessment = assessment_results[0] if assessment_results else None

    # reconciled match with assessment
    print("\n=== 3. Reconciled match with assessment ===")
    verified = matcher.match(
        candidate_skills,
        MOCK_JD.required,
        MOCK_JD.weights,
        assessment=primary_assessment
    )
    print(json.dumps(asdict(verified), indent=2))

    # bias check
    print("\n=== 4. Bias check ===")
    profile = dict(MOCK_CANDIDATE_PROFILE)
    profile["skills"] = candidate_skills
    bias_result = bias_check(
        profile,
        MOCK_JD.required,
        MOCK_JD.weights,
        matcher
    )
    print(json.dumps(bias_result, indent=2))

    # build evidence panel
    evidence = {
        "languages": MOCK_GITHUB.languages,
        "code_quality_score": MOCK_GITHUB.code_quality.score,
        "active_repos": MOCK_GITHUB.active_repos,
        "assessments": [asdict(r) for r in assessment_results]
    }

    # glass-box report
    print("\n=== 5. Final glass-box report ===")
    report = build_report(
        match=verified,
        evidence=evidence,
        assessment=primary_assessment,
        bias_check=bias_result,
    )
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    run()