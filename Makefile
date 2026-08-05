# Hybrid Rule-Constrained PPO for Binary HVAC Scheduling
# Convenience targets. `make help` lists everything.

PY      ?= python3
LATEX   ?= pdflatex
OUTDIR  ?= build

.PHONY: help paper clean verify validate install reference-check test

help:
	@echo "make install          install Python dependencies"
	@echo "make paper            compile main.tex -> main.pdf (pdflatex + bibtex)"
	@echo "make test             run the table consistency tests"
	@echo "make verify           re-verify the published tables reproduce"
	@echo "make validate         RC model validation and integration stability"
	@echo "make reference-check  thermostat baselines + DP optimality ceiling"
	@echo "make clean            remove LaTeX build products"

install:
	$(PY) -m pip install -r requirements.txt

paper:
	$(LATEX) -interaction=nonstopmode main.tex
	bibtex main
	$(LATEX) -interaction=nonstopmode main.tex
	$(LATEX) -interaction=nonstopmode main.tex
	@echo "main.pdf written"

test:
	$(PY) -m pytest tests/ -v || $(PY) tests/test_tables.py

verify:
	$(PY) results/load_tables.py

validate:
	cd reference_implementation && $(PY) validate_rc.py

reference-check:
	cd reference_implementation && $(PY) rerun_corrected.py --stage 1

clean:
	rm -f *.aux *.bbl *.blg *.log *.out *.synctex.gz *.fls *.fdb_latexmk
	rm -rf $(OUTDIR)
