#!/usr/bin/env python3
# DEPRECATED (RULING_round4 §3 F1, 2026-11-12): do not use. Retired in favour of jobq2.py +
# jobs/round4.jsonl. Known defects (SPEC_software S9): RUN lines are never reconciled, `until [ -f ]`
# jobs hold slots and spin on failed producers, non-atomic state, RBRL_* env leaks into jobs,
# no admission control. Kept only so old logs remain interpretable.
"""Persistent job queue: runs commands from queue.txt, at most MAXJ at once,
marking each line DONE/FAIL in queue_state.json. Exits after MAX_MIN minutes
(the caller relaunches it); jobs already running are left to finish and are
picked up as done when their log ends with an exit marker."""
import json, os, subprocess, sys, time
Q, ST = "jobq.txt", "jobq_state.json"
MAXJ = int(os.environ.get("MAXJ", "2")); MAX_MIN = float(os.environ.get("MAX_MIN", "110"))
t0 = time.time()
st = json.load(open(ST)) if os.path.exists(ST) else {}
running = {}
def pending():
    out = []
    for i, l in enumerate(open(Q)):
        l = l.strip()
        if l and not l.startswith("#") and st.get(l) not in ("DONE", "FAIL", "RUN"):
            out.append(l)
    return out
while True:
    for l, p in list(running.items()):
        if p.poll() is not None:
            st[l] = "DONE" if p.returncode == 0 else "FAIL"; del running[l]
            json.dump(st, open(ST, "w"), indent=1)
            print(time.strftime("%H:%M"), st[l], l, flush=True)
    if time.time() - t0 > MAX_MIN * 60:
        for l in running: st[l] = "RUN"
        json.dump(st, open(ST, "w"), indent=1); break
    todo = pending()
    if not todo and not running:
        break
    while todo and len(running) < MAXJ:
        l = todo.pop(0)
        running[l] = subprocess.Popen(["bash", "-c", l])
        st[l] = "RUN"; json.dump(st, open(ST, "w"), indent=1)
        print(time.strftime("%H:%M"), "START", l, flush=True)
    time.sleep(20)
