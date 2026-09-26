#!/usr/bin/env python3
"""
main.tex (elsarticle) -> JSPS_submission/main.tex (Springer Nature sn-jnl).

Journal of Signal Processing Systems gonderimi icin. Govde metnine dokunmaz;
yalnizca preamble, on-madde (baslik/yazar/ozet/anahtar kelime) ve son-madde
(Statements and Declarations) degisir. Springer LaTeX yuklemesinde alt klasor
kabul etmedigi icin sekiller duz klasore kopyalanir ve yollar duzeltilir.

Kullanim:  python make_jsps.py
Cikti   :  JSPS_submission/  (main.tex, references.bib, sn-jnl.cls, .bst, sekiller)
"""
import os
import re
import shutil
import sys

SRC = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(SRC, "JSPS_submission")
TEMPLATE = os.path.join(SRC, "springer_template")  # sn-jnl.cls + bst/

PREAMBLE = r"""%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Journal of Signal Processing Systems (Springer) : gonderim formati
% Sablon: Springer Nature sn-jnl v3.1, sn-mathphys-num (numarali kaynak stili).
% Bu dosya make_jsps.py tarafindan ../main.tex'ten uretilir. Govde metnini
% burada degil ana main.tex'te duzenleyin, sonra script'i yeniden calistirin.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\documentclass[pdflatex,sn-mathphys-num]{sn-jnl}

\usepackage{graphicx}
\usepackage{multirow}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{xcolor}
\usepackage{textcomp}
\usepackage{booktabs}
\usepackage{array}
\usepackage{siunitx}

% sn-jnl hyperref'i kendisi yukler.
\hypersetup{hidelinks}

% Dar tablo sutunlarinda iki yana yaslama kelimeler arasi asiri bosluk
% aciyor; L sola dayali p sutunudur.
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}

\raggedbottom

\begin{document}

\title[Run-Time Reconfigurable Neural Inference on a Low-Cost FPGA SoC]{%
A Run-Time Reconfigurable Neural Inference Engine with Deterministic
Sub-Microsecond Latency on a Low-Cost FPGA SoC}

\author*[1]{\fnm{Ahmet Batuhan} \sur{\"Ozkaner}}\email{ahmet.ozakner@bilgiedu.net}

\author[1]{\fnm{Mustafa Alper} \sur{Il{\i}k}}\email{alper.ilik@bilgiedu.net}

\author[1]{\fnm{Baykal} \sur{Sar{\i}o\u{g}lu}}\email{baykal.sarioglu@bilgi.edu.tr}

\affil*[1]{\orgdiv{Department of Electrical and Electronics Engineering},
\orgname{Istanbul Bilgi University}, \orgaddress{\city{Istanbul},
\country{T\"urkiye}}}

"""


def balanced(s, start):
    """s[start] == '{' ise eslesen kapanisa kadar icerigi ve bitis indeksini dondurur."""
    assert s[start] == "{"
    depth = 0
    for i in range(start, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
    raise ValueError("dengesiz parantez")


def between(s, a, b):
    i = s.index(a) + len(a)
    return s[i:s.index(b, i)]


def main():
    tex = open(os.path.join(SRC, "main.tex"), encoding="utf-8").read()

    abstract = between(tex, r"\begin{abstract}", r"\end{abstract}").strip()
    kw = between(tex, r"\begin{keyword}", r"\end{keyword}")
    kw = ", ".join(k.strip() for k in kw.split(r"\sep"))

    # Govde: Introduction'dan elsarticle beyanlarinin basina kadar.
    body_start = tex.index(r"\section{Introduction}")
    # Introduction'dan onceki yuzde-cizgi yorum satirini da al
    body_start = tex.rfind("\n%%%", 0, body_start) + 1
    body_end = tex.index(r"\section*{CRediT authorship contribution statement}")
    body_end = tex.rfind("\n%%%", 0, body_end - 200) + 1  # ELSEVIER yorum blogu
    body = tex[body_start:body_end].rstrip() + "\n"

    # Sekiller: figures/x -> x (Springer alt klasor istemiyor)
    body = body.replace("{figures/", "{")

    # sn-jnl tek sutun ve metin genisligi elsarticle 5p'den dar; iki sutuna
    # yayilan bu tablolar tasiyor (Overfull hbox). Metin genisligine sigdir.
    for label in ("tab:related_work", "tab:latency_breakdown"):
        i = body.index(r"\label{" + label + "}")
        a = body.index(r"\begin{tabular}", i)
        b = body.index(r"\end{tabular}", a) + len(r"\end{tabular}")
        body = body[:a] + r"\resizebox{\textwidth}{!}{%" + "\n" + \
            body[a:b] + "}" + body[b:]

    # Mevcut beyanlardan metinleri al
    def section_text(name):
        i = tex.index(r"\section*{" + name + "}") + len(r"\section*{" + name + "}")
        j = tex.find(r"\section*{", i)
        if j < 0:
            j = tex.index("%%%%", i)
        return tex[i:j].strip()

    data = section_text("Data availability")
    funding = section_text("Funding")
    competing = section_text("Declaration of competing interest")

    backmatter = r"""
\backmatter

\section*{Statements and Declarations}

\bmhead{Funding}
%s

\bmhead{Competing interests}
%s

\bmhead{Ethics approval and consent to participate}
Not applicable.

\bmhead{Consent for publication}
Not applicable.

\bmhead{Data availability}
The market data used in this study are publicly available Binance BTCUSDT
aggregated trade records. The measurement logs and verification stimuli are
part of the artifact described under Code availability.

\bmhead{Code availability}
%s

\bmhead{Author contributions}
Ahmet Batuhan \"Ozkaner: conceptualization, methodology, hardware and software
implementation, verification, formal analysis, investigation, data curation,
visualization, and writing of the original draft. Mustafa Alper Il{\i}k:
software, investigation, and review and editing of the manuscript. Baykal
Sar{\i}o\u{g}lu: supervision and project administration. All authors read and
approved the final manuscript.

\bibliography{references}

\end{document}
""" % (funding, competing, data)

    front = PREAMBLE + "\\abstract{%\n" + abstract + "}\n\n" + \
        "\\keywords{" + kw + "}\n\n\\maketitle\n\n"

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "main.tex"), "w", encoding="utf-8", newline="\n") as f:
        f.write(front + body + backmatter)

    shutil.copy(os.path.join(SRC, "references.bib"), OUT)
    shutil.copy(os.path.join(TEMPLATE, "sn-jnl.cls"), OUT)
    shutil.copy(os.path.join(TEMPLATE, "bst", "sn-mathphys-num.bst"), OUT)

    used = set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", body))
    for name in sorted(used):
        shutil.copy(os.path.join(SRC, "figures", name), OUT)
    print("yazildi:", os.path.join(OUT, "main.tex"))
    print("sekil:", len(used), "| anahtar kelime:", kw)
    print("ozet kelime:", len(re.sub(r"\\[A-Za-z]+|[{}]", " ", abstract).split()))


if __name__ == "__main__":
    sys.exit(main())
