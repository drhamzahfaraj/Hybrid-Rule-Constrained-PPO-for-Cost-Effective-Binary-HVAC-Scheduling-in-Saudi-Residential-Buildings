# Material moved from the manuscript to the repository documentation (14 Nov 2026)

Each moved item is published under `docs/` in this repository. For item 1 the paper keeps one pointer sentence in its place. Nothing on which a claim of the
main text rests was moved.

| # | What | From | Why | To | Pointer sentence now in the paper |
|---|---|---|---|---|---|
| 1 | Development note that the feasibility invariant class still contains checks written for the band of an earlier model version, with the class list and what each class checks | main.tex, Section "Verification and Validity" (clause "although the feasibility class retains some checks written for the band of an earlier version of the model") | A development note, not a result | `docs/invariant-suite.md` | "…exits non-zero on any failure, and all pass; the classes and the checks each one runs are documented in the repository (`docs/invariant-suite.md`)." |
| 2 | Provenance statement that THERM's time-step and capacity comfort records in Supplementary Table S1 come from a separate THERM run | main.tex, Data and Code Availability | Pure reproducibility detail, already stated in the Table S1 caption; the run (`therm_leak.py`, files `T37_therm_leak_tl<dt>_<cth>.csv`) belongs in the repository's value map | `docs/PROVENANCE.md` (its rows for Table S1 map to the T37 files) | None; the Data and Code Availability statement links the repository and its Zenodo archive |

## Also removed from the source (not moved)

* All LaTeX comments were removed from `main.tex` and `supplement.tex`; the compiled text is
  unchanged.
