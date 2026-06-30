import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()
import json
import re
from src.contracts import ResumeClaims


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extracts raw text from a PDF resume using PyMuPDF.
    Works on any PDF — scanned or digital.
    """
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        return f"Error reading PDF: {e}"


def _extract_with_llm(text: str, llm_fn) -> dict:
    """
    Sends the FULL resume text to the LLM and extracts a comprehensive
    skill list — including skills implied by project tech stacks,
    not just ones explicitly listed under a 'Skills' section.
    """
    prompt = f"""You are an expert technical recruiter analyzing a resume.

Read the ENTIRE resume below carefully — including the Skills section,
Education, AND every Project description.

Extract ALL technical skills the candidate has demonstrated, including:
- Explicitly listed skills (languages, frameworks, tools, cloud platforms)
- Skills IMPLIED by project tech stacks even if not in a "Skills" section
  (e.g. if a project says "built with LangGraph and Qdrant", include
  "LangGraph", "Qdrant", "Vector Databases", "RAG", "Agentic AI" as relevant)
- Modern/specific terms: Agentic AI, RAG, LLM Orchestration, Vector Search,
  Prompt Engineering, MLOps, CI/CD, Microservices, etc. if evidenced by
  the work described
- Soft skills only if explicitly stated

Be thorough — do not miss skills just because they weren't in a bullet list.
Infer reasonably from context, but do not invent things with zero evidence.

Return ONLY a valid JSON object, no explanation, no markdown:
{{
    "skills": ["Python", "PyTorch", "Agentic AI", "RAG", "LangGraph"],
    "experience": {{
        "Python": "expert",
        "PyTorch": "used",
        "Agentic AI": "demonstrated via project"
    }}
}}

Rules:
- skills: comprehensive list, include both explicit AND inferred skills
- experience: how candidate described/demonstrated each skill.
  Use exact resume wording where stated (e.g. "expert", "3 years").
  For inferred skills (from project tech stack), use "demonstrated via project".
- Return ONLY JSON, nothing else

FULL RESUME TEXT:
{text}
"""
    raw = llm_fn(prompt).strip()
    raw = re.sub(r"^```(json)?|```$", "", raw,
                 flags=re.MULTILINE).strip()
    return json.loads(raw)


def _extract_with_vocab(text: str) -> dict:
    """
    Fallback — matches against skill vocabulary when no LLM available.
    """
    SKILL_VOCAB = [
        "Python", "JavaScript", "TypeScript", "Java", "Go",
        "Rust", "C++", "C#", "Ruby", "Django", "Flask",
        "FastAPI", "React", "Vue", "Angular", "Node.js",
        "PostgreSQL", "MySQL", "MongoDB", "Redis", "SQL",
        "Docker", "Kubernetes", "AWS", "GCP", "Azure",
        "Machine Learning", "Deep Learning", "PyTorch",
        "TensorFlow", "NLP", "Pandas", "NumPy", "Git",
    ]
    EXPERIENCE_WORDS = [
        "expert", "advanced", "proficient", "experienced",
        "senior", "strong", "extensive", "years", "familiar",
        "beginner", "intermediate", "basic", "knowledge of",
    ]
    low = text.lower()
    skills = []
    experience = {}

    for skill in SKILL_VOCAB:
        if skill.lower() in low:
            skills.append(skill)
            idx = low.find(skill.lower())
            context = low[max(0, idx-50):idx+50]
            for word in EXPERIENCE_WORDS:
                if word in context:
                    experience[skill] = word
                    break
            if skill not in experience:
                experience[skill] = "mentioned"

    return {"skills": skills, "experience": experience}


def extract_project_feedback(text: str, llm_fn) -> list:
    """
    Extracts each project from the resume, summarizes it,
    and gives honest technical feedback — depth, relevance, complexity.
    Returns a list of {title, summary, tech_stack, feedback}.
    """
    if not llm_fn:
        return []

    prompt = f"""You are a technical reviewer analyzing a resume's projects.

