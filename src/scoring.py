import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.contracts import MatchResult, AssessmentResult

_MODEL = None
MATCH_THRESHOLD = 0.55

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

class Matcher:
    def __init__(self, embedder=None, threshold: float = MATCH_THRESHOLD):
        self.embed = embedder or _default_embedder
        self.threshold = threshold

    def match(self, candidate_skills: list, required: list,
              weights: dict = None,
              assessment: AssessmentResult = None) -> MatchResult:
        weights = weights or {s: 1.0 for s in required}
        if not required:
            return MatchResult(score=0, matched=[], missing=[])
        if not candidate_skills:
            return MatchResult(score=0, matched=[], missing=list(required))

        req_vec = self.embed(required)
        cand_vec = self.embed(candidate_skills)
        sims = _cosine_matrix(req_vec, cand_vec)

        matched, missing = [], []
        for i, skill in enumerate(required):
            best = float(sims[i].max())
            if best >= self.threshold:
                matched.append(skill)
            else:
                missing.append(skill)

        total_w = sum(weights.get(s, 1.0) for s in required) or 1.0
        got_w = sum(weights.get(s, 1.0) for s in matched)
        score = 100.0 * got_w / total_w

        claim_supported = None
        if assessment is not None:
            score, claim_supported = self._apply_assessment(score, assessment)

        return MatchResult(
            score=int(round(score)),
            matched=matched,
            missing=missing,
            claim_supported=claim_supported,
        )

    def _apply_assessment(self, score: float, a: AssessmentResult):
        band_value = {"beginner": 1, "intermediate": 2, "advanced": 3}.get(
            a.verified_band, 0)
        if band_value == 0:
            return score, None
        delta = (band_value - 2) * 6 * max(a.confidence, 0.3)
        supported = band_value >= 2
        return max(0.0, min(100.0, score + delta)), supported
    
if __name__ == "__main__":
    import json
    from src.contracts import asdict

    m = Matcher()
    candidate = ["Python", "REST APIs", "PostgreSQL"]
    required = ["Python", "Django", "PostgreSQL", "Docker"]
    weights = {"Python": 1.0, "Django": 0.9, "PostgreSQL": 0.7, "Docker": 0.5}

    result = m.match(candidate, required, weights)
    print(json.dumps(asdict(result), indent=2))