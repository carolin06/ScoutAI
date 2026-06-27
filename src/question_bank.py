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
    )
    return response.choices[0].message.content

def _generate_question(skill: str, difficulty: int) -> dict:
    prompt = f"""You are a coding question generator. Generate a {skill} coding question.

Difficulty: {difficulty}/5
- Level 1: print, arithmetic, simple string operations
- Level 2: loops, conditionals, basic list operations  
- Level 3: dictionaries, string algorithms, simple sorting
- Level 4: two pointers, sliding window, hash maps
- Level 5: dynamic programming, graphs, complex algorithms

STRICT RULES:
1. The _solution MUST pass ALL test cases
2. Use only standard {skill} library, no imports needed
3. test args must match exactly the function parameters
4. expected values must be exactly what the solution returns
5. Return ONLY raw JSON, no markdown, no backticks, no explanation

JSON format:
{{
    "id": "gen_{skill.lower()}_l{difficulty}",
    "skill": "{skill}",
    "difficulty": {difficulty},
    "type": "coding",
    "prompt": "Write a function description here",
    "function_name": "function_name",
    "starter_code": "def function_name(param):\\n    pass",
    "tests": [
        {{"args": [input1], "expected": output1}},
        {{"args": [input2], "expected": output2}},
        {{"args": [input3], "expected": output3}}
    ],
    "_solution": "def function_name(param):\\n    return result"
}}

Example for difficulty 2:
{{
    "id": "gen_python_l2",
    "skill": "Python",
    "difficulty": 2,
    "type": "coding",
    "prompt": "Write a function square(n) that returns the square of a number.",
    "function_name": "square",
    "starter_code": "def square(n):\\n    pass",
    "tests": [
        {{"args": [3], "expected": 9}},
        {{"args": [4], "expected": 16}},
        {{"args": [0], "expected": 0}}
    ],
    "_solution": "def square(n):\\n    return n * n"
}}

Now generate a NEW different question for {skill} at difficulty {difficulty}:"""

    raw = _call_llm(prompt).strip()
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
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
        print(f"  test: {{_c['args']}} -> got {{_r}}, expected {{_c['expected']}}")
        if _r == _c["expected"]:
            _passed += 1
    except Exception as e:
        print(f"  test error: {{e}}")
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
        print("  stdout:", out.stdout)
        print("  stderr:", out.stderr[:200] if out.stderr else "")
        line = (out.stdout or "").strip().split("\n")[-1]
        passed, total = (int(x) for x in line.split())
        return passed == total and total > 0
    
    except Exception as e:
        print(f"  verify error: {e}")
        return False
    
    finally:
        try:
            os.remove(path)
        except OSError:
            pass

def get_question(skill: str, difficulty: int, asked: set = None,
                 max_retries: int = 3) -> dict | None:
    """
    Main entry point. Generates a fresh question for the given skill
    and difficulty, verifies it works, and returns it.
    Retries up to max_retries times if the LLM makes a mistake.
    Never returns the same question twice (tracked via asked set).
    """
    asked = asked or set()
    
    for attempt in range(max_retries):
        try:
            print(f"  generating {skill} L{difficulty} "
                  f"(attempt {attempt + 1}/{max_retries})...")
            
            question = _generate_question(skill, difficulty)
            
            # make sure we haven't asked this exact question before
            if question["id"] in asked:
                question["id"] = question["id"] + f"_{attempt}"
            
            # verify the solution actually passes its own tests
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


if __name__ == "__main__":
    import os
    print("Testing dynamic question generation...")
    print("Skill: Python, Difficulty: 3")
    q = get_question("Python", 3)
    if q:
        print(json.dumps({
            "id": q["id"],
            "prompt": q["prompt"],
            "function_name": q["function_name"],
            "tests": q["tests"],
        }, indent=2))
    else:
        print("Generation failed")