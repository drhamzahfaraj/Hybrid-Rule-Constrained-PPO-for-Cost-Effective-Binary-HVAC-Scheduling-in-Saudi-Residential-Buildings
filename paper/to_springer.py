#!/usr/bin/env python3
"""Convert main.tex (elsarticle, numbered) -> main_sn.tex (Springer Nature sn-jnl,
Springer Basic author-year, two-column), matching the format of the author's
published JKSU-ES article (2026) 38:58.

Idempotent: always regenerates main_sn.tex from main.tex, so content edits are
made once, in main.tex, and the Springer build follows.

Transformations
  1. Preamble: documentclass -> sn-jnl[pdflatex,sn-basic,iicol]; drop the
     elsarticle-only \\journal; theorem environments declared with sn styles.
  2. Front matter: frontmatter/\\author/\\ead/\\cortext/\\affiliation/abstract/
     keywords -> \\title \\author*{\\fnm \\sur}\\email \\affil* \\abstract \\keywords
     \\maketitle; affiliation as printed in the published article.
  3. Citations (numbered -> author-year):
       "Name et al.~\\cite{K}", "A and B~\\cite{K}", "Name~\\cite{K}" -> \\citet{K}
       remaining "\\cite{A}, \\cite{B}" runs -> \\citep{A,B}; lone \\cite -> \\citep
  4. Back matter: the elsarticle declaration sections -> \\backmatter with
     \\bmhead / \\section*{Declarations}, ordered as in the published article.
  5. Bibliography style -> handled by the class option (sn-basic).
"""
import re, sys

SRC, DST = "main.tex", "main_sn.tex"
s = open(SRC).read()

# ------------------------------------------------------------- 1. preamble
s = s.replace(r"\documentclass[3p,twocolumn,number]{elsarticle}",
              r"\documentclass[pdflatex,sn-mathphys-num,iicol]{sn-jnl}")
s = re.sub(r"\\journal\{[^}]*\}\n?", "", s)
s = s.replace(r"\usepackage{amsmath,amssymb,amsthm}", r"\usepackage{amsmath,amssymb}")
# sn-jnl loads amsthm and defines theorem styles; declare ours with them
s = s.replace(
    r"\newtheorem{definition}{Definition} \newtheorem{proposition}{Proposition} \newtheorem{remark}{Remark} \newtheorem{observation}{Observation} \newtheorem{corollary}{Corollary}",
    "\\theoremstyle{thmstyleone}\\newtheorem{proposition}{Proposition}\\newtheorem{corollary}{Corollary}\n"
    "\\theoremstyle{thmstyletwo}\\newtheorem{remark}{Remark}\\newtheorem{observation}{Observation}\n"
    "\\theoremstyle{thmstylethree}\\newtheorem{definition}{Definition}")
# hyperref is loaded by sn-jnl; a second load with options clashes
s = re.sub(r"\\usepackage\[colorlinks=true[^\]]*\]\{hyperref\}\n", "", s)
s = re.sub(r"\\pdfstringdefDisableCommands\{%.*?\n\}\n", "", s, flags=re.S)

# ------------------------------------------------------------- 2. front matter
fm_a = s.index(r"\begin{frontmatter}")
fm_b = s.index(r"\end{frontmatter}") + len(r"\end{frontmatter}")
fm = s[fm_a:fm_b]
title = re.search(r"\\title\{(.*?)\}\s*\\author", fm, re.S).group(1)
abstract = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", fm, re.S).group(1).strip()
kw = re.search(r"\\begin\{keyword\}(.*?)\\end\{keyword\}", fm, re.S).group(1)
kws = [k.strip() for k in kw.replace("\n", " ").split(r"\sep") if k.strip()]
new_fm = (
    f"\\title[Optimising Binary HVAC Switching in Saudi Homes]{{{title}}}\n\n"
    "\\author*[1]{\\fnm{Hamzah} \\sur{Faraj}}\n\n"  # e-mail omitted in the public repository copy
    "\\affil*[1]{\\orgdiv{Department of Sciences and Technology}, "
    "\\orgname{Ranyah University College, Taif University}, "
    "\\orgaddress{\\street{P.O. Box 11099}, \\city{Taif}, \\postcode{21944}, "
    "\\country{Saudi Arabia}}}\n\n"
    f"\\abstract{{{abstract}}}\n\n"
    f"\\keywords{{{', '.join(kws)}}}\n\n"
    "\\maketitle\n")
s = s[:fm_a] + new_fm + s[fm_b:]