Find EVERY project mentioned in this resume. For each one, extract:
- title: the project name
- summary: 1-2 sentences on what it does and how it works
- tech_stack: list of technologies/tools used
- feedback: an honest technical assessment, 2-3 sentences. Comment on
  depth, real-world relevance, and complexity. Is this a toy project or
  something genuinely substantial? Be specific and critical, not generic
  praise like "great project". If something seems exaggerated relative to
  the description, say so.

Return ONLY a valid JSON array, no explanation, no markdown:
[
    {{
        "title": "Project Name",
        "summary": "what it does",
        "tech_stack": ["Python", "FastAPI"],
        "feedback": "honest technical assessment"
    }}
]

FULL RESUME TEXT:
{text}
"""
    try:
        raw = llm_fn(prompt).strip()
        raw = re.sub(r"^```(json)?|```$", "", raw,
                     flags=re.MULTILINE).strip()
        return json.loads(raw)
    except Exception:
        return []


def extract_github_username(raw_text: str) -> str | None:
    """
    Extracts GitHub username from resume text.
    STRICT: only matches when there's clear evidence this is a GitHub
    link/icon, not just any capitalized word. No loose fallback —
    a missed username is far better than a wrong one.
    """
    patterns = [
        r"github\.com/([a-zA-Z0-9_-]+)",
        r"github:\s*([a-zA-Z0-9_-]+)",
        r"github\.com\\([a-zA-Z0-9_-]+)",
        # broken icon glyph (common LaTeX resume icons) directly
        # followed by a username-like token, but require it NOT be
        # a common word and require digits OR be clearly a handle
        r"[§ï](?:\s*)([A-Za-z][a-zA-Z]{2,20}[0-9]{1,4})\b",
    ]

    BLOCKLIST = {
        "features", "pricing", "login", "signup", "about",
        "contact", "join", "api", "json", "models", "code",
        "platform", "search", "engine", "mode", "panel",
    }

    for pattern in patterns:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            username = match.group(1)
            if username.lower() not in BLOCKLIST:
                return username

    return None
def parse_resume(pdf_path: str, llm_fn=None) -> ResumeClaims:
    """
    Main entry point. Takes a PDF path and returns ResumeClaims.
    Uses LLM (full resume, comprehensive inference) if available,
    falls back to vocab matching otherwise.
    Also runs project feedback extraction if LLM available.
    """
    raw_text = extract_text_from_pdf(pdf_path)

    if raw_text.startswith("Error"):
        return ResumeClaims(
            skills=[],
            experience={},
            raw_text=raw_text,
            projects=[]
        )

    if llm_fn is not None:
        try:
            extracted = _extract_with_llm(raw_text, llm_fn)
        except Exception:
            extracted = _extract_with_vocab(raw_text)
    else:
        extracted = _extract_with_vocab(raw_text)

    projects = extract_project_feedback(raw_text, llm_fn)

    return ResumeClaims(
        skills=extracted.get("skills", []),
        experience=extracted.get("experience", {}),
        raw_text=raw_text,
        projects=projects
    )


if __name__ == "__main__":
    import json
    from src.contracts import asdict
    from groq import Groq

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    def llm_fn(prompt):
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return response.choices[0].message.content

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        result = parse_resume(pdf_path, llm_fn=llm_fn)
        print(json.dumps(asdict(result), indent=2))

        username = extract_github_username(result.raw_text)
        print(f"\nExtracted GitHub username: {username}")
    else:
        print("No PDF provided. Testing with sample text...")
        sample = """
        John Doe — Software Engineer
        GitHub: github.com/johndoe
        Skills: Expert Python, 3 years Django, familiar with Docker
        Experience with PostgreSQL and REST APIs.
        Machine Learning enthusiast. Basic knowledge of AWS.

        Project: ChatBot Assistant
        Built a RAG-based chatbot using LangChain and Pinecone for
        vector search, deployed via FastAPI on AWS.
        """
        extracted = _extract_with_llm(sample, llm_fn)
        print(json.dumps(extracted, indent=2))

        projects = extract_project_feedback(sample, llm_fn)
        print(json.dumps(projects, indent=2))

        username = extract_github_username(sample)
        print(f"\nExtracted GitHub username: {username}")