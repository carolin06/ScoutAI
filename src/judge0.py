import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import json
import subprocess
import tempfile
import requests

PYTHON_LANGUAGE_ID = 71
JUDGE0_URL = os.environ.get("JUDGE0_URL", "")
JUDGE0_KEY = os.environ.get("JUDGE0_KEY", "")
JUDGE0_HOST = os.environ.get("JUDGE0_HOST", "")
def _build_program(candidate_code: str, question: dict) -> str:
    """
    Combines the candidate's code with a test driver that runs
    all test cases and prints how many passed.
    """
    fn = question["function_name"]
    tests = json.dumps(question["tests"])
    
    driver = f"""
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
    return candidate_code + "\n" + driver

def _grade_local(candidate_code: str, question: dict, timeout: int = 5) -> dict:
    """DEV ONLY — runs code locally. Never use for real candidates."""
    program = _build_program(candidate_code, question)
    
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(program)
        path = f.name
    
    try:
        out = subprocess.run(
            ["python", path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        line = (out.stdout or "").strip().split("\n")[-1]
        passed, total = (int(x) for x in line.split())
    except Exception:
        passed, total = 0, len(question["tests"])
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    
    return {
        "passed": passed == total and total > 0,
        "passed_count": passed,
        "total": total
    }


def _grade_judge0(candidate_code: str, question: dict) -> dict:
    """Real sandboxed execution via Judge0."""
    url = JUDGE0_URL.rstrip("/") + "/submissions?base64_encoded=false&wait=true"
    headers = {
        "Content-Type": "application/json",
        "X-RapidAPI-Key": JUDGE0_KEY,
        "X-RapidAPI-Host": JUDGE0_HOST,
    }
    body = {
        "source_code": _build_program(candidate_code, question),
        "language_id": PYTHON_LANGUAGE_ID,
        "stdin": ""
    }
    r = requests.post(url, headers=headers, json=body, timeout=20)
    r.raise_for_status()
    data = r.json()
    
    line = (data.get("stdout") or "").strip().split("\n")[-1]
    try:
        passed, total = (int(x) for x in line.split())
    except Exception:
        passed, total = 0, len(question["tests"])
    
    return {
        "passed": passed == total and total > 0,
        "passed_count": passed,
        "total": total,
        "status": (data.get("status") or {}).get("description", "")
    }


def grade(candidate_code: str, question: dict, use_judge0: bool = False) -> dict:
    """Main entry point. Switch use_judge0=True for the real demo."""
    if use_judge0:
        return _grade_judge0(candidate_code, question)
    return _grade_local(candidate_code, question)


if __name__ == "__main__":
    from src.question_bank import get_question
    print("Generating a test question...")
    q = get_question("Python", 2)
    if q:
        print(f"Question: {q['prompt']}")
        print("\nGrading correct solution...")
        print(grade(q["_solution"], q))
        print("\nGrading wrong solution...")
        print(grade(q["starter_code"], q))