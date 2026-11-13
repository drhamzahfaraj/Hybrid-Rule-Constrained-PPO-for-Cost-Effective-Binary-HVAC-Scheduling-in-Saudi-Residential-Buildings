"""rbrl_io: the ONLY way results are written. Atomic, locked, provenance-stamped.

    import rbrl_io as IO
    IO.write_csv("T1v2_heldout", rows, inputs=[f"{IO.R}/tuned_params_v2{H.TAG}.json"])
    IO.write_json("tuned_params_v2", params)
    p = IO.read_json("tuned_params_v2")            # tag-aware, records itself as an input

Contract (RULING_round4 §3 F2)
  * atomic (mkstemp -> fsync -> os.replace) and locked (O_EXCL lock file, stale-pid lock broken);
  * header = UNION of row keys (first-seen order, or sorted with sort_keys=True), restval "";
  * every CSV row carries prov_code_sha, prov_impl, prov_env (RBRL_* only), prov_inputs (sha of
    every input read through read_json/read_csv or passed as inputs=), prov_utc; the full record
    goes to <file>.meta.json (argv, git rev, python/numpy, host, pid);
  * RBRL_TAG is appended to the file name (apply_tag=True);
  * an empty table or an empty row raises ValueError; rows with fit_status == "none" are REFUSED:
    never written to the CSV, listed under "refused_rows" in the .meta.json and printed
    (on_refused="raise" makes them an error instead). A table of only refused rows raises.
"""
from __future__ import annotations
import contextlib, csv, fcntl, glob, hashlib, json, os, socket, subprocess, sys, tempfile, time
import numpy as np

ROOT = os.environ.get("RBRL_ROOT", "/home/claude/rbrl")
R = os.environ.get("RBRL_RESULTS", f"{ROOT}/results")
_READ = {}                      # every input this process read via read_json/read_csv -> sha


def _sha(path, n=16):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:n]


def code_sha_now():
    """hash of every top-level .py in ROOT (basename + bytes), computed now. Covers uncommitted
    edits, which the git rev (also recorded) does not; jobq2.code_sha uses the same algorithm."""
    h = hashlib.sha256()
    for p in sorted(glob.glob(f"{ROOT}/*.py")):
        h.update(os.path.basename(p).encode()); h.update(open(p, "rb").read())
    return h.hexdigest()[:12]


# The code a process STARTED with (V-code-2): jobq2 passes the sha it computed at launch in
# RBRL_CODE_SHA; otherwise it is computed at import. A job that spans a commit is therefore
# stamped with its starting code, and the write-time sha is recorded beside it in .meta.json.
_CODE = os.environ.get("RBRL_CODE_SHA") or code_sha_now()


def code_sha():
    return _CODE


def git_rev():
    try:
        r = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or None
    except Exception:
        return None


def tag():
    return os.environ.get("RBRL_TAG", "")


def provenance(inputs=(), impl=None):
    ins = dict(_READ)
    for p in inputs:
        if os.path.exists(p):
            ins[os.path.relpath(p, ROOT)] = _sha(p)
    now = code_sha_now()
    return dict(code_sha=code_sha(), code_sha_at_write=now, code_changed_during_run=(now != code_sha()),
                git=git_rev(), impl=impl or os.path.basename(sys.argv[0]),
                argv=" ".join(sys.argv),
                env={k: v for k, v in sorted(os.environ.items())
                     if k.startswith("RBRL_") and k != "RBRL_CODE_SHA"},
                inputs=ins, python=sys.version.split()[0], numpy=np.__version__,
                host=socket.gethostname(), pid=os.getpid(),
                utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))


def _py(v, ndigits=6):
    """numpy-safe scalar for CSV/JSON: np.float32/int64/bool_ -> Python; floats rounded to
    ndigits (None: unrounded)."""
    if isinstance(v, np.ndarray):
        return [_py(x, ndigits) for x in v.tolist()]
    if isinstance(v, np.generic):
        v = v.item()
    if isinstance(v, float) and ndigits is not None:
        return round(v, ndigits)
    return v


def _json_default(o):
    if isinstance(o, (np.generic, np.ndarray)):
        return _py(o)
    raise TypeError(f"not JSON serialisable: {type(o).__name__}")


def _pid_alive(pid):
    try:
        os.kill(pid, 0); return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


@contextlib.contextmanager
def locked(path, wait_s=600):
    """per-output advisory lock (fcntl.flock on <path>.lock). The kernel drops the lock when the
    holder dies, so there is no stale-lock breaking and no TOCTOU race (V-code-4); the lock file
    is never unlinked (unlinking a flock file would reopen the race). A live holder makes us wait,
    then fail loudly. The file holds the holder's pid and argv for diagnostics only."""
    lk = path + ".lock"; t0 = time.time()
    os.makedirs(os.path.dirname(lk) or ".", exist_ok=True)
    fd = os.open(lk, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB); break
            except BlockingIOError:
                if time.time() - t0 > wait_s:
                    try:
                        who = open(lk).read().strip()
                    except Exception:
                        who = "?"
                    raise RuntimeError(f"{lk} held by a live writer ({who}): concurrent writer")
                time.sleep(min(1.0, max(0.05, wait_s / 10)))
        os.ftruncate(fd, 0); os.lseek(fd, 0, 0)
        os.write(fd, f"{os.getpid()} {' '.join(sys.argv)}\n".encode())
        yield
    finally:
        os.close(fd)                      # releases the flock


