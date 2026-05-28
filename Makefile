.PHONY: check test

RUFF_VERSION ?= 0.15.14
RUFF = uvx ruff@$(RUFF_VERSION)

TY_VERSION ?= 0.0.40
TY = uvx ty@$(TY_VERSION)

check:
	# For now check reports many issues we'll have to fix. No reformatting yet.
	#$(RUFF) check .
	$(TY) check
	#$(RUFF) format .

test:
	python3 test/all_tests.py
