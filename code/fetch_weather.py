#!/usr/bin/env python3
"""Obtain and verify the three TMYx weather files used by the headline study.

The files are NOT redistributed with this repository: climate.onebuilding.org
reserves its rights. Download each station's SRC-TMYx EPW from
https://climate.onebuilding.org (WMO Region 2 - Asia > Saudi Arabia), save it as
<city>.epw next to this script, and run this script to confirm it is the exact
file the paper used (SHA-256 below). Citation: Lawrie, L.K. and Crawley, D.B.,
Development of Global Typical Meteorological Years (TMYx), climate.onebuilding.org.

  city    WMO     station                       period of record    SHA-256
"""
import hashlib, os, sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
FILES = {
    "riyadh": ("404380", "Riyadh.AB (SRC-TMYx, 2009-2022, 12 years of data)",
               "a2e88409591c158ff7f86d2710e1715c4ab0b2fc072381fd8fdfe0556651dd9a"),
    "jeddah": ("410240", "Jeddah-Abdulaziz.Intl.AP (SRC-TMYx, 2009-2023)",
               "690cae887558f09ee16edc9a8ba9be1878c4709f29218df09c14759a23871c47"),
    "taif":   ("410360", "Taif.Intl.AP (SRC-TMYx, 2009-2023)",
               "dc35449564eea0ae42fdb87431c251e60ef89c7e343b1b185ae40f30e4a0110d"),
}

if __name__ == "__main__":
    bad = 0
    for city, (wmo, desc, sha) in FILES.items():
        p = os.path.join(_ROOT, f"{city}.epw")
        if not os.path.exists(p):
            print(f"MISSING {city}.epw  <- download WMO {wmo}: {desc}")
            bad += 1
            continue
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        ok = h == sha
        print(f"{'OK     ' if ok else 'MISMATCH'} {city}.epw  WMO {wmo}  {desc}")
        bad += 0 if ok else 1
    sys.exit(1 if bad else 0)
