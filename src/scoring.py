import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import json
import re
from src.contracts import MatchResult, AssessmentResult

_MODEL = None
MATCH_THRESHOLD = 0.45


def _default_embedder(texts: list):
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL.encode(texts, normalize_embeddings=True)


def _cosine_matrix(a, b):
    import numpy as np
    a, b = np.asarray(a), np.asarray(b)
    return a @ b.T


def normalize_skills_with_llm(candidate_skills: list,
                              required_skills: list,
                              llm_fn) -> dict:
    """
    Asks the LLM to identify which candidate skills are equivalent
    to which required skills, even with spelling/naming differences.
    Returns a mapping: {required_skill: matched_candidate_skill or None}
    """
    if not llm_fn or not candidate_skills or not required_skills:
        return {}

    prompt = f"""You are matching candidate skills against job requirements.
Some skills may be written differently but mean the same thing
(e.g. "sklearn" = "Scikit-learn", "ML" = "Machine Learning", "JS" = "JavaScript").

Candidate has these skills: {candidate_skills}
Job requires these skills: {required_skills}

For EACH required skill, find if the candidate has an equivalent skill
(exact match OR same meaning with different spelling/abbreviation).

Return ONLY a valid JSON object mapping each required skill to either
the matching candidate skill name, or null if no match:

{{"Python": "Python", "Scikit-learn": "sklearn", "TensorFlow": null}}

Return ONLY JSON, no explanation."""

    try:
        raw = llm_fn(prompt).strip()
        raw = re.sub(r"^```(json)?|```$", "", raw,
                     flags=re.MULTILINE).strip()
        return json.loads(raw)
    except Exception:
        return {}


class Matcher:
    def __init__(self, embedder=None, threshold: float = MATCH_THRESHOLD):
        self.embed = embedder or _default_embedder
        self.threshold = threshold

    def match(self, candidate_skills: list, required: list,
              weights: dict = None,
              assessment: AssessmentResult = None,
              llm_fn=None) -> MatchResult:
        weights = weights or {s: 1.0 for s in required}
        if not required:
            return MatchResult(score=0, matched=[], missing=[])
        if not candidate_skills:
            return MatchResult(score=0, matched=[], missing=list(required))

        req_vec = self.embed(required)
        cand_vec = self.embed(candidate_skills)
        sims = _cosine_matrix(req_vec, cand_vec)

        matched, missing = [], []
        partial_credit = 0.0

        for i, skill in enumerate(required):
            best = float(sims[i].max())
            w = weights.get(skill, 1.0)

            if best >= self.threshold:
                matched.append(skill)
            else:
                missing.append(skill)
                if best >= 0.30:
                    partial_credit += w * (best / self.threshold) * 0.4

        # LLM fallback for skills the embedder missed
        # (spelling differences, abbreviations like ML/AI/JS)
        if missing and llm_fn is not None:
            llm_matches = normalize_skills_with_llm(
                candidate_skills, missing, llm_fn
            )
            still_missing = []
            for skill in missing:
                if llm_matches.get(skill):
                    matched.append(skill)
                    # remove any partial credit already given
                    # for this skill to avoid double counting
                    w = weights.get(skill, 1.0)
                    idx = required.index(skill)
                    best = float(sims[idx].max())
                    if best >= 0.30:
                        partial_credit -= w * (
                            best / self.threshold
                        ) * 0.4
                else:
                    still_missing.append(skill)
            missing = still_missing

        total_w = sum(weights.get(s, 1.0) for s in required) or 1.0
        got_w = sum(weights.get(s, 1.0) for s in matched)
        score = 100.0 * (got_w + partial_credit) / total_w
        score = max(0.0, min(100.0, score))  # clamp safety net

        claim_supported = None
        if assessment is not None:
            score, claim_supported = self._apply_assessment(
                score, assessment
            )

        return MatchResult(
            score=int(round(score)),
            matched=matched,
            missing=missing,
            claim_supported=claim_supported,
        )

    def _apply_assessment(self, score: float, a: AssessmentResult):
        band_value = {
            "beginner": 1, "intermediate": 2, "advanced": 3
        }.get(a.verified_band, 0)
        if band_value == 0:
            return score, None
        delta = (band_value - 2) * 6 * max(a.confidence, 0.3)
        supported = band_value >= 2
        return max(0.0, min(100.0, score + delta)), supported


if __name__ == "__main__":
    import json as j
    from src.contracts import asdict
    from groq import Groq

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def llm_fn(prompt):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )
        return response.choices[0].message.content

    m = Matcher()
    candidate = ["Python", "sklearn", "PostgreSQL", "ML"]
    required = ["Python", "Scikit-learn", "Django", "Machine Learning"]
    weights = {
        "Python": 1.0, "Scikit-learn": 0.9,
        "Django": 0.7, "Machine Learning": 0.8
    }

    print("Without LLM fallback:")
    result = m.match(candidate, required, weights)
    print(j.dumps(asdict(result), indent=2))

    print("\nWith LLM fallback:")
    result = m.match(candidate, required, weights, llm_fn=llm_fn)
    print(j.dumps(asdict(result), indent=2))