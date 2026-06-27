import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.contracts import MatchResult, AssessmentResult

# Fake MatchResult — pretend Carolin's scorer already ran
# Replace with real MatchResult at the hour-9 sync
MOCK_MATCH = MatchResult(
    score=68,
    matched=["Python", "REST APIs", "PostgreSQL"],
    missing=["Docker", "Django"],
    claim_supported=False,
)

# Fake bias check — pretend Carolin's bias_check already ran
MOCK_BIAS_CHECK = {
    "with_demographics": 68,
    "without": 68,
    "delta": 0,
    "fair": True,
}

# Fake evidence panel — GitHub signals summary
MOCK_EVIDENCE = {
    "languages": {"Python": 0.62, "JavaScript": 0.28},
    "code_quality_score": 4.1,
    "active_repos": 12,
}

# Your OWN assessment output — this one YOU produce for real
MOCK_ASSESSMENT_RESULT = AssessmentResult(
    skill="Python",
    verified_band="intermediate",
    trajectory=[3, 4, 4, 5, 4],
    confidence=0.82,
)