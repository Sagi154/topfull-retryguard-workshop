"""Convert mentor-update/MENTOR-UPDATE.md to a single PDF with charts inlined.

The Mermaid block is replaced with infra_diagram.png (ELK layout of the same
graph). A landscape CSS page gives that wide diagram enough room on A4.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import markdown
except ImportError:
    sys.exit("Missing 'markdown'. Create scripts/.venv and pip install -r scripts/requirements-pdf.txt")

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MD = REPO_ROOT / "Guides and Info" / "mentor-update" / "MENTOR-UPDATE.md"
DEFAULT_PDF = (
    REPO_ROOT
    / "Guides and Info"
    / "mentor-update"
    / "RetryGuard-on-TopFull-Mentor-Update.pdf"
)

MERMAID_FENCE = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
IMG_SRC = re.compile(r'<img\s([^>]*?)src="([^"]+)"', re.IGNORECASE)
INFRA_PLACEHOLDER = "INFRA_DIAGRAM_PLACEHOLDER"
INFRA_DIAGRAM_PNG = REPO_ROOT / "Guides and Info" / "mentor-update" / "infra_diagram.png"

CSS = """
@page { size: A4 portrait; margin: 14mm 12mm; }
@page landscape-diagram { size: A4 landscape; margin: 10mm 12mm; }
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.45;
  color: #1a1a1a;
}
h1 { font-size: 20pt; border-bottom: 2px solid #444; padding-bottom: 6px; margin: 0 0 12px; }
h2 { font-size: 15pt; border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 22px; page-break-after: avoid; }
h3 { font-size: 12.5pt; margin-top: 16px; color: #222; page-break-after: avoid; }
p, li { font-size: 11pt; }
ul, ol { padding-left: 22px; margin: 6px 0 14px; }
li { margin: 5px 0; }
code {
  font-family: "Cascadia Code", Consolas, monospace;
  background: #f2f2f2;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 9.5pt;
}
pre {
  background: #f6f8fa;
  border: 1px solid #ddd;
  border-radius: 5px;
  padding: 10px 12px;
  white-space: pre-wrap;
  word-wrap: break-word;
}
blockquote {
  border-left: 4px solid #b0b0b0;
  margin: 10px 0;
  padding: 4px 14px;
  color: #555;
  background: #fafafa;
}
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 8.5pt; }
th, td { border: 1px solid #bbb; padding: 5px 7px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
th { background: #eee; }
img {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 8px 0 14px;
  page-break-inside: avoid;
  break-inside: avoid;
}
hr { border: none; border-top: 1px solid #ccc; margin: 18px 0; }
.mermaid-figure {
  page: landscape-diagram;
  break-before: page;
  break-after: page;
  page-break-before: always;
  page-break-after: always;
  margin: 0;
  text-align: center;
}
.mermaid-figure img {
  width: 100%;
  height: auto;
  margin: 0;
  page-break-inside: auto;
  break-inside: auto;
}
"""


def find_browser() -> Path:
    candidates = [
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "Google"
        / "Chrome"
        / "Application"
        / "chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "Microsoft"
        / "Edge"
        / "Application"
        / "msedge.exe",
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError("Chrome or Edge not found")


def prepare_markdown(text: str) -> str:
    if MERMAID_FENCE.search(text):
        text = MERMAID_FENCE.sub(INFRA_PLACEHOLDER, text, count=1)
        if MERMAID_FENCE.search(text):
            raise RuntimeError("More than one Mermaid block; script handles one")
    text = re.sub(r"(\*\*[^*]+\*\*:)\n(?=- )", r"\1\n\n", text)
    return text


def rewrite_images(html: str, md_dir: Path) -> str:
    def repl(match: re.Match[str]) -> str:
        attrs, src = match.group(1), match.group(2)
        if src.startswith(("http://", "https://", "data:", "file:")):
            resolved = src
        else:
            resolved = (md_dir / src).resolve().as_uri()
        return f'<img {attrs}src="{resolved}"'

    return IMG_SRC.sub(repl, html)


def md_to_html(md_path: Path) -> str:
    text = prepare_markdown(md_path.read_text(encoding="utf-8"))
    body = markdown.markdown(
        text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list", "md_in_html"],
    )
    if INFRA_PLACEHOLDER in body:
        if not INFRA_DIAGRAM_PNG.is_file():
            sys.exit(f"Missing infrastructure diagram: {INFRA_DIAGRAM_PNG}")
        uri = INFRA_DIAGRAM_PNG.resolve().as_uri()
        figure = (
            f'<figure class="mermaid-figure">'
            f'<img alt="Infrastructure request path" src="{uri}">'
            f"</figure>"
        )
        body = body.replace(f"<p>{INFRA_PLACEHOLDER}</p>", figure)
        body = body.replace(INFRA_PLACEHOLDER, figure)
    body = rewrite_images(body, md_path.parent)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>RetryGuard on TopFull — Mentor Update</title>
<style>{CSS}</style>
</head>
<body>
{body}
</body>
</html>
"""


def print_pdf(html_path: Path, pdf_path: Path) -> None:
    import time

    browser = find_browser()
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    with tempfile.TemporaryDirectory(prefix="mentor-pdf-") as profile:
        cmd = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ]
        subprocess.run(cmd, check=True)
        for _ in range(20):
            if pdf_path.is_file() and pdf_path.stat().st_size > 10_000:
                return
            time.sleep(0.25)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    args = parser.parse_args()
    md_path = args.md.resolve()
    pdf_path = args.pdf.resolve()
    if not md_path.is_file():
        sys.exit(f"Markdown not found: {md_path}")

    with tempfile.TemporaryDirectory(prefix="mentor-update-pdf-") as tmp:
        html_path = Path(tmp) / "mentor-update.html"
        html_path.write_text(md_to_html(md_path), encoding="utf-8")
        print(f"Printing PDF with {find_browser().name}…")
        print_pdf(html_path, pdf_path)

    if not pdf_path.is_file() or pdf_path.stat().st_size < 10_000:
        sys.exit(f"PDF was not created or is too small: {pdf_path}")
    print(f"PDF: {pdf_path} ({pdf_path.stat().st_size / 1_048_576:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
