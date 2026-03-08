"""Convert resume .md files to PDF using config/resume-pdf-template.html."""
from __future__ import annotations

from pathlib import Path

from bs4 import BeautifulSoup

from .config import CONFIG_DIR, RESUMES_DIR, RESUME_PDF_TEMPLATE_PATH


def _strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```markdown"):
        text = text[len("```markdown"):].strip()
    elif text.startswith("```"):
        text = text.split("\n", 1)[-1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3].strip()
    return text


def _md_to_html(md: str) -> str:
    import markdown
    try:
        html = markdown.markdown(md, extensions=["extra"])
    except Exception:
        html = markdown.markdown(md)
    return html


def _contact_to_oneline(soup: BeautifulSoup) -> None:
    for h2 in soup.find_all("h2", limit=1):
        if "contact" not in (h2.get_text() or "").lower():
            break
        next_el = h2.find_next_sibling()
        if next_el and next_el.name == "ul":
            items = [li.get_text(separator=" ", strip=True) for li in next_el.find_all("li") if li.get_text(strip=True)]
            if items:
                new_div = soup.new_tag("div", attrs={"class": "contact-block"})
                new_ul = soup.new_tag("ul")
                for item in items:
                    li = soup.new_tag("li")
                    li.string = item
                    new_ul.append(li)
                new_div.append(new_ul)
                next_el.replace_with(new_div)
        break


def _wrap_content_in_template(html_body: str, template_path: Path | None = None) -> str:
    path = template_path or RESUME_PDF_TEMPLATE_PATH
    if not path.exists():
        return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
        body {{ font-family: Calibri, Arial, sans-serif; font-size: 11pt; margin: 0.6in; }}
        h1 {{ text-align: center; font-size: 22pt; text-transform: uppercase; }}
        h2 {{ font-size: 12pt; font-weight: bold; text-decoration: underline; margin-top: 14px; }}
        </style></head><body><div class="resume-content">{html_body}</div></body></html>"""
    template = path.read_text(encoding="utf-8")
    return template.replace("{{CONTENT}}", html_body)


def md_file_to_pdf(
    md_path: Path,
    pdf_path: Path | None = None,
    template_path: Path | None = None,
) -> Path:
    md_path = Path(md_path)
    if not md_path.exists():
        raise FileNotFoundError(md_path)
    pdf_path = Path(pdf_path) if pdf_path else md_path.with_suffix(".pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    raw = md_path.read_text(encoding="utf-8")
    md = _strip_markdown_fence(raw)
    html_body = _md_to_html(md)
    soup = BeautifulSoup(html_body, "html.parser")
    _contact_to_oneline(soup)
    html_body = str(soup)
    full_html = _wrap_content_in_template(html_body, template_path)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_content(full_html, wait_until="networkidle")
            page.pdf(
                path=str(pdf_path),
                format="Letter",
                margin={"top": "0.6in", "right": "0.6in", "bottom": "0.6in", "left": "0.6in"},
                print_background=True,
            )
        finally:
            browser.close()
    return pdf_path


def convert_resume_mds_to_pdfs(
    resumes_dir: Path | None = None,
    template_path: Path | None = None,
    skip_existing: bool = False,
) -> list[Path]:
    dir_path = Path(resumes_dir or RESUMES_DIR)
    if not dir_path.exists():
        return []
    template_path = template_path or RESUME_PDF_TEMPLATE_PATH
    created = []
    for md_file in sorted(dir_path.glob("*.md")):
        if md_file.name.lower() == "job_links.md":
            continue
        pdf_file = md_file.with_suffix(".pdf")
        if skip_existing and pdf_file.exists():
            continue
        try:
            md_file_to_pdf(md_file, pdf_path=pdf_file, template_path=template_path)
            created.append(pdf_file)
        except Exception as e:
            import sys
            print(f"Warning: could not convert {md_file.name} to PDF: {e}", file=sys.stderr)
    return created
