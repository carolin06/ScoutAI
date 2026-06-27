import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.contracts import (
    GitHubSignals, CodeQuality, JDSkills, AssessmentResult
)

# Fake GitHub signals — pretend the extractor already ran
MOCK_GITHUB = GitHubSignals(
    username="sample_dev",
    languages={"Python": 0.62, "JavaScript": 0.28, "Go": 0.10},
    active_repos=12,
    original_ratio=0.75,
    commit_quality=0.8,
    inferred_skills=["Python", "JavaScript", "Go", "REST APIs", "PostgreSQL"],
    code_quality=CodeQuality(
        tests_present=0.78,
        llm_readability=4.3,
        avg_complexity="low",
        score=4.1
    ),
)

# Fake JD skills — pretend the JD parser already ran
MOCK_JD = JDSkills(
    required=["Python", "Django", "PostgreSQL", "REST APIs", "Docker"],
    weights={
        "Python": 1.0,
        "Django": 0.9,
        "PostgreSQL": 0.7,
        "REST APIs": 0.6,
        "Docker": 0.5
    },
)

# Fake AssessmentResult — pretend Jason's adaptive assessment already ran
# Replace this with Jason's real output at the hour-9 sync
MOCK_ASSESSMENT = AssessmentResult(
    skill="Python",
    verified_band="intermediate",
    trajectory=[3, 4, 4, 5, 4],
    confidence=0.82,
)

# Fake candidate profile for bias check testing
MOCK_CANDIDATE_PROFILE = {
    "name": "A. Candidate",
    "gender": "female",
    "university": "State University",
    "skills": ["Python", "JavaScript", "Go", "REST APIs", "PostgreSQL"],
}

# Fake employee list for internal mobility stretch (Area 03)
MOCK_EMPLOYEES = [
    {"id": "E_017", "skills": ["Python", "Django", "PostgreSQL"]},
    {"id": "E_042", "skills": ["Python", "Docker", "REST APIs"]},
    {"id": "E_103", "skills": ["Java", "Spring"]},
    {"id": "E_088", "skills": ["Python", "Flask", "PostgreSQL", "Docker"]},
]