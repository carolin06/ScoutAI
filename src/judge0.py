import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import json
import subprocess
import tempfile
import requests

# Piston language identifiers
PISTON_LANGUAGES = {
    "Python": "python",
    "JavaScript": "javascript",
    "Java": "java",
    "C++": "c++",
    "C#": "csharp",
    "Ruby": "ruby",
    "Go": "go",
    "Rust": "rust",
    "TypeScript": "typescript",
}

# Judge0 config (fallback if you get a key later)
JUDGE0_URL = os.environ.get("JUDGE0_URL", "")
JUDGE0_KEY = os.environ.get("JUDGE0_KEY", "")
JUDGE0_HOST = os.environ.get("JUDGE0_HOST", "")
PYTHON_LANGUAGE_ID = 71


def _build_program(candidate_code: str, question: dict) -> str:
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


def _grade_local(candidate_code: str, question: dict,
                 timeout: int = 5) -> dict:
    """DEV ONLY — runs Python locally via subprocess."""
    program = _build_program(candidate_code, question)
    with tempfile.NamedTemporaryFile(
        "w", suffix=".py", delete=False
    ) as f:
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


def _grade_piston(candidate_code: str, question: dict) -> dict:
    """
    Sandboxed execution via Piston API.
    Free, no API key needed, supports 50+ languages.
    """
    skill = question.get("skill", "Python")
    language = PISTON_LANGUAGES.get(skill, "python")
    program = _build_program(candidate_code, question)

    try:
        response = requests.post(
            "https://api.piston.rs/api/v2/execute",
            json={
                "language": language,
                "version": "*",
                "files": [{"content": program}]
            },
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        output = (data.get("run") or {}).get("stdout", "").strip()
        stderr = (data.get("run") or {}).get("stderr", "")

        if stderr and not output:
            return {
                "passed": False,
                "passed_count": 0,
                "total": len(question["tests"]),
                "error": stderr[:200]
            }

        line = output.split("\n")[-1]
        passed, total = (int(x) for x in line.split())

    except Exception as e:
        return {
            "passed": False,
            "passed_count": 0,
            "total": len(question["tests"]),
            "error": str(e)
        }

    return {
        "passed": passed == total and total > 0,
        "passed_count": passed,
        "total": total
    }


def _grade_judge0(candidate_code: str, question: dict) -> dict:
    """Sandboxed execution via Judge0 RapidAPI."""
    url = JUDGE0_URL.rstrip("/") + \
          "/submissions?base64_encoded=false&wait=true"
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


def grade(candidate_code: str, question: dict,
          mode: str = "local") -> dict:
    """
    Main entry point.
    mode: "local" | "piston" | "judge0"
    """
    if mode == "piston":
        return _grade_piston(candidate_code, question)
    elif mode == "judge0":
        return _grade_judge0(candidate_code, question)
    return _grade_local(candidate_code, question)


if __name__ == "__main__":
    from src.question_bank import get_question

    print("Generating test question...")
    q = get_question("Python", 2)
    if q:
        print(f"Question: {q['prompt']}")

        print("\n--- Local runner ---")
        print(grade(q["_solution"], q, mode="local"))
        print(grade(q["starter_code"], q, mode="local"))

        print("\n--- Piston API ---")
        print(grade(q["_solution"], q, mode="piston"))
        print(grade(q["starter_code"], q, mode="piston"))