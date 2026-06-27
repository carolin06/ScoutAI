import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from src.contracts import AssessmentResult
from src.question_bank import get_question
from src.judge0 import grade

MIN_LEVEL = 1
MAX_LEVEL = 5


class AdaptiveAssessment:
    def __init__(self, skill: str = "Python",
                 start_difficulty: int = 3,
                 max_questions: int = 5,
                 use_judge0: bool = False):
        self.skill = skill
        self.difficulty = start_difficulty
        self.max_questions = max_questions
        self.use_judge0 = use_judge0
        self.asked = set()
        self.history = []
        self.questions = []

    def next_question(self) -> dict | None:
        """
        Generates the next question at current difficulty.
        Returns None when max questions reached.
        """
        if len(self.history) >= self.max_questions:
            return None

        question = get_question(
            skill=self.skill,
            difficulty=self.difficulty,
            asked=self.asked
        )

        if question is None:
            return None

        self.asked.add(question["id"])
        self.questions.append(question)
        return question

    def submit(self, question: dict,
               candidate_code: str) -> bool:
        """
        Grades the candidate's code.
        Steps difficulty up on pass, down on fail.
        Records result in history.
        Returns True if passed.
        """
        result = grade(
            candidate_code,
            question,
            use_judge0=self.use_judge0
        )
        passed = result["passed"]

        self.history.append({
            "id": question["id"],
            "skill": question["skill"],
            "difficulty": question["difficulty"],
            "passed": passed,
            "passed_count": result["passed_count"],
            "total": result["total"]
        })

        if passed:
            self.difficulty = min(MAX_LEVEL, self.difficulty + 1)
        else:
            self.difficulty = max(MIN_LEVEL, self.difficulty - 1)

        return passed

    def finalize(self) -> AssessmentResult:
        """
        Converts the trajectory into a verified band.
        
        Band logic:
        - advanced:     solved level 4 or 5
        - intermediate: solved level 3
        - beginner:     solved level 1 or 2 only
        - unknown:      solved nothing
        """
        passed_levels = [
            h["difficulty"]
            for h in self.history
            if h["passed"]
        ]

        if not passed_levels:
            band = "unknown"
        elif max(passed_levels) >= 4:
            band = "advanced"
        elif max(passed_levels) == 3:
            band = "intermediate"
        else:
            band = "beginner"

        total = len(self.history) or 1
        passed_count = len([h for h in self.history if h["passed"]])
        confidence = round(passed_count / total, 2)

        trajectory = [h["difficulty"] for h in self.history]

        return AssessmentResult(
            skill=self.skill,
            verified_band=band,
            trajectory=trajectory,
            confidence=confidence
        )


if __name__ == "__main__":
    import json
    from src.contracts import asdict

    print("=== Simulating adaptive assessment ===")
    print("Candidate: strong at L3, struggles at L4+")
    print()

    a = AdaptiveAssessment(
        skill="Python",
        start_difficulty=3,
        max_questions=3
    )

    while (q := a.next_question()) is not None:
        print(f"Question: {q['prompt']}")

        # simulate: solve if difficulty <= 3, fail if > 3
        if q["difficulty"] <= 3:
            code = q["_solution"]
            print(f"Candidate submits correct solution")
        else:
            code = q["starter_code"]
            print(f"Candidate submits empty solution")

        passed = a.submit(q, code)
        print(f"Result: {'PASS' if passed else 'FAIL'} "
              f"| next difficulty: {a.difficulty}")
        print()

    result = a.finalize()
    print("=== Final Assessment Result ===")
    print(json.dumps(asdict(result), indent=2))