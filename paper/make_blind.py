#!/usr/bin/env python3
"""Produce double-anonymous review copies from the Springer build.

    python3 to_springer.py      # main.tex -> main_sn.tex
    python3 make_blind.py       # main_sn.tex -> main_sn_blind.tex,
                                # supplement.tex -> supplement_blind.tex

Removed: author names, affiliation, e-mail, ORCID (none is given), the
funding and author-contribution statements (replaced by "Removed for
double-anonymous review"), acknowledgements (none in this manuscript), the
GitHub repository URL and name and the Zenodo DOI (replaced by "[link withheld
for double-anonymous review]"), and PDF author metadata. Self-references in the
text are rewritten in the third person; the reference list is kept unchanged,
so the author's earlier paper stays an ordinary numbered citation.

Every substitution is checked: the script stops if a pattern it expects is not
found, so a later edit of main.tex cannot silently leave an identifying
passage in the blinded copy.
"""
import re
import sys

WITHHELD = "[link withheld for double-anonymous review]"
REMOVED = "Removed for double-anonymous review."


def sub_once(s, pattern, repl, what, flags=0, count=1):
    new, n = re.subn(pattern, repl, s, count=0 if count is None else count, flags=flags)
    if n == 0:
        sys.exit(f"make_blind: pattern for {what!r} not found")
    return new


def blind_main(src="main_sn.tex", dst="main_sn_blind.tex"):
    s = open(src).read()
    # 1. author, e-mail and affiliation
    s = sub_once(s, r"\\author\*\[1\]\{[^\n]*\}(?:\\email\{[^}]*\})?\n", "", "author/email")
    s = sub_once(s, r"\\affil\*\[1\]\{.*?\}\}\}\n", "", "affiliation", flags=re.S)
    # 2. PDF metadata
    s = sub_once(s, r"\\begin\{document\}",
                 r"\\hypersetup{pdfauthor={},pdfsubject={},pdfkeywords={}}\n\\begin{document}",
                 "hypersetup")
    # 3. self-references in the third person
    s = sub_once(s, r"The closest prior work is the present author's physics-informed",
                 "The closest prior work is an earlier physics-informed", "self-ref (Sec. 1)")
    s = sub_once(s, r"The nearest neighbour to this study is the present author's own recent work in\s*\nthis journal",
                 "The nearest neighbour to this study is earlier work in\nthis journal", "self-ref (Sec. 2.4)")
    # 4. funding and author contributions
    s = sub_once(s, r"(\\bmhead\{Funding\}\n).*?(?=\n\n)", r"\g<1>" + REMOVED, "funding", flags=re.S)
    s = sub_once(s, r"(\\bmhead\{Author contributions\}\n).*?(?=\n\n)", r"\g<1>" + REMOVED,
                 "author contributions", flags=re.S)
    if re.search(r"\\bmhead\{Acknowledg", s):
        s = sub_once(s, r"(\\bmhead\{Acknowledg[^}]*\}\n).*?(?=\n\n)", r"\g<1>" + REMOVED,
                     "acknowledgements", flags=re.S)
    # 5. repository and archive links
    s = sub_once(s, r"The code is available at\s*\n\\href\{https://github\.com/[^}]*\}\{[^\n]*\}\},\s*\narchived on Zenodo at\s*\n\\href\{https://doi\.org/10\.5281/zenodo\.[0-9]+\}\{[^\n]*\}\}\n\(release v4\.0-round4\)",
                 "The code is available at " + WITHHELD + ",\narchived on Zenodo at " + WITHHELD + "\n(release v4.0-round4)",
                 "repository links")
    # 6. final check: nothing identifying may remain outside the bibliography
    body = s[: s.index("\\bibliography")] if "\\bibliography" in s else s
    for pat in (r"Faraj", r"Hamzah", r"drhamzahfaraj", r"zenodo\.\d", r"github",
                r"tu\.edu\.sa", r"Taif University", r"Ranyah", r"present author"):
        hits = [m.start() for m in re.finditer(pat, body)]
        # \citep{Faraj2026} is a citation key, not printed text
        hits = [h for h in hits if not body[max(0, h - 7):h].endswith("{") and
                not re.match(r"Faraj20\d\d", body[h:h + 9])]
        if hits:
            sys.exit(f"make_blind: {pat!r} still in {dst} body at offsets {hits[:5]}")
    open(dst, "w").write(s)
    print(f"-> {dst}")


def blind_supplement(src="supplement.tex", dst="supplement_blind.tex"):
    s = open(src).read()
    s = sub_once(s, r"\\author\{[^}]*\}", r"\\author{}", "supplement author")
    s = sub_once(s, r"\\begin\{document\}",
                 r"\\hypersetup{pdfauthor={}}\n\\begin{document}", "supplement hypersetup")
    for pat in (r"Faraj", r"Hamzah", r"github", r"zenodo", r"Taif University"):
        if re.search(pat, s):
            sys.exit(f"make_blind: {pat!r} still in {dst}")
    open(dst, "w").write(s)
    print(f"-> {dst}")


if __name__ == "__main__":
    blind_main()
    blind_supplement()
