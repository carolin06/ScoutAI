import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
from src.contracts import MatchResult, AssessmentResult, FinalReport


def reasoning_chain(match: MatchResult,
                    assessment: AssessmentResult = None,
                    evidence: dict = None,
                    llm_fn=None) -> str:
    """
    Builds a plain English explanation of why the score is what it is.
    Every clause traces back to something real and measurable.
    """
    n_req = len(match.matched) + len(match.missing)
    parts = []

    # opening — the score and skill count
    parts.append(
        f"Ranked match {match.score}%: "
        f"{len(match.matched)} of {n_req} required skills present"
    )

    # which skills matched
    if match.matched:
        parts.append("including " + ", ".join(match.matched[:3]))

    # which skills are missing
    if match.missing:
        parts.append("missing " + ", ".join(match.missing))

    # live assessment verdict
    if assessment and assessment.verified_band != "unknown":
        if match.claim_supported:
            verdict = "confirmed"
        else:
            verdict = "NOT fully supported by"
        parts.append(
            f"live assessment {verdict} the {assessment.skill} claim "
            f"({assessment.verified_band}, "
            f"confidence {assessment.confidence})"
        )

    # code quality signal
    if evidence and evidence.get("code_quality_score"):
        parts.append(
            f"code quality {evidence['code_quality_score']}/5 "
            f"from real GitHub repos"
        )

    text = "; ".join(parts) + "."

    # optional LLM rephrasing for nicer prose
    if llm_fn is not None:
        try:
            text = llm_fn(
                "Rephrase this hiring rationale in 2 crisp "
                "professional sentences, keeping every fact:\n" + text
            ).strip()
        except Exception:
            pass

    return text


def build_report(match: MatchResult,
                 evidence: dict,
                 assessment: AssessmentResult = None,
                 bias_check: dict = None,
                 llm_fn=None) -> FinalReport:
    """
    Assembles the final auditable card the UI renders.
    Combines score, evidence, reasoning, and bias check.
    """
    return FinalReport(
        score=match.score,
        evidence=evidence,
        matched=match.matched,
        missing=match.missing,
        reasoning=reasoning_chain(
            match, assessment, evidence, llm_fn
        ),
        bias_check=bias_check or {},
    )


if __name__ == "__main__":
    import json
    from src.contracts import asdict

    # mock inputs to test the glass-box standalone
    mock_match = MatchResult(
        score=68,
        matched=["Python", "REST APIs", "PostgreSQL"],
        missing=["Docker", "Django"],
        claim_supported=False,
    )
    mock_assessment = AssessmentResult(
        skill="Python",
        verified_band="intermediate",
        trajectory=[3, 4, 4, 5, 4],
        confidence=0.82,
    )
    mock_evidence = {
        "languages": {"Python": 0.62, "JavaScript": 0.28},
        "code_quality_score": 4.1,
        "active_repos": 12,
    }
    mock_bias = {
        "with_demographics": 68,
        "without": 68,
        "delta": 0,
        "fair": True,
    }

    report = build_report(
        match=mock_match,
        evidence=mock_evidence,
        assessment=mock_assessment,
        bias_check=mock_bias,
    )
    print(json.dumps(asdict(report), indent=2))