# Unified Talent Intelligence


> **"Verify capability — don't trust the resume."**

A full-stack AI hiring system that moves beyond resume parsing to **verify real human capability** from evidence a candidate cannot fake, and explains every hiring decision in an auditable, bias-resistant way.

---

## The Problem

The modern hiring pipeline is broken by two simultaneous forces:

- **The AI-spam flood** — Generative AI can produce a perfectly optimised resume in seconds. A resume is now a low-trust document, not a credential.
- **Skill half-life collapse** — Technical skills go obsolete faster than hiring cycles. Matching static credentials to static job descriptions no longer predicts success.

Organisations need systems that **verify actual human capability**, predict learning trajectories, and surface hidden internal talent — not just parse PDFs.

---

## Our Solution

One unified talent-intelligence engine spanning all four hackathon impact areas:

| Area | What it does | Status |
|---|---|---|
| 01 — Signal Extraction & Verification | GitHub signals + live adaptive coding test | ✅ Core spine |
| 04 — The Glass-Box Recruiter | Reasoning chain + bias audit on every decision | ✅ Wraps all modes |
| 02 — Potential & Learning Trajectory | Skill-adjacency learnability for missing skills | 🔶 Stretch |
| 03 — Internal Talent Liquidity | Same engine run over an employee CSV | 🔶 Stretch |

**The key insight:** Areas 01, 02, and 03 are the same matching engine pointed at different inputs. Area 04 is a layer that wraps all of them. So instead of four separate systems, we built one generic engine and went deep where it matters.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  SHARED BACKBONE                    │
│           skill extraction + embeddings             │
└────────────┬────────────────────┬───────────────────┘
             │                    │
    ┌────────▼────────┐  ┌────────▼────────┐
    │  GitHub signal  │  │  Adaptive live  │
    │   extraction    │  │   assessment    │
    │   (Person A)    │  │   (Person B)    │
    └────────┬────────┘  └────────┬────────┘
             │                    │
    ┌────────▼────────┐           │
    │   JD parser     │           │
    │   (Person A)    │           │
    └────────┬────────┘           │
             └──────────┬─────────┘
                        │
              ┌─────────▼─────────┐
              │   Scoring engine  │
              │  MiniLM + cosine  │
              │   (Person A)      │
              └─────────┬─────────┘
                        │
              ┌─────────▼─────────┐
              │  Glass-box layer  │
              │ reasoning + bias  │
              │   (Person B)      │
              └─────────┬─────────┘
                        │
              ┌─────────▼─────────┐
              │   Final Report    │
              │ score · evidence  │
              │ reasoning · fair  │
              └───────────────────┘
