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
    Sends resume text to LLM and extracts structured claims.
    Returns skills list and experience dict.
    """
    prompt = f"""You are a resume parser. Extract skills and experience from this resume.

Return ONLY a valid JSON object, no explanation, no markdown:
{{
    "skills": ["Python", "Django", "Docker"],
    "experience": {{
        "Python": "expert",
        "Django": "3 years",
        "Docker": "familiar"
    }}
}}

Rules:
- skills: list of ALL technical skills mentioned
- experience: how candidate described each skill
- Use exact words from resume for experience values
- If no experience level mentioned, use "mentioned"
- Return ONLY JSON, nothing else

RESUME TEXT:
{text[:3000]}
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
            # find experience level near skill mention
            idx = low.find(skill.lower())
            context = low[max(0, idx-50):idx+50]
            for word in EXPERIENCE_WORDS:
                if word in context:
                    experience[skill] = word
                    break
            if skill not in experience:
                experience[skill] = "mentioned"

    return {"skills": skills, "experience": experience}

def parse_resume(pdf_path: str, llm_fn=None) -> ResumeClaims:
    """
    Main entry point. Takes a PDF path and returns ResumeClaims.
    Uses LLM if available, falls back to vocab matching.
    """
    # extract raw text from PDF
    raw_text = extract_text_from_pdf(pdf_path)

    if raw_text.startswith("Error"):
        return ResumeClaims(
            skills=[],
            experience={},
            raw_text=raw_text
        )

    # extract structured claims
    if llm_fn is not None:
        try:
            extracted = _extract_with_llm(raw_text, llm_fn)
        except Exception:
            extracted = _extract_with_vocab(raw_text)
    else:
        extracted = _extract_with_vocab(raw_text)

    return ResumeClaims(
        skills=extracted.get("skills", []),
        experience=extracted.get("experience", {}),
        raw_text=raw_text
    )


if __name__ == "__main__":
    import sys
    import json
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

    # test with a PDF path passed as argument
    # python src/resume_parser.py path/to/resume.pdf
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        result = parse_resume(pdf_path, llm_fn=llm_fn)
        print(json.dumps(asdict(result), indent=2))
    else:
        # test with fake text if no PDF provided
        print("No PDF provided. Testing with sample text...")
        sample = """
        John Doe — Software Engineer
        Skills: Expert Python, 3 years Django, familiar with Docker
        Experience with PostgreSQL and REST APIs.
        Machine Learning enthusiast. Basic knowledge of AWS.
        """
        extracted = _extract_with_llm(sample, llm_fn)
        print(json.dumps(extracted, indent=2))