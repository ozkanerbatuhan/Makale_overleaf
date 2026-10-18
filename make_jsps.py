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

# JSPS her yazar icin kisa biyografi + fotograf istiyor. Foto figures/ altinda
# yoksa yerine cerceveli bos kutu basilir; foto gelince dosyayi koymak yeter.
BIOS = [
    ("bio_ozkaner.jpg", r"Ahmet Batuhan \"Ozkaner",
     r"""received the B.Sc. degree in energy systems engineering in 2025 and the
B.Sc. degree in electrical and electronics engineering (double major) in 2026,
both from \.Istanbul Bilgi University, \.Istanbul, T\"urkiye. Since 2026,
\"Ozkaner has been an electrical design engineer at R\"onesans Holding,
\.Istanbul. Research interests include FPGA-based digital design,
low-latency hardware acceleration of neural network inference, and embedded
systems."""),
    # TASLAK: Alper'in CV'si gelince doldurulacak.
    ("bio_ilik.jpg", r"Mustafa Alper Il{\i}k",
     r"""is with the Department of Electrical and Electronics Engineering,
\.Istanbul Bilgi University, \.Istanbul, T\"urkiye. Research interests
include embedded systems and FPGA-based hardware design."""),
    ("bio_sarioglu.jpg", r"Baykal Sar{\i}o\u{g}lu",
     r"""received the B.Sc. degree in electrical and electronics engineering
from Kadir Has University, \.Istanbul, T\"urkiye, in 2004, and the M.Sc. and
Ph.D. degrees in electrical and electronics engineering from Bo\u{g}azi\c{c}i
University, \.Istanbul, in 2007 and 2013, respectively. In 2007 Sar{\i}o\u{g}lu
worked as an FPGA system engineer at PAVO, and in 2013 was a postdoctoral
researcher at Bo\u{g}azi\c{c}i University within an EU FP7 project. Sar{\i}o\u{g}lu
joined the Department of Electrical and Electronics Engineering, \.Istanbul
Bilgi University, in 2013 and has been an Associate Professor there since
2023. Research interests include analog and digital integrated circuits,
biomedical circuits and systems, and embedded system design."""),
]


def biographies():
    out = []
    for photo, name, text in BIOS:
        if os.path.exists(os.path.join(SRC, "figures", photo)):
            pic = r"\includegraphics[width=\linewidth]{%s}" % photo
        else:
            pic = r"\fbox{\parbox[c][1.25\linewidth][c]{\dimexpr\linewidth-2\fboxsep-2\fboxrule}{\centering\scriptsize Photo}}"
        out.append(
            "\\noindent\\begin{minipage}[t]{0.24\\linewidth}\\vspace{0pt}\n"
            "%s\n\\end{minipage}\\hfill\n"
            "\\begin{minipage}[t]{0.72\\linewidth}\\vspace{0pt}\\footnotesize\n"
            "\\textbf{%s} %s\n\\end{minipage}\n\\par\\medskip\n" % (pic, name, text))
    return "\n".join(out)

