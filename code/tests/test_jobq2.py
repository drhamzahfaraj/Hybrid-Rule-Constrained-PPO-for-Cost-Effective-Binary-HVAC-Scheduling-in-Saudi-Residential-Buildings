"""F1 acceptance: jobq2 smoke test (dependencies, env scrub, output/mtime check, stale RUN re-queue,
FAIL -> dependants BLOCKED, idempotent re-run). Runs in a temp copy; < 10 s."""
import json, os, shutil, subprocess, sys, time

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")


def _run(d, jobs):
    with open(os.path.join(d, "jobs.jsonl"), "w") as f:
        f.write("# comment line\n")
        for j in jobs:
            f.write(json.dumps(j) + "\n")
    env = dict(os.environ, RBRL_TAG="_leak", MAXJ="50", JOBQ_POLL="0.1")
    r = subprocess.run([sys.executable, "-I", os.path.join(d, "jobq2.py"), os.path.join(d, "jobs.jsonl")],
                       cwd=d, env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _st(d, jid):
    return json.load(open(os.path.join(d, ".jobq", jid + ".json")))


def test_jobq2_smoke(tmp_path):
    d = str(tmp_path)
    shutil.copy(os.path.join(ROOT, "jobq2.py"), d)
    os.makedirs(os.path.join(d, ".jobq"))
    # a stale RUN row left by a dead runner (pid that cannot exist) must be re-queued
    json.dump(dict(state="RUN", pid=2 ** 22 + 12345, key="old", t_start=0), open(os.path.join(d, ".jobq", "a.json"), "w"))
    open(os.path.join(d, "stale_out.txt"), "w").write("old")       # pre-existing output: mtime < start
    os.utime(os.path.join(d, "stale_out.txt"), (time.time() - 3600, time.time() - 3600))
    jobs = [
        dict(id="a", cmd='echo "tag=[$RBRL_TAG][$RBRL_X] omp=$OMP_NUM_THREADS" > a.txt', env={"RBRL_X": "1"}, outputs=["a.txt"]),
        dict(id="b", cmd="cat a.txt > b.txt", outputs=["b.txt"], after=["a"]),
        dict(id="c", cmd="true", outputs=["stale_out.txt"]),            # rc 0 but output is stale -> FAIL
        dict(id="d", cmd="echo never > d.txt", outputs=["d.txt"], after=["c"]),   # blocked by c
        dict(id="e", cmd="echo x > e.txt; exit 3", outputs=["e.txt"]),  # rc != 0 -> FAIL
    ]
    out = _run(d, jobs)
    assert _st(d, "a")["state"] == "DONE" and _st(d, "b")["state"] == "DONE"
    assert open(os.path.join(d, "b.txt")).read().strip() == "tag=[][1] omp=1"   # scrubbed, own env, 1 thread
    assert _st(d, "c")["state"] == "FAIL" and _st(d, "e")["state"] == "FAIL"
    assert not os.path.exists(os.path.join(d, ".jobq", "d.json")) and "d" in out.split("blocked:")[-1]
    # idempotent: a second run launches nothing
    mt = os.path.getmtime(os.path.join(d, "a.txt"))
    out2 = _run(d, jobs)
    assert "START" not in out2 and os.path.getmtime(os.path.join(d, "a.txt")) == mt


def test_round4_joblist_parses():
    p = os.path.join(ROOT, "jobs", "round4.jsonl")
    jobs = [json.loads(l) for l in open(p) if l.strip() and not l.lstrip().startswith("#")]
    ids = [j["id"] for j in jobs]
    assert len(ids) == len(set(ids))
    for j in jobs:
        assert set(j) <= {"id", "cmd", "env", "outputs", "after", "code_sensitive"}
        assert set(j.get("after", [])) <= set(ids)


def test_jobq2_dep_waits_for_rerun_after_code_change(tmp_path):
    """V-code-1: after a code edit both a and b are stale; b must wait for a's NEW output."""
    d = str(tmp_path)
    shutil.copy(os.path.join(ROOT, "jobq2.py"), d)
    jobs = [dict(id="a", cmd="sleep 0.5; date +%s%N > a.txt", outputs=["a.txt"]),
            dict(id="b", cmd="cat a.txt > b.txt; echo $RBRL_CODE_SHA > b_sha.txt", outputs=["b.txt"], after=["a"])]
    _run(d, jobs)
    first = open(os.path.join(d, "a.txt")).read()
    sha1 = open(os.path.join(d, "b_sha.txt")).read().strip()
    open(os.path.join(d, "other.py"), "w").write("x = 1\n")          # any code edit invalidates both keys
    out = _run(d, jobs)
    lines = [l.split()[1:3] for l in out.splitlines() if l[:2].isdigit()]
    assert lines.index(["DONE", "a"]) < lines.index(["START", "b"]), out
    a2 = open(os.path.join(d, "a.txt")).read()
    assert a2 != first and open(os.path.join(d, "b.txt")).read() == a2
    sha2 = open(os.path.join(d, "b_sha.txt")).read().strip()
    assert len(sha2) == 12 and sha2 != sha1                          # job sees the sha it started with


def test_jobq2_adopts_finished_orphan(tmp_path):
    """V-code-5: a RUN job whose runner died is accepted as DONE if its rc file says 0 and its
    outputs are fresh (not re-run); without an rc file it is re-queued."""
    d = str(tmp_path)
    shutil.copy(os.path.join(ROOT, "jobq2.py"), d)
    os.makedirs(os.path.join(d, ".jobq"))
    sys.path.insert(0, d)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("jq_t", os.path.join(d, "jobq2.py"))
        jq = importlib.util.module_from_spec(spec); spec.loader.exec_module(jq)
    finally:
        sys.path.remove(d)
    jobs = [dict(id="x", cmd="echo new > x.txt", outputs=["x.txt"]),
            dict(id="y", cmd="echo new > y.txt", outputs=["y.txt"])]
    t0 = time.time() - 10
    for j in jobs:
        json.dump(dict(state="RUN", pid=2 ** 22 + 4321, pstart=1, key=jq.key(j), t_start=t0),
                  open(os.path.join(d, ".jobq", j["id"] + ".json"), "w"))
        open(os.path.join(d, j["id"] + ".txt"), "w").write("orphan")
    open(os.path.join(d, ".jobq", "x.rc"), "w").write("0 done\n")
    open(os.path.join(d, "logs_x.txt"), "w").write("finished\n")
    _run(d, jobs)
    assert _st(d, "x")["state"] == "DONE" and open(os.path.join(d, "x.txt")).read() == "orphan"
    assert _st(d, "y")["state"] == "DONE" and open(os.path.join(d, "y.txt")).read().strip() == "new"


def test_jobq2_killed_job_is_not_adopted(tmp_path):
    """§21.1: a job killed while its runner was away must NOT be adopted as DONE rc=0 (no rc line
    from a completed command, outputs not fresh); it is re-queued (STALE) and rerun. Also: jobs
    without outputs are refused."""
    import signal
    d = str(tmp_path)
    shutil.copy(os.path.join(ROOT, "jobq2.py"), d)
    jobs = [dict(id="k", cmd="if [ -f again ]; then echo ok > k.txt; echo ran; else sleep 30; fi", outputs=["k.txt"])]
    with open(os.path.join(d, "jobs.jsonl"), "w") as f:
        f.write(json.dumps(jobs[0]) + "\n")
    env = dict(os.environ, MAXJ="50", JOBQ_POLL="0.1")
    r = subprocess.Popen([sys.executable, "-I", os.path.join(d, "jobq2.py"), os.path.join(d, "jobs.jsonl")],
                         cwd=d, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    for _ in range(100):
        if os.path.exists(os.path.join(d, ".jobq", "k.json")) and _st(d, "k").get("state") == "RUN":
            break
        time.sleep(0.05)
    r.send_signal(signal.SIGTERM); r.wait(timeout=10)             # runner gone, job keeps running
    pid = _st(d, "k")["pid"]
    os.killpg(os.getpgid(pid), signal.SIGTERM)                    # the job is killed
    for _ in range(100):
        try:
            os.kill(pid, 0); time.sleep(0.05)
        except ProcessLookupError:
            break
    open(os.path.join(d, "again"), "w").write("")
    out = _run(d, jobs)
    assert "ADOPTED-STALE k" in out and "ADOPTED-DONE" not in out, out
    assert _st(d, "k")["state"] == "DONE" and open(os.path.join(d, "k.txt")).read().strip() == "ok"
    # refusals
    with open(os.path.join(d, "bad.jsonl"), "w") as f:
        f.write(json.dumps(dict(id="n", cmd="true")) + "\n")
    rr = subprocess.run([sys.executable, "-I", os.path.join(d, "jobq2.py"), os.path.join(d, "bad.jsonl")],
                        cwd=d, env=env, capture_output=True, text=True, timeout=30)
    assert rr.returncode != 0 and "without an 'outputs'" in rr.stderr
