from dotenv import load_dotenv
load_dotenv()
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import re
import subprocess
import tempfile
from groq import Groq

client = None

def _get_client():
    global client
    if client is None:
        client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    return client


def _call_llm(prompt: str) -> str:
    response = _get_client().chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2048,
    )
    return response.choices[0].message.content


# ── CODING QUESTIONS ───────────────────────────────────────

def _generate_question(skill: str, difficulty: int) -> dict:
    prompt = f"""Generate a {skill} coding question at difficulty {difficulty}/5.

Return ONLY this JSON, nothing else, no explanation:
{{
"id":"gen_{skill.lower()}_l{difficulty}",
"skill":"{skill}",
"difficulty":{difficulty},
"type":"coding",
"prompt":"function description",
"function_name":"fn_name",
"starter_code":"def fn_name(x):\\n    pass",
"tests":[{{"args":[1],"expected":1}},{{"args":[2],"expected":4}},{{"args":[3],"expected":9}}],
"_solution":"def fn_name(x):\\n    return x*x"
}}

Rules:
- difficulty 1: arithmetic, string length
- difficulty 2: loops, basic list ops
- difficulty 3: sorting, two sum, palindrome
- difficulty 4: hash maps, sliding window
- difficulty 5: dynamic programming
- solution must be ONE line only, no multiline
- keep entire JSON under 400 characters total
- use shortest possible solution
- tests must have exactly 3 cases
- CRITICAL: if function takes a list, args must be [[1,2,3]] not [1,2,3]
- args is always a list of arguments, each argument wrapped separately
- example: fn([1,2,3]) -> args must be [[1,2,3]]
- example: fn(5) -> args must be [5]
- example: fn("hello") -> args must be ["hello"]
- NO imports needed

Generate for {skill} difficulty {difficulty}:"""

    raw = _call_llm(prompt).strip()
    raw = re.sub(r"^```(json)?|```$", "", raw,
                 flags=re.MULTILINE).strip()
    return json.loads(raw)


def _verify_question(question: dict) -> bool:
    fn = question["function_name"]
    tests = json.dumps(question["tests"])

    program = question["_solution"] + f"""
import json as _json
_cases = _json.loads({tests!r})
_passed = 0
for _c in _cases:
    try:
        _r = {fn}(*_c["args"])
        if _r == _c["expected"]:
            _passed += 1
    except Exception:
        pass
print(_passed, len(_cases))
"""
    try:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".py", delete=False
        ) as f:
            f.write(program)
            path = f.name

        out = subprocess.run(
            ["python", path],
            capture_output=True,
            text=True,
            timeout=5
        )
        line = (out.stdout or "").strip().split("\n")[-1]
        passed, total = (int(x) for x in line.split())
        return passed == total and total > 0

    except Exception:
        return False

    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def get_question(skill: str, difficulty: int,
                 asked: set = None,
                 max_retries: int = 3) -> dict | None:
    """
    Generates and verifies a coding question.
    Retries up to max_retries if LLM makes a mistake.
    """
    asked = asked or set()

    for attempt in range(max_retries):
        try:
            print(f"  generating {skill} L{difficulty} "
                  f"(attempt {attempt + 1}/{max_retries})...")
            question = _generate_question(skill, difficulty)

            if question["id"] in asked:
                question["id"] = question["id"] + f"_{attempt}"

            if _verify_question(question):
                print(f"  verified ok")
                return question
            else:
                print(f"  solution failed its own tests, retrying...")

        except json.JSONDecodeError:
            print(f"  LLM returned invalid JSON, retrying...")
        except Exception as e:
            print(f"  error: {e}, retrying...")

    print(f"  failed after {max_retries} attempts")
    return None


# ── MCQ QUESTIONS ──────────────────────────────────────────

def _generate_mcq(skill: str, difficulty: int) -> dict:
    prompt = f"""Generate a multiple choice question for {skill} at difficulty {difficulty}/5.

Difficulty guide:
- Level 1: basic concepts, definitions
- Level 2: simple usage, syntax
- Level 3: intermediate concepts, common patterns
- Level 4: advanced concepts, edge cases
- Level 5: expert level, architecture, optimization

Return ONLY this JSON, nothing else, no markdown:
{{
    "id": "mcq_{skill.lower()}_l{difficulty}",
    "skill": "{skill}",
    "difficulty": {difficulty},
    "type": "mcq",
    "prompt": "the question here",
    "options": {{
        "A": "first option",
        "B": "second option",
        "C": "third option",
        "D": "fourth option"
    }},
    "correct": "B",
    "explanation": "one sentence why B is correct"
}}

Rules:
- exactly 4 options A B C D
- only ONE correct answer
- make wrong options plausible, not obviously wrong
- explanation must be clear and concise
- Return ONLY JSON, no extra text"""

    raw = _call_llm(prompt).strip()
    raw = re.sub(r"^```(json)?|```$", "", raw,
                 flags=re.MULTILINE).strip()
    return json.loads(raw)


def get_mcq_question(skill: str, difficulty: int,
                     asked: set = None,
                     max_retries: int = 3) -> dict | None:
    """
    Generates an MCQ question for any skill.
    No code execution needed — just LLM generation.
    Works for SQL, Docker, AWS, system design, anything.
    """
    asked = asked or set()

    for attempt in range(max_retries):
        try:
            print(f"  generating MCQ {skill} L{difficulty} "
                  f"(attempt {attempt + 1}/{max_retries})...")
            question = _generate_mcq(skill, difficulty)

            # basic validation
            if not all(k in question for k in [
                "prompt", "options", "correct", "explanation"
            ]):
                print(f"  missing fields, retrying...")
                continue

            if question["correct"] not in ["A", "B", "C", "D"]:
                print(f"  invalid correct answer, retrying...")
                continue

            if len(question["options"]) != 4:
                print(f"  wrong number of options, retrying...")
                continue

            if question["id"] in asked:
                question["id"] = question["id"] + f"_{attempt}"

            print(f"  MCQ verified ok")
            return question

        except json.JSONDecodeError:
            print(f"  LLM returned invalid JSON, retrying...")
        except Exception as e:
            print(f"  error: {e}, retrying...")

    print(f"  failed after {max_retries} attempts")
    return None


# ── SMART QUESTION PICKER ──────────────────────────────────

def get_smart_question(skill: str, difficulty: int,
                       asked: set = None,
                       mcq_only: bool = False) -> dict | None:
    """
    Smart picker:
    - mcq_only=True → always generate MCQ
    - skill is Python → coding question
    - everything else → MCQ
    """
    CODING_SKILLS = {"Python"}

    if mcq_only or skill not in CODING_SKILLS:
        return get_mcq_question(skill, difficulty, asked)
    else:
        q = get_question(skill, difficulty, asked)
        if q is None:
            # fallback to MCQ if coding fails
            print(f"  coding failed, falling back to MCQ")
            return get_mcq_question(skill, difficulty, asked)
        return q


if __name__ == "__main__":
    print("=== Testing coding question ===")
    q = get_question("Python", 3)
    if q:
        print(f"Prompt: {q['prompt']}")
        print(f"Type: {q['type']}")

    print("\n=== Testing MCQ question ===")
    q = get_mcq_question("SQL", 3)
    if q:
        print(f"Prompt: {q['prompt']}")
        print(f"Options: {q['options']}")
        print(f"Correct: {q['correct']}")
        print(f"Explanation: {q['explanation']}")

    print("\n=== Testing smart picker ===")
    q = get_smart_question("Docker", 2)
    if q:
        print(f"Skill: {q['skill']}, Type: {q['type']}")
        print(f"Prompt: {q['prompt']}")