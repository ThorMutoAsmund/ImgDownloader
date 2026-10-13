#!/usr/bin/env python3
# Build USER_MANUAL.pdf from USER_MANUAL.md via HTML + Microsoft Edge.

from __future__ import annotations

import html
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MD_PATH = ROOT / "USER_MANUAL.md"
HTML_PATH = ROOT / "USER_MANUAL.html"
PDF_PATH = ROOT / "USER_MANUAL.pdf"

EDGE_CANDIDATES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


# Convert a small subset of Markdown (headings, lists, tables, code) to HTML.
def md_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    out: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>Stock Photo Downloader - User Manual</title>",
        "<style>",
        "body{font-family:'Segoe UI',Calibri,sans-serif;max-width:800px;"
        "margin:40px auto;line-height:1.45;color:#222}",
        "h1{font-size:1.8rem;border-bottom:2px solid #333;padding-bottom:.3em}",
        "h2{font-size:1.25rem;margin-top:1.6em}",
        "code,pre{font-family:Consolas,monospace;background:#f4f4f4}",
        "pre{padding:12px;overflow:auto;border-radius:4px}",
        "table{border-collapse:collapse;width:100%;margin:1em 0}",
        "th,td{border:1px solid #ccc;padding:6px 10px;text-align:left}",
        "th{background:#f0f0f0}",
        "ul{padding-left:1.2em}",
        "</style>",
        "</head>",
        "<body>",
    ]

    in_code = False
    in_table = False
    in_list = False
    table_header_done = False

    # Close an open <ul> if one is in progress.
    def close_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    # Close an open <table> if one is in progress.
    def close_table() -> None:
        nonlocal in_table, table_header_done
        if in_table:
            out.append("</table>")
            in_table = False
            table_header_done = False

    # Escape HTML and apply bold, code, and link Markdown inline markup.
    def inline(text: str) -> str:
        text = html.escape(text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        return text

    for line in lines:
        if line.startswith("```"):
            close_list()
            close_table()
            if in_code:
                out.append("</pre>")
                in_code = False
            else:
                out.append("<pre>")
                in_code = True
            continue

        if in_code:
            out.append(html.escape(line))
            continue

        if line.startswith("|"):
            close_list()
            if re.match(r"^\|\s*-+", line):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not in_table:
                out.append("<table>")
                in_table = True
                table_header_done = False
            tag = "th" if not table_header_done else "td"
            out.append(
                "<tr>"
                + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in cells)
                + "</tr>"
            )
            table_header_done = True
            continue

        close_table()

        if line.startswith("# "):
            close_list()
            out.append(f"<h1>{inline(line[2:])}</h1>")
            continue
        if line.startswith("## "):
            close_list()
            out.append(f"<h2>{inline(line[3:])}</h2>")
            continue
        if line.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(line[2:])}</li>")
            continue

        close_list()
        if not line.strip():
            continue
        out.append(f"<p>{inline(line)}</p>")

    close_list()
    close_table()
    if in_code:
        out.append("</pre>")
    out.extend(["</body>", "</html>", ""])
    return "\n".join(out)


# Return the path to msedge.exe, or raise if Edge is not installed.
def find_edge() -> Path:
    for candidate in EDGE_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Microsoft Edge not found")


# Build USER_MANUAL.pdf from USER_MANUAL.md and return an exit code.
def main() -> int:
    markdown = MD_PATH.read_text(encoding="utf-8")
    # Normalize any leftover fancy punctuation to ASCII for PDF safety.
    replacements = {
        "\u2014": "-",  # em dash
        "\u2013": "-",  # en dash
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u00d7": "x",
        "\u2026": "...",
    }
    for src, dst in replacements.items():
        markdown = markdown.replace(src, dst)

    HTML_PATH.write_text(md_to_html(markdown), encoding="utf-8")

    edge = find_edge()
    if PDF_PATH.exists():
        PDF_PATH.unlink()

    subprocess.run(
        [
            str(edge),
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={PDF_PATH}",
            HTML_PATH.resolve().as_uri(),
        ],
        check=False,
    )

    for _ in range(20):
        if PDF_PATH.exists() and PDF_PATH.stat().st_size > 0:
            break
        time.sleep(0.25)
    else:
        print("PDF was not created", file=sys.stderr)
        return 1

    HTML_PATH.unlink(missing_ok=True)
    print(f"Wrote {PDF_PATH} ({PDF_PATH.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
