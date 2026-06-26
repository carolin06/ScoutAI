import json
import re

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.contracts import JDSkills

SKILL_VOCAB = [
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++", "C#", "Ruby",
    "Django", "Flask", "FastAPI", "React", "Vue", "Angular", "Node.js", "Express",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQL", "GraphQL", "REST APIs",
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "CI/CD",
    "Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "NLP",
    "Pandas", "NumPy", "Spark", "Kafka", "Microservices", "Git", "Linux",
]

def _llm_extract(text: str, llm_fn) -> list:
    prompt = (
        "You are a skill extraction engine. Extract all technical skills "
        "required by this job description. Return ONLY a valid JSON array "
        "of strings, no prose. Example: [\"Python\", \"Docker\"]\n\n"
        "JOB DESCRIPTION:\n" + text
    )
    raw = llm_fn(prompt).strip()
    raw = re.sub(r"^```(json)?|```$", "", raw).strip()
    skills = json.loads(raw)
    return [s.strip() for s in skills if isinstance(s, str) and s.strip()]


def _vocab_extract(text: str) -> list:
    found = []
    low = text.lower()
    for skill in SKILL_VOCAB:
        pattern = r"(?<![a-z0-9])" + re.escape(skill.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, low):
            found.append(skill)
    return found

def _infer_weights(text: str, skills: list) -> dict:
    low = text.lower()
    weights = {}
    for s in skills:
        count = low.count(s.lower())
        pos = low.find(s.lower())
        base = 0.6 + min(count * 0.15, 0.4)
        if pos != -1 and pos < len(low) * 0.3:
            base += 0.1
        weights[s] = round(min(base, 1.0), 2)
    return weights

def parse_jd(text: str, llm_fn=None) -> JDSkills:
    skills = []
    if llm_fn is not None:
        try:
            skills = _llm_extract(text, llm_fn)
        except Exception:
            skills = []
    if not skills:
        skills = _vocab_extract(text)
    seen, ordered = set(), []
    for s in skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            ordered.append(s)
    return JDSkills(required=ordered, weights=_infer_weights(text, ordered))


if __name__ == "__main__":
    sample = """
    We are hiring a Backend Engineer. You must have strong Python and Django
    experience, build REST APIs, and work with PostgreSQL. Familiarity with
    Docker and AWS is a plus. Bonus: Kubernetes.
    """
    result = parse_jd(sample)
    import json
    from src.contracts import asdict
    print(json.dumps(asdict(result), indent=2))