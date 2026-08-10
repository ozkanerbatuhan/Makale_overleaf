#!/usr/bin/env python3
"""
main.tex icin ONIZLEME PDF'i uretir.

Neden gerekli: bu makinede elsarticle.cls ve siunitx kurulu degil. Bu script
main.tex'e DOKUNMADAN gecici bir kopya uzerinde calisir, elsarticle'in on-madde
yapisini standart article ile taklit eder ve JSA'nin iki sutunlu duzenine yakin
bir cikti verir.

Gercek cikti Overleaf'te asil elsarticle ile alinacaktir; bu yalnizca metni ve
tablolari gozle kontrol etmek icindir.

Kullanim:  python3 build_preview.py
Cikti   :  main_onizleme.pdf
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

SRC = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SRC, "main_onizleme.pdf")


def balanced(s, start):
    """s[start] == '{' varsayimiyla eslesen kapanis parantezine kadar icerigi dondurur."""
    assert s[start] == "{"
    d, i = 0, start
    while i < len(s):
        if s[i] == "{":
            d += 1
        elif s[i] == "}":
            d -= 1
            if d == 0:
                return s[start + 1:i], i + 1
        i += 1
    raise ValueError("dengesiz parantez")


def grab(s, cmd):
    """\\cmd[opt]{...} icerigini ve tam eslesmeyi dondurur."""
    m = re.search(r"\\" + cmd + r"\s*(\[[^\]]*\])?\s*\{", s)
    if not m:
        return None, None
    body, end = balanced(s, m.end() - 1)
    return body, s[m.start():end]


SHIM = r"""
\documentclass[twocolumn,10pt]{article}
\usepackage[a4paper,top=2.2cm,bottom=2.2cm,left=1.8cm,right=1.8cm]{geometry}
\usepackage{times}
\usepackage[T1]{fontenc}
\setlength{\columnsep}{0.7cm}
\setlength{\parindent}{1em}
% --- siunitx yerine minimal karsiliklar ---
\newcommand{\percent}{\%}\newcommand{\micro}{$\mu$}\newcommand{\nano}{n}
\newcommand{\milli}{m}\newcommand{\kilo}{k}\newcommand{\mega}{M}\newcommand{\giga}{G}
\newcommand{\second}{s}\newcommand{\hertz}{Hz}\newcommand{\watt}{W}
\newcommand{\celsius}{$^\circ$C}\newcommand{\bit}{bit}
\newcommand{\SI}[2]{#1\,{#2}}\newcommand{\si}[1]{{#1}}\newcommand{\num}[1]{#1}
% --- bolum basliklarini JSA'ya yaklastir ---
\usepackage[small,bf]{titlesec}
\titleformat{\section}{\normalfont\bfseries}{\thesection.}{0.6em}{}
\titleformat{\subsection}{\normalfont\itshape}{\thesubsection.}{0.6em}{}
% elsarticle'a ozgu, article'da bulunmayan komutlar
\newcommand{\journal}[1]{}
\newcommand{\ead}[1]{}
\newcommand{\cortext}[2][]{}
\newcommand{\corref}[1]{}
"""


def main():
    src = open(os.path.join(SRC, "main.tex"), encoding="utf-8").read()

    title, _ = grab(src, "title")
    # yazar adlarini dengeli parantezle topla (\corref{} icerdigi icin
    # basit [^}]* kalibi calismaz -- ilk denemede tam olarak burada kirilmisti)
    names = []
    for m in re.finditer(r"\\author\s*(\[[^\]]*\])?\s*\{", src):
        body, _ = balanced(src, m.end() - 1)
        body = re.sub(r"\\corref\{[^}]*\}", r"$^{*}$", body)
        names.append(body.strip())
    addr, _ = grab(src, "address")

    abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", src, re.S)
    abstract = abstract.group(1).strip() if abstract else ""
    kw = re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}", src, re.S)
    kw = kw.group(1).strip() if kw else ""
    kw = re.sub(r"%[^\n]*", "", kw)
    kw = ", ".join(x.strip() for x in kw.split(r"\sep") if x.strip())

    # --- govde: on-maddeyi tamamen cikar ---
    body = src
    body = re.sub(r"\\begin\{frontmatter\}.*?\\end\{frontmatter\}", "@@FRONT@@",
                  body, flags=re.S)
    body = re.sub(r"\n\\documentclass\[[^\]]*\]\{elsarticle\}", "\n@@SHIM@@", body)
    body = re.sub(r"\\usepackage\{siunitx\}\n", "", body)
    body = body.replace("\\bibliographystyle{elsarticle-num}",
                        "\\bibliographystyle{unsrt}")

    front = (
        # NOT: iceride \\[10pt] gibi kaliplar var; kose parantez istege
        # bagli argumani erken kapatiyor -> tum icerik {} ile korunuyor.
        "\\twocolumn[{%\n"
        "\\vspace*{-0.8cm}\n"
        "\\begin{center}\n"
        "{\\LARGE\\linespread{1.25}\\selectfont " + (title or "").strip() + "\\par}\\vspace{12pt}\n"
        "{\\large " + " \\quad ".join(names) + "}\\\\[6pt]\n"
        "{\\itshape " + (addr or "").strip() + "}\n"
        "\\end{center}\n"
        "\\vspace{6pt}\\noindent\\rule{\\textwidth}{0.4pt}\\vspace{6pt}\n"
        "\\noindent\\textbf{Abstract}\\\\[4pt]\n"
        "\\noindent " + abstract + "\\\\[6pt]\n"
        "\\noindent\\textit{Keywords:} " + kw + "\n"
        "\\vspace{6pt}\\noindent\\rule{\\textwidth}{0.4pt}\\vspace{14pt}\n"
        "}]\n"
    )
    body = body.replace("@@SHIM@@", SHIM).replace("@@FRONT@@", front)

    tmp = tempfile.mkdtemp(prefix="tex_")
    for f in os.listdir(SRC):
        s = os.path.join(SRC, f)
        d = os.path.join(tmp, f)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)
    open(os.path.join(tmp, "main.tex"), "w", encoding="utf-8").write(body)

    env = dict(os.environ, TEXINPUTS=".:")
    for cmd in (["pdflatex", "-interaction=nonstopmode", "main.tex"],
                ["bibtex", "main"],
                ["pdflatex", "-interaction=nonstopmode", "main.tex"],
                ["pdflatex", "-interaction=nonstopmode", "main.tex"]):
        subprocess.run(cmd, cwd=tmp, env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    pdf = os.path.join(tmp, "main.pdf")
    if not os.path.exists(pdf):
        log = open(os.path.join(tmp, "main.log"), encoding="utf-8",
                   errors="replace").read()
        print("\n".join(l for l in log.splitlines() if l.startswith("! "))[:1500])
        sys.exit("PDF uretilemedi")
    shutil.copy2(pdf, OUT)

    log = open(os.path.join(tmp, "main.log"), encoding="utf-8",
               errors="replace").read()
    errs = [l for l in log.splitlines() if l.startswith("! ")]
    und = log.count("undefined")
    over = [float(x) for x in
            re.findall(r"Overfull \\hbox \(([0-9.]+)pt", log) if float(x) > 20]
    print("hata: %d   tanimsiz: %d   ciddi tasma(>20pt): %d" %
          (len(errs), und, len(over)))
    for e in errs[:5]:
        print("  ", e)
    print("cikti:", OUT)


if __name__ == "__main__":
    main()
