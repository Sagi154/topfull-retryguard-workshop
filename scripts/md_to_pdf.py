import sys
import pathlib
import markdown

CSS = """
@page { size: A4; margin: 18mm 16mm; }
* { box-sizing: border-box; }
body {
  font-family: "Segoe UI", Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.5;
  color: #1a1a1a;
  max-width: 100%;
}
h1 { font-size: 22pt; border-bottom: 2px solid #444; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 16pt; border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 22px; }
h3 { font-size: 13pt; margin-top: 18px; color: #222; }
h4 { font-size: 11.5pt; margin-top: 14px; color: #333; }
p, li { font-size: 11pt; }
ul, ol { padding-left: 22px; }
li { margin: 3px 0; }
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
  overflow-x: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}
pre code { background: none; padding: 0; font-size: 9pt; }
blockquote {
  border-left: 4px solid #b0b0b0;
  margin: 10px 0;
  padding: 4px 14px;
  color: #555;
  background: #fafafa;
}
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 10pt; }
th, td { border: 1px solid #bbb; padding: 6px 9px; text-align: left; vertical-align: top; }
th { background: #eee; }
a { color: #0b5cad; text-decoration: none; }
hr { border: none; border-top: 1px solid #ccc; margin: 20px 0; }
"""

def convert(md_path: pathlib.Path, html_path: pathlib.Path):
    text = md_path.read_text(encoding="utf-8")
    html_body = markdown.markdown(
        text,
        extensions=[
            "tables",
            "fenced_code",
            "toc",
            "sane_lists",
            "attr_list",
            "md_in_html",
        ],
    )
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{md_path.stem}</title>
<style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""
    html_path.write_text(doc, encoding="utf-8")

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        md = pathlib.Path(arg)
        html = md.with_suffix(".html")
        convert(md, html)
        print(f"HTML: {html}")
