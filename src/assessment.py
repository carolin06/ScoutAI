import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from src.contracts import AssessmentResult
from src.question_bank import get_question, get_smart_question
from src.judge0 import grade

MIN_LEVEL = 1
MAX_LEVEL = 5

TESTABLE_SKILLS = {
    "Python", "JavaScript", "Java", "C++",
    "C#", "Ruby", "Go", "Rust", "TypeScript"
}

FRAMEWORK_MAP = {
    "Django": "Python",
    "Flask": "Python",
    "FastAPI": "Python",
    "React": "JavaScript",
    "Vue": "JavaScript",
    "Angular": "TypeScript",
    "Express": "JavaScript",
    "Spring": "Java",
}


def pick_skills_to_verify(required: list, weights: dict,
                          top_n: int = 3) -> list:
    """
    Picks top N skills to verify.
    With MCQ support, ALL skills are now testable.
    """
    sorted_skills = sorted(
        required,
        key=lambda s: weights.get(s, 0.5),
        reverse=True
    )
    return sorted_skills[:top_n]


class AdaptiveAssessment:
    def __init__(self, skill: str = "Python",
                 start_difficulty: int = 3,
                 max_questions: int = 5,
                 mode: str = "local",
                 mcq_only: bool = False):
        self.skill = skill
        self.question_skill = FRAMEWORK_MAP.get(skill, skill)
        self.difficulty = start_difficulty
        self.max_questions = max_questions
        self.mode = mode
        self.mcq_only = mcq_only
        self.asked = set()
        self.history = []
        self.questions = []

    def next_question(self) -> dict | None:
        if len(self.history) >= self.max_questions:
            return None
        question = get_smart_question(
            skill=self.question_skill,
            difficulty=self.difficulty,
            asked=self.asked,
            mcq_only=self.mcq_only
        )
        if question is None:
            return None
        self.asked.add(question["id"])
        self.questions.append(question)
        return question

    def submit(self, question: dict,
               candidate_answer: str) -> bool:
        """
        Handles both MCQ and coding submissions.
        MCQ: checks if answer matches correct option
        Coding: runs code against test cases
        """
        if question["type"] == "mcq":
            passed = (
                candidate_answer.strip().upper() ==
                question["correct"]
            )
            result = {
                "passed": passed,
                "passed_count": 1 if passed else 0,
                "total": 1
            }
        else:
            result = grade(
                candidate_answer,
                question,
                mode=self.mode
            )
            passed = result["passed"]

        self.history.append({
            "id": question["id"],
            "skill": self.skill,
            "difficulty": question["difficulty"],
            "passed": passed,
            "passed_count": result["passed_count"],
            "total": result["total"],
            "type": question["type"]
        })

        if passed:
            self.difficulty = min(MAX_LEVEL, self.difficulty + 1)
        else:
            self.difficulty = max(MIN_LEVEL, self.difficulty - 1)

        return passed

    def finalize(self) -> AssessmentResult:
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


def run_multi_skill_assessment(required: list, weights: dict,
                               max_skills: int = 3,
                               questions_per_skill: int = 2,
                               mode: str = "local",
                               mcq_only: bool = False) -> list:
    """
    Runs adaptive assessment on top N skills.
    Python → coding questions
    Everything else → MCQ questions
    mcq_only=True → MCQ for all skills
    """
    skills_to_test = pick_skills_to_verify(
        required, weights, max_skills
    )
    print(f"Skills selected for assessment: {skills_to_test}")

    results = []
    for skill in skills_to_test:
        print(f"\n--- Testing: {skill} ---")
        a = AdaptiveAssessment(
            skill=skill,
            start_difficulty=3,
            max_questions=questions_per_skill,
            mode=mode,
            mcq_only=mcq_only
        )
        while (q := a.next_question()) is not None:
            if q["type"] == "mcq":
                # simulate: answer correctly if difficulty <= 3
                if q["difficulty"] <= 3:
                    answer = q["correct"]
                else:
                    answer = "A"  # wrong answer simulation
            else:
                # coding: use solution if difficulty <= 3
                if q["difficulty"] <= 3:
                    answer = q["_solution"]
                else:
                    answer = q["starter_code"]

            passed = a.submit(q, answer)
            print(f"  {q['type'].upper()} L{q['difficulty']} -> "
                  f"{'PASS' if passed else 'FAIL'}")

        result = a.finalize()
        results.append(result)
        print(f"  band: {result.verified_band} "
              f"(confidence {result.confidence})")

    return results


if __name__ == "__main__":
    import json
    from src.contracts import asdict

    print("=== Smart assessment (Python=coding, rest=MCQ) ===")
    required = ["Python", "SQL", "Docker", "AWS"]
    weights = {
        "Python": 1.0,
        "SQL": 0.9,
        "Docker": 0.7,
        "AWS": 0.5
    }
    results = run_multi_skill_assessment(
        required, weights,
        max_skills=3,
        questions_per_skill=2
    )
    for r in results:
        print(json.dumps(asdict(r), indent=2))

    print("\n=== MCQ only mode ===")
    results = run_multi_skill_assessment(
        required, weights,
        max_skills=2,
        questions_per_skill=2,
        mcq_only=True
    )
    for r in results:
        print(json.dumps(asdict(r), indent=2))