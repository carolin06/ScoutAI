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

def _infer_weights(text: str, skills: list, llm_fn=None) -> dict:
    """
    Uses LLM to classify each skill as must_have, strongly_preferred,
    nice_to_have, or bonus based on context in the JD.
    Falls back to position/count heuristic if no LLM.
    """
    if llm_fn is not None:
        try:
            prompt = f"""You are analyzing a job description.
For each skill in this list, classify it based on how it appears in the JD.

Skills to classify: {skills}

Job Description:
{text}

Return ONLY a valid JSON object mapping each skill to a weight:
- "must_have" or "required" or "essential" → 1.0
- "strongly preferred" or "strong experience" → 0.8
- "familiar" or "knowledge of" or "exposure" → 0.6
- "nice to have" or "plus" or "bonus" → 0.4
- not mentioned clearly → 0.5

Return exactly this format, no explanation:
{{"Python": 1.0, "Django": 0.8, "Docker": 0.4}}
"""
            raw = llm_fn(prompt).strip()
            raw = re.sub(r"^```(json)?|```$", "", raw,
                        flags=re.MULTILINE).strip()
            weights = json.loads(raw)
            # make sure every skill has a weight
            for s in skills:
                if s not in weights:
                    weights[s] = 0.5
            return weights
        except Exception:
            pass

    # fallback — keyword based
    low = text.lower()
    weights = {}
    MUST_HAVE = ["must", "required", "essential", "need", "mandatory"]
    STRONG = ["strong", "experience", "proficient", "expertise", "solid"]
    FAMILIAR = ["familiar", "knowledge", "exposure", "understanding"]
    BONUS = ["plus", "bonus", "preferred", "nice to have", "beneficial"]

    for s in skills:
        sl = s.lower()
        # find the sentence containing this skill
        sentences = text.lower().split(".")
        context = " ".join([
            sent for sent in sentences if sl in sent
        ])
        if any(w in context for w in MUST_HAVE):
            weights[s] = 1.0
        elif any(w in context for w in STRONG):
            weights[s] = 0.8
        elif any(w in context for w in FAMILIAR):
            weights[s] = 0.6
        elif any(w in context for w in BONUS):
            weights[s] = 0.4
        else:
            weights[s] = 0.5
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
    return JDSkills(
        required=ordered,
        weights=_infer_weights(text, ordered, llm_fn)  # pass llm_fn
    )


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