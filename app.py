import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import json
import tempfile
from src.contracts import asdict
from src.jd_parser import parse_jd
from src.github_extractor import extract_github_signals
from src.scoring import Matcher
from src.bias_check import bias_check
from src.glassbox import build_report
from src.assessment import (AdaptiveAssessment,
                             run_multi_skill_assessment,
                             pick_skills_to_verify)
from src.resume_parser import parse_resume
from groq import Groq

# ── page config ────────────────────────────────────────────
st.set_page_config(
    page_title="ScoutAI — Talent Intelligence",
    page_icon="🎯",
    layout="wide"
)

# ── Groq client ────────────────────────────────────────────
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def llm_fn(prompt: str) -> str:
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content

# ── session state defaults ─────────────────────────────────
def init_state():
    defaults = {
        "stage": "input",           # input | evidence | match | assess | report
        "jd": None,
        "github": None,
        "resume": None,
        "matcher": None,
        "baseline": None,
        "assessment_obj": None,
        "current_question": None,
        "assessment_results": [],
        "verified_match": None,
        "bias_result": None,
        "report": None,
        "candidate_code": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── header ─────────────────────────────────────────────────
st.title("🎯 ScoutAI — Talent Intelligence")
st.caption("Verify capability. Don't trust the resume.")
st.divider()

# ── sidebar inputs ─────────────────────────────────────────
with st.sidebar:
    st.header("📋 Recruiter Inputs")

    jd_text = st.text_area(
        "Paste Job Description",
        height=200,
        placeholder="We are hiring a Backend Engineer..."
    )

    github_username = st.text_input(
        "Candidate GitHub Username",
        placeholder="e.g. torvalds"
    )

    resume_file = st.file_uploader(
        "Upload Resume PDF",
        type=["pdf"]
    )

    analyze_btn = st.button(
        "🔍 Analyze Candidate",
        type="primary",
        use_container_width=True
    )

    st.divider()
    st.caption("ScoutAI · Techkriti '26 × Eightfold AI")

# ── analyze button clicked ─────────────────────────────────
if analyze_btn:
    if not jd_text or not github_username:
        st.error("Please provide a job description and GitHub username.")
    else:
        # reset state for fresh analysis
        for k in ["stage", "jd", "github", "resume", "matcher",
                  "baseline", "assessment_obj", "current_question",
                  "assessment_results", "verified_match",
                  "bias_result", "report"]:
            st.session_state[k] = None
        st.session_state["assessment_results"] = []
        st.session_state["stage"] = "evidence"

        # ── parse JD ──────────────────────────────────────
        with st.spinner("Parsing job description..."):
            st.session_state["jd"] = parse_jd(jd_text, llm_fn=llm_fn)

        # ── extract GitHub signals ─────────────────────────
        with st.spinner(f"Fetching GitHub signals for {github_username}..."):
            st.session_state["github"] = extract_github_signals(
                github_username,
                token=os.environ.get("GITHUB_TOKEN")
            )

        # ── parse resume ───────────────────────────────────
        if resume_file:
            with st.spinner("Parsing resume..."):
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                ) as tmp:
                    tmp.write(resume_file.read())
                    tmp_path = tmp.name
                st.session_state["resume"] = parse_resume(
                    tmp_path, llm_fn=llm_fn
                )
                os.remove(tmp_path)

        # ── baseline scoring ───────────────────────────────
        with st.spinner("Scoring candidate against JD..."):
            matcher = Matcher()
            st.session_state["matcher"] = matcher
            candidate_skills = (
                st.session_state["github"].inferred_skills
            )
            if (st.session_state["resume"] and
                    st.session_state["resume"].skills):
                candidate_skills = list(set(
                    candidate_skills +
                    st.session_state["resume"].skills
                ))
            st.session_state["baseline"] = matcher.match(
                candidate_skills,
                st.session_state["jd"].required,
                st.session_state["jd"].weights
            )

        st.rerun()

