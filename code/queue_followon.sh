#!/bin/bash
# Wait for the MPC grid-convergence trio and the 801 re-run, then run the
# queued CPU-bound jobs that would otherwise contend for the two cores.
while pgrep -f "mpc_perwindow.py --ngrid" > /dev/null; do sleep 60; done
echo "[queue] MPC runs finished at $(date)"
python3 -u mpc_ruled.py --cities riyadh --horizons 24 > logs_mpc_ruled_1601.txt 2>&1
echo "[queue] mpc_ruled done at $(date)"
python3 -u amy_spread.py > logs_amy_spread.txt 2>&1
echo "[queue] amy_spread done at $(date)"
