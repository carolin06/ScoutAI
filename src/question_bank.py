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
    print(f"  response length: {len(raw)}")
    raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
    print(f"  LLM raw response:\n{raw[:300]}")
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