# ------------------------------------------------------------- 3. citations
NAME = r"(?:[A-Z][A-Za-z\\{}'\-\u00C0-\u017F]+)"
# "X et al.~\cite{K}" / "X et al. (2021)~\cite{K}"
s = re.sub(NAME + r"(?:\s+" + NAME + r")?\s+et\s+al\.(?:\s*\(\d{4}\))?~\\cite\{([^}]+)\}",
           r"\\citet{\1}", s)
# "A and B~\cite{K}"
s = re.sub(NAME + r"\s+and\s+" + NAME + r"~\\cite\{([^}]+)\}", r"\\citet{\1}", s)
# runs "\cite{A}, \cite{B}" -> \citep{A,B}
def merge(m):
    keys = re.findall(r"\\cite\{([^}]+)\}", m.group(0))
    return r"\citep{" + ",".join(keys) + "}"
s = re.sub(r"\\cite\{[^}]+\}(?:\s*,\s*\\cite\{[^}]+\})+", merge, s)
# single-surname narrative "Krarti~\cite{K}": only when the word IS the first
# author's surname of K (read from the .bib), never a common noun before \cite
bib = open("references.bib").read()
first_sur = {}
for key, auth in re.findall(r"@\w+\{([^,]+),.*?author\s*=\s*\{(.*?)\},\s*\n", bib, re.S):
    a1 = auth.split(" and ")[0].strip().strip("{}")
    sur = a1.split(",")[0].strip() if "," in a1 else a1.split()[-1]
    first_sur[key.strip()] = re.sub(r"[{}\\'`^\"~]", "", sur)
def narr(m):
    word, key = m.group(1), m.group(2).split(",")[0].strip()
    clean = re.sub(r"[{}\\'`^\"~]", "", word)
    sur = first_sur.get(key, "")
    if sur and (clean == sur or sur.endswith(clean) or clean.endswith(sur.split()[-1])):
        return r"\citet{" + m.group(2) + "}"
    return m.group(0)
s = re.sub(r"(?<![.\w])(" + NAME + r")~\\cite\{([^}]+)\}", narr, s)
# remaining "~\cite" / "\cite" -> parenthetical
s = s.replace(r"~\cite{", r" \citep{")
s = re.sub(r"\\cite\{", r"\\citep{", s)

# ------------------------------------------------------------- 4. back matter
def grab(head):
    m = re.search(r"\\section\*?\{" + re.escape(head) + r"\}\s*(?:\\label\{[^}]*\}\s*)?(.*?)(?=\\section\*?\{|\\bibliographystyle|\\bibliography\{)",
                  s, re.S)
    return (m.group(1).strip() if m else None), m
blocks = {}
for h in ("CRediT Author Statement", "Declaration of Competing Interest",
          "Funding", "Ethics Declaration", "Data and Code Availability"):
    txt, m = grab(h)
    if txt is not None:
        blocks[h] = txt
first = min(s.index("\\section{" + h + "}") for h in blocks)
end = s.index(r"\bibliographystyle")
bm = ["\\backmatter\n"]
if "Funding" in blocks:
    bm.append("\\bmhead{Funding}\n" + blocks["Funding"] + "\n")
if "CRediT Author Statement" in blocks:
    bm.append("\\bmhead{Author contributions}\n" + blocks["CRediT Author Statement"] + "\n")
if "Data and Code Availability" in blocks:
    bm.append("\\bmhead{Data availability}\n" + blocks["Data and Code Availability"] + "\n")
bm.append("\\section*{Declarations}\n")
if "Ethics Declaration" in blocks:
    bm.append("\\bmhead{Ethics approval and consent to participate}\n" + blocks["Ethics Declaration"] + "\n")
if "Declaration of Competing Interest" in blocks:
    bm.append("\\bmhead{Competing interests}\n" + blocks["Declaration of Competing Interest"] + "\n")
s = s[:first] + "\n".join(bm) + "\n" + s[end:]
s = re.sub(r"\\bibliographystyle\{[^}]*\}\n?", "", s)

# the Data section becomes an unnumbered back-matter heading in Springer layout
s = re.sub(r"Section~\\ref\{sec:data\}", "the Data availability statement", s)
s = re.sub(r"Section \\ref\{sec:data\}", "the Data availability statement", s)
open(DST, "w").write(s)
left = len(re.findall(r"\\cite\{", s))
print(f"-> {DST}: {len(re.findall(r'citet', s))} \\citet, "
      f"{len(re.findall(r'citep', s))} \\citep, {left} bare \\cite left")