# ── SECTION 1 — Evidence ───────────────────────────────────
if st.session_state["stage"] in [
    "evidence", "match", "assess", "report"
]:
    st.subheader("📊 Evidence Panel")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**GitHub Signals**")
        gh = st.session_state["github"]
        if gh:
            st.metric("Active Repos", gh.active_repos)
            st.metric("Code Quality", f"{gh.code_quality.score}/5")
            st.metric("Commit Quality",
                      f"{int(gh.commit_quality * 100)}%")
            st.markdown("**Languages:**")
            for lang, pct in gh.languages.items():
                st.progress(pct, text=f"{lang} {int(pct*100)}%")

    with col2:
        st.markdown("**Resume Claims**")
        resume = st.session_state["resume"]
        if resume:
            for skill, level in resume.experience.items():
                st.markdown(f"- **{skill}**: {level}")
        else:
            st.info("No resume uploaded")

    st.divider()

    # ── SECTION 2 — Baseline match ─────────────────────────
    st.subheader("🎯 Baseline Match")
    baseline = st.session_state["baseline"]
    jd = st.session_state["jd"]

    if baseline and jd:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Match Score", f"{baseline.score}%")
        with col2:
            st.metric("Skills Matched",
                      f"{len(baseline.matched)}/{len(jd.required)}")
        with col3:
            st.metric("Missing Skills", len(baseline.missing))

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**✅ Matched Skills**")
            for s in baseline.matched:
                st.success(s)
        with col2:
            st.markdown("**❌ Missing Skills**")
            for s in baseline.missing:
                st.error(s)

    st.divider()

    # ── start assessment button ────────────────────────────
    if st.session_state["stage"] == "evidence":
        if st.button("▶️ Start Live Assessment",
                     type="primary"):
            skills = pick_skills_to_verify(
                jd.required, jd.weights, top_n=2
            )
            if skills:
                a = AdaptiveAssessment(
                    skill=skills[0],
                    start_difficulty=3,
                    max_questions=3,
                    mode="local"
                )
                st.session_state["assessment_obj"] = a
                st.session_state["skills_to_test"] = skills
                st.session_state["skill_index"] = 0
                q = a.next_question()
                st.session_state["current_question"] = q
                st.session_state["stage"] = "assess"
                st.rerun()
            else:
                st.warning(
                    "No testable skills found. "
                    "Generating report without assessment."
                )
                st.session_state["stage"] = "report"
                st.rerun()

# ── SECTION 3 — Live Assessment ────────────────────────────
if st.session_state["stage"] == "assess":
    st.subheader("💻 Live Assessment")
    a = st.session_state["assessment_obj"]
    q = st.session_state["current_question"]

    if q:
        skill = q["skill"]
        difficulty = q["difficulty"]
        q_num = len(a.history) + 1

        st.markdown(
            f"**Testing: {skill} · "
            f"Question {q_num} · "
            f"Difficulty L{difficulty}/5**"
        )
        st.info(q["prompt"])

        code = st.text_area(
            "Your solution:",
            value=q["starter_code"],
            height=180,
            key=f"code_{q_num}"
        )

        if st.button("✅ Submit Answer", type="primary"):
            with st.spinner("Grading..."):
                passed = a.submit(q, code)

            if passed:
                st.success(
                    f"✅ Passed! Next difficulty: L{a.difficulty}"
                )
            else:
                st.error(
                    f"❌ Failed. Next difficulty: L{a.difficulty}"
                )

            next_q = a.next_question()

            if next_q is None:
                # current skill done
                result = a.finalize()
                st.session_state["assessment_results"].append(result)

                # check if more skills to test
                skill_index = st.session_state.get(
                    "skill_index", 0) + 1
                skills = st.session_state.get("skills_to_test", [])

                if skill_index < len(skills):
                    # start next skill
                    st.session_state["skill_index"] = skill_index
                    new_a = AdaptiveAssessment(
                        skill=skills[skill_index],
                        start_difficulty=3,
                        max_questions=3,
                        mode="local"
                    )
                    st.session_state["assessment_obj"] = new_a
                    next_q = new_a.next_question()
                    st.session_state["current_question"] = next_q
                else:
                    # all skills done — generate report
                    st.session_state["stage"] = "report"
                    st.session_state["current_question"] = None

            else:
                st.session_state["current_question"] = next_q

            st.rerun()

