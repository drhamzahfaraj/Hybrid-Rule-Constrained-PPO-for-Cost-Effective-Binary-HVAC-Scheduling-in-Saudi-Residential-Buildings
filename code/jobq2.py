#!/usr/bin/env python3
"""jobq2: dependency-aware, resumable, idempotent job runner for a 2-core box.

Run ONLY as:  cd /home/claude/rbrl && nohup python3 -I jobq2.py jobs/round4.jsonl > logs_jobq2.txt 2>&1 &
(replaces jobq_runner.py + jobq.txt, which are retired; see jobs/round4.jsonl for the format)
(file name chosen so it cannot shadow any stdlib / site-packages module; checked by tests/test_fast.py::test_no_module_shadowing)

jobs.jsonl, one JSON object per line:
  {"id": "t1_copT", "cmd": "python3 t1_v2.py t1",
   "env": {"RBRL_COP": "badescu", "RBRL_TAG": "_copT"},
   "outputs": ["results/T1v2_heldout_copT.csv", "results/tuned_params_v2_copT.json"],
   "after": []}
  {"id": "mpc_copT_riyadh", "cmd": "python3 mpc_lambda.py --city riyadh --horizons 24",
   "env": {"RBRL_COP": "badescu", "RBRL_TAG": "_copT"},
   "outputs": ["results/T21v2_riyadh_copT.csv"], "after": ["t1_copT"]}

Guarantees
  * a job starts only when every 'after' job is DONE (no `until [ -f ]` loops holding a slot;
    a FAILED dependency marks dependants BLOCKED instead of spinning forever);
  * env is SCRUBBED of every RBRL_* variable, then the job's own env is applied (no leakage);
  * one thread per BLAS/torch, nice 10, own session (killable as a group);
  * idempotent: DONE is keyed by sha(cmd, env, code); changing any of them reruns the job;
  * resumable: state is one atomic file per job in .jobq/; a RUN whose pid is gone is re-queued;
  * a job is DONE only if exit 0 AND every declared output exists and is newer than its start;
    every job must declare a non-empty `outputs` list (refused otherwise);
  * an orphan (runner gone, job no longer alive) is adopted as DONE only if the wrapper wrote
    "<rc> done" AFTER the command returned (a killed job never writes it) with rc 0, fresh
    outputs and a non-empty log (ruling §21.1: killed jobs were adopted as rc=0);
  * admission control: slots = MAXJ minus CPU-bound python processes this runner does not own.
"""
import hashlib, glob, json, os, shlex, signal, subprocess, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
SD = os.path.join(ROOT, ".jobq")
MAXJ = int(os.environ.get("MAXJ", "2"))
POLL = float(os.environ.get("JOBQ_POLL", "15"))
THREADS = {k: "1" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                            "NUMEXPR_NUM_THREADS", "TORCH_NUM_THREADS")}


def code_sha():
    """Same algorithm as rbrl_io.code_sha (basename + content of every top-level *.py), so a
    job's DONE key and the prov_code_sha stamped in its CSVs refer to the same code state."""
    h = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(ROOT, "*.py"))):
        h.update(os.path.basename(p).encode()); h.update(open(p, "rb").read())
    return h.hexdigest()[:12]


def key(job, sha=None):
    sha = code_sha() if sha is None else sha
    s = json.dumps([job["cmd"], job.get("env", {}), sha if job.get("code_sensitive", True) else ""],
                   sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def st_path(jid):
    return os.path.join(SD, jid + ".json")


def load(jid):
    try:
        return json.load(open(st_path(jid)))
    except FileNotFoundError:
        return {}


def save(jid, d):
    tmp = st_path(jid) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(d, f); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, st_path(jid))


def rc_path(jid):
    return os.path.join(SD, jid + ".rc")


def pstart(pid):
    """kernel start time of pid (field 22 of /proc/pid/stat), or None: guards against pid reuse."""
    try:
        return int(open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[19])
    except (FileNotFoundError, ProcessLookupError, IndexError, ValueError):
        return None


def alive(pid, start=None):
    if start is not None and pstart(pid) != start:
        return False                       # pid gone or reused by another process
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:                                   # zombie child counts as dead
        return open(f"/proc/{pid}/stat").read().split()[2] != "Z"
    except FileNotFoundError:
        return False


def foreign_cpu_jobs(own):
    n = 0
    for d in os.listdir("/proc"):
        if not d.isdigit() or int(d) in own:
            continue
        try:
            sid = int(open(f"/proc/{d}/stat").read().rsplit(")", 1)[1].split()[3])
            if sid in own:                      # our own job's session (children have start_new_session)
                continue
            cmd = [c for c in open(f"/proc/{d}/cmdline", "rb").read().split(b"\0") if c]
            if (cmd and os.path.basename(cmd[0]).startswith(b"python")
                    and any(c.endswith(b".py") for c in cmd[1:])
                    and not any(c.endswith(b"jobq2.py") for c in cmd)):
                n += 1
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            pass
    return n


