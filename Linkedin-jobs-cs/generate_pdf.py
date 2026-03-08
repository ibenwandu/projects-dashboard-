"""Generate PDF from a single .md file (resume or cover letter). PDF-only, no other steps.

Usage:
  python generate_pdf.py <path-to-file.md>

Examples:
  python generate_pdf.py processed/Analyst__Data_Analytics___Modelling_Connor__Clark___Lunn_Infrastructure.md
  python generate_pdf.py processed/BUSINESS_MANAGEMENT_ANALYST_City_of_Toronto_cover_letter.md

- Filenames containing "cover_letter" use the cover letter template (top-right block, letter layout).
- All other .md files use the resume template.
- PDF is written next to the .md (same name, .pdf). If that file is locked (e.g. open), writes *_1.pdf.

Run from the Linkedin-jobs project root.
"""
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Delegate to existing converter
from md_to_pdf_one import main

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1].startswith("--"):
        print("Usage: python generate_pdf.py <path-to-file.md>", file=sys.stderr)
        print("Example: python generate_pdf.py processed/MyResume_cover_letter.md", file=sys.stderr)
        sys.exit(1)
    main()