def _atomic(path, write_fn, mode="w"):
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix="_" + os.path.basename(path))
    try:
        with os.fdopen(fd, mode, newline="" if "b" not in mode else None) as f:
            write_fn(f); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)                       # atomic on POSIX: readers see old or new, never partial
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


PROV_COLS = ("prov_code_sha", "prov_impl", "prov_env", "prov_inputs", "prov_utc")


def _is_none_fit(r):
    v = r.get("fit_status")
    return isinstance(v, str) and v.strip().lower() == "none"


def write_csv(name, rows, inputs=(), impl=None, apply_tag=True, ndigits=6, sort_keys=False,
              on_refused="drop"):
    """ndigits: round floats (6 = the historical t1_v2/rbrl_ppo convention; None = full repr).
    sort_keys: sorted header (the historical final_tables.dump convention)."""
    rows = list(rows)
    if not rows:
        raise ValueError(f"{name}: no rows (refusing to write an empty table)")
    if any(not r for r in rows):
        raise ValueError(f"{name}: empty row(s) at {[i for i, r in enumerate(rows) if not r]}")
    clash = sorted({k for r in rows for k in r} & set(PROV_COLS))
    if clash:
        raise ValueError(f"{name}: row keys collide with provenance columns {clash}")
    refused = [r for r in rows if _is_none_fit(r)]
    if refused:
        msg = f"{name}: {len(refused)} row(s) with fit_status == 'none' refused (no admissible parameter)"
        if on_refused == "raise":
            raise ValueError(msg)
        print("!! " + msg, flush=True)
        rows = [r for r in rows if not _is_none_fit(r)]
        if not rows:
            raise ValueError(f"{name}: every row has fit_status == 'none' (refusing to write an empty table)")
    path = f"{R}/{name}{tag() if apply_tag else ''}.csv"
    prov = provenance(inputs, impl)
    if refused:
        prov["refused_rows"] = [{k: _py(v) for k, v in r.items()} for r in refused]
    keys = list(dict.fromkeys(k for r in rows for k in r))      # UNION of keys, first-seen order
    if sort_keys:
        keys = sorted(keys)
    stamp = dict(prov_code_sha=prov["code_sha"], prov_impl=prov["impl"],
                 prov_env=json.dumps(prov["env"], sort_keys=True),
                 prov_inputs=json.dumps(prov["inputs"], sort_keys=True), prov_utc=prov["utc"])
    conv = (lambda v: _py(v, ndigits))
    def w(f):
        wr = csv.DictWriter(f, fieldnames=keys + list(stamp), restval="")
        wr.writeheader()
        for r in rows:
            wr.writerow({**{k: conv(v) for k, v in r.items()}, **stamp})
    # meta first, then the table: the two are separate atomic replaces, so a crash in between
    # leaves an OLD csv beside a NEW meta, detectable because every row carries prov_utc and
    # meta["utc"] must equal it (never a new table described by old provenance)
    with locked(path):
        _atomic(path + ".meta.json", lambda f: json.dump(prov, f, indent=1, default=_json_default))
        _atomic(path, w)
    print(f"-> {os.path.relpath(path, ROOT)}  [code {prov['code_sha']}, env {prov['env']}]", flush=True)
    return path


def read_csv(name, apply_tag=True):
    """tag-aware CSV read (list of dicts, strings); records the file's sha as an input."""
    path = f"{R}/{name}{tag() if apply_tag else ''}.csv"
    _READ[os.path.relpath(path, ROOT)] = _sha(path)
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_json(name, obj, inputs=(), impl=None, apply_tag=True, embed=True):
    """dict payloads get a "_provenance" key unless embed=False (readers index by their own keys;
    read_json strips it); the same record always goes to <file>.meta.json."""
    path = f"{R}/{name}{tag() if apply_tag else ''}.json"
    prov = provenance(inputs, impl)
    payload = {"_provenance": prov, **obj} if (embed and isinstance(obj, dict)) else obj
    with locked(path):
        _atomic(path + ".meta.json", lambda f: json.dump(prov, f, indent=1, default=_json_default))
        _atomic(path, lambda f: json.dump(payload, f, indent=1, default=_json_default))
    print(f"-> {os.path.relpath(path, ROOT)}  [code {prov['code_sha']}, env {prov['env']}]", flush=True)
    return path


def note_input(path):
    """record a file this process read by other means (e.g. csv.DictReader) as a provenance input."""
    if os.path.exists(path):
        _READ[os.path.relpath(path, ROOT)] = _sha(path)
    return path


def write_text(path, text, inputs=(), impl=None, comment="%"):
    """atomic, locked write of a generated text file (e.g. a LaTeX table) at an explicit path,
    with a one-line provenance header in the file's comment syntax."""
    prov = provenance(inputs, impl)
    head = (f"{comment} generated by {prov['impl']} code_sha={prov['code_sha']} git={prov['git']} "
            f"utc={prov['utc']} inputs={json.dumps(prov['inputs'], sort_keys=True)}\n")
    with locked(path):
        _atomic(path, lambda f: f.write(head + text))
    print(f"-> {path}  [code {prov['code_sha']}]", flush=True)
    return path


def read_json(name, apply_tag=True):
    path = f"{R}/{name}{tag() if apply_tag else ''}.json"
    _READ[os.path.relpath(path, ROOT)] = _sha(path)
    d = json.load(open(path))
    d.pop("_provenance", None)
    return d