# ── SECTION 4 — Final Report ───────────────────────────────
if st.session_state["stage"] == "report":
    st.subheader("📋 Final Report")

    matcher = st.session_state["matcher"]
    jd = st.session_state["jd"]
    gh = st.session_state["github"]
    assessment_results = st.session_state["assessment_results"]
    primary = assessment_results[0] if assessment_results else None

    # get candidate skills
    candidate_skills = gh.inferred_skills if gh else []
    if (st.session_state["resume"] and
            st.session_state["resume"].skills):
        candidate_skills = list(set(
            candidate_skills +
            st.session_state["resume"].skills
        ))

    # verified match
    with st.spinner("Generating final report..."):
        verified = matcher.match(
            candidate_skills,
            jd.required,
            jd.weights,
            assessment=primary
        )

        # bias check
        profile = {
            "name": github_username,
            "skills": candidate_skills
        }
        if st.session_state["resume"]:
            profile["university"] = "unknown"
        bias_result = bias_check(
            profile, jd.required, jd.weights, matcher
        )

        # evidence panel
        evidence = {
            "languages": gh.languages if gh else {},
            "code_quality_score": (
                gh.code_quality.score if gh else 0
            ),
            "active_repos": gh.active_repos if gh else 0,
            "assessments": [
                asdict(r) for r in assessment_results
            ]
        }

        # build report
        report = build_report(
            match=verified,
            evidence=evidence,
            assessment=primary,
            bias_check=bias_result,
            llm_fn=llm_fn
        )
        st.session_state["report"] = report

    # ── display report ─────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Final Score", f"{report.score}%",
                  delta=f"{report.score - st.session_state['baseline'].score}% vs baseline")
    with col2:
        fair = report.bias_check.get("fair", False)
        st.metric("Bias Check",
                  "✅ Fair" if fair else "❌ Biased",
                  delta=f"Δ={report.bias_check.get('delta', 0)}")
    with col3:
        if primary:
            st.metric(
                f"{primary.skill} Verified",
                primary.verified_band.title(),
                delta="✅ Confirmed" if verified.claim_supported
                else "⚠️ Contradicted"
            )

    st.divider()

    # assessment results
    if assessment_results:
        st.markdown("**🎯 Assessment Results**")
        for r in assessment_results:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"**{r.skill}**")
            with col2:
                st.markdown(f"Band: `{r.verified_band}`")
            with col3:
                st.markdown(f"Confidence: {int(r.confidence*100)}%")

    st.divider()

    # claim contradiction check
    if st.session_state["resume"] and primary:
        st.markdown("**🔍 Claim Verification**")
        resume = st.session_state["resume"]
        claimed = resume.experience.get(
            primary.skill, "not mentioned"
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**Claimed:** {claimed}")
        with col2:
            st.markdown(
                f"**Verified:** {primary.verified_band}"
            )
        with col3:
            if verified.claim_supported:
                st.success("✅ Claim supported")
            else:
                st.error("❌ Claim contradicted")

    st.divider()

    # reasoning chain
    st.markdown("**💡 Reasoning Chain**")
    st.info(report.reasoning)

    # bias check detail
    st.markdown("**⚖️ Bias Audit**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("With Demographics",
                  report.bias_check.get("with_demographics", 0))
    with col2:
        st.metric("Without Demographics",
                  report.bias_check.get("without", 0))
    with col3:
        st.metric("Delta",
                  report.bias_check.get("delta", 0))

    if report.bias_check.get("fair"):
        st.success(
            "✅ Score unchanged when demographics removed "
            "— no demographic leakage detected."
        )
    else:
        st.error(
            "❌ Score changed when demographics removed "
            "— potential bias detected."
        )

    st.divider()

    # full evidence
    with st.expander("📂 Full Evidence Panel"):
        st.json(evidence)

    # restart button
    if st.button("🔄 Analyze Another Candidate"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()