```

---

## How It Works — The 7-Step Demo

| Step | What happens | What the judge sees |
|---|---|---|
| 1 | **Input** | Paste a job description + a GitHub handle, click run |
| 2 | **Extract** | GitHub profile pulls real language distribution and repo signals | Required skills as tags; real GitHub language breakdown |
| 3 | **Baseline match** | Embedding cosine similarity scores candidate vs JD | Match score, matched skills in green, missing in gray |
| 4 | **Live assessment** | 5 adaptive questions, difficulty steps up/down per answer | Questions load, Judge0 grades, verified band prints |
| 5 | **Reconcile & explain** | Verified band compared against resume claim | The killer moment: "Expert claimed, intermediate verified" |
| 6 | **Bias check** | Re-run scoring with demographics stripped | Both scores side by side, delta shown, fairness confirmed |
| 7 | **Final report** | Everything in one auditable card | Score, evidence, reasoning chain, bias-audited badge |

---

## The Differentiator

Most teams at this hackathon will parse a GitHub profile and run cosine similarity. The brief literally describes that as the baseline winning entry.

**Our differentiator is the live adaptive assessment** — a coding test that adjusts its own difficulty in real time based on how the candidate is performing, verified through a sandboxed code-execution engine (Judge0). This gives us:

- **Active** verification, not just passive signal scraping
- A visible, interactive demo moment judges can watch in real time
- A reconciliation that can **contradict** a resume claim with evidence

> Resume says: *"Expert Python"*
> Live assessment says: *"Intermediate — solved L3, failed L4"*
> System says: *"Claim not fully supported by live evidence."*

That single moment proves the thesis better than any slide.

---

## Tech Stack

| Purpose | Tool | Why |
|---|---|---|
| Embeddings | `sentence-transformers` (all-MiniLM-L6-v2) | Fast, local, free, good enough |
| Skill extraction | LLM prompt → JSON + spaCy fallback | Structured output with offline fallback |
| Vector similarity | `FAISS` + cosine | Millisecond matching, no cloud needed |
| GitHub API | `PyGithub` | Real language + repo + commit data |
| Code sandbox | `Judge0` (RapidAPI free tier) | Sandboxed execution of untrusted code |
| Static analysis | `radon` + `pylint` | Cyclomatic complexity + maintainability |
| UI | `Streamlit` | Python → web app in minutes |
| LLM API | Groq / OpenAI | Skill extraction + LLM-as-judge code review |

---

## Project Structure

```
talent-intelligence/
│
├── contracts.py              # Shared data shapes (both people build against this)
│
├── person_a/                 # Evidence & scoring (Person A)
│   ├── github_extractor.py   # GitHub signals + 4-tier code quality
│   ├── jd_parser.py          # Job description → required skills + weights
│   ├── scoring.py            # Generic semantic matcher (core engine)
│   ├── bias_check.py         # Strip demographics, re-run, show delta
│   ├── mock_data.py          # Mocks of Person B output until sync
│   └── pipeline_a.py         # End-to-end runner for Person A's half
│
├── person_b/                 # Verification & trust (Person B)
│   ├── question_bank.py      # Questions tagged by skill + difficulty 1–5
│   ├── judge0.py             # Code execution (Judge0 + local dev fallback)
│   ├── assessment.py         # Adaptive loop — your differentiator
│   ├── glassbox.py           # Reasoning chain + final report assembly
│   ├── adjacency.py          # Area 02 skill adjacency (stretch)
│   ├── mock_data_b.py        # Mocks of Person A output until sync
│   └── pipeline_b.py         # End-to-end runner for Person B's half
│
├── app.py                    # Streamlit UI — built last, wires both halves
├── requirements.txt          # All dependencies
├── .gitignore
└── README.md
```

---

## Work Split

### Person A — Evidence & Scoring

Owns the evidence pipeline: what a candidate has actually done, matched against what the role needs.

| File | Responsibility |
|---|---|
| `github_extractor.py` | Pull real signals from GitHub — languages, repo hygiene, commit quality, LLM-as-judge code review |
| `jd_parser.py` | Parse a pasted job description into a weighted required-skill list |
| `scoring.py` | **The heart** — generic semantic matcher powering all three areas |
| `bias_check.py` | Score once with demographics, once without, display the delta |

### Person B — Verification & Trust

Owns the live verification and the explanation layer: what the candidate can actually do right now, explained without a black box.

| File | Responsibility |
|---|---|
| `question_bank.py` | Questions tagged by skill and difficulty level 1–5 |
| `judge0.py` | Sandboxed code execution + local dev runner |
| `assessment.py` | **The differentiator** — adaptive loop that verifies a claimed skill live |
| `glassbox.py` | Reasoning chain + final auditable report |

### The boundary between them

One object passes each way across the seam:

```
Person A → Person B:   MatchResult(score, matched, missing, claim_supported)
Person B → Person A:   AssessmentResult(skill, verified_band, trajectory, confidence)
```

Everything else is built independently against mocks until the sync points.

---

## Data Contracts

The shapes that pass between the two halves. Both people agree on these first and never change them independently.

```python
# Person B produces this → Person A's scorer adjusts the score
AssessmentResult(
    skill="Python",
    verified_band="intermediate",   # "beginner" | "intermediate" | "advanced"
    trajectory=[3, 4, 4, 5, 4],    # difficulty of each question asked
    confidence=0.82                 # pass rate across the session
)

# Person A produces this → Person B's glass-box explains it
MatchResult(
    score=68,
    matched=["Python", "REST APIs"],
    missing=["Docker", "PostgreSQL"],
    claim_supported=False           # True/False when assessment was run
)
```

---

## Git Workflow

### Branch strategy

```
main                        ← always working, integrated
├── feat/evidence-scoring   ← Person A's branch
└── feat/assessment-glassbox ← Person B's branch
```

`main` is never broken. Both people live on their feature branch and merge to `main` only at the two sync points.

### Setup (one time)

```bash
# whoever creates the repo:
git clone <repo-url>
cd talent-intelligence
git checkout main