PREAMBLE = r"""%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Journal of Signal Processing Systems (Springer) : gonderim formati
% Sablon: Springer Nature sn-jnl v3.1, sn-mathphys-num (numarali kaynak stili).
% Bu dosya make_jsps.py tarafindan ../main.tex'ten uretilir. Govde metnini
% burada degil ana main.tex'te duzenleyin, sonra script'i yeniden calistirin.
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
\documentclass[pdflatex,sn-mathphys-num,iicol]{sn-jnl}

\usepackage[T1]{fontenc}
\setlength{\tabcolsep}{3.5pt}  % iki sutunda tablolar sutuna sigsin
% Yayimlanmis JSPS gorunumune yakin: basliklar sans kalin ve sola yasli, ozet
% tam genislik. Yalniz sn-jnl'in font makrolari degisir, yerlesim ayni.
\usepackage[scaled=0.92]{helvet}
\makeatletter
\def\Titlefont{\reset@font\sffamily\fontsize{16bp}{20bp}\bfseries\selectfont\raggedright}%
\def\Authorfont{\reset@font\sffamily\fontsize{10.5bp}{13bp}\bfseries\selectfont\raggedright}%
\def\addressfont{\reset@font\fontsize{8.5bp}{10.5bp}\selectfont\raggedright}%
\def\abstractheadfont{\reset@font\sffamily\fontsize{10bp}{12bp}\bfseries\selectfont\raggedright}%
\def\abstractfont{\reset@font\fontsize{9.5bp}{11.5bp}\selectfont\leftskip=0pt\rightskip=0pt\parfillskip=0pt plus 1fil}%
\def\keywordfont{\reset@font\fontsize{9bp}{11bp}\selectfont\leftskip=0pt\rightskip=0pt plus0.5fill}%
\def\sectionfont{\reset@font\sffamily\fontsize{12bp}{14bp}\bfseries\selectfont\raggedright}%
\def\subsectionfont{\reset@font\sffamily\fontsize{10.5bp}{12.5bp}\bfseries\selectfont\raggedright}%
\def\subsubsectionfont{\reset@font\sffamily\fontsize{10bp}{12bp}\bfseries\itshape\selectfont\raggedright}%
\makeatother
\usepackage{graphicx}
\usepackage{multirow}
\usepackage{amsmath}
\usepackage{newtxtext,newtxmath}  % Times; amssymb sembolleri newtxmath'te
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

\author*[1]{\fnm{Ahmet Batuhan} \sur{\"Ozkaner}}\email{ahmet.ozkaner@bilgiedu.net}

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

    def fill_width(tab, width):
        """\\begin{tabular}{spec}...\\end{tabular} -> tabular* genislik doldurur."""
        head = r"\begin{tabular}"
        if not tab.startswith(head):
            return tab
        i, depth = len(head), 0
        for k in range(i, len(tab)):
            depth += {"{": 1, "}": -1}.get(tab[k], 0)
            if depth == 0:
                break
        spec = tab[i + 1:k]
        inner = tab[k + 1:-len(r"\end{tabular}")]
        # Yalniz metin sutunlu tablo (p/L): genislikleri oranla dagit, sola yasla.
        cols = re.findall(r"[pL]\{([\d.]+)cm\}", spec)
        rest = re.sub(r"@\{\}|[pL]\{[\d.]+cm\}|\s", "", spec)
        if cols and not rest:
            tot = sum(float(c) for c in cols)
            spec = "".join(r"L{\dimexpr%.3f%s-2\tabcolsep\relax}" % (float(c) / tot, width)
                           for c in cols)
            return r"\begin{tabular}{" + spec + "}" + inner + r"\end{tabular}"
        if spec.startswith("@{}"):
            spec = spec[3:]
        return (r"\begin{tabular*}{" + width + r"}{@{\extracolsep{\fill}}" + spec + "}" +
                inner + r"\end{tabular*}")

    # Sekiller: figures/x -> x (Springer alt klasor istemiyor)
    body = body.replace("{figures/", "{")

    # sn-jnl iki sutunu (iicol) elsarticle 5p sutunundan dar; tablolar tasiyor
    # (Overfull hbox). Her tabular'i kendi kutusuna sigdir: table* -> metin
    # genisligi, table -> sutun genisligi. Dar tablo buyutulmez (max width).
    out, pos = [], 0
    for m in re.finditer(r"\\begin\{(table\*?)\}", body):
        env = m.group(1)
        end = body.index(r"\end{" + env + "}", m.end())
        a = body.find(r"\begin{tabular", m.end(), end)
        if a < 0:
            continue
        b = body.index(r"\end{tabular}", a) + len(r"\end{tabular}")
        # sn-jnl'de \caption'dan sonra tabular kutuya alinamiyor (Missing
        # \endgroup); bu yuzden kutu yerine sabit sutunlari %10 daralt.
        tab = body[a:b]
        pre = body[pos:a]
        # Dogrulama tablosu (5 sayisal sutun) sutuna 8 pt tasiyor: bir punto kucult.
        if r"\label{tab:verification}" in body[m.end():a]:
            pre = pre.replace(r"\small", r"\footnotesize")
        # Karsilastirma tablosu iki sutun genisliginde bos kaliyor: sutunlari ac.
        if r"\label{tab:related_work}" in body[m.end():a]:
            tab = re.sub(r"([pL])\{([\d.]+)cm\}",
                         lambda t: "%s{%.2fcm}" % (t.group(1), float(t.group(2)) * 1.2), tab)
        if env == "table":
            tab = re.sub(r"([pL])\{([\d.]+)cm\}",
                         lambda t: "%s{%.2fcm}" % (t.group(1), float(t.group(2)) * 0.9), tab)
        # Dar tablo sutunun ortasinda kucuk duruyordu: tabular* ile tam genislige
        # yay (fazla bosluk sutun aralarina dagilir).
        tab = fill_width(tab, r"\textwidth" if env == "table*" else r"\columnwidth")
        out.append(pre + tab)
        pos = b
    body = "".join(out) + body[pos:]

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

\bmhead{Use of AI tools}
Large language model based assistants were used as an aid in the literature
search, in the development of the measurement and verification software, and
for correcting typographical and language errors in the manuscript. The authors
reviewed all such output and take full responsibility for the content of this
article.

{\raggedright
\bibliography{references}
\par}

\section*{Author Biographies}

%s
\end{document}
""" % (funding, competing, data, biographies())

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
    for photo, _, _ in BIOS:
        if os.path.exists(os.path.join(SRC, "figures", photo)):
            shutil.copy(os.path.join(SRC, "figures", photo), OUT)
    print("yazildi:", os.path.join(OUT, "main.tex"))
    print("sekil:", len(used), "| anahtar kelime:", kw)
    print("ozet kelime:", len(re.sub(r"\\[A-Za-z]+|[{}]", " ", abstract).split()))


if __name__ == "__main__":
    sys.exit(main())
