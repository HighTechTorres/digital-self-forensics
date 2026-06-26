#!/usr/bin/env python3
"""
render_docs.py — convert Markdown to Word (.docx) and PDF, robustly, on any machine.

Usage:
    python3 render_docs.py <file.md | folder>     # converts a file or every .md in a folder

Strategy (auto-detects what's installed, no hard dependency):
  Markdown -> HTML : python 'markdown' pkg if present, else a minimal built-in converter.
  HTML -> .docx    : pandoc  ->  macOS textutil  ->  LibreOffice (soffice)
  HTML -> .pdf     : headless Chrome/Chromium/Brave/Edge  ->  pandoc  ->  wkhtmltopdf  ->  LibreOffice

Nothing is uploaded; all conversion is local.
"""
import os, sys, shutil, subprocess, tempfile, re, glob

CSS = """
@page{margin:1in;}
body{font-family:-apple-system,'Segoe UI','Helvetica Neue',Arial,sans-serif;font-size:11pt;line-height:1.5;color:#1a1a1a;max-width:780px;margin:0 auto;}
h1{font-size:22pt;border-bottom:3px solid #2b5fa8;padding-bottom:6px;color:#15233a;}
h2{font-size:15pt;color:#2b5fa8;border-bottom:1px solid #ddd;padding-bottom:3px;margin-top:24px;}
h3{font-size:12.5pt;color:#444;margin-top:16px;}
table{border-collapse:collapse;width:100%;margin:12px 0;font-size:10pt;}
th,td{border:1px solid #ccc;padding:6px 9px;text-align:left;vertical-align:top;}
th{background:#e9eef6;color:#15233a;}
tr:nth-child(even) td{background:#f7f9fc;}
blockquote{border-left:4px solid #5b9bd5;background:#eef5fc;margin:12px 0;padding:8px 16px;}
code,pre{font-family:'SF Mono',Consolas,Menlo,monospace;font-size:9.5pt;}
pre{background:#f4f6f9;border:1px solid #dce3ec;border-radius:5px;padding:12px;overflow-x:auto;}
hr{border:none;border-top:1px solid #ddd;margin:20px 0;} a{color:#2b5fa8;}
"""

def which(*names):
    for n in names:
        p = shutil.which(n)
        if p: return p
    return None

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
def find_chrome():
    for c in CHROME_CANDIDATES:
        if os.path.exists(c): return c
    return which("google-chrome","chromium","chromium-browser","brave-browser","msedge")

def md_to_html(md_text):
    try:
        import markdown
        body = markdown.markdown(md_text, extensions=["tables","fenced_code","sane_lists","nl2br"])
    except Exception:
        body = _minimal_md(md_text)
    return f'<!DOCTYPE html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'

def _minimal_md(t):
    # very small fallback: headers, bold/italic, code, hr, paragraphs, simple tables
    out, in_tbl = [], False
    for line in t.split("\n"):
        if re.match(r'^\s*\|.*\|\s*$', line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if re.match(r'^[\s\|:\-]+$', line): continue
            if not in_tbl: out.append("<table>"); in_tbl=True
            tag = "th" if all(re.match(r'^[\*_ A-Za-z0-9].*', c) for c in cells) and out[-1]=="<table>" else "td"
            out.append("<tr>"+"".join(f"<{tag}>{c}</{tag}>" for c in cells)+"</tr>")
            continue
        if in_tbl: out.append("</table>"); in_tbl=False
        h = re.match(r'^(#{1,6})\s+(.*)', line)
        if h: out.append(f"<h{len(h.group(1))}>{h.group(2)}</h{len(h.group(1))}>"); continue
        if re.match(r'^\s*---\s*$', line): out.append("<hr>"); continue
        if line.strip()=="" : out.append("<br>"); continue
        line = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', line)
        line = re.sub(r'`(.+?)`', r'<code>\1</code>', line)
        out.append(f"<p>{line}</p>")
    if in_tbl: out.append("</table>")
    return "\n".join(out)

def to_docx(html_path, out_docx):
    pandoc = which("pandoc")
    if pandoc:
        if subprocess.run([pandoc, html_path, "-o", out_docx]).returncode==0 and os.path.exists(out_docx): return "pandoc"
    textutil = which("textutil")
    if textutil:
        if subprocess.run([textutil,"-convert","docx","-output",out_docx,html_path]).returncode==0 and os.path.exists(out_docx): return "textutil"
    soffice = which("soffice","libreoffice")
    if soffice:
        subprocess.run([soffice,"--headless","--convert-to","docx","--outdir",os.path.dirname(out_docx) or ".",html_path])
        cand = os.path.splitext(html_path)[0]+".docx"
        if os.path.exists(cand):
            if cand!=out_docx: shutil.move(cand,out_docx)
            return "libreoffice"
    return None

def to_pdf(html_path, out_pdf):
    chrome = find_chrome()
    if chrome:
        subprocess.run([chrome,"--headless","--disable-gpu","--no-pdf-header-footer",
                        f"--print-to-pdf={out_pdf}", "file://"+os.path.abspath(html_path)],
                       stderr=subprocess.DEVNULL)
        if os.path.exists(out_pdf) and os.path.getsize(out_pdf)>0: return "chrome"
    wk = which("wkhtmltopdf")
    if wk and subprocess.run([wk,html_path,out_pdf]).returncode==0 and os.path.exists(out_pdf): return "wkhtmltopdf"
    pandoc = which("pandoc")
    if pandoc and subprocess.run([pandoc,html_path,"-o",out_pdf]).returncode==0 and os.path.exists(out_pdf): return "pandoc"
    soffice = which("soffice","libreoffice")
    if soffice:
        subprocess.run([soffice,"--headless","--convert-to","pdf","--outdir",os.path.dirname(out_pdf) or ".",html_path])
        cand=os.path.splitext(html_path)[0]+".pdf"
        if os.path.exists(cand):
            if cand!=out_pdf: shutil.move(cand,out_pdf)
            return "libreoffice"
    return None

def convert(md_file):
    base = os.path.splitext(md_file)[0]
    html = md_to_html(open(md_file, encoding="utf-8").read())
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html); hp=f.name
    d = to_docx(hp, base+".docx"); p = to_pdf(hp, base+".pdf")
    os.unlink(hp)
    print(f"  {os.path.basename(md_file)}  ->  docx:{d or 'FAILED'}  pdf:{p or 'FAILED'}")

def main():
    if len(sys.argv)<2:
        print(__doc__); sys.exit(1)
    target=sys.argv[1]
    files = sorted(glob.glob(os.path.join(target,"*.md"))) if os.path.isdir(target) else [target]
    if not files: print("No .md files found."); sys.exit(1)
    print(f"Rendering {len(files)} file(s):")
    for f in files: convert(f)

if __name__=="__main__":
    main()