# Person B starts their branch:
git checkout -b feat/assessment-glassbox
git push -u origin feat/assessment-glassbox
```

### Daily workflow

```bash
git add <files>
git commit -m "feat: describe what you did"
git push
```

### Sync points (critical — do not skip)

**Hour 9 sync:**
```bash
git checkout main && git pull
git checkout feat/assessment-glassbox
git merge main
# run pipeline_b.py — confirm it still works
# open Pull Request on GitHub → review → merge
```

**Hour 15 sync:**
```bash
# same process — after this the spine is LOCKED
# swap mock_data for real objects from the other person
```

### The one rule

`contracts.py` lives on `main`. If a data shape must change, **both people change it together on `main` and both immediately `git pull`.** Never edit `contracts.py` on a feature branch independently — it's the only file that can cause a painful conflict.

---

## Setup

### 1. Clone and create virtual environment

```bash
git clone https://github.com/YOURTEAM/talent-intelligence.git
cd talent-intelligence
python3 -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set environment variables

```bash
# GitHub token (raises rate limit from 60 to 5000 requests/hour)
export GITHUB_TOKEN="ghp_your_token_here"

# Judge0 — get a free key at rapidapi.com → search "Judge0 CE"
export JUDGE0_URL="https://judge0-ce.p.rapidapi.com"
export JUDGE0_KEY="your_rapidapi_key"
export JUDGE0_HOST="judge0-ce.p.rapidapi.com"

# LLM API — Groq is free and fast
export GROQ_API_KEY="your_groq_key"
```

### 4. Verify setup

```bash
# Person A's half:
python3 person_a/pipeline_a.py

# Person B's half:
python3 person_b/pipeline_b.py
```

Both should run end to end with no errors. They use offline mocks so no API keys are needed for development.

### 5. Run the demo app

```bash
streamlit run app.py
```

---

## The 20-Hour Build Timeline

| Hours | Focus | Outcome |
|---|---|---|
| 0–0.5 | Agree on `contracts.py` together | Shared shapes locked |
| 1–4 | A: GitHub extractor, JD parser · B: question bank | Data pipelines working |
| 5–9 | A: scoring engine · B: Judge0 + assessment loop | **SYNC 1 at hour 9** |
| 10–14 | A: code quality signals · B: adaptive loop complete | Live assessment working |
| 15–17 | A: bias check · B: glass-box reasoning | **SYNC 2 at hour 15** |
| 16–19 | Stretch: adjacency + internal mobility (if ahead) | Extra areas riding the engine |
| 18–20 | Streamlit UI · demo rehearsal · writeup · pitch deck | Submission-ready |

---

## Rubric Alignment

| Criterion | Weight | How we earn it |
|---|---|---|
| Problem Depth & Relevance | 25% | Attacks AI-spam at the root: verified signals from real artifacts, not parsed PDFs |
| Technical Execution | 25% | Working pipeline: GitHub extraction, semantic scoring, live sandboxed code execution |
| Explainability & Fairness | 20% | Full reasoning chain + demographic-blind bias check with a visible delta |
| Innovation | 15% | Live adaptive assessment — active verification no other team will have |
| Demo & Communication | 15% | Judge pastes their own JD live; claim-vs-evidence contradiction is the unforgettable moment |

---

## Known Limitations

- GitHub signals only reflect **public** work — an empty profile is not evidence of incompetence
- The adaptive loop is a simplified difficulty-stepping rule, not full Item Response Theory
- LLM-as-judge code reviews are subjective; averaged across multiple files to reduce variance
- Skill adjacency learnability estimates are heuristic, not empirically validated
- The bias check confirms no demographic leakage in our pipeline; it does not audit the question bank itself for content bias

---

## Resources

| Resource | What it's for |
|---|---|
| [Resume Dataset — Kaggle](https://kaggle.com) | ~2,400 categorised resumes for testing |
| [LinkedIn Job Postings — Kaggle](https://kaggle.com) | Real JDs with required skills |
| [Lightcast Skills Taxonomy](https://skills.lightcast.io) | 32,000+ skills with adjacency relationships |
| [Judge0 on RapidAPI](https://rapidapi.com/judge0-official/api/judge0-ce) | Free sandboxed code execution |
| [Groq](https://groq.com) | Free-tier LLM inference (fast) |
| [sentence-transformers](https://sbert.net) | all-MiniLM-L6-v2 embeddings |

---

## Deliverables (hackathon submission)

- [ ] Working prototype — runnable, demonstrable live
- [ ] 1-page technical writeup — area chosen, architecture, tools, known limitations
- [ ] 5–7 minute pitch deck — problem, solution walkthrough, live demo, next steps

---

*Built for the Techkriti '26 × Eightfold AI Hackathon. All candidate data used in development is synthetic. The system is designed for accuracy, explainability, and demonstrable fairness across one unified engine.*