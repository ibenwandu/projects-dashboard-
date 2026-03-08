"""Convert a single resume or cover letter .md file to PDF.

- Resume: uses config/resume-pdf-template.html (centered name, underlined sections).
- Cover letter: uses config/cover-letter-template.html (sender/date top right, letter layout).

Usage:
  python md_to_pdf_one.py <path-to-resume.md>
  python md_to_pdf_one.py processed/Business_Analyst_Galent.md
  python md_to_pdf_one.py processed/BUSINESS_MANAGEMENT_ANALYST_City_of_Toronto_cover_letter.md --cover-letter

If the filename contains "cover_letter", the cover letter template is used automatically
unless you pass --resume. Use --cover-letter to force cover letter layout for any file.

Output: PDF is written next to the .md file (same name, .pdf) unless --output is set.

Run from the Linkedin-jobs project root.
"""
from pathlib import Path
import sys

# Project root = parent of script
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.md_to_pdf import md_file_to_pdf
from src.config import RESUME_PDF_TEMPLATE_PATH, COVER_LETTER_TEMPLATE_PATH


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out_arg = None
    force_cover_letter = "--cover-letter" in sys.argv[1:]
    force_resume = "--resume" in sys.argv[1:]
    for i, a in enumerate(sys.argv[1:]):
        if a == "--output" and i + 2 < len(sys.argv):
            out_arg = sys.argv[i + 2]
            break

    if not args:
        print("Usage: python md_to_pdf_one.py <path-to-file.md> [--cover-letter | --resume] [--output path/to/output.pdf]", file=sys.stderr)
        sys.exit(1)

    md_path = Path(args[0])
    if not md_path.is_absolute():
        md_path = PROJECT_ROOT / md_path
    if not md_path.exists():
        print(f"Error: file not found: {md_path}", file=sys.stderr)
        sys.exit(1)
    if md_path.suffix.lower() != ".md":
        print("Error: expected a .md file", file=sys.stderr)
        sys.exit(1)

    # Choose template: explicit flag wins; else auto-detect by filename
    if force_cover_letter:
        template_path = COVER_LETTER_TEMPLATE_PATH
    elif force_resume:
        template_path = RESUME_PDF_TEMPLATE_PATH
    else:
        is_cover_letter = "cover_letter" in md_path.stem.lower()
        template_path = COVER_LETTER_TEMPLATE_PATH if is_cover_letter else RESUME_PDF_TEMPLATE_PATH
    if template_path == COVER_LETTER_TEMPLATE_PATH and not template_path.exists():
        template_path = RESUME_PDF_TEMPLATE_PATH

    default_pdf_dir = md_path.parent
    pdf_path = Path(out_arg) if out_arg else None
    if pdf_path and not pdf_path.is_absolute():
        pdf_path = PROJECT_ROOT / pdf_path
    if pdf_path is None:
        pdf_path = default_pdf_dir / f"{md_path.stem}.pdf"

    try:
        result = md_file_to_pdf(
            md_path,
            pdf_path=pdf_path,
            template_path=template_path,
        )
        print(f"Created: {result}")
    except (PermissionError, OSError) as e:
        if getattr(e, "errno", None) == 13 or "Permission denied" in str(e):
            # Try alternate filename in case the original PDF is open
            alt_path = default_pdf_dir / f"{md_path.stem}_1.pdf"
            try:
                result = md_file_to_pdf(
                    md_path,
                    pdf_path=alt_path,
                    template_path=template_path,
                )
                print(f"Created: {result}")
                print("(Original path was locked—e.g. PDF open in a viewer. Close it to overwrite next time.)", file=sys.stderr)
            except Exception:
                print(f"Error: {e}", file=sys.stderr)
                print("Close the PDF if it's open in a viewer, or use --output to write to a different path.", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
