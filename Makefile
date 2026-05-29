.PHONY: check test

RUFF_VERSION ?= 0.15.14
RUFF = uvx ruff@$(RUFF_VERSION)

TY_VERSION ?= 0.0.40
TY = uvx ty@$(TY_VERSION)

check:
	$(RUFF) check .
	$(TY) check

test:
	python3 test/all_tests.py
