"""Test 18 (gate only): every result file the manuscript cites exists and is CURRENT: every CSV row
carries prov_code_sha == the code sha of ONE tag of the code-of-record lineage (RBRL_GATE_TAG,
comma-separated, default build_registry.GATE_TAGS), the
.meta.json has the same code_sha and code_changed_during_run == false (V-code-15).

The cited set = tests/cited_tables.txt (globs must match) + results/<name> paths in main.tex and the
files it \\input's. It may not be vacuous: at least MIN_CITED files (V-code-15). Frozen entries need
a reason and must exist. Logic lives in build_registry (manifest, resolve, file_status) so the
registry's auto-status and this gate cannot disagree.

Run at CP1/CP2, not in the fast tier:  pytest -m gate tests/test_gate_provenance.py
The tag's sha uses rbrl_io's algorithm on the TAGGED tree, so jobs must run from a clean checkout
of that tag (an untracked .py changes the sha). The fast tests below check the gate logic itself.
"""
import csv, json, os, sys
import pytest

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
sys.path.insert(0, ROOT)
import build_registry as B

TAG = os.environ.get("RBRL_GATE_TAG", B.GATE_TAGS)
# Required cited entries (manifest lines; each glob counts once). Lower ONLY together with a
# deletion from the paper of a REQ-or-delete job, with a note here: (none so far).
MIN_CITED = 130


@pytest.mark.slow
@pytest.mark.gate
def test_cited_files_current_with_tag_sha():
    sha, where = B.record_sha()
    assert "tags" in where, f"no tag of {TAG} exists (Gate T0 not passed): the gate cannot pass"
    files, unmatched = B.cited()
    assert len(B.manifest()) >= MIN_CITED and len(files) >= MIN_CITED, \
        f"manifest too short: {len(B.manifest())} lines / {len(files)} files < {MIN_CITED} (vacuous gate)"
    bad = [f"{g}: glob matched no file" for g in unmatched]
    for name, frozen in sorted(files.items()):
        st, det = B.file_status(name, sha, frozen)
        if st not in B.OK:
            bad.append(f"{name}: {st} {det}")
    assert not bad, f"{len(bad)} cited file(s) not CURRENT:\n" + "\n".join(bad)


# ------------------------------------------------------------------ fast: the gate is not vacuous
def test_manifest_is_not_vacuous_and_covers_the_consumers():
    import v3_names as V
    m = B.manifest()
    assert len(m) >= MIN_CITED
    files, _ = B.resolve(m)
    used = {V.name(k, c) + (".json" if k == "DUAL" else ".csv")
            for k in V.V3 for c in (V.CITIES if "{c}" in V.V3[k] else (None,))}
    used |= {V.MZ_RULES.format(topo=t, lij=l) + s for t, ls in V.MZ_LAYOUTS for l in ls for s in (".csv", "_perwindow.csv")}
    used |= {V.MZ_MPC.format(topo=t, lij=l, h=V.MZ_MPC_H) + s for t, ls in V.MZ_LAYOUTS for l in ls
             for s in (".csv", "_perwindow.csv")}
    missing = sorted(n for n in used if n not in files)
    assert not missing, f"read by the v3 consumers but not in the manifest: {missing}"


def _stamp(d, name, sha, changed=False, rows=2, meta=True):
    p = os.path.join(d, name)
    if name.endswith(".csv"):
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["x", "prov_code_sha"]); w.writeheader()
            for i in range(rows):
                w.writerow(dict(x=i, prov_code_sha=sha))
    else:
        json.dump({"a": 1}, open(p, "w"))
    if meta:
        json.dump(dict(code_sha=sha, code_changed_during_run=changed, impl="t"), open(p + ".meta.json", "w"))


def test_file_status_flags_every_failure(tmp_path):
    d = str(tmp_path)
    _stamp(d, "ok.csv", "aaa"); _stamp(d, "old.csv", "bbb"); _stamp(d, "span.csv", "aaa", changed=True)
    _stamp(d, "nometa.csv", "aaa", meta=False); _stamp(d, "c.json", "aaa"); _stamp(d, "cs.json", "bbb")
    st = lambda n, fr=None: B.file_status(n, "aaa", fr, results=d)[0]
    assert st("ok.csv") == "CURRENT" and st("c.json") == "CURRENT"
    assert st("old.csv") == "STALE" and st("cs.json") == "STALE"
    assert st("span.csv") == "SPANNED"                  # code_changed_during_run -> not current
    assert st("nometa.csv") == "UNSTAMPED" and st("gone.csv") == "MISSING"
    assert st("old.csv", "kept for the record") == "FROZEN" and st("gone.csv", "x") == "MISSING"


def test_manifest_syntax_globs_and_frozen(tmp_path):
    d = str(tmp_path)
    for n in ("T16v3_r23.6-22.4_riyadh.csv", "T16v3_riyadh.csv"):
        _stamp(d, n, "aaa")
    man = tmp_path / "m.txt"
    man.write_text("# c\nT16v3_r*_riyadh.csv\nT16v3_r*_taif.csv\nold.csv frozen superseded, kept\n")
    files, unmatched = B.resolve(B.manifest(str(man)), results=d)
    assert files == {"T16v3_r23.6-22.4_riyadh.csv": None, "old.csv": "superseded, kept"}
    assert unmatched == ["T16v3_r*_taif.csv"]
    man.write_text("old.csv frozen\n")
    with pytest.raises(ValueError, match="reason"):
        B.manifest(str(man))
