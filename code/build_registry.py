#!/usr/bin/env python3
"""Build VALUES_REGISTRY.md: every cited v3 file with its status DERIVED FROM THE DATA, and the
headline values read from those files (RULING_round4 F18, job J17).

Status (automatic; nothing is typed):
  CURRENT    every CSV row carries prov_code_sha == ONE code of record and the .meta.json has the
             same code_sha and code_changed_during_run == false. The code of record is the tag
             lineage RBRL_GATE_TAG (comma-separated; default p6,p9,p10,p11,p13 — RULING_round4
             §15–§28 records what each tag changed and why the earlier outputs stay valid); the
             working-tree code sha if no tag exists yet
  STALE      stamped with another code sha (re-run the job)
  SPANNED    the run straddled a code change (code_changed_during_run == true)
  UNSTAMPED  no provenance (no prov_code_sha column or no .meta.json)
  MISSING    cited but absent
  FROZEN     listed "frozen <reason>" in the manifest (exists; reason printed)
The cited set is tests/cited_tables.txt (+ results/<name> paths in main.tex and its \\input files);
every other file under results/ is listed as NOT CITED with its own stamp, for the record.

Run:  python3 build_registry.py   -> VALUES_REGISTRY.md; exit 1 if any cited file is not CURRENT/FROZEN
"""
from __future__ import annotations
import csv, fnmatch, glob, hashlib, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import rbrl_io as IO
import v3_names as V

OUT = f"{IO.ROOT}/VALUES_REGISTRY.md"
MANIFEST = f"{IO.ROOT}/tests/cited_tables.txt"
TEX = os.environ.get("RBRL_TEX_DIR", "/home/claude/v4")
OK = ("CURRENT", "FROZEN")


