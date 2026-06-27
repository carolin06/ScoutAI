import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import json
from src.contracts import asdict
from src.assessment import AdaptiveAssessment
from src.glassbox import build_report
from src.mock_data_b import (
    MOCK_MATCH,
    MOCK_BIAS_CHECK,
    MOCK_EVIDENCE,
)


def run():
    print("=== 1. Live adaptive assessment (your differentiator) ===")
    
    a = AdaptiveAssessment(
        skill="Python",
        start_difficulty=3,
        max_questions=3
    )

    while (q := a.next_question()) is not None:
        print(f"\nQuestion: {q['prompt']}")
        
        # simulate candidate: solves up to L3, fails L4+
        if q["difficulty"] <= 3:
            code = q["_solution"]
            print("Candidate: submits correct solution")
        else:
            code = q["starter_code"]
            print("Candidate: submits empty solution")

        passed = a.submit(q, code)
        print(f"Result: {'PASS' if passed else 'FAIL'} "
              f"| next difficulty: {a.difficulty}")

    assessment = a.finalize()
    print(f"\nVerified: {json.dumps(asdict(assessment), indent=2)}")

    print("\n=== 2. Glass-box report ===")
    print("(using mock MatchResult from Carolin until sync point)")
    
    report = build_report(
        match=MOCK_MATCH,
        evidence=MOCK_EVIDENCE,
        assessment=assessment,
        bias_check=MOCK_BIAS_CHECK,
    )
    print(json.dumps(asdict(report), indent=2))


if __name__ == "__main__":
    run()