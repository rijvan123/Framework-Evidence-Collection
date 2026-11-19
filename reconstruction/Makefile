PY ?= python

.PHONY: install test test-slow smoke paper verify design-figures clean-smoke

install:
	$(PY) -m pip install -e ".[test]"

test:
	$(PY) -m pytest

test-slow:
	$(PY) -m pytest -m slow

smoke:
	$(PY) scripts/make_synthetic.py --out data/synthetic
	bash scripts/run_all.sh configs/smoke.yaml

paper:
	bash scripts/run_all.sh configs/default.yaml
	$(PY) scripts/compare_to_paper.py

verify:
	$(PY) scripts/verify_ledger.py --config configs/default.yaml

design-figures:
	cd figures/design && for f in fig1_architecture fig2_flow fig3_conceptual fig4_taxonomy; do $(PY) $$f.py || exit 1; done
	cd figures/literature && $(PY) fig22_coverage.py

clean-smoke:
	rm -rf runs/smoke data/synthetic
