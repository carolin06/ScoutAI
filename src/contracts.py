from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class CodeQuality:
    tests_present: float = 0.0
    llm_readability: float = 0.0
    avg_complexity: str = "unknown"
    score: float = 0.0

@dataclass
class ResumeClaims:
    skills: list = field(default_factory=list)
    experience: dict = field(default_factory=dict)
    raw_text: str = ""
    projects: list = field(default_factory=list)

@dataclass
class GitHubSignals:
    username: str = ""
    languages: dict = field(default_factory=dict)
    active_repos: int = 0
    original_ratio: float = 0.0
    commit_quality: float = 0.0
    inferred_skills: list = field(default_factory=list)
    code_quality: CodeQuality = field(default_factory=CodeQuality)
    note: str = ""


@dataclass
class JDSkills:
    required: list = field(default_factory=list)
    weights: dict = field(default_factory=dict)


@dataclass
class AssessmentResult:
    skill: str = ""
    verified_band: str = "unknown"
    trajectory: list = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class MatchResult:
    score: int = 0
    matched: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    claim_supported: Optional[bool] = None


@dataclass
class FinalReport:
    score: int = 0
    evidence: dict = field(default_factory=dict)
    matched: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    reasoning: str = ""
    bias_check: dict = field(default_factory=dict)


__all__ = [
    "CodeQuality", "ResumeClaims", "GitHubSignals", "JDSkills",
    "AssessmentResult", "MatchResult", "FinalReport", "asdict",
]