# ------------------------------------------------------------------ code of record, manifest
def tag_code_sha(tag):
    """rbrl_io's algorithm (basename + bytes of every top-level *.py) on the TAGGED tree."""
    r = subprocess.run(["git", "-C", IO.ROOT, "ls-tree", "--name-only", tag], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    h = hashlib.sha256()
    for name in sorted(n for n in r.stdout.split() if n.endswith(".py")):
        h.update(name.encode())
        h.update(subprocess.run(["git", "-C", IO.ROOT, "show", f"{tag}:{name}"], capture_output=True, check=True).stdout)
    return h.hexdigest()[:12]


GATE_TAGS = "p6,p9,p10,p11,p13,p16,p19,p20"   # the round-4 lineage of record (RULING_round4 §31)


def record_sha():
    """(set of accepted code shas, description). One file must be stamped by ONE of them."""
    tags = [t.strip() for t in os.environ.get("RBRL_GATE_TAG", GATE_TAGS).split(",") if t.strip()]
    shas = {t: tag_code_sha(t) for t in tags}
    ok = {s: t for t, s in shas.items() if s}
    if not ok:
        return frozenset({IO.code_sha_now()}), "working tree (tags absent)"
    return frozenset(ok), "tags " + ", ".join(f"{t}={s}" for s, t in ok.items())


def manifest(path=MANIFEST):
    """[(pattern, frozen_reason or None)] in file order; comments and blank lines dropped."""
    out = []
    for line in open(path):
        line = line.split("#")[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        fr = None
        if len(parts) > 1:
            if not parts[1].startswith("frozen"):
                raise ValueError(f"manifest: bad line {line!r}")
            fr = parts[1][len("frozen"):].strip()
            if not fr:
                raise ValueError(f"manifest: frozen without a reason: {line!r}")
        out.append((parts[0], fr))
    return out


def tex_cited(tex=TEX):
    """results/<name> paths written in main.tex and the files it \\input's."""
    main = os.path.join(tex, "main.tex")
    if not os.path.exists(main):
        return []
    src = open(main).read()
    texs = [main] + [os.path.join(tex, m if m.endswith(".tex") else m + ".tex")
                     for m in re.findall(r"\\input\{([^}]+)\}", src)]
    out = []
    for t in texs:
        if os.path.exists(t):
            for n in re.findall(r"results/([A-Za-z0-9_.\-]*[A-Za-z0-9_\-])", open(t).read()):
                out.append(n if n.endswith((".csv", ".json")) else n + ".csv")
    return out


def resolve(entries, results=None):
    """{file: frozen_reason or None} plus [unmatched globs]."""
    results = results or IO.R
    files, unmatched = {}, []
    for pat, fr in entries:
        if any(ch in pat for ch in "*?["):
            hits = sorted(os.path.basename(p) for p in glob.glob(os.path.join(results, pat))
                          if not p.endswith((".meta.json", ".lock")))
            if not hits:
                unmatched.append(pat)
            for h in hits:
                files[h] = fr
        else:
            files[pat] = fr
    return files, unmatched


def cited(results=None, tex=TEX):
    files, unmatched = resolve(manifest(), results)
    for n in tex_cited(tex):
        files.setdefault(n, None)
    return files, unmatched


def file_status(name, sha, frozen=None, results=None):
    """(status, detail) of one result file against the code-of-record sha."""
    p = os.path.join(results or IO.R, name)
    if not os.path.exists(p):
        return "MISSING", ""
    if frozen is not None:
        return "FROZEN", frozen
    meta = p + ".meta.json"
    if not os.path.exists(meta):
        return "UNSTAMPED", "no .meta.json"
    m = json.load(open(meta))
    shas = {m.get("code_sha") or "<none>"}
    if name.endswith(".csv"):
        rows = list(csv.DictReader(open(p)))
        if not rows or "prov_code_sha" not in rows[0]:
            return "UNSTAMPED", "no prov_code_sha column"
        shas |= {r.get("prov_code_sha") or "<none>" for r in rows}
    accepted = set(sha) if isinstance(sha, (set, frozenset)) else {sha}
    if len(shas) != 1 or not shas <= accepted:
        return "STALE", f"code {sorted(shas)} not one of {sorted(accepted)}"
    if m.get("code_changed_during_run"):
        return "SPANNED", f"code changed during the run (at write {m.get('code_sha_at_write')})"
    return "CURRENT", f"{m.get('impl', '?')} {m.get('utc', '')}"


# ------------------------------------------------------------------ values (read, never typed)
def values():
    """[(quantity, value string, source stem)] for the headline numbers; MISSING on any error."""
    out = []

    def add(q, fn, src):
        try:
            out.append((q, fn(), src))
        except Exception as e:
            out.append((q, f"**MISSING** ({type(e).__name__}: {e})", src))
    for c in V.CITIES:
        for arm, src in (("TUNED", "T1v3_perwindow"), ("guard", "T1v3_perwindow"),
                         ("MPC24", f"T21v3_{c}_perwindow"), ("MPCp24", f"T21v3_pers_{c}_perwindow"),
                         ("MPCr24", f"T16v3_r23.8-22.4_{c}_perwindow")):
            add(f"{V.CN[c]}: {arm} pooled equalised saving s (%)",
                lambda arm=arm, c=c: f"{V.pooled(V.perwindow(arm, c).values()):.2f}", src)
        add(f"{V.CN[c]}: RBRL saving, mean of seeds (%)",
            lambda c=c: f"{np.mean([V.pooled(v.values()) for v in V.perwindow_seeds('RBRL', c).values()]):.2f}",
            f"rbrl_ppo5_v3_{c}_perwindow")
        add(f"{V.CN[c]}: CLV (best attained) / bound B* (%)",
            lambda c=c: "{:.2f} / {:.1f}".format(*[float(V.read('CLV', c)[0][k]) for k in ("clv_s_pooled", "bound_reported")]),
            f"T17v3_{c}")
    try:
        for r in V.read("STATS"):
            out.append((f"{r['family']} {r['contrast']}, {V.CN[r['city']]}: HL [95.3% CI], p_adj",
                        f"{float(r['hl']):+.2f} [{float(r['hl_lo']):+.2f}, {float(r['hl_hi']):+.2f}], "
                        f"{float(r['p_adj']):.3f} ({r['resolution']})", V.name("STATS")))
    except Exception as e:
        out.append(("paired statistics", f"**MISSING** ({type(e).__name__}: {e})", V.name("STATS")))
    try:
        inv = json.load(open(f"{IO.R}/invariants_run.json"))
        out.append(("invariant gate: checks / failed / full run",
                    f"{inv['n_checks']} / {inv['n_failed']} / {inv['full_gate']}", "invariants_run"))
    except Exception as e:
        out.append(("invariant gate", f"**MISSING** ({type(e).__name__})", "invariants_run"))
    return out


def main(out=OUT):
    sha, where = record_sha()
    files, unmatched = cited()
    st = {n: file_status(n, sha, fr) for n, fr in files.items()}
    L = ["# Values Registry", "",
         f"Generated by `build_registry.py` from `results/` and `tests/cited_tables.txt`. **Do not edit.** "
         f"Code of record: `{sha}` ({where}). Every status below is computed from the files' provenance "
         "stamps; every value is read from its v3 file when this document is built.", "",
         "```bash", "python3 invariants.py        # gate; saves results/invariants_run.json",
         "python3 stats_v3.py && python3 cycling_energy.py && python3 gen_tables_v3.py",
         "python3 verify_numbers.py    # re-derives every tabulated value (--final at G2)",
         "python3 build_registry.py    # this document", "```", "",
         "## 1. Headline values", "", "| Quantity | Value | Source | Source status |", "|---|---|---|---|"]
    for q, v, src in values():
        s = st.get(src + ".csv", st.get(src + ".json", (file_status(src + ".csv", sha)[0], "")))[0]
        L.append(f"| {q} | {v} | `{src}` | {s} |")
    counts = {k: sum(1 for s in st.values() if s[0] == k) for k in
              ("CURRENT", "FROZEN", "STALE", "SPANNED", "UNSTAMPED", "MISSING")}
    L += ["", f"## 2. Cited files ({len(files)}): " + ", ".join(f"{k} {v}" for k, v in counts.items() if v), "",
          "| File | Status | Detail |", "|---|---|---|"]
    for n in sorted(files):
        L.append(f"| `{n}` | {st[n][0]} | {st[n][1]} |")
    for pat in unmatched:
        L.append(f"| `{pat}` | MISSING | glob matched no file |")
    other = sorted(os.path.basename(p) for p in glob.glob(f"{IO.R}/*") if os.path.isfile(p)
                   and p.endswith((".csv", ".json")) and not p.endswith(".meta.json")
                   and os.path.basename(p) not in files)
    L += ["", f"## 3. Not cited ({len(other)}; never a source of a printed figure)", "",
          "| File | Stamp |", "|---|---|"]
    for n in other:
        L.append(f"| `{n}` | {file_status(n, sha)[0]} |")
    IO.write_text(out, "\n".join(L) + "\n", comment="[//]: #")
    bad = [n for n, s in st.items() if s[0] not in OK] + unmatched
    print(f"-> {out}: {len(files)} cited, {len(bad)} not CURRENT")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