def outputs_ok(job, t_start):
    if not job.get("outputs"):
        return False                       # nothing to check is never success (§21.1)
    for o in job["outputs"]:
        p = os.path.join(ROOT, o)
        if not os.path.exists(p) or os.path.getmtime(p) < t_start:      # ruling: mtime >= start
            return False
    return True


def log_ok(jid):
    p = os.path.join(ROOT, f"logs_{jid}.txt")
    return os.path.exists(p) and os.path.getsize(p) > 0


def read_rc(jid):
    """rc of a COMPLETED command: the wrapper writes "<rc> done" only after the command returned
    (no EXIT trap: a trap also fires when the shell itself is killed). None otherwise."""
    try:
        f = open(rc_path(jid)).read().split()
        return int(f[0]) if len(f) >= 2 and f[1] == "done" else None
    except (FileNotFoundError, ValueError, IndexError):
        return None


def main(jobfile):
    os.makedirs(SD, exist_ok=True)
    jobs = [json.loads(l) for l in open(jobfile) if l.strip() and not l.lstrip().startswith("#")]
    ids = [j["id"] for j in jobs]
    assert len(ids) == len(set(ids)), "duplicate job ids"
    unknown = sorted({a for j in jobs for a in j.get("after", [])} - set(ids))
    assert not unknown, f"'after' names unknown job ids: {unknown}"
    no_out = [j["id"] for j in jobs if not j.get("outputs")]
    assert not no_out, f"jobs without an 'outputs' list (refused, §21.1): {no_out}"
    byid = {j["id"]: j for j in jobs}
    procs = {}
    while True:
        # 1. reap finished children
        for jid, p in list(procs.items()):
            if p.poll() is None:
                continue
            s = load(jid); job = byid[jid]
            ok = p.returncode == 0 and read_rc(jid) == 0 and outputs_ok(job, s["t_start"])
            s.update(state="DONE" if ok else "FAIL", rc=p.returncode, t_end=time.time())
            save(jid, s); del procs[jid]
            print(time.strftime("%H:%M"), s["state"], jid, f"rc={p.returncode}", flush=True)
        # 2. classify (one code sha per pass; every key below refers to the same code state)
        sha = code_sha()
        keys = {j["id"]: key(j, sha) for j in jobs}
        pending, blocked = [], []
        for j in jobs:
            s = load(j["id"]); k = keys[j["id"]]
            if s.get("state") == "RUN" and j["id"] not in procs:
                if alive(s.get("pid", -1), s.get("pstart")):
                    continue                         # still running from a previous runner
                # died while we were away: accept it if the wrapper recorded rc 0 and the outputs
                # are fresh; otherwise re-queue
                rc = read_rc(j["id"])
                ok = rc == 0 and outputs_ok(j, s.get("t_start", float("inf"))) and log_ok(j["id"])
                s.update(state="DONE" if ok else "STALE", rc=rc, adopted=True); save(j["id"], s)
                print(time.strftime("%H:%M"), "ADOPTED-" + s["state"], j["id"], f"rc={rc}", flush=True)
            if j["id"] in procs:
                continue
            if s.get("state") == "DONE" and s.get("key") == k:
                continue
            if s.get("state") == "FAIL" and s.get("key") == k:
                continue                             # needs a human (or a code/env change)
            # a dependency is satisfied only by a DONE under the CURRENT key and not running:
            # after a code/env edit the parent reruns first and the child waits for it
            dst = [(a, load(a)) for a in j.get("after", [])]
            if any(d.get("state") == "FAIL" and d.get("key") == keys[a] for a, d in dst):
                blocked.append(j["id"]); continue
            if all(d.get("state") == "DONE" and d.get("key") == keys[a] and a not in procs for a, d in dst):
                pending.append(j)
        if not pending and not procs:
            print("idle; blocked:", blocked or "none", flush=True)
            return
        # 3. launch within the free cores
        free = MAXJ - len(procs) - foreign_cpu_jobs({p.pid for p in procs.values()} | {os.getpid()})
        for j in pending[:max(0, free)]:
            env = {k: v for k, v in os.environ.items() if not k.startswith("RBRL_")}
            env.update(THREADS); env.update(j.get("env", {}))
            env["RBRL_CODE_SHA"] = sha        # rbrl_io stamps this, the code the job STARTED with
            rcf = rc_path(j["id"])
            if os.path.exists(rcf):
                os.unlink(rcf)
            wrapped = f"( {j['cmd']}\n)\nrc=$?; echo \"$rc done\" > {shlex.quote(rcf)}; exit $rc"
            t_start = time.time()
            with open(os.path.join(ROOT, f"logs_{j['id']}.txt"), "w") as log:
                p = subprocess.Popen(["nice", "-n", "10", "bash", "-c", wrapped], cwd=ROOT, env=env,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            procs[j["id"]] = p
            save(j["id"], dict(state="RUN", pid=p.pid, pstart=pstart(p.pid), key=keys[j["id"]],
                               code_sha=sha, t_start=t_start, cmd=j["cmd"], env=j.get("env", {})))
            print(time.strftime("%H:%M"), "START", j["id"], flush=True)
        time.sleep(POLL)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))   # children keep running; next runner adopts them
    main(sys.argv[1])
