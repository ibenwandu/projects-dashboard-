"""Generate a professional cover letter for a job using the job description and your resume.

Uses the same AI provider as the workflow (Gemini or OpenAI via .env).

Usage:
  python cover_letter_one.py <job-file.md> <resume-file.md>
  python cover_letter_one.py output/18_BUSINESS_MANAGEMENT_ANALYST_City_of_Toronto.md processed/BUSINESS_MANAGEMENT_ANALYST_City_of_Toronto.md

Options:
  --output path.md   Write cover letter to this path (default: next to resume, name_cover_letter.md)
  --pdf              Also convert the cover letter to PDF (uses config/cover-letter-template.html)

Run from the Linkedin-jobs project root.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```markdown"):
        text = text[len("```markdown") :].strip()
    elif text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def _read_path(p: Path) -> str:
    if not p.exists():
        raise FileNotFoundError(p)
    return p.read_text(encoding="utf-8")


def generate_cover_letter(job_content: str, resume_content: str) -> str:
    from datetime import date
    from src.ai_client import generate

    today = date.today().strftime("%B %d, %Y")  # e.g. March 4, 2026

    prompt = f"""Write a professional, one-page formal cover letter for the candidate applying to this role.

STRUCTURE (include all of these in order, in Markdown):

1. **Sender block (top right):** The candidate's full name and contact (email, phone, city/region) on 2–4 lines. Use the exact name and contact from the resume. This block should appear at the upper right of the letter.

2. **Date (top right, directly below the sender block):** Use this exact date: {today}. Keep it right-aligned, below the contact block.

3. **Recipient block (left-aligned, after the date):** On 2–4 lines: addressee (e.g. "Hiring Manager" or "Hiring Committee"), department or "Human Resources" if applicable, company name, and company address if known from the job posting (city, province/state). If address is unknown, use at least "Company Name" and city.

4. **Salutation:** "Dear Hiring Manager," or "Dear Hiring Committee," (or specific name if mentioned in the job posting).

5. **Body (2–3 paragraphs):** Open with a strong hook stating the role and company and the candidate's interest. In the next paragraph(s), connect the candidate's experience and skills to the job's requirements; reference specific qualifications from the job description. Keep a formal, confident tone. Roughly 250–400 words total. End with a brief closing paragraph expressing interest and inviting an interview. Use paragraphs and optional **bold** for key terms. Do not repeat the resume verbatim—synthesize and emphasize fit.

6. **Closing:** "Sincerely," or "Yours sincerely," on its own line.

7. **Signature block:** Leave 2–3 blank lines (for handwritten signature), then the candidate's full name on one line and their professional title (e.g. "Senior Business Analyst") on the next. Use the name and title from the resume.

Output ONLY the complete letter in Markdown. No preamble, no explanation, no placeholders—use real details from the resume and job posting."""

    full_prompt = f"""JOB POSTING (role, company, description):
---
{job_content}
---

CANDIDATE'S RESUME (use for name, contact, title, and experience):
---
{resume_content}
---

{prompt}"""
    return generate(full_prompt)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    output_path = None
    do_pdf = "--pdf" in sys.argv[1:]

    for i, a in enumerate(sys.argv[1:]):
        if a == "--output" and i + 2 < len(sys.argv):
            output_path = sys.argv[i + 2]
            break

    if len(args) < 2:
        print(
            "Usage: python cover_letter_one.py <job-file.md> <resume-file.md> [--output path.md] [--pdf]",
            file=sys.stderr,
        )
        print(
            "Example: python cover_letter_one.py output/18_BUSINESS_MANAGEMENT_ANALYST_City_of_Toronto.md processed/BUSINESS_MANAGEMENT_ANALYST_City_of_Toronto.md",
            file=sys.stderr,
        )
        sys.exit(1)

    job_file = Path(args[0])
    resume_file = Path(args[1])
    if not job_file.is_absolute():
        job_file = PROJECT_ROOT / job_file
    if not resume_file.is_absolute():
        resume_file = PROJECT_ROOT / resume_file

    for p, name in [(job_file, "Job file"), (resume_file, "Resume file")]:
        if not p.exists():
            print(f"Error: {name} not found: {p}", file=sys.stderr)
            sys.exit(1)
        if p.suffix.lower() != ".md":
            print(f"Error: {name} should be a .md file: {p}", file=sys.stderr)
            sys.exit(1)

    job_content = _read_path(job_file)
    resume_content = _strip_markdown_fence(_read_path(resume_file))

    print("Generating cover letter...")
    content = generate_cover_letter(job_content, resume_content)

    if not content or content.startswith("[Gemini error") or content.startswith("[OpenAI error"):
        print(f"Error: AI returned: {content[:200]}", file=sys.stderr)
        sys.exit(1)

    if output_path:
        out_path = Path(output_path)
    else:
        out_path = resume_file.parent / f"{resume_file.stem}_cover_letter.md"
    if not out_path.is_absolute():
        out_path = PROJECT_ROOT / out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"Created: {out_path}")

    if do_pdf:
        from src.md_to_pdf import md_file_to_pdf
        from src.config import COVER_LETTER_TEMPLATE_PATH

        pdf_path = out_path.with_suffix(".pdf")
        template_path = COVER_LETTER_TEMPLATE_PATH
        if not template_path.exists():
            from src.config import RESUME_PDF_TEMPLATE_PATH
            template_path = RESUME_PDF_TEMPLATE_PATH
        try:
            md_file_to_pdf(out_path, pdf_path=pdf_path, template_path=template_path)
            print(f"Created: {pdf_path}")
        except Exception as e:
            print(f"Warning: could not create PDF: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
